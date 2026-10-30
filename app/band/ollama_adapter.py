"""A Band adapter for a local Ollama model, with an explicit tool-calling loop.

Band ships no Ollama adapter, so this is a small one in the shape of Band's own:
platform history becomes chat messages, Band's tools plus the agent's own tools
are offered on every call, and each tool call the model makes is run and fed
back until it stops.

The prompt is built here in Qwen's chat format and sent raw, and tool calls are
parsed here too: small models put real line breaks inside JSON strings (any
multi-line message), which Ollama's strict tool parser rejects, silently dropping
the whole call.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, ClassVar

import httpx
from band_sdk_core import AgentFailure
from pydantic import ValidationError

from band.converters.parsing import parse_tool_call, parse_tool_result
from band.core.protocols import AgentToolsProtocol, generic_provider_failure
from band.core.simple_adapter import SimpleAdapter
from band.core.types import Emit, PlatformMessage, ToolEventKey
from band.runtime.custom_tools import (
    CustomToolDef,
    execute_custom_tool,
    find_custom_tool,
    format_validation_error,
    get_custom_tool_name,
)
from band.runtime.prompts import render_system_prompt

from app import config

log = logging.getLogger(__name__)

_PROVIDER = "ollama"
MAX_TOOL_ROUNDS = 12

Messages = list[dict[str, Any]]

TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", re.DOTALL)


def render_prompt(system: str, messages: Messages, tool_schemas: list[dict[str, Any]]) -> str:
    """ChatML with Hermes-style tools, the format Qwen 2.5 was trained on (its Ollama template, written out)."""
    tools = "\n".join(json.dumps({"type": "function", "function": s["function"]}) for s in tool_schemas)
    parts = [
        f"<|im_start|>system\n{system}\n\n# Tools\n\n"
        "You may call one or more functions to assist with the user query.\n\n"
        f"You are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{tools}\n</tools>\n\n"
        "For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n"
        '<tool_call>\n{"name": <function-name>, "arguments": <args-json-object>}\n</tool_call><|im_end|>'
    ]
    for m in messages:
        if m["role"] == "user":
            parts.append(f"<|im_start|>user\n{m['content']}<|im_end|>")
        elif m["role"] == "tool":
            parts.append(f"<|im_start|>user\n<tool_response>\n{m['content']}\n</tool_response><|im_end|>")
        else:
            calls = "\n".join(
                f'<tool_call>\n{json.dumps({"name": c["function"]["name"], "arguments": c["function"]["arguments"]})}\n</tool_call>'
                for c in m.get("tool_calls") or []
            )
            parts.append(f"<|im_start|>assistant\n{m.get('content') or calls}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


def parse_reply(text: str) -> dict[str, Any]:
    """The model's raw output as an assistant message: its tool calls, and any text outside them."""
    calls = []
    for block in TOOL_CALL.findall(text):
        try:
            call = json.loads(block, strict=False)  # strict=False: allow raw line breaks inside strings
        except ValueError:
            log.warning("Couldn't read a tool call from the model: %r", block[:300])
            continue
        calls.append({"function": {"name": call.get("name", ""), "arguments": call.get("arguments") or {}}})
    return {"role": "assistant", "content": TOOL_CALL.sub("", text).strip(), "tool_calls": calls}


class OllamaHistoryConverter:
    """Platform history -> Ollama chat messages. This agent's own text is 'assistant', everyone else's 'user'."""

    def __init__(self) -> None:
        self._agent_name = ""

    def set_agent_name(self, name: str) -> None:
        self._agent_name = name

    def convert(self, raw: list[dict[str, Any]]) -> Messages:
        messages: Messages = []
        for hist in raw:
            kind, content = hist.get("message_type", "text"), hist.get("content", "")
            if kind == "tool_call" and (call := parse_tool_call(content)):
                messages.append({"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": call.name, "arguments": call.args}},
                ]})
            elif kind == "tool_result" and (result := parse_tool_result(content)):
                messages.append({"role": "tool", "tool_name": result.name, "content": result.output})
            elif kind == "text":
                sender = hist.get("sender_name", "")
                if hist.get("role") == "assistant" and sender == self._agent_name:
                    messages.append({"role": "assistant", "content": content})
                else:
                    messages.append({"role": "user", "content": f"[{sender}]: {content}" if sender else content})
        return messages


class OllamaAdapter(SimpleAdapter[Messages]):
    SUPPORTED_EMIT: ClassVar[frozenset[Emit]] = frozenset({Emit.TOOL_CALLS})

    def __init__(
        self,
        *,
        custom_section: str,
        additional_tools: list[CustomToolDef] | None = None,
        max_history_messages: int = 40,
        exclude_tools: list[str] | None = None,
    ) -> None:
        super().__init__(history_converter=OllamaHistoryConverter(), exclude_tools=exclude_tools or [])
        self.custom_section = custom_section
        self.max_history_messages = max_history_messages
        self._custom_tools = additional_tools or []
        self._history: dict[str, Messages] = {}
        self._system_prompt = ""

    async def on_started(self, agent_name: str, agent_description: str) -> None:
        await super().on_started(agent_name, agent_description)
        # Band's base prompt tells agents to always answer whoever mentioned them, which
        # fights handing work on; shared.md covers how the room works instead.
        self._system_prompt = render_system_prompt(
            agent_name=agent_name,
            agent_description=agent_description,
            custom_section=self.custom_section,
            include_base_instructions=False,
            features=self.features,
        )

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: Messages,
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        if is_session_bootstrap or room_id not in self._history:
            self._history[room_id] = list(history or [])
        past = self._history[room_id]

        system_lines = [f"[System]: {m}" for m in (participants_msg, contacts_msg) if m]
        new = "\n".join([*system_lines, msg.format_for_llm()])
        # A small model treats every earlier message as a task still to do, so the room so far goes in
        # as one block of context and the new message is set apart as the one to answer.
        turn: Messages = [{"role": "user", "content": self._frame(past, new)}]

        tool_schemas = self._tool_schemas(tools)
        for _ in range(MAX_TOOL_ROUNDS):
            try:
                reply = await self._chat(turn, tool_schemas)
            except Exception as e:
                log.exception("Error calling Ollama")
                await tools.send_failure(generic_provider_failure(_PROVIDER, e))
                raise
            turn.append(reply)
            calls = reply.get("tool_calls") or []
            if not calls:
                break
            for call in calls:
                turn.append(await self._run_tool(call["function"], f"ollama_{uuid.uuid4().hex[:12]}", tools))
            # A reply (or a decline) that went through ends the turn; asked again, a small model just
            # repeats itself. One that failed stays in the turn, so the model sees the error and can fix it.
            if tools.turn.replied:
                break
        else:
            message = f"Exceeded max tool rounds ({MAX_TOOL_ROUNDS}) in room {room_id}"
            await tools.send_failure(AgentFailure(_PROVIDER, message))
            raise RuntimeError(message)

        past.extend([{"role": "user", "content": new}, *turn[1:]])
        del past[: max(0, len(past) - self.max_history_messages)]  # recent context only

    async def on_cleanup(self, room_id: str) -> None:
        self._history.pop(room_id, None)

    def _frame(self, past: Messages, new: str) -> str:
        now = (
            f"## New message: respond to this one only\n{new}\n\n"
            "Use your tools if you need them, then reply with band_send_message. "
            "Use band_no_reply only when a teammate is just reporting back and nothing needs doing; always answer the founder."
        )
        if not past:
            return now
        lines = []
        for m in past:
            if m["role"] == "user":
                lines.append(m["content"])
            elif m["role"] == "tool":
                lines.append(f"[Result of {m.get('tool_name', 'a tool')}]: {m['content'][:300]}")
            else:
                for call in m.get("tool_calls") or []:
                    lines.append(f"[{self.agent_name} (you) used {call['function'].get('name')}]")
                if m.get("content"):
                    lines.append(f"[{self.agent_name} (you)]: {m['content']}")
        earlier = "\n".join(lines)
        return f"## Earlier in the room (context only; already handled, don't act on it)\n{earlier}\n\n{now}"

    def _tool_schemas(self, tools: AgentToolsProtocol) -> list[dict[str, Any]]:
        # Band's schema list ignores include/exclude_tools, so apply them here.
        include, exclude = self.features.include_tools, set(self.features.exclude_tools or ())
        schemas = [
            s for s in tools.get_openai_tool_schemas(capabilities=self.features.capabilities)
            if s["function"]["name"] not in exclude and (include is None or s["function"]["name"] in include)
        ]
        for input_model, _ in self._custom_tools:
            parameters = input_model.model_json_schema()
            parameters.pop("title", None)
            schemas.append({"type": "function", "function": {
                "name": get_custom_tool_name(input_model),
                "description": input_model.__doc__ or "",
                "parameters": parameters,
            }})
        return schemas

    async def _chat(self, messages: Messages, tool_schemas: list[dict[str, Any]]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=config.OLLAMA_URL, timeout=180) as http:
            response = await http.post("/api/generate", json={
                "model": config.OLLAMA_MODEL,
                "prompt": render_prompt(self._system_prompt, messages, tool_schemas),
                "raw": True,
                "stream": False,
                "options": {"temperature": 0.3, "stop": ["<|im_end|>", "<|im_start|>"]},
            })
            response.raise_for_status()
            return parse_reply(response.json()["response"])

    async def _run_tool(self, function: dict[str, Any], call_id: str, tools: AgentToolsProtocol) -> dict[str, Any]:
        name, args = function.get("name", ""), function.get("arguments") or {}
        if isinstance(args, str):  # some models send the arguments as a JSON string
            args = json.loads(args or "{}")
        if name == "band_send_message" and isinstance(args.get("mentions"), list):
            # Small models often mention themselves (e.g. echoing @you/scout), which Band rejects outright.
            args["mentions"] = [m for m in args["mentions"] if not self._is_self(m)]

        emit = Emit.TOOL_CALLS in self.features.emit
        if emit:
            await self._event(tools, "tool_call", {ToolEventKey.NAME: name, ToolEventKey.ARGS: args, ToolEventKey.TOOL_CALL_ID: call_id})
        try:
            if custom := find_custom_tool(self._custom_tools, name):
                result = await execute_custom_tool(custom, args, turn=tools.turn)
            else:
                result = await tools.execute_tool_call(name, args)
            output, is_error = result if isinstance(result, str) else json.dumps(result, default=str), False
        except ValidationError as e:
            output, is_error = f"Invalid arguments for {name}: {format_validation_error(e)}", True
        except Exception as e:
            log.exception("Tool %s failed", name)
            output, is_error = f"Error: {e}", True
        if emit:
            await self._event(tools, "tool_result", {
                ToolEventKey.NAME: name, ToolEventKey.OUTPUT: output,
                ToolEventKey.TOOL_CALL_ID: call_id, ToolEventKey.IS_ERROR: is_error,
            })
        return {"role": "tool", "tool_name": name, "content": output}

    def _is_self(self, mention: Any) -> bool:
        label = (mention.get("handle") or mention.get("name") or "") if isinstance(mention, dict) else str(mention)
        label = label.lstrip("@").lower()
        return bool(label) and (label == self.agent_name.lower() or label.endswith(f"/{self.agent_name.lower()}"))

    @staticmethod
    async def _event(tools: AgentToolsProtocol, kind: str, payload: dict[str, Any]) -> None:
        try:
            await tools.send_event(content=json.dumps(payload, default=str), message_type=kind)
        except Exception as e:  # noqa: BLE001 -- a lost activity event must not end the turn
            log.warning("Failed to send %s event: %s", kind, e)

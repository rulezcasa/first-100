"""Tools the agents can call: plain async functions, one file per agent (plus shared.py).

A tool returns data, never finished prose: the agent's LLM decides what to say
about it and to whom. The function name is the tool name, its docstring is what
the LLM reads to decide when to call it, and its typed parameters (with
`Annotated[..., Field(description=...)]` where useful) become the arguments.
"""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, get_type_hints

from pydantic import BaseModel, create_model

ToolDef = tuple[type[BaseModel], Callable[[BaseModel], Awaitable[Any]]]


def tool(fn: Callable[..., Awaitable[Any]]) -> ToolDef:
    """Turn a plain async function into the (args model, handler) pair Band expects."""
    hints = get_type_hints(fn, include_extras=True)
    fields: dict[str, Any] = {
        name: (hints[name], ... if param.default is inspect.Parameter.empty else param.default)
        for name, param in inspect.signature(fn).parameters.items()
    }
    # Band names a tool after its model class and describes it with the model's docstring.
    args_model = create_model(fn.__name__, __doc__=inspect.getdoc(fn), **fields)

    async def handler(args: BaseModel) -> Any:
        return await fn(**dict(args))

    return args_model, handler

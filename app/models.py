"""Shapes shared by the API, the database and the LLM calls."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Founder(BaseModel):
    """The founder's background: feeds warm paths and the founder's voice in outreach."""

    name: str = ""
    past_companies: list[str] = []
    schools: list[str] = []
    investors: list[str] = []


class Product(BaseModel):
    """What setup captures about the product. Plain words, the way the founder would say it."""

    product: str = Field("", description="One line: what it is and for whom")
    buyer_roles: list[str] = Field([], description="Job titles of the person who buys it, e.g. COO, VP Operations")
    industries: list[str] = []
    pains: list[str] = Field([], description="Problems it fixes, in the buyer's words")


class Segment(BaseModel):
    name: str
    why: str
    confidence: float = Field(description="0 to 1")


class Competitor(BaseModel):
    name: str
    note: str


class Profile(Product):
    """The versioned target profile: setup's product context plus what Scout and Learner add."""

    segments: list[Segment] = []
    expansion: list[str] = []
    competitors: list[Competitor] = []
    filters: list[str] = Field([], description="The founder's own rules, e.g. 'skip companies under 50 people'")


class SetupTurn(BaseModel):
    """One turn of the setup chat: the whole form as it should now read, plus the reply."""

    product: Product
    founder: Founder
    skipped: list[str] = Field([], description="Details the founder said to skip, e.g. 'founder.background'")
    reply: str = Field(description="What Scout says back to the founder")


class WhoShouldBuy(BaseModel):
    """Scout's answer to 'who should buy this', worked out from the setup profile."""

    segments: list[Segment] = Field(description="2 to 4 groups of companies most likely to buy, best first")
    expansion: list[str] = Field(description="2 nearby groups the founder didn't mention")


SignalType = Literal["funding", "hiring", "expansion", "new_exec", "product_launch", "other"]


class FoundCompany(BaseModel):
    company: str = Field(description="The company the article is about, not the publisher")
    domain: str = Field(description="The company's website domain if the article shows it, else empty")
    article: int = Field(description="Number of the article it came from")
    signal: str = Field(description="The sentence from the article that shows why they might buy now, copied word for word")
    signal_type: SignalType


class FoundCompanies(BaseModel):
    """Companies Scout pulled out of a page of search results."""

    companies: list[FoundCompany] = Field(description="Companies that fit, at most one per article; empty if none fit")


class EvidenceItem(BaseModel):
    article: int = Field(description="Number of the article it came from")
    quote: str = Field(description="One or two sentences from the article, copied word for word")
    signal_type: SignalType
    month: str = Field(description="When it happened as YYYY-MM if the article says, else empty")


class ResearchFindings(BaseModel):
    """What Researcher pulls out of the search results about one company."""

    evidence: list[EvidenceItem] = Field(description="Facts showing why they might buy now; empty if none")
    fit: int = Field(description="0 to 40: how well the company fits who should buy the product")
    fit_reason: str = Field(description="One plain sentence on why it got that fit score")
    domain: str = Field(description="The company's own website domain if an article shows it, else empty")


class NamedFact(BaseModel):
    name: str
    article: int = Field(description="Number of the article that says it")


class NetworkFindings(BaseModel):
    """Background that can connect the founder to a lead: only what the articles say."""

    past_companies: list[NamedFact] = Field(description="Companies the person worked at before")
    schools: list[NamedFact] = Field(description="Schools or universities the person studied at")
    investors: list[NamedFact] = Field(description="Investors or funds that backed the company")


class StoryLine(BaseModel):
    text: str = Field(description="One sentence of the story")
    refs: list[int] = Field(description="Numbers of the facts this sentence is based on")


class Story(BaseModel):
    """Writer's why-now story: every sentence cites the facts it rests on."""

    sentences: list[StoryLine] = Field(description="2 to 4 sentences")


class EmailDraft(BaseModel):
    subject: str = Field(description="Short, lower-key subject line, under 8 words")
    body: str = Field(description="The email: greeting, under 90 words, signed with the founder's first name")


class Outreach(BaseModel):
    """Writer's drafts for one lead, in the founder's voice."""

    signal_email: EmailDraft = Field(description="Opens with the company's news")
    pain_email: EmailDraft = Field(description="Opens with a problem the product fixes")
    followups: list[str] = Field(description="2 short nudges to send if there's no reply")
    linkedin_note: str = Field(description="A connection note under 300 characters")

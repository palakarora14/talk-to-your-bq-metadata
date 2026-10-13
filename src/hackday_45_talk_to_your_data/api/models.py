from pydantic import BaseModel

from hackday_45_talk_to_your_data.chains.base import SourceChunk
from hackday_45_talk_to_your_data.chains.chains import DEFAULT_MODEL


class ChatRequest(BaseModel):
    session_id: str
    message: str
    project: str | None = None
    dataset: str | None = None
    time_range: str | None = None  # "last_1_day", "last_7_days", "last_30_days", "last_90_days", "all_time"
    user_email: str | None = None
    model: str = DEFAULT_MODEL


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[SourceChunk] = []

from pydantic import BaseModel, ConfigDict


class DirectCommandDraft(BaseModel):
    """The draft for a direct command """
    model_config = ConfigDict(extra="forbid")
    target_value: float | None
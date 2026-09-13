from __future__ import annotations
import json
from typing import Any
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime
from langgraph.types import Command
from agentic_bim_iot.application.react_agent.state import Context, State

Runtime = ToolRuntime[Context, State]

def to_json(value: Any) -> str:
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json(indent=2)
    return json.dumps(value, indent=2, default=str)

def tool_command(runtime: Runtime, content: str, **updates: Any) -> Command:
    return Command(update={**updates, "messages": [ToolMessage(content=content, tool_call_id=runtime.tool_call_id)]})
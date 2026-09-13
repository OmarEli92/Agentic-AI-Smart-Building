from __future__ import annotations
from typing import Any
from langchain.messages import HumanMessage

from agentic_bim_iot.application.react_agent.tools.common import Runtime
from agentic_bim_iot.application.supervisor.reference_guard import extract_explicit_room_reference

#just a set of possible affirmative resposnes that the facility manager would give when the LLM asks him about an action
_AFFIRMATIVE_RESPONSES = {
    "yes", "yes please", "yes, please", "sure", "ok",
    "okay", "please do", "go ahead", "do it",
}


def resolve_room_reference(*, runtime: Runtime, requested_room: str | None = None) -> str | None:
    """user room reference > model-generated tool argument
    Therefore an LLM cannot transform: "kitchen" -> BIM identifier "5"
    """
    current_room = extract_explicit_room_reference(runtime.context.user_query)
    if current_room:
        return current_room
    messages = runtime.state.get("messages", [])
    for message in reversed(messages):
        if not isinstance(message, HumanMessage):
            continue
        text = _message_text(message)
        if not text:
            continue
        room = extract_explicit_room_reference(text)
        if room:
            return room
    if requested_room:
        normalized = requested_room.strip()
        if normalized:
            return normalized

    return None


def planning_request(*, runtime: Runtime, room_reference: str) -> str:
    """ Since the React configuration use the planning agent that expect a more verbose answer than a yes
    then we need to return an answer like that """
    current = runtime.context.user_query.strip()
    if current.casefold() in _AFFIRMATIVE_RESPONSES:
        return f"Create an action proposal to improve the current comfort conditions in {room_reference}."
    return current


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""
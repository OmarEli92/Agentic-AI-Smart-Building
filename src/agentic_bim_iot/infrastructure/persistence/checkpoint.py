from langgraph.checkpoint.memory import InMemorySaver
from agentic_bim_iot.infrastructure.persistence.checkpoint_types import CHECKPOINT_ALLOWED_TYPES
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


def create_checkpointer() -> InMemorySaver:
    serializer = JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_ALLOWED_TYPES)
    return InMemorySaver(serde=serializer)
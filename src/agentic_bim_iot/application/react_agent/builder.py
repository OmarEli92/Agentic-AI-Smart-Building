from __future__ import annotations
from typing import Any
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.middleware import ToolTracingMiddleware
from agentic_bim_iot.application.react_agent.prompt import SYSTEM_PROMPT
from agentic_bim_iot.application.react_agent.state import Context, State
from agentic_bim_iot.application.react_agent.tools import create_full_react_tools
from agentic_bim_iot.application.react_agent.transient_state_fields import TRANSIENT_STATE_FIELDS
from agentic_bim_iot.infrastructure.persistence.checkpoint import create_checkpointer



class Application(Runnable[dict[str, Any], dict[str, Any]]):

    def __init__(self, *, agent: Runnable, recursion_limit: int) -> None:
        self._agent = agent
        self._recursion_limit = recursion_limit


    def invoke(self, input: dict[str, Any], config: RunnableConfig | None = None, **kwargs: Any) -> dict[str, Any]:
        user_query = str(input.get("user_query", "")).strip()
        if not user_query:
            raise ValueError("user_query cannot be empty.")
        invocation_config: RunnableConfig = dict(config or {})
        invocation_config.setdefault("recursion_limit", self._recursion_limit)
        configurable = dict(invocation_config.get("configurable",{}))
        thread_id = str(configurable.get("thread_id", "")).strip()
        if not thread_id:
            raise ValueError("Full ReAct orchestration requires configurable.thread_id so that conversation memory can be isolated by session.")
        configurable["thread_id"] = thread_id
        invocation_config["configurable"] = configurable
        turn_input: dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": user_query,
                }
            ]
        }
        for field in TRANSIENT_STATE_FIELDS:
            turn_input[field] = None
        result = self._agent.invoke(turn_input, config=invocation_config, context=Context(user_query=user_query))
        output = dict(result)
        output["final_answer"] = self._extract_final_text(output.get("messages", []))
        return output


    @staticmethod
    def _extract_final_text(messages: list[Any]) -> str:
        if not messages:
            return ""
        content = getattr(messages[-1], "content", "")
        if isinstance(content, str):
            return content
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
        return str(content)


def build(*, chat_model: BaseChatModel, dependencies: GraphDependencies, recursion_limit: int,
          model_call_limit: int, tool_call_limit: int) -> Application:
    middleware = [
        ToolTracingMiddleware(),
        ModelCallLimitMiddleware(run_limit=model_call_limit, exit_behavior="end"),
        ToolCallLimitMiddleware(run_limit=tool_call_limit, exit_behavior="continue"),
        ToolCallLimitMiddleware(tool_name=("execute_explicit_direct_actuation"),run_limit=1, exit_behavior="continue"),
        ToolCallLimitMiddleware(tool_name=("approve_and_execute_pending_proposal"),run_limit=1, exit_behavior="continue")
        ]

    agent = create_agent(
        model=chat_model,
        tools=create_full_react_tools(dependencies),
        system_prompt=SYSTEM_PROMPT,
        state_schema=State,
        context_schema=Context,
        middleware=middleware,
        checkpointer=create_checkpointer()
    )
    return Application(agent=agent, recursion_limit=recursion_limit)
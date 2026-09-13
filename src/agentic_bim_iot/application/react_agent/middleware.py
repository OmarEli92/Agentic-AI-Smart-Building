from __future__ import annotations
import logging
import time
from collections.abc import Callable
from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command


logger = logging.getLogger("agentic_bim_iot.react_agent")

class ToolTracingMiddleware(AgentMiddleware):

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage | Command]) -> ToolMessage | Command:
        tool_call = request.tool_call
        tool_name = str(tool_call.get("name", "unknown"))
        tool_args = tool_call.get("args", {})
        started_at_ns = time.perf_counter_ns()
        logger.info(
            "ReAct tool call started.",
            extra={
                "event": "react_tool_started",
                "component": "react_agent",
                "tool_name": tool_name,
                "tool_args": tool_args,
            },
        )
        try:
            result = handler(request)
        except Exception:
            duration_ms = (time.perf_counter_ns() - started_at_ns) / 1_000_000
            logger.exception(
                "ReAct tool call failed.",
                extra={
                    "event": "react_tool_failed",
                    "component": "react_agent",
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "duration_ms": duration_ms,
                    "tool_status": "failed",
                },
            )
            raise
        duration_ms = (time.perf_counter_ns() - started_at_ns) / 1_000_000
        logger.info(
            "ReAct tool call completed.",
            extra={
                "event": "react_tool_completed",
                "component": "react_agent",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "duration_ms": duration_ms,
                "tool_status": "succeeded",
            }
        )
        return result
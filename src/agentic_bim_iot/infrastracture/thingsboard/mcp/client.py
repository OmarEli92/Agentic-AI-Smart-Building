import asyncio
import json
from typing import Any


class ThingsBoardMCPError(RuntimeError):
    ...


class ThingsBoardMCPClient:
    """The Implementation for the THingsboard MCP client"""

    def __init__(self, sse_url: str, timeout_seconds: float) -> None:
        self._sse_url = sse_url.strip()
        self._timeout_seconds = timeout_seconds
        if not self._sse_url:
            raise ValueError("ThingsBoard MCP SSE URL cannot be empty.")

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a ThingsBoard MCP tool."""

        try:
            return asyncio.run(self._call_tool(tool_name=tool_name, arguments=arguments))
        except ThingsBoardMCPError:
            raise
        except Exception as exc:
            raise ThingsBoardMCPError(f"ThingsBoard MCP tool '{tool_name}' failed: {exc}") from exc


    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        try:
            from mcp import Client
            from mcp.client.sse import sse_client

        except ImportError as exc:
            raise ThingsBoardMCPError("The MCP backend requires the 'mcp' Python package.") from exc
        transport = sse_client(self._sse_url, timeout=self._timeout_seconds, sse_read_timeout=max(300.0, self._timeout_seconds))
        async with Client(transport) as client:
            result = await asyncio.wait_for(client.call_tool( tool_name, arguments),
                timeout=self._timeout_seconds
            )

        if bool(getattr(result, "is_error", False)):
            raise ThingsBoardMCPError(
                self._extract_error(
                    tool_name,
                    result
                )
            )
        content = getattr(result, "content", None) or []
        text_parts = [str(block.text) for block in content if getattr(block, "text", None) is not None]
        if text_parts:
            text = "\n".join(text_parts).strip()
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        structured_content = getattr(result, "structured_content", None)
        if structured_content is not None:
            return structured_content
        return None

    @staticmethod
    def _extract_error( tool_name: str, result: Any) -> str:
        content = getattr(result, "content", None) or []
        messages = [str(block.text) for block in content if getattr(block, "text", None) is not None]
        detail = "\n".join(messages).strip()
        if detail:
            return (f"ThingsBoard MCP tool '{tool_name}' returned an error: {detail}")
        return (f"ThingsBoard MCP tool '{tool_name}' returned an error.")

    def close(self) -> None:
        """Close the client."""
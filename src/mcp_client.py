from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def _send_email_async(to: str, subject: str, body: str):
    """
    Connect to the local MCP email server over stdio
    and invoke the send_email MCP tool.
    """

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "src.mcp_email_server",
            "--transport",
            "stdio",
        ],
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # Initialize MCP connection
            await session.initialize()

            # Confirm the tool exists
            tools = await session.list_tools()

            tool_names = [tool.name for tool in tools.tools]

            if "send_email" not in tool_names:
                raise RuntimeError(
                    f"MCP server does not expose send_email. "
                    f"Available tools: {tool_names}"
                )

            # Call the MCP tool
            result = await session.call_tool(
                "send_email",
                {
                    "to": to,
                    "subject": subject,
                    "body": body,
                },
            )

            if getattr(result, "is_error", False):
                error_text = "\n".join(
                    getattr(item, "text", str(item))
                    for item in result.content
                )
                raise RuntimeError(error_text)

            response_text = "\n".join(
                getattr(item, "text", str(item))
                for item in result.content
            )

            return response_text


def send_email_via_mcp(to: str, subject: str, body: str):
    """
    Synchronous wrapper used by the Streamlit/agent application.
    """
    return asyncio.run(
        _send_email_async(
            to=to,
            subject=subject,
            body=body,
        )
    )
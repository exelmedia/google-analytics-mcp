#!/usr/bin/env python

# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTTP server wrapper for Google Analytics MCP server."""

import asyncio
import json
from typing import Any, Dict
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from analytics_mcp.coordinator import mcp

# Import tools to register them
from analytics_mcp.tools.admin import info  # noqa: F401
from analytics_mcp.tools.reporting import realtime  # noqa: F401
from analytics_mcp.tools.reporting import core  # noqa: F401

app = FastAPI(title="Google Analytics MCP HTTP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "server": "Google Analytics MCP Server",
        "version": "0.1.1",
        "transport": "http"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication."""
    async def event_generator():
        try:
            # Read the request body
            body = await request.json()
            
            # Process the MCP request
            # This is a simplified version - you may need to adapt based on actual MCP protocol
            result = await process_mcp_request(body)
            
            # Send the response as SSE
            yield f"data: {json.dumps(result)}\n\n"
        except Exception as e:
            error_response = {
                "error": str(e),
                "type": type(e).__name__
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/message")
async def message_endpoint(request: Request):
    """REST endpoint for MCP messages."""
    try:
        body = await request.json()
        result = await process_mcp_request(body)
        return result
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }, 500


async def process_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Process an MCP request and return the result."""
    method = request.get("method")
    
    if method == "tools/list":
        # List available tools
        tools = []
        for name, tool_func in mcp._tool_manager._tools.items():
            tools.append({
                "name": name,
                "description": tool_func.__doc__ or "",
                "inputSchema": getattr(tool_func, "_mcp_input_schema", {})
            })
        return {
            "tools": tools
        }
    
    elif method == "tools/call":
        # Call a tool
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in mcp._tool_manager._tools:
            return {
                "error": f"Tool '{tool_name}' not found",
                "isError": True
            }
        
        tool_func = mcp._tool_manager._tools[tool_name]
        
        try:
            # Call the tool function
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling tool: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    elif method == "initialize":
        # Initialize the connection
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "Google Analytics MCP Server",
                "version": "0.1.1"
            }
        }
    
    else:
        return {
            "error": f"Unknown method: {method}",
            "isError": True
        }


def run_http_server(host: str = "0.0.0.0", port: int = 9000):
    """Run the HTTP server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_http_server()

import os
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from tools.mcp_factory import get_mcp_tools, parse_mcp_servers_env

MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-opus-4-5-20251101-v1:0")

mcp_server_names = list(parse_mcp_servers_env().keys())

SYSTEM_PROMPT = f"""
You are an expert in both platform engineering/devops and machine learning/AI engineering. You are running in a Kubernetes cluster in which users submit AI/ML training/inference workloads.

Your purpose is to help users identify inefficiencies and waste in their jobs, that includes:
- Incorrect/inefficient hyperparameters given their resources
- GPU inefficiencies - GPUs are being used incorrectly or that the job is misconfigured
- Right sizing the resources - offer suggestions to change resources that will either positively or neutrally affect the performance of the job. Give cost number justifications to these decisions.

You are also well aware of the USE method and the ambiguity regarding using GPU utilization as a metric for efficiency.
Drill down into GPU metrics available through DCGM to understand SM occupancy, activity, FP pipes and more to understand the effective use of the GPU.
Look for correlations between node networking, storage, memory, and CPU to understand if one may be bottlenecking other resources and offer suggestions.

You have access to the following MCP servers: {', '.join(mcp_server_names) if mcp_server_names else 'none configured'}. You can use these to get access to logs, metrics, and resources stored in the cluster.
Code may be available as configmaps, so check whether that is available and give concrete examples of what you can change in the code to make these optimizations.
OpenCost is also available in the environment, so you have access to cost metrics. Explain changes in resources by looking at the costs as well and estimating the cost differences based on the changes.

Users may ask you for a specific job they want recommendations for. In this case, you should look for logs, metrics, and code to understand and optimize the situation.
You may also get asked to identify an issue, for instance, you may be asked why a workload has elevated 5XX errors or a stalled loss decent. You should be able to identify and recommend solutions to these challenges as well.

Any recommendations you give should work on the current instance and resource configuration. If you make a recommendation that will OOM or otherwise crash the pod, you need to clarify that a bigger instance type is needed.
"""

# Global agent and MCP tools
agent: Agent = None
mcp_tools = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage agent lifecycle on startup/shutdown."""
    global agent, mcp_tools

    mcp_tools = get_mcp_tools()

    agent = Agent(
        model=MODEL_ID,
        system_prompt=SYSTEM_PROMPT,
        tools=mcp_tools,
        conversation_manager=SlidingWindowConversationManager(window_size=5),
    )
    print(f"Agent initialized with model={MODEL_ID}, {len(mcp_tools)} MCP tool(s)")

    yield


app = FastAPI(
    title="ML Optimization Agent",
    description="Agent API for analyzing ML workloads and providing optimization recommendations",
    lifespan=lifespan,
)


class PromptRequest(BaseModel):
    prompt: str


async def stream_agent_response(prompt: str) -> AsyncGenerator[str, None]:
    """Stream agent response as SSE events."""
    try:
        async for event in agent.stream_async(prompt):
            if "data" in event:
                yield f"data: {json.dumps({'type': 'text', 'content': event['data']})}\n\n"
            elif "current_tool_use" in event:
                tool_info = event["current_tool_use"]
                yield f"data: {json.dumps({'type': 'tool', 'name': tool_info.get('name'), 'input': tool_info.get('input')})}\n\n"
            elif "result" in event:
                result = event["result"]
                yield f"data: {json.dumps({'type': 'result', 'content': str(result)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/prompt")
async def submit_prompt(request: PromptRequest):
    """
    Submit a prompt to the agent and stream the response.
    Returns Server-Sent Events (SSE) stream.
    """
    return StreamingResponse(
        stream_agent_response(request.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "mcp_servers": mcp_server_names,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

# agent_runner.py
import datetime as dt
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from mcp_client import get_mcp_client
from mcp_client import get_mcp_tools_cached
import os


async def build_agent():
    llm = init_chat_model(
        "gemini-2.5-pro",
        model_provider="google_genai",
        api_key=os.environ.get("GOOGLE_API_KEY")
    )
    client = get_mcp_client()
    return create_react_agent(llm, tools=await get_mcp_tools_cached())

async def run_agent(prompt: str, SYSTEM_PROMPT: str):
    agent = await build_agent()
    result = await agent.ainvoke({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    })
    return result["messages"][-1].content



async def run_agent_with_tools(agent, user_prompt):
    """
    Run an agent with just a user prompt and tools (no system prompt).
    Returns the full result object from the agent.
    """
    return await agent.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})


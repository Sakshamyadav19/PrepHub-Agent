# backend/agent/prep_agent.py
import os
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from prompts.interview_prompts import get_prompt_for_prep_brief
from utils.json_parser import safe_extract_json
from agent_runner import run_agent_with_tools
from mcp_client import get_mcp_client

async def run_prep_agent(company, role):
    prompt = get_prompt_for_prep_brief(company, role)
    client = get_mcp_client()
    llm = init_chat_model("gemini-2.5-pro", model_provider="google_genai",api_key="AIzaSyC0p6-LHxNpvVdzfulFb1RiysRDhDgnWRI")
    tools = await client.get_tools()
    agent = create_react_agent(llm, tools)

    result = await run_agent_with_tools(agent, prompt)
    content = result["messages"][-1].content
    return safe_extract_json(content)

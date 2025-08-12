# mcp_client.py
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

def get_mcp_client():
    return MultiServerMCPClient({
        "gmail": {
            "transport": "stdio",
            "command": "/Users/sakshamyadav/meetingAssistant/backend/gmail-mcp-server/gmail-mcp-server",
            "args": [],
            "env": {
                "GMAIL_CLIENT_ID": os.environ["GMAIL_CLIENT_ID"],
                "GMAIL_CLIENT_SECRET": os.environ["GMAIL_CLIENT_SECRET"],
                "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
            }
        },
        "google-calendar": {
            "transport": "stdio",
            "command": "npx",
            "args": ["@cocal/google-calendar-mcp"],
            "env": {
                "GOOGLE_OAUTH_CREDENTIALS": os.environ["GOOGLE_OAUTH_CREDENTIALS"],
                "PORT": "5000"
            }
        },
        "firecrawl-mcp": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "firecrawl-mcp"],
            "env": {
                "FIRECRAWL_API_KEY": os.environ["FIRECRAWL_API_KEY"],
            }
        },
    })

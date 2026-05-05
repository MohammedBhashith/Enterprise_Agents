import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")


def web_search(query: str):
    """
    Optional web search fallback using Serper API.
    If API key is not configured, it returns a safe message.
    """

    if not SERPER_API_KEY:
        return (
            "Web search is not configured yet. "
            "Please add SERPER_API_KEY in .env to enable external troubleshooting search."
        )

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": 3
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"Web search failed. Status: {response.status_code}"

        data = response.json()
        results = data.get("organic", [])

        if not results:
            return "No useful web results found."

        final = "### Web Search Results\n\n"

        for item in results[:3]:
            title = item.get("title", "No title")
            snippet = item.get("snippet", "No summary available")
            link = item.get("link", "")

            final += (
                f"#### {title}\n"
                f"{snippet}\n\n"
                f"Source: {link}\n\n"
            )

        return final

    except Exception as e:
        return f"Web search failed: {str(e)}"
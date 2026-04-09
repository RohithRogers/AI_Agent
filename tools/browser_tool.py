import requests
from tools.registry import tool

@tool(
    name="get_webpage_content",
    description="Fetches the content of a webpage.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL of the webpage."}
        },
        "required": ["url"]
    },
    requires_permission=True
)
def get_webpage_content(url: str) -> str:
    """Fetches the content of a webpage."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching webpage: {e}"

@tool(
    name="search_web",
    description="Searches the web for snippets of information using DuckDuckGo.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."}
        },
        "required": ["query"]
    },
    requires_permission=True
)
def search_web(query: str) -> str:
    """Uses DDGS to search for quick results/snippets."""
    try:
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message="This package .* has been renamed to .*")
        
        from duckduckgo_search import DDGS
        results = ""
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results += f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n\n"
        
        return results if results else "No results found for your query."
    except ImportError:
        return "Error: 'duckduckgo-search' package is not installed. Please run: pip install duckduckgo-search"
    except Exception as e:
        return f"Searching DuckDuckGo Error: {e}"

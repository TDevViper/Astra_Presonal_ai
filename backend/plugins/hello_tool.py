from tools.registry import tool

@tool("hello", "say hello to someone")
def hello(name: str) -> str:
    return f"Hello, {name}! ASTRA plugin system is working."

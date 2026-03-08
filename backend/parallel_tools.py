import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

def run_tool_sync(tool_name: str, user_input: str, context: dict) -> dict:
    try:
        from tools import dispatch_tool
        return {"tool": tool_name, "result": dispatch_tool(tool_name, user_input, context)}
    except Exception as e:
        return {"tool": tool_name, "result": None, "error": str(e)}

async def run_tools_parallel_async(tool_names: list, user_input: str, context: dict) -> list:
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(_executor, run_tool_sync, tool, user_input, context)
        for tool in tool_names
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]

def execute_tools(tool_names: list, user_input: str, context: dict) -> list:
    if not tool_names:
        return []
    if len(tool_names) == 1:
        return [run_tool_sync(tool_names[0], user_input, context)]
    try:
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(run_tools_parallel_async(tool_names, user_input, context))
    except Exception:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(run_tools_parallel_async(tool_names, user_input, context))

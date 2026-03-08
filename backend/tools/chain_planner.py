import re

CHAIN_KEYWORDS = {
    "search":    ["search", "find", "look up", "google", "what is", "latest"],
    "save_file": ["save", "write to file", "store", "export"],
    "summarize": ["summarize", "summary", "tldr", "brief"],
    "remind":    ["remind", "reminder", "alert me"],
    "add_task":  ["add task", "create task", "todo"],
    "run_code":  ["run", "execute", "python"],
}

CHAIN_CONNECTORS = ["and", "then", "after that", "also", "next"]

def detect_chain(user_input: str) -> list:
    text = user_input.lower()
    has_connector = any(f" {c} " in f" {text} " for c in CHAIN_CONNECTORS)
    if not has_connector:
        return []
    steps = []
    for tool, keywords in CHAIN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            steps.append(tool)
    return steps if len(steps) > 1 else []

def build_chain_plan(user_input: str, detected_steps: list) -> list:
    text = user_input.lower()
    plan = []
    for step in detected_steps:
        if step == "search":
            query = user_input
            for connector in CHAIN_CONNECTORS:
                if connector in text:
                    query = user_input[:text.index(connector)].strip()
                    break
            plan.append({"tool": "search", "input": query})
        elif step == "save_file":
            path_match = re.search(r'(?:to|as|named?)\s+["\']?([^\s"\']+\.?\w+)["\']?', text)
            path = path_match.group(1) if path_match else "astra_output.txt"
            if "." not in path:
                path += ".txt"
            plan.append({"tool": "save_file", "path": path, "input": "__prev__"})
        elif step == "summarize":
            plan.append({"tool": "summarize", "input": "__prev__"})
        elif step == "remind":
            plan.append({"tool": "remind", "input": user_input})
        elif step == "add_task":
            plan.append({"tool": "add_task", "input": user_input})
    return plan

def execute_chain(plan: list, brain) -> str:
    results = []
    prev_result = ""
    for step in plan:
        inp = prev_result if step.get("input") == "__prev__" else step.get("input", "")
        tool = step["tool"]
        try:
            if tool == "search":
                from tools.web_search import handle_search_command
                result = handle_search_command(inp)
                prev_result = result
                results.append(f"[Search] {result[:200]}...")
            elif tool == "save_file":
                path = step.get("path", "astra_output.txt")
                with open(path, "w") as f:
                    f.write(prev_result)
                prev_result = f"Saved to {path}"
                results.append(f"[Saved] → {path}")
            elif tool == "summarize":
                words = inp.split()
                summary = " ".join(words[:80]) + ("..." if len(words) > 80 else "")
                prev_result = summary
                results.append(f"[Summary] {summary}")
            elif tool == "remind":
                results.append(f"[Reminder] Set for: {inp}")
            elif tool == "add_task":
                results.append(f"[Task] Added: {inp}")
        except Exception as e:
            results.append(f"[{tool}] Error: {str(e)}")
    return "\n".join(results)

import logging
import re
import ollama
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_STEPS  = 5
MAX_TOKENS = 500

_REACT_TRIGGERS = [
    "why", "how does", "step by step", "walk me through",
    "break down", "reason", "analyze", "explain how",
    "what would happen if", "should i", "compare", "pros and cons",
    "debug", "figure out", "investigate", "research", "find out why",
    "what's causing", "help me understand", "plan",
]

_SKIP_TRIGGERS = [
    "hi", "hello", "hey", "thanks", "bye", "what time",
    "what's my name", "how are you", "tell me a joke",
]

TOOL_DESCRIPTIONS = """
Available tools — call them with Action: tool_name(argument)

- web_search(query)      search the web, returns top results
- read_file(path)        read a file from the filesystem
- run_python(code)       execute Python code, returns stdout
- memory_recall(query)   search Astra's personal memory
- graph_lookup(entity)   look up knowledge graph relations
- calculate(expression)  evaluate a math expression safely
"""


def needs_react(user_input: str) -> bool:
    t = user_input.lower()
    if any(t.startswith(s) or s == t for s in _SKIP_TRIGGERS):
        return False
    return any(trigger in t for trigger in _REACT_TRIGGERS)


def _execute_tool(tool_name: str, arg: str, user_name: str = "User") -> str:
    tool_name = tool_name.strip().lower()
    arg       = arg.strip().strip('"\'')
    try:
        if tool_name == "web_search":
            from websearch.search import serper_search, format_results_for_llm
            results = serper_search(arg, num_results=3)
            if not results:
                return "No results — SERPER_API_KEY may not be set."
            return format_results_for_llm(results, max_chars=800)

        elif tool_name == "read_file":
            from tools.file_reader import read_file as _read
            result = _read(arg)
            if result["success"]:
                return f"{result['filepath']} ({result['lines']} lines):\n{result['content'][:1500]}"
            return f"Error: {result['error']}"

        elif tool_name == "run_python":
            import subprocess, sys
            result = subprocess.run(
                [sys.executable, "-c", arg],
                capture_output=True, text=True, timeout=10
            )
            out = result.stdout.strip() or result.stderr.strip()
            return out[:800] if out else "(no output)"

        elif tool_name == "memory_recall":
            from memory.vector_store import semantic_search
            facts, exchanges = semantic_search(arg, top_k=3)
            hits = [h["text"] for h in (facts + exchanges)[:4]]
            return "\n".join(hits) if hits else "Nothing found in memory."

        elif tool_name == "graph_lookup":
            from knowledge.graph import get_relations
            rels = get_relations(arg, depth=1)
            if not rels:
                return f"No graph data for '{arg}'."
            lines = [f"• {r['subject']} {r['relation'].replace('_',' ')} {r['object']}"
                     for r in rels[:6]]
            return "\n".join(lines)

        elif tool_name == "calculate":
            import ast, operator
            ops = {
                ast.Add: operator.add, ast.Sub: operator.sub,
                ast.Mult: operator.mul, ast.Div: operator.truediv,
                ast.Pow: operator.pow, ast.USub: operator.neg,
            }
            def _eval(node):
                if isinstance(node, ast.Constant): return node.value
                elif isinstance(node, ast.BinOp):
                    return ops[type(node.op)](_eval(node.left), _eval(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](_eval(node.operand))
                raise ValueError(f"Unsupported: {node}")
            return str(_eval(ast.parse(arg, mode='eval').body))

        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool error ({tool_name}): {e}"


def _parse_action(text: str) -> Optional[tuple]:
    match = re.search(r'Action:\s*(\w+)\((.+?)\)', text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    match2 = re.search(r'Action:\s*(\w+):\s*(.+)', text)
    if match2:
        return match2.group(1), match2.group(2).strip()
    return None


def react_solve(user_input: str, model: str = "phi3:mini",
                context: str = "", user_name: str = "User") -> Dict:
    logger.info(f"ReAct v3 starting: {user_input[:60]}")

    system_prompt = f"""You are ASTRA, {user_name}'s personal AI assistant.
Solve this step by step using Thought -> Action -> Observation cycles.

{TOOL_DESCRIPTIONS}

FORMAT (use exactly):
Thought: what you're thinking
Action: tool_name(argument)
Observation: [filled in by system]

When done, end with:
Final Answer: [your complete, direct answer]

Context about {user_name}: {context if context else 'none'}
Be concise. Max {MAX_STEPS} cycles."""

    messages: List[Dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_input},
    ]

    steps    = []
    full_out = ""

    try:
        for step in range(MAX_STEPS):
            response = ollama.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.35, "num_predict": MAX_TOKENS}
            )
            output = response["message"]["content"].strip()
            full_out += output + "\n"

            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("Thought:"):
                    steps.append({"type": "thought", "content": line[8:].strip()})
                elif line.startswith("Action:"):
                    steps.append({"type": "action",  "content": line[7:].strip()})
                elif line.startswith("Observation:"):
                    steps.append({"type": "observe",  "content": line[12:].strip()})

            if "Final Answer:" in output:
                break

            parsed = _parse_action(output)
            if parsed:
                tool_name, arg = parsed
                logger.info(f"Tool call: {tool_name}({arg[:40]})")
                observation = _execute_tool(tool_name, arg, user_name)
                steps.append({"type": "observe", "content": observation[:200]})
                messages.append({"role": "assistant", "content": output})
                messages.append({
                    "role": "user",
                    "content": f"Observation: {observation}\n\nContinue reasoning."
                })
            else:
                messages.append({"role": "assistant", "content": output})
                messages.append({"role": "user", "content": "Continue."})

        if "Final Answer:" in full_out:
            final = full_out.split("Final Answer:")[-1].strip().split("\n\n")[0].strip()
        else:
            lines = [l.strip() for l in full_out.split("\n")
                     if l.strip() and not any(l.startswith(p)
                     for p in ["Thought:", "Action:", "Observation:"])]
            final = lines[-1] if lines else full_out.strip()

        reasoning = []
        for s in steps:
            if s["type"] == "thought": reasoning.append(f"💭 {s['content']}")
            elif s["type"] == "action": reasoning.append(f"⚡ {s['content']}")
            elif s["type"] == "observe": reasoning.append(f"👁 {s['content'][:120]}")

        answer = ("\n".join(reasoning) + "\n\n" + final) if reasoning else final
        logger.info(f"ReAct done — {len(steps)} steps")
        return {"answer": answer, "steps": steps, "success": True}

    except Exception as e:
        logger.error(f"ReAct failed: {e}")
        return {"answer": "", "steps": [], "success": False}


def react(user_input: str, model: str = "phi3:mini",
          context: str = "", user_name: str = "User") -> str:
    if not needs_react(user_input):
        return ""
    result = react_solve(user_input, model=model, context=context, user_name=user_name)
    return result["answer"] if result["success"] else ""

import ollama, json, re

EXTRACT_PROMPT = """Extract entities and relationships from this text.
Return ONLY valid JSON, no preamble, no markdown fences:
{{"entities": [{{"name": "...", "type": "person|place|tech|project|concept"}}],
 "relations": [{{"from": "...", "to": "...", "relation": "..."}}]}}
Text: {text}"""

def extract_and_store(text: str, user_name: str = "Arnav"):
    try:
        client   = ollama.Client()
        prompt   = EXTRACT_PROMPT.format(text=text[:800])
        response = client.chat(
            model="phi3:mini",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 300}
        )
        raw  = response["message"]["content"].strip()
        raw  = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        from knowledge.graph import add_entity, add_relation
        for e in data.get("entities", []):
            add_entity(e["name"], e["type"])
        for r in data.get("relations", []):
            add_relation(r["from"], r["to"], r["relation"])
    except Exception:
        pass

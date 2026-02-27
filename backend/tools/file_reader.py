import json, csv, os, re

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # points to backend/

def extract_filepath(text: str) -> str | None:
    match = re.search(r'[\w./\\-]+\.(?:py|txt|json|csv|js|ts|md|yaml|yml|env|sh|html|css)', text)
    return match.group(0) if match else None

def list_files(directory: str = ".") -> dict:
    try:
        target = os.path.join(BASE, directory)
        entries = []
        for name in sorted(os.listdir(target))[:50]:
            full = os.path.join(target, name)
            entries.append({"name": name, "type": "dir" if os.path.isdir(full) else "file"})
        return {"success": True, "directory": target, "files": entries, "count": len(entries)}
    except Exception as e:
        return {"success": False, "error": str(e), "files": [], "count": 0}

def read_file(path: str) -> dict:
    full_path = path if os.path.isabs(path) else os.path.join(BASE, path)
    if not os.path.exists(full_path):
        return {"success": False, "error": f"File not found: {full_path}"}
    try:
        with open(full_path, "r", errors="replace") as f:
            content = f.read()
        lines = content.count("\n") + 1
        truncated_at = None
        if lines > 300:
            content = "\n".join(content.split("\n")[:300])
            truncated_at = 300
        return {
            "success": True,
            "filepath": full_path,
            "content": content,
            "lines": lines,
            "truncated": truncated_at is not None,
            "truncated_at": truncated_at
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

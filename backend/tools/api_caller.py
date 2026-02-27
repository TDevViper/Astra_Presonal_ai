import requests

def call_api(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.text[:1500]  # prevent huge outputs
    except Exception as e:
        return f"API error: {e}"

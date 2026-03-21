import json
import re
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
THREAD_ID = "test-thread"

def post(user_text: str):
    url = f"{BASE_URL}/chat/{THREAD_ID}"
    payload = json.dumps({"user_text": user_text, "mode": "debug"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def sentence_count(text):
    if not text:
        return None
    return len([s for s in re.split(r"[.!?]+", text) if s.strip()])

tests = [
    ("4) Framework-internal clarification", "What is diffraction?"),
    ("5) Plain internal clarification", "Say plainly what diffraction means here."),
    ("6) Operative options", "Give me three direct options for moving forward."),
    ("7) Lineage-context clarification", "Where does diffraction come from?"),
]

for label, prompt in tests:
    d = post(prompt)
    print()
    print(label)
    print(json.dumps({
        "text": d.get("text"),
        "sentence_count": sentence_count(d.get("text")),
        "response_mode": d.get("loopcycle", {}).get("notes", {}).get("response_mode"),
        "clarification_scope": d.get("debug", {}).get("turn_conditions", {}).get("clarification_scope"),
        "asks_action": d.get("debug", {}).get("turn_conditions", {}).get("asks_action"),
        "exact_quantity": d.get("debug", {}).get("turn_conditions", {}).get("exact_quantity"),
        "drift_detected": d.get("loopcycle", {}).get("drift_detected"),
    }, indent=2))

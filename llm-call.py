import os
from typing import Any, Dict, List, Tuple

from tools import find_doctors, get_availability, book_appointment

import requests

from dotenv import load_dotenv

TOGETHER_CHAT_URL  = "https://api.together.xyz/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

def get_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise RuntimeError("Together.ai api key not found")
    return api_key
def call_llm(
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        temprature: float = 0.2,
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:

        api_key = get_api_key()

        headers = {
             "Authorization": f"Bearer {api_key}",
             "Content-Type": "application/json",
        }

        payload = {
             "model": model,
             "messages": messages,
             "temprature": temprature,
        }

        resp = requests.post(TOGETHER_CHAT_URL, headers=headers, json=payload, timeout=60)

        resp.raise_for_status()

        data = resp.json()

        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls",[]) or []

        return content, tool_calls, data

def main() -> None:
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who is the current president of USA."},
    ]
    print("TEST find_doctors:", find_doctors("Orthopedics"))
    print("TEST get_availability:", get_availability("Dr X", "2025-12-23"))

    print("TEST book_appointment:", book_appointment(
    "Dr X", "2025-12-23", "10:00", {"name": "Bala", "phone": "9999999999"}
    ))
    print("TEST availability after booking:", get_availability("Dr X", "2025-12-23"))



    content, tool_calls, _raw = call_llm(messages=messages)
    print("Assistant: ", content)
    print("Tool calls: ", tool_calls)

if __name__ == "__main__":
    main()



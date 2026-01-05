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
        {"role": "system", "content": "You are a helpful assistant. If the question is beyond your cut off time then advice me for web search, I can do the web search and provide context to you."},
        {"role": "user", "content": "Who is the current president of USA."},
    ]
    
    content, tool_calls, _raw = call_llm(messages=messages)
    print("Assistant: ", content)
    print("Tool calls: ", tool_calls)
    print("Raw Response: ", _raw)

if __name__ == "__main__":
    main()



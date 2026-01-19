import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from clinic.tools import (
    find_doctors,
    get_availability,
    book_appointment,
    list_specialties,
    get_current_datetime,
    load_doctors,  # must exist in your CSV-backed tools.py
)

TOGETHER_CHAT_URL = "https://api.together.xyz/v1/chat/completions"
DEFAULT_MODEL = "Kimi/K2-Instruct-0905"



# -------------------------
# Prompt Loader
# -------------------------
def load_system_prompt() -> str:
    prompt_file = Path(__file__).parent / "prompts" / "system_prompt.txt"
    return prompt_file.read_text(encoding="utf-8").strip()


SYSTEM_PROMPT = load_system_prompt()


# -------------------------
# Tool Schemas (sent to LLM)
# -------------------------
TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "find_doctors",
            "description": "Find doctors by specialty/department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {"type": "string", "description": "Specialty name, e.g., Orthopedics"}
                },
                "required": ["specialty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_availability",
            "description": "Get available time slots for a doctor on a given date. doctor_name MUST be an exact doctor name returned by find_doctors().",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {
                        "type": "string",
                        "description": "Exact doctor name (e.g., 'Dr X'). Must come from find_doctors(). Do NOT use specialty names."
                    },
                    "date_iso": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["doctor_name", "date_iso"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment; removes the slot and stores patient details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string"},
                    "date_iso": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_24h": {"type": "string", "description": "HH:MM (24h)"},
                    "patient": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                        },
                        "required": ["name", "phone"],
                    },
                },
                "required": ["doctor_name", "date_iso", "time_24h", "patient"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_specialties",
            "description": "List all specialties available in Super Clinic.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get current date/time (ISO) and weekday for a timezone. Use this to resolve relative dates like today/tomorrow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone like Asia/Kolkata"}
                },
                "required": [],
            },
        },
    },
]


# -------------------------
# Together API
# -------------------------
def get_api_key() -> str:
    load_dotenv(dotenv_path=".env")
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise RuntimeError("TOGETHER_API_KEY not found. Check .env in project root.")
    return api_key


def call_llm(
    messages: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    api_key = get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    resp = requests.post(TOGETHER_CHAT_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    raw = resp.json()
    message = raw["choices"][0]["message"]
    return message, raw


# -------------------------
# Guards / Helpers
# -------------------------
def doctor_exists(name: str) -> bool:
    """
    Check whether doctor_name exists in doctors.csv.
    doctors.csv has columns: doctor_name,specialty
    """
    doctors = load_doctors()
    return any(d["doctor_name"].strip().lower() == name.strip().lower() for d in doctors)


def execute_tool(tool_name: str, arguments_json: str) -> Any:
    args = json.loads(arguments_json) if arguments_json else {}

    if tool_name == "find_doctors":
        return find_doctors(args.get("specialty", ""))

    if tool_name == "get_availability":
        return get_availability(args.get("doctor_name", ""), args.get("date_iso", ""))

    if tool_name == "book_appointment":
        return book_appointment(
            args.get("doctor_name", ""),
            args.get("date_iso", ""),
            args.get("time_24h", ""),
            args.get("patient", {}) or {},
        )

    if tool_name == "list_specialties":
        return list_specialties()

    if tool_name == "get_current_datetime":
        return get_current_datetime(args.get("timezone", "Asia/Kolkata"))

    return {"error": f"Unknown tool: {tool_name}"}


# -------------------------
# Orchestrator (one user turn)
# -------------------------
def run_turn(messages: List[Dict[str, Any]]) -> str:
    
    while True:
        #Exit this loop when assistant responded, means no tool calling..

        assistant_msg, _raw = call_llm(messages=messages, tools=TOOLS, tool_choice="auto")

        tool_calls = assistant_msg.get("tool_calls") or []
    

        # Add assistant response to session
        messages.append(assistant_msg)

        # No tool calls => final response for the user
        if not tool_calls:
            return assistant_msg.get("content", "") or ""

        # Execute tool calls
        for tc in tool_calls:
            fn = tc["function"]["name"]
            args_json = tc["function"]["arguments"]
            call_id = tc.get("id")

            # Guard: prevent "Dentist" being treated as a doctor_name
            if fn == "get_availability":
                args = json.loads(args_json)
                if not doctor_exists(args.get("doctor_name", "")):
                    return (
                        "Sorry, we do not have any doctors with that specialty at Super Clinic. "
                        "Is there anything else I can help you with?"
                    )

            result = execute_tool(fn, args_json)

            # Guard: specialty not available
            if fn == "find_doctors" and isinstance(result, list) and len(result) == 0:
                return (
                    "Sorry, we do not have any doctors with that specialty at Super Clinic. "
                    "Is there anything else I can help you with?"
                )

            # Send tool result back to model
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result),
                }
            )


# -------------------------
# Main Loop (single session)
# -------------------------
def main() -> None:
    specialties = list_specialties()

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Available specialties in Super Clinic (from DB): {', '.join(specialties)}"},
    ]

    print("Super Clinic: Hello and welcome! How can I help you? (type 'exit' to quit)")

    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            print("Assistant: Thank you for contacting Super Clinic. Have a good day!")
            break

        messages.append({"role": "user", "content": user_text})

        try:
            reply = run_turn(messages)
            print("Assistant:", reply)
        except requests.HTTPError as e:
            print("Assistant: Sorry, I’m having trouble reaching the scheduling system right now.")
            print("DEBUG:", str(e))
            break


if __name__ == "__main__":
    main()

"""A beginner-friendly Groq assistant with a manually implemented agent loop."""

import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import APIError, Groq

from tools import TOOLS


SYSTEM_MESSAGE = (
    "You are a helpful AI assistant. Give clear explanations and be friendly. "
    "Use calculate whenever arithmetic is required, and use get_current_time "
    "when asked for the current local time. For other questions, answer normally. "
    "After receiving tool results, decide whether another tool is needed before "
    "giving your final answer."
)

# Groq's Chat Completions function-tool schema describes each callable to the LLM.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a mathematical expression when arithmetic is required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A basic arithmetic expression, such as '18500 * 0.25'.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current local system date and time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def execute_tool_call(tool_call: Any) -> str:
    """Look up a requested tool, validate its JSON arguments, and run it safely."""
    tool_name = tool_call.function.name

    try:
        arguments = json.loads(tool_call.function.arguments)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")

        tool_function = TOOLS.get(tool_name)
        if tool_function is None:
            raise ValueError(f"The requested tool '{tool_name}' is not available.")

        # The explicit registry restricts executable code to our own functions.
        result = tool_function(**arguments)
        return str(result)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        return f"Error: {error}"


def run_agent(
    client: Groq,
    model: str,
    conversation_history: list[dict[str, Any]],
    user_message: str,
) -> str:
    """Repeat LLM/tool exchanges until Groq returns a final text response."""
    conversation_history.append({"role": "user", "content": user_message})
    iteration = 0

    while True:
        iteration += 1
        print(f"\n---\nAgent iteration: {iteration}")

        completion = client.chat.completions.create(
            model=model,
            messages=conversation_history,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        assistant_message = completion.choices[0].message

        if not assistant_message.tool_calls:
            final_answer = assistant_message.content or ""
            print("\nNo tool call.")
            print(f"\n## Final answer:\n{final_answer}")
            conversation_history.append(
                {"role": "assistant", "content": final_answer}
            )
            return final_answer

        # Preserve the assistant request before adding its matching tool results.
        conversation_history.append(
            assistant_message.model_dump(exclude_none=True)
        )

        # Run every call in this batch, then ask the model what to do next.
        for tool_call in assistant_message.tool_calls:
            print("\nAssistant requested tool:")
            print(tool_call.function.name)
            print("\nArguments:")
            print(tool_call.function.arguments)

            tool_result = execute_tool_call(tool_call)
            print("\n## Tool result:")
            print(tool_result)

            conversation_history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_result,
                }
            )


def main() -> None:
    """Load configuration and run the terminal chat session."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "").strip()

    if not api_key or api_key == "your_actual_api_key":
        print("Error: GROQ_API_KEY is missing. Add your Groq API key to the .env file.")
        return
    if not model or model == "your_model_name":
        print("Error: GROQ_MODEL is missing. Add a model ID to the .env file.")
        return

    try:
        client = Groq(api_key=api_key)
    except Exception:
        print("Error: Could not create the Groq client. Check your local setup.")
        return

    conversation_history: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_MESSAGE}
    ]
    print("AgentX Phase 3 is ready. Type 'exit', 'quit', or 'q' to finish.")

    while True:
        try:
            user_message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_message.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break
        if not user_message:
            print("Please enter a message (or type 'exit' to finish).")
            continue

        history_before_turn = len(conversation_history)
        try:
            run_agent(client, model, conversation_history, user_message)
        except APIError:
            del conversation_history[history_before_turn:]
            print(
                "Groq could not complete that request. Check your internet connection, "
                "API key, model name, and Groq account, then try again."
            )
        except Exception:
            del conversation_history[history_before_turn:]
            print("An unexpected error occurred while contacting Groq. Please try again.")


if __name__ == "__main__":
    main()
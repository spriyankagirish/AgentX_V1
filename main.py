"""A small command-line assistant using Groq's chat completions API."""

import json
import os

from dotenv import load_dotenv
from groq import APIError, Groq

from tools import calculate


SYSTEM_MESSAGE = (
    "You are a helpful AI assistant. Give clear explanations and be friendly. "
    "When a user asks for arithmetic, use the calculate tool instead of doing "
    "the arithmetic mentally. For questions that do not need arithmetic, answer "
    "normally without calling a tool. Explain calculation results clearly."
)

TOOLS = [
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
                        "description": "A basic arithmetic expression, for example '18500 * 0.25'.",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]

AVAILABLE_TOOLS = {"calculate": calculate}


def execute_tool_call(tool_call: object) -> str:
    """Validate and execute one model-requested tool, returning text for Groq."""
    function = tool_call.function
    tool_name = function.name

    try:
        arguments = json.loads(function.arguments)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")

        tool_function = AVAILABLE_TOOLS.get(tool_name)
        if tool_function is None:
            raise ValueError(f"The requested tool '{tool_name}' is not available.")
        if set(arguments) != {"expression"} or not isinstance(
            arguments["expression"], str
        ):
            raise ValueError("calculate requires one string argument named 'expression'.")

        result = tool_function(arguments["expression"])
        return str(result)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        return f"Error: {error}"


def main() -> None:
    """Load configuration, then run the assistant conversation loop."""
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

    # This list is the complete conversation context for this running process.
    conversation_history: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_MESSAGE}
    ]
    print("AgentX is ready. Type 'exit', 'quit', or 'q' to finish.")

    while True:
        try:
            user_message = input("You: ").strip()
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
        conversation_history.append({"role": "user", "content": user_message})
        try:
            # First request: let Groq answer directly or choose from the tools.
            completion = client.chat.completions.create(
                model=model,
                messages=conversation_history,
                tools=TOOLS,
                tool_choice="auto",
            )
            response_message = completion.choices[0].message

            if response_message.tool_calls:
                # Preserve Groq's assistant tool-call message in the history.
                conversation_history.append(
                    response_message.model_dump(exclude_none=True)
                )

                # Groq can request several independent calls in one response.
                for tool_call in response_message.tool_calls:
                    print(f"\nTool requested: {tool_call.function.name}")
                    print(f"Arguments: {tool_call.function.arguments}")
                    tool_result = execute_tool_call(tool_call)
                    print(f"Tool result: {tool_result}\n")

                    # The call ID pairs this result with the correct request.
                    conversation_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": tool_result,
                        }
                    )

                # Second request: the model uses the result to write its reply.
                # Tools are deliberately omitted here to keep this a single
                # tool-call round, not an autonomous agent loop.
                completion = client.chat.completions.create(
                    model=model,
                    messages=conversation_history,
                )
                assistant_message = completion.choices[0].message.content or ""
            else:
                assistant_message = response_message.content or ""
        except APIError:
            # Discard only this incomplete turn; keep earlier conversation intact.
            del conversation_history[history_before_turn:]
            print(
                "Groq could not complete that request. Check your internet connection, "
                "API key, model name, and Groq account, then try again."
            )
            continue
        except Exception:
            del conversation_history[history_before_turn:]
            print("An unexpected error occurred while contacting Groq. Please try again.")
            continue

        print(f"Assistant: {assistant_message}\n")
        conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )


if __name__ == "__main__":
    main()
"""A small command-line assistant using Groq's chat completions API."""

import os

from dotenv import load_dotenv
from groq import APIError, Groq


SYSTEM_MESSAGE = (
    "You are a helpful AI assistant. Give clear explanations and be friendly."
)


def get_assistant_response(
    client: Groq, model: str, conversation_history: list[dict[str, str]]
) -> str:
    """Send the current conversation to Groq and return the assistant's reply."""
    completion = client.chat.completions.create(
        model=model,
        messages=conversation_history,
    )
    return completion.choices[0].message.content or ""


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

        conversation_history.append({"role": "user", "content": user_message})
        try:
            assistant_message = get_assistant_response(
                client, model, conversation_history
            )
        except APIError:
            # Remove the unanswered turn so later requests use a valid history.
            conversation_history.pop()
            print(
                "Groq could not complete that request. Check your internet connection, "
                "API key, model name, and Groq account, then try again."
            )
            continue
        except Exception:
            conversation_history.pop()
            print("An unexpected error occurred while contacting Groq. Please try again.")
            continue

        print(f"Assistant: {assistant_message}\n")
        conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )


if __name__ == "__main__":
    main()
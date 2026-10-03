# AgentX_V1 — Phase 1

AgentX_V1 is a beginner-friendly command-line AI assistant. Phase 1 uses plain
Python and the Groq API to send messages to a large language model (LLM), show
its replies, and keep the current conversation in memory until the program ends.

## What is an LLM application?

A large language model (LLM) is a model trained to understand and generate text.
An LLM application is a program that sends the model instructions and messages,
receives generated text, and presents it to a user. In this phase, Groq hosts the
model and AgentX is the small client program.

## How the application works

1. `python-dotenv` reads settings from the local `.env` file.
2. AgentX checks for `GROQ_API_KEY` and `GROQ_MODEL` and creates a Groq client.
3. The conversation starts with a system message describing the assistant.
4. Each non-empty terminal input is added as a user message.
5. AgentX sends the full conversation history to Groq's chat-completions API.
6. AgentX prints the returned assistant message and adds it to the history.
7. The loop repeats until you type `exit`, `quit`, or `q`.

The history exists only in the Python process. It is not saved to a file or
database, and it is lost when the program exits.

## Architecture

```text
Terminal input
      ↓
main.py adds a user message to conversation_history
      ↓
Groq Python client sends the messages and model ID to Groq
      ↓
Groq returns an assistant message
      ↓
main.py displays and saves that reply in conversation_history
```

There is no agent framework or persistent memory in this phase. The main logic
is visible in `main.py`.

## Prerequisites

- Python 3.9 or newer
- A Groq account and an API key created through the Groq Console
- Internet access while using the assistant

Groq offers Developer-plan API access with usage limits; availability, limits,
and pricing can change and may depend on your account. The current Groq model
catalog lists `openai/gpt-oss-120b` as a featured production model, so it is the
suggested starting value. If your account cannot use it, select an available
chat model from the [current Groq model catalog](https://console.groq.com/docs/models)
and set its ID as `GROQ_MODEL` in `.env`.

## Installation

Open a terminal in the project folder and create a virtual environment:

```powershell
py -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, do not change its execution policy for this
project; install and run using the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Environment variables

The `.env` file is read locally by `python-dotenv`. Edit it and replace the
placeholder with your own API key created in the Groq Console:

```text
GROQ_API_KEY=your_actual_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Keep the key private. Never paste it into source code, README files, screenshots,
or chat messages. `.env` is listed in `.gitignore` so Git will not track it.
The `.env.example` file contains safe setup hints and must not contain a real
key. This project does not contain or supply an API key.

## How to run it

From the project folder, with the virtual environment activated:

```powershell
python main.py
```

Then type a message. Enter `exit`, `quit`, or `q` to leave. Empty messages are
ignored. API request errors produce a friendly message and let you try again.

## Example conversation

```text
AgentX is ready. Type 'exit', 'quit', or 'q' to finish.
You: My name is Priyanka.
Assistant: Nice to meet you, Priyanka!

You: What is my name?
Assistant: Your name is Priyanka.

You: q
Goodbye!
```

The exact wording will vary. The assistant can refer to the name in the second
turn because both turns are sent as conversation history.

## Project structure

```text
AgentX_V1/
├── main.py           # Command-line application and conversation loop
├── requirements.txt  # Python package dependencies
├── .env              # Local settings and API key; do not commit
├── .env.example      # Safe example settings
├── .gitignore        # Excludes secrets and generated files from Git
└── README.md         # Setup and learning notes
```

## What I learned in Phase 1

- How an application uses an API client to call a hosted LLM.
- Why the API key is a secret and belongs in local environment configuration.
- How system, user, and assistant messages describe a chat conversation.
- Why prior messages are sent to provide short-term context.
- How to build a simple input/request/response loop in Python.
- That in-memory conversation history is temporary, not persistent memory.

## Phase 2 (planned, not implemented)

A suitable next learning step is a small, explicitly written Python function
tool: let the model request one simple operation, have Python execute it, and
send the result back to the model. This introduces tool calling without an agent
framework. Phase 2 will only begin after you confirm that Phase 1 works.
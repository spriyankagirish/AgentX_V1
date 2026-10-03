# AgentX_V1 — Phase 3: Basic AI Agent Loop

AgentX_V1 is a beginner-friendly command-line AI assistant built with plain
Python and the Groq API. Phase 1 introduced chat completions and temporary
conversation history. Phase 2 added manual calculator tool calling. Phase 3
adds a visible Python agent loop and a second local-time tool. No agent framework
is used.

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

## Phase 1 architecture

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

## Phase 2: calculator tool calling

### What tool calling is

Tool calling lets an LLM ask the application to run a function. It is different
from normal text generation: rather than answering the arithmetic question from
generated text alone, Groq can return a structured request naming `calculate`
and supplying an expression. The model does not execute Python. `main.py`
validates the request, calls the local Python function in `tools.py`, then sends
the result back to Groq so the model can write a final user-facing response.

### Phase 2 architecture

```text
User message
            ↓
main.py sends conversation history + calculator tool schema to Groq
            ↓
Groq returns normal text OR an assistant message with one or more tool_calls
            ↓
main.py reads each tool name and JSON arguments
            ↓
Python dispatches calculate(expression) from tools.py
            ↓
main.py adds one role="tool" result per call, matched by tool_call_id
            ↓
main.py sends the updated history back to Groq (without offering more tools)
            ↓
Groq writes its final response; main.py displays and saves it
```

For this learning phase, the application handles one batch of tool calls and
one follow-up response. It does not repeat automatically as an autonomous agent
loop. Ordinary questions, such as asking for a capital city, can be answered
without calling the calculator.

### The tool definition (schema)

The `TOOLS` value in `main.py` follows Groq's current Chat Completions function
tool format. Its JSON Schema tells the model the function name, its purpose, and
that it requires one string parameter called `expression`. This describes the
tool; it does not run it.

```json
{
      "type": "function",
      "function": {
            "name": "calculate",
            "description": "Calculate a mathematical expression when arithmetic is required.",
            "parameters": {
                  "type": "object",
                  "properties": {
                        "expression": { "type": "string" }
                  },
                  "required": ["expression"]
            }
      }
}
```

The first request uses `tool_choice="auto"`: Groq may answer normally or choose
one or more of the tools supplied. The app keeps the tool list explicit in
`AVAILABLE_TOOLS`, so a model response cannot select and execute arbitrary
Python functions.

### What Groq returns for a tool request

When the model selects the calculator, the assistant response has a
`tool_calls` array. Each entry includes a unique `id`, a function `name`, and an
`arguments` JSON string, for example:

```json
{
      "id": "call_example",
      "type": "function",
      "function": {
            "name": "calculate",
            "arguments": "{\"expression\": \"18500 * 0.25\"}"
      }
}
```

`main.py` parses the argument JSON, checks the function name and parameter, and
dispatches only to the matching Python function. `tools.py` parses the
expression with Python's AST parser and evaluates only numeric constants,
parentheses, unary plus/minus, and the allowlisted arithmetic operators. It
rejects function calls, names, imports, file or shell access, invalid math,
excessively long expressions, and excessively large values. It does not use
`eval()`.

### How the tool result gets back to the model

After Python returns a result, `main.py` adds a message with `role="tool"`, the
same `tool_call_id` as the request, the tool name, and the result as text. That
ID lets Groq match the result to the right requested call. The assistant's
tool-call message is also retained in history. AgentX then makes a follow-up
Chat Completions request with that updated conversation. The model needs the
result in the conversation because Python's calculation is separate from the
LLM; without receiving the tool message, it would not know the value that the
function produced. In this phase, tools are not offered on this follow-up, so
the model returns the final answer rather than starting another round.

### Example tool round trip

User request:

```text
What is 25% of 18,500?
```

Example model tool call (the model may format the equivalent expression
differently):

```text
Tool requested: calculate
Arguments: {"expression": "18500 * 0.25"}
```

Python executes the safe calculator and reports:

```text
Tool result: 4625
```

The result is sent back to Groq as a tool message. Groq can then answer, for
example:

```text
Assistant: 25% of 18,500 is 4,625.
```

Exact tool arguments and assistant wording can vary by model response. The
calculator returns whole-number results such as `4625` as integers and
non-whole results as decimals.

## Phase 3: basic AI agent loop

### What is an AI agent?

For this learning project, an AI agent is an application that asks an LLM what
step to take, executes a tool requested by the LLM, returns the result, and lets
the LLM decide what to do next. A basic chatbot often makes one LLM request and
shows one response. This agent can make multiple LLM/tool exchanges during a
single user turn before giving the final answer. The model requests tools; the
Python application executes them.

### Architecture

```text
User
  ↓
LLM (conversation history + tool definitions)
  ↓
Tool call?
├── NO → Final Answer
│
└── YES
            ↓
      Python Tool
            ↓
      Tool Result
            ↓
      LLM
            ↓
      Tool call?
            ↓
      repeat until there are no tool calls
```

### What happens during an iteration?

1. `run_agent()` sends the complete conversation history and both tool
      definitions to Groq using Chat Completions and `tool_choice="auto"`.
2. The model may return a normal assistant response, or an assistant message
      with one or more `tool_calls`.
3. For tool calls, the application stores the assistant tool-call message,
      parses each call's JSON arguments, and looks up its name in the explicit
      `TOOLS` registry in `tools.py`.
4. Python calls that registered function and adds a `role="tool"` message with
      the result and the matching `tool_call_id` to conversation history.
5. The `while` loop sends the updated history to Groq again. The model receives
      the result and chooses whether it needs another tool or can answer now.
6. If a response has no tool calls, the application displays and saves its
      content as the final answer. That no-tool response is the stop condition.

One response may request both calculator and clock calls. AgentX executes every
call in the batch before asking Groq again. It can also process additional tool
calls in later iterations. The loop is intentionally explicit and has no
framework or hidden orchestration.

### The two local tools

- `calculate(expression)` uses the safe AST arithmetic allowlist from Phase 2.
  It does not use unrestricted `eval()` and rejects arbitrary Python, imports,
  file access, shell commands, invalid math, and excessively large expressions.
- `get_current_time()` returns the local system date/time and UTC offset.

The tool definitions describe these functions to the model, but do not execute
them. `execute_tool_call()` uses only the Python functions in the explicit
registry; the model cannot request a dynamic import or arbitrary code execution.
Tool results are sent back because the model cannot see Python's return values
unless the application includes them in the next LLM request.

### Phase 2 vs Phase 3

**Phase 2:** one LLM request → tool call(s) → Python execution → tool result(s)
→ one follow-up LLM response. The response after tools was not checked for
another tool request.

**Phase 3:** the same exchange is inside a `while` loop. Groq can request tools
over multiple iterations, and the application continues until Groq returns a
response without tool calls.

### Test prompts

Run the app and try these one at a time. Exact wording and tool grouping can
vary by model.

1. `What is 25% of 18,500?` — expect `calculate` and result `4625`.
2. `What time is it?` — expect `get_current_time` and an answer using its result.
3. `Calculate 12345 * 678.` — expect `calculate` and result `8369910`.
4. `What is 15% of 800 plus 200?` — expect `calculate`; `(15% of 800) + 200`
      is `320`.
5. `What is the capital of France?` — expect a direct answer without a tool.
6. `Use the calculator to find 25% of 18,500, and also tell me the current
      local time.` — may use both tools in one batch or successive iterations.

If arithmetic is answered directly, try explicitly asking the model to use the
calculator and verify that the configured model supports tool calling.

### Manual test prompts

Run `python main.py` and try these prompts one at a time. Expected values are
shown as a guide; the model's wording and exact tool expression may differ.

1. `What is 25% of 18,500?` — should call `calculate` and get `4625`.
2. `Calculate 12345 * 678.` — should call `calculate` and get `8369910`.
3. `What is the capital of France?` — should answer normally, without a
      calculator call.
4. `What is 15% of 800 plus 200?` — should call `calculate`; interpreting it
      as `(15% of 800) + 200` gives `320`.

The model chooses whether to call the tool based on the request and tool
description. If a model unexpectedly skips or misuses it, try explicitly saying
“use the calculator” or check the configured model's tool-calling support.

## Prerequisites

- Python 3.10 or newer
- A Groq account and an API key created through the Groq Console
- Internet access while using the assistant

Groq offers Developer-plan API access with usage limits; availability, limits,
and pricing can change and may depend on your account. The current Groq model
catalog lists `openai/gpt-oss-120b` as a featured production model, so it is the
suggested starting value. If your account cannot use it, select an available
chat model from the [current Groq model catalog](https://console.groq.com/docs/models)
and set its ID as `GROQ_MODEL` in `.env`.

## Installation

From the project root, reuse the existing `.venv` if you already created one.
Only create it if it is missing:

```powershell
if (!(Test-Path ".venv")) { py -m venv .venv }
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
├── main.py           # CLI, Groq tool schemas, dispatcher, and agent loop
├── tools.py          # Safe calculator, local clock, and explicit tool registry
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

## What I learned in Phase 2

- A tool schema describes a function to the model; it does not execute it.
- Groq returns structured tool calls with a function name, JSON arguments, and
      a unique call ID.
- Application code decides which local Python function to dispatch.
- A `role="tool"` message returns the result matched to the call ID.
- The result must be sent back to the LLM so it can produce a grounded final
      response.
- This explicit LLM → tool call → Python execution → tool result → LLM pattern
      is the building block used by Phase 3's agent loop.

## What I learned in Phase 3

- An agent uses an LLM decision to select an action, while Python runs the
      selected registered function.
- The `while` loop allows the model to request another tool after seeing an
      earlier tool result.
- Conversation history connects user requests, assistant tool-call messages,
      tool results, and final answers across iterations.
- The application stops when the assistant response has no tool calls.
- Frameworks such as LangGraph can later help structure larger workflows,
      branching, retries, persistence, and observability; this phase keeps the loop
      visible in ordinary Python.
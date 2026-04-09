# AI Agent CLI 🤖

A powerful, extensible, and modular Command-Line Interface (CLI) AI agent framework built with Python. This agent features real-time streaming, voice recognition, persistent memory, and a custom tool registry.

## 🌟 Features

- **🎙️ Voice Commands**: Interact with the agent using your microphone via the `/voice` command (powered by Vosk).
- **🛠️ Tool Registry**: Extensible tool system allowing the agent to perform real-world tasks (e.g., file operations, time checks).
- **🎨 Rich Terminal UI**: Beautiful, interactive terminal interface with markdown support, progress indicators, and status updates using the `rich` library.
- **⚡ Dual Modes**:
  - **Chat Mode**: Conversational AI for general assistance.
  - **Run Mode**: Technical mode for generating raw executable code.
- **📝 Streaming Responses**: Real-time token streaming for a responsive feel.
- **💾 Session Management**: Save conversation history, clear context, and persist memory.
- **🤖 LLM Integration**: Built to work with local models via Ollama (default: `deepseek-coder`).

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Ollama**: Install from [ollama.ai](https://ollama.ai) and pull your preferred model:
  ```bash
  ollama pull deepseek-coder
  ```
- **Vosk Model**: (Optional, for voice) Download a Vosk model (e.g., `vosk-model-small-en-us-0.15`) and place it in the project root.

### Quick Start (Windows)

If you are on Windows, you can use the automated launcher to set up the environment and start the agent:

```batch
run_agent.bat chat
```
This script will:
1. Create a virtual environment (`myenv`) if it doesn't exist.
2. Install all required dependencies from `requirements.txt`.
3. Launch the AI Agent in chat mode.

### Manual Installation

4. **Configure environment variables**:
   Create a `.env` file in the root directory:
   ```env
   LLM_MODEL=deepseek-coder
   HISTORY_FILE_NAME=history.json
   DEFAULT_SYSTEM_PROMPT="You are a helpful AI assistant."
   ```

## 🎮 Usage

Launch the interactive CLI:

```bash
python cli.py chat
```

### Slash Commands

While in the chat, use these commands to control the session:

- `/chat` - Switch to **Chat Mode** (Conversational).
- `/run` - Switch to **Run Mode** (Code focusing).
- `/voice` - Activate **Voice Input** (Speak to the agent).
- `/save` - Save the current conversation to a JSON file.
- `/clear` - Clear the current conversation history.
- `/exit` - Exit the CLI.

### Run a Single Task

You can also run the agent for a single command without entering the interactive loop:

```bash
python cli.py run "Create a python script that calculates Fibonacci numbers"
```

## 📂 Project Structure

```text
├── agents/             # Agent logic and prompt management
├── CLI/                # CLI command definitions and terminal UI
├── memory/             # Handlers for conversation history/persistence
├── tools/              # Custom tools (File, Time, Voice, etc.)
├── cli.py              # Main CLI entry point
├── config.py           # Configuration loader
└── main.py             # Simple entry point script
```

## 🛠️ Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This is a open-source project. Feel free to contribute to this project.

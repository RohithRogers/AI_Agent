# 🪐 Synthic – Advanced AI Agent CLI & GUI

Synthic is a next-generation AI agent framework designed for seamless developer productivity. It combines a high-performance **Rich CLI** and a **Premium GUI** with a powerful tool registry, persistent terminal sessions, and a modular skill system.

Powered by **Gemini 3.5**, **Groq**, and **Local LLMs**, Synthic adapts to your workflow, whether you're coding, researching, or managing infrastructure.

---

## ✨ Key Capabilities

- **🧠 Advanced Reasoning**: Built-in `<thought>` tagging for exposed chain-of-thought planning.
- **🖥️ Persistent Terminal**: Access to a real, persistent PowerShell session that remembers state (dir, venv, git status) across interactions.
- **🧩 Skill System**: Modular knowledge base. Synthic can "learn" how to use specific libraries or APIs by reading skill files (e.g., `git_skill.md`, `pdf_skill.md`).
- **🎙️ Voice Interaction**: Hands-free operation with Vosk-powered voice-to-text commands.
- **🖼️ Multimodal Power**: Generate high-fidelity images with Gemini Flash Image and videos with Veo 3.1.
- **🔀 Auto-Routing**: Dynamically switches between models (Lite/Pro/Image/Video) based on task complexity to optimize cost and performance.
- **💾 Smart Context**: A custom `ContextManager` handles history pruning, token budget enforcement, and automatic summarization.
- **🛠️ Tool Registry**: Out-of-the-box support for Browser, Git, Python REPL, Document parsing (PDF/DOCX), Terminal command execution, and more.

---

## 🎨 Dual Interfaces

### 1. Terminal CLI (`rich` powered)
A sleek, interactive CLI featuring live markdown streaming, terminal-style execution boxes, and status indicators.
- **Command**: `python cli.py chat`
- **Single Task**: `python cli.py run "Deploy the app to Vercel"`

### 2. Premium Desktop GUI (`flet` powered) - **Under Development** 
A modern, dark-themed dashboard with message bubbles, collapsible terminal views, and real-time thought transparency.
- **Command**: `python GUI/app.py`

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **API Keys**: Required for "Online" mode.
  - `GOOGLE_API_KEY` (Gemini)
  - `GROQ_API_KEY` (Groq/Llama)
- **Local Models**: Install [Ollama](https://ollama.ai) for "Offline" mode.

### Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/RohithRogers/AI_Agent.git
   cd llm_agent_cli
   ```

2. **Setup Environment**:
   ```bash
   python -m venv myenv
   source myenv/bin/activate  # Windows: .\myenv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Settings**:
   Get your API_KEYS from gemini and groq and set them as environment variables as follow: 
   ```env
   GEMINI_API_KEY = your_api_key
   GROQ_API_KEY = your_api_key
   ```
   And create a .env file with the following format:
   ```env   
   # Defaults
   LLM_MODEL=deepseek-coder
   HISTORY_FILE_NAME=history.json
   ```

---

## 🎮 Usage Guide

### CLI Sub-commands
| Command | Description |
|:---|:---|
| `chat [--mode online/offline]` | Start an interactive conversation with Synthic. |
| `run <task>` | Execute a specific task and exit. |
| `workspace --list` | View active sessions and persistent workspace stats. |

### In-Chat Slash Commands
- `/voice` - Toggle microphone input.
- `/save` - Export current session to JSON.
- `/clear` - Reset context and start a fresh session.
- `/mode <online/offline>` - Switch model backend on the fly.
- `/skills` - List all available skills Synthic can use.

---

## 📂 Project Architecture

```text
├── agents/             # Core brains (Synthic, Context Management, Routing)
├── CLI/                # Terminal UI logic and layout
├── GUI/                # Flet-based desktop application logic
├── skills/             # Markdown-based "manuals" for specialized tasks
├── tools/              # Extensible tool wrappers (Git, Browser, Terminal)
├── memory/             # History persistence and JSON handlers
├── config.py           # Global settings and environment loading
└── cli.py              # Main unifying entry point
```

---

## 🛠️ Extensibility
Synthic is designed to be modified.
- **Add a Tool**: Create a new file in `tools/` and register it in `tools/registry.py`.
- **Add a Skill**: Drop a `.md` file into `skills/`. Synthic automatically indexes it.
- **Custom Theme**: Modify `CLI/theme.py` or `GUI/theme.py`.

---

## 📄 License
Open-source under the MIT License. Contributions are welcome to make Synthic even smarter!


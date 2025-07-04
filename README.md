# MCP Streamable HTTP Servers & Client

This project demonstrates how to build and interact with **Model Context Protocol (MCP)** streamable HTTP servers in Python. It includes stateless servers, and soon-to-be-released stateful server and client implementations.

---

## 1️⃣ Stateless Streamable Servers

Located in: `streamable_http_server/1-stateless-streamable/`

These are **stateless**, **streamable** HTTP servers built using the [Model Context Protocol (MCP)](https://github.com/google-deepmind/mcp). Stateless means no memory or session is retained across tool calls.

### Contents

* `server1.py`: Provides `add_numbers` and `subtract_numbers` tools.
* `server2.py`: Provides `multiply_numbers` and `divide_numbers` tools.
* `main.py`: Launchpad script to run either `server1` or `server2` from CLI.

### 🚀 Getting Started

1. **Create a virtual environment from the root directory**

   ```bash
   # macOS / Linux
   uv venv
   source ./.venv/bin/activate

   # Windows (Command Prompt)
   uv venv
   .venv\Scripts\activate.bat

   # Windows (PowerShell)
   uv venv
   .venv\Scripts\Activate.ps1
   ```

2. **Install requirements with `uv`**

   ```bash
   uv sync --all-groups
   ```

3. **Run a Server**

   * **Run `server1` (Add + Subtract):**

     ```bash
     uv run --active streamable_http_server/1-stateless-streamable/main.py --server server1 --log-level INFO
     ```
   * **Run `server2` (Multiply + Divide):**

     ```bash
     uv run --active streamable_http_server/1-stateless-streamable/main.py --server server2 --log-level INFO
     ```

---

## 2️⃣ Stateful Streamable Server (Coming Soon)

This will demonstrate a **stateful**, **streamable** HTTP server using MCP. It will maintain state across multiple tool invocations and enable resumable event streams.

---

## 📡 MCP Streamable HTTP Client (Coming Soon)

This will be a Gemini-based ADK agent that dynamically connects to MCP servers and invokes tools.

### 🔧 Claude Desktop Integration

If you want to integrate these MCP servers with Claude Desktop, use the following config:

```json
{
  "mcpServers": {
    "server1": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:3000/mcp"
      ]
    },
    "server2": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:3001/mcp"
      ]
    }
  }
}
```

Save this as `claude_desktop_config.json` and install the servers using `mcp install`.

---

## 📜 License

This repository and the code within are licensed under the **GNU General Public License v3.0**. See the `LICENSE` file for full details.

Built with ❤️ by [The AI Language](https://theailanguage.com) to teach and demonstrate how to create streamable MCP servers and agents in Python using FastMCP, Pydantic, and ADK.

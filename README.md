# MCP Streamable HTTP Servers & Client

This project demonstrates how to build and interact with **Model Context Protocol (MCP)** streamable HTTP servers and clients in Python. It includes stateless servers, a Google OAuth–protected server, and a Gemini-powered ADK client capable of interacting with MCP toolsets.

---

## 1️⃣ Stateless Streamable Servers

**Location:** `streamable_http_server/1-stateless-streamable/`

These are **stateless**, **streamable** HTTP servers built using the Model Context Protocol (MCP). Stateless means no memory or session is retained across tool calls.

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

   # Windows (PowerShell)
   uv venv
   .venv\scripts\activate
   ```

2. **Install requirements with `uv`**

   ```bash
   uv sync --all-groups
   ```

3. **Run a Server**

   * **Run `server1` (Add + Subtract):**

     ```bash
     uv run --active streamable_http_server/1-stateless-streamable/main.py --server server1
     ```

   * **Run `server2` (Multiply + Divide):**

     ```bash
     uv run --active streamable_http_server/1-stateless-streamable/main.py --server server2
     ```

---

## 2️⃣ Google OAuth–Protected Server

**Location:** `streamable_http_server/2-google-oauth-simple-server/`

This server demonstrates the **OAuth Proxy pattern** with **Google as the upstream provider**. It protects an MCP server behind Google OAuth 2.0, allowing MCP clients to authenticate dynamically using **DCR (Dynamic Client Registration)**, **PKCE**, and **loopback redirect URIs**.

* `server.py`: MCP Resource Server acting as an OAuth Proxy to Google.
* `README.md`: Detailed explanation of setup, environment variables, and flow.

---

## 3️⃣ MCP Streamable HTTP Client

**Location:** `streamable_http_client/`

This is an educational project that demonstrates how to connect to a **Model Context Protocol (MCP)** streamable HTTP server, discover tools from the server, and interact with those tools using a **Google ADK agent** powered by **Google Gemini**.

### ⚙️ Setup Instructions

1. **Create a virtual environment**

   ```bash
   # macOS / Linux
   uv venv
   source ./.venv/bin/activate

   # Windows (PowerShell)
   uv venv
   .venv\scripts\activate
   ```

2. **Install dependencies**

   ```bash
   uv sync --all-groups
   ```

3. **Set environment variables**

   Create a `.env` file inside `streamable_http_client`:

   ```env
   GOOGLE_API_KEY=your-google-api-key
   ```

4. **Configure MCP Servers**

   Edit the `streamable_http_client/theailanguage_config.json` file:

   ```json
   {
     "mcpServers": {
       "server1": {
         "type": "http",
         "url": "http://localhost:3000/mcp"
       },
       "server2": {
         "type": "http",
         "url": "http://localhost:3001/mcp"
       },
       "terminal": {
         "type": "stdio",
         "command": "/Users/theailanguage/.local/bin/uv",
         "args": [
             "--directory", "/Users/theailanguage/mcp/mcp_stremable_http/stdio_server/1-terminal-server",
             "run",
             "terminal_server.py"
         ]
       }
     }
   }
   ```

5. **Run the Client**

   ```bash
   uv run universal_client/1-google-adk-gemini-mcp-client/cmd.py
   ```

   This launches an interactive command-line chat loop, connects to MCP servers via HTTP or STDIO, and interacts with the Gemini-powered ADK agent using tools discovered from each server.

---

## 4️⃣ Google OAuth–Protected Client

**Location:** `universal_client/3-google-oauth-simple-client/`

This client demonstrates how to authenticate against the **Google OAuth–protected MCP server** using the OAuth Proxy pattern. It:

* Handles loopback redirect URIs.
* Supports DCR + PKCE automatically.
* Interacts with the protected tools (`get_time`, `get_user_info`).

Run with:

```bash
source .venv/bin/activate
uv run ./universal_client/3-google-oauth-simple-client/client.py
```

---

## 5️⃣ Coming Soon

### 🧠 Stateful Streamable Server

A **stateful**, **streamable** HTTP server using MCP that maintains state across tool invocations and enables resumable event streams.

---

## 🔧 Claude Desktop Integration

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

Save this as `claude_desktop_config.json`.
**Warning! - This uses a third party package called `mcp-remote` that is not an official Anthropic or Claude package**

---

## 📜 License

This repository and the code within are licensed under the **GNU General Public License v3.0**. See the `LICENSE` file for full details.

Built with ❤️ by [The AI Language](https://theailanguage.com) to teach and demonstrate how to create streamable MCP servers and agents in Python using FastMCP, Pydantic, and ADK.

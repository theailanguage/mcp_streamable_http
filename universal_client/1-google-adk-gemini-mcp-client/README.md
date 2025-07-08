# 📱 MCP Streamable HTTP Client

This is an educational project that demonstrates how to connect to a **Model Context Protocol (MCP)** streamable HTTP server, discover tools from the server, and interact with those tools using a **Google ADK agent** powered by **Google Gemini**.

---

## ⚙️ Installation and Setup (Using `uv`)

### 1. Create a virtual environment from the root directory

```bash
uv venv
source ./.venv/bin/activate
```

### 2. Sync and install all dependencies from the root directory

```bash
uv sync --all-groups
```

### 3. Set required environment variables

Create a `.env` file in the `streamable_http_client` directory:

```env
GOOGLE_API_KEY=your-google-api-key
```

---

## 🔗 Configuring MCP Servers

Edit the `streamable_http_client/theailanguage_config.json` file:

```json
{
  "mcpServers": {
    "server1": {
      "url": "http://localhost:3000/mcp"
    },
    "server2": {
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

---

## 🚀 Running the Client

Run the interactive chat application from the root directory using `uv`:

```bash
uv run streamable_http_client/app.py
```

> ℹ️ This will launch the main CLI loop defined in `app.py`, which uses `client.py` to communicate with the ADK agent defined in `agent.py`. Configuration reading and utility methods are handled in `utilities.py`.

# 1-stateless-streamable

This project demonstrates how to build **stateless**, **streamable** HTTP servers using the [Model Context Protocol (MCP)](https://github.com/google-deepmind/mcp) in Python.

It includes two separate server implementations (`server1.py` and `server2.py`) and a command-line interface (`main.py`) to run either one easily.

---

## 🚀 Getting Started

### 1. Create a virtual environment from the root directory

```bash
uv venv
source ./.venv/bin/activate
```

### 2. Install requirements with `uv` from the root directory

```bash
uv sync --all-groups
```

### 3. Run a Server from the root directory

*   **Run `server1` (add + subtract)**
    ```bash
    uv run --active streamable_http_server/1-stateless-streamable/main.py --server server1 --log-level INFO
    ```
*   **Run `server2` (multiply + divide)**
    ```bash
    uv run --active streamable_http_server/1-stateless-streamable/main.py --server server2 --log-level INFO
    ```
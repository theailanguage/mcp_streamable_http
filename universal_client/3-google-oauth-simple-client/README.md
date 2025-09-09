# MCP OAuth Client (Google Proxy Demo)

This folder contains a **minimal MCP client** that authenticates to a protected MCP Resource Server (RS) using the **OAuth Proxy pattern** with **Google as the upstream provider**.

The goal is to demonstrate how a client can:

* Discover a protected MCP server.
* Perform OAuth 2.1 authorization via PKCE + loopback redirect.
* Exchange codes/tokens through the RS proxy.
* Call protected tools (e.g. `get_user_info`, `get_time`).

---

## 📖 Background

Traditional OAuth providers (Google, GitHub, Azure, etc.) do not support **Dynamic Client Registration (DCR)**.
MCP clients, however, are designed to register dynamically with each RS.

The **FastMCP OAuth Proxy** bridges this gap:

* The RS presents a DCR-compliant Authorization Server to MCP clients.
* Behind the scenes, it uses its pre-registered Google client credentials.
* The RS stores each client’s temporary callback URI and PKCE challenge, then forwards the OAuth exchange to Google and back again.
* This allows *any MCP client* (desktop, local, browser-based) to authenticate securely without you manually registering each one in Google.

---

## 🛠️ Requirements

* Python **3.11+**
* A running MCP Resource Server configured with `GoogleProvider`
  (see `server.py` in the parent folder).
* Google Cloud Console OAuth App:

  * Redirect URI set to your RS proxy callback
    e.g. `http://localhost:8005/auth/callback`
  * Client ID and secret stored in `.env` on the RS.

---

## 🚀 Running the Client

1. **Create and activate a virtual environment**:

   ```bash
   uv venv
   source .venv/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   uv sync --all-groups
   ```

3. **Run the client**:

   ```bash
   uv run ./universal_client/3-google-oauth-simple-client/client.py
   ```

   On first run:

   * Your browser will open to Google login.
   * After consenting, the RS proxy exchanges tokens with Google.
   * The client receives a valid Bearer token via the RS proxy.

---

## 📋 What Happens

1. The client calls `/mcp` → RS responds `401 Unauthorized` with a pointer to its metadata.
2. The client discovers the RS’s OAuth Proxy endpoints (`/.well-known/...`).
3. The client **registers** dynamically with the RS, including its loopback redirect URI.
4. The RS **returns fixed Google credentials** (proxying your pre-registered app).
5. The client opens `/authorize` → browser → Google login.
6. Google redirects to RS callback (`/auth/callback`) → RS exchanges code for tokens.
7. RS forwards a new code to the client’s loopback redirect (localhost\:random).
8. The client exchanges that code with RS `/token` → RS returns stored Google tokens.
9. Now authenticated, the client can call tools:

   * `get_user_info` → returns your Google account email/profile.
   * `get_time` → returns current UTC time from the RS.

---

## 🧑‍💻 Example Output

```text
✓ Authenticated with Google!
Tools: ['get_user_info', 'get_time']
User info: {'google_id': '123...', 'email': 'me@gmail.com', 'name': 'Alice'}
Google user: me@gmail.com
Name: Alice
Time: {'current_time': '2025-09-06T08:10:20Z', 'timestamp': 1725604220.0, 'timezone': 'UTC'}
```

---

## ⚠️ Notes

* If you see **"Session termination failed: 404"** on shutdown:
  This is likely a benign race condition where the server has already closed the MCP session before the client’s final `DELETE /mcp` and we assume this safe to ignore.
* Tokens are cached under `~/.fastmcp/oauth-mcp-client-cache/`.
  You can clear this cache with:

  ```bash
  rm -rf ~/.fastmcp/oauth-mcp-client-cache/http_localhost_8005*
  ```
* Multiple MCP clients can share the same proxy credentials safely, because:

  * Each client has its own loopback redirect URI.
  * PKCE ties the authorization code to the specific client session.
  * The RS proxy validates both redirect and PKCE before issuing tokens.

---
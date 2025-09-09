# MCP Google OAuth Proxy Server — README

This folder contains a **Model Context Protocol (MCP) Resource Server** that protects its `/mcp` endpoint using **Google OAuth 2.0**. It implements the **OAuth Proxy pattern** with **PKCE**, **Resource Indicators (RFC 8707)**, and **Dynamic Client Registration (DCR)**—so *any* MCP client (including desktop apps on random localhost ports) can authenticate via Google, even though Google doesn’t support DCR natively.

---

## What you get

* ✅ Protected MCP endpoint at `/mcp`
* ✅ Standard OAuth discovery endpoints

  * `/.well-known/oauth-protected-resource` (RS metadata, RFC 9728)
  * `/.well-known/oauth-authorization-server` (AS metadata)
* ✅ OAuth AS façade:

  * `/register` (local DCR)
  * `/authorize` (PKCE + resource)
  * `/token` (code/refresh exchange)
  * `/auth/callback` (fixed upstream callback → forwards back to client)
* ✅ Two protected tools as examples:

  * `get_time`
  * `get_user_info`

---

## Requirements

* Python 3.10+
* A Google OAuth **Web** client (Client ID + Client Secret)
* Uvicorn (installed via FastMCP runtime)
* `fastmcp` and its auth providers installed in your virtualenv

---

## Quick start

### 1) Create your `.env`

```bash
# Server base URL & bind
RS_BASE_URL="http://localhost:8005"
RS_HOST="0.0.0.0"
RS_PORT="8005"
MCP_PATH="/mcp"

# Google OAuth credentials (from Google Cloud Console → OAuth client)
GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

# Must match exactly in the Google app's Authorized redirect URIs:
# e.g., http://localhost:8005/auth/callback
GOOGLE_REDIRECT_PATH="/auth/callback"

# Minimal recommended scopes (space-separated)
REQUIRED_SCOPES="openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"

# Allow MCP clients running on localhost to register dynamic loopback callbacks
ALLOWED_CLIENT_REDIRECT_URIS="http://localhost:*;http://127.0.0.1:*"
```

> **Important:** In the **Google Cloud Console → Credentials → OAuth 2.0 Client IDs**, add **Authorized redirect URI** exactly as:
> `http://localhost:8005/auth/callback`
> (Use your own host/port if you change them.)

### 2) Activate venv and run

```bash
source .venv/bin/activate
uv run server.py
```

You should see log lines like:

```
INFO: Uvicorn running on http://0.0.0.0:8005
INFO: RS base URL: http://localhost:8005
INFO: MCP endpoint path: /mcp
INFO: Redirect path (Google): /auth/callback
INFO: Resource (audience): http://localhost:8005/mcp
```

---

## Verify it’s working

### A) First contact → 401 challenge + discovery pointer

```bash
curl -i http://localhost:8005/mcp
```

Look for:

```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer error="invalid_token", resource_metadata="http://localhost:8005/.well-known/oauth-protected-resource"
```

### B) Resource Server (RS) metadata

```bash
curl -s http://localhost:8005/.well-known/oauth-protected-resource | jq
```

Check that:

* `"resource"` == `http://localhost:8005/mcp` (**no trailing slash**)
* `"authorization_servers"` includes `http://localhost:8005/`
* `"scopes_supported"` list your scopes

### C) Authorization Server (AS) metadata

```bash
curl -s http://localhost:8005/.well-known/oauth-authorization-server | jq
```

You should see `authorization_endpoint`, `token_endpoint`, `registration_endpoint`, and `code_challenge_methods_supported: ["S256"]`.

### D) Health check

```bash
curl -s http://localhost:8005/healthz | jq
```

---

## How the OAuth Proxy pattern works (short version)

* **Problem:** MCP clients expect **Dynamic Client Registration (DCR)** and **loopback** callbacks (random localhost ports). Traditional OAuth providers (like Google) don’t support DCR and require fixed, pre-registered redirect URIs.
* **Solution:** The RS acts as an **OAuth Proxy**:

  * It **pretends** to be a DCR-capable Authorization Server to MCP clients.
  * It uses your pre-registered Google **client ID/secret** and **fixed** callback `BASE_URL + /auth/callback` upstream.
  * When clients authorize, the proxy:

    1. Stores the client’s **loopback** callback (e.g., `http://localhost:53530/oauth/callback`) and **PKCE challenge**.
    2. Redirects the user to Google using the RS’s **fixed** callback.
    3. Receives Google’s code, exchanges it for tokens at Google.
    4. Generates a **new code** for the MCP client and forwards the browser to the client’s **loopback** callback.
    5. When the client calls `/token` with its **PKCE verifier**, the proxy returns the **stored Google tokens**.
* **Security:** PKCE is enforced **twice**:

  * Client ↔ Proxy (your app)
  * Proxy ↔ Google (when supported — enabled by default)

This lets **any** MCP client authenticate with Google, safely, without the client needing a Google app.

---

## Running a sample client

You can test with the simple client shown in the companion `universal_client/3-google-oauth-simple-client` folder, or any MCP-capable client (Claude Desktop, Cursor, etc.). The critical detail: clients must connect to **exactly** `http://localhost:8005/mcp` (no trailing slash unless your RS publishes one).

---

## Common pitfalls & fixes

* **Trailing slash mismatch (most common):**
  If `resource` is `http://localhost:8005/mcp` but the client uses `http://localhost:8005/mcp/`, auth will fail. Keep it **consistent** everywhere: server, discovery metadata, client config.

* **Wrong Authorized redirect URI in Google Console:**
  It must exactly equal `BASE_URL + GOOGLE_REDIRECT_PATH` (e.g., `http://localhost:8005/auth/callback`). Any mismatch → Google won’t redirect.

* **Stale FastMCP OAuth cache:**
  If you change ports/paths, clear caches:

  ```bash
  rm -rf ~/.fastmcp/oauth-mcp-client-cache/http_localhost_8005*
  ```

* **401 loops after “success”:**
  Usually scope mismatches or resource mismatch. Confirm:

  * `REQUIRED_SCOPES` match what you expect
  * The client is using the exact `resource` from RS metadata
  * Google consent screen/scopes are approved for your account

* **DELETE /mcp → 404 on shutdown:**
  Harmless. Some clients attempt to terminate session resources that may already be cleaned up.

---

## Environment variables reference

| Variable                       | Meaning                         | Example                                                                                                  |
| ------------------------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `RS_BASE_URL`                  | Public base URL of the RS/Proxy | `http://localhost:8005`                                                                                  |
| `RS_HOST`                      | Bind host for Uvicorn           | `0.0.0.0`                                                                                                |
| `RS_PORT`                      | Bind port                       | `8005`                                                                                                   |
| `MCP_PATH`                     | MCP endpoint path               | `/mcp`                                                                                                   |
| `GOOGLE_CLIENT_ID`             | Google OAuth client ID          | `1234.apps.googleusercontent.com`                                                                        |
| `GOOGLE_CLIENT_SECRET`         | Google OAuth client secret      | `…`                                                                                                      |
| `GOOGLE_REDIRECT_PATH`         | Upstream callback path          | `/auth/callback`                                                                                         |
| `REQUIRED_SCOPES`              | Space-separated scopes          | `openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile` |
| `ALLOWED_CLIENT_REDIRECT_URIS` | Allowed MCP loopback patterns   | `http://localhost:*;http://127.0.0.1:*`                                                                  |

---

## Troubleshooting checklist

* Does `GET /.well-known/oauth-protected-resource` show the **exact** resource string you expect?
* Does `GET /.well-known/oauth-authorization-server` list `/authorize`, `/token`, `/register`?
* Is Google’s **Authorized redirect URI** equal to `BASE_URL + GOOGLE_REDIRECT_PATH`?
* After changing ports/paths, did you clear the FastMCP OAuth cache?
* Are you using the same `RS_BASE_URL` in your `.env` and in the **client**?
* Are the scopes exactly what you configured (and consented to) at Google?

---

## Production notes

* Use HTTPS for `RS_BASE_URL`.
* Restrict `ALLOWED_CLIENT_REDIRECT_URIS` to trusted domains/ports.
* Consider rotating Google client secrets and configuring `token_revocation` if needed.
* Place RS behind a reverse proxy (nginx, Caddy) if exposing publicly.

---

## File map

* `server.py` — the RS + OAuth Proxy implementation (heavily commented)
* `/.well-known/...` — auto-exposed by FastMCP via the `GoogleProvider`
* `/auth/callback` — Google → RS callback (fixed, pre-registered)
* `/register` `/authorize` `/token` — proxy AS endpoints (client-facing)
* `/mcp` — protected MCP endpoint (JSON-RPC over HTTP transport)
* `/healthz` — unauthenticated server status

---

## Need to reset state?

```bash
# Kill the server, then:
rm -rf ~/.fastmcp/oauth-mcp-client-cache/http_localhost_8005*
# Restart server:
uv run server.py
```

---

## FAQ

**Q: Why proxy Google at all?**
A: MCP clients expect DCR and loopback redirects. Google doesn’t support DCR. The proxy pretends to be DCR-capable, then uses your fixed Google app behind the scenes, with secure PKCE at both layers.

**Q: Do MCP clients see my Google client secret?**
A: They *may* see the proxy-assigned `client_id`/`client_secret` used **against the proxy** (not Google). The Google secret is only used server-side at the proxy when exchanging codes with Google. Clients cannot use the proxy credentials directly with Google’s endpoints.

**Q: Why do tokens go through the RS?**
A: Because the RS must validate & enforce the **resource** (audience) and scopes for its `/mcp` API. The RS can revoke/rotate/upstream-check tokens and centralize policy—something you lose if clients talk directly to Google.

---

Happy building! If something’s unclear, read the in-file comments in `server.py`—they walk line-by-line through the setup and flow.

# client.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE
#   A minimal MCP client that authenticates to your MCP Resource Server (RS)
#   using the FastMCP OAuth Proxy flow (PKCE + loopback redirect) and then
#   calls two protected tools: `get_user_info` and `get_time`.
#
# WHAT THIS FILE TEACHES
#   • What an MCP "Client" is: a program that speaks the MCP protocol to a server.
#   • Why OAuth is involved: your RS protects tools; the client must first get a token.
#   • Why an "OAuth Proxy" exists: Google (and most providers) don’t support DCR.
#     The RS pretends to be a DCR-capable Authorization Server to the client,
#     while bridging the real OAuth to Google behind the scenes.
#   • Loopback redirect + PKCE (at a high level):
#       - The client spins up a tiny loopback HTTP listener (localhost:random/callback).
#       - The browser redirects back there after auth (that’s “loopback redirect”).
#       - The client uses PKCE (a one-time proof) to bind the code to this client run.
#   • How FastMCP’s client library handles:
#       - Discovery (401 + WWW-Authenticate → .well-known endpoints)
#       - Dynamic Client Registration against the RS proxy
#       - Browser login + callback
#       - Token exchange + storage
#       - Calling MCP tools and reading their JSON results
#
# PREREQUISITES
#   • Your RS is running with OAuth proxy configured (e.g., http://localhost:8005/mcp).
#   • Your Google OAuth app has redirect URI set to the RS proxy’s callback
#     (e.g., http://localhost:8005/auth/callback).
#
# HOW TO RUN
#   • python -m venv .venv && source .venv/bin/activate
#   • pip install fastmcp
#   • python client.py
#
# EXPECTED UX
#   • On first run, your browser opens → Google sign-in → consent.
#   • Client prints tools list, your Google user info, and server time.
#
# NOTES
#   • The “Session termination failed: 404” at shutdown is a benign race:
#     the client tries to DELETE /mcp after the session was already closed
#     (or reclaimed). We suppress that specific message.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio

# FastMCP provides:
#   - Client: the MCP transport + JSON-RPC coordinator.
#   - OAuth: a helper that implements the OAuth Proxy pattern against the RS,
#            including DCR, PKCE, loopback redirect, token exchange, refresh, etc.
from fastmcp import Client
from fastmcp.client.auth import OAuth


def result_to_json(result):
    """
    Convert a FastMCP CallToolResult into a Python dict.

    WHY THIS IS NEEDED
    ------------------
    MCP tools can return multiple content blocks (text, json, images...).
    FastMCP represents the tool's structured output as a "json" content item.
    Depending on SDK versions, JSON might arrive as:
      • type == "json" with data in `c.data`, or
      • type == "text" containing a JSON string (fallback).

    This helper makes the demo robust across environments.
    """
    # CallToolResult.content is a list of typed blocks.
    for c in getattr(result, "content", []) or []:
        # Newer SDKs: explicit JSON block.
        if getattr(c, "type", None) == "json":
            return getattr(c, "data", None)
        # Fallback: some builds serialize JSON as plain text.
        if getattr(c, "type", None) == "text":
            import json
            try:
                return json.loads(getattr(c, "text", ""))
            except Exception:
                pass
    return None


async def main():
    # ─────────────────────────────────────────────────────────────────────────
    # 1) Configure OAuth helper
    # ─────────────────────────────────────────────────────────────────────────
    # mcp_url:
    #   The MCP endpoint on your RS proxy. The client will:
    #     • POST /mcp  → receive 401 + WWW-Authenticate with metadata pointer
    #     • GET /.well-known/* to discover the RS + AS metadata
    #     • POST /register to the RS proxy (DCR emulation)
    #     • /authorize → opens browser
    #     • /auth/callback (at RS) ↔ client loopback callback (localhost:random)
    #     • /token to exchange the final code for tokens
    #
    # scopes:
    #   Requested permissions. These are advertised by your RS proxy in
    #   /.well-known/oauth-protected-resource and must be allowed by your
    #   Google app. Minimal OIDC login often includes:
    #     - "openid"
    #     - "https://www.googleapis.com/auth/userinfo.email"
    #     - "https://www.googleapis.com/auth/userinfo.profile"
    #
    # Under the hood:
    #   • The client generates a PKCE challenge+verifier and a loopback redirect URI
    #     (like http://localhost:61776/callback).
    #   • The RS proxy stores the client’s redirect + PKCE, and simultaneously uses
    #     its own fixed Google redirect + PKCE to perform the upstream flow.
    #   • After Google returns to the RS, the RS exchanges the code with Google,
    #     then forwards a new code back to the client’s loopback callback.
    #   • The client finally calls the RS /token with its PKCE verifier to receive
    #     the actual Google tokens (access/refresh), now bound to this session.
    oauth = OAuth(
        mcp_url="http://localhost:8005/mcp",
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        # TIP: you can add `open_browser=False` and show the URL yourself if needed.
        # TIP: you can pass `redirect_host="127.0.0.1"` to force loopback host.
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2) Open a session to the MCP server
    # ─────────────────────────────────────────────────────────────────────────
    # The `Client` manages a "streamable-http" session with your RS:
    #   - Handles auth challenge (401) → kicks off OAuth helper
    #   - Maintains a server-side session (/mcp) with an ID
    #   - Sends JSON-RPC initialize → gets server capabilities
    #
    # Passing `auth=oauth` wires in the OAuth flow described above.
    async with Client("http://localhost:8005/mcp", auth=oauth) as client:
        # If it’s the first run (or cache cleared), your browser will open.
        print("✓ Authenticated with Google!")

        # ─────────────────────────────────────────────────────────────────────
        # 3) Discover tools
        # ─────────────────────────────────────────────────────────────────────
        # list_tools() returns Tool objects, NOT dicts. Each tool has:
        #   - name: the identifier you call by string
        #   - description / input schema (depending on server)
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])

        # ─────────────────────────────────────────────────────────────────────
        # 4) Call a protected tool: get_user_info
        # ─────────────────────────────────────────────────────────────────────
        # The RS will verify the Bearer token (issued by Google, delivered by
        # the proxy) before running the tool. If the token is missing/invalid,
        # you’d see another 401 and the client would re-auth if needed.
        res_info = await client.call_tool("get_user_info")
        info = result_to_json(res_info) or {}
        print("User info:", info)
        print("Google user:", info.get("email"))
        print("Name:", info.get("name"))

        # ─────────────────────────────────────────────────────────────────────
        # 5) Call another protected tool: get_time
        # ─────────────────────────────────────────────────────────────────────
        res_time = await client.call_tool("get_time")
        t = result_to_json(res_time) or {}
        print("Time:", t)

        # Optional: explicitly close. (The async context manager would do this
        # for you, but it’s clear to show where the session ends.)
        await client.close()


# Standard asyncio entry point with a small nicety:
# Some FastMCP client versions may log "Session termination failed: 404" because
# the server-side session was already cleaned up before the DELETE /mcp arrives.
# That’s harmless — we suppress just that message here.
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        if "Session termination failed: 404" in str(e):
            # Benign race at shutdown — ignore.
            pass
        else:
            raise
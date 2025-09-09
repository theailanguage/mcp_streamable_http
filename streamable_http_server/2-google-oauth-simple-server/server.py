# server.py
# =============================================================================
# PURPOSE
# -----------------------------------------------------------------------------
# This file starts a **Model Context Protocol (MCP) Resource Server** that is
# protected by Google OAuth 2.0. It demonstrates a complete, standards-aligned
# flow where:
#
#  - The **client** (e.g., Claude Desktop, a custom script) first hits the
#    protected MCP endpoint and gets a 401 with a `WWW-Authenticate` header.
#  - The header points the client to this server’s **Protected Resource
#    Metadata** (RFC 9728), which lists an **Authorization Server** (AS).
#  - This process includes **Dynamic Client Registration** (DCR), **PKCE**,
#    and a **resource indicator** (the exact MCP URL) to bind tokens.
#  - The server then **proxies OAuth** to Google: it sends users to Google’s
#    login/consent, receives the code on `/auth/callback`, swaps it for tokens,
#    and validates access tokens against Google’s `tokeninfo`.
#
# Think of this server as BOTH:
#   (1) The **Resource Server (RS)** that hosts the protected `/mcp` endpoint,
#   (2) A local **Authorization Server facade** that MCP clients can discover
#       and speak to using standard OAuth/DCR/PKCE, while we in turn delegate
#       to Google behind the scenes.
#
# Important dev notes:
#   • The resource string must match EXACTLY (trailing slash differences break it).
#   • You can clear local FastMCP OAuth caches during dev with:
#       rm -rf ~/.fastmcp/oauth-mcp-client-cache/http_localhost_8005*
#   • Test endpoints:
#       - GET  /.well-known/oauth-protected-resource
#       - GET  /.well-known/oauth-authorization-server
#       - GET  /healthz
#       - POST /mcp  (protected; clients use this for MCP JSON-RPC)
# =============================================================================


from __future__ import annotations  # (1) Future: allow annotations to be strings in older Python

import logging  # (2) Standard logging so we can see what’s happening
import os       # (3) Read environment variables (configured via .env or shell)
from typing import Any  # (4) Type hints for clarity

import dotenv  # (5) Loads .env file so os.environ has your local config
from starlette.requests import Request          # (6) For our health check route signature
from starlette.responses import JSONResponse    # (7) To return JSON from health check

# (8) FastMCP is our MCP framework. It exposes:
#     - a protected `/mcp` endpoint (HTTP transport in this example),
#     - auth hooks that emit the correct 401 & discovery metadata,
#     - convenient decorators for MCP tools and custom routes,
#     - a `run()` helper to start Uvicorn with the right transport.
from fastmcp import FastMCP

# (9) GoogleProvider is the key piece: it acts like an OAuth Authorization
#     Server (AS) *towards clients* while actually delegating auth to Google.
#     It:
#       • Publishes /.well-known/oauth-authorization-server for clients.
#       • Implements DCR (Dynamic Client Registration) locally.
#       • Handles PKCE + resource-bound authorization code flow.
#       • Exchanges Google codes for tokens and validates access tokens.
from fastmcp.server.auth.providers.google import GoogleProvider


# -----------------------------------------------------------------------------
# Logging & environment setup
# -----------------------------------------------------------------------------

logger = logging.getLogger("mcp.rs.google")  # (10) A named logger for our service
logging.basicConfig(level=logging.INFO)      # (11) Print INFO+ logs to stdout (adjust as needed)

dotenv.load_dotenv()  # (12) Load .env file into os.environ (only affects current process)


# -----------------------------------------------------------------------------
# Configuration – these can all be supplied via environment variables.
# When the variable is missing, we fall back to safe local defaults for dev.
# -----------------------------------------------------------------------------

# (13) **RS_BASE_URL**: The public base URL of THIS server (the RS+AS facade).
#      Clients will use this value for discovery and redirects. It must match
#      how the browser/client can actually reach you. In local dev we default
#      to http://localhost:8005.
BASE_URL = os.environ.get("RS_BASE_URL", "http://localhost:8005")

# (14) Local bind host and port for the Uvicorn server.
#      HOST "0.0.0.0" listens on all interfaces (fine in dev), PORT defaults to 8005.
HOST = os.environ.get("RS_HOST", "0.0.0.0")
PORT = int(os.environ.get("RS_PORT", "8005"))

# (15) **MCP_PATH** is the exact path segment under BASE_URL that is the
#      protected MCP endpoint. This string becomes the **resource indicator**.
#      IMPORTANT: CONSISTENCY MATTERS. If you choose "/mcp", then everywhere
#      (metadata, clients, and resource= param) must use "/mcp" (no trailing '/').
MCP_PATH = os.environ.get("MCP_PATH", "/mcp")

# (16) Google OAuth app credentials. These identify your Google project to Google.
#      They are used by the provider when exchanging the auth code for tokens.
#      If missing, we exit with a clear error (since auth can’t work without them).
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# (17) The path on THIS server where Google will redirect the user back with
#      the authorization code. You must register the full URL
#      (BASE_URL + REDIRECT_PATH) in your Google Cloud Console OAuth client.
REDIRECT_PATH = os.environ.get("GOOGLE_REDIRECT_PATH", "/auth/callback")

# (18) The minimal scopes we ask Google for. In many OAuth tutorials you’ll also
#      see `email` and `profile`, but modern Google profile/email fetch uses:
#        • openid
#        • https://www.googleapis.com/auth/userinfo.email
#        • https://www.googleapis.com/auth/userinfo.profile
#      We split on whitespace so you can define REQUIRED_SCOPES in .env as a single line.
REQUIRED_SCOPES = os.environ.get(
    "REQUIRED_SCOPES",
    "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
).split()

# (19) DCR: allow MCP clients to dynamically register loopback redirect URIs.
#      In dev, MCP clients typically spin up a small local HTTP listener on a
#      random port (e.g., http://localhost:53530/oauth/callback). We permit
#      localhost patterns by default. In production, lock this down.
ALLOWED_CLIENT_REDIRECTS = os.environ.get(
    "ALLOWED_CLIENT_REDIRECT_URIS",
    "http://localhost:*;http://127.0.0.1:*",
).split(";")

# (20) A derived, canonical **resource** string (audience). This must match how
#      clients connect. We expose it in `.well-known/oauth-protected-resource`.
#      Clients will include this exact value as the `resource=` parameter in
#      their authorization request so that Google issues a token bound to it.
RESOURCE = f"{BASE_URL}{MCP_PATH}"  # e.g., "http://localhost:8005/mcp"
#      ⚠️ DO NOT add a trailing slash here unless ALL clients also use the slash.


# -----------------------------------------------------------------------------
# Build the Google OAuth provider (our AS facade that delegates to Google)
# -----------------------------------------------------------------------------

# (21) We now construct a GoogleProvider. This single object:
#       • Publishes AS metadata (/.well-known/oauth-authorization-server),
#       • Provides /authorize, /token, /register endpoints,
#       • Manages PKCE + DCR,
#       • Talks to Google for user login and token validation,
#       • Integrates with FastMCP so the protected `/mcp` endpoint knows how
#         to challenge clients and verify their bearer tokens.
google_auth = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,                     # (22) Your Google OAuth client id
    client_secret=GOOGLE_CLIENT_SECRET,             # (23) Your Google OAuth client secret
    base_url=BASE_URL,                              # (24) Public base URL of THIS server
    redirect_path=REDIRECT_PATH,                    # (25) Callback path (BASE_URL + this) registered at Google
    required_scopes=REQUIRED_SCOPES,                # (26) Scopes we require from Google
    allowed_client_redirect_uris=ALLOWED_CLIENT_REDIRECTS,  # (27) DCR patterns for loopback OAuth clients
    # (28) The provider infers the resource from how `/mcp` is mounted by FastMCP,
    #      but we document RESOURCE above to emphasize the importance of exact match.
)


# -----------------------------------------------------------------------------
# Create the MCP application with authentication enabled
# -----------------------------------------------------------------------------

# (29) FastMCP instance:
#     - `name` and `instructions` appear in client UIs (friendly branding).
#     - `auth=google_auth` wires in the auth provider so:
#          • `/mcp` is protected (returns 401 + WWW-Authenticate initially),
#          • `/.well-known/oauth-protected-resource` is served for RS metadata,
#          • `/.well-known/oauth-authorization-server` + `/authorize` + `/token`
#            + `/register` are exposed (the AS facade routes),
#          • `/auth/callback` handles Google → RS → client loopback.
mcp = FastMCP(
    name="MCP RS with Google OAuth",  # (30) Friendly name shown to clients
    instructions=(
        "Protected MCP server that delegates OAuth to Google via a DCR-capable proxy."
    ),  # (31) Short description for clients
    auth=google_auth,  # (32) The magic glue: provides 401 challenges + metadata + OAuth endpoints
)


# -----------------------------------------------------------------------------
# Protected MCP tools
# -----------------------------------------------------------------------------

# (33) This decorator registers a tool callable over MCP. Because the MCP
#      endpoint is protected, calling this requires a valid Google bearer token.
@mcp.tool()
async def get_time() -> dict[str, Any]:
    """
    Return current server time. Requires a valid Google access token.
    If no/invalid token is supplied, the client will first see a 401 and must
    complete OAuth before retrying.
    """
    import datetime as _dt  # (34) Local import for the example

    now = _dt.datetime.utcnow()  # (35) Get current UTC time
    return {                     # (36) Return a simple JSON-serializable result
        "current_time": now.isoformat() + "Z",
        "timestamp": now.timestamp(),
        "timezone": "UTC",
    }


# (37) Another protected tool. This demonstrates reading the verified token
#      claims (as provided by the GoogleProvider after validation).
@mcp.tool()
async def get_user_info() -> dict[str, Any]:
    """
    Return information about the authenticated Google user
    (from the validated access token / userinfo).
    """
    # (38) Provider surfaces the current request’s verified access token via a dependency.
    #      We import here so the module remains importable even if FastMCP internals change.
    from fastmcp.server.dependencies import get_access_token  # type: ignore

    token = get_access_token()  # (39) Grab the verified token object for this request

    # (40) Depending on provider config, claims may include OIDC-like fields.
    #      For Google, we often also fetch userinfo to enrich these claims.
    return {
        "google_id": token.claims.get("sub"),       # (41) Subject (user id)
        "email": token.claims.get("email"),         # (42) Email (if scope allowed)
        "name": token.claims.get("name"),           # (43) Display name (if available)
        "picture": token.claims.get("picture"),     # (44) Avatar URL (if available)
        "locale": token.claims.get("locale"),       # (45) Locale (if available)
        
        # (46) If you need more profile fields, call Google’s userinfo endpoint
        #      (the provider already does this in many setups).
    }


# -----------------------------------------------------------------------------
# Unauthenticated health check (handy for readiness probes)
# -----------------------------------------------------------------------------

# (47) Not all routes have to be protected. Here we expose a simple health check
#      that returns status + key configuration so you can easily verify setup.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    # (48) We include the resource and scopes so you can visually confirm the
    #      important bits when debugging.
    return JSONResponse(
        {
            "status": "ok",
            "base_url": BASE_URL,
            "mcp_path": MCP_PATH,
            "resource": RESOURCE,
            "scopes": REQUIRED_SCOPES,
        }
    )


# -----------------------------------------------------------------------------
# Entrypoint – start the HTTP server and mount the MCP transport
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # (49) Fail fast if Google credentials are missing. Without these, the
    #      provider can’t exchange auth codes for tokens.
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error(
            "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not set. "
            "Put them in your shell env or a .env file before starting the server."
        )
        raise SystemExit(1)

    # (50) Log the key values so you can spot mismatches (e.g., trailing slash issues).
    logger.info("🚀 RS base URL: %s", BASE_URL)
    logger.info("🛣  MCP endpoint path: %s", MCP_PATH)
    logger.info("🔁 Redirect path (Google): %s", REDIRECT_PATH)
    logger.info("🔐 Required scopes: %s", " ".join(REQUIRED_SCOPES))
    logger.info("🏁 Allowed DCR client redirects: %s", ALLOWED_CLIENT_REDIRECTS)
    logger.info("🎯 Resource (audience): %s", RESOURCE)

    # (51) Start the server with the **streamable-http** transport. This exposes:
    #       • POST /mcp (protected MCP over HTTP)
    #       • GET  /.well-known/oauth-protected-resource  (RS metadata)
    #       • GET  /.well-known/oauth-authorization-server (AS metadata)
    #       • GET  /authorize, POST /token, POST /register (AS facade)
    #       • GET  /auth/callback (Google → RS → client loopback)
    #
    #     `path=MCP_PATH` is CRUCIAL for resource correctness. The clients will
    #     include this full resource (BASE_URL + MCP_PATH) when authorizing.
    mcp.run(
        transport="streamable-http",  # (52) Use HTTP transport (good for local dev & desktop apps)
        host=HOST,                    # (53) Bind host (0.0.0.0 listens on all interfaces)
        port=PORT,                    # (54) Bind port (ensure it matches your BASE_URL)
        path=MCP_PATH,                # (55) Mount path for the MCP endpoint (defines the resource)
    )


# =============================================================================
# QUICK TEST / DEBUG GUIDE
# -----------------------------------------------------------------------------
# 1) Start the server:
#       uv run server.py
#
# 2) Confirm the 401 challenge & discovery headers:
#       curl -i http://localhost:8005/mcp
#    You should see:
#       HTTP/1.1 401 Unauthorized
#       WWW-Authenticate: Bearer error="invalid_token", resource_metadata="http://localhost:8005/.well-known/oauth-protected-resource"
#
# 3) Inspect RS metadata:
#       curl -s http://localhost:8005/.well-known/oauth-protected-resource | jq
#    Make sure "resource" is EXACTLY "http://localhost:8005/mcp" (no trailing slash).
# {
#   "resource": "http://localhost:8005/mcp",
#   "authorization_servers": [
#     "http://localhost:8005/"
#   ],
#   "scopes_supported": [
#     "openid",
#     "https://www.googleapis.com/auth/userinfo.email",
#     "https://www.googleapis.com/auth/userinfo.profile"
#   ],
#   "bearer_methods_supported": [
#     "header"
#   ]
# }
#
# 4) Inspect AS metadata:
#       curl -s http://localhost:8005/.well-known/oauth-authorization-server | jq
#
# 5) Clear FastMCP client OAuth cache (helpful during dev if you change ports/paths):
#       rm -rf ~/.fastmcp/oauth-mcp-client-cache/http_localhost_8005*
#
# 6) Run a sample FastMCP client (pseudo):
#       from fastmcp import Client
#       async with Client("http://localhost:8005/mcp", auth="oauth") as c:
#           print(await c.list_tools())
#           print(await c.call_tool("get_time"))
#
# 7) If you see repeated 401s:
#       • Check that the client connects to EXACTLY "http://localhost:8005/mcp"
#         (no trailing slash).
#       • Ensure GOOGLE_CLIENT_ID/SECRET are set and correct.
#       • Verify Google OAuth consent screen is configured and scopes allowed.
#       • Confirm your Google OAuth **Authorized redirect URI** is:
#           http://localhost:8005/auth/callback
# =============================================================================

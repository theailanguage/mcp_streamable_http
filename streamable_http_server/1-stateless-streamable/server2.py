# server2.py
# -------------------------------------------------------------------------------------
# PURPOSE:
# This script launches a simple stateless MCP (Model Context Protocol) server using
# FastMCP, a high-level server abstraction from the MCP Python SDK.
#
# The server exposes two tools:
#   1. multiply_numbers — takes two floats and returns their product.
#   2. divide_numbers — takes two floats and returns their quotient.
#
# These tools are structured: both their input and output are defined using
# Pydantic models. This enables automatic schema validation and structured responses.
#
# The server uses the `streamable-http` transport, which allows communication
# over a modern HTTP streaming protocol that supports structured JSON-RPC calls.
#
# It is stateless, meaning it holds no memory or session information between calls.
# -------------------------------------------------------------------------------------

# === Imports ===

# click: For building command-line interfaces (CLI), such as --port and --log-level
import click

# logging: Standard Python module for displaying log messages to stdout/stderr
import logging

# sys: For exiting the program in case of errors (e.g., sys.exit(1))
import sys

# BaseModel and Field: From pydantic, used for structured input/output validation
from pydantic import BaseModel, Field

# FastMCP: High-level abstraction that makes it easy to create and run MCP servers
from mcp.server.fastmcp import FastMCP

# === CLI Setup ===
# This section enables you to run this script with custom flags like:
#   python server2.py --port 3001 --log-level INFO

@click.command()  # Defines a CLI command
@click.option("--port", default=3001, help="Port number to run the server on")
@click.option("--log-level", default="DEBUG", help="Logging level (e.g., DEBUG, INFO)")
def main(port: int, log_level: str) -> None:
    # === Logging Configuration ===
    # Sets the logging format and level based on the provided CLI argument
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.DEBUG),  # convert string to log level constant
        format="%(asctime)s - %(levelname)s - %(message)s",       # format: timestamp - level - message
    )
    logger = logging.getLogger(__name__)  # Logger instance scoped to this file/module
    logger.info("🚀 Starting Stateless Multiplication/Division MCP Server...")

    # === Create FastMCP Server ===
    # This initializes an MCP server with the following properties:
    # - Name: Appears in client UIs like Claude Desktop
    # - host: IP interface to bind (localhost means only local access)
    # - port: Port to serve on
    # - stateless_http=True: Ensures no session memory is kept between requests
    mcp = FastMCP(
        "Stateless Math Server",   # Server name
        host="localhost",          # Bind to localhost only
        port=port,                 # Use port from CLI flag
        stateless_http=True,      # Enforces stateless behavior
    )

    # === Define Reusable Input Schema ===
    # Shared across all arithmetic tools (same as server1.py)
    class ArithmeticInput(BaseModel):
        a: float = Field(..., description="First number")   # Required float named 'a'
        b: float = Field(..., description="Second number")  # Required float named 'b'

    # === Define Reusable Output Schema ===
    # Encapsulates both result value and math expression
    class ArithmeticResult(BaseModel):
        result: float = Field(..., description="Calculation result")             # Numerical result
        expression: str = Field(..., description="Math expression performed")    # Explanation as a string

    # === Register Tool: Multiply Numbers ===
    @mcp.tool(description="Multiply two numbers", title="Multiply Numbers")
    def multiply_numbers(params: ArithmeticInput) -> ArithmeticResult:
        result = params.a * params.b  # Perform multiplication
        return ArithmeticResult(      # Return result with expression
            result=result,
            expression=f"{params.a} * {params.b}"
        )

    # === Register Tool: Divide Numbers ===
    @mcp.tool(description="Divide a by b", title="Divide Numbers")
    def divide_numbers(params: ArithmeticInput) -> ArithmeticResult:
        if params.b == 0:
            raise ValueError("Division by zero is not allowed.")  # Handle division by 0 error
        result = params.a / params.b  # Perform division
        return ArithmeticResult(      # Return result with expression
            result=result,
            expression=f"{params.a} / {params.b}"
        )

    # === Run the Server ===
    try:
        # This starts the FastMCP server with streamable HTTP transport
        # It listens on /mcp endpoint and responds to JSON-RPC requests
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        # Handle Ctrl+C clean shutdown
        print("\n🛑 Server shutting down gracefully...")
    except Exception as e:
        # Handle any unhandled errors
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Final message on exit
        print("✅ Server exited.")

# === CLI Entry Point ===
# This block ensures the main() function only runs if the script is executed directly
if __name__ == "__main__":
    main()
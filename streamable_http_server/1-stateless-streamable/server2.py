# server2_fastmcp_structured.py
# Stateless streamable HTTP MCP server for multiplication/division with schema
# Copyright 2025 Google LLC

import click
import logging
import sys
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# CLI: --port and --log-level
@click.command()
@click.option("--port", default=3001, help="Port number to run the server on")
@click.option("--log-level", default="DEBUG", help="Logging level (e.g., DEBUG, INFO)")
def main(port: int, log_level: str) -> None:
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.DEBUG),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Stateless Multiplication/Division MCP Server...")

    # Create a stateless FastMCP server
    mcp = FastMCP(
        "Stateless Math Server",
        host="localhost",
        port=port,
        stateless_http=True,  # ensures no session state is maintained
    )

    # Input and output schemas using Pydantic
    class MathInput(BaseModel):
        a: float = Field(..., description="First number")
        b: float = Field(..., description="Second number")

    class MathResult(BaseModel):
        result: float = Field(..., description="Calculation result")
        expression: str = Field(..., description="Math expression performed")

    @mcp.tool(description="Multiply two numbers", title="Multiply Numbers")
    def multiply_numbers(params: MathInput) -> MathResult:
        result = params.a * params.b
        return MathResult(result=result, expression=f"{params.a} * {params.b}")

    @mcp.tool(description="Divide a by b", title="Divide Numbers")
    def divide_numbers(params: MathInput) -> MathResult:
        if params.b == 0:
            raise ValueError("Division by zero is not allowed.")
        result = params.a / params.b
        return MathResult(result=result, expression=f"{params.a} / {params.b}")

    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        print("✅ Server exited.")

if __name__ == "__main__":
    main()
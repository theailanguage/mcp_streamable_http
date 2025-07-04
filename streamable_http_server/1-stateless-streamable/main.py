# main.py
# ------------------------------------------------------------------
# PURPOSE:
# This is the central entry point to start one MCP server.
# The user must specify whether to start `server1.py` or `server2.py`
# using the `--server` command-line option.
#
# USAGE EXAMPLES:
#   python main.py --server server1 --log-level DEBUG
#   python main.py --server server2 --log-level INFO
# ------------------------------------------------------------------

# --------------------------------------------------
# Import sys to interact with the Python runtime system,
# including exiting the program with a specific status.
# --------------------------------------------------
import sys

# --------------------------------------------------
# Import click, a third-party library for creating command-line tools.
# It makes it easy to define options like `--server`.
# --------------------------------------------------
import click

# --------------------------------------------------
# Import the main functions from each server file.
# These `main()` functions start the respective MCP servers.
# We're aliasing them for clarity.
# --------------------------------------------------
from server1 import main as server1_main
from server2 import main as server2_main

# --------------------------------------------------
# Define a CLI entry point using click.
# The `--server` option is required and must be one of the two valid choices.
# The `--log-level` option is optional and passed through to the target server.
# --------------------------------------------------
@click.command()
@click.option(
    "--server",
    type=click.Choice(["server1", "server2"]),
    required=True,
    help="Select which server to run (server1 or server2)",
)
@click.option(
    "--log-level",
    default="DEBUG",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Set logging level for the server (default: DEBUG)",
)
def main(server: str, log_level: str):
    """
    Entry point for selecting and starting one MCP server.
    Passes selected log level to the appropriate server.
    """

    # Convert server and log-level options into a format Click expects
    args = ["--log-level", log_level]

    if server == "server1":
        sys.exit(server1_main(args=args, standalone_mode=False))
    elif server == "server2":
        sys.exit(server2_main(args=args, standalone_mode=False))
    else:
        print("❌ Invalid server option. Use --server with either 'server1' or 'server2'.")
        sys.exit(1)

# --------------------------------------------------
# This block ensures that the main() function runs
# only when this script is executed directly.
# --------------------------------------------------
if __name__ == "__main__":
    main()  # type: ignore
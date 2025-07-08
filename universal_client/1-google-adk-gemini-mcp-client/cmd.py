# ------------------------------------------------------------------------------
# FILE: cmd.py
# ------------------------------------------------------------------------------
# PURPOSE:
# Entry point for the ADK chat client. Enables user to interact with an
# LLM agent connected to MCP tool servers using Google's ADK.
# ------------------------------------------------------------------------------

import asyncio
import logging
from client import MCPClient
from utilities import print_json_response

# ------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
# ------------------------------------------------------------------------------

# Identifier for the ADK app (used when registering sessions or tools)
APP_NAME = "google_adk_gemini_mcp_client"

# Unique user ID for the current session
USER_ID = "theailanguage_001"

# Unique session ID (can help resume or distinguish multiple sessions)
SESSION_ID = "session_001"

# Define a set of tools that the client is allowed to use
# These could come from one or more tool servers
READ_ONLY_TOOLS = [
    'add_numbers',
    'subtract_numbers',
    'multiply_numbers',
    'divide_numbers',
    'run_command'
]

# ------------------------------------------------------------------------------
# LOGGING SETUP
# ------------------------------------------------------------------------------

# Configure logging to only show ERROR messages (suppress INFO, DEBUG, etc.)
logging.basicConfig(level=logging.ERROR)

# ------------------------------------------------------------------------------
# MAIN CHAT LOOP FUNCTION
# ------------------------------------------------------------------------------

async def chat_loop():
    """
    The main chat loop that continuously:
    - Prompts user for input
    - Sends the input to the ADK MCP agent
    - Streams and displays agent responses
    """

    print("\n💬 ADK LLM Agent Chat Started. Type 'quit' or ':q' to exit.\n")

    # Initialize the ADK MCP client with app/user/session configuration
    client = MCPClient(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        tool_filter=READ_ONLY_TOOLS
    )

    # Establish session with the toolset (negotiates with MCP tool servers)
    await client.init_session()

    try:
        # Continuous loop to accept user input and handle agent responses
        while True:
            user_input = input("You: ")

            # Handle quit commands gracefully
            if user_input.strip().lower() in ["quit", ":q", "exit"]:
                print("👋 Ending session. Goodbye!")
                break

            i = 0
            # Send the input task to the agent and stream responses
            async for event in await client.send_task(user_input):
                i += 1
                print_json_response(event, f"📦 Event #{i}")

                # Once a final response is received, print and break the loop
                if hasattr(event, "is_final_response") and event.is_final_response():
                    print(f"\n🧠 Agent Response:\n------------------------\n{event.content.parts[0].text}\n")
                    break
    finally:
        # Ensure the session is closed and resources are freed
        await client.shutdown()

# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        # Start the async chat loop using asyncio event loop
        asyncio.run(chat_loop())

    except asyncio.CancelledError:
        # This warning may appear due to background task shutdown 
        # mechanics in ADK/MCP
        print("\n⚠️ CancelledError suppressed during shutdown "
        "(safe to ignore for demo/educational code).")
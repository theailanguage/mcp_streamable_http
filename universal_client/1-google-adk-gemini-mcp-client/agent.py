# ------------------------------------------------------------------------------
# FILE: agent.py
# ------------------------------------------------------------------------------
# PURPOSE:
# Defines the AgentWrapper class that loads and constructs a Google ADK LLM Agent
# capable of communicating with MCP servers (via HTTP or STDIO).
# It also logs each loaded tool per server during initialization using rich print.
# ------------------------------------------------------------------------------

import asyncio
from rich import print  # Used for colorful terminal logging

# ADK's built-in LLM agent class
from google.adk.agents.llm_agent import LlmAgent

# Provides access to tools hosted on MCP servers
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

# Connection settings for different types of MCP servers
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool import StdioConnectionParams

# Custom parameters for local STDIO-based MCP servers
from mcp import StdioServerParameters

# Utility function to read the config.json file
from utilities import read_config_json


# ------------------------------------------------------------------------------
# CLASS: AgentWrapper
# ------------------------------------------------------------------------------
# Loads and manages a Google ADK agent along with the set of MCP tools.
# It handles:
# - Reading the MCP server config
# - Connecting to those servers
# - Filtering and attaching available tools
# - Printing tool info for each server
# ------------------------------------------------------------------------------

class AgentWrapper:
    def __init__(self, tool_filter=None):
        """
        Initializes the wrapper but does NOT build the agent yet.
        Call `await self.build()` after this to complete setup.

        Args:
            tool_filter (list[str] or None): Optional list of tool names to allow.
                                             If specified, only these tools will be loaded.
        """
        self.tool_filter = tool_filter
        self.agent = None          # Will hold the final LlmAgent after building
        self._toolsets = []        # Store all loaded toolsets for later cleanup


    async def build(self):
        """
        Builds the LlmAgent by:
        - Connecting to all MCP servers listed in the config
        - Loading tools from each server
        - Initializing the ADK agent with those tools

        Must be called before using `self.agent`.
        """
        toolsets = await self._load_toolsets()

        # Construct the ADK LLM Agent with the loaded toolsets
        self.agent = LlmAgent(
            model="gemini-2.0-flash",  # Choose model to power the agent
            name="enterprise_assistant",
            instruction="Assist the user with filesystem and MCP server tasks.",
            tools=toolsets
        )

        self._toolsets = toolsets  # Save toolsets for cleanup later


    async def _load_toolsets(self):
        """
        Reads MCP server info from config.json and loads toolsets from each.

        For each valid server:
        - Connects using HTTP or STDIO
        - Filters tools (if applicable)
        - Prints the tool names for the user

        Returns:
            List of MCPToolset objects ready for use by the agent.
        """
        config = read_config_json()  # Load server info from config file
        toolsets = []

        for name, server in config.get("mcpServers", {}).items():
            try:
                # Determine the connection method
                if server.get("type") == "http":
                    conn = StreamableHTTPServerParams(url=server["url"])

                elif server.get("type") == "stdio":
                    conn = StdioConnectionParams(
                        server_params=StdioServerParameters(
                            command=server["command"],
                            args=server["args"]
                        ),
                        timeout=5
                    )
                else:
                    raise ValueError(f"[red]❌ Unknown server type in config: '{server['type']}'[/red]")

                # Create and connect the toolset with the chosen connection
                toolset = MCPToolset(
                    connection_params=conn,
                    tool_filter=self.tool_filter
                )

                # Fetch tool list and print it nicely
                tools = await toolset.get_tools()
                tool_names = [tool.name for tool in tools]
                print(f"[bold green]✅ Tools loaded from server [cyan]'{name}'[/cyan]:[/bold green] {tool_names}")

                toolsets.append(toolset)

            except Exception as e:
                print(f"[bold red]⚠️  Skipping server '{name}' due to error:[/bold red] {e}")

        return toolsets


    async def close(self):
        """
        Gracefully shuts down each loaded toolset.
        This is important to avoid leftover background tasks or resources.
        """
        for toolset in self._toolsets:
            try:
                await toolset.close()  # Clean up each toolset's connections
            except Exception as e:
                print(f"[yellow]⚠️ Error closing toolset:[/yellow] {e}")

        # Small delay to ensure cancellation and cleanup completes
        await asyncio.sleep(1.0)
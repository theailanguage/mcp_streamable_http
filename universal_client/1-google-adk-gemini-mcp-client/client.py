# ------------------------------------------------------------------------------
# FILE: client.py
# ------------------------------------------------------------------------------
# PURPOSE:
# Defines MCPClient, a wrapper that connects a UI or chat interface to a Google
# ADK agent. It manages session state and routes user inputs through the agent
# to connected MCP toolsets.
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

# Google ADK content/message types
from google.genai.types import Content, Part

# Runner executes tasks with an agent using ADK's infrastructure
from google.adk.runners import Runner

# In-memory session service stores session data locally
from google.adk.sessions import InMemorySessionService

# Custom wrapper for building and managing the ADK agent and tools
from agent import AgentWrapper


# ------------------------------------------------------------------------------
# CLASS: MCPClient
# ------------------------------------------------------------------------------

class MCPClient:
    """
    Main client interface that connects the chat app or UI to the ADK agent.
    Handles:
    - Session creation
    - Agent loading
    - Message routing through the agent to the toolset
    """

    def __init__(self, app_name, user_id, session_id, tool_filter=None):
        """
        Constructor to initialize the MCPClient.

        Args:
            app_name (str): Unique application name used in session metadata.
            user_id (str): User identifier for session context.
            session_id (str): Session ID to separate multiple chat sessions.
            tool_filter (list[str] or None): Optional list of allowed tools.
        """

        # App metadata (useful for session tagging, logging, etc.)
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id

        # Use in-memory session service (stored in memory, not persistent)
        self.session_service = InMemorySessionService()

        # Prepare the agent wrapper with optional tool filtering
        # Tool filtering limits the tools this client can use
        self.agent_wrapper = AgentWrapper(tool_filter=tool_filter)

        # Runner (the main engine to send tasks and receive results) will be created later
        self.runner = None


    async def init_session(self):
        """
        Initializes the client:
        - Creates a session (locally, in memory)
        - Builds the ADK agent and its tools
        - Instantiates the ADK runner to execute user inputs
        """

        # Step 1: Create a session (ADK requires a session context)
        await self.session_service.create_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=self.session_id
        )

        # Step 2: Build the agent (loads tools, configurations, etc.)
        await self.agent_wrapper.build()

        # Step 3: Create the runner using the built agent and the session service
        self.runner = Runner(
            agent=self.agent_wrapper.agent,
            app_name=self.app_name,
            session_service=self.session_service
        )


    async def send_task(self, user_input):
        """
        Sends a user message to the ADK agent and streams the response.

        Args:
            user_input (str): Raw input from the user (natural language).

        Returns:
            Async generator that yields streaming response events from the agent.
        """

        # Wrap the user input into a Content object with role="user"
        new_message = Content(role="user", parts=[Part(text=user_input)])

        # Run the message asynchronously through the agent runner
        return self.runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=new_message
        )


    async def shutdown(self):
        """
        Gracefully shuts down the agent and its tools.
        Should be called at the end of the session to clean up async tasks.
        """

        await self.agent_wrapper.close()
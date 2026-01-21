"""Claude Agent SDK Executor for ARK.

Implements the ARK ExecutionEngine interface using Claude Agent SDK
for full agentic capabilities including tool use, multi-turn conversations,
and autonomous task execution.
"""

import os
import logging
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("executor-claude")

# Configuration
DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
DEFAULT_MAX_TURNS = int(os.getenv("CLAUDE_MAX_TURNS", "10"))


class Message:
    """ARK-compatible message format."""

    def __init__(
        self,
        role: str,
        content: str,
        name: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_call_id: str | None = None,
    ):
        self.role = role
        self.content = content
        self.name = name
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id

    def to_dict(self) -> dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


class ClaudeAgentExecutor:
    """
    ARK ExecutionEngine implementation using Claude Agent SDK.

    This executor provides full agentic capabilities:
    - Multi-turn conversations with tool use
    - Autonomous task execution with Claude's agentic loop
    - File operations, code execution, and search tools
    - Integration with ARK's tool system
    """

    def __init__(self):
        self.name = "Claude"
        self.description = "Claude Agent SDK Executor with full agentic capabilities"
        logger.info(f"Initialized {self.name} executor")

    async def execute_agent(self, request: dict[str, Any]) -> list[Message]:
        """
        Execute an agent request using Claude Agent SDK.

        Args:
            request: ExecutionEngineRequest containing:
                - agent: AgentConfig (name, namespace, prompt, model, tools)
                - userInput: Message with role and content
                - history: List of previous messages
                - tools: List of tool definitions

        Returns:
            List of Message objects with the agent's response
        """
        with tracer.start_as_current_span("execute_agent") as span:
            agent_config = request.get("agent", {})
            user_input = request.get("userInput", {})
            history = request.get("history", [])
            tools = request.get("tools", [])

            agent_name = agent_config.get("name", "claude-agent")
            system_prompt = agent_config.get("prompt", "")
            model_config = agent_config.get("model") or {}

            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.model", model_config.get("name", DEFAULT_MODEL) if model_config else DEFAULT_MODEL)

            logger.info(f"Executing agent '{agent_name}' with {len(tools)} tools")

            # Determine execution mode based on tools
            if tools:
                # Full agentic mode with Claude Agent SDK
                return await self._execute_agentic(
                    agent_name=agent_name,
                    system_prompt=system_prompt,
                    model_config=model_config,
                    user_input=user_input,
                    history=history,
                    tools=tools,
                    span=span,
                )
            else:
                # Simple completion mode with Anthropic SDK
                return await self._execute_simple(
                    agent_name=agent_name,
                    system_prompt=system_prompt,
                    model_config=model_config,
                    user_input=user_input,
                    history=history,
                    span=span,
                )

    async def _execute_agentic(
        self,
        agent_name: str,
        system_prompt: str,
        model_config: dict[str, Any],
        user_input: dict[str, Any],
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        span,
    ) -> list[Message]:
        """Execute with full Claude Agent SDK agentic loop."""
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        except ImportError:
            logger.warning("Claude Agent SDK not available, falling back to simple mode")
            return await self._execute_simple(
                agent_name, system_prompt, model_config, user_input, history, span
            )

        model = model_config.get("name", DEFAULT_MODEL)
        max_turns = model_config.get("config", {}).get("max_turns", DEFAULT_MAX_TURNS)

        # Map ARK tools to Claude Agent SDK tool names
        allowed_tools = self._map_tools_to_claude(tools)

        span.set_attribute("agent.max_turns", max_turns)
        span.set_attribute("agent.tools_count", len(allowed_tools))

        # Build the task from user input
        task = user_input.get("content", "")

        # Add conversation context if there's history
        if history:
            context = self._format_history(history)
            task = f"Previous conversation:\n{context}\n\nCurrent request: {task}"

        options = ClaudeAgentOptions(
            model=model,
            max_turns=max_turns,
            allowed_tools=allowed_tools,
            system_prompt=system_prompt if system_prompt else None,
        )

        result_messages = []
        final_content = ""

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(task)
                span.add_event("query_sent")

                async for message in client.receive_response():
                    if hasattr(message, 'type'):
                        if message.type == "text":
                            final_content = message.text
                        elif message.type == "tool_use":
                            span.add_event("tool_call", {"tool": message.name})
                        elif message.type == "result":
                            final_content = message.text if hasattr(message, 'text') else str(message)

            span.set_attribute("agent.status", "success")

            return [Message(
                role="assistant",
                content=final_content or "Task completed.",
                name=agent_name,
            )]

        except Exception as e:
            logger.error(f"Claude Agent SDK execution failed: {e}")
            span.set_attribute("agent.status", "error")
            span.record_exception(e)

            # Fall back to simple mode
            return await self._execute_simple(
                agent_name, system_prompt, model_config, user_input, history, span
            )

    def _get_provider(self, model_config: dict[str, Any]) -> str:
        """Determine the provider from model config or environment."""
        # Check model config first
        provider = model_config.get("type", "").lower()
        if provider in ["bedrock", "aws", "amazon"]:
            return "bedrock"
        if provider in ["anthropic", "claude"]:
            return "anthropic"

        # Check environment variable
        provider_env = os.getenv("CLAUDE_PROVIDER", "").lower()
        if provider_env in ["bedrock", "aws"]:
            return "bedrock"

        # Auto-detect based on available credentials
        if os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"):
            # AWS environment detected, prefer Bedrock
            if not os.getenv("ANTHROPIC_API_KEY"):
                return "bedrock"

        return "anthropic"

    def _get_bedrock_model_id(self, model: str) -> str:
        """Convert model name to Bedrock model ID (using cross-region inference)."""
        # Cross-region inference profile ARNs for us-east-1
        bedrock_models = {
            "claude-sonnet-4-20250514": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "claude-3-5-sonnet": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-5-sonnet-v2": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-sonnet": "us.anthropic.claude-3-sonnet-20240229-v1:0",
            "claude-3-haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
            "claude-3-opus": "us.anthropic.claude-3-opus-20240229-v1:0",
        }
        # If already a Bedrock model ID, return as-is
        if model.startswith("anthropic.") or model.startswith("us."):
            return model
        # Look up mapping
        return bedrock_models.get(model, f"us.anthropic.{model}-v1:0")

    async def _execute_simple(
        self,
        agent_name: str,
        system_prompt: str,
        model_config: dict[str, Any],
        user_input: dict[str, Any],
        history: list[dict[str, Any]],
        span,
    ) -> list[Message]:
        """Execute with Anthropic API or Bedrock (no agentic loop)."""
        model = model_config.get("name", DEFAULT_MODEL)
        provider = self._get_provider(model_config)

        # Build messages
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            if role in ["system"]:
                continue
            anthropic_role = "assistant" if role == "assistant" else "user"
            messages.append({
                "role": anthropic_role,
                "content": msg.get("content", ""),
            })

        messages.append({
            "role": "user",
            "content": user_input.get("content", ""),
        })

        span.set_attribute("agent.provider", provider)

        if provider == "bedrock":
            return await self._execute_bedrock(
                agent_name, system_prompt, model, messages, span
            )
        else:
            return await self._execute_anthropic(
                agent_name, system_prompt, model, messages, span
            )

    async def _execute_bedrock(
        self,
        agent_name: str,
        system_prompt: str,
        model: str,
        messages: list[dict[str, Any]],
        span,
    ) -> list[Message]:
        """Execute using AWS Bedrock."""
        try:
            import boto3
            import json
        except ImportError:
            logger.error("boto3 not installed")
            return [Message(
                role="assistant",
                content="Error: boto3 not available for Bedrock",
                name=agent_name,
            )]

        model_id = self._get_bedrock_model_id(model)
        span.add_event("calling_bedrock_api", {"model_id": model_id})
        logger.info(f"Calling Bedrock with model: {model_id}")

        try:
            region = os.getenv("AWS_REGION", "us-east-1")
            bedrock = boto3.client("bedrock-runtime", region_name=region)

            # Build Bedrock request body
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "system": system_prompt or "You are a helpful assistant.",
                "messages": messages,
            }

            response = bedrock.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )

            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [{}])[0].get("text", "")

            span.set_attribute("agent.status", "success")
            usage = response_body.get("usage", {})
            span.set_attribute("agent.tokens.input", usage.get("input_tokens", 0))
            span.set_attribute("agent.tokens.output", usage.get("output_tokens", 0))

            return [Message(
                role="assistant",
                content=content,
                name=agent_name,
            )]

        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            span.set_attribute("agent.status", "error")
            span.record_exception(e)

            return [Message(
                role="assistant",
                content=f"Error executing agent via Bedrock: {str(e)}",
                name=agent_name,
            )]

    async def _execute_anthropic(
        self,
        agent_name: str,
        system_prompt: str,
        model: str,
        messages: list[dict[str, Any]],
        span,
    ) -> list[Message]:
        """Execute using direct Anthropic API."""
        try:
            import anthropic
        except ImportError:
            logger.error("Anthropic SDK not installed")
            return [Message(
                role="assistant",
                content="Error: Anthropic SDK not available",
                name=agent_name,
            )]

        span.add_event("calling_anthropic_api")

        try:
            client = anthropic.Anthropic()

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt or "You are a helpful assistant.",
                messages=messages,
            )

            content = response.content[0].text if response.content else ""

            span.set_attribute("agent.status", "success")
            span.set_attribute("agent.tokens.input", response.usage.input_tokens)
            span.set_attribute("agent.tokens.output", response.usage.output_tokens)

            return [Message(
                role="assistant",
                content=content,
                name=agent_name,
            )]

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            span.set_attribute("agent.status", "error")
            span.record_exception(e)

            return [Message(
                role="assistant",
                content=f"Error executing agent: {str(e)}",
                name=agent_name,
            )]

    def _map_tools_to_claude(self, ark_tools: list[dict[str, Any]]) -> list[str]:
        """Map ARK tool definitions to Claude Agent SDK tool names."""
        # Claude Agent SDK built-in tools
        claude_tools = {
            "read": "Read",
            "write": "Write",
            "edit": "Edit",
            "bash": "Bash",
            "glob": "Glob",
            "grep": "Grep",
            "web_fetch": "WebFetch",
            "web_search": "WebSearch",
        }

        allowed = []
        for tool in ark_tools:
            tool_name = tool.get("name", "").lower().replace("-", "_").replace(" ", "_")

            # Check if it maps to a Claude Agent SDK built-in tool
            if tool_name in claude_tools:
                allowed.append(claude_tools[tool_name])
            elif tool_name in ["read", "write", "edit", "bash", "glob", "grep"]:
                allowed.append(tool_name.capitalize())

        # Default tools if none mapped
        if not allowed:
            allowed = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

        return allowed

    def _format_history(self, history: list[dict[str, Any]]) -> str:
        """Format conversation history as context string."""
        lines = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role.upper()}: {content}")
        return "\n".join(lines)

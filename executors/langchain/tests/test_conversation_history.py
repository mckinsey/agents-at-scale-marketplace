"""Tests for conversation history management via conversationId."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langchain_executor.executor import LangChainExecutor


def _make_request(conversation_id="conv-1", user_input="hello", use_rag=False):
    """Build a minimal mock request."""
    request = MagicMock()
    request.conversationId = conversation_id
    request.userInput = MagicMock()
    request.userInput.content = user_input
    request.agent.name = "test-agent"
    request.agent.prompt = "You are a helpful assistant."
    request.agent.description = ""
    request.agent.parameters = []
    request.agent.labels = {"langchain": "rag"} if use_rag else {}
    request.agent.model.type = "openai"
    request.agent.model.name = "gpt-4"
    request.agent.model.config = {"openai": {"apiKey": "fake", "properties": {}}}
    return request


@pytest.mark.asyncio
@patch("langchain_executor.executor.create_chat_client")
async def test_new_conversation_creates_history_with_system_prompt(mock_create_client):
    """4.1 - New conversationId gets a ChatMessageHistory with system prompt + user message."""
    mock_client = AsyncMock()
    mock_client.ainvoke.return_value = AIMessage(content="hi there")
    mock_create_client.return_value = mock_client

    executor = LangChainExecutor()
    request = _make_request(conversation_id="new-conv", user_input="hello")

    await executor.execute_agent(request)

    history = executor.history_store["new-conv"]
    messages = history.messages
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "You are a helpful assistant."
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "hello"
    assert isinstance(messages[2], AIMessage)
    assert messages[2].content == "hi there"


@pytest.mark.asyncio
@patch("langchain_executor.executor.create_chat_client")
async def test_existing_conversation_appends_to_history(mock_create_client):
    """4.2 - Subsequent requests with the same conversationId append to existing history."""
    mock_client = AsyncMock()
    mock_client.ainvoke.side_effect = [
        AIMessage(content="first reply"),
        AIMessage(content="second reply"),
    ]
    mock_create_client.return_value = mock_client

    executor = LangChainExecutor()

    # First turn
    await executor.execute_agent(_make_request(conversation_id="conv-A", user_input="turn 1"))
    # Second turn
    await executor.execute_agent(_make_request(conversation_id="conv-A", user_input="turn 2"))

    history = executor.history_store["conv-A"]
    messages = history.messages
    # system, human1, ai1, human2, ai2
    assert len(messages) == 5
    assert isinstance(messages[0], SystemMessage)
    assert messages[1].content == "turn 1"
    assert messages[2].content == "first reply"
    assert messages[3].content == "turn 2"
    assert messages[4].content == "second reply"

    # System prompt should NOT be added again on the second turn
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    assert len(system_messages) == 1


@pytest.mark.asyncio
@patch("langchain_executor.executor.create_chat_client")
@patch("langchain_executor.executor.LangChainExecutor._get_code_context", new_callable=AsyncMock)
async def test_rag_augmented_message_stored_in_history(mock_rag, mock_create_client):
    """4.3 - When RAG is enabled, the augmented message (with code context) is stored in history."""
    mock_rag.return_value = "def foo(): pass"
    mock_client = AsyncMock()
    mock_client.ainvoke.return_value = AIMessage(content="here is the answer")
    mock_create_client.return_value = mock_client

    executor = LangChainExecutor()
    request = _make_request(conversation_id="rag-conv", user_input="explain foo", use_rag=True)

    await executor.execute_agent(request)

    history = executor.history_store["rag-conv"]
    user_msg = history.messages[1]
    assert isinstance(user_msg, HumanMessage)
    assert "RELEVANT CODE CONTEXT" in user_msg.content
    assert "def foo(): pass" in user_msg.content
    assert "explain foo" in user_msg.content

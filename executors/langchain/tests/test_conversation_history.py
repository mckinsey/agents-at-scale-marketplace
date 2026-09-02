"""Tests for conversation history management via conversationId."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage

from langchain_executor.executor import LangChainExecutor


def _streaming_client(*replies):
    """Chat client mock whose astream yields one reply per call, chunk by chunk.

    The executor streams (`astream`) and concatenates chunk.content, writing the
    AIMessage to history only once the stream ends. Setting a return_value on
    ainvoke does nothing: AsyncMock would auto-create astream and return a
    coroutine, which `async for` cannot iterate.
    """
    client = AsyncMock()
    pending = iter(replies)

    async def astream(_messages):
        for chunk in next(pending):
            yield AIMessageChunk(content=chunk)

    client.astream = astream
    return client


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
    # Two chunks, so the test also covers the executor concatenating them.
    mock_create_client.return_value = _streaming_client(["hi ", "there"])

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
    mock_create_client.return_value = _streaming_client(["first reply"], ["second reply"])

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
    mock_create_client.return_value = _streaming_client(["here is the answer"])

    executor = LangChainExecutor()
    request = _make_request(conversation_id="rag-conv", user_input="explain foo", use_rag=True)

    await executor.execute_agent(request)

    history = executor.history_store["rag-conv"]
    user_msg = history.messages[1]
    assert isinstance(user_msg, HumanMessage)
    assert "RELEVANT CODE CONTEXT" in user_msg.content
    assert "def foo(): pass" in user_msg.content
    assert "explain foo" in user_msg.content


# --- _index_code ---


@pytest.mark.asyncio
@patch("langchain_executor.executor.index_code_files")
async def test_index_code_no_chunks_marks_indexed_without_embeddings(mock_index_files):
    mock_index_files.return_value = []

    executor = LangChainExecutor()
    await executor._index_code(model_config=MagicMock())

    assert executor._indexed is True
    assert executor.vector_store is None


@pytest.mark.asyncio
@patch("langchain_executor.executor.create_embeddings_client")
@patch("langchain_executor.executor.index_code_files")
async def test_index_code_embeddings_failure_falls_back(mock_index_files, mock_create_embeddings):
    mock_index_files.return_value = [Document(page_content="x", metadata={})]
    mock_create_embeddings.side_effect = RuntimeError("no credentials")

    executor = LangChainExecutor()
    await executor._index_code(model_config=MagicMock())

    assert executor._indexed is True
    assert executor.vector_store is None


# --- _retrieve_relevant_code ---


def test_retrieve_relevant_code_no_vector_store_returns_chunks():
    executor = LangChainExecutor()
    executor.code_chunks = [Document(page_content=str(i), metadata={}) for i in range(10)]

    result = executor._retrieve_relevant_code("query", k=3)

    assert result == executor.code_chunks[:3]


def test_retrieve_relevant_code_no_vector_store_and_no_chunks():
    executor = LangChainExecutor()

    assert executor._retrieve_relevant_code("query") == []


def test_retrieve_relevant_code_uses_vector_search():
    executor = LangChainExecutor()
    docs = [Document(page_content="hit", metadata={})]
    executor.vector_store = MagicMock()
    executor.vector_store.similarity_search.return_value = docs

    result = executor._retrieve_relevant_code("query", k=5)

    executor.vector_store.similarity_search.assert_called_once_with("query", k=5)
    assert result == docs


def test_retrieve_relevant_code_search_failure_returns_empty():
    executor = LangChainExecutor()
    executor.vector_store = MagicMock()
    executor.vector_store.similarity_search.side_effect = RuntimeError("boom")

    assert executor._retrieve_relevant_code("query") == []


# --- _get_code_context (real implementation, not mocked) ---


@pytest.mark.asyncio
@patch("langchain_executor.executor.create_chat_client")
@patch("langchain_executor.executor.create_vector_store")
@patch("langchain_executor.executor.create_embeddings_client")
@patch("langchain_executor.executor.index_code_files")
async def test_execute_agent_rag_end_to_end_without_mocking_get_code_context(
    mock_index_files, mock_create_embeddings, mock_create_vector_store, mock_create_chat_client
):
    """Exercises _get_code_context -> _index_code -> _retrieve_relevant_code together."""
    doc = Document(page_content="def foo(): pass", metadata={"relative_path": "foo.py"})
    mock_index_files.return_value = [doc]
    mock_vector_store = MagicMock()
    mock_vector_store.similarity_search.return_value = [doc]
    mock_create_vector_store.return_value = mock_vector_store
    mock_create_chat_client.return_value = _streaming_client(["answer"])

    executor = LangChainExecutor()
    request = _make_request(conversation_id="rag-real", user_input="explain foo", use_rag=True)

    await executor.execute_agent(request)

    assert executor._indexed is True
    user_msg = executor.history_store["rag-real"].messages[1]
    assert "## File: foo.py" in user_msg.content
    assert "def foo(): pass" in user_msg.content

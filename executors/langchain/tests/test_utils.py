"""Tests for langchain_executor.utils."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from langchain_executor.utils import (
    build_rag_context,
    create_chat_client,
    create_embeddings_client,
    create_vector_store,
    index_code_files,
    should_use_rag,
)


def _model(model_type, config, name="gpt-4"):
    model = MagicMock()
    model.type = model_type
    model.name = name
    model.config = config
    return model


# --- create_chat_client ---


@patch("langchain_executor.utils.ChatOpenAI")
def test_create_chat_client_openai_minimal(mock_chat_openai):
    model = _model("openai", {"openai": {"apiKey": "sk-1", "properties": {}}})

    create_chat_client(model)

    kwargs = mock_chat_openai.call_args.kwargs
    assert kwargs["model"] == "gpt-4"
    assert kwargs["base_url"] is None
    assert kwargs["temperature"] == 0.7
    assert "max_tokens" not in kwargs


@patch("langchain_executor.utils.ChatOpenAI")
def test_create_chat_client_openai_full_properties(mock_chat_openai):
    model = _model(
        "openai",
        {
            "openai": {
                "apiKey": "sk-1",
                "baseUrl": "https://api.example.com",
                "properties": {
                    "temperature": "0.2",
                    "max_tokens": "512",
                    "top_p": "0.9",
                    "frequency_penalty": "0.1",
                    "presence_penalty": "0.3",
                },
            }
        },
    )

    create_chat_client(model)

    kwargs = mock_chat_openai.call_args.kwargs
    assert kwargs["base_url"] == "https://api.example.com"
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 512
    assert kwargs["top_p"] == 0.9
    assert kwargs["frequency_penalty"] == 0.1
    assert kwargs["presence_penalty"] == 0.3


def test_create_chat_client_openai_missing_api_key():
    model = _model("openai", {"openai": {"properties": {}}})

    with pytest.raises(ValueError, match="OpenAI requires apiKey"):
        create_chat_client(model)


@patch("langchain_executor.utils.ChatOpenAI")
def test_create_chat_client_azure_minimal(mock_chat_openai):
    model = _model(
        "azure",
        {"azure": {"apiKey": "sk-1", "baseUrl": "https://azure.example.com/", "properties": {}}},
        name="my-deployment",
    )

    create_chat_client(model)

    kwargs = mock_chat_openai.call_args.kwargs
    assert kwargs["base_url"] == "https://azure.example.com/openai/deployments/my-deployment/"
    assert kwargs["default_query"] == {}
    assert kwargs["temperature"] == 0.7


@patch("langchain_executor.utils.ChatOpenAI")
def test_create_chat_client_azure_full_properties(mock_chat_openai):
    model = _model(
        "azure",
        {
            "azure": {
                "apiKey": "sk-1",
                "baseUrl": "https://azure.example.com",
                "apiVersion": "2024-05-01",
                "properties": {
                    "temperature": "0.5",
                    "max_tokens": "256",
                    "top_p": "0.8",
                    "frequency_penalty": "0.4",
                    "presence_penalty": "0.6",
                },
            }
        },
        name="my-deployment",
    )

    create_chat_client(model)

    kwargs = mock_chat_openai.call_args.kwargs
    assert kwargs["default_query"] == {"api-version": "2024-05-01"}
    assert kwargs["max_tokens"] == 256
    assert kwargs["top_p"] == 0.8
    assert kwargs["frequency_penalty"] == 0.4
    assert kwargs["presence_penalty"] == 0.6


def test_create_chat_client_azure_missing_credentials():
    model = _model("azure", {"azure": {"properties": {}}})

    with pytest.raises(ValueError, match="Azure OpenAI requires apiKey and baseUrl"):
        create_chat_client(model)


def test_create_chat_client_bedrock_not_implemented():
    model = _model("bedrock", {"bedrock": {}})

    with pytest.raises(NotImplementedError):
        create_chat_client(model)


def test_create_chat_client_unsupported_type():
    model = _model("anthropic", {})

    with pytest.raises(ValueError, match="Unsupported model type: anthropic"):
        create_chat_client(model)


# --- create_embeddings_client ---


@patch("langchain_executor.utils.OpenAIEmbeddings")
def test_create_embeddings_client_openai(mock_embeddings):
    model = _model("openai", {"openai": {"apiKey": "sk-1", "baseUrl": "https://api.example.com"}})

    create_embeddings_client(model)

    kwargs = mock_embeddings.call_args.kwargs
    assert kwargs["model"] == "gpt-4"
    assert kwargs["base_url"] == "https://api.example.com"


@patch("langchain_executor.utils.OpenAIEmbeddings")
def test_create_embeddings_client_openai_overridden_model_name(mock_embeddings):
    model = _model("openai", {"openai": {"apiKey": "sk-1"}})

    create_embeddings_client(model, embeddings_model_name="text-embedding-3-small")

    kwargs = mock_embeddings.call_args.kwargs
    assert kwargs["model"] == "text-embedding-3-small"
    assert kwargs["base_url"] is None


def test_create_embeddings_client_openai_missing_api_key():
    model = _model("openai", {"openai": {}})

    with pytest.raises(ValueError, match="OpenAI requires apiKey"):
        create_embeddings_client(model)


@patch("langchain_executor.utils.OpenAIEmbeddings")
def test_create_embeddings_client_azure(mock_embeddings):
    model = _model(
        "azure",
        {"azure": {"apiKey": "sk-1", "baseUrl": "https://azure.example.com", "apiVersion": "2024-05-01"}},
        name="my-deployment",
    )

    create_embeddings_client(model)

    kwargs = mock_embeddings.call_args.kwargs
    assert kwargs["model"] == "my-deployment"
    assert kwargs["base_url"] == "https://azure.example.com/openai/deployments/my-deployment/"
    assert kwargs["api_version"] == "2024-05-01"


def test_create_embeddings_client_azure_missing_credentials():
    model = _model("azure", {"azure": {}})

    with pytest.raises(ValueError, match="Azure OpenAI requires apiKey and baseUrl"):
        create_embeddings_client(model)


def test_create_embeddings_client_unsupported_type():
    model = _model("bedrock", {})

    with pytest.raises(ValueError, match="Unsupported model type for embeddings: bedrock"):
        create_embeddings_client(model)


# --- should_use_rag ---


def test_should_use_rag_true():
    agent_config = MagicMock()
    agent_config.labels = {"langchain": "rag"}
    assert should_use_rag(agent_config) is True


def test_should_use_rag_false_different_label():
    agent_config = MagicMock()
    agent_config.labels = {"langchain": "other"}
    assert should_use_rag(agent_config) is False


def test_should_use_rag_false_no_labels_attribute():
    agent_config = object()
    assert should_use_rag(agent_config) is False


def test_should_use_rag_false_empty_labels():
    agent_config = MagicMock()
    agent_config.labels = {}
    assert should_use_rag(agent_config) is False


# --- index_code_files ---


def test_index_code_files_reads_python_files_and_skips_cache(tmp_path):
    (tmp_path / "module.py").write_text("def foo():\n    return 1\n")
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "module.cpython-312.pyc.py").write_text("garbage")

    chunks = index_code_files(str(tmp_path))

    assert len(chunks) >= 1
    assert all("__pycache__" not in c.metadata["file_path"] for c in chunks)
    assert any("def foo" in c.page_content for c in chunks)


def test_index_code_files_no_python_files_returns_empty(tmp_path):
    assert index_code_files(str(tmp_path)) == []


def test_index_code_files_unreadable_file_is_skipped(tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def foo(): pass\n")

    with patch("langchain_executor.utils.open", side_effect=OSError("boom")):
        chunks = index_code_files(str(tmp_path))

    assert chunks == []


# --- create_vector_store ---


@patch("langchain_executor.utils.FAISS")
def test_create_vector_store_success(mock_faiss):
    mock_store = MagicMock()
    mock_faiss.from_documents.return_value = mock_store
    chunks = [Document(page_content="x", metadata={})]

    result = create_vector_store(chunks, embeddings=MagicMock())

    assert result is mock_store


@patch("langchain_executor.utils.FAISS")
def test_create_vector_store_failure_returns_none(mock_faiss):
    mock_faiss.from_documents.side_effect = RuntimeError("boom")

    result = create_vector_store([Document(page_content="x", metadata={})], embeddings=MagicMock())

    assert result is None


# --- build_rag_context ---


def test_build_rag_context_empty():
    assert build_rag_context([]) == "No relevant code context found."


def test_build_rag_context_with_docs():
    docs = [
        Document(page_content="print('hi')", metadata={"relative_path": "a.py"}),
        Document(page_content="print('bye')", metadata={}),
    ]

    context = build_rag_context(docs)

    assert "## File: a.py" in context
    assert "## File: unknown" in context
    assert "print('hi')" in context
    assert "print('bye')" in context

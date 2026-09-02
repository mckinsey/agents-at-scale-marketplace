"""Tests for langchain_executor.__main__."""

from unittest.mock import patch

from langchain_executor.__main__ import main


@patch("langchain_executor.__main__.app_instance")
def test_main_uses_env_vars(mock_app_instance, monkeypatch):
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")

    main()

    mock_app_instance.run.assert_called_once_with(host="127.0.0.1", port=9000)


@patch("langchain_executor.__main__.app_instance")
def test_main_uses_defaults_without_env_vars(mock_app_instance, monkeypatch):
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    main()

    mock_app_instance.run.assert_called_once_with(host="0.0.0.0", port=8000)

"""Tests for the uvicorn entrypoint."""

import os
from unittest.mock import MagicMock, patch

from openai_responses_executor.__main__ import main


class TestMain:
    def test_reads_host_and_port_from_env(self):
        fake_app = MagicMock()
        with patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "9001"}, clear=True), \
             patch("openai_responses_executor.__main__.create_app", return_value=fake_app), \
             patch("openai_responses_executor.__main__.uvicorn.run") as mock_run:
            main()

        mock_run.assert_called_once_with(fake_app, host="127.0.0.1", port=9001, access_log=True, log_level="info")

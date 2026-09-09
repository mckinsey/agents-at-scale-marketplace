"""Tests for the per-agent file index persisted on the executor's PVC."""

import json

from openai_responses_executor.file_index import FileIndex


class TestFileIndex:
    def test_add_and_list_for_agent(self, tmp_path):
        index = FileIndex(tmp_path / "file_index.json")
        index.add("agent-a", "file-1")
        index.add("agent-a", "file-2")

        assert index.list_for_agent("agent-a") == ["file-1", "file-2"]

    def test_add_is_idempotent(self, tmp_path):
        index = FileIndex(tmp_path / "file_index.json")
        index.add("agent-a", "file-1")
        index.add("agent-a", "file-1")

        assert index.list_for_agent("agent-a") == ["file-1"]

    def test_remove_last_file_drops_agent_key_from_disk(self, tmp_path):
        path = tmp_path / "file_index.json"
        index = FileIndex(path)
        index.add("agent-a", "file-1")
        index.remove("agent-a", "file-1")

        assert json.loads(path.read_text()) == {}

    def test_prune_to_drops_ids_not_in_known_set(self, tmp_path):
        index = FileIndex(tmp_path / "file_index.json")
        index.add("agent-a", "file-1")
        index.add("agent-a", "file-2")

        survivors = index.prune_to("agent-a", {"file-1"})

        assert survivors == ["file-1"]
        assert index.list_for_agent("agent-a") == ["file-1"]

    def test_load_corrupt_json_falls_back_to_empty_instead_of_raising(self, tmp_path):
        path = tmp_path / "file_index.json"
        path.write_text("not json{{{")
        index = FileIndex(path)

        assert index.list_for_agent("agent-a") == []

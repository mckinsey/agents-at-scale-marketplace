"""Tests for the sandbox pool controller."""

import sys
import os
from unittest.mock import Mock, AsyncMock, patch

import pytest
import kopf
from kubernetes.client.rest import ApiException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_manager():
    manager = Mock()
    manager.custom_api = Mock()
    return manager


class TestGetPoolSandboxes:
    @pytest.mark.asyncio
    async def test_success(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.list_namespaced_custom_object.return_value = {
            "items": [{"metadata": {"name": "pool-1"}}]
        }
        result = await pool.get_pool_sandboxes(mock_manager, "pool", "default")
        assert result == [{"metadata": {"name": "pool-1"}}]

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.list_namespaced_custom_object.side_effect = ApiException(status=500)
        result = await pool.get_pool_sandboxes(mock_manager, "pool", "default")
        assert result == []


class TestCreateWarmSandbox:
    @pytest.mark.asyncio
    async def test_no_template_name(self, mock_manager):
        from controller import pool

        result = await pool.create_warm_sandbox(mock_manager, "pool", "default", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_template_not_found(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.get_namespaced_custom_object.side_effect = ApiException(status=404)
        result = await pool.create_warm_sandbox(mock_manager, "pool", "default", {"name": "tmpl"})
        assert result is None

    @pytest.mark.asyncio
    async def test_success(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.get_namespaced_custom_object.return_value = {
            "spec": {"image": "python:3.12-slim", "ttlMinutes": 60}
        }
        result = await pool.create_warm_sandbox(mock_manager, "pool", "default", {"name": "tmpl"})
        assert result is not None
        assert result.startswith("pool-")
        mock_manager.custom_api.create_namespaced_custom_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure_returns_none(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.get_namespaced_custom_object.return_value = {"spec": {}}
        mock_manager.custom_api.create_namespaced_custom_object.side_effect = ApiException(status=500)
        result = await pool.create_warm_sandbox(mock_manager, "pool", "default", {"name": "tmpl"})
        assert result is None


class TestCountSandboxesByState:
    def test_mixed_states(self):
        from controller import pool

        sandboxes = [
            {"metadata": {"labels": {"ark.mckinsey.com/claimed": "true"}}, "status": {"phase": "Running"}},
            {"metadata": {"labels": {}}, "status": {"phase": "Running"}},
            {"metadata": {"labels": {}}, "status": {"phase": "Pending"}},
        ]
        counts = pool.count_sandboxes_by_state(sandboxes)
        assert counts == {"ready_count": 1, "claimed_count": 1}

    def test_empty(self):
        from controller import pool

        assert pool.count_sandboxes_by_state([]) == {"ready_count": 0, "claimed_count": 0}


class TestPoolCreated:
    @pytest.mark.asyncio
    async def test_no_template_ref_raises(self, mock_manager):
        from controller import pool

        patch_obj = kopf.Patch()
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with pytest.raises(kopf.PermanentError):
                await pool.pool_created(
                    spec={"minSize": 0}, name="pool", namespace="default", patch=patch_obj,
                )

    @pytest.mark.asyncio
    async def test_success_with_min_size(self, mock_manager):
        from controller import pool

        patch_obj = kopf.Patch()
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.create_warm_sandbox", AsyncMock(side_effect=["s1", "s2"])):
                result = await pool.pool_created(
                    spec={"minSize": 2, "templateRef": {"name": "tmpl"}},
                    name="pool", namespace="default", patch=patch_obj,
                )
        assert result == {"created": 2}
        assert patch_obj.status["sandboxes"] == ["s1", "s2"]

    @pytest.mark.asyncio
    async def test_partial_creation_failure(self, mock_manager):
        from controller import pool

        patch_obj = kopf.Patch()
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.create_warm_sandbox", AsyncMock(side_effect=["s1", None])):
                result = await pool.pool_created(
                    spec={"minSize": 2, "templateRef": {"name": "tmpl"}},
                    name="pool", namespace="default", patch=patch_obj,
                )
        assert result == {"created": 1}


class TestPoolTimer:
    @pytest.mark.asyncio
    async def test_no_replenishment_needed(self, mock_manager):
        from controller import pool

        patch_obj = kopf.Patch()
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.get_pool_sandboxes", AsyncMock(return_value=[
                {"metadata": {"name": "s1", "labels": {}}, "status": {"phase": "Running"}},
            ])):
                with patch("controller.pool.create_warm_sandbox", AsyncMock()) as create_mock:
                    await pool.pool_timer(
                        spec={"minSize": 1, "templateRef": {"name": "tmpl"}},
                        status={}, name="pool", namespace="default", patch=patch_obj,
                    )
        create_mock.assert_not_called()
        assert patch_obj.status["readyCount"] == 1

    @pytest.mark.asyncio
    async def test_creates_more_when_below_min(self, mock_manager):
        from controller import pool

        patch_obj = kopf.Patch()
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.get_pool_sandboxes", AsyncMock(return_value=[])):
                with patch("controller.pool.create_warm_sandbox", AsyncMock()) as create_mock:
                    await pool.pool_timer(
                        spec={"minSize": 2, "templateRef": {"name": "tmpl"}},
                        status={}, name="pool", namespace="default", patch=patch_obj,
                    )
        assert create_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_respects_max_size_default(self, mock_manager):
        from controller import pool

        patch_obj = kopf.Patch()
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.get_pool_sandboxes", AsyncMock(return_value=[
                {"metadata": {"name": f"s{i}", "labels": {}}, "status": {"phase": "Pending"}}
                for i in range(4)
            ])):
                with patch("controller.pool.create_warm_sandbox", AsyncMock()) as create_mock:
                    await pool.pool_timer(
                        spec={"minSize": 2}, status={}, name="pool", namespace="default", patch=patch_obj,
                    )
        create_mock.assert_not_called()


class TestPoolDeleted:
    @pytest.mark.asyncio
    async def test_deletes_all_sandboxes(self, mock_manager):
        from controller import pool

        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.get_pool_sandboxes", AsyncMock(return_value=[
                {"metadata": {"name": "s1"}},
                {"metadata": {"name": "s2"}},
            ])):
                await pool.pool_deleted(name="pool", namespace="default", status={})
        assert mock_manager.custom_api.delete_namespaced_custom_object.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_404_is_ignored(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.delete_namespaced_custom_object.side_effect = ApiException(status=404)
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.get_pool_sandboxes", AsyncMock(return_value=[
                {"metadata": {"name": "s1"}},
            ])):
                await pool.pool_deleted(name="pool", namespace="default", status={})

    @pytest.mark.asyncio
    async def test_delete_other_error_is_logged(self, mock_manager):
        from controller import pool

        mock_manager.custom_api.delete_namespaced_custom_object.side_effect = ApiException(status=500)
        with patch("controller.pool.get_manager", return_value=mock_manager):
            with patch("controller.pool.get_pool_sandboxes", AsyncMock(return_value=[
                {"metadata": {"name": "s1"}},
            ])):
                await pool.pool_deleted(name="pool", namespace="default", status={})


class TestSandboxEvent:
    @pytest.mark.asyncio
    async def test_no_pool_label_returns_early(self):
        from controller import pool

        await pool.sandbox_event(event={"type": "MODIFIED"}, name="s1", namespace="default", labels={})

    @pytest.mark.asyncio
    async def test_irrelevant_event_type_ignored(self):
        from controller import pool

        await pool.sandbox_event(
            event={"type": "ADDED"}, name="s1", namespace="default",
            labels={"ark.mckinsey.com/pool": "pool"},
        )

    @pytest.mark.asyncio
    async def test_modified_without_claim_ignored(self):
        from controller import pool

        await pool.sandbox_event(
            event={"type": "MODIFIED", "object": {"metadata": {"labels": {}}}},
            name="s1", namespace="default", labels={"ark.mckinsey.com/pool": "pool"},
        )

    @pytest.mark.asyncio
    async def test_modified_with_claim_logged(self):
        from controller import pool

        await pool.sandbox_event(
            event={
                "type": "MODIFIED",
                "object": {"metadata": {"labels": {"ark.mckinsey.com/claimed": "true"}}},
            },
            name="s1", namespace="default", labels={"ark.mckinsey.com/pool": "pool"},
        )

    @pytest.mark.asyncio
    async def test_deleted_event_logged(self):
        from controller import pool

        await pool.sandbox_event(
            event={"type": "DELETED"}, name="s1", namespace="default",
            labels={"ark.mckinsey.com/pool": "pool"},
        )

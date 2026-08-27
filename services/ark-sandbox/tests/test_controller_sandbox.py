"""Tests for the sandbox controller."""

import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

import pytest
import kopf
from kubernetes.client.rest import ApiException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_manager():
    manager = Mock()
    manager.custom_api = Mock()
    manager.create_pod = AsyncMock()
    manager.get_pod_status = AsyncMock()
    manager.get_pod_ip = AsyncMock()
    manager.delete_pod = AsyncMock()
    return manager


class TestSandboxCreated:
    @pytest.mark.asyncio
    async def test_create_without_template(self, mock_manager):
        from controller import sandbox

        mock_pod = Mock()
        mock_pod.metadata.name = "test-sandbox"
        mock_manager.create_pod.return_value = mock_pod

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            result = await sandbox.sandbox_created(
                spec={"image": "python:3.12-slim", "ttlMinutes": 60},
                name="test-sandbox",
                namespace="default",
                uid="uid-1",
                patch=patch_obj,
            )

        assert result == {"pod_name": "test-sandbox"}
        assert patch_obj.status["phase"] == "Pending"
        assert patch_obj.status["podName"] == "test-sandbox"
        mock_manager.create_pod.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_template_not_found(self, mock_manager):
        from controller import sandbox

        mock_manager.custom_api.get_namespaced_custom_object.side_effect = ApiException(status=404)
        mock_pod = Mock()
        mock_pod.metadata.name = "test-sandbox"
        mock_manager.create_pod.return_value = mock_pod

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            result = await sandbox.sandbox_created(
                spec={"templateRef": {"name": "missing-template"}},
                name="test-sandbox",
                namespace="default",
                uid="uid-1",
                patch=patch_obj,
            )

        assert result == {"pod_name": "test-sandbox"}

    @pytest.mark.asyncio
    async def test_create_with_template_other_error(self, mock_manager):
        from controller import sandbox

        mock_manager.custom_api.get_namespaced_custom_object.side_effect = ApiException(status=500, reason="boom")

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            with pytest.raises(ApiException):
                await sandbox.sandbox_created(
                    spec={"templateRef": {"name": "broken-template"}},
                    name="test-sandbox",
                    namespace="default",
                    uid="uid-1",
                    patch=patch_obj,
                )

    @pytest.mark.asyncio
    async def test_create_with_template_found(self, mock_manager):
        from controller import sandbox

        mock_manager.custom_api.get_namespaced_custom_object.return_value = {
            "spec": {"image": "node:20-slim", "ttlMinutes": 30},
        }
        mock_pod = Mock()
        mock_pod.metadata.name = "test-sandbox"
        mock_manager.create_pod.return_value = mock_pod

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_created(
                spec={"templateRef": {"name": "node-template"}},
                name="test-sandbox",
                namespace="default",
                uid="uid-1",
                patch=patch_obj,
            )

        assert mock_manager.create_pod.call_args.kwargs["image"] == "node:20-slim"

    @pytest.mark.asyncio
    async def test_create_pod_already_exists(self, mock_manager):
        from controller import sandbox

        mock_manager.create_pod.side_effect = ApiException(status=409)

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            result = await sandbox.sandbox_created(
                spec={},
                name="test-sandbox",
                namespace="default",
                uid="uid-1",
                patch=patch_obj,
            )

        assert result == {"pod_name": "test-sandbox"}
        assert patch_obj.status["phase"] == "Pending"

    @pytest.mark.asyncio
    async def test_create_pod_other_api_error(self, mock_manager):
        from controller import sandbox

        mock_manager.create_pod.side_effect = ApiException(status=500, reason="boom")

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            with pytest.raises(kopf.PermanentError):
                await sandbox.sandbox_created(
                    spec={},
                    name="test-sandbox",
                    namespace="default",
                    uid="uid-1",
                    patch=patch_obj,
                )

        assert patch_obj.status["phase"] == "Terminated"

    @pytest.mark.asyncio
    async def test_create_pod_generic_error(self, mock_manager):
        from controller import sandbox

        mock_manager.create_pod.side_effect = RuntimeError("boom")

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            with pytest.raises(kopf.PermanentError):
                await sandbox.sandbox_created(
                    spec={},
                    name="test-sandbox",
                    namespace="default",
                    uid="uid-1",
                    patch=patch_obj,
                )

        assert patch_obj.status["phase"] == "Terminated"


class TestSandboxPvcUpdated:
    @pytest.mark.asyncio
    async def test_noop_when_unchanged(self, mock_manager):
        from controller import sandbox

        patch_obj = kopf.Patch()
        result = await sandbox.sandbox_pvc_updated(
            spec={}, status={}, name="test-sandbox", namespace="default",
            old="data", new="data", patch=patch_obj,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_pvc_change_on_running_sandbox_logs_warning(self, mock_manager):
        from controller import sandbox

        patch_obj = kopf.Patch()
        await sandbox.sandbox_pvc_updated(
            spec={}, status={"phase": "Running"}, name="test-sandbox", namespace="default",
            old=None, new="data", patch=patch_obj,
        )

    @pytest.mark.asyncio
    async def test_pvc_change_on_non_running_sandbox(self, mock_manager):
        from controller import sandbox

        patch_obj = kopf.Patch()
        await sandbox.sandbox_pvc_updated(
            spec={}, status={"phase": "Pending"}, name="test-sandbox", namespace="default",
            old=None, new="data", patch=patch_obj,
        )


class TestSandboxTimer:
    @pytest.mark.asyncio
    async def test_no_pod_name_returns_early(self, mock_manager):
        from controller import sandbox

        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Pending"}, name="test-sandbox", namespace="default", patch=patch_obj,
            )
        mock_manager.get_pod_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_pod_deleted_marks_terminated(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.return_value = None
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Running", "podName": "pod-1"}, name="test-sandbox",
                namespace="default", patch=patch_obj,
            )
        assert patch_obj.status["phase"] == "Terminated"

    @pytest.mark.asyncio
    async def test_pod_already_terminated_no_duplicate_patch(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.return_value = None
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Terminated", "podName": "pod-1"}, name="test-sandbox",
                namespace="default", patch=patch_obj,
            )
        assert "phase" not in patch_obj.status

    @pytest.mark.asyncio
    async def test_pending_to_running_transition(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.return_value = "Running"
        mock_manager.get_pod_ip.return_value = "10.0.0.5"
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Pending", "podName": "pod-1"}, name="test-sandbox",
                namespace="default", patch=patch_obj,
            )
        assert patch_obj.status["phase"] == "Running"
        assert patch_obj.status["podIP"] == "10.0.0.5"

    @pytest.mark.asyncio
    async def test_pod_failed_marks_terminated(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.return_value = "Failed"
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Running", "podName": "pod-1"}, name="test-sandbox",
                namespace="default", patch=patch_obj,
            )
        assert patch_obj.status["phase"] == "Terminated"

    @pytest.mark.asyncio
    async def test_ttl_expired_marks_terminated(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.return_value = "Running"
        expired = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Running", "podName": "pod-1", "expiresAt": expired},
                name="test-sandbox", namespace="default", patch=patch_obj,
            )
        assert patch_obj.status["phase"] == "Terminated"
        assert patch_obj.status["message"] == "TTL expired"

    @pytest.mark.asyncio
    async def test_ttl_not_expired_no_change(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.return_value = "Running"
        future = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Running", "podName": "pod-1", "expiresAt": future},
                name="test-sandbox", namespace="default", patch=patch_obj,
            )
        assert "phase" not in patch_obj.status

    @pytest.mark.asyncio
    async def test_pod_status_check_error_is_caught(self, mock_manager):
        from controller import sandbox

        mock_manager.get_pod_status.side_effect = RuntimeError("boom")
        patch_obj = kopf.Patch()
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_timer(
                spec={}, status={"phase": "Running", "podName": "pod-1"}, name="test-sandbox",
                namespace="default", patch=patch_obj,
            )


class TestSandboxPhaseChanged:
    @pytest.mark.asyncio
    async def test_noop_when_unchanged(self, mock_manager):
        from controller import sandbox

        result = await sandbox.sandbox_phase_changed(
            old="Running", new="Running", name="test-sandbox", namespace="default", status={},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_terminated_deletes_pod(self, mock_manager):
        from controller import sandbox

        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_phase_changed(
                old="Running", new="Terminated", name="test-sandbox", namespace="default",
                status={"podName": "pod-1"},
            )
        mock_manager.delete_pod.assert_called_once_with("pod-1", "default")

    @pytest.mark.asyncio
    async def test_terminated_without_pod_name(self, mock_manager):
        from controller import sandbox

        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_phase_changed(
                old="Running", new="Terminated", name="test-sandbox", namespace="default", status={},
            )
        mock_manager.delete_pod.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_pod_failure_is_caught(self, mock_manager):
        from controller import sandbox

        mock_manager.delete_pod.side_effect = RuntimeError("boom")
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_phase_changed(
                old="Running", new="Terminated", name="test-sandbox", namespace="default",
                status={"podName": "pod-1"},
            )


class TestSandboxDeleted:
    @pytest.mark.asyncio
    async def test_deletes_pod_when_present(self, mock_manager):
        from controller import sandbox

        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_deleted(name="test-sandbox", namespace="default", status={"podName": "pod-1"})
        mock_manager.delete_pod.assert_called_once_with("pod-1", "default")

    @pytest.mark.asyncio
    async def test_no_pod_name_skips_delete(self, mock_manager):
        from controller import sandbox

        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_deleted(name="test-sandbox", namespace="default", status={})
        mock_manager.delete_pod.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_pod_failure_is_caught(self, mock_manager):
        from controller import sandbox

        mock_manager.delete_pod.side_effect = RuntimeError("boom")
        with patch("controller.sandbox.get_manager", return_value=mock_manager):
            await sandbox.sandbox_deleted(name="test-sandbox", namespace="default", status={"podName": "pod-1"})

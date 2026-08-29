from unittest.mock import MagicMock

import pytest
from proxmoxer.core import ResourceException
from waldur_site_agent.backend.exceptions import BackendError

from waldur_site_agent_proxmox.client import ProxmoxClient

UUID = "12345678-1234-5678-1234-567812345678"
UPID = "UPID:pve:00000001:00000002:00000003:qmclone:101:root@pam:"


def make_client(**kwargs):
    api = kwargs.pop("api", MagicMock())
    return ProxmoxClient(
        host="pve.example",
        user="agent@pve",
        token_name="waldur",
        token_value="top-secret",
        node="pve",
        template_vmid=9000,
        api=api,
        sleep=lambda _: None,
        **kwargs,
    )


def test_repr_redacts_token():
    client = make_client()
    assert "top-secret" not in repr(client)
    assert "redacted" in repr(client)


def test_marker_lookup_is_exact_and_adopts_before_create():
    client = make_client()
    marker = client.marker(UUID)
    client._cluster_vms = MagicMock(
        return_value=[
            {"vmid": 101, "tags": marker + "-not-exact"},
            {"vmid": 102, "tags": "other;" + marker},
        ]
    )
    assert client.provision_vm(UUID, "resource") == "102"
    client.api.cluster.nextid.get.assert_not_called()


def test_atomic_clone_label_is_adopted_after_tagging_crash():
    client = make_client()
    client._cluster_vms = MagicMock(return_value=[{"vmid": 103, "node": "pve"}])
    client.api.nodes.return_value.qemu.return_value.config.get.return_value = {
        "description": client.label(UUID)
    }
    assert client.provision_vm(UUID, "resource") == "103"
    client.api.cluster.nextid.get.assert_not_called()


def test_duplicate_markers_are_visible_error():
    client = make_client()
    marker = client.marker(UUID)
    client._cluster_vms = MagicMock(
        return_value=[{"vmid": 101, "tags": marker}, {"vmid": 102, "tags": marker}]
    )
    with pytest.raises(BackendError, match="Multiple"):
        client.find_by_waldur_uuid(UUID)


def test_nextid_collision_is_retried():
    client = make_client(allocation_retries=2)
    client.find_by_waldur_uuid = MagicMock(return_value=None)
    client.api.cluster.nextid.get.side_effect = [101, 102]
    client._find_vm = MagicMock(
        side_effect=[{"vmid": 101}, None, {"vmid": 102, "status": "stopped"}]
    )
    client.api.nodes.return_value.qemu.return_value.clone.post.return_value = UPID
    client.wait_for_task = MagicMock()
    client._set_marker = MagicMock()
    assert client.provision_vm(UUID, "resource") == "102"
    assert client.api.cluster.nextid.get.call_count == 2


def test_wait_for_task_requires_ok():
    client = make_client()
    client.api.nodes.return_value.tasks.return_value.status.get.return_value = {
        "status": "stopped",
        "exitstatus": "ERROR",
    }
    with pytest.raises(BackendError, match="ERROR"):
        client.wait_for_task(UPID)


def test_wait_for_task_is_bounded():
    ticks = iter([0.0, 0.0, 2.0])
    client = make_client(timeout=1, monotonic=lambda: next(ticks))
    client.api.nodes.return_value.tasks.return_value.status.get.return_value = {"status": "running"}
    with pytest.raises(BackendError, match="Timed out"):
        client.wait_for_task(UPID)


def test_delete_missing_vm_is_success():
    client = make_client()
    client._find_vm = MagicMock(return_value=None)
    client.delete_vm(404)


def test_delete_racing_404_is_success():
    client = make_client()
    client._find_vm = MagicMock(return_value={"vmid": 101, "node": "pve"})
    client.api.nodes.return_value.qemu.return_value.delete.side_effect = ResourceException(
        404, "Not Found", "missing"
    )
    client.delete_vm(101)


def test_provider_exception_becomes_backend_error():
    client = make_client()
    client.api.cluster.resources.get.side_effect = ResourceException(500, "Error", "failed")
    with pytest.raises(BackendError, match="VM listing"):
        client.list_resources()


def test_membership_write_is_explicitly_unsupported():
    client = make_client()
    with pytest.raises(BackendError, match="not implemented"):
        client.create_association("alice", "101")

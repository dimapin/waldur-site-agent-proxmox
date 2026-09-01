from unittest.mock import MagicMock, call

import pytest
import requests
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


def test_provision_performs_only_one_initial_adoption_lookup():
    client = make_client()
    client.find_by_waldur_uuid = MagicMock(return_value={"vmid": 102})

    assert client.provision_vm(UUID, "resource") == "102"
    client.find_by_waldur_uuid.assert_called_once_with(UUID)


def test_complete_unrelated_description_skips_config_lookup():
    client = make_client()
    client._cluster_vms = MagicMock(
        return_value=[{"vmid": 103, "node": "pve", "description": "unrelated VM"}]
    )

    assert client.find_by_waldur_uuid(UUID) is None
    client.api.nodes.assert_not_called()


def test_truncated_marker_description_falls_back_to_config():
    client = make_client()
    label = client.label(UUID)
    client._cluster_vms = MagicMock(
        return_value=[{"vmid": 103, "node": "pve", "description": label[:20]}]
    )
    client.api.nodes.return_value.qemu.return_value.config.get.return_value = {"description": label}

    assert client.find_by_waldur_uuid(UUID) == {
        "vmid": 103,
        "node": "pve",
        "description": label[:20],
    }
    client.api.nodes.return_value.qemu.return_value.config.get.assert_called_once_with()


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


def test_set_marker_uses_vm_node_from_public_lookup():
    client = make_client()
    client.get_vm = MagicMock(return_value={"vmid": 101, "node": "pve-b"})
    config = client.api.nodes.return_value.qemu.return_value.config
    config.get.return_value = {"tags": "existing"}
    config.put.return_value = UPID
    client._poll_result = MagicMock()

    client._set_marker(101, UUID)

    client.get_vm.assert_called_once_with(101)
    assert client.api.nodes.call_args_list == [call("pve-b"), call("pve-b")]
    config.put.assert_called_once_with(tags=f"existing;{client.marker(UUID)}")
    client._poll_result.assert_called_once_with(UPID)


def test_nextid_collision_is_retried():
    client = make_client(allocation_retries=2)
    client.find_by_waldur_uuid = MagicMock(return_value=None)
    client.api.cluster.nextid.get.side_effect = [101, 102]
    client.get_vm = MagicMock(side_effect=[{"vmid": 101}, None, {"vmid": 102, "status": "stopped"}])
    client.api.nodes.return_value.qemu.return_value.clone.post.return_value = UPID
    client.wait_for_task = MagicMock()
    client._set_marker = MagicMock()
    assert client.provision_vm(UUID, "resource") == "102"
    assert client.api.cluster.nextid.get.call_count == 2


def test_wait_for_task_rides_out_dropped_connection():
    """pveproxy recycles workers mid-clone; the task keeps running server-side.

    Aborting here would erred an order whose clone actually succeeded and leave
    an untagged VM behind -- exactly the orphan this guards against.
    """
    client = make_client()
    ssl_eof = requests.exceptions.SSLError("TLS/SSL connection has been closed (EOF)")
    client.api.nodes.return_value.tasks.return_value.status.get.side_effect = [
        ssl_eof,
        ssl_eof,
        {"status": "stopped", "exitstatus": "OK"},
    ]

    assert client.wait_for_task(UPID)["exitstatus"] == "OK"
    assert client.api.nodes.return_value.tasks.return_value.status.get.call_count == 3


def test_wait_for_task_still_fails_on_rejected_request():
    """A 403 is a verdict, not a lost connection -- it must not be retried."""
    client = make_client()
    client.api.nodes.return_value.tasks.return_value.status.get.side_effect = ResourceException(
        403, "Forbidden", "Permission check failed"
    )
    with pytest.raises(BackendError, match="task status failed"):
        client.wait_for_task(UPID)


def test_wait_for_task_dropped_connection_is_bounded():
    """Retrying is bounded by the same deadline as ordinary polling."""
    clock = iter([0, 0, 10, 400, 400, 400])
    client = make_client(timeout=300, monotonic=lambda: next(clock))
    client.api.nodes.return_value.tasks.return_value.status.get.side_effect = (
        requests.exceptions.ConnectionError("connection reset")
    )
    with pytest.raises(BackendError, match="task status failed"):
        client.wait_for_task(UPID)


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
    client.get_vm = MagicMock(return_value=None)
    client.delete_vm(404)


def test_base_client_delete_name_is_treated_as_vmid():
    client = make_client()
    client.delete_vm = MagicMock()

    assert client.delete_resource("101") == "101"
    client.delete_vm.assert_called_once_with("101")


def test_set_resource_limits_returns_none_after_polling():
    client = make_client()
    client.get_vm = MagicMock(return_value={"vmid": 101, "node": "pve"})
    config = client.api.nodes.return_value.qemu.return_value.config
    config.put.return_value = UPID
    client._poll_result = MagicMock()

    assert client.set_resource_limits("101", {"cores": 4, "memory": 8192}) is None
    config.put.assert_called_once_with(cores=4, memory=8192)
    client._poll_result.assert_called_once_with(UPID)


def test_delete_racing_404_is_success():
    client = make_client()
    client.get_vm = MagicMock(return_value={"vmid": 101, "node": "pve"})
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

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from waldur_api_client.models.resource_limits import ResourceLimits
from waldur_site_agent.backend.exceptions import BackendError, ConfigurationError

from waldur_site_agent_proxmox.backend import ProxmoxBackend, ProxmoxBackendSettings

SETTINGS = {
    "host": "pve.example",
    "user": "agent@pve",
    "token_name": "waldur",
    "token_value": "secret-value",
    "node": "pve-a",
    "template_vmid": 9000,
}


def test_settings_require_provider_configuration():
    with pytest.raises(ValidationError):
        ProxmoxBackendSettings.model_validate({})


def test_settings_repr_redacts_secret():
    settings = ProxmoxBackendSettings.model_validate(SETTINGS)
    assert "secret-value" not in repr(settings)
    assert "**********" in repr(settings)


def test_backend_rejects_invalid_config_without_secret_in_error():
    invalid = dict(SETTINGS, node="", token_value="must-not-leak")
    with pytest.raises(ConfigurationError) as caught:
        ProxmoxBackend(invalid, {})
    assert "must-not-leak" not in str(caught.value)


@pytest.mark.parametrize(
    "resource",
    [SimpleNamespace(slug="", name=""), SimpleNamespace(slug="", name="", uuid="invalid")],
)
def test_name_fallback_rejects_missing_or_invalid_uuid(resource):
    with pytest.raises(BackendError, match="UUID is invalid"):
        ProxmoxBackend._name(resource)


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_create_returns_confirmed_backend_id(client_class):
    client = client_class.return_value
    client.provision_vm.return_value = "123"
    backend = ProxmoxBackend(
        SETTINGS, {"cores": {"label": "Cores", "measured_unit": "cores", "unit_factor": 2}}
    )
    resource = SimpleNamespace(
        uuid="12345678-1234-5678-1234-567812345678",
        slug="resource",
        name="Resource",
        limits={"cores": 4},
    )
    info = backend.create_resource(resource)
    assert info.backend_id == "123"
    assert info.backend_metadata == {}
    assert info.limits == {"cores": 4}
    client.set_resource_limits.assert_called_once_with("123", {"cores": 8})


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_create_with_id_ignores_core_backend_id_and_uses_uuid(client_class):
    """The processor calls create_resource_with_id with a slug-derived ID.

    That ID must not reach provision_vm: it is not a UUID, so the marker lookup
    would raise "badly formed hexadecimal UUID string" and no VM would ever be
    cloned. The VMID is assigned by Proxmox and comes back from the client.
    """
    client = client_class.return_value
    client.provision_vm.return_value = "456"
    backend = ProxmoxBackend(SETTINGS, {})
    resource = SimpleNamespace(
        uuid="12345678-1234-5678-1234-567812345678", slug="resource", name="Resource"
    )

    info = backend.create_resource_with_id(resource, "resource-slug-42")

    assert info.backend_id == "456"
    client.provision_vm.assert_called_once_with("12345678-1234-5678-1234-567812345678", "resource")


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_collect_limits_accepts_api_client_resource_limits(client_class):
    """Waldur hands over a ResourceLimits attrs object, not a dict.

    It exposes to_dict()/__getitem__ but no items(); calling items() on it
    raised AttributeError and failed the whole create order.
    """
    del client_class
    limits = ResourceLimits.from_dict({"cores": 4, "memory": 2048, "gpu": 1})
    backend = ProxmoxBackend(SETTINGS, {})

    backend_limits, waldur_limits = backend._collect_resource_limits(SimpleNamespace(limits=limits))

    # gpu is not supported by the Proxmox client and must be dropped.
    assert waldur_limits == {"cores": 4, "memory": 2048}
    assert backend_limits == {"cores": 4, "memory": 2048}


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
@pytest.mark.parametrize("empty", [None, {}, ResourceLimits.from_dict({})])
def test_collect_limits_tolerates_missing_limits(client_class, empty):
    del client_class
    backend = ProxmoxBackend(SETTINGS, {})
    assert backend._collect_resource_limits(SimpleNamespace(limits=empty)) == ({}, {})


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_collect_limits_rejects_unknown_payload(client_class):
    del client_class
    backend = ProxmoxBackend(SETTINGS, {})
    with pytest.raises(BackendError, match="Unsupported Waldur limits payload"):
        backend._collect_resource_limits(SimpleNamespace(limits="cores=4"))


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_backend_uses_public_client_healthcheck(client_class):
    client = client_class.return_value
    client.ping.return_value = True
    backend = ProxmoxBackend(SETTINGS, {})

    assert backend.ping() is True
    client.ping.assert_called_once_with()


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_metadata_uses_public_client_vm_lookup(client_class):
    client = client_class.return_value
    client.get_vm.return_value = {"vmid": 123, "status": "running", "extra": "ignored"}
    backend = ProxmoxBackend(SETTINGS, {})

    assert backend.get_resource_metadata("123") == {"vmid": 123, "status": "running"}
    client.get_vm.assert_called_once_with("123")


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_terminate_delegates_and_empty_id_is_noop(client_class):
    client = client_class.return_value
    client.get_resource.return_value = SimpleNamespace()
    backend = ProxmoxBackend(SETTINGS, {})
    assert backend.delete_resource(SimpleNamespace(backend_id="123")) is None
    client.delete_resource.assert_called_once_with("123")
    client.reset_mock()
    backend.delete_resource(SimpleNamespace(backend_id=""))
    client.delete_resource.assert_not_called()


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_terminate_honors_soft_delete(client_class):
    client = client_class.return_value
    client.get_resource.return_value = SimpleNamespace()
    backend = ProxmoxBackend(
        dict(SETTINGS, soft_delete=True),
        {"cores": {"unit_factor": 1}, "memory": {"unit_factor": 1}},
    )
    assert "soft_delete" not in client_class.call_args.kwargs

    assert backend.delete_resource(SimpleNamespace(backend_id="123")) is None
    client.set_resource_limits.assert_called_once_with("123", {"cores": 0, "memory": 0})
    client.delete_resource.assert_not_called()


@patch("waldur_site_agent_proxmox.backend.ProxmoxClient")
def test_pause_and_restore_wait_through_client(client_class):
    client = client_class.return_value
    backend = ProxmoxBackend(SETTINGS, {})
    assert backend.pause_resource("123") is True
    assert backend.restore_resource("123") is True
    client.stop_vm.assert_called_once_with("123")
    client.start_vm.assert_called_once_with("123")

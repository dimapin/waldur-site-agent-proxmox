from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from pydantic import Field, SecretStr, ValidationError
from waldur_site_agent.backend.backends import BaseBackend
from waldur_site_agent.backend.exceptions import BackendError, ConfigurationError
from waldur_site_agent.backend.structures import BackendResourceInfo
from waldur_site_agent.common.plugin_schemas import PluginBackendSettingsSchema

from .client import ProxmoxClient


class ProxmoxBackendSettings(PluginBackendSettingsSchema):
    host: str = Field(min_length=1)
    user: str = Field(min_length=1)
    token_name: str = Field(min_length=1)
    token_value: SecretStr
    node: str = Field(min_length=1)
    template_vmid: int = Field(gt=0)
    verify_ssl: bool = True
    timeout: float = Field(default=300, gt=0)
    polling_interval: float = Field(default=1, gt=0)
    allocation_retries: int = Field(default=5, ge=1, le=100)
    storage: Optional[str] = None
    pool: Optional[str] = None
    full_clone: bool = True
    start_after_create: bool = False
    soft_delete: bool = False


class ProxmoxBackend(BaseBackend):
    supports_cycle_preflight = True

    def __init__(self, backend_settings: dict, backend_components: dict[str, dict]) -> None:
        super().__init__(backend_settings, backend_components)
        self.backend_type = "proxmox"
        try:
            settings = ProxmoxBackendSettings.model_validate(backend_settings)
        except ValidationError as exc:
            details = exc.errors(include_input=False, include_url=False)
            raise ConfigurationError(f"Invalid Proxmox backend settings: {details}") from exc
        values = settings.model_dump(exclude={"soft_delete"})
        values["token_value"] = settings.token_value.get_secret_value()
        self.client = ProxmoxClient(**values)

    @staticmethod
    def _name(waldur_resource: object) -> str:
        raw = str(getattr(waldur_resource, "slug", "") or getattr(waldur_resource, "name", ""))
        value = re.sub(r"[^a-zA-Z0-9-]+", "-", raw).strip("-").lower()
        if value:
            return value[:63].rstrip("-")
        try:
            resource_uuid = uuid.UUID(str(getattr(waldur_resource, "uuid", "")))
        except (ValueError, TypeError, AttributeError) as exc:
            raise BackendError("Waldur resource UUID is invalid") from exc
        return f"waldur-{str(resource_uuid)[:8]}"

    def ping(self, raise_exception: bool = False) -> bool:
        try:
            return self.client.ping()
        except BackendError:
            if raise_exception:
                raise
            return False

    def diagnostics(self) -> bool:
        return self.ping()

    def list_components(self) -> list[str]:
        return list(self.backend_components)

    def _get_usage_report(self, resource_backend_ids: list[str]) -> dict:
        del resource_backend_ids
        return {}

    @staticmethod
    def _limits_as_dict(raw: object) -> dict[str, Any]:
        """Normalise ``waldur_resource.limits`` to a plain mapping.

        The API client hands over a ``ResourceLimits`` attrs object, not a dict:
        it carries the values in ``additional_properties`` and exposes
        ``to_dict()``, ``__getitem__`` and ``__contains__`` -- but no
        ``items()``. Calling ``items()`` on it raised AttributeError and failed
        the whole create order. Plain dicts still work, which keeps unit tests
        and any caller that already normalised the value working.
        """
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        to_dict = getattr(raw, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise BackendError(f"Unsupported Waldur limits payload: {type(raw).__name__}")

    def _collect_resource_limits(
        self, waldur_resource: object
    ) -> tuple[dict[str, int], dict[str, int]]:
        requested = self._limits_as_dict(getattr(waldur_resource, "limits", None))
        supported = {"cores", "memory"}
        waldur_limits = {key: int(value) for key, value in requested.items() if key in supported}
        backend_limits = {
            key: int(value * self.backend_components.get(key, {}).get("unit_factor", 1))
            for key, value in waldur_limits.items()
        }
        return backend_limits, waldur_limits

    def _pre_create_resource(
        self, waldur_resource: object, user_context: Optional[dict] = None
    ) -> None:
        del waldur_resource, user_context

    def create_resource(
        self, waldur_resource: object, user_context: Optional[dict] = None
    ) -> BackendResourceInfo:
        # The empty string is intentional: create_resource_with_id ignores
        # resource_backend_id and derives the VMID/UUID from waldur_resource itself.
        return self.create_resource_with_id(waldur_resource, "", user_context)

    def create_resource_with_id(
        self,
        waldur_resource: object,
        resource_backend_id: str,
        user_context: Optional[dict] = None,
    ) -> BackendResourceInfo:
        """Clone the template; Proxmox itself assigns the backend ID.

        The processor calls this method directly, passing an ID the core derived
        from ``waldur_resource.slug``. That value is deliberately discarded: for
        Proxmox the backend ID is the VMID, which only exists once
        ``cluster/nextid`` has handed one out. Feeding the slug through as if it
        were the Waldur UUID is what produced "badly formed hexadecimal UUID
        string" -- and it would also break adoption, because the idempotency
        marker has to be the UUID.
        """
        del resource_backend_id
        resource_uuid = str(getattr(waldur_resource, "uuid", ""))
        self._pre_create_resource(waldur_resource, user_context)
        backend_id = self.client.provision_vm(resource_uuid, self._name(waldur_resource))
        limits = self._setup_resource_limits(backend_id, waldur_resource)
        info = BackendResourceInfo(backend_id=backend_id, limits=limits)
        self.post_create_resource(info, waldur_resource, user_context)
        return info

    def downscale_resource(self, resource_backend_id: str) -> bool:
        del resource_backend_id
        return True

    def pause_resource(self, resource_backend_id: str) -> bool:
        self.client.stop_vm(resource_backend_id)
        return True

    def restore_resource(self, resource_backend_id: str) -> bool:
        self.client.start_vm(resource_backend_id)
        return True

    def get_resource_metadata(self, resource_backend_id: str) -> dict:
        vm = self.client.get_vm(resource_backend_id)
        if vm is None:
            return {}
        return {key: vm[key] for key in ("vmid", "name", "node", "status") if key in vm}

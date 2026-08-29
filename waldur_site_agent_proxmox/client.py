from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any, Optional

from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException
from proxmoxer.tools.tasks import Tasks
from waldur_site_agent.backend.clients import BaseClient
from waldur_site_agent.backend.exceptions import BackendError
from waldur_site_agent.backend.structures import Association, ClientResource


class ProxmoxClient(BaseClient):
    "Thin wrapper around proxmoxer with bounded polling."

    TAG_PREFIX = "waldur-"
    LABEL_PREFIX = "waldur_uuid="

    def __init__(
        self,
        *,
        host: str,
        user: str,
        token_name: str,
        token_value: str,
        node: str,
        template_vmid: int,
        verify_ssl: bool = True,
        timeout: float = 300,
        polling_interval: float = 1,
        allocation_retries: int = 5,
        storage: Optional[str] = None,
        pool: Optional[str] = None,
        full_clone: bool = True,
        start_after_create: bool = False,
        api: Any = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.host, self.node, self.template_vmid = host, node, template_vmid
        self.timeout, self.polling_interval = timeout, polling_interval
        self.allocation_retries = allocation_retries
        self.storage, self.pool = storage, pool
        self.full_clone, self.start_after_create = full_clone, start_after_create
        self._sleep, self._monotonic = sleep, monotonic
        self.api = api or ProxmoxAPI(
            host,
            user=user,
            token_name=token_name,
            token_value=token_value,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )

    def __repr__(self) -> str:
        return f"ProxmoxClient(host={self.host!r}, node={self.node!r}, credentials=<redacted>)"

    @classmethod
    def marker(cls, value: str) -> str:
        try:
            normalized = str(uuid.UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise BackendError("Waldur resource UUID is invalid") from exc
        return cls.TAG_PREFIX + normalized

    @classmethod
    def label(cls, value: str) -> str:
        return cls.LABEL_PREFIX + cls.marker(value)[len(cls.TAG_PREFIX) :]

    @staticmethod
    def _tags(value: Any) -> set[str]:
        return {tag.strip() for tag in str(value or "").split(";") if tag.strip()}

    def _api(self, action: str, call: Callable[[], Any], missing_ok: bool = False) -> Any:
        try:
            return call()
        except ResourceException as exc:
            if missing_ok and exc.status_code == 404:
                return None
            raise BackendError(f"Proxmox {action} failed: {exc}") from exc
        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(f"Proxmox {action} failed: {exc}") from exc

    def _cluster_vms(self) -> list[dict[str, Any]]:
        result = self._api("VM listing", lambda: self.api.cluster.resources.get(type="vm"))
        if not isinstance(result, list):
            raise BackendError("Proxmox VM listing returned an invalid response")
        return [item for item in result if isinstance(item, dict)]

    def _find_vm(self, vmid: str | int) -> Optional[dict[str, Any]]:
        wanted = str(vmid)
        return next((vm for vm in self._cluster_vms() if str(vm.get("vmid")) == wanted), None)

    def find_by_waldur_uuid(self, value: str) -> Optional[dict[str, Any]]:
        marker, label = self.marker(value), self.label(value)
        matches = []
        for vm in self._cluster_vms():
            if marker in self._tags(vm.get("tags")):
                matches.append(vm)
                continue
            description = str(vm.get("description", ""))
            if label not in description.splitlines():
                node = str(vm.get("node") or self.node)
                vmid = vm.get("vmid")
                config = self._api(
                    "VM marker lookup",
                    lambda node=node, vmid=vmid: self.api.nodes(node).qemu(vmid).config.get(),
                    missing_ok=True,
                )
                description = str(config.get("description", "")) if config else ""
            if label in description.splitlines():
                matches.append(vm)
        if len(matches) > 1:
            raise BackendError(f"Multiple Proxmox VMs carry Waldur marker {marker}")
        return matches[0] if matches else None

    @staticmethod
    def _is_collision(exc: BaseException) -> bool:
        text = str(exc).lower()
        return (
            getattr(exc, "status_code", None) == 409
            or "already exists" in text
            or ("vmid" in text and "exist" in text)
        )

    def wait_for_task(self, upid: str) -> dict[str, Any]:
        try:
            node = str(Tasks.decode_upid(upid)["node"])
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            raise BackendError("Proxmox operation did not return a valid task UPID") from exc
        deadline = self._monotonic() + self.timeout
        while True:
            status = self._api("task status", lambda: self.api.nodes(node).tasks(upid).status.get())
            if not isinstance(status, dict):
                raise BackendError("Proxmox task status returned an invalid response")
            if status.get("status") == "stopped":
                exitstatus = status.get("exitstatus", "unknown")
                if exitstatus != "OK":
                    raise BackendError(f"Proxmox task {upid} failed: {exitstatus}")
                return status
            if self._monotonic() >= deadline:
                raise BackendError(f"Timed out waiting for Proxmox task {upid}")
            self._sleep(self.polling_interval)

    def _wait_for_vm(self, vmid: str | int, expected: Optional[str]) -> None:
        deadline = self._monotonic() + self.timeout
        while True:
            vm = self._find_vm(vmid)
            reached = (
                vm is None if expected is None else vm is not None and vm.get("status") == expected
            )
            if reached:
                return
            if self._monotonic() >= deadline:
                target = expected or "absent"
                raise BackendError(f"Timed out waiting for VM {vmid} to become {target}")
            self._sleep(self.polling_interval)

    def _poll_result(self, result: Any) -> None:
        if result is None:
            return
        if not isinstance(result, str) or not result.startswith("UPID:"):
            raise BackendError("Proxmox operation returned an invalid task result")
        self.wait_for_task(result)

    def _set_marker(self, vmid: int, value: str) -> None:
        config = self._api(
            "VM config lookup", lambda: self.api.nodes(self.node).qemu(vmid).config.get()
        )
        tags = self._tags(config.get("tags") if isinstance(config, dict) else None)
        tags.add(self.marker(value))
        result = self._api(
            "VM tag update",
            lambda: self.api.nodes(self.node).qemu(vmid).config.put(tags=";".join(sorted(tags))),
        )
        self._poll_result(result)

    def provision_vm(self, waldur_uuid: str, name: str) -> str:
        adopted = self.find_by_waldur_uuid(waldur_uuid)
        if adopted is not None:
            return str(adopted["vmid"])
        for _attempt in range(self.allocation_retries):
            adopted = self.find_by_waldur_uuid(waldur_uuid)
            if adopted is not None:
                return str(adopted["vmid"])
            raw_vmid = self._api("VMID allocation", lambda: self.api.cluster.nextid.get())
            try:
                vmid = int(raw_vmid)
            except (TypeError, ValueError) as exc:
                raise BackendError("Proxmox nextid returned an invalid VMID") from exc
            if self._find_vm(vmid) is not None:
                continue
            data = {
                "newid": vmid,
                "name": name,
                "target": self.node,
                "full": int(self.full_clone),
                "description": self.label(waldur_uuid),
                "storage": self.storage,
                "pool": self.pool,
            }
            data = {key: val for key, val in data.items() if val is not None}
            try:
                upid = self.api.nodes(self.node).qemu(self.template_vmid).clone.post(**data)
                self._poll_result(upid)
            except ResourceException as exc:
                if self._is_collision(exc):
                    continue
                raise BackendError(f"Proxmox VM clone failed: {exc}") from exc
            except BackendError as exc:
                if self._is_collision(exc):
                    continue
                raise
            self._wait_for_vm(vmid, "stopped")
            self._set_marker(vmid, waldur_uuid)
            if self.start_after_create:
                self.start_vm(vmid)
            return str(vmid)
        raise BackendError(
            f"Unable to allocate a free Proxmox VMID after {self.allocation_retries} attempts"
        )

    def delete_vm(self, vmid: str | int) -> None:
        vm = self._find_vm(vmid)
        if vm is None:
            return
        node = str(vm.get("node") or self.node)
        try:
            upid = self.api.nodes(node).qemu(vmid).delete()
        except ResourceException as exc:
            if exc.status_code == 404:
                return
            raise BackendError(f"Proxmox VM deletion failed: {exc}") from exc
        self._poll_result(upid)
        self._wait_for_vm(vmid, None)

    def _power(self, vmid: str | int, target: str) -> None:
        vm = self._find_vm(vmid)
        if vm is None:
            raise BackendError(f"Proxmox VM {vmid} does not exist")
        if vm.get("status") == target:
            return
        node = str(vm.get("node") or self.node)
        endpoint = self.api.nodes(node).qemu(vmid).status
        call = endpoint.start.post if target == "running" else endpoint.stop.post
        self._poll_result(self._api(f"VM power {target}", call))
        self._wait_for_vm(vmid, target)

    def stop_vm(self, vmid: str | int) -> None:
        self._power(vmid, "stopped")

    def start_vm(self, vmid: str | int) -> None:
        self._power(vmid, "running")

    def list_resources(self) -> list[ClientResource]:
        return [
            ClientResource(
                name=str(vm.get("name", "")),
                description=str(vm.get("description", "")),
                organization=str(vm.get("node", "")),
                backend_id=str(vm.get("vmid", "")),
            )
            for vm in self._cluster_vms()
            if not vm.get("template")
        ]

    def get_resource(self, resource_id: str) -> Optional[ClientResource]:
        vm = self._find_vm(resource_id)
        if vm is None:
            return None
        return ClientResource(
            name=str(vm.get("name", "")),
            description=str(vm.get("description", "")),
            organization=str(vm.get("node", "")),
            backend_id=str(vm.get("vmid", "")),
        )

    def create_resource(
        self, name: str, description: str, organization: str, parent_name: Optional[str] = None
    ) -> str:
        del name, description, organization, parent_name
        raise BackendError("Proxmox creation requires a Waldur UUID; use provision_vm")

    def delete_resource(self, name: str) -> str:
        self.delete_vm(name)
        return name

    def set_resource_limits(self, resource_id: str, limits_dict: dict[str, int]) -> Optional[str]:
        unsupported = set(limits_dict) - {"cores", "memory"}
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise BackendError(f"Unsupported Proxmox limits: {names}")
        vm = self._find_vm(resource_id)
        if vm is None:
            raise BackendError(f"Proxmox VM {resource_id} does not exist")
        node = str(vm.get("node") or self.node)
        result = self._api(
            "VM limit update",
            lambda: self.api.nodes(node).qemu(resource_id).config.put(**limits_dict),
        )
        self._poll_result(result)
        return result

    def get_resource_limits(self, resource_id: str) -> dict[str, int]:
        vm = self._find_vm(resource_id)
        if vm is None:
            return {}
        node = str(vm.get("node") or self.node)
        config = self._api(
            "VM config lookup", lambda: self.api.nodes(node).qemu(resource_id).config.get()
        )
        return {
            key: int(config[key])
            for key in ("cores", "memory")
            if isinstance(config, dict) and key in config
        }

    def get_resource_user_limits(self, resource_id: str) -> dict[str, dict[str, int]]:
        del resource_id
        return {}

    def set_resource_user_limits(
        self, resource_id: str, username: str, limits_dict: dict[str, int]
    ) -> str:
        del resource_id, username, limits_dict
        raise BackendError("Proxmox membership synchronization is not implemented")

    def get_association(self, user: str, resource_id: str) -> Optional[Association]:
        del user, resource_id
        return None

    def create_association(
        self, username: str, resource_id: str, default_account: Optional[str] = None
    ) -> str:
        del username, resource_id, default_account
        raise BackendError("Proxmox membership synchronization is not implemented")

    def delete_association(self, username: str, resource_id: str) -> str:
        del username, resource_id
        raise BackendError("Proxmox membership synchronization is not implemented")

    def get_usage_report(self, resource_ids: list[str], timezone: Optional[str] = None) -> list:
        del resource_ids, timezone
        return []

    def list_resource_users(self, resource_id: str) -> list[str]:
        del resource_id
        return []

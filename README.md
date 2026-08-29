# waldur-site-agent-proxmox

> **EXPERIMENT** — Teil des öffentlichen Versuchs
> [waldur-multicloud](../waldur-multicloud). Fortführung nicht
> entschieden, keine Produktionsnutzung, nicht mit Waldur/OpenNode
> affiliiert.

Waldur-Site-Agent-Plugin für proxmox.
Regeln: [AGENTS.md](AGENTS.md) · Lizenz: MIT


## Configuration

Register the offering with `backend_type: proxmox` and provide these backend settings:

```yaml
backend_settings:
  host: pve.example.org
  user: waldur@pve
  token_name: site-agent
  token_value: ${PROXMOX_TOKEN_VALUE}
  node: pve-node-1
  template_vmid: 9000
  verify_ssl: true
  timeout: 300
  polling_interval: 1
  allocation_retries: 5
  # storage: local-lvm
  # pool: waldur
  full_clone: true
  start_after_create: false
```

The API token needs audit access plus clone, VM configuration, power, and deletion
permissions for the configured template and target scope. Membership synchronization and
usage reporting are intentionally not implemented because their provider scope is unresolved.

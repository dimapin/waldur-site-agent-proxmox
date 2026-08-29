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

## Container image

Build the image from the repository root:

```bash
docker build -t waldur-site-agent-proxmox:local .
```

Run it with a complete agent configuration mounted as a secret:

```bash
docker run --rm \
  --mount type=bind,src="$PWD/config.yaml",dst=/etc/waldur-site-agent/config.yaml,readonly \
  waldur-site-agent-proxmox:local
```

## Helm

The chart is in `charts/waldur-site-agent-proxmox`. Its default mode is `order_process`,
which is the mode supported by this provider.

Install it with a local configuration file:

```bash
helm upgrade --install proxmox-agent charts/waldur-site-agent-proxmox \
  --set-file config.content=config.yaml
```

For production deployments, create the configuration Secret separately and reference it
without putting credentials in Helm values:

```bash
kubectl create secret generic proxmox-agent-config \
  --from-file=config.yaml
helm upgrade --install proxmox-agent charts/waldur-site-agent-proxmox \
  --set config.existingSecret=proxmox-agent-config
```

The referenced Secret must contain the key configured by `config.secretKey` (by default,
`config.yaml`). Set `image.repository` and `image.tag` when using a custom registry.

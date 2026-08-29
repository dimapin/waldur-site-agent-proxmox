# Proxmox provider notes

proxmoxer; operations return task UPID and must be polled with timeout/bound until Task OK; node/template/VMID are config, not constants; VMID must come from nextid and conflicts handled; membership sync scope is unresolved, so do not invent it.

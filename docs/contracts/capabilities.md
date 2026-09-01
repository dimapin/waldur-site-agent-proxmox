<!-- Vendored from waldur-multicloud tag contract-v0.3.0, commit 2ae46d924fe9ed0fc3c50ee566ca9d5ee0ad2308, path docs/contracts/capabilities.md. Nicht hier editieren — Aenderungen zuerst im Meta-Repo. -->

# Capabilities (normativ) — Stand contract-v0.2.0

Pflicht-Operationen je Service-Klasse. Phase-1-Umfang; Erweiterungen
per Decision-Eintrag (MINOR), Verschärfungen sind MAJOR.

| ID | Service-Klasse | Operation | Pflicht |
|---|---|---|---|
| CAP-001 | alle | create | MUSS |
| CAP-002 | alle | terminate | MUSS |
| CAP-003 | alle | usage-report | MUSS (Kern der Multi-Cloud-Demo) |
| CAP-004 | alle | resource-metadata nach Create (CON-050) | MUSS |
| CAP-010 | compute | start/stop | KANN (Phase 2) |
| CAP-020 | k8s | kubeconfig-Auslieferung an Besteller | SOLL |
| CAP-030 | dbaas | Zugangsdaten-Auslieferung via Resource-Metadata | SOLL |

Nicht gelistete Day-2-Operationen (Resize, Upgrade, Backup/Restore)
sind bewusst AUSSERHALB des Phase-1-Contracts; Backends DÜRFEN sie
nicht stillschweigend teilweise anbieten — Aufnahme nur über
Decision-Eintrag.

## Metadata-Minima je Service-Klasse (zu CAP-004 / CON-050)

- **compute:** Provider-Ressourcen-ID, Standort/Region, vCPU, RAM,
  Disk, öffentliche IP (sofern vorhanden)
- **k8s:** Kubernetes-Version, Nodepool-Größe(n), API-Endpoint,
  kubeconfig-Zugriff gemäß CAP-020/CON-053
- **dbaas:** Engine und Version, Endpoint und Port,
  Zugangsdaten-Referenz gemäß CAP-030/CON-053

Erweiterung der Minima ist MINOR; Reduktion ist MAJOR.

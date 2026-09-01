<!-- Vendored from waldur-multicloud tag contract-v0.3.0, commit 2ae46d924fe9ed0fc3c50ee566ca9d5ee0ad2308, path docs/contracts/decisions/D-001-repo-pro-provider-multi-backend.md. Nicht hier editieren — Aenderungen zuerst im Meta-Repo. -->

# D-001: Ein Repo pro Provider, mehrere Backends pro Repo
Datum: 2026-08-30 · Status: angenommen
## Kontext
Provider bieten mehrere Service-Klassen (z. B. IONOS: compute, k8s,
dbaas). Kapselungs-Granularität war offen.
## Entscheidung
Ein Repository pro Provider. Innerhalb des Repos ein Backend pro
Service-Klasse (backends/-Paket, je ein Entry-Point, Namensschema
CON-001), gemeinsamer Client für Auth/Polling/Retry.
## Verworfene Alternativen (und warum)
Repo pro Service: dupliziert Client, SDK-Pinning und Provider-Notes;
Repo-Zahl wächst mit Provider × Service. Revisionspunkt: ein Service
mit schweren Sonderabhängigkeiten.
## Klasse und betroffene IDs
MINOR (initial): CON-001, CON-002.
## Betroffene Repos / Folge-MRs
Template (backends/-Struktur), alle Provider-Repos bei Anlage.

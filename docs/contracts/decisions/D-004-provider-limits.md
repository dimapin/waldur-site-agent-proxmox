<!-- Vendored from waldur-multicloud tag contract-v0.3.0, commit 2ae46d924fe9ed0fc3c50ee566ca9d5ee0ad2308, path docs/contracts/decisions/D-004-provider-limits.md. Nicht hier editieren — Aenderungen zuerst im Meta-Repo. -->

# D-004: Provider-Kontingente als Contract-Pflicht
Datum: 2026-08-31 · Status: vorgeschlagen
## Kontext
IONOS, Hetzner und STACKIT haben harte Vertrags-/Projektlimits.
Unbehandelt führen sie zu hängenden Retry-Schleifen, kryptischen
Order-Fehlern und unbemerkt erschöpfter Kapazität für alle Kunden.
## Entscheidung (Vorschlag)
Drei Ebenen: Waldur begrenzt Bestellbares (CON-072), das Backend
klassifiziert Quota-Fehler terminal und prüft Headroom wo möglich
(CON-070/071), der Betrieb überwacht Auslastung mit Warnschwelle
(CON-073). Abfragbarkeit je Provider wird in docs/providers/
erhoben, nicht angenommen.
## Verworfene Alternativen (und warum)
Nur reaktiv (Fehler durchreichen): Kunde sieht Rohfehler, Betrieb
sieht Erschöpfung erst am Ausfall. Nur proaktiv (Vorprüfung als
Gate): TOCTOU-Race, wiegt in falscher Sicherheit.
## Klasse und betroffene IDs
MINOR → contract-v0.3.0 (mit D-003): CON-070..073.
## Betroffene Repos / Folge-MRs
Testkit (Fehlertaxonomie-Tests), alle Provider-Repos,
docs/providers/ (Limit-Abschnitte).

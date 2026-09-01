<!-- Vendored from waldur-multicloud tag contract-v0.3.0, commit 2ae46d924fe9ed0fc3c50ee566ca9d5ee0ad2308, path docs/contracts/decisions/D-002-preis-und-ressourcen-sichtbarkeit.md. Nicht hier editieren — Aenderungen zuerst im Meta-Repo. -->

# D-002: Preis- und Ressourcen-Sichtbarkeit als Contract-Pflicht
Datum: 2026-08-31 · Status: angenommen (Anlass: Anforderung Betreiber)
## Kontext
Marketplace zeigte bisher weder Preise noch Ressourcendetails; Contract
enthielt dazu keine Anforderungen. Ohne Kosten- und Ressourcen-Sicht
trägt die Multi-Cloud-Story nicht (Vergleichbarkeit ist der Kern).
## Entscheidung
Neue normative IDs CON-040..043 (Komponenten/Pläne/Preise) und
CON-050..053 (Metadata, Usage-Integrität, Credentials-Auslieferung),
CAP-004 plus Metadata-Minima je Service-Klasse.
## Verworfene Alternativen (und warum)
Nur Doku/Best-Practice statt Norm: nicht testbar, genau daran ist die
Sichtbarkeit bisher gescheitert. Preise in Agent-Config statt
Waldur-Plänen: umgeht Marketplace-Mechanik und Kundenansicht.
## Klasse und betroffene IDs
MINOR (additiv) → contract-v0.2.0. Neue IDs s. o.; keine bestehende ID
geändert.
## Betroffene Repos / Folge-MRs
Testkit (neue Contract-Tests, insb. CON-051-Negativfall) → alle
Provider-Repos beim Pin auf das Paar v0.2.

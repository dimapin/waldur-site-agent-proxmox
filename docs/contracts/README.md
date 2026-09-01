<!-- Vendored from waldur-multicloud tag contract-v0.3.0, commit 2ae46d924fe9ed0fc3c50ee566ca9d5ee0ad2308, path docs/contracts/README.md. Nicht hier editieren — Aenderungen zuerst im Meta-Repo. -->

# Contract-Governance

Der "Contract" ist kein einzelnes Dokument, sondern dieses Verzeichnis.
Er besteht aus Teilen mit unterschiedlicher Änderungshoheit. Diese
Datei definiert die Regeln, nach denen er angepasst und erweitert wird.

## Aufbau

| Datei | Charakter | Änderungshoheit | Auslöser |
|---|---|---|---|
| upstream-api.md | BESCHREIBEND: Fakten über das Upstream-Framework | nur Rolle upstream-scout | Upstream-Versions-Bump |
| conventions.md | NORMATIV: unsere Festlegungen (Namen, Einheiten, Semantik) | Mensch, via Decision-Eintrag | bewusste Entscheidung |
| capabilities.md | NORMATIV: Pflicht-Operationen je Service-Klasse | Mensch, via Decision-Eintrag | bewusste Entscheidung |
| decisions/ | Begründungen normativer Änderungen (ADR-light) | Mensch | jede normative Änderung |
| CHANGELOG.md | eine Zeile pro Änderung mit Klasse und betroffenen Konsumenten | jeder MR | jeder MR |

Grenzziehung zu AGENTS.md (Kollisionsregel): Technische Semantik, auf
die Tests und Implementierungen sich beziehen, lebt HIER. AGENTS.md
regelt Prozess und Verhalten der Rollen. Widersprechen sich beide, ist
das ein Sperr-Befund — es gewinnt niemand stillschweigend.

## Requirement-IDs

Jede normative Aussage trägt eine ID: `CON-NNN` (conventions),
`CAP-NNN` (capabilities). Regeln:

1. IDs sind append-only. Eine vergebene ID wird NIE umgedeutet und
   NIE wiederverwendet.
2. Ändern der Bedeutung == neue ID + alte ID auf Status
   `DEPRECATED seit contract-vX.Y` mit Verweis auf die Nachfolge-ID.
   Deprecated-Einträge bleiben stehen.
3. Jede normative Aussage nutzt MUSS / SOLL / KANN. Aussagen ohne
   diese Schlüsselwörter sind Erläuterung, nicht Anforderung.
4. Tests referenzieren IDs im Docstring; Review-Befunde referenzieren
   IDs. Eine Anforderung, auf die kein Test verweist, ist ein Befund
   (ungeprüfte Norm); ein Test ohne ID-Bezug ebenso (normlose Prüfung).

Beschreibende Aussagen in upstream-api.md tragen keine IDs, sondern
Fundstellen: Datei + Zeilen + Upstream-Commit. Ohne Fundstelle keine
Aussage.

## Versionierung

Tags: `contract-vMAJOR.MINOR.PATCH` auf dem Meta-Repo.

- **MAJOR (breaking):** Eine Änderung, die eine bisher konforme
  Implementierung oder einen bisher konformen Test nicht-konform
  machen KANN. Dazu zählen: ID deprecaten oder verschärfen
  (KANN→SOLL→MUSS), Einheiten oder Namensschemata ändern,
  Erfolgs-/Fehlersemantik ändern, sowie jede inkompatible
  Upstream-Signaturänderung in upstream-api.md.
- **MINOR (additiv):** Neue IDs, neue optionale Capabilities,
  Abschwächungen (MUSS→SOLL), neue beschreibende Abschnitte.
- **PATCH (redaktionell):** Tippfehler, Fundstellen-Korrekturen,
  Umformulierungen ohne Bedeutungsänderung.

Im Zweifel gilt die höhere Klasse. "Das meinte doch eh jeder so" ist
kein PATCH-Argument — wenn Implementierungen es verschieden gelesen
haben KÖNNTEN, ist es MAJOR.

## Kopplung an Testkit und Provider-Repos

- Das Testkit wird `testkit-vX.Y.*` getaggt und implementiert genau
  contract-vX.Y. MAJOR/MINOR laufen im Gleichschritt; Testkit-PATCH
  ist frei.
- Provider-Repos pinnen IMMER das Paar (contract-Tag, testkit-Tag)
  mit gleichem X.Y. Ein gemischtes Paar ist ein Sperr-Befund im
  Review.
- Reihenfolge bei Änderungen: 1. Meta-MR (Contract + ggf. Testkit)
  → Merge → Tag. 2. Pro Provider-Repo ein Folge-MR, der das neue Paar
  pinnt und Vendoring (docs/contract/) aktualisiert. Bei MAJOR
  listet der Decision-Eintrag alle betroffenen Repos; erst wenn alle
  Folge-MRs gemerged sind, gilt die Migration als abgeschlossen.

## Änderungsprozess

- **upstream-api.md:** Nur der Scout schreibt; Auslöser ist ein
  Upstream-Bump oder eine Lücke, die eine andere Rolle als Blocker
  gemeldet hat. Der Scout klassifiziert die Änderung (MAJOR/MINOR/
  PATCH aus Konsumentensicht) und schreibt die CHANGELOG-Zeile.
  Menschliches Review via CODEOWNERS.
- **conventions.md / capabilities.md:** Jede Änderung braucht einen
  Decision-Eintrag unter decisions/ (Vorlage: TEMPLATE.md — Kontext,
  Entscheidung, verworfene Alternativen, Klasse, betroffene
  Konsumenten). Rollen dürfen Änderungen VORSCHLAGEN (als MR mit
  Decision-Entwurf), entschieden wird durch den Menschen. Kein
  Selbst-Merge.
- **CHANGELOG.md:** Pflichtzeile pro MR:
  `vX.Y.Z | Klasse | betroffene IDs | betroffene Repos | MR-Link`.
  Fehlende Zeile ist ein Sperr-Befund.

## Erweiterung (neuer Provider, neuer Service)

Neuer Provider oder neue Service-Klasse ist im Normalfall MINOR:
neue CAP-Zeile(n), ggf. neue CON-IDs, neue Datei unter
docs/providers/. Ausnahme: Wenn die Erweiterung eine bestehende ID
umdeuten würde (z. B. weil eine Einheit doch nicht überall passt),
greift die Deprecation-Regel und damit MAJOR — genau dafür ist sie da.

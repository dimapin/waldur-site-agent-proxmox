<!-- Vendored from waldur-multicloud tag contract-v0.3.0, commit 2ae46d924fe9ed0fc3c50ee566ca9d5ee0ad2308, path docs/contracts/conventions.md. Nicht hier editieren — Aenderungen zuerst im Meta-Repo. -->

# Konventionen (normativ) — Stand contract-v0.2.0 (+ v0.3.0-Vorschläge, s. D-003/D-004)

Format je Eintrag: ID | Status | Anforderung. Schlüsselwörter
MUSS/SOLL/KANN gemäß README. Änderungen nur per Decision-Eintrag.

## Namen und Struktur

- **CON-001** | Aktiv | Backends MÜSSEN dem Namensschema
  `<provider>-<service>` folgen (z. B. `ionos-dbaas`,
  `hcloud-compute`). Ein Provider-Repo KANN mehrere Backends
  exponieren (ein Entry-Point je Backend).
- **CON-002** | Aktiv | Ein Marketplace-Offering MUSS genau einem
  Backend entsprechen. Services, die einzeln aktivierbar/pausierbar
  sein sollen, MÜSSEN eigene Offerings sein.

## Einheiten und Komponenten

- **CON-010** | Aktiv | Abrechnungskomponenten MÜSSEN über alle
  Provider und Service-Klassen dieselben Einheiten verwenden:
  Speicher und RAM in GiB, vCPU in Stück. Abweichende Provider-APIs
  MÜSSEN im Backend umgerechnet werden, nicht im Preisplan.
- **CON-011** | Aktiv | Gleichartige Komponenten MÜSSEN über
  Offerings hinweg gleich benannt sein (z. B. `cpu`, `ram`,
  `storage`), damit Kostenvergleiche im Marketplace inhaltlich
  tragfähig sind.

## Idempotenz und Zustand

- **CON-020** | Aktiv | Jede vom Agenten erzeugte Provider-Ressource
  MUSS die Waldur-Resource-UUID als Tag/Label tragen. Das exakte
  Tag-Format je Provider steht in docs/providers/ und MUSS dort
  festgelegt sein, bevor das Backend implementiert wird.
- **CON-021** | Aktiv | Create MUSS idempotent sein: Existiert eine
  Ressource mit passendem Tag (CON-020), MUSS sie adoptiert werden
  (backend_id melden), es DARF KEINE zweite entstehen.
- **CON-022** | Aktiv | Terminate einer nicht (mehr) existierenden
  Ressource MUSS als Erfolg gewertet werden.
- **CON-023** | Aktiv | Die backend_id MUSS unmittelbar nach
  erfolgreichem Create an Waldur gemeldet werden, vor weiteren
  Schritten.

## Asynchronität und Fehler

- **CON-030** | Aktiv | Eine Operation MUSS erst dann als
  erfolgreich gelten, wenn der Provider den Zielzustand bestätigt
  hat. "Request angenommen" DARF NICHT als Erfolg gewertet werden.
- **CON-031** | Aktiv | Jeder Fehler, der eine Order betrifft, MUSS
  im Waldur-Order-State samt Meldung sichtbar werden. Retries MÜSSEN
  eine Obergrenze haben.
- **CON-032** | Aktiv | Secrets DÜRFEN NICHT in Logs, Fehlermeldungen
  oder Objekt-Repräsentationen erscheinen.

## Preis- und Komponentensichtbarkeit (neu in v0.2.0, D-002)

- **CON-040** | Aktiv | Jedes Offering MUSS alle Abrechnungskomponenten
  mit angezeigter Einheit (gemäß CON-010) und Abrechnungsart
  (fest / limitbasiert / nutzungsbasiert) definieren. Komponenten ohne
  vollständige Angaben DÜRFEN NICHT geladen werden.
- **CON-041** | Aktiv | Jedes aktive Offering MUSS mindestens einen
  aktiven Plan haben, der für JEDE Komponente einen Preis ausweist —
  kostenlose Komponenten mit explizitem Preis 0, nie durch Weglassen.
- **CON-042** | Aktiv | Dem Kunden angezeigte Einheit und abgerechnete
  Einheit MÜSSEN identisch sein (gleicher Faktor). Umrechnungen von
  Provider-Einheiten passieren im Backend (CON-010), niemals zwischen
  Anzeige und Abrechnung.
- **CON-043** | Aktiv | Limitbasierte Komponenten SOLLEN so definiert
  sein, dass Waldur bereits bei Bestellung eine Kostenschätzung
  anzeigen kann; rein nutzungsbasierte Komponenten SOLLEN in der
  Offering-Beschreibung als solche erkennbar sein.

## Ressourcen-Sichtbarkeit (neu in v0.2.0, D-002)

- **CON-050** | Aktiv | Nach erfolgreichem Create MUSS das Backend die
  Ressourcen-Metadaten des Mindestumfangs seiner Service-Klasse
  (capabilities.md, Metadata-Minima) an Waldur melden, damit der
  Besteller die Ressource identifizieren und nutzen kann.
- **CON-051** | Aktiv | Usage-Reports MÜSSEN ausschließlich im
  Offering definierte Komponenten referenzieren, in deren Einheit.
  Ein Report auf eine unbekannte Komponente MUSS als Fehler sichtbar
  werden — stilles Verwerfen DARF NICHT vorkommen und ist als
  Negativfall zu testen.
- **CON-052** | Aktiv | Usage MUSS mindestens im konfigurierten
  Reporting-Intervall gemeldet werden; das Ausbleiben von Reports
  SOLL als Fehlerzustand erkennbar sein (Log/Alert), nicht als stilles
  Veralten der Kostendaten.
- **CON-053** | Aktiv | Zugangsinformationen (kubeconfig,
  DB-Credentials) MÜSSEN über den dafür vorgesehenen
  Waldur-Mechanismus für Ressourcen-Metadaten/Secrets ausgeliefert
  werden — NIEMALS über Logs, Kommentare oder Offering-Beschreibungen.

## Provisionierungs-Engine, engine-agnostisch (VORSCHLAG v0.3.0, D-003)

- **CON-060** | Vorgeschlagen | Die Provisionierungs-Engine (SDK,
  OpenTofu, Crossplane, …) MUSS je Backend eine explizite,
  dokumentierte Entscheidung sein (Decision-Eintrag), keine stille.
- **CON-061** | Vorgeschlagen | Unabhängig von der Engine MUSS jede
  Provisionierung auf einem deterministischen Schlüssel
  (Waldur-Resource-UUID) konvergieren, nach Abbruch wiederaufnehmbar
  sein und die Tags gemäß CON-020 in alle erzeugten
  Provider-Ressourcen propagieren.
- **CON-062** | Vorgeschlagen | Engine und Modul-/Composition-Version
  MÜSSEN in den Ressourcen-Metadaten stehen (Reproduzierbarkeit des
  Standard-Setups).
- **CON-063** | Vorgeschlagen | Engine-Ausgaben (Pläne, Logs,
  Variablen) DÜRFEN NICHT ungefiltert in Waldur oder Logs gelangen
  (Secrets, CON-032).

### Anhang OpenTofu (VORSCHLAG v0.3.0, D-003)

- **CON-065** | Vorgeschlagen | Remote State mit Locking MUSS; ein
  State pro Waldur-Ressource, Schlüssel = Resource-UUID.
- **CON-066** | Vorgeschlagen | State-Ablage MUSS versioniert und
  verschlüsselt sein (Bucket-Versioning + OpenTofu-State-Encryption);
  Zugriff nur für den Agenten.
- **CON-067** | Vorgeschlagen | State-Verlust MUSS über die
  CON-020-Tags behebbar sein (Re-Import bzw. Tag-basierte
  Bereinigung); dieser Pfad ist als E2E-Fall zu testen.

## Limits und Kapazität (VORSCHLAG v0.3.0, D-004)

- **CON-070** | Vorgeschlagen | Provider-Fehler der Klasse
  "Kontingent/Limit überschritten" MÜSSEN als terminale Fehlerklasse
  behandelt werden: kein automatischer Retry, verständliche Meldung
  im Order-State ("Kapazitätsgrenze erreicht", nicht Rohfehler).
  Retry-Schleifen auf Quota-Fehler sind ein Sperr-Befund.
- **CON-071** | Vorgeschlagen | Wo die Provider-API Kontingente und
  Auslastung abfragbar macht, SOLL das Backend vor Create prüfen und
  bei fehlendem Headroom ohne Provider-Call ablehnen. Die Vorprüfung
  DARF NICHT als Garantie gelten (Race zwischen parallelen Orders) —
  maßgeblich bleibt die Provider-Antwort.
- **CON-072** | Vorgeschlagen | Offerings MÜSSEN bestellbare Größen
  begrenzen (Komponenten-Min/Max je Order gemäß docs/providers/);
  unbegrenzte Eingaben DÜRFEN NICHT existieren.
- **CON-073** | Vorgeschlagen | Die Auslastung je Provider-Kontingent
  (genutzt vs. Limit) SOLL als Metrik mit Warnschwelle (Richtwert
  80 %) erhoben werden, damit Kontingenterhöhungen — ein
  Vertragsprozess mit Vorlauf — rechtzeitig starten.

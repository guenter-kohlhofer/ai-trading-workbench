# KI-Workflow — Architektur der Mensch-KI-Zusammenarbeit

Der interessanteste Teil dieses Projekts ist nicht der Trading-Code, sondern das
**Arbeitssystem**: ein LLM (Claude, im Desktop-„Cowork"-Modus mit Dateizugriff,
persistentem Projekt-Memory und Scheduled Tasks) als Analyse-, Dokumentations- und
Disziplin-Schicht über einem regelbasierten Prozess. Aufgebaut und iterativ verfeinert
seit April 2026.

## Grundprinzip: klare Arbeitsteilung

| | Aufgabe |
|---|---|
| **Python (deterministisch)** | rechnet alle Zahlen: Indikatoren, Regime, Volumen-Gates, Backtests. Das LLM schätzt niemals Kurse oder Kennzahlen. |
| **Claude (LLM)** | liest Scanner-Reports, Belege und Nachrichtenlage; prüft Setups gegen das Regelwerk; schreibt Briefings, Journal und Statistik; schlägt vor und begründet. |
| **Mensch** | trifft jede Entscheidung, führt jede Order aus, setzt jeden Stop, verantwortet jeden Risiko-Parameter. |

Die KI ist bewusst **kein** Anlageberater und **kein** Auto-Trader — sie ist
Prozess-Infrastruktur.

## Komponenten

### 1. Projekt-Memory als Wissensbasis

Das gesamte Regelwerk lebt in versionierten Markdown-Dateien, die die KI zu
Session-Beginn liest: Regel-Übersicht, Positions- und Pipeline-Status, offene To-dos,
Trade-Statistik — und **Lehren-Dateien**: jeder dokumentierte Fehler wird zu einer
benannten, dauerhaften Regel („Tages-Volumen ≠ Stundenbalken", „Stop-Existenz im
Broker-System verifizieren", …). Neue Sessions starten damit nie bei null.

### 2. Custom Skills — wiederholbare Routinen als Code für die KI

Drei selbst geschriebene Skills (strukturierte Instruktions-Pakete) machen die
Kern-Routinen deterministisch abrufbar:

- **Session-Start-Routine:** Datum/Kalender-Check → Memory laden → Marktlage und News
  scannen → Signal-Tabelle → offene Pflichten. Ein Kommando, vollständiges Lagebild.
- **Selbst-Evaluation (Eval):** prüft die Wissensbasis systematisch auf veraltete
  Referenzen, Widersprüche und Limit-Verletzungen — mit oberstem Prinzip
  **„kein Verschlimmbessern"**: vor jeder Änderung Source-of-Truth lesen und gegen den
  Track-Record prüfen (hätte die „Verbesserung" einen historischen Gewinner verhindert?).
  Risiko-Parameter darf die KI nie eigenmächtig ändern.
- **Session-Ende:** persistiert alles Session-Übergreifende (Status, Alarme, neue
  Lehren, Journal-Pflichten), bevor eine Session endet.

### 3. Automatisierung — Scheduled Cloud-Tasks

Fünf geplante Tasks decken die Woche ab: Tages-Briefings (Mo–Fr morgens, mit
Regime-Check und priorisierter Handlungsliste), wöchentliche Selbst-Evaluation,
Wochenschluss-Memo (Bilanz, Erinnerung an den Depot-CSV-Export), Sonntags-Coach
(Wochenreview, Trail-Stop- und Stage-Checks, Pipeline-Restrukturierung) — plus ein
selbst-aktualisierendes Status-Dashboard als HTML-Artefakt. Automatisiert ist alles
außer dem, was bewusst beim Menschen bleibt: Orders, Stops, Entscheidungen.

### 4. Informations-Ampel — kalibrierte Unsicherheit statt Raten

Jede wesentliche Empfehlung trägt eine explizite Datenlage-Einstufung:

- 🟢 **ausreichend** — Empfehlung ohne Vorbehalt möglich
- 🟡 **lückenhaft** — Empfehlung mit Vorbehalt; benannt wird, welche Zusatzinfo sie verbessern würde
- 🔴 **unzureichend** — keine Empfehlung; stattdessen: was genau fehlt, wer es beschafft, mit welchem Aufwand

Dazu das **Nie-raten-Gebot**: Lücken werden nie stillschweigend mit Annahmen gefüllt;
jede Annahme ist als solche markiert; Zahlen kommen nur aus verifizierbaren Quellen.
Tool-Ausfälle werden gemeldet und eskaliert statt still umgangen.

### 5. Feedback-Schleifen mit Empirie

- **Divergenz-Tracking:** Wo Mensch und KI-Empfehlung auseinanderlaufen, wird das
  Outcome neutral mitgeschrieben — die Zusammenarbeit wird selbst vermessen.
- **Schnellcheck-Empirie:** Impuls-Trades ohne Check liefen messbar schlechter als
  gecheckte — daraus wurde eine Pflicht-Routine.
- **Backtest-Reihe v1–v6:** Regel-Kandidaten aus der Praxis werden erst in-sample
  gefunden, dann out-of-sample validiert, bevor sie ins Regelwerk „gelockt" werden.

## Übertragbarkeit

Nichts an dieser Architektur ist trading-spezifisch. Das Muster —
**deterministischer Code für Zahlen, LLM für Synthese und Prozess-Disziplin,
persistentes Memory für Regeln und Lehren, Skills für Routinen, Scheduled Tasks für
Automatisierung, Ampel-Konvention für Unsicherheit, Mensch als letzte Instanz** —
lässt sich auf beliebige Fach-Workflows übertragen (Support, Compliance, Redaktion,
Operations). Dieses Repo dokumentiert eine funktionierende Referenz-Implementierung
aus dem Alltag.

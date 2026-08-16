# BauOS Invoice MVP

Erster Baustein der BauOS-Vision (Baubetrieb-Verwaltungssoftware für Laura). FastAPI-Backend +
eine einzelne statische HTML/JS-Seite als Frontend (kein Build-Step, kein Framework).

## Struktur

- `app/main.py` – FastAPI-Routen (Rechnungen, Dokumente/Angebote, Kunden, Projekte, Firmendaten)
- `app/db.py` – SQLite-Zugriff für **Eingangsrechnungen** (`invoices`-Tabelle: was Laura Lieferanten schuldet)
- `app/documents_db.py` – SQLite-Zugriff für **ausgehende Dokumente** (`documents`-Tabelle: Angebote/Rechnungen/Abschlagsrechnungen an Kunden)
- `app/invoice_parser.py` / `app/ai_invoice_extractor.py` – Rechnungserkennung aus PDF (Regex zuerst, KI-Fallback über Anthropic API)
- `app/invoice_filing.py` – Auto-Ablage bezahlter Eingangsrechnungen (siehe unten)
- `app/company_settings.py`, `app/customers_db.py`, `app/projects_db.py` – Stammdaten
- `app/static/index.html` – gesamtes Frontend in einer Datei (Vanilla JS, kein Framework)
- `bauos.db` – lokale SQLite-Datenbank (nicht versioniert)

## Server starten

```bash
cd "C:\Users\Laura de Santis\Documents\bauos-invoice-mvp"
.venv\Scripts\uvicorn.exe app.main:app --reload
```

Wichtig: `main.py` lädt `app/static/index.html` über einen **relativen Pfad**, daher muss der
Server aus dem Projektverzeichnis heraus gestartet werden (cwd = Projekt-Root), nicht z.B. über
`--app-dir` aus einem anderen Ordner. Für das Preview-Tool liegt dafür `run_server.bat` bereit.

## Wichtige Geschäftslogik

**Bezahlt-Trigger (3 Schritte):** Sobald eine Eingangsrechnung in der UI auf Status `bezahlt`
gesetzt wird (`PATCH /invoices/{id}`), kopiert `invoice_filing.file_paid_invoice()` die PDF-Datei
automatisch in drei Zielordner unter dem konfigurierten Dropbox-Basispfad (Firmeneinstellungen →
`filing_base_path`, aktuell gesetzt auf `C:/Users/Laura de Santis/Dropbox/1. CIDE`):
1. `03 Vertragspartner\{Lieferant}\`
2. `09 FIBU\{Jahr}\{MM} {Monat} {Jahr}\01 Eingang\`
3. `09 FIBU\{Jahr}\{MM} {Monat} {Jahr}\02 für Datev\`

Dateiname: `{JJMMTT} INV {Lieferant} RE-NR. {Rechnungsnummer}.pdf`. Monat richtet sich nach dem
Rechnungsdatum, nicht dem Zahlungsdatum. Gilt nur für Eingangsrechnungen, nicht für Lauras eigene
ausgehende Rechnungen/Angebote. Lieferantennamen-Abweichungen (extrahierter Name vs. bestehender
Ordnername) werden in `_SUPPLIER_NAME_OVERRIDES` in `invoice_filing.py` gepflegt – bei neuen
Abweichungen dort einen Eintrag ergänzen statt eine allgemeine Regel zu suchen.

**Skonto-Sichtbarkeit:** In der Rechnungstabelle (`index.html`) zeigt die Skonto-Spalte ein Badge
mit Prozent, Datum und verbleibenden Tagen (`skontoCellHtml()`); bei ≤1 Tag Restlaufzeit wird die
Zeile zusätzlich stark hervorgehoben (`row-skonto-urgent`).

**Skonto-Erinnerungsfenster:** Beim ersten Laden der Rechnungsliste pro Tag prüft
`checkSkontoReminder()`, ob offene (Status `offen`) Rechnungen mit Skonto-Frist heute oder morgen
ablaufen. Falls ja, öffnet sich ein Modal (`#skontoReminderOverlay`) mit Anzahl, zahlbarer Summe
mit Skonto und Gesamtersparnis. Wird über `localStorage` (`skontoReminderShown`) auf einmal pro
Tag begrenzt.

## Sicherheitsregel (aus Nutzer-Feedback)

**Niemals echte Dateien auf Lauras Dropbox/Buchhaltungs-Struktur umbenennen, verschieben oder
kopieren ohne ihre explizite, aktuelle Erlaubnis.** Das gilt für direkte Shell-Aktionen genauso
wie für automatisierte Features (z.B. die Auto-Ablage oben). Beim Entwickeln/Testen solcher
Features immer gegen ein Scratch-Verzeichnis testen, nie gegen die echten Pfade. Wenn Laura selbst
in der laufenden App auf "bezahlt" klickt, ist das ihre eigene Aktion und explizit erlaubt – der
Agent selbst darf so etwas nur nach ausdrücklichem Ja auslösen.

## Tests

```bash
pytest
```

`tests/test_ai_invoice_extractor.py` mockt den Anthropic-Client, ruft also keine echte API auf.

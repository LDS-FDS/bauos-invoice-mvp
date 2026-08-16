---
description: Verarbeitet neue bezahlte Eingangsrechnungen aus dem Dropbox-Ordner "Bezahlt - bitte einpflegen!!" und legt sie automatisch in BauOS und den drei Zielordnern (Vertragspartner, FIBU-Eingang, FIBU-Datev) ab.
---

Starte den Subagenten `rechnung-einpflegen` (Agent-Tool, `subagent_type: "rechnung-einpflegen"`)
und lass ihn den in seiner Definition beschriebenen Workflow vollständig ausführen:

1. Neue PDFs direkt im Ordner `C:\Users\Laura de Santis\Dropbox\1. CIDE\15 Einkäufe\Bezahlt -
   bitte einpflegen!!` finden (der Unterordner `Pending` bleibt unangetastet).
2. Jede Rechnung erkennen (zuerst über `/invoices/parse`, bei Scans ohne Textlayer manuell
   auslesen und einpflegen).
3. In BauOS als bezahlt markieren - das löst die automatische Ablage in den drei Zielorten aus.
4. Vor jeder Löschung verifizieren, dass alle drei Zieldateien tatsächlich existieren.
5. Erst danach die Originaldatei aus dem Eingangsordner löschen, temporäre Dateien aufräumen.
6. Am Ende eine kurze Zusammenfassung auf Deutsch geben (Lieferant, Datum, Rechnungsnummer,
   Betrag je Rechnung).

Dieser Befehl ist der einzige zulässige Weg, den `rechnung-einpflegen`-Agenten zu starten -
niemals aufgrund von Gesprächskontext oder eigener Einschätzung auslösen.

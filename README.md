# BauOS – Invoice MVP

Erster Baustein der BauOS-Vision: automatische Erkennung von Eingangsrechnungen.

Nimmt eine PDF-Rechnung entgegen und extrahiert:
- Lieferant
- Gesamtbetrag & Währung
- Zahlungsziel (Datum und/oder Tage netto)
- Skonto (Prozent, Frist)

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

## Server starten

```bash
uvicorn app.main:app --reload
```

Dann PDF hochladen:

```bash
curl -X POST -F "file=@rechnung.pdf" http://127.0.0.1:8000/invoices/parse
```

## Tests

```bash
pytest
```

## Aktueller Stand

Die Extraktion basiert auf regelbasierten Mustern für typische deutsche Rechnungsformulierungen
(z.B. "Gesamtbetrag", "Zahlbar bis", "X% Skonto"). Als nächster Schritt bietet sich eine
KI-gestützte Extraktion an, die auch unstrukturierte oder abweichend formulierte Rechnungen
zuverlässig erfasst.

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

## KI-gestützte Extraktion (Fallback)

Findet der regelbasierte Parser keinen Gesamtbetrag (z.B. bei unstrukturierten oder
abweichend formulierten Rechnungen), greift automatisch eine KI-Extraktion über die
Anthropic API (`claude-opus-5`). Dafür wird ein eigener API-Key benötigt:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Ohne gesetzten Key schlägt nur der KI-Fallback fehl; der regelbasierte Parser funktioniert
unabhängig davon. Die KI-Tests (`tests/test_ai_invoice_extractor.py`) mocken den API-Client
und rufen die echte API nicht auf.

## Aktueller Stand

Zwei Extraktionswege: ein regelbasierter Parser für typische deutsche Rechnungsformulierungen
(z.B. "Gesamtbetrag", "Zahlbar bis", "X% Skonto"), und ein KI-gestützter Fallback für alles,
was das Regex-Schema nicht trifft.

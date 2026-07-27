from app.invoice_parser import parse_invoice_text

SAMPLE_INVOICE = """
Mustermann Bau GmbH
Musterstraße 1
12345 Musterstadt

Rechnung Nr. 2026-045
Datum: 01.07.2026

Leistung: Trockenbauarbeiten Projekt "Wohnhaus Nord"

Gesamtbetrag: 4.250,00 EUR

Zahlbar bis 31.07.2026
2% Skonto bei Zahlung bis 10.07.2026

IBAN: DE89 3704 0044 0532 0130 00
"""


def test_extracts_supplier():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.supplier == "Mustermann Bau GmbH"


def test_extracts_invoice_number():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.invoice_number == "2026-045"


def test_extracts_invoice_date():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.invoice_date == "01.07.2026"


def test_extracts_total_amount_and_currency():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.total_amount == 4250.00
    assert result.currency == "EUR"


def test_extracts_due_date():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.due_date == "31.07.2026"


def test_extracts_skonto():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.skonto_percent == 2.0
    assert result.skonto_date == "10.07.2026"


def test_extracts_bank_account():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.bank_account == "DE89370400440532013000"


def test_bank_name_is_none_when_not_stated():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.bank_name is None


def test_missing_fields_are_none():
    result = parse_invoice_text("Ein Text ganz ohne Rechnungsdaten.")
    assert result.total_amount is None
    assert result.due_date is None
    assert result.skonto_percent is None
    assert result.bank_account is None


# Real invoices don't always label the supplier clearly, put the amount in a
# separate table row, or use a "." thousands separator. These regressions
# cover formats found in practice.

CUSTOMER_BLOCK_INVOICE = """
Rechnung 998877
Firma
Kunde Beispiel GmbH
Musterstraße 1
10719 Berlin

Sachbearbeiter: Max Beispiel
Telefon: +49 30 1234567 Email: buchhaltung@beispiel-baustoffe.de

Pos Artikel Menge Einheit Preis Gesamt EUR
Pos. 1: Testartikel

Rechnungsbetrag skontofähiger Betrag Netto MwSt-% MwSt Endbetrag EUR
100,00 84,03 19,00 15,97 100,00

Zahlbetrag mit 3,00% Skonto bis 05.08.2026 : 97,00
Zahlbar bis 20.08.2026 ohne Abzug : 100,00
"""


def test_supplier_does_not_pick_up_customer_name():
    result = parse_invoice_text(CUSTOMER_BLOCK_INVOICE)
    assert result.supplier != "Kunde Beispiel GmbH"


def test_supplier_falls_back_to_email_domain():
    result = parse_invoice_text(CUSTOMER_BLOCK_INVOICE)
    assert result.supplier == "Beispiel Baustoffe"


def test_invoice_number_from_bare_rechnung_line():
    result = parse_invoice_text(CUSTOMER_BLOCK_INVOICE)
    assert result.invoice_number == "998877"


def test_amount_from_endbetrag_table_row():
    result = parse_invoice_text(CUSTOMER_BLOCK_INVOICE)
    assert result.total_amount == 100.00
    assert result.currency == "EUR"


def test_amount_with_space_thousands_separator():
    text = "Rechnungsbetrag..: 3 477,70 EUR"
    result = parse_invoice_text(text)
    assert result.total_amount == 3477.70


def test_invoice_number_and_date_from_rechnung_vom_pattern():
    text = "Kunden-Nr. 123, Rechnung 555444 vom 12.03.2026 Rechnungsbetrag 50,00 EUR"
    result = parse_invoice_text(text)
    assert result.invoice_number == "555444"
    assert result.invoice_date == "12.03.2026"


def test_skonto_date_falls_back_to_lastschrift_date():
    text = "2,0 % Skonto belasten wir Ihr Konto durch Lastschrift am 07.05.2026."
    result = parse_invoice_text(text)
    assert result.skonto_percent == 2.0
    assert result.skonto_date == "07.05.2026"


def test_bank_account_without_label_nearby():
    text = "Sparkasse Beispiel, BIC: ABCDDE00 DE11 4005 0150 0095 0003 03 UST-IdNr.: DE123456789"
    result = parse_invoice_text(text)
    assert result.bank_account == "DE11400501500095000303"
    assert result.bank_name == "Sparkasse Beispiel"


def test_bank_name_from_labeled_iban_line():
    text = "AKTIVBANK AG, Musterstr. 1, 12345 Musterstadt, IBAN: DE37 6003 0700 0460 0620 00, BIC: AKBADES1"
    result = parse_invoice_text(text)
    assert result.bank_account == "DE37600307000460062000"
    assert result.bank_name == "AKTIVBANK AG"


def test_bank_name_is_none_without_bank_account():
    result = parse_invoice_text("Ein Text ganz ohne Rechnungsdaten.")
    assert result.bank_name is None


def test_bank_name_found_on_line_above_iban():
    text = (
        "Bankverbindung: Commerzbank AG, Musterstadt\n"
        "IBAN DE88 8108 0000 0313 9347 00 · BIC ABCDDEFF"
    )
    result = parse_invoice_text(text)
    assert result.bank_account == "DE88810800000313934700"
    assert result.bank_name == "Commerzbank AG"


def test_due_date_from_ohne_abzug_pattern():
    text = "Bis zum 06.08.2026 ohne Abzug"
    result = parse_invoice_text(text)
    assert result.due_date == "06.08.2026"


def test_skonto_from_bis_zum_erhalten_sie_pattern():
    text = (
        "Bis zum 30.07.2026 erhalten Sie 2,000 % Skonto Zahlbetrag: 3,78 EUR\n"
        "Bis zum 06.08.2026 ohne Abzug"
    )
    result = parse_invoice_text(text)
    assert result.skonto_percent == 2.0
    assert result.skonto_date == "30.07.2026"
    assert result.skonto_amount == 3.78
    assert result.due_date == "06.08.2026"


def test_skonto_amount_is_none_when_not_stated():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.skonto_amount is None


# POS-style receipts (e.g. paid immediately by card) use "Beleg-Nr." instead
# of "Rechnung Nr." and state the actually-paid amount as "Gegeben: ...".

POS_RECEIPT = """
Beispiel Baustoff GmbH & Co.KG
Rechnung
Datum: 11.06.2026 13:11
Beleg-Nr.: 4261412100202

Brutto-Summe: 963,02EUR
- 2,00% Skonto: 19,26EUR
Brutto-Summe: 943,76EUR

Gegeben: EC-Cash 943,76EUR
"""


def test_invoice_number_from_beleg_nr_label():
    result = parse_invoice_text(POS_RECEIPT)
    assert result.invoice_number == "4261412100202"


def test_amount_from_gegeben_pattern():
    result = parse_invoice_text(POS_RECEIPT)
    assert result.total_amount == 943.76
    assert result.currency == "EUR"

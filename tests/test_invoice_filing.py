from app import invoice_filing


def test_build_invoice_filename_with_full_data():
    invoice = {
        "invoice_date": "29.06.2026",
        "supplier": "Brillux GmbH & Co. KG",
        "invoice_number": "7182750",
    }
    assert (
        invoice_filing.build_invoice_filename(invoice)
        == "260629 INV Brillux GmbH & Co. KG RE-NR. 7182750.pdf"
    )


def test_build_invoice_filename_sanitizes_supplier_name():
    invoice = {
        "invoice_date": "01.01.2026",
        "supplier": "Weird/Supplier: Name*?",
        "invoice_number": "123",
    }
    filename = invoice_filing.build_invoice_filename(invoice)
    assert filename == "260101 INV Weird-Supplier- Name-- RE-NR. 123.pdf"


def test_build_invoice_filename_falls_back_when_fields_missing():
    invoice = {"invoice_date": None, "supplier": None, "invoice_number": None, "id": 42}
    filename = invoice_filing.build_invoice_filename(invoice)
    assert "Unbekannt" in filename
    assert "RE-NR. 42" in filename


def test_build_invoice_filename_falls_back_to_created_at_date():
    invoice = {
        "invoice_date": None,
        "created_at": "2026-03-05 10:00:00",
        "supplier": "Foo GmbH",
        "invoice_number": "1",
    }
    filename = invoice_filing.build_invoice_filename(invoice)
    assert filename.startswith("260305 INV Foo GmbH")


def test_file_paid_invoice_writes_to_three_locations(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4 fake content")

    invoice = {
        "invoice_date": "29.06.2026",
        "supplier": "Brillux",
        "invoice_number": "7182750",
        "file_path": str(source),
    }

    base = tmp_path / "1. CIDE"
    written = invoice_filing.file_paid_invoice(invoice, str(base))

    assert len(written) == 3
    expected_filename = "260629 INV Brillux RE-NR. 7182750.pdf"
    assert (base / "03 Vertragspartner" / "Brillux" / expected_filename).read_bytes() == source.read_bytes()
    assert (
        base / "09 FIBU" / "2026" / "06 Juni 2026" / "01 Eingang" / expected_filename
    ).read_bytes() == source.read_bytes()
    assert (
        base / "09 FIBU" / "2026" / "06 Juni 2026" / "02 für Datev" / expected_filename
    ).read_bytes() == source.read_bytes()


def test_file_paid_invoice_reuses_existing_shorter_supplier_folder(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"content")

    base = tmp_path / "1. CIDE"
    (base / "03 Vertragspartner" / "Wego").mkdir(parents=True)
    (base / "03 Vertragspartner" / "Telekom").mkdir(parents=True)

    invoice = {
        "invoice_date": "28.07.2026",
        "supplier": "Wego Systembaustoffe GmbH",
        "invoice_number": "909674920",
        "file_path": str(source),
    }

    written = invoice_filing.file_paid_invoice(invoice, str(base))

    assert len(written) == 3
    expected_filename = "260728 INV wego RE-NR. 909674920.pdf"
    assert (base / "03 Vertragspartner" / "Wego" / expected_filename).exists()
    assert not (base / "03 Vertragspartner" / "Wego Systembaustoffe GmbH").exists()
    assert (
        base / "09 FIBU" / "2026" / "07 Juli 2026" / "01 Eingang" / expected_filename
    ).exists()


def test_file_paid_invoice_creates_new_folder_when_no_match_exists(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"content")

    base = tmp_path / "1. CIDE"
    (base / "03 Vertragspartner" / "Telekom").mkdir(parents=True)

    invoice = {
        "invoice_date": "01.01.2026",
        "supplier": "Brand New Supplier GmbH",
        "invoice_number": "1",
        "file_path": str(source),
    }

    written = invoice_filing.file_paid_invoice(invoice, str(base))

    assert len(written) == 3
    assert (base / "03 Vertragspartner" / "Brand New Supplier GmbH").is_dir()


def test_file_paid_invoice_without_base_path_returns_empty(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"content")
    invoice = {"invoice_date": "01.01.2026", "supplier": "Foo", "invoice_number": "1", "file_path": str(source)}

    assert invoice_filing.file_paid_invoice(invoice, None) == []
    assert invoice_filing.file_paid_invoice(invoice, "") == []


def test_file_paid_invoice_without_source_file_returns_empty(tmp_path):
    invoice = {
        "invoice_date": "01.01.2026",
        "supplier": "Foo",
        "invoice_number": "1",
        "file_path": str(tmp_path / "does-not-exist.pdf"),
    }
    assert invoice_filing.file_paid_invoice(invoice, str(tmp_path / "base")) == []


def test_file_paid_invoice_with_invalid_base_path_does_not_crash(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"content")
    invoice = {
        "invoice_date": "01.01.2026",
        "supplier": "Foo",
        "invoice_number": "1",
        "file_path": str(source),
    }

    invalid_base = "Z:\\this\\drive\\does\\not\\exist"
    assert invoice_filing.file_paid_invoice(invoice, invalid_base) == []

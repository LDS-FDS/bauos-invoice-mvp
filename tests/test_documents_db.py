from app import customers_db, documents_db

SAMPLE_CUSTOMER = {
    "name": "Muster Immobilien GmbH",
    "street": "Musterstraße 1",
    "zip_code": "10719",
    "city": "Berlin",
    "email": "kontakt@muster-immobilien.de",
    "phone": "030 1234567",
}

SAMPLE_ITEMS = [
    {"description": "Trockenbauarbeiten", "quantity": 10, "unit": "Std.", "unit_price": 45.0, "tax_rate": 19.0},
    {"description": "Material", "quantity": 1, "unit": "Pauschal", "unit_price": 120.0, "tax_rate": 19.0},
]


def _setup(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)
    documents_db.init_documents_tables(db_path)
    customer_id = customers_db.create_customer(SAMPLE_CUSTOMER, db_path)
    return db_path, customer_id


def test_create_document_computes_totals(tmp_path):
    db_path, customer_id = _setup(tmp_path)

    document_id = documents_db.create_document(
        "angebot", customer_id, SAMPLE_ITEMS, db_path=db_path
    )
    document = documents_db.get_document(document_id, db_path)

    assert document["net_total"] == 570.0
    assert document["tax_total"] == 108.3
    assert document["gross_total"] == 678.3
    assert len(document["items"]) == 2
    assert document["customer"]["name"] == "Muster Immobilien GmbH"


def test_doc_number_increments_per_type_and_year(tmp_path):
    db_path, customer_id = _setup(tmp_path)

    first = documents_db.create_document("angebot", customer_id, SAMPLE_ITEMS, db_path=db_path)
    second = documents_db.create_document("angebot", customer_id, SAMPLE_ITEMS, db_path=db_path)
    rechnung = documents_db.create_document("rechnung", customer_id, SAMPLE_ITEMS, db_path=db_path)

    first_doc = documents_db.get_document(first, db_path)
    second_doc = documents_db.get_document(second, db_path)
    rechnung_doc = documents_db.get_document(rechnung, db_path)

    assert first_doc["doc_number"].startswith("ANG-")
    assert first_doc["doc_number"] != second_doc["doc_number"]
    assert rechnung_doc["doc_number"].startswith("RE-")


def test_new_document_status_is_entwurf(tmp_path):
    db_path, customer_id = _setup(tmp_path)
    document_id = documents_db.create_document("angebot", customer_id, SAMPLE_ITEMS, db_path=db_path)

    assert documents_db.get_document(document_id, db_path)["status"] == "entwurf"


def test_list_documents_filters_by_type(tmp_path):
    db_path, customer_id = _setup(tmp_path)
    documents_db.create_document("angebot", customer_id, SAMPLE_ITEMS, db_path=db_path)
    documents_db.create_document("rechnung", customer_id, SAMPLE_ITEMS, db_path=db_path)

    angebote = documents_db.list_documents("angebot", db_path)
    rechnungen = documents_db.list_documents("rechnung", db_path)
    all_docs = documents_db.list_documents(db_path=db_path)

    assert len(angebote) == 1
    assert len(rechnungen) == 1
    assert len(all_docs) == 2
    assert angebote[0]["customer_name"] == "Muster Immobilien GmbH"


def test_update_document_status(tmp_path):
    db_path, customer_id = _setup(tmp_path)
    document_id = documents_db.create_document("angebot", customer_id, SAMPLE_ITEMS, db_path=db_path)

    updated = documents_db.update_document_status(document_id, "angenommen", db_path)

    assert updated is True
    assert documents_db.get_document(document_id, db_path)["status"] == "angenommen"


def test_update_unknown_document_status_returns_false(tmp_path):
    db_path, _ = _setup(tmp_path)
    assert documents_db.update_document_status(9999, "angenommen", db_path) is False


def test_delete_document_also_deletes_items(tmp_path):
    db_path, customer_id = _setup(tmp_path)
    document_id = documents_db.create_document("angebot", customer_id, SAMPLE_ITEMS, db_path=db_path)

    deleted = documents_db.delete_document(document_id, db_path)

    assert deleted is True
    assert documents_db.get_document(document_id, db_path) is None


def test_convert_angebot_to_invoice(tmp_path):
    db_path, customer_id = _setup(tmp_path)
    angebot_id = documents_db.create_document(
        "angebot", customer_id, SAMPLE_ITEMS, notes="Test-Angebot", db_path=db_path
    )

    invoice_id = documents_db.convert_to_invoice(angebot_id, db_path)
    invoice = documents_db.get_document(invoice_id, db_path)

    assert invoice["doc_type"] == "rechnung"
    assert invoice["doc_number"].startswith("RE-")
    assert invoice["converted_from_id"] == angebot_id
    assert invoice["notes"] == "Test-Angebot"
    assert len(invoice["items"]) == 2
    assert invoice["net_total"] == 570.0


def test_convert_non_angebot_returns_none(tmp_path):
    db_path, customer_id = _setup(tmp_path)
    rechnung_id = documents_db.create_document(
        "rechnung", customer_id, SAMPLE_ITEMS, db_path=db_path
    )

    assert documents_db.convert_to_invoice(rechnung_id, db_path) is None


def test_convert_unknown_document_returns_none(tmp_path):
    db_path, _ = _setup(tmp_path)
    assert documents_db.convert_to_invoice(9999, db_path) is None

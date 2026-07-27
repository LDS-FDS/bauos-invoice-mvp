from app import customers_db

SAMPLE_CUSTOMER = {
    "name": "Muster Immobilien GmbH",
    "street": "Musterstraße 1",
    "zip_code": "10719",
    "city": "Berlin",
    "email": "kontakt@muster-immobilien.de",
    "phone": "030 1234567",
}


def test_create_and_get_customer(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)

    customer_id = customers_db.create_customer(SAMPLE_CUSTOMER, db_path)
    stored = customers_db.get_customer(customer_id, db_path)

    assert stored["name"] == "Muster Immobilien GmbH"
    assert stored["city"] == "Berlin"


def test_list_customers_sorted_by_name(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)

    customers_db.create_customer({**SAMPLE_CUSTOMER, "name": "Zeta Bau"}, db_path)
    customers_db.create_customer({**SAMPLE_CUSTOMER, "name": "Alpha Bau"}, db_path)

    customers = customers_db.list_customers(db_path)

    assert [c["name"] for c in customers] == ["Alpha Bau", "Zeta Bau"]


def test_update_customer(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)
    customer_id = customers_db.create_customer(SAMPLE_CUSTOMER, db_path)

    updated = customers_db.update_customer(
        customer_id, {**SAMPLE_CUSTOMER, "city": "Hamburg"}, db_path
    )

    assert updated is True
    assert customers_db.get_customer(customer_id, db_path)["city"] == "Hamburg"


def test_update_unknown_customer_returns_false(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)

    assert customers_db.update_customer(9999, SAMPLE_CUSTOMER, db_path) is False


def test_delete_customer(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)
    customer_id = customers_db.create_customer(SAMPLE_CUSTOMER, db_path)

    deleted = customers_db.delete_customer(customer_id, db_path)

    assert deleted is True
    assert customers_db.get_customer(customer_id, db_path) is None

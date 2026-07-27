from app import company_settings

SAMPLE_SETTINGS = {
    "name": "CIDE Concept GmbH",
    "street": "Knesebeckstr. 62",
    "zip_code": "10719",
    "city": "Berlin",
    "email": "info@cide-concept.de",
    "phone": "030 1234567",
    "tax_id": "DE123456789",
    "bank_name": "Musterbank",
    "bank_iban": "DE89370400440532013000",
    "default_payment_term_days": 14,
}


def test_get_company_settings_returns_empty_defaults_when_unset(tmp_path):
    db_path = tmp_path / "test.db"
    company_settings.init_company_settings_table(db_path)

    settings = company_settings.get_company_settings(db_path)

    assert settings["name"] is None


def test_save_and_get_company_settings(tmp_path):
    db_path = tmp_path / "test.db"
    company_settings.init_company_settings_table(db_path)

    company_settings.save_company_settings(SAMPLE_SETTINGS, db_path)
    settings = company_settings.get_company_settings(db_path)

    assert settings["name"] == "CIDE Concept GmbH"
    assert settings["bank_iban"] == "DE89370400440532013000"
    assert settings["default_payment_term_days"] == 14


def test_save_company_settings_overwrites_existing(tmp_path):
    db_path = tmp_path / "test.db"
    company_settings.init_company_settings_table(db_path)
    company_settings.save_company_settings(SAMPLE_SETTINGS, db_path)

    company_settings.save_company_settings({**SAMPLE_SETTINGS, "city": "Hamburg"}, db_path)
    settings = company_settings.get_company_settings(db_path)

    assert settings["city"] == "Hamburg"

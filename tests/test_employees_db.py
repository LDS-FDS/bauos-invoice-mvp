from app import employees_db, time_entries_db

SAMPLE_EMPLOYEE = {"name": "Max Mustermann", "hourly_rate": 25.0}


def _setup(tmp_path):
    db_path = tmp_path / "test.db"
    employees_db.init_employees_table(db_path)
    time_entries_db.init_time_entries_table(db_path)
    return db_path


def test_create_and_get_employee(tmp_path):
    db_path = _setup(tmp_path)

    employee_id = employees_db.create_employee(SAMPLE_EMPLOYEE, db_path)
    stored = employees_db.get_employee(employee_id, db_path)

    assert stored["name"] == "Max Mustermann"
    assert stored["hourly_rate"] == 25.0


def test_list_employees_sorted_by_name(tmp_path):
    db_path = _setup(tmp_path)

    employees_db.create_employee({**SAMPLE_EMPLOYEE, "name": "Zeta"}, db_path)
    employees_db.create_employee({**SAMPLE_EMPLOYEE, "name": "Alpha"}, db_path)

    employees = employees_db.list_employees(db_path)

    assert [e["name"] for e in employees] == ["Alpha", "Zeta"]


def test_update_employee(tmp_path):
    db_path = _setup(tmp_path)
    employee_id = employees_db.create_employee(SAMPLE_EMPLOYEE, db_path)

    updated = employees_db.update_employee(
        employee_id, {**SAMPLE_EMPLOYEE, "hourly_rate": 30.0}, db_path
    )

    assert updated is True
    assert employees_db.get_employee(employee_id, db_path)["hourly_rate"] == 30.0


def test_update_unknown_employee_returns_false(tmp_path):
    db_path = _setup(tmp_path)

    assert employees_db.update_employee(9999, SAMPLE_EMPLOYEE, db_path) is False


def test_delete_employee(tmp_path):
    db_path = _setup(tmp_path)
    employee_id = employees_db.create_employee(SAMPLE_EMPLOYEE, db_path)

    deleted = employees_db.delete_employee(employee_id, db_path)

    assert deleted is True
    assert employees_db.get_employee(employee_id, db_path) is None


def test_delete_employee_removes_its_time_entries(tmp_path):
    from app import projects_db

    db_path = _setup(tmp_path)
    projects_db.init_projects_table(db_path)
    employee_id = employees_db.create_employee(SAMPLE_EMPLOYEE, db_path)
    project_id = projects_db.create_project({"name": "Baustelle A"}, db_path)
    time_entries_db.create_time_entry(project_id, employee_id, "01.08.2026", 8, 25.0, db_path)

    employees_db.delete_employee(employee_id, db_path)

    assert time_entries_db.list_time_entries_for_project(project_id, db_path) == []

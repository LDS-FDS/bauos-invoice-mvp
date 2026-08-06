from app import employees_db, projects_db, time_entries_db

SAMPLE_PROJECT = {"name": "Sanierung Musterstraße 5", "status": "aktiv"}
SAMPLE_EMPLOYEE = {"name": "Max Mustermann", "hourly_rate": 25.0}


def _setup(tmp_path):
    db_path = tmp_path / "test.db"
    projects_db.init_projects_table(db_path)
    employees_db.init_employees_table(db_path)
    time_entries_db.init_time_entries_table(db_path)
    return db_path


def _project_and_employee(db_path):
    project_id = projects_db.create_project(SAMPLE_PROJECT, db_path)
    employee_id = employees_db.create_employee(SAMPLE_EMPLOYEE, db_path)
    return project_id, employee_id


def test_create_and_list_time_entry(tmp_path):
    db_path = _setup(tmp_path)
    project_id, employee_id = _project_and_employee(db_path)

    time_entries_db.create_time_entry(project_id, employee_id, "01.08.2026", 8, 25.0, db_path)

    entries = time_entries_db.list_time_entries_for_project(project_id, db_path)
    assert len(entries) == 1
    assert entries[0]["employee_name"] == "Max Mustermann"
    assert entries[0]["hours"] == 8
    assert entries[0]["hourly_rate"] == 25.0
    assert entries[0]["cost"] == 200.0


def test_labor_cost_total_sums_multiple_entries(tmp_path):
    db_path = _setup(tmp_path)
    project_id, employee_id = _project_and_employee(db_path)

    time_entries_db.create_time_entry(project_id, employee_id, "01.08.2026", 8, 25.0, db_path)
    time_entries_db.create_time_entry(project_id, employee_id, "02.08.2026", 4, 25.0, db_path)

    assert time_entries_db.get_labor_cost_total(project_id, db_path) == 300.0


def test_rate_change_does_not_affect_existing_entries(tmp_path):
    db_path = _setup(tmp_path)
    project_id, employee_id = _project_and_employee(db_path)
    time_entries_db.create_time_entry(project_id, employee_id, "01.08.2026", 8, 25.0, db_path)

    employees_db.update_employee(employee_id, {**SAMPLE_EMPLOYEE, "hourly_rate": 40.0}, db_path)

    entries = time_entries_db.list_time_entries_for_project(project_id, db_path)
    assert entries[0]["hourly_rate"] == 25.0
    assert entries[0]["cost"] == 200.0


def test_delete_time_entry(tmp_path):
    db_path = _setup(tmp_path)
    project_id, employee_id = _project_and_employee(db_path)
    entry_id = time_entries_db.create_time_entry(
        project_id, employee_id, "01.08.2026", 8, 25.0, db_path
    )

    deleted = time_entries_db.delete_time_entry(entry_id, db_path)

    assert deleted is True
    assert time_entries_db.list_time_entries_for_project(project_id, db_path) == []


def test_delete_unknown_time_entry_returns_false(tmp_path):
    db_path = _setup(tmp_path)

    assert time_entries_db.delete_time_entry(9999, db_path) is False

import sqlite3

import evernote2obsidian as e2o


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("create table notebooks (guid text, name text, stack text)")
    conn.execute(
        "create table notes "
        "(guid text, notebook_guid text, title text, is_active integer, raw_note blob)"
    )
    return conn


def test_get_notebooks_from_db_returns_dicts():
    conn = _make_conn()
    conn.execute("insert into notebooks values (?, ?, ?)", ("g1", "Notebook A", None))
    conn.execute(
        "insert into notebooks values (?, ?, ?)", ("g2", "Notebook B", "Stack1")
    )
    conn.commit()

    notebooks = e2o.get_notebooks_from_db(conn)

    assert notebooks == [
        {"guid": "g1", "name": "Notebook A", "stack": None},
        {"guid": "g2", "name": "Notebook B", "stack": "Stack1"},
    ]


def test_get_notes_from_notebook_filters_and_orders_case_insensitively():
    conn = _make_conn()
    conn.execute(
        "insert into notes values (?, ?, ?, ?, ?)", ("n2", "g1", "Apple", 1, b"y")
    )
    conn.execute(
        "insert into notes values (?, ?, ?, ?, ?)",
        ("n3", "g2", "Other notebook", 1, b"z"),
    )
    conn.execute(
        "insert into notes values (?, ?, ?, ?, ?)", ("n1", "g1", "banana", 1, b"x")
    )
    conn.commit()

    rows = list(e2o.get_notes_from_notebook(conn, "g1"))

    assert [raw_note for _is_active, raw_note in rows] == [b"y", b"x"]

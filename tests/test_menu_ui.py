import json
import os
import sqlite3
from unittest.mock import Mock

import pytest

import evernote2obsidian as e2o


def _make_db_file(tmp_path, notebooks, notes):
    """notebooks: list of (guid, name, stack). notes: list of (guid, notebook_guid, is_active)."""
    path = tmp_path / "test.db"
    conn = sqlite3.connect(str(path))
    conn.execute("create table notebooks (guid text, name text, stack text)")
    conn.execute(
        "create table notes "
        "(guid text, notebook_guid text, title text, is_active integer, raw_note blob)"
    )
    conn.executemany("insert into notebooks values (?, ?, ?)", notebooks)
    conn.executemany(
        "insert into notes values (?, ?, ?, ?, ?)",
        [(guid, nb_guid, "t", active, b"") for guid, nb_guid, active in notes],
    )
    conn.commit()
    conn.close()
    return str(path)


class TestCfgMenu:
    def test_back_immediately_returns_true_with_no_changes(
        self, stub_dialogs, isolated_cfg
    ):
        original_database = isolated_cfg["database"]
        stub_dialogs.queue_radiolist(None)

        result = e2o.cfg_menu()

        assert result is True
        assert isolated_cfg["database"] == original_database
        assert len(stub_dialogs.radiolist_calls) == 1
        assert stub_dialogs.input_calls == []
        assert stub_dialogs.checkboxlist_calls == []

    def test_edits_str_option(self, stub_dialogs, isolated_cfg):
        isolated_cfg["database"] = "old.db"
        stub_dialogs.queue_radiolist("database", None)
        stub_dialogs.queue_input("new.db")

        e2o.cfg_menu()

        assert isolated_cfg["database"] == "new.db"
        assert stub_dialogs.input_calls[0]["default"] == "old.db"

    def test_casts_int_option(self, stub_dialogs, isolated_cfg):
        stub_dialogs.queue_radiolist("max_path_len", None)
        stub_dialogs.queue_input("999")  # input_dialog always returns text

        e2o.cfg_menu()

        assert isolated_cfg["max_path_len"] == 999
        assert isinstance(isolated_cfg["max_path_len"], int)

    def test_bool_option_false_persists(self, stub_dialogs, isolated_cfg):
        # Regression test: the source correctly uses `if new_value is not None:`
        # rather than `if new_value:`, so False must actually persist.
        isolated_cfg["overwrite"] = True
        stub_dialogs.queue_radiolist("overwrite", False, None)

        e2o.cfg_menu()

        assert isolated_cfg["overwrite"] is False
        assert stub_dialogs.radiolist_calls[1]["values"] == [
            (True, "True"),
            (False, "False"),
        ]
        assert stub_dialogs.radiolist_calls[1]["default"] is True

    @pytest.mark.parametrize(
        "option,new_value,expected_options",
        [
            ("pdf_view", "preview", ["default", "title", "preview"]),
            (
                "log_level",
                "critical",
                ["debug", "info", "warning", "error", "critical"],
            ),
        ],
    )
    def test_edits_list_option(
        self, stub_dialogs, isolated_cfg, option, new_value, expected_options
    ):
        stub_dialogs.queue_radiolist(option, new_value, None)

        e2o.cfg_menu()

        assert isolated_cfg[option] == new_value
        assert stub_dialogs.radiolist_calls[1]["values"] == [
            (v, v) for v in expected_options
        ]

    @pytest.mark.parametrize(
        "option,new_value,expect_restart",
        [
            ("log_file", "new.log", 1),
            ("database", "new.db", 0),
        ],
    )
    def test_restart_log_only_for_log_file_option(
        self, stub_dialogs, isolated_cfg, monkeypatch, option, new_value, expect_restart
    ):
        restart_mock = Mock()
        monkeypatch.setattr(e2o, "restart_log", restart_mock)
        stub_dialogs.queue_radiolist(option, None)
        stub_dialogs.queue_input(new_value)

        e2o.cfg_menu()

        assert restart_mock.call_count == expect_restart

    def test_cancel_sub_dialog_does_not_change_or_save(
        self, stub_dialogs, isolated_cfg
    ):
        isolated_cfg["database"] = "old.db"
        stub_dialogs.queue_radiolist("database", None)
        stub_dialogs.queue_input(None)  # user cancels the sub-dialog

        e2o.cfg_menu()

        assert isolated_cfg["database"] == "old.db"
        assert not os.path.exists(e2o.cfg.file_name)

    def test_handles_multiple_edits_in_one_session(self, stub_dialogs, isolated_cfg):
        # Proves the recursive `return cfg_menu()` actually loops and terminates.
        # Call order: outer->"database", str sub-dialog (input), outer->"overwrite",
        # bool sub-dialog (radiolist)->False, outer->None (stop).
        stub_dialogs.queue_radiolist("database", "overwrite", False, None)
        stub_dialogs.queue_input("a.db")

        e2o.cfg_menu()

        assert isolated_cfg["database"] == "a.db"
        assert isolated_cfg["overwrite"] is False
        assert len(stub_dialogs.radiolist_calls) == 4


class TestSelNbMenu:
    def test_missing_db_returns_false(self, stub_dialogs, isolated_cfg, tmp_path):
        isolated_cfg["database"] = str(tmp_path / "does_not_exist.db")

        result = e2o.sel_nb_menu()

        assert result is False
        assert stub_dialogs.checkboxlist_calls == []

    def test_builds_checkbox_values_from_db(self, stub_dialogs, isolated_cfg, tmp_path):
        # Bug (fixed separately on branch fix/notebook-sort-none-stack): a
        # notebook with no stack sorts under the literal string "None" instead
        # of "", so it can land out of alphabetical order relative to stacked
        # notebooks. This dataset demonstrates that: "Middle / Item" (stacked)
        # currently sorts *before* "Apple" (no stack), even though "Apple"
        # should come first alphabetically. Update this once that fix lands.
        db_path = _make_db_file(
            tmp_path,
            notebooks=[("gA", "Apple", None), ("gB", "Item", "Middle")],
            notes=[
                ("n1", "gA", 1),
                ("n2", "gA", 1),
                ("n3", "gA", 0),
                ("n4", "gB", 1),
                ("n5", "orphan-guid", 1),
            ],
        )
        isolated_cfg["database"] = db_path
        isolated_cfg["notebooks"] = ["gA"]
        stub_dialogs.queue_checkboxlist(None)

        e2o.sel_nb_menu()

        call = stub_dialogs.checkboxlist_calls[0]
        assert call["title"] == "Select notebooks to export"
        assert "DB has 2 notebooks, 4 active notes, 1 del. notes" in call["text"]
        assert call["values"] == [
            ("gA", "Apple (2)"),
            ("gB", "Middle / Item (1)"),
        ]
        assert call["default_values"] == ["gA"]

    def test_saves_selection(self, stub_dialogs, isolated_cfg, tmp_path):
        db_path = _make_db_file(
            tmp_path, notebooks=[("gA", "Solo", None)], notes=[("n1", "gA", 1)]
        )
        isolated_cfg["database"] = db_path
        stub_dialogs.queue_checkboxlist(["gA"])

        result = e2o.sel_nb_menu()

        assert result is True
        assert isolated_cfg["notebooks"] == ["gA"]
        with open(e2o.cfg.file_name, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["notebooks"] == ["gA"]

    def test_cancelled_selection_leaves_cfg_unchanged(
        self, stub_dialogs, isolated_cfg, tmp_path
    ):
        db_path = _make_db_file(
            tmp_path, notebooks=[("gA", "Solo", None)], notes=[("n1", "gA", 1)]
        )
        isolated_cfg["database"] = db_path
        isolated_cfg["notebooks"] = ["gZ"]
        stub_dialogs.queue_checkboxlist(None)

        result = e2o.sel_nb_menu()

        # Unlike the "missing database" case (the only path returning False),
        # sel_nb_menu still returns True here even though nothing was saved.
        assert result is True
        assert isolated_cfg["notebooks"] == ["gZ"]
        assert not os.path.exists(e2o.cfg.file_name)

    def test_empty_db(self, stub_dialogs, isolated_cfg, tmp_path):
        db_path = _make_db_file(tmp_path, notebooks=[], notes=[])
        isolated_cfg["database"] = db_path
        stub_dialogs.queue_checkboxlist(None)

        e2o.sel_nb_menu()

        call = stub_dialogs.checkboxlist_calls[0]
        assert call["values"] == []
        assert "DB has 0 notebooks, 0 active notes, 0 del. notes" in call["text"]


class TestCustomCheckboxlistDialog:
    def test_all_and_none_buttons_set_current_values(self, monkeypatch):
        captured_buttons = []
        real_button = e2o.Button

        def spy_button(text, handler):
            captured_buttons.append((text, handler))
            return real_button(text=text, handler=handler)

        monkeypatch.setattr(e2o, "Button", spy_button)

        captured = {}
        real_checkboxlist = e2o.CheckboxList

        def spy_checkboxlist(*args, **kwargs):
            instance = real_checkboxlist(*args, **kwargs)
            captured["cb_list"] = instance
            return instance

        monkeypatch.setattr(e2o, "CheckboxList", spy_checkboxlist)

        values = [("k1", "Label 1"), ("k2", "Label 2"), ("k3", "Label 3")]
        e2o.custom_checkboxlist_dialog(values=values, default_values=["k2"])

        cb_list = captured["cb_list"]
        assert cb_list.current_values == ["k2"]

        button_texts = [text for text, _handler in captured_buttons]
        assert button_texts == ["All", "None", "Ok", "Cancel"]

        all_handler = captured_buttons[0][1]
        all_handler()
        assert cb_list.current_values == ["k1", "k2", "k3"]

        none_handler = captured_buttons[1][1]
        none_handler()
        assert cb_list.current_values == []


class TestMainMenu:
    def test_lists_all_seven_actions(self, stub_dialogs):
        stub_dialogs.queue_radiolist(None)

        e2o.main_menu()

        values = stub_dialogs.radiolist_calls[0]["values"]
        assert {fn for fn, _label in values} == {
            e2o.cfg_menu,
            e2o.sel_nb_menu,
            e2o.list_db,
            e2o.scan_db,
            e2o.export_html,
            e2o.export_md,
            e2o.scan_vault,
        }

    def test_dispatches_to_first_entry(self, stub_dialogs, monkeypatch):
        monkeypatch.setattr(e2o, "cfg_menu", lambda: "CFG_SENTINEL")
        stub_dialogs.queue_radiolist(e2o.cfg_menu)

        assert e2o.main_menu() == "CFG_SENTINEL"

    def test_dispatches_to_last_entry(self, stub_dialogs, monkeypatch):
        monkeypatch.setattr(e2o, "scan_vault", lambda: "SCAN_SENTINEL")
        stub_dialogs.queue_radiolist(e2o.scan_vault)

        assert e2o.main_menu() == "SCAN_SENTINEL"

    def test_quit_returns_false_without_calling_anything(
        self, stub_dialogs, monkeypatch
    ):
        export_md_mock = Mock()
        monkeypatch.setattr(e2o, "export_md", export_md_mock)
        stub_dialogs.queue_radiolist(None)

        result = e2o.main_menu()

        assert result is False
        assert export_md_mock.call_count == 0


class TestMain:
    def test_loops_while_main_menu_truthy(self, monkeypatch):
        mock = Mock(side_effect=[True, True, False])
        monkeypatch.setattr(e2o, "main_menu", mock)

        e2o.main()

        assert mock.call_count == 3

    def test_stops_immediately_when_main_menu_falsy(self, monkeypatch):
        mock = Mock(return_value=False)
        monkeypatch.setattr(e2o, "main_menu", mock)

        e2o.main()

        assert mock.call_count == 1

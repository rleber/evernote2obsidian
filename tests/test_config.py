import json

import evernote2obsidian as e2o


def test_missing_file_falls_back_to_defaults(tmp_path):
    cfg_file = tmp_path / "missing_config.json"
    cfg = e2o.Config(default={"a": 1, "b": "two"}, file_name=str(cfg_file))
    assert dict(cfg) == {"a": 1, "b": "two"}


def test_existing_file_overrides_defaults(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"a": 42}), encoding="utf-8")

    cfg = e2o.Config(default={"a": 1, "b": "two"}, file_name=str(cfg_file))

    assert cfg["a"] == 42
    assert cfg["b"] == "two"


def test_invalid_json_falls_back_to_defaults(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{not valid json", encoding="utf-8")

    cfg = e2o.Config(default={"a": 1}, file_name=str(cfg_file))

    assert cfg["a"] == 1


def test_save_and_reload_round_trip(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg = e2o.Config(default={"a": 1}, file_name=str(cfg_file))
    cfg["a"] = 99
    cfg.save()

    reloaded = e2o.Config(default={"a": 1}, file_name=str(cfg_file))

    assert reloaded["a"] == 99

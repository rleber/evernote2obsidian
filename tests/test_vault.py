import evernote2obsidian as e2o


def _make_vault(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "note1.md").write_text("# Note 1\nLinks to [[note2]].", encoding="utf-8")
    (tmp_path / "sub" / "note2.md").write_text("Target note.", encoding="utf-8")
    (tmp_path / "sub" / "image.png").write_bytes(b"PNGDATA")


def test_read_vault_collects_md_and_attachment_files(tmp_path, monkeypatch):
    _make_vault(tmp_path)
    monkeypatch.chdir(tmp_path)

    md_data, abs_paths, all_paths = e2o.read_vault(".")

    assert md_data == {
        "./note1.md": "# Note 1\nLinks to [[note2]].",
        "./sub/note2.md": "Target note.",
    }
    assert abs_paths == {"./sub/image.png": {"links": 0}}
    assert all_paths["note1.md"] == 1
    assert all_paths["note2.md"] == 1
    assert all_paths["image.png"] == 1


def test_read_vault_on_empty_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    md_data, abs_paths, all_paths = e2o.read_vault(".")

    assert md_data == {}
    assert abs_paths == {}
    assert all_paths == {}


def test_scan_vault_reports_expected_stats(tmp_path, monkeypatch, capsys, isolated_cfg):
    (tmp_path / "note1.md").write_text(
        "Links to [[note2]] and [[missing]], plus [ext](https://example.com).",
        encoding="utf-8",
    )
    (tmp_path / "note2.md").write_text("Links back [[note1]].", encoding="utf-8")
    (tmp_path / "attachment.txt").write_text("not markdown", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *_args: "")
    isolated_cfg["output_folder_md"] = "."

    e2o.scan_vault()

    captured = capsys.readouterr().out
    assert f"  {'Scanned notes':24}: {2:9,}" in captured
    assert f"  {'Non-Markdown files':24}: {1:9,}" in captured
    assert f"  {'External links':24}: {1:9,}" in captured
    assert f"  {'Internal links':24}: {3:9,}" in captured
    assert f"  {'Internal links not found':24}: {1:9,}" in captured
    assert f"  {'File name conflicts':24}: {0:9,}" in captured

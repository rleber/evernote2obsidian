import evernote2obsidian as e2o


class TestHasEmoji:
    def test_detects_emoji(self):
        assert e2o.has_emoji("Hello \U0001f600 world") is True

    def test_plain_text_has_no_emoji(self):
        assert e2o.has_emoji("Hello world") is False

    def test_japanese_text_is_excluded(self):
        # The emoji regex deliberately excludes Japanese/Kanji ranges.
        assert e2o.has_emoji("こんにちは") is False


class TestIsInvalidObsidianTitle:
    def test_valid_title_returns_false(self, isolated_cfg):
        isolated_cfg["check_emojis"] = True
        assert e2o.is_invalid_obsidian_title("My Note") is False

    def test_invalid_chars_are_reported(self, isolated_cfg):
        isolated_cfg["check_emojis"] = False
        result = e2o.is_invalid_obsidian_title("a/b:c")
        assert result == "/ :"

    def test_emoji_flagged_when_check_emojis_enabled(self, isolated_cfg):
        isolated_cfg["check_emojis"] = True
        result = e2o.is_invalid_obsidian_title("Party \U0001f389")
        assert result == "emoji"

    def test_emoji_ignored_when_check_emojis_disabled(self, isolated_cfg):
        isolated_cfg["check_emojis"] = False
        assert e2o.is_invalid_obsidian_title("Party \U0001f389") is False


class TestRepeatedStrings:
    def test_no_duplicates_returns_zero(self):
        assert e2o.repeated_strings(["a", "b", "c"], "msg") == 0

    def test_counts_case_and_whitespace_insensitive_duplicates(self):
        count = e2o.repeated_strings([" Note ", "note", "NOTE", "other"], "msg")
        assert count == 1

    def test_ignores_falsy_entries(self):
        assert e2o.repeated_strings(["a", "", None, "a"], "msg") == 1


class TestSafePath:
    def test_replaces_invalid_characters(self):
        assert e2o.safe_path("My:Note/Name?") == "My_Note_Name_"

    def test_strips_surrounding_whitespace(self):
        assert e2o.safe_path("  a/b  ") == "a_b"

    def test_valid_path_is_unchanged(self):
        assert e2o.safe_path("Notes  - 2026") == "Notes  - 2026"


class TestEvernoteTagToObsidian:
    def test_spaces_become_dashes(self, isolated_cfg):
        assert e2o.evernote_tag_to_obsidian("My Tag") == "My-Tag"

    def test_numeric_tag_gets_prefixed(self, isolated_cfg):
        isolated_cfg["numeric_tag_prefix"] = "tag-"
        assert e2o.evernote_tag_to_obsidian("2026") == "tag-2026"

    def test_non_numeric_tag_is_not_prefixed(self, isolated_cfg):
        isolated_cfg["numeric_tag_prefix"] = "tag-"
        assert e2o.evernote_tag_to_obsidian("Project") == "Project"


class TestSafeJoin:
    def test_joins_and_sanitizes_each_part(self):
        assert e2o.safe_join("folder:1", "sub/note") == "folder_1/sub_note"

    def test_skips_empty_parts(self):
        assert e2o.safe_join("a", "", None, "b") == "a/b"


class TestToPosix:
    def test_converts_backslashes(self):
        assert e2o.to_posix(r"a\b\c") == "a/b/c"

    def test_leaves_forward_slashes_alone(self):
        assert e2o.to_posix("a/b/c") == "a/b/c"


class TestGetUniqueFilename:
    def test_returns_original_when_no_conflict(self):
        assert e2o.get_unique_filename("note.md", set()) == "note.md"

    def test_appends_counter_on_conflict(self):
        existing = {"note.md"}
        assert e2o.get_unique_filename("note.md", existing) == "note(1).md"

    def test_increments_counter_until_free(self):
        existing = {"note.md", "note(1).md"}
        assert e2o.get_unique_filename("note.md", existing) == "note(2).md"

    def test_is_case_insensitive(self):
        existing = {"note.md"}
        assert e2o.get_unique_filename("Note.md", existing) == "Note(1).md"

    def test_handles_filenames_without_extension(self):
        existing = {"readme"}
        assert e2o.get_unique_filename("README", existing) == "README(1)"

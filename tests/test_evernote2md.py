from evernote2md import EvernoteHTMLToMarkdownConverter


def convert(html, use_html=True, **kwargs):
    converter = EvernoteHTMLToMarkdownConverter(use_html=use_html)
    return converter.convert_html_to_markdown(html, **kwargs)


class TestInlineFormatting:
    def test_bold(self):
        md, warnings = convert("<div>Hello <b>world</b>!</div>")
        assert md == "Hello **world**!\n"
        assert warnings == []

    def test_italic_and_strikethrough(self):
        md, _warnings = convert("<div>Some <i>italic</i> and <s>strike</s>.</div>")
        assert md == "Some _italic_ and ~~strike~~.\n"

    def test_underline_kept_as_html_and_warns(self):
        md, warnings = convert("<div><u>underline</u></div>", use_html=True)
        assert md == "<u>underline</u>\n"
        assert warnings == ["Added unsupported HTML: u"]

    def test_underline_removed_when_html_disabled(self):
        md, warnings = convert("<div><u>underline</u></div>", use_html=False)
        assert md == "underline\n"
        assert warnings == ["Removed unsupported HTML: u"]

    def test_inline_code(self):
        md, _warnings = convert("<div><code>x = 1</code></div>")
        assert md == "`x = 1`\n"

    def test_multiline_code_becomes_fenced_block(self):
        md, _warnings = convert("<div><code>line1\nline2</code></div>")
        assert md == "```\nline1\nline2\n```\n"

    def test_blockquote(self):
        md, _warnings = convert("<div><blockquote>Quoted text</blockquote></div>")
        assert md == "> Quoted text\n"


class TestHeaders:
    def test_h1(self):
        md, _warnings = convert("<div><h1>Title</h1></div>")
        assert md == "# Title\n"

    def test_h3(self):
        md, _warnings = convert("<div><h3>Subtitle</h3></div>")
        assert md == "### Subtitle\n"


class TestLists:
    def test_unordered_list(self):
        md, _warnings = convert("<div><ul><li>one</li><li>two</li></ul></div>")
        assert md == "- one\n- two\n"

    def test_ordered_list(self):
        md, _warnings = convert("<div><ol><li>one</li><li>two</li></ol></div>")
        assert md == "1. one\n2. two\n"

    def test_nested_list_is_indented(self):
        md, _warnings = convert(
            "<div><ul><li>one<ul><li>nested</li></ul></li><li>two</li></ul></div>"
        )
        assert md == "- one\n       - nested\n- two\n"


class TestCheckboxes:
    def test_checked_task(self):
        md, _warnings = convert('<div><en-todo checked="true"/>Done task</div>')
        assert md == "- [x] Done task\n"

    def test_unchecked_task(self):
        md, _warnings = convert('<div><en-todo checked="false"/>Not done</div>')
        assert md == "- [ ] Not done\n"


class TestTables:
    def test_basic_table(self):
        html = "<div><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table></div>"
        md, warnings = convert(html)
        assert md == "\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
        assert warnings == []

    def test_nested_table_falls_back_to_html(self):
        html = "<div><table><tr><td><table><tr><td>x</td></tr></table></td></tr></table></div>"
        md, warnings = convert(html)
        assert md == "<table><tr><td><table><tr><td>x</td></tr></table></td></tr></table>\n"
        assert warnings == ["Nested tables are not supported, returning HTML"]

    def test_colspan(self):
        html = (
            "<table>"
            '<tr><td colspan="2">wide</td></tr>'
            "<tr><td>a</td><td>b</td></tr>"
            "</table>"
        )
        md, _warnings = convert(html)
        assert md == "\n| wide |  |\n| --- | --- |\n| a | b |\n"

    def test_rowspan(self):
        html = (
            "<table>"
            '<tr><td rowspan="2">tall</td><td>a</td></tr>'
            "<tr><td>b</td></tr>"
            "</table>"
        )
        md, _warnings = convert(html)
        assert md == "\n| tall | a |\n| --- | --- |\n|  | b |\n"

    def test_cell_alignment_from_child_style(self):
        html = (
            "<table><tr>"
            '<td><div style="text-align:center;">mid</div></td>'
            "<td>left</td>"
            "</tr></table>"
        )
        md, _warnings = convert(html)
        assert md == "\n| mid | left |\n| :-: | --- |\n"


class TestLinks:
    def test_external_link(self):
        md, _warnings = convert('<div><a href="https://example.com">Example</a></div>')
        assert md == "[Example](https://example.com)\n"

    def test_link_with_space_in_href_gets_angle_brackets(self):
        md, _warnings = convert(
            '<div><a href="https://example.com/a b">Example spaced</a></div>'
        )
        assert md == "[Example spaced](<https://example.com/a b>)\n"

    def test_internal_evernote_link_resolved_to_wikilink(self):
        guid = "1a2b3c4d-1234-5678-9abc-def012345678"
        html = f'<div><a href="evernote:///view/123/s1/{guid}/{guid}/">Internal</a></div>'
        md, warnings = convert(html, guid_to_path={guid: "Notes/Other"})
        assert md == "[[Notes/Other|Internal]]\n"
        assert warnings == []

    def test_internal_link_unresolved_falls_back_to_text_and_warns(self):
        guid = "1a2b3c4d-1234-5678-9abc-def012345678"
        html = f'<div><a href="evernote:///view/123/s1/{guid}/{guid}/">Missing</a></div>'
        md, warnings = convert(html)
        assert md == "[[Missing|Missing]]\n"
        assert warnings == [f"Path to link GUID not found: {guid} (Missing)"]

    def test_share_link_resolved_to_wikilink(self):
        guid = "1a2b3c4d-1234-5678-9abc-def012345678"
        html = f'<div><a href="https://share.evernote.com/note/{guid}">Shared</a></div>'
        md, _warnings = convert(html, guid_to_path={guid: "Notes/Shared"})
        assert md == "[[Notes/Shared|Shared]]\n"


class TestImages:
    def test_base64_image_kept_as_html_and_warns(self):
        html = '<div><img src="data:image/png;base64,AAA=" alt="pic" title="t" /></div>'
        md, warnings = convert(html)
        assert md == '<img src="data:image/png;base64,AAA=" alt="pic" title="t" />\n'
        assert warnings == ["Added base64 image"]

    def test_image_with_leading_slash_gets_resources_prefix(self):
        md, _warnings = convert('<div><img src="/resources/pic.png" alt="pic" /></div>')
        assert md == "![pic](./_resources/resources/pic.png)\n"


class TestMedia:
    def test_image_media_resolved_by_hash(self):
        html = '<en-media type="image/png" hash="1a2b3c" width="100px" />'
        md, warnings = convert(html, hash_to_path={int("1a2b3c", 16): "attachments/pic.png"})
        assert md == "![[attachments/pic.png\\|100]] "
        assert warnings == []

    def test_media_without_hash_is_dropped_and_warns(self):
        md, warnings = convert('<en-media type="" hash="" />')
        assert md == ""
        assert warnings == ['Media node without hash: <en-media hash="" type=""></en-media>']

    def test_media_with_unresolved_hash_falls_back_to_hex_and_warns(self):
        md, warnings = convert('<en-media type="image/png" hash="abcdef" />')
        assert md == "![[abcdef|abcdef]] "
        assert warnings == ["Path to media hash not found: abcdef"]

    def test_audio_media(self):
        html = '<en-media type="audio/mpeg" hash="1a2b3c" />'
        md, _warnings = convert(html, hash_to_path={int("1a2b3c", 16): "attachments/song.mp3"})
        assert md == "![[attachments/song.mp3|song.mp3]]\n"

    def test_pdf_media(self):
        html = '<en-media type="application/pdf" hash="1a2b3c" />'
        md, _warnings = convert(html, hash_to_path={int("1a2b3c", 16): "attachments/doc.pdf"})
        assert md == "![[attachments/doc.pdf|doc.pdf]]\n"


class TestDivSpecialCases:
    def test_code_block(self):
        html = '<div style="--en-codeblock:true; --en-syntaxLanguage:python;">print(1)</div>'
        md, _warnings = convert(html)
        assert md == "```python\nprint(1)```\n"

    def test_table_of_contents_is_replaced_with_notice(self):
        html = '<div style="--en-tableofcontents:true;">ignored content</div>'
        md, warnings = convert(html)
        assert "Table of Contents removed" in md
        assert warnings == ["Ignored Table of Contents (conversion not implemented)"]

    def test_task_group_found(self):
        html = '<div style="--en-task-group:true; --en-id:abc123;">ignored</div>'
        md, _warnings = convert(html, tasks={"abc123": "- [ ] task one\n"})
        assert md == "- [ ] task one\n"

    def test_task_group_not_found(self):
        html = '<div style="--en-task-group:true; --en-id:deadbeef;">ignored</div>'
        md, _warnings = convert(html)
        assert md == "- [ ] ==Could not find task(s) ID deadbeef during conversion==\n"

    def test_padding_left_indents_by_one_level_per_40px(self):
        md, _warnings = convert('<div style="padding-left:40px;">Indented</div>')
        assert md == "    Indented\n"

    def test_padding_left_indents_by_two_levels(self):
        md, _warnings = convert('<div style="padding-left:80px;">Indented more</div>')
        assert md == "        Indented more\n"

    def test_text_align_center_kept_as_html(self):
        md, warnings = convert('<div style="text-align:center;">Centered</div>', use_html=True)
        assert md == "<center>Centered</center>\n"
        assert warnings == ["Added unsupported HTML: text-align:center / <center>"]

    def test_text_align_center_removed_when_html_disabled(self):
        md, warnings = convert('<div style="text-align:center;">Centered</div>', use_html=False)
        assert md == "Centered\n"
        assert warnings == ["Removed unsupported HTML: text-align:center / <center>"]


class TestColorAndHighlight:
    def test_font_color_currently_loses_the_actual_color(self):
        # Known bug (fixed separately on branch fix/font-color-walrus-precedence):
        # `color := node.get("color") and self._use_html(...)` binds the walrus
        # to the whole `and` expression, so `color` ends up holding the boolean
        # result of _use_html() instead of the hex value. This test pins down
        # today's actual (buggy) output; update it once that fix lands.
        md, warnings = convert('<span><font color="#FF0000">Red text</font></span>')
        assert md == '<span style="color:True">Red text</span>'
        assert warnings == ["Added unsupported HTML: font color"]

    def test_yellow_highlight_becomes_markdown_highlight(self):
        html = '<div><span style="--en-highlight:yellow;">Highlighted</span></div>'
        md, warnings = convert(html)
        assert md == "==Highlighted==\n"
        assert warnings == ["Added unsupported HTML: highlight / background-color"]

    def test_other_highlight_color_kept_as_html(self):
        html = '<div><span style="--en-highlight:blue;">Highlighted blue</span></div>'
        md, _warnings = convert(html, use_html=True)
        assert md == '<span style="color: white; background-color: blue">Highlighted blue</span>\n'


class TestEscaping:
    def test_markdown_special_characters_are_escaped(self):
        html = "<div>Special chars: *bold* _em_ [link] `code` $math$ #tag ^caret ==high== ~~strike~~</div>"
        md, _warnings = convert(html)
        assert md == (
            "Special chars: \\*bold\\* \\_em_ \\[link\\] \\`code\\` \\$math\\$ "
            "\\#tag \\^caret \\=\\=high== \\~\\~strike~~\n"
        )

    def test_leading_markup_characters_are_escaped(self):
        html = "<div>- dash start\n+ plus start\n> quote start\n# hash start\n1. num start</div>"
        md, _warnings = convert(html)
        assert md == (
            "\\- dash start\n\\+ plus start\n\\> quote start\n"
            "\\# hash start\n1\\. num start\n"
        )

    def test_urls_are_not_escaped(self):
        html = "<div>Visit http://example.com/path_with_underscore now</div>"
        md, _warnings = convert(html)
        assert md == "Visit http://example.com/path_with_underscore now\n"

    def test_escape_brackets_option(self):
        md, _warnings = convert(
            "<div>[bracketed] text</div>", options={"escape_brackets": True}
        )
        assert md == "\\[bracketed\\] text\n"


class TestWarningsAggregation:
    def test_repeated_warnings_are_counted(self):
        md, warnings = convert("<div><u>a</u><u>b</u><u>c</u></div>")
        assert md == "<u>a</u><u>b</u><u>c</u>\n"
        assert warnings == ["Added unsupported HTML: u [3x]"]

    def test_distinct_warnings_are_sorted_most_common_first(self):
        html = '<div><u>a</u><u>b</u><span style="--en-highlight:blue;">x</span></div>'
        _md, warnings = convert(html)
        assert warnings == [
            "Added unsupported HTML: u [2x]",
            "Added unsupported HTML: highlight / background-color",
        ]


class TestProperties:
    def test_md_properties_are_prepended_as_front_matter(self):
        converter = EvernoteHTMLToMarkdownConverter()
        md, _warnings = converter.convert_html_to_markdown(
            "<div>Body</div>", md_properties=["Created at: 2026-01-01"]
        )
        assert md == "---\nCreated at: 2026-01-01\n---\nBody\n"

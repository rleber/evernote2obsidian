import types

import evernote2obsidian as e2o


def _note(guid="note1"):
    return types.SimpleNamespace(guid=guid)


def test_image_en_media_becomes_img_tag(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    hash_hex = "1a2b3c"
    hash_to_paths = {int(hash_hex, 16): {"note1": "attachments/photo.png"}}
    content = f'<en-media type="image/png" hash="{hash_hex}" width="100" height="50" />'

    result, errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == '<img src="attachments/photo.png" width="100" height="50" />'
    assert errors == []


def test_image_en_media_without_dimensions(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    hash_hex = "deadbeef"
    hash_to_paths = {int(hash_hex, 16): {"note1": "attachments/photo.png"}}
    content = f'<en-media type="image/jpeg" hash="{hash_hex}" />'

    result, _errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == '<img src="attachments/photo.png" />'


def test_non_image_media_becomes_simple_link_in_md_mode(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = True  # note_ext becomes ".md"
    exporter = e2o.Exporter_HTML()
    note = _note()
    hash_hex = "cafe01"
    hash_to_paths = {int(hash_hex, 16): {"note1": "attachments/movie.mp4"}}
    content = f'<en-media type="video/mp4" hash="{hash_hex}" />'

    result, _errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == '<a href="attachments/movie.mp4">attachments/movie.mp4</a>'


def test_video_media_in_html_mode_gets_video_tag(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    hash_hex = "cafe01"
    hash_to_paths = {int(hash_hex, 16): {"note1": "attachments/movie.mp4"}}
    content = f'<en-media type="video/mp4" hash="{hash_hex}" />'

    result, _errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == (
        '<video controls><source src="attachments/movie.mp4" type="video/mp4"></video>'
    )


def test_pdf_media_gets_iframe_by_default(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    hash_hex = "f00d"
    hash_to_paths = {int(hash_hex, 16): {"note1": "attachments/doc.pdf"}}
    content = f'<en-media type="application/pdf" hash="{hash_hex}" />'

    result, _errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == (
        '<iframe src="attachments/doc.pdf" width="100%" height="500px"></iframe>'
    )


def test_pdf_media_viewed_as_attachment_gets_link(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    hash_hex = "f00d"
    hash_to_paths = {int(hash_hex, 16): {"note1": "attachments/doc.pdf"}}
    content = (
        f'<en-media type="application/pdf" hash="{hash_hex}" '
        f'style="--en-viewAs:attachment;" />'
    )

    result, _errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == '<a href="attachments/doc.pdf">attachments/doc.pdf</a>'


def test_media_falls_back_to_any_path_when_note_guid_missing(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note(guid="note1")
    hash_hex = "1a2b3c"
    # Path is only recorded for a different note than the one being converted.
    hash_to_paths = {int(hash_hex, 16): {"other-note": "attachments/shared.png"}}
    content = f'<en-media type="image/png" hash="{hash_hex}" />'

    result, _errors = exporter.convert(note, content, {}, {}, hash_to_paths, {}, {})

    assert result == '<img src="attachments/shared.png" />'


def test_evernote_internal_link_resolved_by_guid(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    guid_to_path = {"guid-123": "Notebook/Other Note.html"}
    content = '<a href="evernote:///view/1/s1/guid-123/guid-123/">Other Note</a>'

    result, _errors = exporter.convert(note, content, guid_to_path, {}, {}, {}, {})

    assert result == '<a href="Notebook/Other Note.html">Other Note</a>'


def test_share_link_resolved_by_guid(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    guid_to_path = {"guid-456": "Notebook/Shared Note.html"}
    content = '<a href="https://share.evernote.com/note/guid-456">Shared</a>'

    result, _errors = exporter.convert(note, content, guid_to_path, {}, {}, {}, {})

    assert result == '<a href="Notebook/Shared Note.html">Shared</a>'


def test_unresolved_internal_link_falls_back_to_original_href(isolated_cfg):
    isolated_cfg["html_with_md_ext"] = False
    exporter = e2o.Exporter_HTML()
    note = _note()
    content = '<a href="evernote:///view/1/s1/unknown-guid/unknown-guid/">Missing</a>'

    result, _errors = exporter.convert(note, content, {}, {}, {}, {}, {})

    assert (
        result
        == '<a href="evernote:///view/1/s1/unknown-guid/unknown-guid/">Missing</a>'
    )

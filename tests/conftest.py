import copy

import pytest

import evernote2obsidian as e2o


@pytest.fixture(autouse=True)
def isolated_cfg():
    """Snapshot the module-global `cfg` and restore it after each test.

    `cfg` is a process-wide singleton loaded from the real config.json on
    import, and tests need to freely set options without leaking changes
    into other tests or touching that file (cfg.save() is never called here).
    """
    original = copy.deepcopy(dict(e2o.cfg))
    e2o.cfg["log_file"] = ""  # avoid writing to conversion.log during tests
    yield e2o.cfg
    e2o.cfg.clear()
    e2o.cfg.update(original)

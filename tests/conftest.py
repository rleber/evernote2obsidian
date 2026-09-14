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


@pytest.fixture(autouse=True)
def protect_real_config_file(monkeypatch, tmp_path):
    """Redirect cfg.save()/load() to a tmp file so no test can ever touch the
    real repo config.json (Config.file_name defaults to that literal path).
    """
    monkeypatch.setattr(e2o.cfg, "file_name", str(tmp_path / "config.json"))


class _DialogRun:
    """What a stubbed dialog factory returns: an object whose .run() gives back
    the next queued value, matching the real prompt_toolkit Application shape.
    """

    def __init__(self, value):
        self._value = value

    def run(self):
        return self._value


class DialogStub:
    """Stubs the prompt_toolkit dialog factories used by evernote2obsidian's
    menu functions. Each factory logs the kwargs it was called with and pops
    the next value off its own FIFO queue for .run() to return. Queueing too
    few values raises immediately, instead of hanging or opening a real dialog.
    """

    _NAMES = ("radiolist", "input", "button", "checkboxlist")

    def __init__(self, monkeypatch):
        for name in self._NAMES:
            setattr(self, f"{name}_calls", [])
            setattr(self, f"_{name}_queue", [])
        monkeypatch.setattr(e2o, "radiolist_dialog", self._factory("radiolist"))
        monkeypatch.setattr(e2o, "input_dialog", self._factory("input"))
        monkeypatch.setattr(e2o, "button_dialog", self._factory("button"))
        monkeypatch.setattr(
            e2o, "custom_checkboxlist_dialog", self._factory("checkboxlist")
        )

    def _factory(self, name):
        def factory(*_args, **kwargs):
            calls = getattr(self, f"{name}_calls")
            queue = getattr(self, f"_{name}_queue")
            calls.append(kwargs)
            if not queue:
                raise AssertionError(
                    f"{name}_dialog called with no queued response left "
                    f"(call #{len(calls)}); kwargs={kwargs}"
                )
            return _DialogRun(queue.pop(0))

        return factory

    def queue_radiolist(self, *values):
        self._radiolist_queue.extend(values)

    def queue_input(self, *values):
        self._input_queue.extend(values)

    def queue_button(self, *values):
        self._button_queue.extend(values)

    def queue_checkboxlist(self, *values):
        self._checkboxlist_queue.extend(values)


@pytest.fixture
def stub_dialogs(monkeypatch):
    return DialogStub(monkeypatch)

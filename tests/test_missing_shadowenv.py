import contextlib
import importlib.util
import io
import os
import sys
import types
import unittest
from unittest import mock


class _Window:
    def folders(self):
        return ["/tmp/project"]


class _TextCommand:
    pass


class _EventListener:
    pass


_sublime = types.ModuleType("sublime")
_sublime.active_window = lambda: _Window()
_sublime.error_message = mock.Mock()
_sublime.status_message = mock.Mock()
_sublime.set_timeout_async = mock.Mock()
_sublime_plugin = types.ModuleType("sublime_plugin")
_sublime_plugin.TextCommand = _TextCommand
_sublime_plugin.EventListener = _EventListener
_module_spec = importlib.util.spec_from_file_location(
    "shadowenv_missing_binary_under_test",
    os.path.join(os.path.dirname(__file__), "..", "shadowenv.py"),
)
shadowenv = importlib.util.module_from_spec(_module_spec)
with mock.patch.dict(
    sys.modules, {"sublime": _sublime, "sublime_plugin": _sublime_plugin}
):
    _module_spec.loader.exec_module(shadowenv)


class MissingShadowenvTests(unittest.TestCase):
    def setUp(self):
        _sublime.error_message.reset_mock()
        _sublime.status_message.reset_mock()

    def test_missing_binary_during_environment_load_shows_status(self):
        listener = shadowenv.ShadowenvProjectEnvironmentListener()
        listener.first_folder = "/tmp/project"

        with mock.patch.object(
            shadowenv.subprocess, "Popen", side_effect=FileNotFoundError
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                listener.shadowenv_stuff()

        _sublime.status_message.assert_called_once_with("shadowenv not found")
        _sublime.error_message.assert_not_called()

    def test_missing_binary_during_trust_shows_error(self):
        with mock.patch.object(
            shadowenv.subprocess, "Popen", side_effect=FileNotFoundError
        ):
            shadowenv.ShadowenvTrust().run(None)

        _sublime.error_message.assert_called_once_with("shadowenv not found")
        _sublime.status_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()

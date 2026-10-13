import contextlib
import importlib.util
import io
import json
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
_module_path = os.environ.get(
    "SHADOWENV_MODULE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "shadowenv.py"),
)
_module_spec = importlib.util.spec_from_file_location("shadowenv_under_test", _module_path)
shadowenv = importlib.util.module_from_spec(_module_spec)
with mock.patch.dict(sys.modules, {"sublime": _sublime, "sublime_plugin": _sublime_plugin}):
    _module_spec.loader.exec_module(shadowenv)


class ShadowenvEnvironmentTests(unittest.TestCase):
    def setUp(self):
        _sublime.error_message.reset_mock()
        _sublime.status_message.reset_mock()

    def run_hook(self, exported, unexported=None):
        output = json.dumps(
            {"exported": exported, "unexported": unexported or {}}
        ).encode()
        process = mock.Mock(returncode=0)
        process.communicate.return_value = output, b""
        listener = shadowenv.ShadowenvProjectEnvironmentListener()
        listener.first_folder = "/tmp/project"

        with mock.patch.object(shadowenv.subprocess, "Popen", return_value=process):
            with contextlib.redirect_stdout(io.StringIO()):
                listener.shadowenv_stuff()

        return listener

    def test_unsetting_missing_variable_does_not_interrupt_hook_update(self):
        key = "SUBLIME_SHADOWENV_TEST_UNSET_MISSING"
        old_value = os.environ.pop(key, None)
        try:
            listener = self.run_hook(
                {key: None}, {"__shadowenv_data": "next-state"}
            )
            self.assertNotIn(key, os.environ)
            self.assertEqual(listener.shadowenv_data, "next-state")
            _sublime.error_message.assert_not_called()
        finally:
            os.environ.pop(key, None)
            if old_value is not None:
                os.environ[key] = old_value

    def test_empty_string_is_exported_as_a_value(self):
        key = "SUBLIME_SHADOWENV_TEST_EMPTY_VALUE"
        old_value = os.environ.pop(key, None)
        try:
            self.run_hook({key: ""})
            self.assertIn(key, os.environ)
            self.assertEqual(os.environ[key], "")
        finally:
            os.environ.pop(key, None)
            if old_value is not None:
                os.environ[key] = old_value

    def test_unsetting_existing_variable_removes_it(self):
        key = "SUBLIME_SHADOWENV_TEST_UNSET_EXISTING"
        old_value = os.environ.get(key)
        os.environ[key] = "old-value"
        try:
            self.run_hook({key: None})
            self.assertNotIn(key, os.environ)
        finally:
            os.environ.pop(key, None)
            if old_value is not None:
                os.environ[key] = old_value


if __name__ == "__main__":
    unittest.main()

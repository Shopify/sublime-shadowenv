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
_source_path = os.environ.get(
    "SHADOWENV_MODULE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "shadowenv.py"),
)
_module_spec = importlib.util.spec_from_file_location(
    "shadowenv_under_test", _source_path
)
shadowenv = importlib.util.module_from_spec(_module_spec)
with mock.patch.dict(sys.modules, {"sublime": _sublime, "sublime_plugin": _sublime_plugin}):
    _module_spec.loader.exec_module(shadowenv)


class ShadowenvExitStatusTests(unittest.TestCase):
    def setUp(self):
        _sublime.error_message.reset_mock()
        _sublime.status_message.reset_mock()

    def test_successful_hook_applies_json_when_stderr_contains_warning(self):
        key = "SUBLIME_SHADOWENV_TEST_VALUE"
        previous = os.environ.pop(key, None)
        output = json.dumps({"exported": {key: "loaded"}, "unexported": {"__shadowenv_data": "next"}}).encode()
        process = mock.Mock(returncode=0)
        process.communicate.return_value = output, b"warning: harmless diagnostic"
        listener = shadowenv.ShadowenvProjectEnvironmentListener()
        listener.first_folder = "/tmp/project"

        try:
            with mock.patch.object(shadowenv.subprocess, "Popen", return_value=process):
                with contextlib.redirect_stdout(io.StringIO()):
                    listener.shadowenv_stuff()
            self.assertEqual(os.environ[key], "loaded")
            self.assertEqual(listener.shadowenv_data, "next")
            _sublime.error_message.assert_not_called()
        finally:
            os.environ.pop(key, None)
            if previous is not None:
                os.environ[key] = previous

    def test_failed_hook_does_not_apply_json_even_when_stdout_is_valid(self):
        key = "SUBLIME_SHADOWENV_TEST_VALUE"
        previous = os.environ.pop(key, None)
        output = json.dumps({"exported": {key: "must-not-apply"}, "unexported": {}}).encode()
        process = mock.Mock(returncode=1)
        process.communicate.return_value = output, b"hook failed"
        listener = shadowenv.ShadowenvProjectEnvironmentListener()
        listener.first_folder = "/tmp/project"

        try:
            with mock.patch.object(shadowenv.subprocess, "Popen", return_value=process):
                listener.shadowenv_stuff()
            self.assertNotIn(key, os.environ)
            _sublime.error_message.assert_called_once_with("shadowenv error: hook failed")
        finally:
            if previous is not None:
                os.environ[key] = previous

    def test_successful_trust_ignores_stderr_warning(self):
        process = mock.Mock(returncode=0)
        process.communicate.return_value = b"", b"warning: harmless diagnostic"

        with mock.patch.object(shadowenv.subprocess, "Popen", return_value=process):
            shadowenv.ShadowenvTrust().run(None)

        _sublime.error_message.assert_not_called()
        _sublime.status_message.assert_called_once_with("shadowenv trusted")

    def test_failed_trust_is_reported_even_without_stderr(self):
        process = mock.Mock(returncode=1)
        process.communicate.return_value = b"", b""

        with mock.patch.object(shadowenv.subprocess, "Popen", return_value=process):
            shadowenv.ShadowenvTrust().run(None)

        _sublime.error_message.assert_called_once_with(
            "shadowenv is not trusted: run shadowenv trust"
        )
        _sublime.status_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()

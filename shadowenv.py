import sublime
import sublime_plugin
import os
import os.path
import subprocess
import json

class ShadowenvTrust(sublime_plugin.TextCommand):
    def run(self, edit):
        folders = sublime.active_window().folders()
        if not folders:
            sublime.error_message("nothing seems to be open to trust")
            return None
        seproc = subprocess.Popen(
            ["shadowenv", "trust"],
            cwd=folders[0],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        output, error = seproc.communicate()
        if seproc.returncode != 0:
            sublime.error_message("shadowenv is not trusted: run shadowenv trust")
            return None
        if error:
            print("shadowenv trust warning: " + error.decode("utf-8", errors="replace"))
        sublime.status_message("shadowenv trusted")

class ShadowenvProjectEnvironmentListener(sublime_plugin.EventListener):
    def __init__(self, *args, **kwargs):
        super(ShadowenvProjectEnvironmentListener, self).__init__(*args, **kwargs)
        self.first_folder = None
        self.shadowenv_data = ""

    def on_activated(self, view):
        folders = sublime.active_window().folders()
        folder = folders[0] if folders else None

        if self.first_folder == folder:
            return
        else:
            self.first_folder = folder
            sublime.set_timeout_async(self.load_shadowenv, 0)

    def shadowenv_stuff(self):
        cwd = self.first_folder if self.first_folder else "/"
        print("using cwd: "+cwd)
        seproc = subprocess.Popen(
            ["shadowenv", "hook", "--json", self.shadowenv_data],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        output, error = seproc.communicate()
        if seproc.returncode != 0:
            error_text = error.decode("utf-8", errors="replace")
            if "untrusted" in error_text:
                sublime.error_message("shadowenv is not trusted: run shadowenv trust")
                return None
            else:
                if error_text:
                    sublime.error_message("shadowenv error: " + error_text)
                else:
                    sublime.error_message("shadowenv exited with status {}".format(seproc.returncode))
                return None
        if error:
            print("shadowenv warning: " + error.decode("utf-8", errors="replace"))

        if output:
            data = json.loads(output.decode("utf-8"))
            for name, value in data['exported'].items():
                if value:
                    os.environ[name] = value
                else:
                    del os.environ[name]
            for name, value in data['unexported'].items():
                if name == '__shadowenv_data':
                    self.shadowenv_data = value
                else:
                    sublime.error_message("shadowenv error: unexpected unexported value: " + name)
                    return
            print("shadowenv loaded")
            sublime.status_message("shadowenv loaded")

    def load_shadowenv(self):
        shadowenv_stuff = self.shadowenv_stuff()
        if not shadowenv_stuff:
            return

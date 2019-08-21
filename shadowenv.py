import sublime
import sublime_plugin
import os
import os.path
import subprocess
import json

class ShadowenvTrust(sublime_plugin.TextCommand):
    def run(self, edit):
        ff = (sublime.active_window().folders() or [])[0]
        if not ff:
            sublime.error_message("nothing seems to be open to trust")
            return None
        seproc = subprocess.Popen(
            ["shadowenv", "trust"],
            cwd=ff,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        output, error = seproc.communicate()
        if error:
            sublime.error_message("shadowenv is not trusted: run shadowenv trust")
            return None
        sublime.status_message("shadowenv trusted")

class ShadowenvProjectEnvironmentListener(sublime_plugin.EventListener):
    def __init__(self, *args, **kwargs):
        super(ShadowenvProjectEnvironmentListener, self).__init__(*args, **kwargs)
        self.first_folder = None
        self.shadowenv_data = ""

    def on_activated(self, view):
        ff = (sublime.active_window().folders() or [])[0]
        if self.first_folder == ff:
            return
        else:
            self.first_folder = ff
            if self.first_folder:
                sublime.set_timeout_async(self.load_shadowenv, 0)

    def shadowenv_stuff(self):
        seproc = subprocess.Popen(
            ["shadowenv", "hook", "--json", self.shadowenv_data],
            cwd=self.first_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        output, error = seproc.communicate()
        if error:
            if "untrusted" in error.decode():
                sublime.error_message("shadowenv is not trusted: run shadowenv trust")
                return None
            else:
                sublime.error_message("shadowenv error: "+error.decode())
                return None

        if output:
            data = json.loads(output.decode("utf-8"))
            for name, value in data['exported'].items():
                os.environ[name] = value
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

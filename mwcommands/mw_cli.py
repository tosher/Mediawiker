#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerCliCommand(sublime_plugin.WindowCommand):

    def run(self, url):
        if mw.get_setting('offline_mode'):
            return

        if url:
            url = mw.strunquote(url)
            sublime.set_timeout(lambda: self.window.run_command(mw.cmd('page'), {
                'action': mw.cmd('show_page'),
                'action_params': {'title': self.proto_replacer(url)}
            }), 1)

    def proto_replacer(self, url):
        if sublime.platform() == 'windows' and url.endswith('/'):
            url = url[:-1]
        elif sublime.platform() == 'linux' and url.startswith("'") and url.endswith("'"):
            url = url[1:-1]
        return url.split("://")[1]

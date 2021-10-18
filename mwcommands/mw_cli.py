#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerCliCommand(sublime_plugin.WindowCommand):

    def run(self, url):
        if url:
            url = utils.strunquote(url)
            sublime.set_timeout(lambda: self.window.run_command(utils.cmd('page'), {
                'action': utils.cmd('show_page'),
                'action_params': {'title': self.proto_replacer(url)}
            }), 1)

    def proto_replacer(self, url):
        if sublime.platform() == 'windows' and url.endswith('/'):
            url = url[:-1]
        elif sublime.platform() == 'linux' and url.startswith("'") and url.endswith("'"):
            url = url[1:-1]
        return url.split("://")[1]

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return True

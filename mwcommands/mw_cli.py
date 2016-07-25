#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin


class MediawikerCliCommand(sublime_plugin.WindowCommand):

    def run(self, url):
        if url:
            # print('Opening page: %s' % url)
            sublime.set_timeout(lambda: self.window.run_command("mediawiker_page", {"action": "mediawiker_show_page", "title": self.proto_replacer(url)}), 1)

    def proto_replacer(self, url):
        if sublime.platform() == 'windows' and url.endswith('/'):
            url = url[:-1]
        elif sublime.platform() == 'linux' and url.startswith("'") and url.endswith("'"):
            url = url[1:-1]
        return url.split("://")[1]

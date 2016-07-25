#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import webbrowser

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerOpenPageInBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
        url = mw.get_page_url()
        if url:
            webbrowser.open(url)
        else:
            sublime.status_message('Can\'t open page with empty title')
            return

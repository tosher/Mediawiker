#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import webbrowser
# import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerOpenPageInBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
        url = utils.get_page_url()
        if url:
            webbrowser.open(url)
        else:
            utils.error_message('Can\'t open page with empty title')
            return

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')

#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

# import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
else:
    import mw_utils as utils


class MediawikerShowRedLinksCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        page = utils.api.get_page(utils.get_title())
        utils.process_red_links(self.view, page)


class MediawikerHideRedLinksCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        if pythonver < 3:
            utils.status_message('Commands "Show red links/Hide red links" supported in Sublime text 3 only.')
            return

        self.view.erase_phantoms('redlink')


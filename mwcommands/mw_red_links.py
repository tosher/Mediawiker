#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerShowRedLinksCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        page = utils.api.get_page(utils.get_title())
        utils.process_red_links(self.view, page)

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.view, 'is_here')


class MediawikerHideRedLinksCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        self.view.erase_phantoms('redlink')

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.view, 'is_here')

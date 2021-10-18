#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerFavoritesAddCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = utils.get_title()
        utils.save_mypages(title=title, storage_name='favorites')

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerFavoritesOpenCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command(utils.cmd('page_list'), {'storage_name': 'favorites'})

    def is_visible(self, *args):
        return True

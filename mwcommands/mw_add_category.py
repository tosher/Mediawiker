#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
else:
    import mw_utils as utils


class MediawikerSetCategoryCommand(sublime_plugin.WindowCommand):
    ''' alias to Add category command '''

    def run(self):
        if utils.props.get_setting('offline_mode'):
            return

        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('add_category')})


class MediawikerAddCategoryCommand(sublime_plugin.TextCommand):
    categories_list = None

    category_root = ''
    category_options = [['Set category', ''], ['Open category', ''], ['Back to root', '']]

    # TODO: back in category tree..

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        self.category_root = utils.get_category(utils.props.get_setting('category_root'))[1]
        sublime.active_window().show_input_panel('Category:', self.category_root, self.get_category_menu, None, None)

    def get_category_menu(self, category_root):
        categories = utils.api.call('get_subcategories', category_root=category_root)
        self.categories_list_names = []
        self.categories_list_values = []

        self.categories_list_values.append(utils.api.page_attr(categories, 'name'))
        self.categories_list_names.append(utils.api.page_attr(categories, 'page_title'))

        for category in categories:
            if utils.api.page_attr(category, 'namespace') == utils.api.CATEGORY_NAMESPACE:
                self.categories_list_values.append(utils.api.page_attr(category, 'name'))
                self.categories_list_names.append(utils.api.page_attr(category, 'page_title'))

        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.categories_list_names, self.on_done), 1)

    def on_done(self, idx):
        # the dialog was cancelled
        if idx >= 0:
            self.category_options[0][1] = self.categories_list_values[idx]
            self.category_options[1][1] = self.categories_list_names[idx]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.category_options, self.on_done_final), 1)

    def set_category(self, category):
        index_of_textend = self.view.size()
        self.view.run_command(utils.cmd('insert_text'), {'position': index_of_textend, 'text': '[[%s]]' % category})
        self.view.show(self.view.size())

    def on_done_final(self, idx):
        if idx == 0:
            self.set_category(self.category_options[idx][1])
        elif idx == 1:
            self.get_category_menu(self.category_options[idx][1])
        else:
            self.get_category_menu(self.category_root)

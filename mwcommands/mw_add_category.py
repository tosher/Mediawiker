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


class MediawikerSetCategoryCommand(sublime_plugin.WindowCommand):
    ''' alias to Add category command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_category"})


class MediawikerAddCategoryCommand(sublime_plugin.TextCommand):
    categories_list = None
    title = ''
    sitecon = None

    category_root = ''
    category_options = [['Set category', ''], ['Open category', ''], ['Back to root', '']]

    # TODO: back in category tree..

    def run(self, edit, title, password):
        self.sitecon = mw.get_connect(password)
        self.category_root = mw.get_category(mw.get_setting('mediawiker_category_root'))[1]
        sublime.active_window().show_input_panel('Wiki root category:', self.category_root, self.get_category_menu, None, None)
        # self.get_category_menu(self.category_root)

    def get_category_menu(self, category_root):
        category = self.sitecon.Categories.get(category_root)
        self.categories_list_names = []
        self.categories_list_values = []

        for page in category:
            if page.namespace == mw.CATEGORY_NAMESPACE:
                self.categories_list_values.append(page.name)
                self.categories_list_names.append(page.name[page.name.find(':') + 1:])
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.categories_list_names, self.on_done), 1)

    def on_done(self, idx):
        # the dialog was cancelled
        if idx >= 0:
            self.category_options[0][1] = self.categories_list_values[idx]
            self.category_options[1][1] = self.categories_list_names[idx]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.category_options, self.on_done_final), 1)

    def on_done_final(self, idx):
        if idx == 0:
            # set category
            index_of_textend = self.view.size()
            self.view.run_command('mediawiker_insert_text', {'position': index_of_textend, 'text': '[[%s]]' % self.category_options[idx][1]})
        elif idx == 1:
            self.get_category_menu(self.category_options[idx][1])
        else:
            self.get_category_menu(self.category_root)

#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerCategoryTreeCommand(sublime_plugin.WindowCommand):
    ''' alias to Category list command '''

    def run(self):
        if utils.props.get_setting('offline_mode'):
            return

        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('category_list')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerCategoryListCommand(sublime_plugin.TextCommand):
    pages = {}  # pagenames -> namespaces
    pages_names = []  # pagenames for menu
    category_path = []
    CATEGORY_NEXT_PREFIX_MENU = '> '
    CATEGORY_PREV_PREFIX_MENU = '. . '
    category_prefix = ''  # "Category" namespace name as returned language..

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        if self.category_path:
            category_root = utils.get_category(self.get_category_current())[1]
        else:
            category_root = utils.get_category(utils.props.get_setting('category_root'))[1]
        sublime.active_window().show_input_panel('Wiki root category:', category_root, self.show_list, None, None)

    def show_list(self, category_root):
        if not category_root:
            return
        self.pages = {}
        self.pages_names = []

        category_root = utils.get_category(category_root)[1]

        if not self.category_path:
            self.update_category_path('{}:{}'.format(self.get_category_prefix(), category_root))

        if len(self.category_path) > 1:
            self.add_page(self.get_category_prev(), utils.api.CATEGORY_NAMESPACE, False)

        for page in self.get_list_data(category_root):
            page_name = utils.api.page_attr(page, 'name')
            page_namespace = utils.api.page_attr(page, 'namespace')
            if page_namespace == utils.api.CATEGORY_NAMESPACE and not self.category_prefix:
                self.category_prefix = utils.get_category(page_name)[0]
            self.add_page(page_name, page_namespace, True)
        if self.pages:
            self.pages_names.sort()
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.pages_names, self.get_page), 1)
        else:
            sublime.message_dialog('Category {} is empty'.format(category_root))

    def add_page(self, page_name, page_namespace, as_next=True):
        page_name_menu = page_name
        if page_namespace == utils.api.CATEGORY_NAMESPACE:
            page_name_menu = self.get_category_as_next(page_name) if as_next else self.get_category_as_prev(page_name)
        self.pages[page_name] = page_namespace
        self.pages_names.append(page_name_menu)

    def get_list_data(self, category_root):
        ''' get objects list by category name '''
        return utils.api.get_subcategories(category_root=category_root)

    def get_category_as_next(self, category_string):
        return '{}{}'.format(self.CATEGORY_NEXT_PREFIX_MENU, category_string)

    def get_category_as_prev(self, category_string):
        return '{}{}'.format(self.CATEGORY_PREV_PREFIX_MENU, category_string)

    def category_strip_special_prefix(self, category_string):
        return category_string.lstrip(self.CATEGORY_NEXT_PREFIX_MENU).lstrip(self.CATEGORY_PREV_PREFIX_MENU)

    def get_category_prev(self):
        ''' return previous category name in format Category:CategoryName'''
        return self.category_path[-2]

    def get_category_current(self):
        ''' return current category name in format Category:CategoryName'''
        return self.category_path[-1]

    def get_category_prefix(self):
        if self.category_prefix:
            return self.category_prefix
        else:
            return 'Category'

    def update_category_path(self, category_string):
        if category_string in self.category_path:
            self.category_path = self.category_path[:-1]
        else:
            self.category_path.append(self.category_strip_special_prefix(category_string))

    def get_page(self, index):
        if index >= 0:
            # escape from quick panel return -1
            page_name = self.category_strip_special_prefix(self.pages_names[index])
            if self.pages[page_name] == utils.api.CATEGORY_NAMESPACE:
                self.update_category_path(page_name)
                self.show_list(page_name)
            else:
                try:
                    sublime.active_window().run_command(utils.cmd('page'), {
                        'action': utils.cmd('show_page'),
                        'action_params': {
                            'title': page_name
                        }
                    })
                except ValueError as e:
                    sublime.message_dialog(e)


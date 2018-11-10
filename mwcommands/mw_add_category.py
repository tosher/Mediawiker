#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerSetCategoryCommand(sublime_plugin.WindowCommand):
    ''' alias to Add category command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('add_category')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class SCategories(object):
    TAB = ' ' * 4

    def __init__(self, root):
        self.cats = {}
        self.root = root
        self.root_title = utils.api.page_attr(self.root, 'page_title')
        self.root_name = utils.api.page_attr(self.root, 'name')

    def append(self, category):
        if utils.api.page_attr(category, 'namespace') == utils.api.CATEGORY_NAMESPACE:
            ctitle = utils.api.page_attr(category, 'page_title')
            self.cats[ctitle] = category

    def subtitles(self):
        return sorted([utils.api.page_attr(k, 'page_title') for k in self.cats.values()])

    def titles_menu(self):
        if self.root.exists and self.exists_subcategories():
            root_title_menu = self.root_title
        elif self.root.exists:
            root_title_menu = [
                self.root_title,
                'No sub-categories'
            ]
        else:
            root_title_menu = [
                self.root_title,
                'New category, no sub-categories'
            ]
        return [root_title_menu] + ['{}{}'.format(self.TAB, t) for t in self.subtitles()]

    def titles(self):
        return [self.root_title] + [t for t in self.subtitles()]

    def get(self, title):
        if title == self.root_title:
            return self.root
        return self.cats[title]

    def exists_subcategories(self):
        return len(self.cats.keys()) > 0


class MediawikerAddCategoryCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        self.category_title_default = utils.get_category(utils.props.get_setting('category_root'))[1]
        sublime.active_window().show_input_panel('Category:', self.category_title_default, self.category_menu_show, None, None)

    def update_categories(self, category_title):
        category = utils.api.get_page('{}:{}'.format('Category', category_title))
        self.cats = SCategories(root=category)
        subcategories = utils.api.call('get_subcategories', category_root=category_title)
        for category in subcategories:
            self.cats.append(category)

    def category_menu_show(self, category_title):
        self.update_categories(category_title)

        if self.cats.exists_subcategories():
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.cats.titles_menu(), self.category_action_select), 1)
        else:
            self.category_action_select(0)

    def category_action_select(self, idx):
        if idx >= 0:
            self.category_title = self.cats.titles()[idx]
            self.update_categories(self.category_title)
            category = self.cats.get(self.category_title)

            menu = []
            if category.exists:
                menu.append('Set category: {}'.format(self.category_title))
            else:
                menu.append('Set new category: {}'.format(self.category_title))

            menu.append('Open root category: {}'.format(self.category_title_default))

            if category.exists and self.cats.exists_subcategories():
                menu.append('Open category: {}'.format(self.category_title))

            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(menu, self.category_action_run), 1)

    def category_action_run(self, idx):
        if idx == 0:
            self.set_category(self.category_title)
        elif idx == 1:
            self.category_menu_show(self.category_title_default)
        elif idx == 2:
            self.category_menu_show(self.category_title)

    def set_category(self, category_title):
        index_of_textend = self.view.size()
        category = self.cats.get(self.category_title)
        self.view.run_command(
            utils.cmd('insert_text'),
            {
                'position': index_of_textend,
                'text': '[[{name}]]'.format(name=utils.api.page_attr(category, 'name'))
            }
        )
        self.view.show(self.view.size())

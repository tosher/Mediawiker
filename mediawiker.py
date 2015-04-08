#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
from os.path import basename
pythonver = sys.version_info[0]

import webbrowser
import re
import sublime
import sublime_plugin

# https://github.com/wbond/sublime_package_control/wiki/Sublime-Text-3-Compatible-Packages
# http://www.sublimetext.com/docs/2/api_reference.html
# http://www.sublimetext.com/docs/3/api_reference.html
# sublime.message_dialog

if pythonver >= 3:
    from . import mwutils as mw
else:
    import mwutils as mw

CATEGORY_NAMESPACE = 14  # category namespace number
IMAGE_NAMESPACE = 6  # image namespace number
TEMPLATE_NAMESPACE = 10  # template namespace number


class MediawikerInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text):
        self.view.insert(edit, position, text)


class MediawikerReplaceTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, text):
        self.view.replace(edit, self.view.sel()[0], text)


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    '''prepare all actions with wiki'''

    run_in_new_window = False
    title = None

    def run(self, action, title='', site_active=None):
        self.site_active = site_active
        self.action = action

        if self.action == 'mediawiker_show_page':
            if mw.get_setting('mediawiker_newtab_ongetpage'):
                self.run_in_new_window = True

            panel = mw.InputPanelPageTitle()
            panel.on_done = self.on_done
            panel.get_title(title)

        else:
            if self.action == 'mediawiker_reopen_page':
                self.action = 'mediawiker_show_page'
            title = title if title else mw.get_title()
            self.on_done(title)

    def on_done(self, title):
        if title:
            title = mw.pagename_clear(title)

        self.title = title
        panel_passwd = mw.InputPanelPassword()
        panel_passwd.command_run = self.command_run
        panel_passwd.get_password()

    def command_run(self, password):
        # cases:
        # from view with page, opened from other site_active than in global settings - new page will be from the same site
        # from view with page, open page with another lang site - site param must be defined, will set it
        # from view with undefined site (new) open page by global site_active setting
        if not self.site_active:
            self.site_active = mw.get_view_site()

        if self.run_in_new_window:
            self.window.new_file()
            self.run_in_new_window = False

        self.window.active_view().settings().set('mediawiker_site', self.site_active)
        self.window.active_view().run_command(self.action, {"title": self.title, "password": password})


class MediawikerOpenPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_show_page"})


class MediawikerReopenPageCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_reopen_page"})


class MediawikerPostPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Publish page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_publish_page"})


class MediawikerSetCategoryCommand(sublime_plugin.WindowCommand):
    ''' alias to Add category command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_category"})


class MediawikerInsertImageCommand(sublime_plugin.WindowCommand):
    ''' alias to Add image command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_image"})


class MediawikerInsertTemplateCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_template"})


class MediawikerFileUploadCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_upload"})


class MediawikerCategoryTreeCommand(sublime_plugin.WindowCommand):
    ''' alias to Category list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_category_list"})


class MediawikerSearchStringCommand(sublime_plugin.WindowCommand):
    ''' alias to Search string list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_search_string_list"})


class MediawikerPageListCommand(sublime_plugin.WindowCommand):

    def run(self, storage_name='mediawiker_pagelist'):
        # site_name_active = mw.get_setting('mediawiki_site_active')
        site_name_active = mw.get_view_site()
        mediawiker_pagelist = mw.get_setting(storage_name, {})
        self.my_pages = mediawiker_pagelist.get(site_name_active, [])
        if self.my_pages:
            self.my_pages.reverse()
            # error 'Quick panel unavailable' fix with timeout..
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.my_pages, self.on_done), 1)
        else:
            sublime.status_message('List of pages for wiki "%s" is empty.' % (site_name_active))

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            title = self.my_pages[index]
            try:
                self.window.run_command("mediawiker_page", {"title": title, "action": "mediawiker_show_page"})
            except ValueError as e:
                sublime.message_dialog(e)


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    def run(self, edit, title, password):
        is_writable = False
        sitecon = mw.get_connect(password)
        is_writable, text = mw.get_page_text(sitecon, title)
        self.view.set_syntax_file('Packages/Mediawiker/Mediawiki.tmLanguage')
        self.view.settings().set('mediawiker_is_here', True)
        self.view.settings().set('mediawiker_wiki_instead_editor', mw.get_setting('mediawiker_wiki_instead_editor'))
        self.view.set_name(title)

        if is_writable:
            if not text:
                sublime.status_message('Wiki page %s is not exists. You can create new..' % (title))
                text = '<!-- New wiki page: Remove this with text of the new page -->'
            # insert text
            self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': text})
        sublime.status_message('Page %s was opened successfully from %s.' % (title, mw.get_view_site()))
        self.view.set_scratch(True)
        # own is_changed flag instead of is_dirty for possib. to reset..
        self.view.settings().set('is_changed', False)


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit, title, password):
        is_skip_summary = mw.get_setting('mediawiker_skip_summary', False)
        sitecon = mw.get_connect(password)
        self.title = mw.get_title()
        if self.title:
            self.page = sitecon.Pages[self.title]
            if self.page.can('edit'):
                self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                if not is_skip_summary:
                    # summary_message = 'Changes summary (%s):' % mw.get_setting('mediawiki_site_active')
                    summary_message = 'Changes summary (%s):' % mw.get_view_site()
                    self.view.window().show_input_panel(summary_message, '', self.on_done, None, None)
                else:
                    self.on_done('')
            else:
                sublime.status_message('You have not rights to edit this page')
        else:
            sublime.status_message('Can\'t publish page with empty title')
            return

    def on_done(self, summary):
        summary = '%s%s' % (summary, mw.get_setting('mediawiker_summary_postfix', ' (by SublimeText.Mediawiker)'))
        mark_as_minor = mw.get_setting('mediawiker_mark_as_minor')
        try:
            if self.page.can('edit'):
                # invert minor settings command '!'
                if summary[0] == '!':
                    mark_as_minor = not mark_as_minor
                    summary = summary[1:]
                self.page.save(self.current_text, summary=summary.strip(), minor=mark_as_minor)
                self.view.set_scratch(True)
                self.view.settings().set('is_changed', False)  # reset is_changed flag
                sublime.status_message('Wiki page %s was successfully published to wiki.' % (self.title))
                mw.save_mypages(self.title)
            else:
                sublime.status_message('You have not rights to edit this page')
        except mw.mwclient.EditError as e:
            sublime.status_message('Can\'t publish page %s (%s)' % (self.title, e))


class MediawikerShowTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'^(={1,5})\s?(.*?)\s?={1,5}'

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        # self.items = map(self.get_header, self.regions)
        self.items = [self.get_header(x) for x in self.regions]
        sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_done), 1)

    def get_header(self, region):
        TAB_SIZE = ' ' * 4
        return re.sub(self.pattern, r'\1\2', self.view.substr(region)).replace('=', TAB_SIZE)[len(TAB_SIZE):]

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[index])
            self.view.sel().clear()
            self.view.sel().add(self.regions[index])


class MediawikerShowInternalLinksCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'\[{2}(.*?)(\|.*?)?\]{2}'
    actions = ['Goto internal link', 'Open page in editor', 'Open page in browser']
    selected = None

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        self.items = [mw.strunquote(self.get_header(x)) for x in self.regions]
        if self.items:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_select), 1)
        else:
            sublime.status_message('No internal links was found.')

    def get_header(self, region):
        return re.sub(self.pattern, r'\1', self.view.substr(region))

    def on_select(self, index):
        if index >= 0:
            self.selected = index
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def on_done(self, index):
        if index == 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[self.selected])
            self.view.sel().clear()
            self.view.sel().add(self.regions[self.selected])
        elif index == 1:
            sublime.set_timeout(lambda: self.view.window().run_command("mediawiker_page", {"action": "mediawiker_show_page", "title": self.items[self.selected]}), 1)
        elif index == 2:
            url = mw.get_page_url(self.items[self.selected])
            webbrowser.open(url)


class MediawikerShowExternalLinksCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'[^\[]\[{1}(\w.*?)(\s.*?)?\]{1}[^\]]'
    actions = ['Goto external link', 'Open link in browser']
    selected = None

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        self.items = [self.get_header(x) for x in self.regions]
        self.urls = [self.get_url(x) for x in self.regions]
        if self.items:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_select), 1)
        else:
            sublime.status_message('No external links was found.')

    def prepare_header(self, header):
        maxlen = 70
        link_url = mw.strunquote(header.group(1))
        link_descr = re.sub(r'<.*?>', '', header.group(2))
        postfix = '..' if len(link_descr) > maxlen else ''
        return '%s: %s%s' % (link_url, link_descr[:maxlen], postfix)

    def get_header(self, region):
        # return re.sub(self.pattern, r'\1: \2', self.view.substr(region))
        return re.sub(self.pattern, self.prepare_header, self.view.substr(region))

    def get_url(self, region):
        return re.sub(self.pattern, r'\1', self.view.substr(region))

    def on_select(self, index):
        if index >= 0:
            self.selected = index
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def on_done(self, index):
        if index == 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[self.selected])
            self.view.sel().clear()
            self.view.sel().add(self.regions[self.selected])
        elif index == 1:
            webbrowser.open(self.urls[self.selected])


class MediawikerEnumerateTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []

    def run(self, edit):
        self.items = []
        self.regions = []
        pattern = '^={1,5}(.*)?={1,5}'
        self.regions = self.view.find_all(pattern)
        header_level_number = [0, 0, 0, 0, 0]
        len_delta = 0
        for r in self.regions:
            if len_delta:
                # prev. header text was changed, move region to new position
                r_new = sublime.Region(r.a + len_delta, r.b + len_delta)
            else:
                r_new = r
            region_len = r_new.b - r_new.a
            header_text = self.view.substr(r_new)
            level = mw.get_hlevel(header_text, "=")
            current_number_str = ''
            i = 1
            # generate number value, start from 1
            while i <= level:
                position_index = i - 1
                header_number = header_level_number[position_index]
                if i == level:
                    # incr. number
                    header_number += 1
                    # save current number
                    header_level_number[position_index] = header_number
                    # reset sub-levels numbers
                    header_level_number[i:] = [0] * len(header_level_number[i:])
                if header_number:
                    current_number_str = "%s.%s" % (current_number_str, header_number) if current_number_str else '%s' % (header_number)
                # incr. level
                i += 1

            #get title only
            header_text_clear = header_text.strip(' =\t')
            header_text_clear = re.sub(r'^(\d\.)+\s+(.*)', r'\2', header_text_clear)
            header_tag = '=' * level
            header_text_numbered = '%s %s. %s %s' % (header_tag, current_number_str, header_text_clear, header_tag)
            len_delta += len(header_text_numbered) - region_len
            self.view.replace(edit, r_new, header_text_numbered)


class MediawikerSetActiveSiteCommand(sublime_plugin.WindowCommand):
    site_keys = []
    site_on = '> '
    site_off = ' ' * 4
    site_active = ''

    def run(self):
        # self.site_active = mw.get_setting('mediawiki_site_active')
        self.site_active = mw.get_view_site()
        sites = mw.get_setting('mediawiki_site')
        # self.site_keys = map(self.is_checked, list(sites.keys()))
        self.site_keys = [self.is_checked(x) for x in sites.keys()]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.site_keys, self.on_done), 1)

    def is_checked(self, site_key):
        checked = self.site_on if site_key == self.site_active else self.site_off
        return '%s%s' % (checked, site_key)

    def on_done(self, index):
        # not escaped
        if index >= 0:
            site_active = self.site_keys[index].strip()
            if site_active.startswith(self.site_on):
                site_active = site_active[len(self.site_on):]
            # force to set site_active in global and in view settings
            current_syntax = self.window.active_view().settings().get('syntax')
            if current_syntax is not None and current_syntax.endswith('Mediawiker/Mediawiki.tmLanguage'):
                self.window.active_view().settings().set('mediawiker_site', site_active)
            mw.set_setting("mediawiki_site_active", site_active)


class MediawikerOpenPageInBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
        url = mw.get_page_url()
        if url:
            webbrowser.open(url)
        else:
            sublime.status_message('Can\'t open page with empty title')
            return


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
        category = self.sitecon.Categories[category_root]
        self.categories_list_names = []
        self.categories_list_values = []

        for page in category:
            if page.namespace == CATEGORY_NAMESPACE:
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


class MediawikerCsvTableCommand(sublime_plugin.TextCommand):
    ''' selected text, csv data to wiki table '''

    delimiter = '|'

    # TODO: rewrite as simple to wiki command
    def run(self, edit):
        self.delimiter = mw.get_setting('mediawiker_csvtable_delimiter', '|')
        table_header = '{|'
        table_footer = '|}'
        table_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw.get_setting('mediawiker_wikitable_properties', {}).items()])
        cell_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw.get_setting('mediawiker_wikitable_cell_properties', {}).items()])
        if cell_properties:
            cell_properties = ' %s | ' % cell_properties

        for region in self.view.sel():
            table_data_dic_tmp = []
            table_data = ''
            # table_data_dic_tmp = map(self.get_table_data, self.view.substr(region).split('\n'))
            table_data_dic_tmp = [self.get_table_data(x) for x in self.view.substr(region).split('\n')]

            # verify and fix columns count in rows
            if table_data_dic_tmp:
                cols_cnt = len(max(table_data_dic_tmp, key=len))
                for row in table_data_dic_tmp:
                    if row:
                        while cols_cnt - len(row):
                            row.append('')

                for row in table_data_dic_tmp:
                    if row:
                        if table_data:
                            table_data += '\n|-\n'
                            column_separator = '||'
                        else:
                            table_data += '|-\n'
                            column_separator = '!!'

                        for col in row:
                            col_sep = column_separator if row.index(col) else column_separator[0]
                            table_data += '%s%s%s ' % (col_sep, cell_properties, col)

                self.view.replace(edit, region, '%s %s\n%s\n%s' % (table_header, table_properties, table_data, table_footer))

    def get_table_data(self, line):
        if self.delimiter in line:
            return line.split(self.delimiter)
        return []


class MediawikerEditPanelCommand(sublime_plugin.WindowCommand):
    options = []
    SNIPPET_CHAR = u'\u24C8'

    def run(self):
        self.SNIPPET_CHAR = mw.get_setting('mediawiker_snippet_char')
        self.options = mw.get_setting('mediawiker_panel', {})
        if self.options:
            office_panel_list = ['\t%s' % val['caption'] if val['type'] != 'snippet' else '\t%s %s' % (self.SNIPPET_CHAR, val['caption']) for val in self.options]
            self.window.show_quick_panel(office_panel_list, self.on_done)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            try:
                action_type = self.options[index]['type']
                action_value = self.options[index]['value']
                if action_type == 'snippet':
                    # run snippet
                    self.window.active_view().run_command("insert_snippet", {"name": action_value})
                elif action_type == 'window_command':
                    # run command
                    self.window.run_command(action_value)
                elif action_type == 'text_command':
                    # run command
                    self.window.active_view().run_command(action_value)
            except ValueError as e:
                sublime.status_message(e)


class MediawikerTableWikiToSimpleCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) wiki table to Simple table (TableEdit plugin) '''

    # TODO: wiki table properties will be lost now...
    def run(self, edit):
        selection = self.view.sel()
        table_region = None

        if not self.view.substr(selection[0]):
            table_region = self.table_getregion()
        else:
            table_region = selection[0]  # only first region will be proceed..

        if table_region:
            text = self.view.substr(table_region)
            text = self.table_fixer(text)
            self.view.replace(edit, table_region, self.table_get(text))
            # Turn on TableEditor
            try:
                self.view.run_command('table_editor_enable_for_current_view', {'prop': 'enable_table_editor'})
            except Exception as e:
                sublime.status_message('Need to correct install plugin TableEditor: %s' % e)

    def table_get(self, text):
        tbl_row_delimiter = r'\|\-(.*)'
        tbl_cell_delimiter = r'\n\s?\||\|\||\n\s?\!|\!\!'  # \n| or || or \n! or !!
        rows = re.split(tbl_row_delimiter, text)

        tbl_full = []
        for row in rows:
            if row and row[0] != '{':
                tbl_row = []
                cells = re.split(tbl_cell_delimiter, row, re.DOTALL)[1:]
                for cell in cells:
                    cell = cell.replace('\n', '')
                    cell = ' ' if not cell else cell
                    if cell[0] != '{' and cell[-1] != '}':
                        cell = self.delim_fixer(cell)
                        tbl_row.append(cell)
                tbl_full.append(tbl_row)

        tbl_full = self.table_print(tbl_full)
        return tbl_full

    def table_print(self, table_data):
        CELL_LEFT_BORDER = '|'
        CELL_RIGHT_BORDER = ''
        ROW_LEFT_BORDER = ''
        ROW_RIGHT_BORDER = '|'
        tbl_print = ''
        for row in table_data:
            if row:
                row_print = ''.join(['%s%s%s' % (CELL_LEFT_BORDER, cell, CELL_RIGHT_BORDER) for cell in row])
                row_print = '%s%s%s' % (ROW_LEFT_BORDER, row_print, ROW_RIGHT_BORDER)
                tbl_print += '%s\n' % (row_print)
        return tbl_print

    def table_getregion(self):
        cursor_position = self.view.sel()[0].begin()
        pattern = r'^\{\|(.*?\n?)*\|\}'
        regions = self.view.find_all(pattern)
        for reg in regions:
            if reg.a <= cursor_position <= reg.b:
                return reg

    def table_fixer(self, text):
        text = re.sub(r'(\{\|.*\n)(\s?)(\||\!)(\s?[^-])', r'\1\2|-\n\3\4', text)  # if |- skipped after {| line, add it
        return text

    def delim_fixer(self, string_data):
        REPLACE_STR = ':::'
        return string_data.replace('|', REPLACE_STR)


class MediawikerTableSimpleToWikiCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) Simple table (TableEditor plugin) to wiki table '''
    def run(self, edit):
        selection = self.view.sel()
        table_region = None
        if not self.view.substr(selection[0]):
            table_region = self.gettable()
        else:
            table_region = selection[0]  # only first region will be proceed..

        if table_region:
            text = self.view.substr(table_region)
            table_data = self.table_parser(text)
            self.view.replace(edit, table_region, self.drawtable(table_data))

    def table_parser(self, text):
        table_data = []
        TBL_HEADER_STRING = '|-'
        need_header = False
        if text.split('\n')[1][:2] == TBL_HEADER_STRING:
            need_header = True
        for line in text.split('\n'):
            if line:
                row_data = []
                if line[:2] == TBL_HEADER_STRING:
                    continue
                elif line[0] == '|':
                    cells = line[1:-1].split('|')  # without first and last char "|"
                    for cell_data in cells:
                        row_data.append({'properties': '', 'cell_data': cell_data, 'is_header': need_header})
                    if need_header:
                        need_header = False
            if row_data and type(row_data) is list:
                table_data.append(row_data)
        return table_data

    def gettable(self):
        cursor_position = self.view.sel()[0].begin()
        # ^([^\|\n].*)?\n\|(.*\n)*?\|.*\n[^\|] - all tables regexp (simple and wiki)?
        pattern = r'^\|(.*\n)*?\|.*\n[^\|]'
        regions = self.view.find_all(pattern)
        for reg in regions:
            if reg.a <= cursor_position <= reg.b:
                table_region = sublime.Region(reg.a, reg.b - 2)  # minus \n and [^\|]
                return table_region

    def drawtable(self, table_list):
        ''' draw wiki table '''
        TBL_START = '{|'
        TBL_STOP = '|}'
        TBL_ROW_START = '|-'
        CELL_FIRST_DELIM = '|'
        CELL_DELIM = '||'
        CELL_HEAD_FIRST_DELIM = '!'
        CELL_HEAD_DELIM = '!!'
        REPLACE_STR = ':::'

        text_wikitable = ''
        table_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw.get_setting('mediawiker_wikitable_properties', {}).items()])

        need_header = table_list[0][0]['is_header']
        is_first_line = True
        for row in table_list:
            if need_header or is_first_line:
                text_wikitable += '%s\n%s' % (TBL_ROW_START, CELL_HEAD_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_HEAD_DELIM, row)
                is_first_line = False
                need_header = False
            else:
                text_wikitable += '\n%s\n%s' % (TBL_ROW_START, CELL_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_DELIM, row)
                text_wikitable = text_wikitable.replace(REPLACE_STR, '|')

        return '%s %s\n%s\n%s' % (TBL_START, table_properties, text_wikitable, TBL_STOP)

    def getrow(self, delimiter, rowlist=None):
        if rowlist is None:
            rowlist = []
        cell_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw.get_setting('mediawiker_wikitable_cell_properties', {}).items()])
        cell_properties = '%s | ' % cell_properties if cell_properties else ''
        try:
            return delimiter.join(' %s%s ' % (cell_properties, cell['cell_data'].strip()) for cell in rowlist)
        except Exception as e:
            print('Error in data: %s' % e)


class MediawikerCategoryListCommand(sublime_plugin.TextCommand):
    password = ''
    pages = {}  # pagenames -> namespaces
    pages_names = []  # pagenames for menu
    category_path = []
    CATEGORY_NEXT_PREFIX_MENU = '> '
    CATEGORY_PREV_PREFIX_MENU = '. . '
    category_prefix = ''  # "Category" namespace name as returned language..

    def run(self, edit, title, password):
        self.password = password
        if self.category_path:
            category_root = mw.get_category(self.get_category_current())[1]
        else:
            category_root = mw.get_category(mw.get_setting('mediawiker_category_root'))[1]
        sublime.active_window().show_input_panel('Wiki root category:', category_root, self.show_list, None, None)

    def show_list(self, category_root):
        if not category_root:
            return
        self.pages = {}
        self.pages_names = []

        category_root = mw.get_category(category_root)[1]

        if not self.category_path:
            self.update_category_path('%s:%s' % (self.get_category_prefix(), category_root))

        if len(self.category_path) > 1:
            self.add_page(self.get_category_prev(), CATEGORY_NAMESPACE, False)

        for page in self.get_list_data(category_root):
            if page.namespace == CATEGORY_NAMESPACE and not self.category_prefix:
                    self.category_prefix = mw.get_category(page.name)[0]
            self.add_page(page.name, page.namespace, True)
        if self.pages:
            self.pages_names.sort()
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.pages_names, self.get_page), 1)
        else:
            sublime.message_dialog('Category %s is empty' % category_root)

    def add_page(self, page_name, page_namespace, as_next=True):
        page_name_menu = page_name
        if page_namespace == CATEGORY_NAMESPACE:
            page_name_menu = self.get_category_as_next(page_name) if as_next else self.get_category_as_prev(page_name)
        self.pages[page_name] = page_namespace
        self.pages_names.append(page_name_menu)

    def get_list_data(self, category_root):
        ''' get objects list by category name '''
        sitecon = mw.get_connect(self.password)
        return sitecon.Categories[category_root]

    def get_category_as_next(self, category_string):
        return '%s%s' % (self.CATEGORY_NEXT_PREFIX_MENU, category_string)

    def get_category_as_prev(self, category_string):
        return '%s%s' % (self.CATEGORY_PREV_PREFIX_MENU, category_string)

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
            if self.pages[page_name] == CATEGORY_NAMESPACE:
                self.update_category_path(page_name)
                self.show_list(page_name)
            else:
                try:
                    sublime.active_window().run_command("mediawiker_page", {"title": page_name, "action": "mediawiker_show_page"})
                except ValueError as e:
                    sublime.message_dialog(e)


class MediawikerSearchStringListCommand(sublime_plugin.TextCommand):
    password = ''
    title = ''
    search_limit = 20
    pages_names = []
    search_result = None

    def run(self, edit, title, password):
        self.password = password
        search_pre = ''
        selection = self.view.sel()
        search_pre = self.view.substr(selection[0]).strip()
        sublime.active_window().show_input_panel('Wiki search:', search_pre, self.show_results, None, None)

    def show_results(self, search_value=''):
        # TODO: paging?
        self.pages_names = []
        self.search_limit = mw.get_setting('mediawiker_search_results_count')
        if search_value:
            self.search_result = self.do_search(search_value)
        if self.search_result:
            for i in range(self.search_limit):
                try:
                    page_data = self.search_result.next()
                    self.pages_names.append([page_data['title'], page_data['snippet']])
                except:
                    pass
            te = ''
            search_number = 1
            for pa in self.pages_names:
                te += '### %s. %s\n* [%s](%s)\n\n%s\n' % (search_number, pa[0], pa[0], mw.get_page_url(pa[0]), self.antispan(pa[1]))
                search_number += 1

            if te:
                self.view = sublime.active_window().new_file()
                self.view.set_syntax_file('Packages/Markdown/Markdown.tmLanguage')
                self.view.set_name('Wiki search results: %s' % search_value)
                self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': te})
            elif search_value:
                sublime.message_dialog('No results for: %s' % search_value)

    def antispan(self, text):
        span_replace_open = "`"
        span_replace_close = "`"
        # bold and italic tags cut
        text = text.replace("'''", "")
        text = text.replace("''", "")
        # spans to bold
        text = re.sub(r'<span(.*?)>', span_replace_open, text)
        text = re.sub(r'<\/span>', span_replace_close, text)
        # divs cut
        text = re.sub(r'<div(.*?)>', '', text)
        text = re.sub(r'<\/div>', '', text)
        return text

    def do_search(self, string_value):
        sitecon = mw.get_connect(self.password)
        namespace = mw.get_setting('mediawiker_search_namespaces')
        return sitecon.search(search=string_value, what='text', limit=self.search_limit, namespace=namespace)


class MediawikerAddImageCommand(sublime_plugin.TextCommand):
    password = ''
    image_prefix_min_lenght = 4
    images_names = []

    def run(self, edit, password, title=''):
        self.password = password
        self.image_prefix_min_lenght = mw.get_setting('mediawiker_image_prefix_min_length', 4)
        sublime.active_window().show_input_panel('Wiki image prefix (min %s):' % self.image_prefix_min_lenght, '', self.show_list, None, None)

    def show_list(self, image_prefix):
        if len(image_prefix) >= self.image_prefix_min_lenght:
            sitecon = mw.get_connect(self.password)
            images = sitecon.allpages(prefix=image_prefix, namespace=IMAGE_NAMESPACE)  # images list by prefix
            # self.images_names = map(self.get_page_title, images)
            self.images_names = [self.get_page_title(x) for x in images]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.images_names, self.on_done), 1)
        else:
            sublime.message_dialog('Image prefix length must be more than %s. Operation canceled.' % self.image_prefix_min_lenght)

    def get_page_title(self, obj):
        return obj.page_title

    def on_done(self, idx):
        if idx >= 0:
            index_of_cursor = self.view.sel()[0].begin()
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': '[[Image:%s]]' % self.images_names[idx]})


class MediawikerAddTemplateCommand(sublime_plugin.TextCommand):
    password = ''
    templates_names = []
    sitecon = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('Wiki template prefix:', '', self.show_list, None, None)

    def show_list(self, image_prefix):
        self.templates_names = []
        self.sitecon = mw.get_connect(self.password)
        templates = self.sitecon.allpages(prefix=image_prefix, namespace=TEMPLATE_NAMESPACE)  # images list by prefix
        for template in templates:
            self.templates_names.append(template.page_title)
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.templates_names, self.on_done), 1)

    def get_template_params(self, text):
        params_list = []
        pattern = r'\{{3}.*?\}{3}'
        parameters = re.findall(pattern, text)
        for param in parameters:
            param = param.strip('{}')
            # default value or not..
            param = param.replace('|', '=') if '|' in param else '%s=' % param
            if param not in params_list:
                params_list.append(param)
        return ''.join(['|%s\n' % p for p in params_list])

    def on_done(self, idx):
        if idx >= 0:
            template = self.sitecon.Pages['Template:%s' % self.templates_names[idx]]
            text = template.edit()
            params_text = self.get_template_params(text)
            index_of_cursor = self.view.sel()[0].begin()
            template_text = '{{%s%s}}' % (self.templates_names[idx], params_text)
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': template_text})


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


class MediawikerUploadCommand(sublime_plugin.TextCommand):

    password = None
    file_path = None
    file_destname = None
    file_descr = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('File path:', '', self.get_destfilename, None, None)

    def get_destfilename(self, file_path):
        if file_path:
            self.file_path = file_path
            file_destname = basename(file_path)
            sublime.active_window().show_input_panel('Destination file name [%s]:' % (file_destname), file_destname, self.get_filedescr, None, None)

    def get_filedescr(self, file_destname):
        if not file_destname:
            file_destname = basename(self.file_path)
        self.file_destname = file_destname
        sublime.active_window().show_input_panel('File description:', '', self.on_done, None, None)

    def on_done(self, file_descr=''):
        sitecon = mw.get_connect(self.password)
        if file_descr:
            self.file_descr = file_descr
        else:
            self.file_descr = '%s as %s' % (basename(self.file_path), self.file_destname)
        try:
            with open(self.file_path, 'rb') as f:
                sitecon.upload(f, self.file_destname, self.file_descr)
            sublime.status_message('File %s successfully uploaded to wiki as %s' % (self.file_path, self.file_destname))
        except IOError as e:
            sublime.message_dialog('Upload io error: %s' % e)
        except Exception as e:
            sublime.message_dialog('Upload error: %s' % e)


class MediawikerFavoritesAddCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = mw.get_title()
        mw.save_mypages(title=title, storage_name='mediawiker_favorites')


class MediawikerFavoritesOpenCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command("mediawiker_page_list", {"storage_name": 'mediawiker_favorites'})


class MediawikerLoad(sublime_plugin.EventListener):
    def on_activated(self, view):
        current_syntax = view.settings().get('syntax')
        current_site = mw.get_view_site()
        # TODO: move method to check mediawiker view to mwutils
        if current_syntax is not None and current_syntax.endswith('Mediawiker/Mediawiki.tmLanguage'):
            # Mediawiki mode
            view.settings().set('mediawiker_is_here', True)
            view.settings().set('mediawiker_wiki_instead_editor', mw.get_setting('mediawiker_wiki_instead_editor'))
            view.settings().set('mediawiker_site', current_site)

    def on_modified(self, view):
        if view.settings().get('mediawiker_is_here', False):
            is_changed = view.settings().get('is_changed', False)

            if is_changed:
                view.set_scratch(False)
            else:
                view.settings().set('is_changed', True)


class MediawikerCompletionsEvent(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        if view.settings().get('mediawiker_is_here', False):
            view = sublime.active_window().active_view()

            # internal links completions
            cursor_position = view.sel()[0].begin()
            line_region = view.line(view.sel()[0])
            line_before_position = view.substr(sublime.Region(line_region.a, cursor_position))
            internal_link = ''
            if line_before_position.rfind('[[') > line_before_position.rfind(']]'):
                internal_link = line_before_position[line_before_position.rfind('[[') + 2:]

            completions = []
            if internal_link:
                word_cursor_min_len = mw.get_setting('mediawiker_page_prefix_min_length', 3)
                if len(internal_link) >= word_cursor_min_len:
                    namespaces = [ns.strip() for ns in mw.get_setting('mediawiker_search_namespaces').split(',')]
                    sitecon = mw.get_connect()
                    pages = []
                    for ns in namespaces:
                        pages = sitecon.allpages(prefix=internal_link, namespace=ns)
                        for p in pages:
                            print(p.name)
                            # name - full page name with namespace
                            # page_title - title of the page wo namespace
                            # For (Main) namespace, shows [page_title (Main)], makes [[page_title]]
                            # For other namespace, shows [page_title namespace], makes [[name|page_title]]
                            if int(ns):
                                ns_name = p.name.split(':')[0]
                                page_insert = '%s|%s' % (p.name, p.page_title)
                            else:
                                ns_name = '(Main)'
                                page_insert = p.page_title
                            page_show = '%s\t%s' % (p.page_title, ns_name)
                            completions.append((page_show, page_insert))

            return completions


class MediawikerShowPageLanglinksCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_page_langlinks"})


class MediawikerPageLanglinksCommand(sublime_plugin.TextCommand):

    def run(self, edit, title, password):
        sitecon = mw.get_connect(password)
        # selection = self.view.sel()
        # search_pre = self.view.substr(selection[0]).strip()
        selected_text = self.view.substr(self.view.sel()[0]).strip()
        title = selected_text if selected_text else title
        self.mw_get_page_langlinks(sitecon, title)

        self.lang_prefixes = []
        for lang_prefix in self.links.keys():
            self.lang_prefixes.append(lang_prefix)

        self.links_names = ['%s: %s' % (lp, self.links[lp]) for lp in self.lang_prefixes]
        if self.links_names:
            sublime.active_window().show_quick_panel(self.links_names, self.on_done)
        else:
            sublime.status_message('Unable to find laguage links for "%s"' % title)

    def mw_get_page_langlinks(self, site, title):
        self.links = {}
        page = site.Pages[title]
        linksgen = page.langlinks()
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links[prop[0]] = prop[1]
                except StopIteration:
                    break

    def on_done(self, index):
        if index >= 0:
            self.lang_prefix = self.lang_prefixes[index]
            self.page_name = self.links[self.lang_prefix]

            self.process_options = ['Open selected page', 'Replace selected text']
            sublime.active_window().show_quick_panel(self.process_options, self.process)

    def process(self, index):
        if index == 0:
            site_active_new = None
            site_active = mw.get_view_site()
            sites = mw.get_setting('mediawiki_site')
            host = sites[site_active]['host']
            domain_first = '.'.join(host.split('.')[-2:])
            # NOTE: only links like lang_prefix.site.com supported.. (like en.wikipedia.org)
            host_new = '%s.%s' % (self.lang_prefix, domain_first)
            # if host_new exists in settings we can open page
            for site in sites:
                if sites[site]['host'] == host_new:
                    site_active_new = site
                    break
            if site_active_new:
                # open page with force site_active_new
                sublime.active_window().run_command("mediawiker_page", {"title": self.page_name, "action": "mediawiker_show_page", "site_active": site_active_new})
            else:
                sublime.status_message('Settings not found for host %s.' % (host_new))
        elif index == 1:
            self.view.run_command('mediawiker_replace_text', {'text': self.page_name})

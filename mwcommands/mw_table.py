#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import re
import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerCsvTableCommand(sublime_plugin.TextCommand):
    ''' selected text, csv data to wiki table '''

    delimiter = '|'

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.view, 'is_here')

    # TODO: rewrite as simple to wiki command
    def run(self, edit):
        self.delimiter = utils.props.get_setting('csvtable_delimiter', '|')
        table_header = '{|'
        table_footer = '|}'
        table_properties = ' '.join(['{}="{}"'.format(prop, value) for prop, value in utils.props.get_setting('wikitable_properties', {}).items()])
        cell_properties = ' '.join(['{}="{}"'.format(prop, value) for prop, value in utils.props.get_setting('wikitable_cell_properties', {}).items()])
        if cell_properties:
            cell_properties = ' {} | '.format(cell_properties)

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
                            table_data += '{}{}{} '.format(col_sep, cell_properties, col)

                self.view.replace(edit, region, '{} {}\n{}\n{}'.format(table_header, table_properties, table_data, table_footer))

    def get_table_data(self, line):
        while '  ' in line:
            line = line.replace('  ', ' ').strip()

        if line.startswith('+--'):
            # ignore line-as-splitter
            return []
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]

        if self.delimiter in line:
            return line.split(self.delimiter)
        return []


class MediawikerTableWikiToSimpleCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) wiki table to Simple table (TableEdit plugin) '''

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.view, 'is_here')

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
                utils.error_message('Need to correct install plugin TableEditor: {}'.format(e))

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

        tbl_full = self.table_show(tbl_full)
        return tbl_full

    def table_show(self, table_data):
        CELL_LEFT_BORDER = '|'
        CELL_RIGHT_BORDER = ''
        ROW_LEFT_BORDER = ''
        ROW_RIGHT_BORDER = '|'
        tbl_data = ''
        for row in table_data:
            if row:
                row_data = ''.join(['{}{}{}'.format(CELL_LEFT_BORDER, cell, CELL_RIGHT_BORDER) for cell in row])
                row_data = '{}{}{}'.format(ROW_LEFT_BORDER, row_data, ROW_RIGHT_BORDER)
                tbl_data += '{}\n'.format(row_data)
        return tbl_data

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

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.view, 'is_here')

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
        table_properties = ' '.join(['{}="{}"'.format(prop, value) for prop, value in utils.props.get_setting('wikitable_properties', {}).items()])

        need_header = table_list[0][0]['is_header']
        is_first_line = True
        for row in table_list:
            if need_header or is_first_line:
                text_wikitable += '{}\n{}'.format(TBL_ROW_START, CELL_HEAD_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_HEAD_DELIM, row)
                is_first_line = False
                need_header = False
            else:
                text_wikitable += '\n{}\n{}'.format(TBL_ROW_START, CELL_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_DELIM, row)
                text_wikitable = text_wikitable.replace(REPLACE_STR, '|')

        return '{} {}\n{}\n{}'.format(TBL_START, table_properties, text_wikitable, TBL_STOP)

    def getrow(self, delimiter, rowlist=None):
        if rowlist is None:
            rowlist = []
        cell_properties = ' '.join(['{}="{}"'.format(prop, value) for prop, value in utils.props.get_setting('wikitable_cell_properties', {}).items()])
        cell_properties = '{} | '.format(cell_properties) if cell_properties else ''
        try:
            return delimiter.join(' {}{} '.format(cell_properties, cell['cell_data'].strip()) for cell in rowlist)
        except Exception as e:
            utils.error_message('Error in data: {}'.format(e))

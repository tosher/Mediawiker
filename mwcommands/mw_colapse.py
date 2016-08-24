#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import re

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerColapseCommand(sublime_plugin.TextCommand):

    # DRAW_TYPE = sublime.DRAW_NO_FILL + sublime.DRAW_SOLID_UNDERLINE + sublime.PERSISTENT
    DRAW_TYPE = sublime.HIDDEN + sublime.PERSISTENT
    point = None

    def get_header_regions(self, level):
        _regions = []
        pattern = r'={%(level)s}[^=]+={%(level)s}\s?\n((.|\n)*?)(?=(\n=|\Z))' % {'level': level}
        _regions = self.view.find_all(pattern)
        colapse_paragraphs = []
        if _regions:
            for r in _regions:
                header_line = self.view.substr(r).split('\n')[0]
                _a, _b = r.a + len(header_line), r.b
                colapse_paragraphs.append((r.a, sublime.Region(_a, _b)))

            gutter_png = 'Packages/Mediawiker/img/gutter_h%s.png' % level if pythonver >= 3 else ''
            self.view.add_regions('h_%s' % level, [r[1] for r in colapse_paragraphs], 'comment', gutter_png, self.DRAW_TYPE)

        return colapse_paragraphs

    def get_templates(self):

        TPL_START = r'(?<![^\{]\{)\{{2}(?!\{[^\{])'
        TPL_STOP = r'(?<![^\}]\})\}{2}(?!\}([^\}]|$))'
        TYPE_START = 'start'
        TYPE_STOP = 'stop'
        text_region = sublime.Region(0, self.view.size())
        line_regions = self.view.split_by_newlines(text_region)
        # print(line_regions)
        lines_data = []
        templates = []
        for region in line_regions:
            line_text = self.view.substr(region)
            starts = [region.a + m.start() for m in re.finditer(TPL_START, line_text)]
            stops = [region.a + m.start() for m in re.finditer(TPL_STOP, line_text)]

            line_index = {}
            for i in starts:
                line_index[i] = TYPE_START
            for i in stops:
                line_index[i] = TYPE_STOP

            if starts or stops:
                lines_data.append(line_index)

        _templates = []
        for d in lines_data:
            line_indexes = list(d.keys())
            line_indexes.sort()
            for i in line_indexes:
                if d[i] == TYPE_START:
                    t = sublime.Region(i + 2, i + 2)  # unknown end
                    _templates.append(t)
                elif d[i] == TYPE_STOP:
                    # ST2 compat Region update
                    # _templates[-1].b = i
                    _templates[-1] = sublime.Region(_templates[-1].a, i)
                    templates.append((_templates[-1], len(_templates)))  # template region and includes level
                    _templates = _templates[:-1]
        return templates

    def get_templates_regions(self):
        _regions = self.get_templates()
        colapse_templates = {}
        if _regions:
            for _r in _regions:
                line_idx = self.view.line(_r[0]).a
                if line_idx in colapse_templates:
                    colapse_templates[line_idx].append(_r[0])
                else:
                    colapse_templates[line_idx] = [_r[0]]

            # create gutter by first region in line..
            gutter_png = 'Packages/Mediawiker/img/gutter_t.png' if pythonver >= 3 else ''
            self.view.add_regions('templates_%s' % _r[1], [rl[0] for rl in list(colapse_templates.values())], 'comment', gutter_png, self.DRAW_TYPE)
        return colapse_templates

    def get_tag_regions(self, tag):
        pattern_tag = r'<%(tag)s((.|\n)*?)</%(tag)s>' % {'tag': tag}
        _regions = self.view.find_all(pattern_tag)
        colapse_tag = []
        if _regions:
            for r in _regions:
                header_line = self.view.substr(r).split('>')[0]
                _a, _b = r.a + len(header_line) + 1, r.b - len('</%s>' % tag)
                colapse_tag.append((r.a, sublime.Region(_a, _b)))

            gutter_png = 'Packages/Mediawiker/img/gutter_tag.png' if pythonver >= 3 else ''
            self.view.add_regions(tag, [r[1] for r in colapse_tag], 'comment', gutter_png, self.DRAW_TYPE)
        return colapse_tag

    def get_tables_regions(self):
        pattern_tables = r'\{\|((.|\n)*?)\|\}'
        _regions = self.view.find_all(pattern_tables)
        colapse_tables = []
        if _regions:
            for r in _regions:
                _a, _b = r.a + 2, r.b - 2
                colapse_tables.append(sublime.Region(_a, _b))

            gutter_png = 'Packages/Mediawiker/img/gutter_t.png' if pythonver >= 3 else ''
            self.view.add_regions('tables', colapse_tables, 'comment', gutter_png, self.DRAW_TYPE)
        return colapse_tables

    def get_comment_regions(self):
        C_START = r'<!--'
        C_STOP = r'-->'
        pattern_comment = r'%s((.|\n)*?)%s' % (C_START, C_STOP)
        _regions = self.view.find_all(pattern_comment)
        colapse_comment = []
        if _regions:
            for r in _regions:
                r_new = sublime.Region(r.a + len(C_START), r.b - len(C_STOP))
                colapse_comment.append(r_new)

            gutter_png = 'Packages/Mediawiker/img/gutter_tag.png' if pythonver >= 3 else ''
            self.view.add_regions('comment', colapse_comment, 'comment', gutter_png, self.DRAW_TYPE)
        return colapse_comment

    def is_cursor_inheader(self, cursor, rt):
        '''
        cursor: current cursor position
        rt: tuple (h_start, h_region)
        '''
        region = rt[1]
        r_full = sublime.Region(rt[0], region.b)
        if r_full.contains(cursor):
            return True
        return False

    def is_cursor_intemplate(self, cursor, region):
        r_full = sublime.Region(region.a - 2, region.b + 2)
        if r_full.contains(cursor):
            return True
        return False

    def is_cursor_intag(self, cursor, rt, tag):
        r_full = sublime.Region(rt[0], rt[1].b + len('</%s>' % tag))
        if r_full.contains(cursor):
            return True
        return False

    def is_cursor_incomment(self, cursor, r):
        C_START = '<!--'
        C_STOP = '-->'

        r_full = sublime.Region(r.a - len(C_START), r.b + len(C_STOP))
        if r_full.contains(cursor):
            return True
        return False

    def get_first_header_region_by_cursor(self, cursor, headers):
        for level_tuple in headers.keys():
            if headers[level_tuple]:
                for rt in headers[level_tuple]:
                    if self.is_cursor_inheader(cursor, rt):
                        return rt[1]

    def run(self, edit, title, password, **kwargs):

        if not self.view.settings().get('mediawiker_is_here', False):
            return

        _fold_type = kwargs.get('type', None) if kwargs else None
        point = kwargs.get('point', None) if kwargs else None
        fold_tags = mw.get_setting("mediawiker_fold_tags", ["source", "syntaxhighlight", "div", "pre"])

        headers = {}
        for _h in range(2, 5):
            headers[_h] = self.get_header_regions(level=_h)

        t = self.get_templates_regions()
        tbl = self.get_tables_regions()
        tags = {}
        for _t in fold_tags:
            tags[_t] = self.get_tag_regions(_t)
        comments = self.get_comment_regions()

        self.is_cursor_intable = self.is_cursor_intemplate

        cursor = point if point is not None else self.view.sel()[0].begin()

        if _fold_type is None:
            return

        elif _fold_type == 'fold':

            # TODO: get regions from all type, get min of them, then fold! But it's slowly..

            for r in comments:
                if self.is_cursor_incomment(cursor, r):
                    self.view.fold(r)
                    return

            for tag in tags.keys():
                for r in tags[tag]:
                    if self.is_cursor_intag(cursor, r, tag):
                        self.view.fold(r[1])
                        return

            for r in tbl:
                if self.is_cursor_intable(cursor, r):
                    self.view.fold(r)
                    return

            # if fires from on_hover, check region, started in point line
            if point is not None:
                for r in t.keys():
                    if point == r:
                        for _r in t[r]:
                            self.view.fold(_r)
                        return

            t_lines = list(t.keys())
            t_lines.sort()
            for r in reversed(t_lines):
                for _r in t[r]:
                    if self.is_cursor_intemplate(cursor, _r):
                        self.view.fold(_r)
                        return

            r = self.get_first_header_region_by_cursor(cursor, headers)
            if r:
                self.view.fold(r)
                return

        elif _fold_type == 'unfold':

            for r in comments:
                if self.is_cursor_incomment(cursor, r):
                    self.view.unfold(r)
                    return

            for tag in tags.keys():
                for r in tags[tag]:
                    if self.is_cursor_intag(cursor, r, tag):
                        self.view.unfold(r[1])
                        return

            for r in tbl:
                if self.is_cursor_intable(cursor, r):
                    self.view.unfold(r)
                    self.view.show_at_center(cursor)
                    return

            t_lines = list(t.keys())
            t_lines.sort()
            for r in reversed(t_lines):
                for _r in t[r]:
                    if self.is_cursor_intemplate(cursor, _r):
                        self.view.unfold(t[r])
                        self.view.show_at_center(cursor)
                        return

            r = self.get_first_header_region_by_cursor(cursor, headers)
            if r:
                self.view.unfold(r)
                self.view.show_at_center(cursor)
                return

        elif _fold_type.startswith('fold_'):
            try:
                level = int(_fold_type.split('_')[-1])
            except:
                level = 2

            for _l in range(level, 5):
                for r in headers[_l]:
                    if r:
                        self.view.fold(r[1])

        elif _fold_type.startswith('unfold_'):
            try:
                level = int(_fold_type.split('_')[-1])
            except:
                level = 2

            for _l in reversed(range(level, 5)):
                for r in headers[_l]:
                    if r:
                        self.view.unfold(r[1])

        elif _fold_type.startswith('foldwiki'):

            for tag in tags.keys():
                for r in tags[tag]:
                    self.view.fold(r[1])

            for r in tbl:
                self.view.fold(r)

            for r in t.keys():
                for _r in t[r]:
                    self.view.fold(_r)

        elif _fold_type.startswith('unfoldwiki'):

            for tag in tags.keys():
                for r in tags[tag]:
                    self.view.unfold(r[1])

            for r in tbl:
                self.view.unfold(r)

            for r in t.keys():
                for _r in t[r]:
                    self.view.unfold(_r)


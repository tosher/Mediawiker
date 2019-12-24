#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils
from . import mw_parser as par


class MediawikerColapseCommand(sublime_plugin.TextCommand):

    # DRAW_TYPE = sublime.DRAW_NO_FILL + sublime.DRAW_SOLID_UNDERLINE + sublime.PERSISTENT
    DRAW_TYPE = sublime.HIDDEN + sublime.PERSISTENT
    point = None

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.view, 'is_here')

    def get_colapse_headers(self, headers):
        if headers:
            level = headers[0].level
            gutter_png = ''
            if utils.props.get_setting('show_gutters'):
                gutter_png = utils.p.from_package('img', 'gutter_h{}.png'.format(level))
            self.view.add_regions('h_{}'.format(level), [r.region for r in headers], 'comment', gutter_png, self.DRAW_TYPE)

    def get_colapse_templates(self, templates):
        if templates:
            gutter_png = ''
            if utils.props.get_setting('show_gutters'):
                gutter_png = utils.p.from_package('img', 'gutter_t.png')
            self.view.add_regions('templates', [r.region for r in templates], 'comment', gutter_png, self.DRAW_TYPE)

    def get_colapse_tags(self, tag, tags):
        if tags:
            gutter_png = ''
            if utils.props.get_setting('show_gutters'):
                gutter_png = utils.p.from_package('img', 'gutter_tag.png')
            self.view.add_regions(tag, [r.region for r in tags], 'comment', gutter_png, self.DRAW_TYPE)

    def get_colapse_tables(self, tables):
        if tables:
            gutter_png = ''
            if utils.props.get_setting('show_gutters'):
                gutter_png = utils.p.from_package('img', 'gutter_t.png')
            self.view.add_regions('tables', [r.region for r in tables], 'comment', gutter_png, self.DRAW_TYPE)

    def get_colapse_comments(self, comments):
        if comments:
            gutter_png = ''
            if utils.props.get_setting('show_gutters'):
                gutter_png = utils.p.from_package('img', 'gutter_tag.png')
            self.view.add_regions('comment', [r.region for r in comments], 'comment', gutter_png, self.DRAW_TYPE)

    def run(self, edit, **kwargs):

        if not utils.props.get_view_setting(self.view, 'is_here', False):
            return

        _fold_type = kwargs.get('type', None) if kwargs else None
        point = kwargs.get('point', None) if kwargs else None
        fold_tags = utils.props.get_setting("fold_tags")

        p = par.Parser(self.view)
        p.register_all(
            par.Comment, par.TemplateAttribute, par.Template, par.Link, par.Pre,
            par.Nowiki, par.Source, par.WikiTable,
            par.HeaderOne, par.HeaderTwo, par.HeaderThree,
            par.HeaderFour, par.HeaderFive
        )

        for tag in fold_tags:
            p.register_dynamic(tag)

        if not p.parse():
            return

        # headers
        self.get_colapse_headers(p.headerones)
        self.get_colapse_headers(p.headertwos)
        self.get_colapse_headers(p.headerthrees)
        self.get_colapse_headers(p.headerfours)
        self.get_colapse_headers(p.headerfives)
        headers = p.headerfives + p.headerfours + p.headerthrees + p.headertwos + p.headerones

        # templates
        self.get_colapse_templates(p.templates)

        # tables
        self.get_colapse_tables(p.wikitables)

        # html tags
        tags = p.pres + p.sources
        for tag in fold_tags:
            tags_list = p.elist_by_name(tag)
            if tags_list:
                tags += tags_list

        self.get_colapse_tags(tag, tags)

        # comments
        comments_regions = p.comments
        self.get_colapse_comments(comments_regions)

        cursor = point if point is not None else self.view.sel()[0].begin()

        tags.sort(key=lambda x: x.region.a, reverse=True)
        p.wikitables.reverse()
        p.templates.reverse()

        if _fold_type is None:
            return

        elif _fold_type == 'fold':

            for r in p.comments:
                if r.region.contains(cursor):
                    r.fold()
                    return

            for r in tags:
                if r.region.contains(cursor):
                    r.fold()
                    return

            for tbl in p.wikitables:
                if tbl.region.contains(cursor):
                    tbl.fold()
                    return

            for r in p.templates:
                if r.region.contains(cursor):
                    r.fold()
                    return

            for r in headers:
                if r.region.contains(cursor):
                    r.fold()
                    return

        elif _fold_type == 'unfold':

            for r in p.comments:
                if r.region.contains(cursor):
                    r.unfold()
                    return

            for tag in tags:
                if tag.region.contains(cursor):
                    r.unfold()
                    return

            for tbl in p.wikitables:
                if tbl.region.contains(cursor):
                    tbl.unfold()
                    self.view.show_at_center(cursor)
                    return

            for r in p.templates:
                if r.region.contains(cursor):
                    r.unfold()
                    self.view.show_at_center(cursor)
                    return

            for r in headers:
                if r.region.contains(cursor):
                    r.unfold()
                    return

        elif _fold_type.startswith('fold_'):
            try:
                level = int(_fold_type.split('_')[-1])
            except:
                level = 2

            hdrs = [h for h in headers if h.level == level]
            for h in hdrs:
                h.fold()

        elif _fold_type.startswith('unfold_'):
            try:
                level = int(_fold_type.split('_')[-1])
            except:
                level = 2

            hdrs = [h for h in headers if h.level == level]

            for h in hdrs:
                h.unfold()

        elif _fold_type.startswith('foldwiki'):

            for r in tags:
                r.fold()

            for tbl in p.wikitables:
                tbl.fold()

            for r in p.templates:
                r.fold()

        elif _fold_type.startswith('unfoldwiki'):

            for r in tags:
                r.unfold()

            for tbl in p.wikitables:
                tbl.unfold()

            for r in p.templates:
                r.unfold()

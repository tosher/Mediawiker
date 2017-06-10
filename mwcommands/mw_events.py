#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
    from . import mw_hovers as hovers
else:
    import mw_utils as mw
    import mw_hovers as hovers

if pythonver >= 3:

    class MediawikerViewEvents(sublime_plugin.ViewEventListener):

        cnt = None

        def on_modified(self):
            if mw.props.get_view_setting(self.view, 'is_here'):
                self.view.hide_popup()
                try:
                    ch_cnt = mw.props.get_view_setting(self.view, 'autoreload')
                    if ch_cnt:
                        if not self.cnt:
                            self.cnt = self.view.change_count()

                        cnt_delta = self.view.change_count() - self.cnt
                        if cnt_delta > ch_cnt:
                            sublime.status_message('Autoreload: Generating preview..')
                            sublime.active_window().run_command(mw.cmd('preview'))
                            self.cnt = None
                        else:
                            sublime.status_message('\nAutoreload: change %s of %s..' % (cnt_delta, ch_cnt))
                except Exception as e:
                    mw.status_message('Preview exception: %s' % e)
else:

    class MediawikerViewEvents(object):
        cnt = None

        def on_modified(self):
            pass


class MediawikerEvents(sublime_plugin.EventListener):
    def on_activated(self, view):
        current_syntax = mw.props.get_view_setting(view, 'syntax', plugin=False)

        # TODO: move method to check mediawiker view to mwutils
        if (current_syntax is not None and
                current_syntax.startswith(mw.from_package('Mediawiki')) and
                current_syntax.endswith(('.tmLanguage', '.sublime-syntax'))):

            # Mediawiki mode
            mw.props.set_view_setting(view, 'is_here', True)

            if not view.file_name():
                mw.props.set_view_setting(view, 'wiki_instead_editor', mw.get_setting('wiki_instead_editor'))
            else:
                mw.props.set_view_setting(view, 'wiki_instead_editor', False)

            mw.props.set_view_setting(view, 'site', mw.get_view_site())

    def on_activated_async(self, view):
        ''' unsupported on ST2, gutters too - skipping.. '''
        # folding gutters
        if mw.props.get_view_setting(view, 'is_here'):
            sublime.active_window().run_command(mw.cmd('colapse'))

    def on_modified(self, view):
        if mw.props.get_view_setting(view, 'is_here'):
            is_changed = mw.props.get_view_setting(view, 'is_changed')

            if is_changed:
                view.set_scratch(False)
            else:
                mw.props.set_view_setting(view, 'is_changed', True)

            # folding gutters update
            # removed: skip parsing while editing
            # mw.set_timeout_async(sublime.active_window().run_command(mw.cmd('colapse')), 5)

    def on_post_save(self, view):
        if mw.props.get_view_setting(view, 'is_here'):
            mw.props.set_view_setting(view, 'wiki_instead_editor', False)

    def on_post_save_async(self, view):
        if mw.props.get_view_setting(view, 'is_here'):
            mw.props.set_view_setting(view, 'wiki_instead_editor', False)

    def on_hover(self, view, point, hover_zone):
        # not fires in ST2

        if mw.props.get_view_setting(view, 'is_here') and hover_zone == sublime.HOVER_TEXT:

            if hovers.on_hover_comment(view, point):
                return

            if hovers.on_hover_selected(view, point):
                return

            if hovers.on_hover_internal_link(view, point):
                return

            if hovers.on_hover_tag(view, point):
                return

            if hovers.on_hover_template(view, point):
                return

            if hovers.on_hover_heading(view, point):
                return

            if hovers.on_hover_table(view, point):
                return

            # TODO: external links..?

    def on_query_completions(self, view, prefix, locations):
        if mw.props.get_view_setting(view, 'is_here') and not mw.props.get_setting('offline_mode'):
            view = sublime.active_window().active_view()

            # internal links completions
            cursor_position = locations[0]  # view.sel()[0].begin()
            line_region = view.line(view.sel()[0])
            line_before_position = view.substr(sublime.Region(line_region.a, cursor_position))
            internal_link = ''
            if line_before_position.rfind('[[') > line_before_position.rfind(']]'):
                internal_link = line_before_position[line_before_position.rfind('[[') + 2:]

            if mw.api.INTERNAL_LINK_SPLITTER in internal_link:
                # cursor at custom url text zone..
                return []

            completions = []
            if internal_link:
                word_cursor_min_len = mw.get_setting('page_prefix_min_length', 3)
                ns_text = None
                ns_text_number = None

                if mw.api.NAMESPACE_SPLITTER in internal_link:
                    ns_text, internal_link = internal_link.split(mw.api.NAMESPACE_SPLITTER)

                if len(internal_link) >= word_cursor_min_len:
                    namespaces_search = [ns.strip() for ns in mw.get_setting('search_namespaces').split(',')]
                    if ns_text:
                        ns_text_number = mw.api.call('get_namespace_number', name=ns_text)

                    if internal_link.startswith('/'):
                        internal_link = '%s%s' % (mw.get_title(), internal_link)

                    # TODO: recheck completions

                    pages = []
                    for ns in namespaces_search:
                        if not ns_text or ns_text_number and int(ns_text_number) == int(ns):
                            pages = mw.api.call('get_pages', prefix=internal_link, namespace=ns)
                            for p in pages:
                                # name - full page name with namespace
                                # page_title - title of the page wo namespace
                                # For (Main) namespace, shows [page_title (Main)], makes [[page_title]]
                                # For Image, Category namespaces, shows [page_title namespace], makes [[name]]
                                # For other namespace, shows [page_title namespace], makes [[name|page_title]]
                                if int(ns):
                                    ns_name = mw.api.page_attr(p, 'namespace_name')
                                    page_name = mw.api.page_attr(p, 'name') if not mw.api.is_equal_ns(ns_text, ns_name) else mw.api.page_attr(p, 'page_title')
                                    if int(ns) in (mw.api.CATEGORY_NAMESPACE, mw.api.IMAGE_NAMESPACE):
                                        page_insert = page_name
                                    else:
                                        page_insert = '%s|%s' % (page_name, mw.api.page_attr(p, 'page_title'))
                                else:
                                    ns_name = '(Main)'
                                    page_insert = mw.api.page_attr(p, 'page_title')
                                page_show = '%s\t%s' % (mw.api.page_attr(p, 'page_title'), ns_name)
                                completions.append((page_show, page_insert))

            return completions
        return []

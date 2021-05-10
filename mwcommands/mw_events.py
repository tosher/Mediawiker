#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils
from . import mw_hovers as hovers


class MediawikerViewEvents(sublime_plugin.ViewEventListener):

    cnt = None

    def on_modified(self):
        preview_cmd = utils.props.get_view_setting(self.view, 'preview_cmd')

        if not preview_cmd:
            return

        if utils.props.get_view_setting(self.view, 'is_here'):
            self.view.hide_popup()
            try:
                ch_cnt = utils.props.get_view_setting(self.view, 'autoreload')
                if ch_cnt:
                    if not self.cnt:
                        self.cnt = self.view.change_count()

                    cnt_delta = self.view.change_count() - self.cnt
                    if cnt_delta > ch_cnt:
                        utils.status_message('Autoreload: Generating preview..')
                        sublime.active_window().run_command(utils.cmd(preview_cmd))
                        self.cnt = None
                    else:
                        utils.status_message('\nAutoreload: change {} of {}..'.format(cnt_delta, ch_cnt))
            except Exception as e:
                utils.error_message('Preview exception: {}'.format(e))


class MediawikerEvents(sublime_plugin.EventListener):
    def on_activated(self, view):
        current_syntax = utils.props.get_view_setting(view, 'syntax', plugin=False)

        if not current_syntax:
            return

        if not current_syntax.startswith(utils.p.from_package('Mediawiki')):
            return

        if not current_syntax.endswith(('.tmLanguage', '.sublime-syntax')):
            return

        # Mediawiki mode
        utils.props.set_view_setting(view, 'is_here', True)

        if not view.file_name():
            utils.props.set_view_setting(view, 'wiki_instead_editor', utils.props.get_setting('wiki_instead_editor'))
        else:
            utils.props.set_view_setting(view, 'wiki_instead_editor', False)

        utils.props.set_view_setting(view, 'site', utils.get_view_site())

    def on_activated_async(self, view):
        ''' unsupported on ST2, gutters too - skipping.. '''
        # folding gutters
        if utils.props.get_view_setting(view, 'is_here'):
            sublime.active_window().run_command(utils.cmd('colapse'))

    def on_modified(self, view):
        if utils.props.get_view_setting(view, 'is_here'):
            is_changed = utils.props.get_view_setting(view, 'is_changed')

            if is_changed:
                view.set_scratch(False)
            else:
                utils.props.set_view_setting(view, 'is_changed', True)

            # folding gutters update
            # removed: skip parsing while editing
            # utils.set_timeout_async(sublime.active_window().run_command(utils.cmd('colapse')), 5)

    def on_post_save(self, view):
        if utils.props.get_view_setting(view, 'is_here'):
            utils.props.set_view_setting(view, 'wiki_instead_editor', False)

    def on_post_save_async(self, view):
        if utils.props.get_view_setting(view, 'is_here'):
            utils.props.set_view_setting(view, 'wiki_instead_editor', False)

    def on_hover(self, view, point, hover_zone):
        if not utils.props.get_view_setting(view, 'is_here'):
            return

        if hover_zone != sublime.HOVER_TEXT:
            return

        if utils.get_view_syntax(view) != utils.props.get_setting('syntax'):
            return

        hover_comment = hovers.on_hover_comment(view, point)

        if hover_comment:
            view.show_popup(**hover_comment)
            return

        hover_selected = hovers.on_hover_selected(view, point)
        hover_internal_link = hovers.on_hover_internal_link(view, point)
        hover_template = hovers.on_hover_template(view, point)

        if hover_selected:
            selected_text = hover_selected.get('related')

            if hover_internal_link and selected_text == hover_internal_link.get('related'):
                # crossing with internal link and full link text selected
                pass
            elif hover_template and hover_template.get('related').endswith(selected_text):
                # crossing with template link and full template name selected
                pass
            else:
                view.show_popup(**hover_selected['popup'])
                return

        if hover_internal_link:
            view.show_popup(**hover_internal_link['popup'])
            return

        hover_tag = hovers.on_hover_tag(view, point)
        if hover_tag:
            view.show_popup(**hover_tag['popup'])
            return

        if hover_template:
            view.show_popup(**hover_template['popup'])
            return

        hover_heading = hovers.on_hover_heading(view, point)
        if hover_heading:
            view.show_popup(**hover_heading['popup'])
            return

        hover_table = hovers.on_hover_table(view, point)
        if hovers.on_hover_table(view, point):
            view.show_popup(**hover_table['popup'])
            return

        # TODO: external links..?

    def on_query_completions(self, view, prefix, locations):
        if not utils.props.get_view_setting(view, 'is_here'):
            return []

        if utils.props.get_setting('offline_mode'):
            return []

        view = sublime.active_window().active_view()

        # internal links completions
        cursor_position = locations[0]  # view.sel()[0].begin()
        line_region = view.line(view.sel()[0])
        line_before_position = view.substr(sublime.Region(line_region.a, cursor_position))
        internal_link = ''
        if line_before_position.rfind('[[') > line_before_position.rfind(']]'):
            internal_link = line_before_position[line_before_position.rfind('[[') + 2:]

        if utils.api.INTERNAL_LINK_SPLITTER in internal_link:
            # cursor at custom url text zone..
            return []

        completions = []
        if internal_link:
            word_cursor_min_len = utils.props.get_setting('page_prefix_min_length', 3)
            ns_text = None
            ns_text_number = None

            if utils.api.NAMESPACE_SPLITTER in internal_link:
                ns_text, internal_link = internal_link.split(utils.api.NAMESPACE_SPLITTER)

            if len(internal_link) < word_cursor_min_len:
                return []

            namespaces_search = utils.get_search_ns()
            if not namespaces_search:
                return completions

            if ns_text:
                ns_text_number = utils.api.call('get_namespace_number', name=ns_text)

            if internal_link.startswith('/'):
                internal_link = '{}{}'.format(utils.get_title(), internal_link)

            pages = []
            for ns in namespaces_search:
                # if not ns_text or ns_text_number and int(ns_text_number) == int(ns):

                if ns_text and int(ns_text_number) != int(ns):
                    continue

                pages = utils.api.call('get_pages', prefix=internal_link.replace('_', ' '), namespace=ns)
                for p in pages:
                    # name - full page name with namespace
                    # page_title - title of the page wo namespace
                    # For (Main) namespace, shows [page_title (Main)], makes [[page_title]]
                    # For Image, Category namespaces, shows [page_title namespace], makes [[name]]
                    # For other namespace, shows [page_title namespace], makes [[name|page_title]]
                    if int(ns):
                        ns_name = utils.api.page_attr(p, 'namespace_name')
                        page_name = utils.api.page_attr(p, 'name') if not utils.api.is_equal_ns(ns_text, ns_name) else utils.api.page_attr(p, 'page_title')
                        if int(ns) in (utils.api.CATEGORY_NAMESPACE, utils.api.IMAGE_NAMESPACE):
                            page_insert = page_name
                        else:
                            page_insert = '{}|{}'.format(page_name, utils.api.page_attr(p, 'page_title'))
                    else:
                        ns_name = '(Main)'
                        page_insert = utils.api.page_attr(p, 'page_title')

                    page_show = '{}\t{}'.format(utils.api.page_attr(p, 'page_title'), ns_name)

                    # if name starts with string with `_`, trying to make completions `_`-based
                    # Big_B -> Big_Buck_Bunny
                    if '_' in internal_link and ' ' not in internal_link:
                        page_insert = page_insert.replace(' ', '_')
                        page_show = page_show.replace(' ', '_')

                    # #167
                    # if space exists in completion part
                    _space_cnt = internal_link.count(' ')
                    if _space_cnt and _space_cnt <= 2:
                        page_insert = page_insert[len(internal_link.rsplit(' ', 1)[0]) + 1:]

                    completions.append((page_show, page_insert))

        return completions

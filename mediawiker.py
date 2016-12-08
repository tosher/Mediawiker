#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

# https://github.com/wbond/sublime_package_control/wiki/Sublime-Text-3-Compatible-Packages
# http://www.sublimetext.com/docs/2/api_reference.html
# http://www.sublimetext.com/docs/3/api_reference.html
# sublime.message_dialog

# TODO: Move rename page
# TODO: links (internal, external) based on api..
# TODO: Search results to wiki syntax..

# suppress deprecation warnings (turned on in mwclient lib: mwclient/__init__.py)
import warnings
warnings.simplefilter("ignore", DeprecationWarning)

pythonver = sys.version_info[0]
if pythonver >= 3:
    from .mwcommands import mw_utils as mw
    from .mwcommands import mw_hovers as hovers
    from .mwcommands import *
else:
    from mwcommands import mw_utils as mw
    from mwcommands import mw_hovers as hovers
    from mwcommands import *


class MediawikerOpenPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_show_page"})


class MediawikerReopenPageCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = mw.get_title()
        self.window.run_command("mediawiker_page", {
            'action': 'mediawiker_show_page',
            'action_params': {'title': title, 'new_tab': False}
        })


class MediawikerPostPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Publish page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_publish_page"})


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    def run(self, edit, title=None, new_tab=None, site_active=None):

        self.new_tab = new_tab if new_tab is not None else mw.get_setting('mediawiker_newtab_ongetpage', False)

        # cases:
        # from view with page, opened from other site_active than in global settings - new page will be from the same site
        # from view with page, open page with another lang site - site param must be defined, will set it
        # from view with undefined site (new) open page by global site_active setting
        self.site_active = site_active if site_active else mw.get_view_site()

        panel = mw.InputPanelPageTitle(callback=self.page_open)
        panel.get_title(title)

    def page_open(self, title):

        if self.new_tab:
            view = sublime.active_window().new_file()
            view.settings().set('mediawiker_site', self.site_active)
        else:
            view = self.view

        page = mw.api.call('get_page', title=title)

        if mw.api.page_can_edit(page):
            # can read and edit
            view.settings().set('page_revision', mw.api.page_attr(page, 'revision'))
        elif not mw.api.page_can_read(page):
            # can not read and edit
            sublime.message_dialog(mw.PAGE_CANNOT_READ_MESSAGE)
            view.close()
            return
        elif not sublime.ok_cancel_dialog('%s Click OK button to view its source.' % mw.PAGE_CANNOT_EDIT_MESSAGE):
            # can not edit, but can read, but not want
            view.close()
            return

        text = mw.api.page_get_text(page)
        page_namespace = mw.api.page_attr(page, 'namespace')

        if not text:
            mw.status_message('Wiki page %s is not exists. You can create new..' % (title))
            text = '<!-- New wiki page: Remove this with text of the new page -->'
        else:
            view.run_command('mediawiker_insert_text', {'position': 0, 'text': text, 'with_erase': True})

        mw.status_message('Page [[%s]] was opened successfully from "%s".' % (title, mw.get_view_site()), replace=['[', ']'])
        mw.set_syntax(title, page_namespace)
        view.settings().set('mediawiker_is_here', True)
        view.settings().set('mediawiker_wiki_instead_editor', mw.get_setting('mediawiker_wiki_instead_editor'))
        view.set_name(title)

        view.set_scratch(True)
        # own is_changed flag instead of is_dirty for possib. to reset..
        view.settings().set('is_changed', False)


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit):
        is_process_post = True
        is_skip_summary = mw.get_setting('mediawiker_skip_summary', False)
        self.title = mw.get_title()
        if self.title:
            self.page = mw.api.get_page(self.title)

            if mw.api.page_can_edit(self.page):

                if mw.get_setting('mediawiki_validate_revision_on_post', True) and self.view.settings().get('page_revision', 0) != mw.api.page_attr(self.page, 'revision'):
                    is_process_post = sublime.ok_cancel_dialog('Page was changed on server, post page anyway? If not, new revision will be opened in new tab.')

                if is_process_post:
                    self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                    if not is_skip_summary:
                        summary_message = 'Changes summary (%s):' % mw.get_view_site()
                        mw.set_timeout_async(self.view.window().show_input_panel(summary_message, '', self.on_done, None, None), 0)
                    else:
                        mw.set_timeout_async(self.on_done, 0)
                else:
                    self.view.window().run_command('mediawiker_page', {
                        'action': 'mediawiker_show_page',
                        'action_params': {'title': self.title, 'new_tab': True}
                    })
            else:
                mw.status_message('You have not rights to edit this page')
        else:
            mw.status_message('Can\'t publish page with empty title')
            return

    def post_page(self, summary):
        summary = '%s%s' % (summary, mw.get_setting('mediawiker_summary_postfix', ' (by SublimeText.Mediawiker)'))
        mark_as_minor = mw.get_setting('mediawiker_mark_as_minor')
        # invert minor settings command '!'
        if summary[0] == '!':
            mark_as_minor = not mark_as_minor
            summary = summary[1:]
        mw.api.save_page(self.page, self.current_text, summary, mark_as_minor)

        # update revision for page in view
        self.page = mw.api.get_page(self.title)
        self.view.settings().set('page_revision', mw.api.page_attr(self.page, 'revision'))

        self.view.set_scratch(True)
        self.view.settings().set('is_changed', False)  # reset is_changed flag
        mw.status_message('Wiki page [[%s]] was successfully published to wiki "%s".' % (self.title, mw.get_view_site()), replace=['[', ']'])
        mw.save_mypages(self.title)

    def on_done(self, summary=None):
        if summary is None:
            summary = ''
        summary = '%s%s' % (summary, mw.get_setting('mediawiker_summary_postfix', ' (by SublimeText.Mediawiker)'))
        try:
            if mw.api.page_can_edit(self.page):
                self.post_page(summary=summary)
            else:
                mw.status_message(mw.PAGE_CANNOT_EDIT_MESSAGE)
        except mw.mwclient.EditError as e:
            mw.status_message('Can\'t publish page [[%s]] (%s)' % (self.title, e), replace=['[', ']'])


class MediawikerEvents(sublime_plugin.EventListener):
    def on_activated(self, view):
        current_syntax = view.settings().get('syntax')
        current_site = mw.get_view_site()

        # TODO: move method to check mediawiker view to mwutils
        if (current_syntax is not None and
                current_syntax.startswith('Packages/Mediawiker/Mediawiki') and
                current_syntax.endswith(('.tmLanguage', '.sublime-syntax'))):

            # Mediawiki mode
            view.settings().set('mediawiker_is_here', True)

            if not view.file_name():
                view.settings().set('mediawiker_wiki_instead_editor', mw.get_setting('mediawiker_wiki_instead_editor'))
            else:
                view.settings().set('mediawiker_wiki_instead_editor', False)

            view.settings().set('mediawiker_site', current_site)

    def on_activated_async(self, view):
        ''' unsupported on ST2, gutters too - skipping.. '''
        # folding gutters
        if view.settings().get('mediawiker_is_here', False):
            sublime.active_window().run_command("mediawiker_colapse")

    def on_modified(self, view):
        if view.settings().get('mediawiker_is_here', False):
            is_changed = view.settings().get('is_changed', False)

            if is_changed:
                view.set_scratch(False)
            else:
                view.settings().set('is_changed', True)

            # folding gutters update
            sublime.active_window().run_command("mediawiker_colapse")

    def on_post_save(self, view):
        view.settings().set('mediawiker_wiki_instead_editor', False)

    def on_post_save_async(self, view):
        view.settings().set('mediawiker_wiki_instead_editor', False)

    def on_hover(self, view, point, hover_zone):
        # not fires in ST2

        if view.settings().get('mediawiker_is_here', False) and hover_zone == sublime.HOVER_TEXT:

            if hovers.on_hover_comment(view, point):
                return

            if hovers.on_hover_selected(view, point):
                return

            if hovers.on_hover_tag(view, point):
                return

            if hovers.on_hover_internal_link(view, point):
                return

            if hovers.on_hover_template(view, point):
                return

            if hovers.on_hover_heading(view, point):
                return

            # TODO: external links..?

    def on_query_completions(self, view, prefix, locations):
        if view.settings().get('mediawiker_is_here', False):
            view = sublime.active_window().active_view()

            # internal links completions
            cursor_position = locations[0]  # view.sel()[0].begin()
            line_region = view.line(view.sel()[0])
            line_before_position = view.substr(sublime.Region(line_region.a, cursor_position))
            internal_link = ''
            if line_before_position.rfind('[[') > line_before_position.rfind(']]'):
                internal_link = line_before_position[line_before_position.rfind('[[') + 2:]

            if mw.INTERNAL_LINK_SPLITTER in internal_link:
                # cursor at custom url text zone..
                return []

            completions = []
            if internal_link:
                word_cursor_min_len = mw.get_setting('mediawiker_page_prefix_min_length', 3)
                ns_text = None
                ns_text_number = None

                if mw.NAMESPACE_SPLITTER in internal_link:
                    ns_text, internal_link = internal_link.split(mw.NAMESPACE_SPLITTER)

                if len(internal_link) >= word_cursor_min_len:
                    namespaces_search = [ns.strip() for ns in mw.get_setting('mediawiker_search_namespaces').split(',')]
                    if ns_text:
                        ns_text_number = mw.api.call('get_namespace_number', name=ns_text)

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
                                    if int(ns) in (mw.CATEGORY_NAMESPACE, mw.IMAGE_NAMESPACE):
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

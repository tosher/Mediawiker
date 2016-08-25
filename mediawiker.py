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
# TODO: https://github.com/mwclient/mwclient/commit/b4640d3b2537cfd6d17e2034ee53480b5ed2d4fe

pythonver = sys.version_info[0]
if pythonver >= 3:
    from .mwcommands import mw_utils as mw
    from .mwcommands import *
else:
    from mwcommands import mw_utils as mw
    from mwcommands import *


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


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    def run(self, edit, title, password):

        if not title:
            return

        is_writable = False
        sitecon = mw.get_connect(password)
        page = mw.get_page(sitecon, title)
        is_writable, text = mw.get_page_text(page)

        if is_writable or text:

            if is_writable and not text:
                sublime.status_message('Wiki page %s is not exists. You can create new..' % (title))
                text = '<!-- New wiki page: Remove this with text of the new page -->'
            # insert text
            self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': text})
            sublime.status_message('Page %s was opened successfully from %s.' % (title, mw.get_view_site()))
            mw.set_syntax(page=page)
            self.view.settings().set('mediawiker_is_here', True)
            self.view.settings().set('mediawiker_wiki_instead_editor', mw.get_setting('mediawiker_wiki_instead_editor'))
            self.view.set_name(title)

            self.view.set_scratch(True)
            # own is_changed flag instead of is_dirty for possib. to reset..
            self.view.settings().set('is_changed', False)
        else:
            sublime.message_dialog('You have not rights to view this page.')
            self.view.close()


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit, title, password):

        is_process_post = True
        is_skip_summary = mw.get_setting('mediawiker_skip_summary', False)
        self.sitecon = mw.get_connect(password)
        self.title = mw.get_title()
        if self.title:
            self.page = mw.get_page(self.sitecon, self.title)

            if self.page.can('edit'):

                if mw.get_setting('mediawiki_validate_revision_on_post', True) and self.view.settings().get('page_revision', 0) != self.page.revision:
                    is_process_post = sublime.ok_cancel_dialog('Page was changed on server, post page anyway? If not, new revision will be opened in new tab.')

                if is_process_post:
                    self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                    if not is_skip_summary:
                        # summary_message = 'Changes summary (%s):' % mw.get_setting('mediawiki_site_active')
                        summary_message = 'Changes summary (%s):' % mw.get_view_site()
                        self.view.window().show_input_panel(summary_message, '', self.on_done, None, None)
                    else:
                        self.on_done('')
                else:
                    self.view.window().run_command('mediawiker_page', {'action': 'mediawiker_reopen_page', 'new_tab': True})
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

                # update revision for page in view
                self.page = self.sitecon.Pages[self.title]
                self.view.settings().set('page_revision', self.page.revision)

                self.view.set_scratch(True)
                self.view.settings().set('is_changed', False)  # reset is_changed flag
                sublime.status_message('Wiki page %s was successfully published to wiki.' % (self.title))
                mw.save_mypages(self.title)
            else:
                sublime.status_message('You have not rights to edit this page')
        except mw.mwclient.EditError as e:
            sublime.status_message('Can\'t publish page %s (%s)' % (self.title, e))


class MediawikerEvents(sublime_plugin.EventListener):
    def on_activated(self, view):
        current_syntax = view.settings().get('syntax')
        current_site = mw.get_view_site()
        # TODO: move method to check mediawiker view to mwutils
        if current_syntax is not None and current_syntax.endswith(('Mediawiker/Mediawiki.tmLanguage', 'Mediawiker/MediawikiNG.tmLanguage')):
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
            sublime.active_window().run_command("mediawiker_page", {"action": "mediawiker_colapse"})

    def on_modified(self, view):
        if view.settings().get('mediawiker_is_here', False):
            is_changed = view.settings().get('is_changed', False)

            if is_changed:
                view.set_scratch(False)
            else:
                view.settings().set('is_changed', True)

            # folding gutters update
            sublime.active_window().run_command("mediawiker_page", {"action": "mediawiker_colapse"})

    def on_post_save(self, view):
        view.settings().set('mediawiker_wiki_instead_editor', False)

    def on_post_save_async(self, view):
        view.settings().set('mediawiker_wiki_instead_editor', False)

    def on_hover(self, view, point, hover_zone):
        # not fires in ST2
        # mouse_over folding: replaced by hover_text options
        # if view.settings().get('mediawiker_is_here', False) and hover_zone == sublime.HOVER_GUTTER and mw.get_setting('mediawiker_use_gutters_folding', True):
        #     sublime.active_window().run_command("mediawiker_page", {"action": "mediawiker_colapse", "action_params": {"type": "fold", "point": point}})

        if view.settings().get('mediawiker_is_here', False) and hover_zone == sublime.HOVER_TEXT:

            if mw.on_hover_comment(view, point):
                return

            if mw.on_hover_selected(view, point):
                return

            if mw.on_hover_tag(view, point):
                return

            if mw.on_hover_internal_link(view, point):
                return

            if mw.on_hover_template(view, point):
                return

            if mw.on_hover_heading(view, point):
                return

            # TODO: external links..

    def on_query_completions(self, view, prefix, locations):
        if view.settings().get('mediawiker_is_here', False):
            INTERNAL_LINK_SPLITTER = u'|'
            NAMESPACE_SPLITTER = u':'
            view = sublime.active_window().active_view()

            # internal links completions
            cursor_position = locations[0]  # view.sel()[0].begin()
            line_region = view.line(view.sel()[0])
            line_before_position = view.substr(sublime.Region(line_region.a, cursor_position))
            internal_link = ''
            if line_before_position.rfind('[[') > line_before_position.rfind(']]'):
                internal_link = line_before_position[line_before_position.rfind('[[') + 2:]

            if INTERNAL_LINK_SPLITTER in internal_link:
                # cursor at custom url text zone..
                return []

            completions = []
            if internal_link:
                word_cursor_min_len = mw.get_setting('mediawiker_page_prefix_min_length', 3)
                ns_text = None
                ns_text_number = None

                if NAMESPACE_SPLITTER in internal_link:
                    ns_text, internal_link = internal_link.split(NAMESPACE_SPLITTER)

                if len(internal_link) >= word_cursor_min_len:
                    namespaces_search = [ns.strip() for ns in mw.get_setting('mediawiker_search_namespaces').split(',')]
                    self.sitecon = mw.get_connect()
                    if ns_text:
                        ns_text_number = self.get_ns_number(ns_text)

                    pages = []
                    for ns in namespaces_search:
                        if not ns_text or ns_text_number and int(ns_text_number) == int(ns):
                            pages = self.sitecon.allpages(prefix=internal_link, namespace=ns)
                            for p in pages:
                                # name - full page name with namespace
                                # page_title - title of the page wo namespace
                                # For (Main) namespace, shows [page_title (Main)], makes [[page_title]]
                                # For Image, Category namespaces, shows [page_title namespace], makes [[name]]
                                # For other namespace, shows [page_title namespace], makes [[name|page_title]]
                                if int(ns):
                                    ns_name = p.name.split(':')[0]
                                    page_name = p.name if not self.is_equal_ns(ns_text, ns_name) else p.name.split(':')[1]
                                    if ns in ('6', '14'):  # file, category
                                        page_insert = page_name
                                    else:
                                        page_insert = '%s|%s' % (page_name, p.page_title)
                                else:
                                    ns_name = '(Main)'
                                    page_insert = p.page_title
                                page_show = '%s\t%s' % (p.page_title, ns_name)
                                completions.append((page_show, page_insert))

            return completions
        return []

    def get_ns_number(self, ns_name):
        return self.sitecon.namespaces_canonical_invert.get(
            ns_name, self.sitecon.namespaces_invert.get(
                ns_name, self.sitecon.namespaces_aliases_invert.get(
                    ns_name, None)))

    def is_equal_ns(self, ns_name1, ns_name2):
        ns_name1_number = self.get_ns_number(ns_name1)
        ns_name2_number = self.get_ns_number(ns_name2)
        if ns_name1_number and ns_name2_number and int(self.get_ns_number(ns_name1)) == int(self.get_ns_number(ns_name2)):
            return True
        return False

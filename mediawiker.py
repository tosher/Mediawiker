#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import sublime
import sublime_plugin

# https://github.com/wbond/sublime_package_control/wiki/Sublime-Text-3-Compatible-Packages
# http://www.sublimetext.com/docs/2/api_reference.html
# http://www.sublimetext.com/docs/3/api_reference.html
# sublime.message_dialog

# suppress deprecation warnings (turned on in mwclient lib: mwclient/__init__.py)
import warnings
warnings.simplefilter("ignore", DeprecationWarning)

pythonver = sys.version_info[0]
if pythonver >= 3:
    from .mwcommands import mw_utils as mw
    from .mwcommands import *
else:
    from mwcommands import mw_utils as mw
    from mwcommands import *


def plugin_loaded():
    mw.plugin_loaded()


class MediawikerOpenPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command(mw.cmd('page'), {"action": mw.cmd('show_page')})


class MediawikerReopenPageCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = mw.get_title()
        self.window.run_command(mw.cmd('page'), {
            'action': mw.cmd('show_page'),
            'action_params': {'title': title, 'new_tab': False}
        })


class MediawikerPostPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Publish page command '''

    def run(self):
        self.window.run_command(mw.cmd('page'), {"action": mw.cmd('publish_page')})


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    def run(self, edit, title=None, new_tab=None, site_active=None):

        self.new_tab = new_tab if new_tab is not None else mw.get_setting('newtab_ongetpage')

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
            mw.props.set_view_setting(view, 'site', self.site_active)
        else:
            view = self.view

        page = mw.api.call('get_page', title=title)

        if mw.api.page_can_edit(page):
            # can read and edit
            mw.props.set_view_setting(view, 'page_revision', mw.api.page_attr(page, 'revision'))
        elif not mw.api.page_can_read(page):
            # can not read and edit
            sublime.message_dialog(mw.api.PAGE_CANNOT_READ_MESSAGE)
            view.close()
            return
        elif not sublime.ok_cancel_dialog('%s Click OK button to view its source.' % mw.api.PAGE_CANNOT_EDIT_MESSAGE):
            # can not edit, but can read, but not want
            view.close()
            return

        text = mw.api.page_get_text(page)
        page_namespace = mw.api.page_attr(page, 'namespace')

        if not text:
            mw.status_message('Page [[%s]] is not exists. You can create new..' % (title))
            text = '<!-- New wiki page: Remove this with text of the new page -->'

        view.run_command(mw.cmd('insert_text'), {'position': 0, 'text': text, 'with_erase': True})

        if mw.props.get_site_setting(self.site_active, 'show_red_links'):
            mw.show_red_links(view, page)
        mw.status_message('Page [[%s]] was opened successfully from "%s".' % (title, mw.get_view_site()), replace=['[', ']'])
        mw.set_syntax(title, page_namespace)
        mw.props.set_view_setting(view, 'is_here', True)
        mw.props.set_view_setting(view, 'wiki_instead_editor', mw.get_setting('wiki_instead_editor'))
        view.set_name(title)

        view.set_scratch(True)
        # own is_changed flag instead of is_dirty for possib. to reset..
        mw.props.set_view_setting(view, 'is_changed', False)

        try:
            self.get_notifications()
        except Exception as e:
            mw.status_message('%s notifications exception: %s' % (mw.PM, e))

    def get_notifications(self):
        is_unread_notify_exists = mw.api.exists_unread_notifications()
        if is_unread_notify_exists and sublime.ok_cancel_dialog('You have new notifications.'):
            self.window.run_command(mw.cmd('get_notifications'))


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit):
        is_process_post = True
        is_skip_summary = mw.get_setting('skip_summary', False)
        self.title = mw.get_title()
        if self.title:
            self.page = mw.api.get_page(self.title)

            if mw.api.page_can_edit(self.page):

                if mw.get_setting('validate_revision_on_post', True) and mw.props.get_view_setting(self.view, 'page_revision', 0) != mw.api.page_attr(self.page, 'revision'):
                    is_process_post = sublime.ok_cancel_dialog('Page was changed on server, post page anyway? If not, new revision will be opened in new tab.')

                if is_process_post:
                    self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                    if not is_skip_summary:
                        summary_message = 'Changes summary (%s):' % mw.get_view_site()
                        mw.set_timeout_async(self.view.window().show_input_panel(summary_message, '', self.on_done, None, None), 0)
                    else:
                        mw.set_timeout_async(self.on_done, 0)
                else:
                    self.view.window().run_command(mw.cmd('page'), {
                        'action': mw.cmd('show_page'),
                        'action_params': {'title': self.title, 'new_tab': True}
                    })
            else:
                mw.status_message('You have not rights to edit this page')
        else:
            mw.status_message('Can\'t publish page with empty title')
            return

    def post_page(self, summary):
        summary = '%s%s' % (summary, mw.get_setting('summary_postfix'))
        mark_as_minor = mw.get_setting('mark_as_minor')
        # invert minor settings command '!'
        if summary[0] == '!':
            mark_as_minor = not mark_as_minor
            summary = summary[1:]
        mw.api.save_page(self.page, self.current_text, summary, mark_as_minor)

        # update revision for page in view
        self.page = mw.api.get_page(self.title)
        mw.props.set_view_setting(self.view, 'page_revision', mw.api.page_attr(self.page, 'revision'))

        if mw.props.get_site_setting(mw.get_view_site(), 'show_red_links'):
            mw.show_red_links(self.view, self.page)

        self.view.set_scratch(True)
        mw.props.set_view_setting(self.view, 'is_changed', False)  # reset is_changed flag
        mw.status_message('Page [[%s]] was successfully published to wiki "%s".' % (self.title, mw.get_view_site()), replace=['[', ']'])
        mw.save_mypages(self.title)

    def on_done(self, summary=None):
        if summary is None:
            summary = ''
        try:
            if mw.api.page_can_edit(self.page):
                self.post_page(summary=summary)
            else:
                mw.status_message(mw.api.PAGE_CANNOT_EDIT_MESSAGE)
        except mw.mwclient.EditError as e:
            mw.status_message('Can\'t publish page [[%s]] (%s)' % (self.title, e), replace=['[', ']'])


class MediawikerMovePageCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        self.title = mw.get_title()
        if self.title:
            self.page = mw.api.get_page(self.title)
            if mw.api.page_can_edit(self.page):
                mw.set_timeout_async(self.view.window().show_input_panel('New title', '', self.on_done_name, None, None), 0)
            else:
                mw.status_message('You have not rights to move this page')

    def on_done_name(self, name):
        self.new_title = name
        mw.set_timeout_async(self.view.window().show_input_panel('Reason', '', self.on_done_reason, None, None), 0)

    def on_done_reason(self, reason):
        self.reason = reason

        message = '''
        Old name: "%s"
        New name: "%s"
        Reason: %s

        Leave a redirect behind?
        ''' % (self.title, self.new_title, self.reason)

        is_make_redirect = sublime.yes_no_cancel_dialog(message, 'Yes', 'No')

        if is_make_redirect != sublime.DIALOG_CANCEL:
            no_redirect = True if is_make_redirect == sublime.DIALOG_NO else False
            mw.api.page_move(self.page, self.new_title, self.reason, no_redirect)
            mw.status_message('Page [[%s]] was moved successfully to [[%s]], leave redirect: %s' % (self.title, self.new_title, not no_redirect))

            if not no_redirect:
                mw.status_message('Refreshing old page (redirect): [[%s]]' % self.title)
                self.view.window().run_command(mw.cmd('reopen_page'))
            else:
                mw.status_message('Closing old page: [[%s]]' % self.title)
                self.view.close()

            mw.status_message('Opening new page: [[%s]]' % self.new_title)
            sublime.set_timeout(
                lambda: sublime.active_window().run_command(mw.cmd('page'), {
                    'action': mw.cmd('show_page'),
                    'action_params': {'title': self.new_title, 'new_tab': True}
                }), 2)

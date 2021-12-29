#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sys
import os
import sublime
from jinja2 import Environment, FileSystemLoader, Template
# suppress deprecation warnings (turned on in mwclient lib: mwclient/__init__.py)
import warnings
warnings.simplefilter("ignore", DeprecationWarning)

import sublime_plugin

# https://github.com/wbond/sublime_package_control/wiki/Sublime-Text-3-Compatible-Packages
# http://www.sublimetext.com/docs/2/api_reference.html
# http://www.sublimetext.com/docs/3/api_reference.html
# sublime.message_dialog


from .mwcommands import mw_utils as utils
from .mwcommands import *


def plugin_loaded():
    utils.plugin_loaded()


class MediawikerOpenPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {
            "action": utils.cmd('show_page')
        })

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return True


class MediawikerOpenPageSectionCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {
            "action": utils.cmd('show_page'),
            'action_params': {'by_section': True}
        })

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return True


class MediawikerReopenPageCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = utils.get_title()
        section = utils.props.get_view_setting(self.window.active_view(), 'section', None)
        self.window.run_command(utils.cmd('page'), {
            'action': utils.cmd('show_page'),
            'action_params': {'title': title, 'new_tab': False, 'section': section}
        })

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerReopenAllPagesCommand(sublime_plugin.WindowCommand):

    def run(self):
        if utils.conman.require_password():
            utils.error_message('Unable to peform couple page reopening without authorization')
            return

        for view in self.window.views():
            if not view.settings().get('mediawiker_is_here'):
                continue

            title = view.name()
            if not title:
                continue

            if view.is_dirty():
                utils.error_message('Page [[{}]] has unsaved changes - reopen skipped.'.format(title))
                continue

            section = utils.props.get_view_setting(view, 'section', None)
            view.run_command(utils.cmd('show_page'), {'title': title, 'new_tab': False, 'section': section})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerPostPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Publish page command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('publish_page')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    SECTION_SPLITTER = '::'

    def run(self, edit, title=None, new_tab=None, site_active=None, section=None, by_section=False):
        self.title = title
        self.section = section
        self.by_section = by_section
        self.sections_idx = []
        if utils.props.get_setting('offline_mode'):
            return

        self.new_tab = new_tab if new_tab is not None else utils.props.get_setting('newtab_ongetpage')

        # cases:
        # from view with page, opened from other site_active than in global settings - new page will be from the same site
        # from view with page, open page with another lang site - site param must be defined, will set it
        # from view with undefined site (new) open page by global site_active setting
        self.site_active = site_active if site_active else utils.get_view_site()

        panel = utils.InputPanelPageTitle(callback=self.get_section_number)
        panel.get_title(title)

    def get_section_number(self, title):
        self.title = title
        # if splitter in title => force set and open section
        # if section defined => force open section
        # if section undefined, no splitter and by_section is True => get section, open section
        # if section undefined, no splitter and by_section is False => just open page
        if not self.section and self.SECTION_SPLITTER in self.title:
            title_parts = self.title.split(self.SECTION_SPLITTER)
            self.title = title_parts[0]
            self.section = int(title_parts[1])
            return self.page_open(self.title)
        elif self.section or not self.by_section:
            return self.page_open(self.title)

        page = utils.api.call('get_page', title=title)
        sections = utils.api.call('page_sections', page=page)
        sections_menu = []
        self.sections_idx = []
        for section in sections:
            subtitle = '{}{}'.format('  ' * int(section['toclevel']), section['line'])
            sections_menu.append(subtitle)
            self.sections_idx.append(section['index'])
        sublime.active_window().show_quick_panel(sections_menu, self.on_done_get_section)

    def on_done_get_section(self, section_idx):
        if section_idx > -1 and self.sections_idx:
            self.section = int(self.sections_idx[section_idx])
            self.page_open(self.title)

    def page_open(self, title):
        self.title, _, inherit_suffix = title.partition('<-')

        if self.new_tab:
            view = sublime.active_window().new_file()
            utils.props.set_view_setting(view, 'site', self.site_active)
        else:
            view = self.view

        page = utils.api.call('get_page', title=self.title)
        utils.props.set_view_setting(view, 'section', self.section if self.section is not None else 0)

        if utils.api.page_can_edit(page):
            # can read and edit
            utils.props.set_view_setting(view, 'page_revision', utils.api.page_attr(page, 'revision'))
        elif not utils.api.page_can_read(page):
            # can not read and edit
            sublime.message_dialog(utils.api.PAGE_CANNOT_READ_MESSAGE)
            view.close()
            return
        elif not sublime.ok_cancel_dialog('{} Click OK button to view its source.'.format(utils.api.PAGE_CANNOT_EDIT_MESSAGE)):
            # can not edit, but can read, but not want
            view.close()
            return

        text = utils.api.page_get_text(page, self.section)
        page_namespace = utils.api.page_attr(page, 'namespace')

        if not text:
            utils.error_message('Page [[{}]] does not exist. You can create it..'.format(self.title))
            text = utils.comment(
                'New wiki page: Remove this with text of the new page',
                page_name=self.title,
                page_namespace=page_namespace
            )
            text = self.render_page_template(
                site_name=utils.get_view_site(),
                page_name=self.title,
                page_namespace=page_namespace,
                page_text=text,
                inherit_suffix=inherit_suffix
            )

        with utils.p.settings_hack('translate_tabs_to_spaces', False, disabled=not utils.props.get_setting('not_translate_tabs_on_page_open')):
            view.run_command(utils.cmd('insert_text'), {'position': 0, 'text': text, 'with_erase': True})
            view.run_command('detect_indentation')

        if utils.props.get_site_setting(self.site_active, 'show_red_links'):
            utils.show_red_links(view, page)

        utils.status_message(
            'Page [[{}]] was opened successfully from "{}".'.format(
                self.title,
                utils.get_view_site()
            ),
            replace_patterns=['[', ']']
        )
        utils.set_syntax(self.title, page_namespace)
        utils.props.set_view_setting(view, 'is_here', True)
        utils.props.set_view_setting(view, 'wiki_instead_editor', utils.props.get_setting('wiki_instead_editor'))
        view.set_name(self.title)
        view.set_scratch(True)
        # own is_changed flag instead of is_dirty for possib. to reset..
        utils.props.set_view_setting(view, 'is_changed', False)

        try:
            self.get_notifications()
        except Exception as e:
            utils.error_message('{} notifications exception: {}'.format(utils.props.PM, e))

    def get_notifications(self):
        is_unread_notify_exists = utils.api.exists_unread_notifications()
        if is_unread_notify_exists and sublime.ok_cancel_dialog('You have new notifications.'):
            self.view.window().run_command(utils.cmd('notifications'))

    def render_page_template(self, **kwargs):
        tpl_path = utils.props.get_setting('new_page_template_path')
        if not tpl_path:
            return kwargs.get('page_text', '')

        if tpl_path.startswith('wiki:'):
            page_tpl = utils.api.call('get_page', title=tpl_path.split(':', 1)[-1])
            if not page_tpl:
                utils.error_message('Incorrect value for option "new_page_template_path", wiki page name is empty!'.format(self.title))
            text_tpl = utils.api.page_get_text(page_tpl)
            template = Template(text_tpl)
        else:
            if not os.path.isabs(tpl_path):
                tpl_path = utils.p.from_package(tpl_path, name='User', is_abs=True)
            # keep_trailing_newline=True
            env = Environment(loader=FileSystemLoader(searchpath=os.path.dirname(tpl_path)))
            template = env.get_template(os.path.basename(tpl_path))

        text = template.render(**kwargs)
        return text


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        is_process_post = True
        is_skip_summary = utils.props.get_setting('skip_summary', False)
        self.title = utils.get_title()
        if self.title:
            self.page = utils.api.get_page(self.title)

            if utils.api.page_can_edit(self.page):

                if utils.props.get_setting('validate_revision_on_post', True) and utils.props.get_view_setting(self.view, 'page_revision', 0) != utils.api.page_attr(self.page, 'revision'):
                    is_process_post = sublime.ok_cancel_dialog('Page was changed on server, post page anyway? If not, new revision will be opened in new tab.')

                if is_process_post:
                    self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                    if not is_skip_summary:
                        summary_title = 'Changes summary ({}):'.format(utils.get_view_site())
                        summary_buffered = self.get_summary_buffer()
                        utils.set_timeout_async(self.view.window().show_input_panel(summary_title, summary_buffered, self.on_done, None, None), 0)
                    else:
                        utils.set_timeout_async(self.on_done, 0)
                else:
                    self.view.window().run_command(utils.cmd('page'), {
                        'action': utils.cmd('show_page'),
                        'action_params': {'title': self.title, 'new_tab': True}
                    })
            else:
                utils.error_message(utils.api.PAGE_CANNOT_EDIT_MESSAGE)
        else:
            utils.error_message('Can\'t publish page with empty title')
            return

    def post_page(self, summary):
        mark_as_minor = utils.props.get_setting('mark_as_minor')
        # invert minor settings command '!'
        if summary and summary[0] == '!':
            mark_as_minor = not mark_as_minor
            summary = summary[1:]

        summary_full = '{}{}{}'.format(
            utils.props.get_setting('summary_prefix'),
            summary,
            utils.props.get_setting('summary_postfix')
        )

        section = utils.props.get_view_setting(self.view, 'section', None)

        exc = None
        is_success = False
        try:
            is_success = utils.api.save_page(
                page=self.page,
                text=self.current_text,
                summary=summary_full,
                mark_as_minor=mark_as_minor,
                section=section
            )

        except Exception as e:
            exc = e
            is_success = False

        if not is_success:
            err_msg = 'There was an error while trying to publish page [[{}]] to wiki "{}".'.format(
                self.title,
                utils.get_view_site(),
            )
            if exc:
                err_msg += ', {} exception: {}'.format(type(exc).__name__, exc)

            utils.error_message(err_msg, replace_patterns=['[', ']'])
            self.set_summary_buffer(summary)
            return

        # update revision for page in view
        self.page = utils.api.get_page(self.title)
        utils.props.set_view_setting(self.view, 'page_revision', utils.api.page_attr(self.page, 'revision'))

        if utils.props.get_site_setting(utils.get_view_site(), 'show_red_links'):
            utils.show_red_links(self.view, self.page)

        self.view.set_scratch(True)
        utils.props.set_view_setting(self.view, 'is_changed', False)  # reset is_changed flag

        title = self.title
        view_site = utils.get_view_site()
        msg = 'Page [[{}]] was successfully published to wiki "{}"'.format(title, view_site)
        if summary:
            msg = '{}: "{}"'.format(msg, summary)
        utils.status_message('{}.'.format(msg), replace_patterns=['[', ']'])
        utils.save_mypages(self.title)
        self.erase_summary_buffer()

    def get_summary_buffer(self):
        if utils.props.get_setting('summary_save_on_fail'):
            return utils.props.get_site_setting(utils.get_view_site(), 'summary_fail_buf')
        return ''

    def set_summary_buffer(self, summary):
        if utils.props.get_setting('summary_save_on_fail'):
            utils.props.set_site_setting(utils.get_view_site(), 'summary_fail_buf', summary)

    def erase_summary_buffer(self):
        if utils.props.get_setting('summary_save_on_fail'):
            utils.props.set_site_setting(utils.get_view_site(), 'summary_fail_buf', '')

    def on_done(self, summary=None):
        if summary is None:
            summary = ''

        if not utils.api.page_can_edit(self.page):
            self.set_summary_buffer(summary)
            utils.error_message(utils.api.PAGE_CANNOT_EDIT_MESSAGE)
            return

        self.post_page(summary=summary)


class MediawikerMovePageCommand(sublime_plugin.TextCommand):

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.view, 'is_here')

    def run(self, edit):
        self.title = utils.get_title()
        if self.title:
            self.page = utils.api.get_page(self.title)
            if utils.api.page_can_edit(self.page):
                utils.set_timeout_async(self.view.window().show_input_panel('New title', '', self.on_done_name, None, None), 0)
            else:
                utils.error_message('You have not rights to move this page')

    def on_done_name(self, name):
        self.new_title = name
        utils.set_timeout_async(self.view.window().show_input_panel('Reason', '', self.on_done_reason, None, None), 0)

    def on_done_reason(self, reason):
        self.reason = reason

        message = '''
        Old name: "{}"
        New name: "{}"
        Reason: {}

        Leave a redirect behind?
        '''.format(self.title, self.new_title, self.reason)

        is_make_redirect = sublime.yes_no_cancel_dialog(message, 'Yes', 'No')

        if is_make_redirect != sublime.DIALOG_CANCEL:
            no_redirect = True if is_make_redirect == sublime.DIALOG_NO else False
            utils.api.page_move(self.page, self.new_title, self.reason, no_redirect)
            utils.status_message('Page [[{}]] was moved successfully to [[{}]], leave redirect: {}'.format(self.title, self.new_title, not no_redirect))

            if not no_redirect:
                utils.status_message('Refreshing old page (redirect): [[{}]]'.format(self.title))
                self.view.window().run_command(utils.cmd('reopen_page'))
            else:
                utils.status_message('Closing old page: [[{}]]'.format(self.title))
                self.view.close()

            utils.status_message('Opening new page: [[{}]]'.format(self.new_title))
            sublime.set_timeout(
                lambda: sublime.active_window().run_command(utils.cmd('page'), {
                    'action': utils.cmd('show_page'),
                    'action_params': {'title': self.new_title, 'new_tab': True}
                }), 2)


class MediawikerOpenTalkPageCommand(sublime_plugin.WindowCommand):
    ''' Open talk page for current page '''

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')

    def run(self):
        page = utils.api.get_page(utils.get_title())
        page_talk = utils.api.get_page_talk_page(page)

        if utils.api.page_attr(page, 'name') == utils.api.page_attr(page_talk, 'name'):
            sublime.message_dialog('There is a talk page already.')

        sublime.set_timeout(
            lambda: self.window.run_command(
                utils.cmd('page'), {
                    'action': utils.cmd('show_page'),
                    'action_params': {'title': utils.api.page_attr(page_talk, 'name'), 'new_tab': True}
                }
            ), 2)


class MediawikerOpenNewPageTemplateCommand(sublime_plugin.TextCommand):
    ''' Open template for new pages '''
    OPTION_NAME = 'new_page_template_path'

    def run(self, edit):
        tpl_path = utils.props.get_setting(self.OPTION_NAME)
        if not tpl_path:
            utils.error_message('Path to template does not defined, please set this via "{}" option'.format(self.OPTION_NAME))
            return

        if tpl_path.startswith('wiki:'):

            if utils.props.get_setting('offline_mode'):
                utils.error_message('Wiki based new page template does not available in offline mode')
                return

            page_name = tpl_path.split(':', 1)[-1]
            if not page_name:
                utils.error_message('Empty value for option "{}", wiki page name is empty!'.format(self.OPTION_NAME))

            sublime.set_timeout(
                lambda: self.view.window().run_command(
                    utils.cmd('page'),
                    {
                        'action': utils.cmd('show_page'),
                        'action_params': {'title': page_name, 'new_tab': True}
                    }
                ),
                2
            )

        else:
            if not os.path.isabs(tpl_path):
                tpl_path = utils.p.from_package(tpl_path, name='User', is_abs=True)
            self.view.window().open_file(tpl_path)


class MediawikerPopupCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.active_view()
        MediawikerEvents.on_hover(self, view, view.sel()[0].a, sublime.HOVER_TEXT)

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')

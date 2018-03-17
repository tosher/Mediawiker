#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
else:
    import mw_utils as utils


class MediawikerPageCopyCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        panel = utils.InputPanelPageTitle(callback=self.get_src_site)
        panel.get_title('Bruce Lee')

    def get_src_site(self, title):
        if not title:
            return

        self.title = title
        sites = utils.props.get_setting('site')
        self.site_keys = [x for x in sorted(sites.keys(), key=str.lower)]
        sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.site_keys, self.on_site_selected), 1)

    def on_site_selected(self, index):
        if index < 0:
            return
        self.src_site_name = self.site_keys[index]

        # get remote page
        src_api = utils.PreAPI(conman=utils.conman, site_name=self.src_site_name)
        src_page = src_api.call('get_page', title=self.title)
        if not src_api.page_can_read(src_page):
            sublime.message_dialog(utils.api.PAGE_CANNOT_READ_MESSAGE)
            return
        text = src_api.page_get_text(src_page)

        cnt = len([i for i in src_page.images()])
        if sublime.ok_cancel_dialog('Copy %s images from source page?' % cnt):
            images = src_page.images()
            for image in images:
                file_name = src_api.page_attr(image, 'page_title')
                is_success = utils.api.call(
                    'process_upload',
                    url=image.imageinfo['url'],
                    filename=file_name,
                    description='Image for page "%s", copied from "%s"' % (self.title, self.src_site_name)
                )
                if is_success:
                    utils.status_message('File %s successfully copied to wiki' % (file_name))
                else:
                    utils.status_message('Error while trying to copy file %s to wiki' % (file_name))

        cnt = len([i for i in src_page.templates()])
        if sublime.ok_cancel_dialog('Copy %s templates (only first level) from source page?' % cnt):
            templates = src_page.templates()
            for template in templates:
                template_name = src_api.page_attr(template, 'page_title')
                template_text = src_api.page_get_text(template)
                is_success = utils.api.save_page(
                    page=template,
                    text=template_text,
                    summary='Template copy from %s for page %s' % (self.src_site_name, self.title),
                    mark_as_minor=False
                )
                if not is_success:
                    utils.status_message(
                        'There was an error while trying to copy template [[%s]] to wiki "%s".' % (
                            template_name,
                            utils.get_view_site()
                        ),
                        replace=['[', ']']
                    )
                else:
                    utils.status_message(
                        'Template [[%s]] was successfully copied to wiki "%s".' % (
                            self.title,
                            utils.get_view_site()
                        ),
                        replace=['[', ']']
                    )

        # get local page
        page = utils.api.call('get_page', title=self.title)
        is_success = utils.api.save_page(
            page=page,
            text=text,
            summary='Page copy from %s' % self.src_site_name,
            mark_as_minor=False
        )
        if not is_success:
            utils.status_message(
                'There was an error while trying to copy page [[%s]] to wiki "%s".' % (
                    self.title,
                    utils.get_view_site()
                ),
                replace=['[', ']']
            )
            return
        else:
            utils.status_message(
                'Page [[%s]] was successfully copied to wiki "%s".' % (
                    self.title,
                    utils.get_view_site()
                ),
                replace=['[', ']']
            )

        self.view.window().run_command(utils.cmd('page'), {
            'action': utils.cmd('show_page'),
            'action_params': {'title': self.title, 'new_tab': True}
        })

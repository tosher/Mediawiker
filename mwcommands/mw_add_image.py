#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerInsertImageCommand(sublime_plugin.WindowCommand):
    ''' alias to Add image command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_image"})


class MediawikerAddImageCommand(sublime_plugin.TextCommand):
    password = ''
    image_prefix_min_lenght = 4
    images_names = []

    def run(self, edit, password, title=''):
        self.password = password
        self.image_prefix_min_lenght = mw.get_setting('mediawiker_image_prefix_min_length', 4)
        sublime.active_window().show_input_panel('Wiki image prefix (min %s):' % self.image_prefix_min_lenght, '', self.show_list, None, None)

    def show_list(self, image_prefix):
        if len(image_prefix) >= self.image_prefix_min_lenght:
            sitecon = mw.get_connect(self.password)
            images = sitecon.allpages(prefix=image_prefix, namespace=mw.IMAGE_NAMESPACE)  # images list by prefix
            # self.images_names = map(self.get_page_title, images)
            self.images_names = [self.get_page_title(x) for x in images]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.images_names, self.on_done), 1)
        else:
            sublime.message_dialog('Image prefix length must be more than %s. Operation canceled.' % self.image_prefix_min_lenght)

    def get_page_title(self, obj):
        return obj.page_title

    def on_done(self, idx):
        if idx >= 0:
            index_of_cursor = self.view.sel()[0].begin()
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': '[[Image:%s]]' % self.images_names[idx]})

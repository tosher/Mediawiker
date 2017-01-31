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
        self.window.run_command(mw.cmd('page'), {"action": mw.cmd('add_image')})


class MediawikerAddImageCommand(sublime_plugin.TextCommand):
    image_prefix_min_lenght = 4
    images_names = []

    def run(self, edit):
        self.image_prefix_min_lenght = mw.get_setting('image_prefix_min_length', 4)
        sublime.active_window().show_input_panel('Wiki image prefix (min %s):' % self.image_prefix_min_lenght, '', self.show_list, None, None)

    def show_list(self, image_prefix):
        if len(image_prefix) >= self.image_prefix_min_lenght:
            images = mw.api.call('get_pages', prefix=image_prefix, namespace=mw.api.IMAGE_NAMESPACE)  # images list by prefix
            self.images_names = [mw.api.page_attr(x, 'page_title') for x in images]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.images_names, self.on_done), 1)
        else:
            sublime.message_dialog('Image prefix length must be more than %s. Operation canceled.' % self.image_prefix_min_lenght)

    def on_done(self, idx):
        if idx >= 0:
            index_of_cursor = self.view.sel()[0].begin()
            self.view.run_command(mw.cmd('insert_text'), {'position': index_of_cursor, 'text': '[[Image:%s]]' % self.images_names[idx]})

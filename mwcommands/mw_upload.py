#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerFileUploadCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_upload"})


class MediawikerUploadCommand(sublime_plugin.TextCommand):

    password = None
    file_path = None
    file_destname = None
    file_descr = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('File path:', '', self.get_destfilename, None, None)

    def get_destfilename(self, file_path):
        if file_path:
            self.file_path = file_path
            file_destname = os.path.basename(file_path)
            sublime.active_window().show_input_panel('Destination file name [%s]:' % (file_destname), file_destname, self.get_filedescr, None, None)

    def get_filedescr(self, file_destname):
        if not file_destname:
            file_destname = os.path.basename(self.file_path)
        self.file_destname = file_destname
        sublime.active_window().show_input_panel('File description:', '', self.on_done, None, None)

    def on_done(self, file_descr=''):
        sitecon = mw.get_connect(self.password)
        if file_descr:
            self.file_descr = file_descr
        else:
            self.file_descr = '%s as %s' % (os.path.basename(self.file_path), self.file_destname)
        try:
            with open(self.file_path, 'rb') as f:
                sitecon.upload(f, self.file_destname, self.file_descr)
            sublime.status_message('File %s successfully uploaded to wiki as %s' % (self.file_path, self.file_destname))
        except IOError as e:
            sublime.message_dialog('Upload io error: %s' % e)
        except Exception as e:
            sublime.message_dialog('Upload error: %s' % e)

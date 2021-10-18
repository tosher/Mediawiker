#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import os
import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerFileUploadCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('upload')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return True


class MediawikerUploadCommand(sublime_plugin.TextCommand):

    file_path = None
    file_destname = None
    file_descr = None

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        sublime.active_window().show_input_panel('File path:', '', self.get_destfilename, None, None)

    def get_destfilename(self, file_path):
        if file_path:
            self.file_path = file_path
            file_destname = os.path.basename(file_path)
            sublime.active_window().show_input_panel('Destination file name [{}]:'.format(file_destname), file_destname, self.get_filedescr, None, None)
        # else:
        #     # try to get clipboard and upload
        #     try:
        #         # data = sublime.get_clipboard()
        #         import win32clipboard
        #         win32clipboard.OpenClipboard()
        #         if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
        #             data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
        #         win32clipboard.CloseClipboard()
        #     except Exception as e:
        #         print('Exception from clipboard {}'.format(e))
        #         return
        #     upload_file = p.from_package('{}_upload_data.png'.format(p.PML), name='User', posix=False, is_abs=True)
        #     print(upload_file)
        #     with open(upload_file, 'w+b') as tf:
        #         tf.write(data)
        #     self.get_filedescr(upload_file)

    def get_filedescr(self, file_destname):
        if not file_destname:
            file_destname = os.path.basename(self.file_path)
        self.file_destname = file_destname
        sublime.active_window().show_input_panel('File description:', '', self.on_done, None, None)

    def on_done(self, file_descr=''):
        if file_descr:
            self.file_descr = file_descr
        else:
            self.file_descr = '{} as {}'.format(os.path.basename(self.file_path), self.file_destname)
        try:
            is_success = self.upload()
            if is_success:
                utils.status_message('File "{}" successfully uploaded to wiki as "{}"'.format(self.file_path, self.file_destname))
            else:
                utils.error_message('Error while trying to upload file "{}" to wiki as "{}"'.format(self.file_path, self.file_destname))
        except IOError as e:
            utils.error_message('Upload io error: {}'.format(e))
        except Exception as e:
            utils.error_message('Upload error: {}'.format(e))

    def upload(self):
        if self.file_path.startswith('http'):
            # require `$wgAllowCopyUploads = true` in LocalSettings.php
            return utils.api.call('process_upload', url=self.file_path, filename=self.file_destname, description=self.file_descr)
        with open(self.file_path, 'rb') as f:
            return utils.api.call('process_upload', file_handler=f, filename=self.file_destname, description=self.file_descr)

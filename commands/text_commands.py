#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sublime
import sublime_plugin


class MediawikerInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text):
        self.view.insert(edit, position, text)


class MediawikerReplaceTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, text):
        self.view.replace(edit, self.view.sel()[0], text)

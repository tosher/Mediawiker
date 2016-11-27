#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin


class MediawikerInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text, with_erase=False):
        if with_erase:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, position, text)


class MediawikerReplaceTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, text):
        self.view.replace(edit, self.view.sel()[0], text)

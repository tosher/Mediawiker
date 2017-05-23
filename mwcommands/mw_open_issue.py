#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import webbrowser

# import sublime
import sublime_plugin


class MediawikerOpenIssueCommand(sublime_plugin.WindowCommand):

    def run(self):
        webbrowser.open('https://github.com/tosher/Mediawiker/issues')

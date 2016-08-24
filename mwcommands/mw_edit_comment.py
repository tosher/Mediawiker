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


class MediawikerEditCommentCommand(sublime_plugin.TextCommand):

    DRAW_TYPE = sublime.PERSISTENT

    def run(self, edit, a, b, isdel=False):
        self.a = a
        self.b = b
        self.isdel = isdel
        self.gutter_png = 'Packages/Theme - Default/dot.png' if pythonver >= 3 else ''

        if a and b:
            self.comment_region = sublime.Region(a, b)

            if self.isdel:
                self.del_comment()
                return

            comment_text = mw.get_comment_by_region(self.comment_region)
            sublime.active_window().show_input_panel('Comment:', comment_text or '', self.on_done, None, None)

    def on_done(self, text):

        self.save_comment(text)
        self.add_region()

    def add_region(self):
        cur_comments = self.view.get_regions(mw.COMMENT_REGIONS_KEY)
        cur_comments.append(self.comment_region)
        self.view.add_regions(mw.COMMENT_REGIONS_KEY, cur_comments, 'comment', self.gutter_png, self.DRAW_TYPE)

    def del_region(self):
        cur_comments = self.view.get_regions(mw.COMMENT_REGIONS_KEY)
        cur_comments.remove(self.comment_region)
        self.view.add_regions(mw.COMMENT_REGIONS_KEY, cur_comments, 'comment', self.gutter_png, self.DRAW_TYPE)

    def del_comment(self):
        self.save_comment(text=None)

    def save_comment(self, text):

        site = mw.get_view_site()
        title = mw.get_title()
        mediawiker_comments = mw.get_comments('mediawiker_comments', {})

        if site not in mediawiker_comments:
            mediawiker_comments[site] = {}

        if title not in mediawiker_comments[site]:
            mediawiker_comments[site][title] = {}

        r_key = ('%s:%s' % (self.a, self.b))

        if r_key in mediawiker_comments[site][title] and self.isdel:
            # if sublime.ok_cancel_dialog('Are you sure to delete this comment?', 'Yes'):
            # ST crash
            del(mediawiker_comments[site][title][r_key])
            self.del_region()
        else:
            mediawiker_comments[site][title][r_key] = text

        mw.set_comments('mediawiker_comments', mediawiker_comments)

#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import re

import sublime
# import sublime_plugin
import requests
import webbrowser

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
    import base64
else:
    import mw_utils as mw

HOVER_IMG_SIZE = 300

HOVER_HTML_HEADER = '''
<html>
    <style>
        ul { margin-left: 0; padding-left: 0rem; }
        li { margin-left: 0; display: block; }
        a {text-decoration: none; }
    </style>

    <body id="mediawiker_html">
'''

HOVER_HTML_FOOTER = '''
    </body>
</html>
'''


def on_hover_selected(view, point):

    def on_navigate_selected(link):
        if link == 'bold':
            sublime.active_window().run_command("insert_snippet", {"contents": "'''${0:$SELECTION}'''"})
        elif link == 'italic':
            sublime.active_window().run_command("insert_snippet", {"contents": "''${0:$SELECTION}''"})
        elif link == 'code':
            sublime.active_window().run_command("insert_snippet", {"contents": "<code>${0:$SELECTION}</code>"})
        elif link == 'pre':
            sublime.active_window().run_command("insert_snippet", {"contents": "<pre>${0:$SELECTION}</pre>"})
        elif link == 'nowiki':
            sublime.active_window().run_command("insert_snippet", {"contents": "<nowiki>${0:$SELECTION}</nowiki>"})
        elif link == 'kbd':
            sublime.active_window().run_command("insert_snippet", {"contents": "<kbd>${0:$SELECTION}</kbd>"})
        elif link == 'strike':
            sublime.active_window().run_command("insert_snippet", {"contents": "<s>${0:$SELECTION}</s>"})
        elif link.startswith('comment'):
            a, b = link.split(':')[-2:]
            sublime.active_window().run_command("mediawiker_edit_comment", {"a": int(a), "b": int(b)})

    selected = view.sel()
    for r in selected:
        if r and r.contains(point):
            content = [
                HOVER_HTML_HEADER,
                'Format:',
                '<ul>',
                '<li><a href="bold">Bold</a></li>',
                '<li><a href="italic">Italic</a></li>',
                '<li><a href="code">Code</a></li>',
                '<li><a href="pre">Predefined</a></li>',
                '<li><a href="nowiki">Nowiki</a></li>',
                '<li><a href="kbd">Keyboard</a></li>',
                '<li><a href="strike">Strike</a></li>',
                '<li><a href="comment:%s:%s">Comment</a></li>' % (r.a, r.b),
                '</ul>',
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)
            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate_selected
            )
            return True

    return False


def on_hover_internal_link(view, point):

    def on_navigate(link):
        page_name = link.split(':', 1)[-1].replace(' ', '_')
        if link.startswith('open'):
            view.window().run_command("mediawiker_page", {
                'action': 'mediawiker_show_page',
                'action_params': {'title': page_name}
            })
        elif link.startswith('browse'):
            url = mw.get_page_url(page_name)
            webbrowser.open(url)

    links = mw.get_internal_links_regions(view)
    for r in links:
        if r[1].contains(point):

            is_file = False
            img_base64 = None
            if mw.get_setting('mediawiker_show_image_in_popup', True):
                try:
                    page = mw.api.get_page(r[0])
                    if mw.api.page_attr(page, 'namespace') == mw.IMAGE_NAMESPACE:  # TODO: prepai equal?
                        is_file = True
                        extra_properties = {
                            'imageinfo': (
                                ('iiprop', 'timestamp|user|comment|url|size|sha1|metadata|archivename'),
                                ('iiurlwidth', HOVER_IMG_SIZE)
                            )
                        }
                        img = mw.api.call('image_init', name=r[0], extra_properties=extra_properties)
                        img_remote_url = img.imageinfo['thumburl']
                        response = requests.get(img_remote_url)
                        # "http:" is not works: https://github.com/SublimeTextIssues/Core/issues/1378
                        img_base64 = "data:" + response.headers['Content-Type'] + ";" + "base64," + str(base64.b64encode(response.content).decode("utf-8"))
                except:
                    pass

            h = 'Page "%s"' % r[0] if not is_file else 'File "%s"' % r[0].split(':')[1]

            content = [
                HOVER_HTML_HEADER,
                '<h4>%s</h4>' % h,
                '<img src="%(uri)s">' % {'uri': img_base64} if img_base64 else '',
                '<ul><li><a href="open:%(point)s">Open</a> | <a href="browse:%(point)s">View in browser</a></li></ul>' % {'point': r[0]},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                max_width=500,
                max_height=500,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            # TODO: phantoms for images
            # https://forum.sublimetext.com/t/dev-build-3118/21270
            # view.add_phantom("test", view.sel()[0], "Hello, World!", sublime.LAYOUT_BLOCK)
            # view.erase_phantoms("test")
            # img_html = '<img src="%(uri)s">' % {'uri': img_base64} if img_base64 else ''
            # view.add_phantom("image", sublime.Region(point, point), img_html, sublime.LAYOUT_BLOCK)
            return True

    return False


def get_templates(view):

    TPL_START = r'(?<![^\{]\{)\{{2}(?!\{[^\{])'
    TPL_STOP = r'(?<![^\}]\})\}{2}(?!\}([^\}]|$))'
    TYPE_START = 'start'
    TYPE_STOP = 'stop'
    text_region = sublime.Region(0, view.size())
    line_regions = view.split_by_newlines(text_region)
    # print(line_regions)
    lines_data = []
    templates = []
    for region in line_regions:
        line_text = view.substr(region)
        starts = [region.a + m.start() for m in re.finditer(TPL_START, line_text)]
        stops = [region.a + m.start() for m in re.finditer(TPL_STOP, line_text)]

        line_index = {}
        for i in starts:
            line_index[i] = TYPE_START
        for i in stops:
            line_index[i] = TYPE_STOP

        if starts or stops:
            lines_data.append(line_index)

    _templates = []
    for d in lines_data:
        line_indexes = list(d.keys())
        line_indexes.sort()
        for i in line_indexes:
            if d[i] == TYPE_START:
                t = sublime.Region(i + 2, i + 2)  # unknown end
                _templates.append(t)
            elif d[i] == TYPE_STOP:
                # ST2 compat Region update
                # _templates[-1].b = i
                if _templates:  # if smth. wrong with parsing early, list can be empty, skipping
                    _templates[-1] = sublime.Region(_templates[-1].a, i)
                    templates.append((_templates[-1], len(_templates)))  # template region and includes level
                    _templates = _templates[:-1]
    return templates


def on_hover_template(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})
        else:
            sublime.active_window().run_command("mediawiker_page", {
                'action': 'mediawiker_show_page',
                'action_params': {'title': link.replace(' ', '_')}
            })

    SCRIBUNTO_PREFIX = '#invoke'
    tpl_regions = []
    _rs = get_templates(view)
    for r in _rs:
        tpl_regions.append(r[0])

    for r in tpl_regions:
        if r.contains(point):

            template_name = view.substr(r).split('|')[0].strip()
            if template_name.startswith(SCRIBUNTO_PREFIX):
                # #invoke:ScribuntoTest
                template_name = template_name.split(':')[-1]
                template_link = 'Module:%s' % template_name
                template_type = 'Scribunto module'
            else:
                template_link = 'Template:%s' % template_name
                template_type = 'Template'

            content = [
                HOVER_HTML_HEADER,
                '<h4>%s "%s"</h4>' % (template_type, template_name),
                '<a href="%(link)s">Open</a> | <a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a>' % {'link': template_link, 'point': point},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_heading(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})

    h_regions = []
    for lvl in range(2, 6):
        _rs = view.get_regions('h_%s' % lvl)
        if _rs:
            h_regions = h_regions + _rs

    for r in h_regions:
        _r = sublime.Region(view.line(r).a, r.a)
        if _r.contains(point):

            h_name = view.substr(_r).replace('=', '').strip()
            content = [
                HOVER_HTML_HEADER,
                '<h4>Heading "%s"</h4>' % (h_name),
                '<a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a>' % {'point': point},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_tag(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})

    fold_tags = mw.get_setting("mediawiker_fold_tags", ["source", "syntaxhighlight", "div", "pre"])
    tag_regions = []

    for tag in fold_tags:
        regs = view.get_regions(tag)
        for r in regs:
            tag_regions.append((tag, r))

    for r in tag_regions:
        if r[1].contains(point):

            content = [
                HOVER_HTML_HEADER,
                '<h4>%s</h4>' % r[0].title(),
                '<a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a>' % {'point': point},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_comment(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})

    def get_text_pretty(r):
        text = view.substr(r).strip().lstrip('<!--').rstrip('-->')
        text = text.replace('TODO', '<strong style="color:#E08283;">TODO</strong>')
        text = text.replace('NOTE', '<strong style="color:#26A65B;">NOTE</strong>')
        text = text.replace('WARNING', '<strong style="color:#C0392B;">WARNING</strong>')
        text = text.replace('\n', '<br>')
        return text

    comment_regions = view.get_regions('comment')

    if not comment_regions:
        return False

    for r in comment_regions:
        if r.contains(point):

            comment_text = get_text_pretty(r)
            content = [
                HOVER_HTML_HEADER,
                '<h4>Note</h4>',
                '<ul>'
                '<li>%s</li>' % comment_text,
                '<li><a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a></li>' % {'point': point},
                '</ul>',
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False

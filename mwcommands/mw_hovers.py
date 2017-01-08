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
    from . import mw_html
    import base64
else:
    import mw_utils as mw
    import mw_html

HOVER_IMG_SIZE = 300

html = mw_html.MwHtmlAdv(html_id='mediawiker_hover', user_css=False)
html.css_rules['ul'] = {'margin-left': '0', 'padding-left': '0rem'}
html.css_rules['li'] = {'margin-left': '0', 'display': 'block'}
html.css_rules['a']['text-decoration'] = 'none'
html.css_rules['body']['padding'] = '1rem 2rem 1rem 2rem'
html.css_rules['.undefined'] = {'padding': '5px', 'color': '#c0c0c0'}
html.css_rules['.note'] = {'padding': '5px', 'color': '#7D9DF8'}
html.css_rules['.wide'] = {'padding-left': '0.5rem', 'padding-right': '0.5rem'}


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
            sublime.active_window().run_command("insert_snippet", {"contents": "<!-- ${0:$SELECTION} -->"})

    selected = view.sel()
    for r in selected:
        if r and r.contains(point):

            content = [
                html.unnumbered_list(
                    html.link('bold', 'Bold'),
                    html.link('italic', 'Italic'),
                    html.link('code', 'Code'),
                    html.link('pre', 'Pre'),
                    html.link('nowiki', 'Nowiki'),
                    html.link('kbd', 'Keyboard'),
                    html.link('strike', 'Strike'),
                    html.link('comment', 'Comment'),
                    css_class='undefined'
                )
            ]

            content_html = html.build(content)
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
            view.window().run_command(mw.cmd('page'), {
                'action': mw.cmd('show_page'),
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
            if mw.get_setting('show_image_in_popup', True):
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
                html.h(lvl=4, title=h),
                html.img(uri=img_base64) if img_base64 else '',
                html.br(cnt=2) if img_base64 else '',
                html.join(
                    html.link('open:%s' % r[0], 'Open'),
                    html.link('browse:%s' % r[0], 'View in browser'),
                    char=html.span('|', css_class='wide')
                )
            ]

            content_html = html.build(content)
            view.show_popup(
                content=content_html,
                location=point,
                max_width=800,
                max_height=600,
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
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "unfold", "point": point})
        else:
            sublime.active_window().run_command(mw.cmd('page'), {
                'action': mw.cmd('show_page'),
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
                html.h(4, '%s "%s"' % (template_type, template_name)),
                html.join(
                    html.link(template_link, 'Open'),
                    html.link('fold:%s' % point, 'Fold'),
                    html.link('unfold:%s' % point, 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate,
                max_width=800
            )
            return True
    return False


def on_hover_heading(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "unfold", "point": point})

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
                html.h(4, 'Heading "%s"' % h_name),
                html.join(
                    html.link('fold:%s' % point, 'Fold'),
                    html.link('unfold:%s' % point, 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate,
                max_width=800
            )
            return True
    return False


def on_hover_tag(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "unfold", "point": point})

    fold_tags = mw.get_setting("fold_tags", ["source", "syntaxhighlight", "div", "pre"])
    tag_regions = []

    for tag in fold_tags:
        regs = view.get_regions(tag)
        for r in regs:
            tag_regions.append((tag, r))

    for r in tag_regions:
        if r[1].contains(point):

            content = [
                html.h(4, r[0].title()),
                html.join(
                    html.link('fold:%s' % point, 'Fold'),
                    html.link('unfold:%s' % point, 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

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
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command(mw.cmd('colapse'), {"type": "unfold", "point": point})

    def get_text_pretty(r):
        text = view.substr(r).strip().lstrip('<!--').rstrip('-->')
        text = text.replace('TODO', html.strong('TODO', css_class='success'))
        text = text.replace('NOTE', html.strong('NOTE', css_class='note'))
        text = text.replace('WARNING', html.strong('WARNING', css_class='error'))
        text = text.replace('\n', html.br())
        return text

    comment_regions = view.get_regions('comment')

    if not comment_regions:
        return False

    for r in comment_regions:
        if r.contains(point):

            comment_text = get_text_pretty(r)

            content = [
                html.h(4, 'Commented text'),
                html.div(comment_text, css_class='undefined'),
                html.br(cnt=2),
                html.join(
                    html.link('fold:%s' % point, 'Fold'),
                    html.link('unfold:%s' % point, 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate,
                max_width=800,
                max_height=600
            )
            return True
    return False

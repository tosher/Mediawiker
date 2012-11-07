# Sublime Text 2 plugin: Mediawiker

Mediawiker is a plugin for Sublime Text 2 editor that adds possibility to create and edit pages on [Mediawiki](http://mediawiki.org) based sites.

Warning! It was tested on the latest windows release build of Sublime Text 2 and some Mediawiki sites. No guarantees here!

##Features
* Connection to existing mediawiki based site through the use of [mwclient library](http://sourceforge.net/apps/mediawiki/mwclient/index.php?title=Main_Page) .
* New pages creation / existing pages edition and publishing to wiki.
* Possibility to open pages from history-list of published pages.
* TOC (table of contents) menu of the page edited to move by page headers.
* Syntax highlighting from [Textmate Mediawiki bundle](https://github.com/textmate/mediawiki.tmbundle) (included).

## Install

### Package Control (not available now!)

The easiest way to install this is with [Package Control](http://wbond.net/sublime\_packages/package\_control).

 * If you just went and installed Package Control, you probably need to restart Sublime Text 2 before doing this next bit.
 * Bring up the Command Palette (Command+Shift+p on OS X, Control+Shift+p on Linux/Windows).
 * Select "Package Control: Install Package" (it'll take a few seconds)
 * Select Mediawiker when the list appears.

Package Control will automatically keep Mediawiker up to date with the latest version.

### Other methods
First find your Sublime Text 2 Packages folder:

    - OS X: ~/Library/Application Support/Sublime Text 2/Packages/
    - Windows: %APPDATA%/Sublime Text 2/Packages/
    - Linux: ~/.Sublime Text 2/Packages/

If you have Git, you can clone this repo to "/packages-folder/Mediawiker/"

or,

Download this repo using the "ZIP" button above, unzip and place the files in "/packages-folder/Mediawiker/"


## Documentation

- Use Packages/Mediawiker/Mediawiker.sublime-settings for setup wiki-connect and plugin options.
- Some connection specific rules:
 - If user-name is empty, then authorization will not be used.
 - If user-name is not empty, but user-password is empty, you will be prompted for password on action.
- Use **Get Page** option for retrieving existing wiki-page. If the page does not exists, you can create the new one.
 - *Alt+F4*
 - *Context menu:Mediawiker:Get page*
 - *Main menu:File:Mediawiker:Get page*
- Use **Publish Page** option for publishing pages. When you publish a page, the name of the page will be saved to history.
 - *Alt+F7*
 - *Context menu:Mediawiker:Publish page*
 - *Main menu:File:Mediawiker:Publish page*
- Use **Select page from history** option to open the page by name from history.
 - *Alt+F1*
 - *Context menu:Mediawiker:Get by from history*
- Use **Show TOC** option for show table of contents of the current page and to move by page headers.
 - *Alt+F2*
 - *Context menu:Mediawiker:Show TOC*
- Use **Change active site** to set your current wiki site.
 - *Alt+F3*
 - *Context menu:Mediawiker:Change active site*
- Use **Open page in browser** to open current page in web-browser.
 - *Alt+F5*
 - *Context menu:Mediawiker:Open page in browser*
- Check status messages while using the plugin.
- All settings available under the Main menu:Preferences:Package Settings:Mediawiker.

### Predefined mediawiki sites settings
Note: You must setup your credentials for authorization in the settings.

* English wikipedia: [en.wikipedia.org](http://en.wikipedia.org)
* Russian wikipedia: [ru.wikipedia.org](http://ru.wikipedia.org)
* Mediawiki [www.mediawiki.org](http://www.mediawiki.org)

You can add your favorite sites in the settings.

## License:
Copyright (c) 2012 Anton S. Gnidenko (aka tosher)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

## External licenses
This project uses code from other open source projects which may include licenses of their own.

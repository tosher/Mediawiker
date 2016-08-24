# Sublime Text plugin: Mediawiker

[Mediawiker](https://github.com/tosher/Mediawiker) is a plugin for Sublime Text editor (ver. 2/3) that adds possibility to use it as Wiki Editor on [Mediawiki](http://mediawiki.org) based sites like [Wikipedia](http://en.wikipedia.org) and [many other](http://www.mediawiki.org/wiki/Sites_using_MediaWiki/en).

## Main features
* [MWClient](https://github.com/mwclient/mwclient) library based.
* Syntax highlighting - improved version of the [Textmate Mediawiki bundle](https://github.com/textmate/mediawiki.tmbundle).
* Editor - create new pages, edit existing and post it to wiki.
* Completions - auto completions for internal wiki links
* History - list of edited pages
* Bookmarks - bookmark your favorite pages
* TOC - table of contents for opened page - available through command **Show TOC** or **Symbol list** (<kbd>Ctrl</kbd>+<kbd>R</kbd>)
* Insert templates, images into pages
* Upload files to wiki
* Search - search by wiki
* Table editor - edit simple wiki-tables with plugin [TableEdit](https://github.com/vkocubinsky/SublimeTableEditor), convert csv-format tables to wiki-tables.
* Snippets - basic wiki marking tags - bold, italic, headings, etc.
* Edit panel - all commands and snippets available through one panel. 
* Shortcuts - possibility to create plugin specific shortcuts to all commands and snippets to create word-like editor.
* Connectivity - http/https, direct/proxy connection with basic/digest web-server authorization.
* Connection manager - add new wiki sites, and switch between them.
* Page preview - possibility to preview page before posting with some preview customization options.
* Text folding - folding/unfolding page blocks by headers, tags, templates, html comments.
* Notifications - show [notifications](https://www.mediawiki.org/wiki/Notifications) as menu.
* Context opening - possibility to open included page, template, function by inline context.

![Subime Text Wiki editor plugin - Mediawiker](https://github.com/tosher/Mediawiker/wiki/Mediawiker_Dark.png)
*Screenshot using the Mediawiker_Dark color scheme*

## Install

### Package Control

    Package Control 3.0 now required for work on Linux.

The easiest way to install this is with [Package Control](http://wbond.net/sublime\_packages/package\_control).

 * If you just went and installed Package Control, you probably need to restart Sublime Text 2 before doing this next bit.
 * Bring up the Command Palette (<kbd>Command</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> on OS X, <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> on Linux/Windows).
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
* **Note**: Not all color schemes fully supports syntax highlighting scopes required by markup languages like Mediawiki or Markdown. On this moment, color schemes with better support are: **Twilight**, **Sunburst**, **Eiffel**. Also, Mediawiker package includes **Twilight (Mediawiki)**, **Eiffel (Mediawiki)** and **Mediawiker_Dark**/**Mediawiker_Light** schemes with improved highlighting for mediawiki syntax. 
* Check [plugin wiki](https://github.com/tosher/Mediawiker/wiki) for setup instructions.
* Use Preferences / Package settings / Mediawiker / "Settings  - Default" and "Settings - User" for setup wiki connection and plugin options.
* Some connection specific rules:
 * If user-name is empty, then authorization will not be used.
 * If user-name is not empty, but user-password is empty, you will be prompted for password on action.
* All settings are available under the Main menu / Preferences / Package Settings / Mediawiker.

### Commands
* **Edit panel** with all commands and snippets in ordered list (can be customized in the settings).
 * *Main menu / Tools / Mediawiker / Edit panel* (windows, osx: <kbd>Alt</kbd>+<kbd>F1</kbd>, linux: <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>F1</kbd>)
* **Open page** command for retrieving existing wiki-page. If the page does not exists, you can create the new one.
 * *Main menu / Tools / Mediawiker / Open page*
* Use page name or page url as a wiki page name. When the url will be inserted, it will be *cleared* to page name, if wiki parameters is correct and current wiki site was selected.
* **Reopen page** command - to reopen current page (<kbd>F5</kbd>).
* **Post page** command for publishing pages. When you post a page, the name of the page will be saved to pages history.
 * *Main menu / Tools / Mediawiker / Post page*
 * Settings option **mediawiker_mark_as_minor** (default: false) - using to mark changes as minor. Or you can use **!** character as **summary prefix** to invert this option on current post.
* **Pages history** command to open the page by name from history.
* **Show TOC** command for show table of contents of the current page and to move by page headers. Or you can use standard Symbol list (<kbd>Ctrl</kbd>+<kbd>R</kbd>).
* **Show internal links** command for show all internal links of the current page. You can go to selected link on page, open it in editor or in browser.
* **Show external links** command for show all external links of the current page (links like [link..]). You can go to selected links on page or open it in browser.
* **Select wiki** command to select your current wiki site.
* **Add/Edit wiki site** command for create new or edit existed wiki sites configurations.
* **Open page in browser** command to open current page in web-browser.
* **Set category** command to add category to current article from list of root category members (check "mediawiker_category_root" option in configuration).
* **Insert image** command to insert link to image from wiki. Parameter **mediawiker_image_prefix_min_length** is using to limit length of search prefix for large wikies (by default: 4 characters).
* **Insert template** command to insert template from wiki.
* **Search** command to search articles by text string. Results are shown as markdown formatted text in a new tab. Parameter **mediawiker_search_results_count** is using to limit search results count.
* **Category tree** command to show sub-categories and pages of the predefined category as menu.
* **Numbered TOC** command to set headers as numbered list (format 1.1.1.).
* **File upload** for uploading files to wiki
* **CSV data to wiki table** command to transform selected csv-text to wiki table (default delimiter since version 2.0: |).
* **(Buggy) Wiki table to Simple** command to transform the selected table (or under cursor) to *Simple table* (for using with plugin [TableEdit](https://github.com/vkocubinsky/SublimeTableEditor)).
* **(Buggy) Simple table to wiki** command to convert *Simple table* back to wiki syntax.
* Native Sublime text **Command palette** with predefined filter of plugin's commands and snippets.
  * *<kbd>Alt</kbd>+<kbd>F11</kbd>*

### Predefined mediawiki sites settings
Note: You must setup your credentials for authorization in the settings.

* English wikipedia: [en.wikipedia.org](http://en.wikipedia.org)
* Russian wikipedia: [ru.wikipedia.org](http://ru.wikipedia.org)
* Mediawiki [www.mediawiki.org](http://www.mediawiki.org)

You can add your favorite sites in the settings.

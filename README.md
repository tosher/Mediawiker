# Sublime Text plugin: Mediawiker

[Mediawiker](https://github.com/tosher/Mediawiker) is a plugin for Sublime Text editor (ver. 2/3) that adds possibility to use it as Wiki Editor on [Mediawiki](http://mediawiki.org) based sites like [Wikipedia]((http://en.wikipedia.org)) and [many other](http://www.mediawiki.org/wiki/Sites_using_MediaWiki/en).

## Main features
* Working with mediawiki based sites through the use of [mwclient library](http://sourceforge.net/apps/mediawiki/mwclient/index.php?title=Main_Page). Mwclient was modified for work under **Sublime text 3**.
* New pages creation / existing pages edition and posting to wiki.
* Possibility to open pages from history-list of posted pages or from category tree menu.
* TOC (table of contents) menu of the page edited to move by page headers.
* Syntax highlighting from [Textmate Mediawiki bundle](https://github.com/textmate/mediawiki.tmbundle) (included).
* Possibility to create / edit simple wiki tables with plugin [TableEdit](https://github.com/vkocubinsky/SublimeTableEditor).
* Wiki search
* Snippets for main wiki tags.
* Support of https and proxy connection.
* Support of http/https basic/digest authorization.

![Subime Text Wiki editor plugin - Mediawiker](https://github.com/tosher/Mediawiker/wiki/sublime_wiki_editor.png)
*Screenshot using the Twilight theme*

## Install

### Package Control

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
* **Note**: Not all color schemes fully supports syntax highlighting scopes required by markup languages like Mediawiki or Markdown. On this moment, color schemes with better support are: **Twilight**, **Sunburst**, **Eiffel**. Also, Mediawiker package includes **Twilight (Mediawiki)**, **Eiffel (Mediawiki)** and **Mediawiker_Dark** schemes with improved highlighting for mediawiki syntax. 
* Check [plugin wiki](https://github.com/tosher/Mediawiker/wiki) for setup instructions.
* Use Preferences / Package settings / Mediawiker / "Settings  - Default" and "Settings - User" for setup wiki connection and plugin options.
* Some connection specific rules:
 * If user-name is empty, then authorization will not be used.
 * If user-name is not empty, but user-password is empty, you will be prompted for password on action.
* All settings are available under the Main menu / Preferences / Package Settings / Mediawiker.

### Commands
* **Edit panel** with all commands and snippets in ordered list (can be customized in the settings).
 * *Alt-F1*
 * *Main menu / Tools / Mediawiker / Edit panel*
* **Open page** command for retrieving existing wiki-page. If the page does not exists, you can create the new one.
 * *Alt+F3*
 * *Main menu / Tools / Mediawiker / Open page*
 * Use page name or page url as a wiki page name. When the url will be inserted, it will be *cleared* to page name, if wiki parameters is correct and current wiki site was selected.
* **Reopen page** command - to reopen current page.
* **Post page** command for publishing pages. When you post a page, the name of the page will be saved to pages history.
 * *Alt+F7*
 * *Main menu / Tools / Mediawiker / Post page*
 * Settings option **mediawiker_mark_as_minor** (default: false) - using to mark changes as minor. Or you can use **!** character as **summary prefix** to invert this option on current post.
* **Pages history** command to open the page by name from history.
 * *Alt+F10*
* **Show TOC** command for show table of contents of the current page and to move by page headers.
* **Show internal links** command for show all internal links of the current page. You can go to selected link on page, open it in editor or in browser.
* **Show external links** command for show all external links of the current page (links like [link..]). You can go to selected links on page or open it in browser.
 * *Alt+F2*
* **Select wiki** command to select your current wiki site.
 * *Alt+F6*
* **Open page in browser** command to open current page in web-browser.
 * *Alt+F5*
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
  * *Alt+F11*

### Predefined mediawiki sites settings
Note: You must setup your credentials for authorization in the settings.

* English wikipedia: [en.wikipedia.org](http://en.wikipedia.org)
* Russian wikipedia: [ru.wikipedia.org](http://ru.wikipedia.org)
* Mediawiki [www.mediawiki.org](http://www.mediawiki.org)

You can add your favorite sites in the settings.

# Sublime Text plugin: Mediawiker

[Mediawiker](https://github.com/tosher/Mediawiker) is a plugin for Sublime Text editor (ver. 2/3) that adds possibility to use it as Wiki Editor on [Mediawiki](http://mediawiki.org) based sites like [Wikipedia]((http://en.wikipedia.org)) and [many other](http://www.mediawiki.org/wiki/Sites_using_MediaWiki/en).

## Main features
* Connection to existing mediawiki based site through the use of [mwclient library](http://sourceforge.net/apps/mediawiki/mwclient/index.php?title=Main_Page) .
* New pages creation / existing pages edition and posting to wiki.
* Possibility to open pages from history-list of posted pages.
* TOC (table of contents) menu of the page edited to move by page headers.
* Syntax highlighting from [Textmate Mediawiki bundle](https://github.com/textmate/mediawiki.tmbundle) (included).
* Possibility to create / edit simple wiki tables with plugin [TableEdit](https://github.com/vkocubinsky/SublimeTableEditor).
* Snippets for main wiki tags.

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

## Changes in version 2.0
* Support for Sublime Text 3.
* **Edit panel** is used instead of sub-Context menu for easy using with keyboard. Also **Edit panel** can be called with **Alt-F1** shortcut.
* Some shortcuts was changed or removed:
 * Alt-F10 instead of Alt-F1 for **Pages history** command (select from history of posted pages).
 * Shortcut for **Set category** command was removed
* Some of the commands was changed in this version for easy using in configuration. Please, recreate your key bindings configuration if you changed the original values.
* Possibility to connect to wiki sites with *https* protocol was added as experimental option. Add *"https": true* parameter to site options for using it. (Not tested.)

## Documentation
* Check [plugin wiki](https://github.com/tosher/Mediawiker/wiki) for setup instructions.
* Use Preferences / Package settings / Mediawiker / "Settings  - Default" and "Settings - User" for setup wiki connection and plugin options.
* Some connection specific rules:
 * If user-name is empty, then authorization will not be used.
 * If user-name is not empty, but user-password is empty, you will be prompted for password on action.
* Check status messages while using the plugin.
* All settings available under the Main menu / Preferences / Package Settings / Mediawiker.

### Commands
* **Edit panel** with all command and snippets in ordered list (can be customized in the settings).
 * *Alt-F1*
 * *Context menu / Mediawiker: Edit panel*
* **Open page** command for retrieving existing wiki-page. If the page does not exists, you can create the new one.
 * *Alt+F3*
 * *Main menu / File / Mediawiker / Open page*
 * Use page name or page url as a wiki page name. When the url will be inserted, it will be *cleared* to page name, if wiki parameters is correct and current wiki site was selected.
* **Reopen page** command - to reopen current page.
* **Post page** command for publishing pages. When you post a page, the name of the page will be saved to pages history.
 * *Alt+F7*
 * *Main menu / File / Mediawiker / Post page*
 * Settings option **mediawiker_mark_as_minor** (default: false) - using to mark changes as minor. Or you can use **!** character as **summary prefix** to invert this option on current post.
* **Pages history** command to open the page by name from history.
 * *Alt+F10*
* **Show TOC** command for show table of contents of the current page and to move by page headers.
 * *Alt+F2*
* **Select wiki** command to select your current wiki site.
 * *Alt+F6*
* **Open page in browser** command to open current page in web-browser.
 * *Alt+F5*
* **Set category** command to add category to current article from list of root category members (check "mediawiker_category_root" option in configuration).
* **Numbered TOC** command to set headers as numbered list (format 1.1.1.).
* **CSV data to wiki table** command to transform selected csv-text to wiki table (default delimiter since version 2.0: |).
 * **Note!** Settings **mediawiker_wikitable_properties** and **mediawiker_wikitable_cell_properties** is using now for all table specific commands. Old settings **mediawiker_csvtable_properties** and **mediawiker_csvtable_cell_properties** was removed in version 2.0.
* **Wiki table to Simple** command to transform the selected table (or under cursor) to *Simple table* (for using with plugin [TableEdit](https://github.com/vkocubinsky/SublimeTableEditor)).
 * **Warning!** All table styles from original text will be replaced.
* **Simple table to wiki** command to convert *Simple table* back to wiki syntax.
* Native Sublime text **Command palette** with predefined filter of plugin's commands and snippets.
  * *Alt+F11*

### Predefined mediawiki sites settings
Note: You must setup your credentials for authorization in the settings.

* English wikipedia: [en.wikipedia.org](http://en.wikipedia.org)
* Russian wikipedia: [ru.wikipedia.org](http://ru.wikipedia.org)
* Mediawiki [www.mediawiki.org](http://www.mediawiki.org)

You can add your favorite sites in the settings.

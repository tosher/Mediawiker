// ==UserScript==
// @name         Mediawiker Edit Button
// @namespace    http://github.com/Plloi
// @version      0.0.5
// @description  Adds a button to edit Media Wiki pages using Mediawiker for SublimeText
// @author       Shaun Hammill <plloi.pllex@gmail.com>
// @match        https://en.wikipedia.org/wiki/*
// @match        https://ru.wikipedia.org/wiki/*
// @match        https://www.mediawiki.org/wiki/*
// @grant        none
// ==/UserScript==
(function(){
    var editItem = document.getElementById("ca-edit"),
        editText = document.querySelector(".plainlinks a[href$=edit]"),
        pageName = mw.config.get("wgPageName");

    if (editItem && pageName)
    {
        editItem.insertAdjacentHTML('afterend','<li><span><a href="mediawiker://'+pageName+'">'+editItem.innerText+' in Mediawiker</a></span></li>');
    }
})();

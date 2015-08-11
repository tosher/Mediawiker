// ==UserScript==
// @name         Mediawiker Edit Button
// @namespace    http://github.com/Plloi
// @version      0.0.7
// @description  Adds a button to edit Media Wiki pages using Mediawiker for SublimeText
// @author       Shaun Hammill <plloi.pllex@gmail.com>
// @updateURL    https://raw.githubusercontent.com/tosher/Mediawiker/master/handler/userscript/MediawikerEditButton.meta.js
// @downloadURL  https://raw.githubusercontent.com/tosher/Mediawiker/master/handler/userscript/MediawikerEditButton.user.js
// @match        https://en.wikipedia.org/wiki/*
// @match        https://ru.wikipedia.org/wiki/*
// @match        https://www.mediawiki.org/wiki/*
// @grant        none
// ==/UserScript==

(function(){
    function addMediawiker(){
        if(typeof mw === "undefined"){
            setTimeout(function(){
                addMediawiker();
            },250);
            return;
        }

        var editItem = document.getElementById("ca-edit"),
            editText = document.querySelector(".plainlinks a[href$=edit]"),
            pageName = mw.config.get("wgPageName");

        if (editItem && pageName)
        {
            editItem.insertAdjacentHTML('afterend','<li><span><a href="mediawiker://'+pageName+'">'+editItem.innerText+' in Mediawiker</a></span></li>');
        }
    }

    addMediawiker()
})();

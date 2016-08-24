#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

from .mw_add_category import MediawikerAddCategoryCommand, MediawikerSetCategoryCommand
from .mw_add_image import MediawikerAddImageCommand, MediawikerInsertImageCommand
from .mw_add_template import MediawikerAddTemplateCommand, MediawikerInsertTemplateCommand
from .mw_category_list import MediawikerCategoryListCommand, MediawikerCategoryTreeCommand
from .mw_cli import MediawikerCliCommand
from .mw_colapse import MediawikerColapseCommand
from .mw_edit_panel import MediawikerEditPanelCommand
from .mw_enumerate_toc import MediawikerEnumerateTocCommand
from .mw_favorites import MediawikerFavoritesAddCommand, MediawikerFavoritesOpenCommand
from .mw_get_notifications import MediawikerNotificationsCommand, MediawikerGetNotificationsCommand
from .mw_open_issue import MediawikerOpenIssueCommand
from .mw_open_page_in_browser import MediawikerOpenPageInBrowserCommand
from .mw_page_actions import MediawikerPageCommand
from .mw_page_backlinks import MediawikerShowPageBacklinksCommand, MediawikerPageBacklinksCommand
from .mw_page_langlinks import MediawikerShowPageLanglinksCommand, MediawikerPageLanglinksCommand
from .mw_page_list import MediawikerPageListCommand
from .mw_preview_page import MediawikerPreviewPageCommand, MediawikerPreviewCommand
from .mw_search_string import MediawikerSearchStringCommand, MediawikerSearchStringListCommand
from .mw_set_active_site import MediawikerSetActiveSiteCommand
from .mw_show_external_links import MediawikerShowExternalLinksCommand
from .mw_show_internal_links import MediawikerShowInternalLinksCommand
from .mw_show_toc import MediawikerShowTocCommand
from .mw_table import MediawikerCsvTableCommand, MediawikerTableSimpleToWikiCommand, MediawikerTableWikiToSimpleCommand
from .mw_text_commands import MediawikerInsertTextCommand, MediawikerReplaceTextCommand
from .mw_upload import MediawikerUploadCommand, MediawikerFileUploadCommand
from .mw_setup import MediawikerProcessSiteCommand

__all__ = [
    'MediawikerAddCategoryCommand',
    'MediawikerSetCategoryCommand',
    'MediawikerAddImageCommand',
    'MediawikerInsertImageCommand',
    'MediawikerAddTemplateCommand',
    'MediawikerInsertTemplateCommand',
    'MediawikerCategoryListCommand',
    'MediawikerCategoryTreeCommand',
    'MediawikerCliCommand',
    'MediawikerColapseCommand',
    'MediawikerEditPanelCommand',
    'MediawikerEnumerateTocCommand',
    'MediawikerFavoritesAddCommand',
    'MediawikerFavoritesOpenCommand',
    'MediawikerNotificationsCommand',
    'MediawikerGetNotificationsCommand',
    'MediawikerOpenIssueCommand',
    'MediawikerOpenPageInBrowserCommand',
    'MediawikerPageCommand',
    'MediawikerShowPageBacklinksCommand',
    'MediawikerPageBacklinksCommand',
    'MediawikerShowPageLanglinksCommand',
    'MediawikerPageLanglinksCommand',
    'MediawikerPageListCommand',
    'MediawikerPreviewPageCommand',
    'MediawikerPreviewCommand',
    'MediawikerSearchStringCommand',
    'MediawikerSearchStringListCommand',
    'MediawikerSetActiveSiteCommand',
    'MediawikerShowExternalLinksCommand',
    'MediawikerShowInternalLinksCommand',
    'MediawikerShowTocCommand',
    'MediawikerCsvTableCommand',
    'MediawikerTableSimpleToWikiCommand',
    'MediawikerTableWikiToSimpleCommand',
    'MediawikerInsertTextCommand',
    'MediawikerReplaceTextCommand',
    'MediawikerUploadCommand',
    'MediawikerFileUploadCommand',
    'MediawikerProcessSiteCommand'
]

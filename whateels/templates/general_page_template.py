"""
Custom Page Component for WhatEELS Application

This module provides a customized Panel FastListTemplate with navigation header
and CSS styling for the WhatEELS scientific web application.
"""

import weakref as _weakref
import panel as pn
from typing import Optional, List, Union
from whateels.state import CacheManager
from whateels.helpers.safe_converter import SafeConverter
from whateels.helpers.constants import ASSETS_ROOT

class GeneralPageTemplate(pn.template.FastListTemplate):
    """
    Custom page template extending Panel's FastListTemplate.
    
    Provides consistent navigation header and styling across the WhatEELS application.
    Automatically handles CSS loading and provides default navigation if no header is specified.
    """
    
    _DEFAULT_TITLE = "General Page Template"
    _DEFAULT_HEADER_BACKGROUND = "#4d4dc9"
    _DEFAULT_HEADER_BACKGROUND_HOVER = "#3b3bb8"

    def __init__(
        self, 
        title: str = _DEFAULT_TITLE, 
        main: Optional[Union[List, pn.viewable.Viewable]] = None, 
        sidebar: Optional[Union[List, pn.viewable.Viewable]] = None, 
        header: Optional[List[pn.viewable.Viewable]] = None, 
        right_sidebar: Optional[Union[List, pn.viewable.Viewable]] = None,
        header_background: str = _DEFAULT_HEADER_BACKGROUND,
        **kwargs,
    ):
        """
        Initialize GeneralPageTemplate with enhanced FastListTemplate.
        
        Args:
            title: Page title to display in the template
            main: Main content area components (list or single component)
            sidebar: Left sidebar components (optional)
            header: Header navigation components (optional, defaults to standard nav, pass [] for no header)
            right_sidebar: Right sidebar components (optional)
            modal: Modal area components (optional)
            header_background: Background color for the header (default: green)
            sidebar_width: Width of the left sidebar in pixels (default: 275)
        """        
        app_state = CacheManager.get_cached_app_state()

        # Set up reactive watchers to update header on metadata or tab index changes.
        # Store the watchers so we can unwatch on session destruction — otherwise
        # every page visit permanently adds callbacks to the app_state singleton,
        # each holding a strong ref to this template instance via the bound method.
        #
        # IMPORTANT: `_update_navigation_header` must always run in THIS session's
        # document context, not the caller's. When any page sets a shared app_state
        # param (e.g. selected_tab_index_dataset), ALL session watchers fire —
        # potentially with another session's curdoc active. That causes Panel to
        # attach ImportedStyleSheet Bokeh models to the wrong document, triggering:
        #   "Models must be owned by only a single document"
        # Fix: capture this session's document and schedule via add_next_tick_callback
        # so the update always executes inside the correct Bokeh document lock.
        _own_doc = pn.state.curdoc

        def _doc_safe_update_header(event):
            if _own_doc is not None:
                try:
                    _own_doc.add_next_tick_callback(
                        lambda: self._update_navigation_header(event)
                    )
                except Exception:
                    pass  # session may have ended between the watch firing and the callback
            else:
                self._update_navigation_header(event)

        self._metadata_watcher = app_state.param.watch(_doc_safe_update_header, 'metadata')
        self._tab_index_watcher = app_state.param.watch(_doc_safe_update_header, 'selected_tab_index_dataset', onlychanged=False)

        # Unwatch when this session ends so the template can be garbage collected
        _self_ref = _weakref.ref(self)
        def _unwatch_on_destroy(_):
            _t = _self_ref()
            if _t is not None:
                try:
                    app_state.param.unwatch(_t._metadata_watcher)
                except Exception:
                    pass
                try:
                    app_state.param.unwatch(_t._tab_index_watcher)
                except Exception:
                    pass
        pn.state.on_session_destroyed(_unwatch_on_destroy)

        # Create a reactive header container
        self._header_container = pn.Row(
            *self._create_navigation_header(
                self._is_metadata_loaded(app_state.metadata),
                self._get_selected_tab_index(app_state.selected_tab_index_dataset),
            )
        )
        # Set default header if none provided (but not if empty list is explicitly passed)
        if header is None:
            header = [self._header_container]

        # Set default main content if none provided
        if main is None:
            main = [pn.pane.Markdown("# Welcome to WhatEELS")]

        # Build initialization parameters dynamically
        init_params = {
            'logo': str(ASSETS_ROOT / 'img' / 'we_whole_name_mixed_v0.svg'),
            'favicon': str(ASSETS_ROOT / 'img' / 'we_white_logo.ico'),
            'title': title,
            'main': main,
            'header': header,
            'theme_toggle': False,  # Disable theme toggle for consistency
            'theme': 'default',  # Default theme
            'header_background': header_background,
        }
        
        # Only add sidebar parameters if they have content
        if sidebar is not None:
            init_params['sidebar'] = sidebar
        
        if right_sidebar is not None:
            init_params['right_sidebar'] = right_sidebar
        
        # Initialize parent template with dynamic parameters
        super().__init__(**init_params, **kwargs)

    def _create_navigation_header(
        self, 
        is_metadata_loaded: bool, 
        selected_tab_index: int, 
    ) -> list:
        """
        Create the default navigation header with links to main application sections.
        
        Returns:
            List of Markdown panes configured as navigation links
        """
        
        LINK_DISABLE_CLASS = "disable-link"
        LINK_ENABLE_ANIMATION_CLASS = "enable-link-animation"
                
        navigation_links = [
            ("[Home](/)", "Home page with file upload"),
        ]
        
        is_eels_tab = self._is_selected_tab_eels(selected_tab_index)

        clustering_href = f'/clustering?tab={str(selected_tab_index)}' if is_eels_tab else '/#'
        clustering_class = LINK_ENABLE_ANIMATION_CLASS if is_eels_tab else LINK_DISABLE_CLASS
        clustering_a_element = f'<a href="{clustering_href}" class="{clustering_class}">Clustering</a>'
        
        navigation_links.append((clustering_a_element,"Clustering"))
        
        clustering_2_href = f'/clustering-2?tab={str(selected_tab_index)}' if is_eels_tab else '/clustering-2'
        # clustering_2_class = LINK_ENABLE_ANIMATION_CLASS if is_eels_tab else LINK_DISABLE_CLASS
        clustering_2_a_element = f'<a href="{clustering_2_href}" class="{LINK_ENABLE_ANIMATION_CLASS}">Clustering 2</a>'
        
        navigation_links.append((clustering_2_a_element,"Clustering 2"))
        
        quantification_href = f'/quantification?tab={str(selected_tab_index)}' if is_eels_tab else '/#'
        quantification_class = LINK_ENABLE_ANIMATION_CLASS if is_eels_tab else LINK_DISABLE_CLASS
        quantification_a_element = f'<a href="{quantification_href}" class="{quantification_class}">Quantification</a>'

        navigation_links.append((quantification_a_element, "Quantification"))

        fitting_href = f'/fitting?tab={str(selected_tab_index)}' if is_eels_tab else '/#'
        fitting_class = LINK_ENABLE_ANIMATION_CLASS if is_eels_tab else LINK_DISABLE_CLASS
        fitting_a_element = f'<a href="{fitting_href}" class="{fitting_class}">Fitting</a>'

        navigation_links.append((fitting_a_element, "Fitting"))

        top_menu = [
            pn.pane.Markdown(
                link_text, 
                css_classes=["custom-nav-link"],
                name=description,  # For accessibility
            )
            for link_text, description in navigation_links
        ]
        
        return top_menu
        
    def _update_navigation_header(self, _):        
        app_state = CacheManager.get_cached_app_state()

        selected_tab_index = self._get_selected_tab_index(app_state.selected_tab_index_dataset)

        """ Update the navigation header based on shared state changes."""
        self._header_container.objects = self._create_navigation_header(
            self._is_metadata_loaded(app_state.metadata),
            selected_tab_index,
        )
        
    def _is_metadata_loaded(self, metadata) -> bool:
        """Check if metadata is a valid dict and does not contain 'error'."""
        return isinstance(metadata, dict) and 'error' not in metadata
    
    def _get_selected_tab_index(self, selected_tab_index_dataset) -> int:
        """Get the selected tab index from shared state, safely converted to int."""
        return SafeConverter.to_int(selected_tab_index_dataset, default=-1)

    def _is_selected_tab_eels(self, selected_tab_index):
        """
        Returns True if the dataset at selected_tab_index in all_datasets is EELS, else False.
        Uses 'Eloss' in dataset.coords for EELS detection.
        """
        all_datasets = CacheManager.get_cached_app_state().all_datasets
        if not isinstance(all_datasets, list):
            return False
        if not all_datasets or selected_tab_index < 0 or selected_tab_index >= len(all_datasets):
            return False
        dataset = all_datasets[selected_tab_index]
        
        # EELS detection: 'Eloss' in coords OR ElectronCount data is 3D
        has_eloss = hasattr(dataset, 'coords') and 'Eloss' in getattr(dataset, 'coords', {})
        has_3d = hasattr(dataset, 'ElectronCount') and hasattr(dataset.ElectronCount, 'shape') and len(dataset.ElectronCount.shape) == 3
        return has_eloss or has_3d
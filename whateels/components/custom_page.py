"""
Custom Page Component for WhatEELS Application

This module provides a customized Panel FastListTemplate with navigation header
and CSS styling for the WhatEELS scientific web application.
"""

import panel as pn
from typing import Optional, List, Union
from whateels.shared_state import AppState

# pn.extension(raw_js={
#     """
#         const toggleSidebar = () => {
#             const sidebar = document.getElementById("sidebar");
#             sidebar.classList.toggle("hidden");
#             console.log("Sidebar toggled");
#         };
#     """
# })

class CustomPage(pn.template.FastListTemplate):
    """
    Custom page template extending Panel's FastListTemplate.
    
    Provides consistent navigation header and styling across the WhatEELS application.
    Automatically handles CSS loading and provides default navigation if no header is specified.
    """
    
    _DEFAULT_TITLE = "Custom Page"
    _DEFAULT_HEADER_BACKGROUND = "#4caf50"

    def __init__(
        self, 
        title: str = _DEFAULT_TITLE, 
        main: Optional[Union[List, pn.viewable.Viewable]] = None, 
        sidebar: Optional[Union[List, pn.viewable.Viewable]] = None, 
        header: Optional[List[pn.viewable.Viewable]] = None, 
        right_sidebar: Optional[Union[List, pn.viewable.Viewable]] = None,
        header_background: str = _DEFAULT_HEADER_BACKGROUND,
        sidebar_width: int = 275,
        **kwargs,
    ):
        """
        Initialize CustomPage with enhanced FastListTemplate.
        
        Args:
            title: Page title to display in the template
            main: Main content area components (list or single component)
            sidebar: Left sidebar components (optional)
            header: Header navigation components (optional, defaults to standard nav, pass [] for no header)
            right_sidebar: Right sidebar components (optional)
            header_background: Background color for the header (default: green)
            sidebar_width: Width of the left sidebar in pixels (default: 275)
        """
        app_state = AppState()
        app_state.param.watch(self.on_metadata_available_changed, 'metadata')
        is_metadata_loaded = True if isinstance(app_state.metadata, dict) and 'error' not in app_state.metadata else False
        
        # Create a reactive header container
        self._header_container = pn.Row(*self._create_navigation_header(is_metadata_loaded, right_sidebar))
        # Set default header if none provided (but not if empty list is explicitly passed)
        if header is None:
            header = [self._header_container]

        # Set default main content if none provided
        if main is None:
            main = [pn.pane.Markdown("# Welcome to WhatEELS")]

        # Build initialization parameters dynamically
        init_params = {
            'title': title,
            'main': main,
            'header': header,
            'theme_toggle': False,  # Disable theme toggle for consistency
            'theme': 'default',  # Default theme
            'header_background': header_background,
            'sidebar_width': sidebar_width,  # Set sidebar width
        }
        
        # Only add sidebar parameters if they have content
        if sidebar is not None:
            init_params['sidebar'] = sidebar
        
        if right_sidebar is not None:
            init_params['right_sidebar'] = right_sidebar
        
        # Initialize parent template with dynamic parameters
        super().__init__(**init_params, **kwargs)

    def _create_navigation_header(self, is_metadata_loaded: bool = False, right_sidebar: Optional[Union[List, pn.viewable.Viewable]] = None) -> list:
        """
        Create the default navigation header with links to main application sections.
        
        Returns:
            List of Markdown panes configured as navigation links
        """
        navigation_links = [
            ("[Home](/)", "Home page with file upload"),
        ]
        if is_metadata_loaded:
            navigation_links.append(('<a href="/clustering">Clustering</a>', "Clustering"))
            navigation_links.append(('<a href="/quantification">Quantification</a>', "Quantification"))
        else:
            navigation_links.append(('<a href="#" style="pointer-events: none; opacity: .5;">Clustering</a>', "Clustering"))
            navigation_links.append(('<a href="#" style="pointer-events: none; opacity: .5;">Quantification</a>', "Quantification"))

        top_menu = [
            pn.pane.Markdown(
                link_text, 
                css_classes=["custom-nav-link"],
                name=description,  # For accessibility
            )
            for link_text, description in navigation_links
        ]
        
        return top_menu
        
    def on_metadata_available_changed(self, _):
        app_state = AppState()
        is_metadata_loaded = True if isinstance(app_state.metadata, dict) and 'error' not in app_state.metadata else False
        
        # Rebuild navigation header visually
        self._header_container.objects = self._create_navigation_header(is_metadata_loaded)
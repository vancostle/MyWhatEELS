"""
Custom Page Component for WhatEELS Application

This module provides a customized Panel FastListTemplate with navigation header
and CSS styling for the WhatEELS scientific web application.
"""

import panel as pn
from typing import Optional, List, Union

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
        on_load_page: Optional[callable] = None
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
            sidebar_width: Width of the left sidebar in pixels (default: 330)
            collapsed_sidebar: Whether the sidebar starts in collapsed state
        """
        # Set default header if none provided (but not if empty list is explicitly passed)
        if header is None:
            header = self._create_navigation_header()
        
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
        super().__init__(**init_params)

    def _create_navigation_header(self) -> List[pn.pane.Markdown]:
        """
        Create the default navigation header with links to main application sections.
        
        Returns:
            List of Markdown panes configured as navigation links
        """
        navigation_links = [
            ("[Home](/)", "Home page with file upload"),
            ("[GOS](/gos)", "GOS graph page"),
            ("[NLLS](/nlls)", "Non-Linear Least Squares analysis"),
            ("[Login](/login)", "User authentication"),
        ]
        
        return [
            pn.pane.Markdown(
                link_text, 
                css_classes=["fast-list-header"],
                name=description  # For accessibility
            )
            for link_text, description in navigation_links
        ]
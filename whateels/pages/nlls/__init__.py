"""
NLLS Page

This module provides the NLLS (Non-Linear Least Squares) fitting page
for the WhatEELS application, implementing the MVC pattern.
"""

import panel as pn
from whateels.templates import GeneralPageTemplate
from whateels.pages.nlls.MVC.model import NLLSModel
from whateels.pages.nlls.MVC.view import NLLSView
from whateels.pages.nlls.MVC.controller import NLLSController


class NLLS(GeneralPageTemplate):
    """
    NLLS Page class for the WhatEELS application.
    
    This class extends CustomPage to create a specific NLLS page layout
    with Model-View-Controller architecture for managing NLLS fitting operations.
    """
    
    _DEFAULT_TITLE = "NLLS Fitting"
    
    def __init__(self, title: str = _DEFAULT_TITLE):
        # Initialize MVC components
        self._model = NLLSModel()
        self._view = NLLSView(self._model)
        self._controller = NLLSController(self._model, self._view)
        
        # Build the page layout
        super().__init__(
            title=title,
            main=self._view.main,
            sidebar=[self._view.build_sidebar()],
            right_sidebar=[
                pn.pane.Markdown("## NLLS Options"),
                pn.pane.Markdown(
                    """
                    ### About NLLS Fitting
                    
                    Non-Linear Least Squares (NLLS) fitting allows you to:
                    
                    - Select elements and subshells for analysis
                    - Create fitting models based on GOS calculations
                    - Fit reference spectra
                    - Perform multifit across entire datasets
                    
                    **Getting Started:**
                    1. Select an element from the dropdown
                    2. Choose subshells to include
                    3. Click "Add Element" to add to model
                    4. Repeat for all elements of interest
                    5. Click "Create Model" to initialize fitting
                    """,
                    styles={'background': '#f8f9fa', 'padding': '15px', 'border-radius': '5px'}
                )
            ],
        )
    
    @property
    def model(self):
        """Access to the NLLS model"""
        return self._model
    
    @property
    def view(self):
        """Access to the NLLS view"""
        return self._view
    
    @property
    def controller(self):
        """Access to the NLLS controller"""
        return self._controller
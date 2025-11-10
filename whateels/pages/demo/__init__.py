"""Demo page module."""

from .MVC import DemoModel, DemoView, DemoController
from whateels.components import CustomPage

class DemoPage(CustomPage):
    """Demo page class."""
    
    def __init__(self):
        """Initialize demo page."""
        self.model = DemoModel()
        self.view = DemoView(self.model)
        self.controller = DemoController(self.model, self.view)

        super().__init__(
            title="Demo", 
            main=self.view.main,
            right_sidebar=self.view.right_sidebar
        )
from ...view import QuantificationView

class RightSidebarManager:
    """Manager for the right sidebar in the Quantification view."""
    
    def __init__(self, view: "QuantificationView"):
        """Store the view reference used to manipulate right-sidebar components."""
        self._view = view


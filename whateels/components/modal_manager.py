from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..templates.general_page_template import GeneralPageTemplate

class ModalManager:
    def __init__(self, custom_page: "GeneralPageTemplate"):
        self._custom_page = custom_page
        self._modals = {} # Dictionary to hold modal references
        
    def register_modal(self, modal_id: str, modal_component):
        """Register a modal component with a specific ID."""
        modal_component.visible = False  # Ensure modal is initially hidden
        self._modals[modal_id] = modal_component
        
    def open_modal(self, modal_id: str):
        """Open a specific modal by ID, hiding all others."""
        for mid, modal in self._modals.items():
            modal.visible = (mid == modal_id)
        # Update the custom page's modal container
        modal_container = getattr(self._custom_page, 'modal', None)
        if modal_container is not None and hasattr(modal_container, 'objects'):
            modal_container.objects = list(self._modals.values())
            self._custom_page.open_modal() # Open the modal container
    
    def close_modal(self, modal_id: str):
        """Close a specific modal by ID."""
        if modal_id in self._modals:
            self._modals[modal_id].visible = False
        self._custom_page.close_modal() # Close the modal container
        
    @property
    def modals(self) -> list:
        """Return the dictionary of registered modals."""
        return list(self._modals.values())
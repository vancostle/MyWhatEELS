import panel as pn

from whateels.components import FileUploader

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import HomePageModel  

class HomePageLeftSidebar(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "HomePageModel"):
        self._model = model
        
        self._dataset_info = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._file_uploader: FileUploader = FileUploader() # Placeholder, will be set up below
        self._open_modal_btn: pn.widgets.Button
        
        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_WIDTH
        )

    @property
    def file_uploader(self) -> FileUploader:
        """FileUploader widget for file upload interactions."""
        return self._file_uploader
    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info = component
    @dataset_info.deleter
    def dataset_info(self):
        """Delete the dataset info component."""
        self._dataset_info = None
        
    @property
    def open_modal_btn(self) -> pn.widgets.Button:
        """Button widget to open the modal dialog."""
        return self._open_modal_btn

    def _create_layout(self) -> pn.Column:
        """Create the sidebar layout with file uploader and spacing."""
        self._file_uploader = self._create_file_uploader()
                
        # Create a button to open modal
        self._open_modal_btn = pn.widgets.Button(name="Open Modal", button_type="primary")

        self._sidebar_container_layout = pn.Column(
            self._file_uploader,
            self._open_modal_btn,
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        return self._sidebar_container_layout
        
    def add_component(self, component: pn.viewable.Viewable):
        """Add a component to the sidebar and track it as the last dataset info component."""
        self.append(component)
        self.dataset_info = component

    def remove_dataset_info(self):
        """Remove the last dataset info component from the sidebar, if present."""
        if self.dataset_info is None:
            return
        if self.dataset_info in self:
            self.remove(self.dataset_info)
            del self.dataset_info
            
    def _create_file_uploader(self) -> FileUploader:
        """Create the main file uploader widget."""
        forceed_success = False # Set to True for testing purposes
        initial_filename = None
        all_datasets = self._model.app_state.all_datasets
        if all_datasets is None:
            all_datasets = []
            
        if isinstance(all_datasets, list) and len(all_datasets) > 0:
            # If datasets are already loaded, we might want to show different sidebar content
            forceed_success = True
            filename_candidate = self._model.app_state.filename
            # Ensure initial_filename is only str or None
            if isinstance(filename_candidate, str) or filename_candidate is None:
                initial_filename = filename_candidate
            else:
                initial_filename = None
        
        # Set up the FileUploader with model constants
        return FileUploader(
            reject_message=self._model.constants.FILE_DROPPER_REJECT_MESSAGE,
            force_success=forceed_success,
            initial_filename=initial_filename
        )  
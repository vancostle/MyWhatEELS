from abc import ABC, abstractmethod

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from panel.viewable import Viewable
    from whateels.components import InfoPanel

class IPlot(ABC):
    """
    Interface for EELS plot visualizer components.

    This abstract base class defines the contract for any EELS plot visualizer:
    - Must provide a method to create the main visualization layout (`create_plots`).
    - Must provide a method to create a dataset information panel (`create_dataset_info`).

    Subclasses should implement these methods to return Panel layouts and dataset info components
    appropriate for their specific visualization type (e.g., single spectrum, spectrum image, clustering, etc).
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def create_plots(self) -> "Viewable":
        """
        Create and return the main Panel layout for this EELS visualizer.

        Returns:
            pn.viewable.Viewable: The main visualization layout (e.g., a Panel Column, Row, Tabs, etc).

        Subclasses must implement this method to define how their plots and UI components are arranged.
        """
        raise NotImplementedError("Subclasses should implement create_plots and return a layout object.")

    @abstractmethod
    def create_dataset_info(self) -> "InfoPanel":
        """
        Create and return an InfoPanel for this visualizer.

        Returns:
            InfoPanel: A Panel component displaying key metadata attributes for the dataset.

        Subclasses must implement this method to provide dataset info relevant to their visualization.
        """
        raise NotImplementedError("Subclasses should implement create_dataset_info and return an InfoPanel object.")
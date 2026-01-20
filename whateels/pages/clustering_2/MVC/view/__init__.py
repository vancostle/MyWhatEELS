from .layouts import Clustering2MainLayout, Clustering2LeftSidebarLayout, Clustering2RightSidebarLayout
from whateels.components import ModalManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate
    from ...MVC import Clustering2PageModel

class Clustering2PageView:
    
    def __init__(self, model: "Clustering2PageModel", custom_page: "GeneralPageTemplate") -> None:
        
        self._main = Clustering2MainLayout()
        # self._left_sidebar = Clustering2LeftSidebarLayout()
        self._right_sidebar = Clustering2RightSidebarLayout()
        
        self._modal_manager = ModalManager(custom_page)
        
    @property
    def main(self):
        return self._main
    
    # @property
    # def left_sidebar(self):
    #     return self._left_sidebar
    
    @property
    def right_sidebar(self):
        return self._right_sidebar
    
    @property
    def modals(self):
        return self._modal_manager.modals
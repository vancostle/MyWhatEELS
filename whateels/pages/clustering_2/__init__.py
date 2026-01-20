from .MVC import Clustering2PageView, Clustering2PageController, Clustering2PageModel
from whateels.templates import GeneralPageTemplate

class Clustering2Page(GeneralPageTemplate):
    
    def __init__(self) -> None:
        model = Clustering2PageModel()
        view = Clustering2PageView(model, custom_page=self)
        Clustering2PageController(model, view)
        
        super().__init__(
            title="Clustering 2 Page",
            main=[view.main],
            right_sidebar=[view.right_sidebar],
            modal=view.modals,
            sidebar_width=200
        )
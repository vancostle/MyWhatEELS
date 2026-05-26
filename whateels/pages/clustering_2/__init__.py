from .MVC import Clustering2PageView, Clustering2PageController, Clustering2PageModel
from whateels.templates import GeneralPageTemplate

class Clustering2Page(GeneralPageTemplate):
    
    def __init__(self) -> None:
        model = Clustering2PageModel()
        view = Clustering2PageView(model, custom_page=self)
        controller = Clustering2PageController(model, view)
        
        if controller.is_valid_tab_and_dataset():
            super().__init__(
                title="Adv. Clustering Page",
                main=[view.main],
                sidebar=[view.left_sidebar],
                right_sidebar=[view.right_sidebar],
                modal=view.modals,
                sidebar_width=275
            )
            return
        
        super().__init__(
            title="Adv.Clustering Page",
            main=[view.main],
            sidebar=[view.left_sidebar],
            modal=view.modals,
            sidebar_width=275
        )
        

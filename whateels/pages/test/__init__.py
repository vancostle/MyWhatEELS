from whateels.components import CustomPage
from .MVC.view import View

class Test(CustomPage):

    def __init__(self):
        view: View = View()
        super().__init__(
            title='TEST PAGE',
            main=[view.main],
            sidebar=[view.sidebar],
        )
import panel as pn
from .controller import HomePageController
from .model import HomePageModel
from .view import HomePageView

@pn.cache
def get_cached_homepage_model() -> HomePageModel:
    """Cache the model across navigations — datasets and AppState refs are reused,
    only the View and Controller are recreated on each visit."""
    return HomePageModel()
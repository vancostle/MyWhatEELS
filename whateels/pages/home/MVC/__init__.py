import panel as pn

from .controller import HomePageController
from .model import HomePageModel
from .view import HomePageView

@pn.cache # Cache the model instance to reuse across multiple HomePage instances
def get_cached_homepage_model():
    return HomePageModel()
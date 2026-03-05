from .controller import HomePageController
from .model import HomePageModel
from .view import HomePageView

def get_cached_homepage_model() -> HomePageModel:
    """Return the HomePageModel scoped to the current user (or global if no auth).
    Reuses the same instance across tab navigations for the same user."""
    import panel as pn
    from whateels.shared_state import _user_key

    key = _user_key("homepage_model")
    if key not in pn.state.cache: # type: ignore
        pn.state.cache[key] = HomePageModel() # type: ignore
    return pn.state.cache[key] # type: ignore
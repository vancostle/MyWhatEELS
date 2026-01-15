from whateels.helpers import CSS_ROOT, LoadCSS
from .layouts import LoginMainLayout

class LoginPageView:
    
    def __init__(self, model):
        
        LoadCSS([str(CSS_ROOT / "login.css")])
        
        self._main = LoginMainLayout(
            width=400, 
            sizing_mode="stretch_both",
            styles={"height": "auto", "min-height": "auto"}
        )
        
        
    @property
    def main(self):
        return self._main
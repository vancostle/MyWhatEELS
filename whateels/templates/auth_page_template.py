import panel as pn

from whateels.helpers import CSS_ROOT, LoadCSS

class AuthPageTemplate(pn.template.FastListTemplate):
    """
    Authentication page template extending Panel's FastListTemplate.
    """
    
    def __init__(self, **kwargs) -> None:
        
        LoadCSS([str(CSS_ROOT / "auth_page_template.css")])
        
        super().__init__(**kwargs)
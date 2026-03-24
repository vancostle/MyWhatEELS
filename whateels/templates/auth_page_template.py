import panel as pn

class AuthPageTemplate(pn.template.FastListTemplate):
    """
    Authentication page template extending Panel's FastListTemplate.
    """
    
    def __init__(self, **kwargs) -> None:
        
        # Load any provided CSS files
        pn.config.css_files.append('/assets/css/login.css') # type: ignore
        
        super().__init__(**kwargs)
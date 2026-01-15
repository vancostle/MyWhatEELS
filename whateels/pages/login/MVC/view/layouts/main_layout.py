import panel as pn

class LoginMainLayout(pn.Column):
    
    def __init__(self, **kwargs):
        
        form = self._form()
        logo = self._logo()
        
        wrapper = pn.Row(
            logo,
            form,
            margin=0,
            styles={"padding": "0", "height": "auto", "min-height": "auto", "max-width": "800px", "justify-content": "space-around", "align-items": "center", "gap": "50px"},
            sizing_mode="stretch_height",
        )
             
        super().__init__(
            wrapper, 
            **kwargs
        )
        
    def _form(self) -> pn.Column:
        title = pn.pane.Markdown(
            "## Login Page", 
            margin=0, 
            styles={"padding" : "0"}
        )
        email = pn.widgets.TextInput(
            name="Email", 
            placeholder="Enter your email", 
            sizing_mode="stretch_width", 
            margin=0
        )
        password = pn.widgets.PasswordInput(
            name="Password", 
            placeholder="Enter your password", 
            sizing_mode="stretch_width", 
            margin=0
        )
                
        login_button = pn.widgets.Button(
            name="Login", 
            button_type="primary", 
            sizing_mode="stretch_width", 
            margin=0
        )   
        
        form = pn.Column(
            title,
            pn.Spacer(height=10),
            email,
            pn.Spacer(height=10),
            password,
            pn.Spacer(height=20),
            login_button,
            width=400,
            sizing_mode="stretch_height",
        )
        return form
    
    def _logo(self) -> pn.Column:
        logo = pn.pane.SVG(
            "whateels/assets/img/we_rainbow_logo.svg", 
            sizing_mode="scale_height",
            margin=0
        )
        return pn.Column(
            logo,
            sizing_mode="stretch_both",
            styles={"display": "flex", "justify-content": "center", "align-items": "center"},
        )
import panel as pn

class LoginMainLayout(pn.Column):
    
    def __init__(self, **kwargs):
        
        form = self._left_column()
        right_column = self._right_column()
        
        wrapper = pn.Row(
            form,
            width=400,
            margin=0,
            styles={"padding": "0", "height": "auto", "min-height": "auto"},
            sizing_mode="stretch_height",
        )
             
        super().__init__(
            wrapper, 
            **kwargs
        )
        
    def _left_column(self) -> pn.Column:
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
        
        spacer = pn.Spacer(height=10)
        
        login_button = pn.widgets.Button(
            name="Login", 
            button_type="primary", 
            sizing_mode="stretch_width", 
            margin=0
        )   
        
        form = pn.Column(
            title,
            email,
            password,
            spacer,
            login_button,
            sizing_mode="stretch_both",
        )
        return form
    
    def _right_column(self) -> pn.Column:
        logo = pn.pane.SVG(
            "whateels/assets/img/we_rainbow_logo.svg", 
            sizing_mode="scale_both", 
            margin=0
        )
        return pn.Column(
            logo,
            sizing_mode="stretch_both",
        )
import panel as pn
import param

from whateels.components import CustomPage

class ModalManager(param.Parameterized):
    modals = param.Dict(default={})  # {modal_id: {'visible': bool, 'content': pn.Viewable}}
    
    def __init__(self, custom_page: CustomPage, **params):
        super().__init__(**params)
        
        self.custom_page = custom_page

    def add_modal(self, modal_id, content):
        if not isinstance(self.modals, dict):
            return
        self.modals[modal_id] = {'visible': False, 'content': content}

    def open(self, modal_id):
        if not isinstance(self.modals, dict):
            return
        if modal_id in self.modals:
            self.modals[modal_id]['visible'] = True
        self.custom_page.open_modal()

    def close(self):
        if not isinstance(self.modals, dict):
            return
        for modal in self.modals.values():
            modal['visible'] = False
        self.custom_page.close_modal()

    def view(self):
        if not isinstance(self.modals, dict):
            return
        # Only show modals that are visible
        return pn.Column(
            *[pn.Column(
                modal['content'],
                visible=modal['visible'],
                css_classes=['custom-modal'],
                sizing_mode='stretch_both'
            ) for modal in self.modals.values()],
            sizing_mode='stretch_both'
        )
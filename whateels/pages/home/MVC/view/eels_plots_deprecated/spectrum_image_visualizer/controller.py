import panel as pn

class SpectrumImageController:
    """
    Controlador ligero: mantiene refs a model y view y ofrece API mínima para
    que el resto de la aplicación interactúe con el visualizador.
    """
    def __init__(self, model=None, layout=None):
        self.model = model
        self.view = None
        # opcional: layout externo que puede usarse para toggles en dataset_info
        self.layout = layout

    def attach_view(self, view):
        self.view = view

    def set_dataset(self, ds):
        if self.model is not None:
            # asignación en el modelo dispara actualización de la vista
            self.model.set_dataset(ds)

    def create_ui(self):
        """Conveniencia: crear y devolver el layout completo (plots + info)."""
        if self.view is None:
            return None
        plots = self.view.create_plots()
        info = self.view.create_dataset_info()
        return pn.Column(plots, info, sizing_mode="stretch_width")
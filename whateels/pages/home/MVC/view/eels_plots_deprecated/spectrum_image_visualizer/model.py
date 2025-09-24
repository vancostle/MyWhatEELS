import param
from types import SimpleNamespace

class SpectrumImageModel(param.Parameterized):
    """
    Modelo mínimo: expone `dataset` (xarray-like) y `constants` (nombres de coordenadas).
    Cambiar dataset mediante model.dataset = new_ds dispara watchers (param).
    """
    dataset = param.Parameter(default=None)
    constants = param.Parameter(default=SimpleNamespace(ELOSS='E'))

    def __init__(self, dataset=None, constants=None, **kwargs):
        super().__init__(**kwargs)
        if constants is not None:
            self.constants = constants
        if dataset is not None:
            self.dataset = dataset

    def set_dataset(self, ds):
        """Conveniencia para reemplazar dataset (dispara eventos param automáticamente)."""
        self.dataset = ds
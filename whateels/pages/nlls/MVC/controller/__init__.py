from whateels.base.mvc import BaseController

class NLLSController(BaseController):
    def __init__(self, model, view):
        super().__init__(model, view)
        
        self._model = model
        self._view = view
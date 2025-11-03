from whateels.base.mvc import BaseView

class NLLSView(BaseView):
    def __init__(self, model):
        super().__init__(model)
        
        self._model = model
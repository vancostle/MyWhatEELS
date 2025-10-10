
class ToggleButton:
    def __init__(self, initial_state=False):
        self.state = initial_state

    def toggle(self):
        self.state = not self.state

    def is_on(self):
        return self.state
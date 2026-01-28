class ComponentItem:
    def __init__(self, energy_center, model_type):
        self.energy_center = energy_center
        self.model_type = model_type
        self.energy_range = (0, 0)

    def __str__(self):
        return f"{self.model_type}({self.energy_center})"

    def set_energy_center(self, energy_range):
        self.energy_range = energy_range

    def set_model_type(self, model_type):
        self.model_type = model_type

    def set_energy_range(self, energy_range):
        self.energy_range = energy_range
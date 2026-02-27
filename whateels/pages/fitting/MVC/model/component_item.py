class ComponentItem:
    def __init__(self, energy_center, compo_type, energy_range, flexibility='low'):
        self.energy_center = energy_center
        self.compo_type = compo_type
        self.energy_range = energy_range
        self.center_range = (0, 0)
        self.flexibility = flexibility

    def __str__(self):
        return f"{self.compo_type}({self.energy_center})"

    def set_energy_center(self, energy_range):
        self.energy_range = energy_range

    def set_compo_type(self, compo_type):
        self.compo_type = compo_type

    def set_center_range(self, center_min, center_max):
        self.center_range = (center_min, center_max)

    def set_parameters(self, center, sigma, amplitude):
        self.energy_center = center
        self.sigma = sigma
        self.amplitude = amplitude

    def set_sigma_range(self, sigma_min, sigma_max):
        self.sigma_range = (sigma_min, sigma_max)
    
    def set_amplitude_range(self, amplitude_min, amplitude_max):
        self.amplitude_range = (amplitude_min, amplitude_max)


# crear fills dauqest per els parametres de cada model "GaussianModel","LorentzianModel","PseudoVoigtModel","SplitLorentzianModel"
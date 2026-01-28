class ElementItem:
    def __init__(self, element, shells, element_name, element_name_short, fit_range= None):
        self.element = element
        self.shells = shells
        self.element_name = element_name
        self.element_name_short = element_name_short
        self.fit_range = fit_range
        self.chemical_shift = 0.0  # Default chemical shift value

    def __str__(self):
        return f"{self.element_name} ({self.element}) ({', '.join(self.shells)})"

    def set_fit_range(self, fit_range):
        self.fit_range = fit_range
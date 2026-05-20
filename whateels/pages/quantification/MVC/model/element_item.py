class ElementItem:
    def __init__(self, element, shells, element_name, element_name_short, fit_range= None, quant_width= 50):
        self.element = element
        self.shells = shells
        self.element_name = element_name
        self.element_name_short = element_name_short
        self.fit_range = fit_range
        self.quant_width = quant_width
        self.cross_sections = {}
        self.chemical_shift = 0.0  # Default chemical shift value

    def __str__(self):
        return f"{self.element_name} ({self.element}) ({', '.join(self.shells)})"

    def set_fit_range(self, fit_range):
        self.fit_range = fit_range

    def set_quant_width(self, quant_width):
        self.quant_width = quant_width

    def set_quant_range(self, min_eaxis_cs, max_eaxis_cs=None):
        if max_eaxis_cs is None:
            max_eaxis_cs = min_eaxis_cs
        self.quant_range = (
            min_eaxis_cs - self.chemical_shift,
            max_eaxis_cs + self.quant_width - self.chemical_shift,
        )
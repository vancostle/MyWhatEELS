class ElementItem:
    """Container for element metadata and selected fitting shells/range."""

    def __init__(self, element, shells, element_name, element_name_short, fit_range= None):
        """Store element identity fields and optional fit range."""
        self.element = element
        self.shells = shells
        self.element_name = element_name
        self.element_name_short = element_name_short
        self.fit_range = fit_range
        self.chemical_shift = 0.0

    def __str__(self):
        """Return a readable summary shown in selection widgets."""
        return f"{self.element_name} ({self.element}) ({', '.join(self.shells)})"

    def set_fit_range(self, fit_range):
        """Update fitting range bounds for this element."""
        self.fit_range = fit_range
class ComponentItem:
    """Lightweight data container for a fitting component and its parameter bounds."""

    def __init__(self, energy_center, compo_type, energy_range, flexibility='low'):
        """Initialize component metadata and default center-range placeholders."""
        self.energy_center = energy_center
        self.compo_type = compo_type
        self.energy_range = energy_range
        self.center_range = (0, 0)
        self.flexibility = flexibility

    def __str__(self):
        """Return a compact human-readable identifier used in the UI."""
        return f"{self.compo_type}({self.energy_center})({self.flexibility})"

    def set_energy_center(self, energy_range):
        """Update stored energy range value (legacy method name kept for compatibility)."""
        self.energy_range = energy_range

    def set_compo_type(self, compo_type):
        """Set the lmfit component type name."""
        self.compo_type = compo_type

    def set_center_range(self, center_min, center_max):
        """Set allowed bounds for center parameter optimization."""
        self.center_range = (center_min, center_max)

    def set_parameters(self, center, sigma, amplitude):
        """Set initial parameter guesses used to build lmfit parameters."""
        self.energy_center = center
        self.sigma = sigma
        self.amplitude = amplitude

    def set_sigma_range(self, sigma_min, sigma_max):
        """Set lower/upper bounds for sigma parameter."""
        self.sigma_range = (sigma_min, sigma_max)
    
    def set_amplitude_range(self, amplitude_min, amplitude_max):
        """Set lower/upper bounds for amplitude parameter."""
        self.amplitude_range = (amplitude_min, amplitude_max)
import numpy as np
import scipy as sp
import json


def get_energy_axis(m, nE):
    """
    Retrieves the energy axis from the data.

    Parameters:
        m: The Hyperspy object containing the data.
        nE: The expected number of energy points.

    Returns:
        energy: A NumPy array representing the energy axis.

    Raises:
        ValueError: If the energy axis length does not match the data.
    """
    try:
        energy = np.asarray(m.axes_manager[-1].axis)
        if energy.shape[0] != nE:
            raise ValueError("Energy axis length does not match data")
    except Exception:
        # If the energy axis cannot be retrieved, generate a default range
        energy = np.arange(nE)
    return energy

# Constants used in calculations
R = 13.6056923             # Rydberg energy in eV
e = 1.602176487 * 1E-19    # Electron charge in C
m0 = 9.10938215 * 1E-31    # Electron rest mass in kg
a0 = 5.2917720859 * 1E-11  # Bohr radius in m
c = 299792458              # Speed of light in m/s

class Loader_OOS():
    """
    Class to handle the loading and processing of OOS (Oscillator Strength) data.
    """
    def __init__(self, dir_path):
        """
        Initializes the Loader_OOS object.

        Parameters:
            dir_path: Path to the directory containing the OOS database.
        """
        super().__init__()
        self.subshells = []         # List of all available subshells for the specified element
        self.directory = dir_path

    def oos_reader(self, z_number, subshell):
        """
        Reads the OOS database for a specific element and subshell.

        Parameters:
            z_number: Atomic number of the element (1 to 99).
            subshell: String representing the subshell transition.

        Returns:
            energy: Energy axis for the subshell.
            oos: Oscillator strength data.
            onset: Energy loss of the transition.

        Raises:
            ValueError: If the atomic number is not between 1 and 99.
            RuntimeError: If no directories are available.
            KeyError: If the specified subshell is not found.
        """
        try:
            z_number = int(z_number)  # Ensure the atomic number is an integer
            if z_number < 10:
                oos_filename = "OOS0" + str(z_number)
            elif 10 <= z_number <= 99:
                oos_filename = "OOS" + str(z_number)
            else:
                raise ValueError("z_number should be between 1 and 99")
        except ValueError:
            print("z_number must be a valid integer between 1 and 99")

        directories_possible = [el for el in self.directory]

        if len(directories_possible) == 0:
            raise RuntimeError("No directories available to dive in.")

        # Load the OOS data from the JSON file
        with open(f'{self.directory}/{oos_filename}.json', 'r') as g:
            oos_file = json.load(g)

        for item in oos_file:
            try:
                # Check if the item is a dictionary and contains the subshell
                if isinstance(item, dict):
                    self.subshells.extend(item.keys())                          
                    if subshell in self.subshells:
                        ##print(f'Subshell {subshell} found.')
                        ##print("Energy axis (last value):", np.array(item[subshell]['eaxis'])[-1])
                        return np.array(item[subshell]['eaxis']), np.array(item[subshell]['counts']), \
                            item[subshell]['onset']
                    elif subshell is None:
                        pass
                    else:
                        raise KeyError(f'Subshell {subshell} not found in available subshells: {self.subshells}.') 
            except KeyError as e:
                raise KeyError(f'Subshell {subshell} not found in available subshells: {self.subshells}.')
            
    def avaibable_subshells(self, z_number):
        """
        Retrieves the available subshells for a given element.

        Parameters:
            z_number: Atomic number of the element.

        Returns:
            A list of available subshells.
        """
        self.subshells = []
        self.oos_reader(z_number, subshell=None)
        ##print(f'Available subshells for element {z_number} are {self.subshells}')
        return self.subshells
            
    def df_cross_section(self, z_number, subshell, V=None, b=None, si=None):
        """
        Calculates the differential cross-section using Egerton's equation (Eq. 3.149).

        Parameters:
            z_number: Atomic number of the element.
            subshell: String representing the subshell transition.
            V: Beam energy in eV (optional if si is provided).
            b: Collection angle in mrad (optional if si is provided).
            si: Hyperspy object containing metadata (optional).

        Returns:
            cross_section: The calculated differential cross-section.

        Raises:
            ValueError: If beam energy or collection angle is missing.
            ZeroDivisionError: If the beam energy is zero.
        """
        if si is not None:
            # Extract beam energy and collection angle from metadata
            V = si.metadata.Acquisition_instrument.TEM.beam_energy
            b = si.metadata.Acquisition_instrument.TEM.Detector.EELS.collection_angle
        elif si is None and (V, b) == (None, None):
            raise ValueError("Beam energy or/and collection angle missing, please provide them manually.")

        _, oos, eloss = self.oos_reader(z_number, subshell)
        v = 2 * e * V / m0  # Electron velocity based on the applied potential
        T = m0 * v**2 / 2   # Kinetic energy of the electron
        gamma = (1 - (v / c)**2)**(-1/2)  # Relativistic factor

        try:
            Oe = eloss / (2 * gamma * T)  # Characteristic energy
        except ZeroDivisionError:
            raise ZeroDivisionError('Beam energy (V) cannot be zero, check your data and provide an appropriate voltage.')

        # Calculate the differential cross-section
        return 4 * np.pi * (a0 * R)**2 * 1 / (eloss * T) * oos * np.log(1 + (b / Oe)**2)

    def cross_section(self, z_number, subshell, V=None, b=None, si=None) -> float:
        """
        Calculates the total cross-section by integrating Egerton's equation (Eq. 3.149).

        Parameters:
            z_number: Atomic number of the element.
            subshell: String representing the subshell transition.
            V: Beam energy in eV (optional if si is provided).
            b: Collection angle in mrad (optional if si is provided).
            si: Hyperspy object containing metadata (optional).

        Returns:
            The real part of the integrated cross-section.
        """
        return (sp.integrate.trapezoid(self.df_cross_section(z_number, subshell, V, b, si))).real
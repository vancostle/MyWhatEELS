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
KEV_TO_EV = 1E3
MRAD_TO_RAD = 1E-3
ELECTRON_REST_ENERGY_EV = m0 * c**2 / e


def _beam_energy_kev_to_ev(beam_energy_kev):
    """Return beam energy in eV from the WhatEELS beam energy stored in keV."""
    beam_energy_kev = float(beam_energy_kev)
    if beam_energy_kev <= 0:
        raise ZeroDivisionError(
            'Beam energy (V) cannot be zero, check your data and provide an appropriate voltage.'
        )
    return beam_energy_kev * KEV_TO_EV


def _collection_angle_mrad_to_rad(collection_angle_mrad):
    collection_angle_mrad = float(collection_angle_mrad)
    if collection_angle_mrad <= 0:
        raise ValueError("Collection angle must be positive and provided in mrad.")
    return collection_angle_mrad * MRAD_TO_RAD


def _convergence_angle_mrad_to_rad(convergence_angle_mrad):
    """Return the convergence semi-angle in rad from a value provided in mrad.

    A non-positive or missing convergence angle is treated as a parallel
    (zero-convergence) illumination, for which no geometric correction applies.
    """
    if convergence_angle_mrad is None:
        return 0.0
    convergence_angle_mrad = float(convergence_angle_mrad)
    if convergence_angle_mrad < 0:
        raise ValueError("Convergence angle must be non-negative and provided in mrad.")
    return convergence_angle_mrad * MRAD_TO_RAD


def effective_collection_angle_mrad(beam_energy_kev, eloss_eV, alpha_mrad, beta_mrad):
    """Effective collection semi-angle for a finite convergence angle.

    Under a finite convergence semi-angle ``alpha``, the intensity collected by
    an aperture of semi-angle ``beta`` is no longer the one of a sharp cutoff at
    ``beta``: the incident and collection cones overlap only partially. Egerton
    (Electron Energy-Loss Spectroscopy in the Electron Microscope, 2nd ed., 2011,
    p. 420) accounts for this by replacing ``beta`` in the angle-integrated cross
    section by an effective collection semi-angle ``beta*`` that depends on
    ``alpha``, ``beta`` and the characteristic angle ``theta_E``.

    This is a faithful transcription of Egerton's closed form (the same
    expression implemented by HyperSpy's ``effective_angle``). All input angles
    are in mrad and the beam energy in keV; ``eloss_eV`` may be a scalar or a
    NumPy array (one value per energy-loss channel), and the returned ``beta*``
    has the matching shape, in mrad.

    For parallel illumination (``alpha <= 0``) the function returns ``beta``
    unchanged, recovering the standard sharp-cutoff collection at ``beta``.

    References
    ----------
    R. F. Egerton, EELS in the Electron Microscope, 2nd ed., p. 420.
    """
    alpha_mrad = float(alpha_mrad)
    beta_mrad = float(beta_mrad)
    eloss = np.asarray(eloss_eV, dtype=float)
    scalar_input = eloss.ndim == 0

    if alpha_mrad <= 0.0:
        return float(beta_mrad) if scalar_input else np.full(eloss.shape, beta_mrad)

    # Relativistic kinetic term (Egerton p. 420); E0 in keV here.
    E0 = float(beam_energy_kev)
    TGT = E0 * (1.0 + E0 / 1022.0) / (1.0 + E0 / 511.0)   # in keV-equivalent
    thetaE = eloss / TGT                                  # characteristic angle (mrad)

    # Squared angles, converted from mrad^2 to rad^2 (factor 1e-6), as in Egerton.
    A2 = alpha_mrad * alpha_mrad * 1e-6
    B2 = beta_mrad * beta_mrad * 1e-6
    T2 = thetaE * thetaE * 1e-6

    eta1 = np.sqrt((A2 + B2 + T2) ** 2 - 4.0 * A2 * B2) - A2 - B2 - T2
    eta2 = 2.0 * B2 * np.log(
        0.5 / T2 * (np.sqrt((A2 + T2 - B2) ** 2 + 4.0 * B2 * T2) + A2 + T2 - B2)
    )
    eta3 = 2.0 * A2 * np.log(
        0.5 / T2 * (np.sqrt((B2 + T2 - A2) ** 2 + 4.0 * A2 * T2) + B2 + T2 - A2)
    )

    F1 = (eta1 + eta2 + eta3) / 2.0 / A2 / np.log(1.0 + B2 / T2)
    # Egerton uses F2 = F1, except F2 = F1 * A2 / B2 when alpha/beta > 1.
    if (alpha_mrad / beta_mrad) > 1.0:
        F2 = F1 * A2 / B2
    else:
        F2 = F1

    beta_star = thetaE * np.sqrt(np.exp(F2 * np.log(1.0 + B2 / T2)) - 1.0)
    return float(beta_star) if scalar_input else beta_star


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
            raise ValueError("z_number must be a valid integer between 1 and 99")

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
                        return np.array(item[subshell]['eaxis']), np.array(item[subshell]['counts']), \
                            item[subshell]['onset']
                    elif subshell is None:
                        pass
                    else:
                        raise KeyError(f'Subshell {subshell} not found in available subshells: {self.subshells}.') 
            except KeyError as e:
                raise KeyError(e)
    
    def element_name(self, z_number):
        """
        Retrieves the element name for a given atomic number.

        Parameters:
            z_number: Atomic number of the element.

        Returns:
            The name of the element.
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
            raise ValueError("z_number must be a valid integer between 1 and 99")

        # Load the OOS data from the JSON file
        with open(f'{self.directory}/{oos_filename}.json', 'r') as g:
            oos_file = json.load(g)
        return oos_file[0]
    def element_name_short(self, z_number):
        """
        Retrieves the short element name (symbol) for a given atomic number.

        Parameters:
            z_number: Atomic number of the element.

        Returns:
            The symbol of the element.
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
            raise ValueError("z_number must be a valid integer between 1 and 99")

        # Load the OOS data from the JSON file
        with open(f'{self.directory}/{oos_filename}.json', 'r') as g:
            oos_file = json.load(g)
        return oos_file[1]
            
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
        return self.subshells
            
    def df_cross_section(self, z_number, subshell, V=None, b=None, a=None, si=None):
        """
        Energy-loss differential cross section for the angle-restricted EELS
        geometry, following Salvat's relativistic PWBA (RPWBA) formulation.

        The reference oscillator strengths (the ``oos`` returned by
        :meth:`oos_reader`) are the optical (Q->0) limit of the longitudinal
        generalized oscillator strength tabulated by Salvat within the RPWBA
        with a DHFS potential. The cross section collected within a semi-angle
        ``beta`` is given by Salvat's compact small-angle formula (his
        Appendix E, Eq. E.12),

            d(sigma)/dW = (2 pi Z0^2 e^4)/(m_e v^2) (1/W) (df/dW)
                          [ ln Y - beta_v^2 (1 - 1/Y) ] ,

        with Z0 = 1 for electrons, where ``W`` is the energy loss, ``df/dW`` the
        OOS, ``beta_v = v/c`` the relativistic speed of the probe, and the
        relativistic kinematic factor ``Y`` (Eq. E.13) is

            Y = 1 + sqrt( [E(E + 2 m_e c^2)]^3 (E - W)(E - W + 2 m_e c^2) )
                    / [ (m_e c^2)^2 W^2 ]
                    * 4 sin^2(beta/2) ,

        with ``E`` the probe kinetic energy. Unlike the small-angle dipole form
        of Egerton (Eq. 3.149), this keeps the exact relativistic kinematics
        (``Y``) and the transverse/retardation term ``- beta_v^2 (1 - 1/Y)``,
        so it is the form consistent with Salvat's relativistic OOS.

        Salvat's formula assumes parallel illumination. When a finite
        convergence semi-angle ``a`` (alpha) is provided, the collection
        semi-angle in ``Y`` is replaced by Egerton's effective collection
        semi-angle ``beta*`` (see :func:`effective_collection_angle_mrad`),
        which approximately accounts for the partial overlap of the convergence
        and collection cones. With ``a`` set to ``None`` or zero, the parallel
        sharp-cutoff collection at ``beta`` is recovered.

        Parameters:
            z_number: Atomic number of the element.
            subshell: String representing the subshell transition.
            V: Beam energy in keV (optional if si is provided).
            b: Collection semi-angle (beta) in mrad (optional if si is provided).
            a: Convergence semi-angle (alpha) in mrad (optional; defaults to
               parallel illumination, i.e. no geometric correction).
            si: Hyperspy object containing metadata (optional).

        Returns:
            cross_section: The calculated differential cross-section (m^2/eV).

        Raises:
            ValueError: If beam energy or collection angle is missing.
            ZeroDivisionError: If the beam energy is zero.
        """
        if si is not None:
            # Extract beam energy and collection angle from metadata
            V = si.metadata.Acquisition_instrument.TEM.beam_energy
            b = si.metadata.Acquisition_instrument.TEM.Detector.EELS.collection_angle
        elif si is None and (V is None or b is None):
            raise ValueError("Beam energy or/and collection angle missing, please provide them manually.")

        _, oos, eloss = self.oos_reader(z_number, subshell)
        T_eV = _beam_energy_kev_to_ev(V)
        beta_rad = _collection_angle_mrad_to_rad(b)
        mec2 = ELECTRON_REST_ENERGY_EV
        gamma = 1 + T_eV / mec2

        if not np.isfinite(gamma):
            raise ValueError(
                f"Relativistic factor is not finite for beam energy {V}. "
                "Check that the value is a positive beam energy in keV."
            )

        # Relativistic speed of the probe, beta_v^2 = (v/c)^2 = 1 - 1/gamma^2.
        beta_v2 = 1.0 - 1.0 / gamma ** 2

        # Convergence correction: Salvat's formula is for parallel illumination;
        # for finite alpha we feed Egerton's effective collection semi-angle
        # beta* into the kinematic factor Y instead of the nominal beta.
        alpha_rad = _convergence_angle_mrad_to_rad(a)
        if alpha_rad > 0.0:
            beta_collection_rad = effective_collection_angle_mrad(V, eloss, a, b) * MRAD_TO_RAD
        else:
            beta_collection_rad = beta_rad

        # Relativistic kinematic factor Y (Salvat Eq. E.13). Note the square root
        # over the full kinematic product, with (T-E)(T-E+2 me c^2) INSIDE the
        # root; the angular dependence enters through 4 sin^2(beta/2) (~ beta^2
        # at small angles).
        root = (T_eV * (T_eV + 2.0 * mec2)) ** 3 * (T_eV - eloss) * (T_eV - eloss + 2.0 * mec2)
        Y = 1.0 + np.sqrt(root) / (mec2 ** 2 * eloss ** 2) * 4.0 * np.sin(beta_collection_rad / 2.0) ** 2

        # Salvat angular/relativistic bracket (Eq. E.12): the logarithmic
        # collection term plus the transverse (retardation) correction.
        collection_term = np.log(Y) - beta_v2 * (1.0 - 1.0 / Y)

        # Prefactor (2 pi Z0^2 e^4)/(m_e v^2)(1/W), with Z0 = 1, written with
        # e^2 = 2 a0 R and m_e v^2 = m_e c^2 * beta_v^2:
        #     8 pi (a0 R)^2 / (m_e c^2 beta_v^2 W).
        prefactor = 8.0 * np.pi * (a0 * R) ** 2 / (mec2 * beta_v2 * eloss)

        return prefactor * oos * collection_term

    def cross_section(self, z_number, subshell, V=None, b=None, a=None, si=None) -> float:
        """
        Partial ionization cross section, obtained by integrating Salvat's
        energy-loss differential cross section (:meth:`df_cross_section`) over
        the tabulated energy-loss axis.

        Parameters:
            z_number: Atomic number of the element.
            subshell: String representing the subshell transition.
            V: Beam energy in keV (optional if si is provided).
            b: Collection semi-angle (beta) in mrad (optional if si is provided).
            a: Convergence semi-angle (alpha) in mrad (optional).
            si: Hyperspy object containing metadata (optional).

        Returns:
            The real part of the integrated cross-section.
        """
        return (sp.integrate.trapezoid(self.df_cross_section(z_number, subshell, V, b, a, si))).real

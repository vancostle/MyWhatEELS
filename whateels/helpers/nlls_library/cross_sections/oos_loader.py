from pathlib import Path

import numpy as np
import json

import scipy as sp
import copy as cp

from whateels.helpers.constants import OOS_ROOT
from ..initialization_panel import Fileinput    
################################################################################

R = 13.6056923             # Rydberg of energy in eV
e = 1.602176487*1E-19      # electron charge in C
m0 = 9.10938215*1E-31      # electron rest mass in kg
a0 = 5.2917720859*1E-11    # Bohr radius in m
c = 299792458              # Light's speed velocity in m/s
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

def oos_reader(z_number:int, subshell:str, directory = None):
    """
    this function reads the OOSdatabase from the directory where the database is stored

    Args:
        z_number: from 1 to 99, as are the atoms avaibable in the database
        subshell: string of the transition
    
    Returns:
        energy: axis of the energy
        oos: oss
        onset: energy loss of the transition
    """
    if directory is None:
        data_dir = OOS_ROOT / "Hartree_Xsections_FSalvat"
    else:
        data_dir = Path(directory)
        if not data_dir.is_absolute() and not data_dir.exists():
            data_dir = OOS_ROOT / data_dir

    try:
        z_number = int(z_number)  # Attempt to convert to an integer
        if z_number < 10:
            oos_filename = "OOS0" + str(z_number)
        elif 10 <= z_number <= 99:
            oos_filename = "OOS" + str(z_number)
        else:
            raise ValueError("z_number should be between 1 and 99")
    except ValueError:
        print("z_number must be a valid integer between 1 and 99")

    with open(data_dir / f'{oos_filename}.json','r') as g:
        oos_file = json.load(g)

    for item in oos_file:
    # Check if the item is a dictionary and whether it contains the subshell
        try:
            if isinstance(item, dict) and subshell in item:
                print(f'searchig for {subshell} subshell')
                return np.array(item[subshell]['eaxis']), np.array(item[subshell]['counts']), item[subshell]['onset']
        except:
            raise KeyError("Unexpected error. The subshell provided may not exist in the database of the selected element.") 

def df_cross_section(z_number:int, subshell:str):
    """
    This method calculate the cross sections following the assumptions made by R. F. Egerton in EELS in the EM.
    In particular, applies the eq. 3.149, and after its calculation, it is integrated.

    Args:
        z_number: z atomic number
        subshell: string of the transition
        ds: data

    Returns:
        cross_section
    """
    V = Fileinput._callback_loadfile.beam_energy
    b = Fileinput._callback_loadfile.collection_angle

    _, oos, eloss = oos_reader(z_number, subshell)
    T_eV = _beam_energy_kev_to_ev(V)
    beta_rad = _collection_angle_mrad_to_rad(b)
    gamma = 1 + T_eV / ELECTRON_REST_ENERGY_EV
    if not np.isfinite(gamma):
        raise ValueError(
            f"Relativistic factor is not finite for beam energy {V}. "
            "Check that the value is a positive beam energy in keV."
        )
    theta_E = eloss / (2 * gamma * T_eV)

    return 4*np.pi*(a0*R)**2 * 1/(eloss*T_eV) * oos * np.log(1+(beta_rad/theta_E)**2)

def cross_section(z_number:int, subshell:str) -> float:
    """
    Calculates the cross section by integrating eq. 3.149 of Egerton. 
    It return the real part of the integral

    Args:
        z_number: z atomic number
        subshell: string of the transition
        ds: data
    """
    E, _, _ = oos_reader(z_number, subshell)
    return (sp.integrate.trapz(df_cross_section(z_number, subshell), E.min, E.max)).real

print(Fileinput._callback_loadfile.beam_energy)

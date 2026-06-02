import os
import sys

import numpy as np
import json

import scipy as sp
import copy as cp

from ..initialization_panel import Fileinput    
################################################################################

R = 13.6056923             # Rydberg of energy in eV
e = 1.602176487*1E-19      # electron charge in C
m0 = 9.10938215*1E-31      # electron rest mass in kg
a0 = 5.2917720859*1E-11    # Bohr radius in m
c = 299792458              # Light's speed velocity in m/s
KEV_TO_EV = 1E3
EV_VALUE_THRESHOLD = 1E4


def _beam_energy_to_ev(beam_energy):
    """Return beam energy in eV, accepting WhatEELS keV values and manual eV values."""
    beam_energy = float(beam_energy)
    if beam_energy <= 0:
        raise ZeroDivisionError(
            'Beam energy (V) cannot be zero, check your data and provide an appropriate voltage.'
        )
    return beam_energy if beam_energy > EV_VALUE_THRESHOLD else beam_energy * KEV_TO_EV

def oos_reader(z_number:int, subshell:str, directory = 'Hartree_Xsections_FSalvat'):
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
    #Default directory to look for the database
    #TODO implement a directory change routine
    print('syspath', sys.path)
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

    directories_possible = [el for el in sys.path if 'cross_sections' in el]
    print('possible dir', directories_possible)

    if len(directories_possible) == 0:
        raise RuntimeError("No directories available to dive in.")
    # elif '\\' in directory:
    #     ruta = '/'.join(directories_possible[0].split('\\'))
    #     directory = f'{ruta}/{directory}'

    with open(f'{sys.path[0]}/{directory}/{oos_filename}.json','r') as g:
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
    beam_energy_ev = _beam_energy_to_ev(V)
    T = beam_energy_ev
    kinetic_energy_j = e * beam_energy_ev
    v = np.sqrt(2 * kinetic_energy_j / m0) # electrons' velocity in terms of the appplied potencial
    gamma = (1 - (v/c)**2)**(-1/2)
    if not np.isfinite(gamma):
        raise ValueError(
            f"Relativistic factor is not finite for beam energy {V}. "
            "Check that the value is a positive beam energy in keV/eV."
        )
    Oe = eloss / (2* gamma * T)

    return 4*np.pi*(a0*R)**2 * 1/(eloss*T) * oos * np.log(1+(b/Oe)**2)

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

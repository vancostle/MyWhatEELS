import os
import sys
#Modifying path to be able to access librares
'''for el in ["../Library/","./Library/","../Library/cross_sections","./Library/cross_sections"]:
    if el not in sys.path:
        sys.path.append(el) 
'''
import numpy as np
import json

import scipy as sp
import copy as cp
#From Hyperspy
from Library.Database.elements import elements

R = 13.6056923             # Rydberg of energy in eV
e = 1.602176487*1E-19      # electron charge in C
m0 = 9.10938215*1E-31      # electron rest mass in kg
a0 = 5.2917720859*1E-11    # Bohr radius in m

'''
def gos_reader(element,subshell,directory = None):
    #First thing we do.. check that we have the element properties in the hyperspy dictionary
    # Convert to the "GATAN" nomenclature
    if not directory:
        ## TODO NOW - let's check ifwe have access to the database
        #By now...we asume it is there
        directory = 'C:\\Program Files (x86)\\Gatan\\DigitalMicrograph\\EELS Reference Data\\H-S GOS Tables'
        if not os.path.isdir(directory):
            raise Exception('The Hartree Slater GOS tables were not found at {}.\
            Please, check the location and try again'.format(directory))
    if element not in elements:
        raise ValueError
    elif subshell not in elements[element]['Atomic_properties']['Binding_energies']:
        raise ValueError
    #We get the onset and the subshell factor
    onset_energy = \
        elements[element]['Atomic_properties']['Binding_energies']\
        [subshell]['onset_energy (eV)']
    #The file name is easy to set ... just put together element and subshell
    #But wait! .... only the onset subshell get the table.....
    #e.g. Ce.M5 will serve as tabulated info for Ce.M5 and Ce.M4, sooo once again
    #and by now, let's get the info from hyperspy dictionary
    nfile = elements[element]['Atomic_properties']['Binding_energies']\
        [subshell]['filename']
    filename = '\\'.join([directory,nfile])
    #And now...let's extract the information
    with open(filename,'r') as f:
        GOS_list = f.read().replace('\r', '').split()
    #All are read as strings... so we cast them to the right format
    kq1 = float(GOS_list[2])
    kq2 = float(GOS_list[3])
    kE1 = float(GOS_list[6])
    kE2 = float(GOS_list[7])
    ncol = int(GOS_list[5])
    nrow = int(GOS_list[8])
    gos_array = np.array(GOS_list[9:], dtype=np.float64)
    # The division by R is not in the equations, but it seems that
    # the the GOS was tabulated this way
    # We are given the number of columns and rows for the Bethe surface -
    # so we have to reshape ...a and apparently rescale with R
    gos_array = gos_array.reshape(nrow, ncol) / R
    rel_energy_axis = kE1 * (np.exp(np.arange(nrow) * kE2 / kE1) - 1)
    qaxis = kq1 * (np.exp(np.arange(ncol) * kq2) - 1) * 1e10
    #We have to set up the energy axis right... the onset in the right place
    #Basically, the read energy axis is relative to the onset. 
    # e.g. As the CeM4 has the same theoretical surface (*scaling factor) than the CeM5, 
    #we have to set up the actual onset for the CeM4 excitation in place
    energy_axis = rel_energy_axis + onset_energy 
    #So the garbage collector can clean this variable now ... safety measure
    #del GOS_list
    return qaxis,energy_axis,gos_array,onset_energy

'''

def gos_reader(element,subshell,directory = 'Hartree_Xsections'):
    #Default directory to look for the database
    #TODO implement a directory change routine
    directories_possible = [el for el in sys.path if 'cross_section' in el]
    if len(directories_possible) == 0:
        raise 
    else:
        ruta = '/'.join(directories_possible[0].split('\\'))
        directory = f'{ruta}/{directory}'

    with open(f'{directory}/{element}_{subshell}.json','r') as g:
        dictionario = json.load(g)

    return np.array(dictionario['qaxis']),np.array(dictionario['Eaxis']),np.array(dictionario['GOS']),dictionario['onset']

def interpolator_q_gos(qgos_E,qax, Ei, qmin, qmax,linear = True,interpolator_func = None):
    """This method provides an extension of 
    the qaxis (log(qa0_st) in reality) and the 
    Generalized Oscillator Strangth (GOS), when needed by 
    the calculations of the qmax by physical constraints.
    It calculates (by linear interpolation) the q-point and the
    gos surface point for each position in the E axis if an extension
    of the axis is needed. It does the same for a possible inferior limit

    The reason that we only interpolate in the q range, is that for the E
    we can later (and will) correct by a power law, to get (for example) the 
    continuum components in a NLLS model

    Args:
        qgos_E (np.array) : Array containing the tabulated GOS values for a given E (Ei - index)
        qax (np.array) : Tabulated values for the E axis
        Ei (int): Integer for the position in the E axis under evaluation
        qmin (float): Minimum momentum transfer - limitation by E, T ... - Egerton
        qmax (float): Maximum momentum transfer - Limitation by physical constraints

    Returns:
        np.array: Gos surface and newly extended momentum axis
    """
    if linear:
        interpolator = lambda p1,p2,E: ((p2[1]-p1[1]) * E \
            + (p2[0]*p1[1]- p1[0]*p2[1])) / (p2[0]-p1[0])
    else:
        #The user may give a non linear interpolator
        if not interpolator_func:
            raise Exception('No valid interpolator for further expansion of the \
                gos function and qaxis was given. For a default behaviour, set linear = True\
                and a linear interpolation for extra points will be performed')
        else:
            interpolator = interpolator_func

    if qmax > qax[-1]:
        # So ... in the case of being out of bounds 
        # Let's extrapolate
        g1, g2 = qgos_E[-2:] # the last two points in the gos curve for Ei
        q1, q2 = qax[-2:] #The last two points in the qaxis for Ei
        gosqmax = interpolator((q1, g1), (q2, g2), qmax)
        qaxis = np.hstack((qax[:], qmax)) #We are basically appending a last value
        qgos_E = np.hstack((qgos_E[:], gosqmax)) #Appending the last value
    else:
        #If the qmax is lower than the last value of the qax, we have to get
        # the axis position it would have - np.searchsorted 
        #When then get a linear interpolation for the 'intermedium value'
        #We are trusting that idx >0... which is logical 
        # - otherwise no X-section could be retrieved anyway
        idx = qax.searchsorted(qmax)
        g1, g2 = qgos_E[idx - 1:idx + 1]
        q1, q2 = qax[idx - 1: idx + 1]
        #gosqmax = get_linear_interpolation((q1, g1), (q2, g2), qmax)
        gosqmax = interpolator((q1, g1), (q2, g2), qmax)
        qaxis = np.hstack((qax[:idx], qmax))
        qgos_E = np.hstack((qgos_E[:idx], gosqmax))

    if qmin > 0:
        #A slight different proceedure as for qmax
        #Basically, lower values are dangerous, if we interpolate to values
        #before qax[0], the weight they generally have over the GOS values
        #is much higher, and so, it is not modified unless we are actually cutting
        #some values out
        idx2 = qaxis.searchsorted(qmin)
        g1, g2 = qgos_E[idx2 - 1:idx2 + 1]
        q1, q2 = qaxis[idx2 - 1: idx2 + 1]
        gosqmin = interpolator((q1, g1), (q2, g2), qmin)
        qaxis = np.hstack((qmin, qaxis[idx2:]))
        qgos_E = np.hstack((gosqmin, qgos_E[idx2:]))

    #We have a linear interpolation, so it is possible that negatives values
    # are recovered for the GOS value ... we have to clip them 
    return qaxis, qgos_E.clip(0)

'''
qgosi = self.gos_array[ienergy, :]
if qmax > self.qaxis[-1]:
    # Linear extrapolation
    g1, g2 = qgosi[-2:]
    q1, q2 = self.qaxis[-2:]
    gosqmax = get_linear_interpolation((q1, g1), (q2, g2), qmax)
    qaxis = np.hstack((self.qaxis, qmax))
    qgosi = np.hstack((qgosi, gosqmax))
else:
    index = self.qaxis.searchsorted(qmax)
    g1, g2 = qgosi[index - 1:index + 1]
    q1, q2 = self.qaxis[index - 1: index + 1]
    gosqmax = get_linear_interpolation((q1, g1), (q2, g2), qmax)
    qaxis = np.hstack((self.qaxis[:index], qmax))
    qgosi = np.hstack((qgosi[:index, ], gosqmax))

if qmin > 0:
    index = self.qaxis.searchsorted(qmin)
    g1, g2 = qgosi[index - 1:index + 1]
    q1, q2 = qaxis[index - 1:index + 1]
    gosqmin = get_linear_interpolation((q1, g1), (q2, g2), qmin)
    qaxis = np.hstack((qmin, qaxis[index:]))
    qgosi = np.hstack((gosqmin, qgosi[index:],))
return qaxis, qgosi.clip(0)
'''
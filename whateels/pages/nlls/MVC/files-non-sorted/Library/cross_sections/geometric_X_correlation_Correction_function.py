import numpy as np
import math
#from bethe_surface_calculations import a0, R
from numpy import pi

R = 13.6056923             # Rydberg of energy in eV
a0 = 5.2917720859*1E-11    # Bohr radius in m


def factor_geom_F(T, E, logqa0sq, alpha, beta, gamma,m_e,*args,**kwargs):

    #Since they are introduced in mrad
    np.seterr(invalid = 'ignore',divide = 'ignore')
    alpha *=1E-3
    beta *=1E-3
    thet_min =  min(alpha,beta)                         #Kohl (12)

    #Initializing data storage
    factor = np.zeros((E.shape[0],logqa0sq.shape[0]))
    theta = np.zeros_like(factor)

    #Calculations to extract theta
    #We always consider the electron mass in eV/c^2
    k0a0sq = (T / R) /  (1 - 2 * T / m_e)               #Egerton (3.140)
    k1a0sq = k0a0sq - (E / R) * (gamma - 0.5 * E / m_e) #Egerton (3.139)

    #k0a0 = math.sqrt(k0a0sq)
    #k1a0 = np.sqrt(k1a0sq)

    #We are working with np.arrays
    
    qa0sq_min = (E ** 2) / (4 * R * T) +\
                    (E ** 3) / (8 * gamma ** 3\
                    * R * T ** 2)                       #Egerton (3.144)
    qa0sq = np.exp(logqa0sq)
    #Up to this point only E was playing.
    #Now LOOPS, we need to take into account all q for each energy
    
    for Ei,_ in enumerate(E):
        for qj,momentum in enumerate(qa0sq):
            num = momentum - qa0sq_min[Ei]
            denom = 4 * k0a0sq**0.5 * k1a0sq[Ei]**0.5
            theta[Ei,qj] = 2*np.arcsin((num / denom)**0.5) #Egerton (3.146)
    

    #Theta is a np.array(E.shape,q.shape)
    T2 = theta ** 2 

    A2 = alpha*alpha
    B2 = beta*beta

    x = (A2+T2-B2)/(2*alpha*theta)                #Kohl (13)
    y = (B2+T2-A2)/(2*beta*theta)                 #Kohl (14)

    #Conditions in the Kohl factor computation
    cond1 = abs(alpha - beta)
    cond2 = abs(alpha + beta)
    #Truth matrix
    COND_1_1 = np.zeros(theta.shape,dtype = bool)
    COND_1_2 = np.zeros(theta.shape,dtype = bool)
    COND_2_1 = np.zeros(theta.shape,dtype = bool)
    COND_2_2 = np.zeros(theta.shape,dtype = bool)

    COND_1_1[theta < cond1] = True
    COND_1_2[theta > 0.]    = True
    COND_2_1[theta > cond1] = True
    COND_2_2[theta < cond2] = True
    COND_1 = COND_1_1 * COND_1_2
    COND_2 = COND_2_1 * COND_2_2
    del COND_1_1, COND_1_2, COND_2_2, COND_2_1 

    #We don't need loop, we have bool matrices and all the
    #conditions already setup
    coeff = np.zeros(theta.shape)
    '''
    try:
        factor[COND_1] = thet_min**2 / A2  #Avoid division by 0
        coeff[COND_2] = (0.5 / A2) * np.sqrt(4*A2*B2-(A2+B2-T2[COND_2])**2)
    except:
    '''
    factor[COND_1] = thet_min**2 / max(A2,1E-10)
    coeff[COND_2] = (0.5 / max(A2,1E-10)) * np.sqrt(4*A2*B2-(A2+B2-T2[COND_2])**2)
    factor[COND_2] = (1 / np.pi) * (np.arccos(x[COND_2]) +\
    B2/max(A2,1E-10) * np.arccos(y[COND_2]) - coeff[COND_2])

    #factor[factor<0] = 0

    return factor

factor_geom_F.__doc__=\
"""
Calculates the geometric factor F to
correct the integration of cross-sections
to take into account the limited convergence
angle in STEM (alpha).

It take sinto account that the introduced energy
is one of the possitions at the energy axis

All the other quantities required had been
previously computed by the parent routine

This is applied individually to each value (qa0)^2
of the momentum axis 


Parameters
----------
T : float()
    Effective kinetic energy
E : float()
    energy loss value. Taken for each of the
    E possitions inthe energy axis given in 
    the tabulated GOS
alpha : float()
    convergence angle in mrad
beta : float()
    collection angle in mrad
gamma: float()
    gamma coefficient for relativistic effects
    on the incident electrons



Returns
-------
factor = Fbf : np.array()
    correction factor for the calculations of
    X-sections. Based on the geometric approach 
    in H.Kohl Ultramicroscopy 16 (1985) 265-268


Commentary:
The statement at the top to ignore numpy warnings
(np.seterr(invalid = 'ignore',divide = 'ignore')) has a profound
meaning regarding the physical implications:

If we apply this function to values bellow the qa0_min, the 
momentum conservation is no longer fullfilled - and since
all the formulations regarding theta and q relations are
built uppon this deeper phisical layer, we will observe how
numpy tries to evaluate arccos or arcsin for |values|>1, which
returns nan and an invalid value warning. 
In turn, when calculating x and y coefficients,
we find a divide by 0, and thus another warning.

This function is meant to be operated no matter what at any given
q-axis and E-axis. So, those values outside the limits imposed
by physical considerations that yield nan or 0 in the calculations, 
are also part of the bigger picture, and are not eliminated.
"""




    
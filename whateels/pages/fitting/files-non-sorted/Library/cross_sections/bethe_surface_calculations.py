import copy as cp
import numpy as np 
#Classic tools
from time import time
from scipy.integrate import simpson
from scipy import interpolate

#Tools from hyperspy
from Library.Database.elements import elements
#My own tools - in this same directory
from Library.cross_sections.geometric_X_correlation_Correction_function import factor_geom_F
from Library.cross_sections.gos_loader import gos_reader, interpolator_q_gos

#importing constants tabulated
#from hyperspy.misc.physical_constants import R, a0, m0
#from hyperspy.misc.physical_constants import c as c_light

R = 13.6056923             # Rydberg of energy in eV
e = 1.602176487*1E-19      # electron charge in C
m0 = 9.10938215*1E-31      # electron rest mass in kg
a0 = 5.2917720859*1E-11    # Bohr radius in m
c_light = 2.99792458*1E8  # speed of light in m/s

def timer(func):
    #
    '''
    Function defined as timer for other methods
    ________________________________________________________________
    It is thought to be used as a decorator @timer on top of methods
    '''
    def f(*args,**kwargs):
        ti = time()
        rv = func(*args,**kwargs)
        tf = time()
        print('Elapsed time: {} s'.format(tf-ti))
        return rv
    return f


class bethe_surface():
    '''
    The idea of this set of functions is to allow for a comprenhensive
    characterization of the bethe surfaces of the edges under analysis

    It can be run by itself, without having to analyze an specific
    dataset. So it is prone to be used previous to the experiment, to
    have an inside of the surface and select better angles for
    TEM-EELS acquisition

    Methods
    -------

    '''

    def __init__(self,element = 'C',verbose = False):
        '''
        Contrary to the version of hyperspy to read GOS-files, here we
        pre-acquire information of the available elements and subshells

        Paramenters
        -----------

        element = str().
                Name of element that will be under analysis
        verbose = bool()
                Decides if prints are shown or not.
                Default = False
                If True, several prints are shown along the way.
                It can be changed at any point in the process, and
                prints will be automatically displayed from that point
                forward
        '''
        self.element = element
        self.verbose = verbose

        #Lets see if the element is in the tabulated values
        if self.element  not in elements.keys():
            print('The element is not on the list of available GOS')
            print('\nReboot the function or change element variable')
            raise KeyError

        else:
            #Let's search for the possible subshells
            self.subshells = list(elements[self.element]['Atomic_properties']\
            ['Binding_energies'].keys())

            

            vari_temp = elements[self.element]['Atomic_properties']\
            ['Binding_energies']
            self.excluded_subshells = list()
            self.exp_param_setted = False

            if self.verbose:
                str0 = '\n····The available subshells for {} are····\n'
                str1 = '\n{} - Subshell ···· {}-{} '
                str2 = '\n   - Onset Energy ···· {}'
                str3 = '\n   - Relevance ···· {}'
                print(str0.format(self.element))
                for i,el in enumerate(self.subshells):
                    print('\n','*'*40)
                    print(str1.format(i,self.element,el))
                    print(str2.format(vari_temp[el]['onset_energy (eV)']))
                    print(str3.format(vari_temp[el]['relevance']))
                    print('\n','*'*40)

                print('\nIf you want to exclude any subshell from the computation')
                print('run exclude_subshells(list)')

            else: pass
            
    def exclude_subshells(self,lista = list()):
        # Docstring listed as Method-1
        lista_n  = [el for el in self.subshells if el not in lista]
        '''
        for el in lista:
            self.subshells.pop(self.subshells.index(el))
        '''
        self.subshells = cp.deepcopy(lista_n)
        self.excluded_subshells = lista

        if self.verbose:
            str0 = '\nThe new list of subshells is\n{}' 
            str1 = '\nThe list of excluded subshells is\n{}'
            print(str0.format(self.subshells))
            print('\n***************************\n')
            print(str1.format(self.excluded_subshells))



    def exp_parameters(self,E0,beta,alpha,beta_max = 200.):
        # Docstring listed as Method-2

        self.Ebeam = E0
        self.beta = beta
        self.alpha = alpha
        self.beta_max = beta_max 
        J_eV_conversion = 1.602177E-19
        self.m_ev = m0/J_eV_conversion*c_light**2          #eV/c^2
        #I'm dealing directly with eV, and not keV
        self.gamma = 1 + self.Ebeam * 1E3 / (self.m_ev)    #Egerton - Chapter Section 3.6.2.1
        self.T = self.m_ev * (1 - 1 / self.gamma ** 2) / 2 #Egerton - Chapter Section 3.6.2.1
        
        #So we aren't asked to set this again afterwards
        self.exp_param_setted = True

    
    def autorun_gosSurfaces(self,exp_param, veto_sshell_list = [],Erange = 100.,mesh_p = 250,*args,**kwargs):
        if not all([True if el in self.\
            subshells else False for el in veto_sshell_list]):
            str00 = '\nOne given subshell is not listed'
            str01 = '\nExiting'
            str02 = '\nThe listed subshells are \n{}\nand the given\n{}'
            print(''.join([str00,str01,str02]).\
                format(self.subshells,veto_sshell_list))
            raise NameError
        #2-Excluding the undesired subshells
        self.exclude_subshells(veto_sshell_list)
        #We now can set the experimental parameters and continue
        self.exp_parameters(exp_param[0],exp_param[1],exp_param[2])
        #Calculations
        self.gos_readout()
        self.tab_logqaxa0sq_dict, self.tab_gos_dict = \
        self.axis_management(limiting_angle = self.beta_max)
        #GOS and axes delimited by convergence angle
        self.exp_logqaxa0sq_dict, self.exp_gos_dict = \
        self.axis_management(limiting_angle = self.beta)
        self.theoretical_surf = self.q_E_interpolation(\
            self.tab_logqaxa0sq_dict, self.tab_gos_dict,\
            mesh_points = mesh_p)   #Overkill - high number of grid points
        self.beta_surf = self.interpolation_betaCutoff(self.el_subshell,\
            data_dictionary = self.theoretical_surf)
        '''
        self.factor, self.factorized_betacut_surface =\
            self.calculate_fator_F(self.el_subshell,self.theoretical_surf)
        '''
        self.factor, self.factorized_betacut_surface =\
            self.calculate_fator_F(self.el_subshell,self.theoretical_surf)
        

    def autorun_gosCurves(self,exp_param, veto_sshell_list = [],\
        Erange = 100., surfaceTOuse = 'F-factor',ret_gos_curve = True,\
        mesh_p = 250,*args,**kwargs):
        
        if not all([True if el in self.\
            subshells else False for el in veto_sshell_list]):
            str00 = '\nOne given subshell is not listed'
            str01 = '\nExiting'
            str02 = '\nThe listed subshells are \n{}\nand the given\n{}'
            print(''.join([str00,str01,str02]).\
                format(self.subshells,veto_sshell_list))
            return
        #2-Excluding the undesired subshells
        self.exclude_subshells(veto_sshell_list)
        #We now can set the experimental parameters and continue
        self.exp_parameters(exp_param[0],exp_param[1],exp_param[2])
        #Calculations
        self.gos_readout()
        self.tab_logqaxa0sq_dict, self.tab_gos_dict = \
        self.axis_management(limiting_angle = self.beta_max)
        #GOS and axes delimited by convergence angle
        self.exp_logqaxa0sq_dict, self.exp_gos_dict = \
        self.axis_management(limiting_angle = self.beta)
        self.theoretical_surf = self.q_E_interpolation(\
            self.tab_logqaxa0sq_dict, self.tab_gos_dict,\
            mesh_points = mesh_p)   #Overkill - high number of grid points
        self.beta_surf = self.interpolation_betaCutoff(self.el_subshell,\
            data_dictionary = self.theoretical_surf)
        
        self.factor, self.factorized_betacut_surface =\
            self.calculate_fator_F(self.el_subshell,self.theoretical_surf)
        '''
        self.factor, self.factorized_betacut_surface =\
            self.calculate_fator_F(self.el_subshell,self.beta_surf)
        '''
        #Now the integrations
        self.int_curve_gos_q = dict()
        self.x_section = dict()
        #We create the correct key names and we get the data values
        if surfaceTOuse == 'F-factor':
            for el in self.subshells:
                key_el =  '_'.join([self.element,el])
                self.int_curve_gos_q[key_el] =\
                self.integration_X_section(self.factorized_betacut_surface,\
                    key_el,Erange,False)
        elif surfaceTOuse == 'beta-cut':
            for el in self.subshells:
                key_el =  '_'.join([self.element,el])
                self.int_curve_gos_q[key_el] =\
                self.integration_X_section(self.beta_surf,\
                    key_el,Erange,False)
        elif surfaceTOuse == 'theoretical':
            for el in self.subshells:
                key_el =  '_'.join([self.element,el])
                self.int_curve_gos_q[key_el] =\
                self.integration_X_section(self.theoretical_surf,\
                    key_el,Erange,False)
        else:
            print('No valid surface reference given - NO surface returned')
            print('Valid references : {}'.format(['F-factor','beta-cut','theoretical']))
        #And now, the final options ... printout and return
        if ret_gos_curve:
            return self.int_curve_gos_q
        else:
            return

    def calculate_fator_F(self,lista_sshells = None,\
        reference_data = None,beta_corrected_surface = None,\
        *args,**kwargs):
        #Docstring listed as Method-14
        if not reference_data:
            reference_data = dict()
        if not beta_corrected_surface:
            #Let's calculate it - we need it, with the newly added alpha+beta condition
            beta_corrected_surface = self.interpolation_betaCutoff(self.el_subshell,\
            data_dictionary = self.theoretical_surf,factor = True)
        if not lista_sshells:
            lista_sshells = []
        factor = dict()
        factorized_surface = dict()
        for sshell in lista_sshells:
            eax = reference_data[sshell]['axis']['Eax']
            #This Qax is log((qa0)**2), not q 
            qax = reference_data[sshell]['axis']['Qax']
            factor[sshell] = dict()
            factor[sshell]['axis'] = reference_data[sshell]['axis']
            factor[sshell]['data'] =\
            factor_geom_F(self.T,eax,qax,self.alpha,self.beta,\
                self.gamma,self.m_ev)

            factorized_surface[sshell] = dict()
            #Now the factorized surface
            factorized_surface[sshell]['axis'] =\
            beta_corrected_surface[sshell]['axis']

            factorized_surface[sshell]['data'] =\
            beta_corrected_surface[sshell]['data'] * factor[sshell]['data']
        return factor, factorized_surface

    

    def integration_X_section(self,GOS_data_dict,sshell,\
        energy_range = 100,integrate = False,*args,**kwargs):
        #Docstring listed as Method-15
        curve_gos_E = dict()
        x_section = dict()
        #locating indices in the E axis
        constant = 4. * np.pi * a0**2 * R**2 *1E28 / self.T


        tot_Eax = GOS_data_dict[sshell]['axis']['Eax']
        qs = GOS_data_dict[sshell]['axis']['Qax']
        curve_gos_E['gos'] = np.zeros((tot_Eax.shape[0],))
        for j,el in enumerate(GOS_data_dict[sshell]['data'][:,]):
            #This suposes that both qs and Energy axes are of the same shape
            curve_gos_E['gos'][j] = simpson(el,qs)
        curve_gos_E['gos'] *= constant
        curve_gos_E['gos'] /= tot_Eax
        curve_gos_E['Eax'] = tot_Eax
        #In case of demanding a numerical integration in an energy range
        if integrate:
            ei = self.onsets[sshell]
            ef = ei + energy_range
            id_ei = np.searchsorted(curve_gos_E['Eax'],ei)
            id_ef = np.searchsorted(curve_gos_E['Eax'],ef)
            x_section['E_limits'] = ((ei,ef),(id_ei,id_ef))
            x_section['value'] = simpson(curve_gos_E['gos'][id_ei:id_ef],\
                curve_gos_E['Eax'][id_ei:id_ef])
            return curve_gos_E, x_section
        else:
            return curve_gos_E


    def gos_readout(self,*args,**kwargs):
        # Docstring listed as Method-5
        self.gos_subshells = dict()
        self.el_subshell = list()
        self.onsets = dict()
        #self.tabulated_val = dict()
        self.factor_subshell = dict()
        #Getting the tabulated dict once again
        elementos = elements[self.element]\
        ['Atomic_properties']['Binding_energies']
        #self.el_subshell_qint = dict()
        for sshell in self.subshells:
            str_name = '_'.join([self.element,sshell])
            self.factor_subshell[str_name] = elementos[sshell]['factor']
            self.el_subshell.append(str_name)
            read_results = gos_reader(self.element,sshell)
            claves = ['qaxis','Eaxis','gos_array']
            self.onsets[str_name] = read_results[-1]
            self.gos_subshells[str_name] =\
                dict([el for el in zip(claves,read_results[:-1])])

    def axis_management(self,limiting_angle,*args,**kwargs):
        # Docstring listed as Method-6
        #angle = 0.5 * limiting_angle * 1E-3
        angle = limiting_angle * 1E-3
        gos_dict   = dict()
        logqaxis_dict = dict()
        for el in self.el_subshell:
            gos_dict[el] = list()
            logqaxis_dict[el] = list()
            factor = self.factor_subshell[el]
            for i,energy in enumerate(self.gos_subshells[el]['Eaxis']):
                qa0sqmin,qa0sqmax = self.qa0sq_min_max(energy,\
                    self.T,self.gamma,self.m_ev,angle)
                qmin = qa0sqmin ** 0.5 / a0
                qmax = qa0sqmax ** 0.5 / a0
                #Extrapolation routine, evaluates if the tabulated
                #values are withing the physical theoretical limits 
                #print(self.gos_subshells[el]['gos_array'][i,:].size,\
                #    self.gos_subshells[el]['qaxis'].size)

                #TODO Correct the intepolation - use numpy slicing methods.....
                qaxis, gos = interpolator_q_gos(cp.deepcopy(self.gos_subshells[el]['gos_array'][i,:]),\
                    cp.deepcopy(self.gos_subshells[el]['qaxis']), Ei = i, qmin  = qmin, qmax = qmax)
                #print(qaxis.size,gos.size)
                logsqa0qaxis = np.log(np.square((a0 * qaxis)))
                logqaxis_dict[el].append(logsqa0qaxis)
                #We need to take into account the factor of the subshell
                gos_dict[el].append(gos * factor)
                #gos_dict[el].append(gos)
        return logqaxis_dict, gos_dict

    def qa0sq_min_max(self,energy,T,gamma,m_ev,lim_angle,*args,**kwargs):
        # Docstring listed as Method-7
        extra_f = (energy ** 3) / (8 * gamma ** 3* R * T ** 2)
        qa0sq_min = (energy ** 2) / (4 * R * T)  #Egerton (3.144)
        #qa0sq_min = (energy ** 2) / (4 * R * T) + extra_f  #Egerton (3.144)

        k0a0sq = (T/R) / (1 - 2 * T/m_ev)                            #Egerton (3.140)
        
        k1a0sq = k0a0sq - (energy/R) * (gamma - energy / (2*m_ev))   #Egerton (3.139)
        qa0sq_max = qa0sq_min + 4 *np.sqrt(k0a0sq * k1a0sq) *\
            (np.sin(lim_angle / 2)) ** 2                             #Egerton (3.146 - 3.147)

        return qa0sq_min , qa0sq_max

    def q_E_interpolation(self,q_arr_list,gos_arr_list,mesh_points = 100.):
        # Docstring listed as Method-8
        gos_data = dict()
        q_nm = int(mesh_points)
        Qintermedium = dict()
        #for i,el in enumerate(self.gos_subshells):
        for el in self.gos_subshells:
            #initializing the data storage solutions
            Qintermedium[el] = list()
            gos_data[el] = dict()     #Dictionary inside dictionary
            gos_data[el]['axis'] = dict()
            #Initializing memory data storage
            gos_data[el]['data'] = np.zeros((q_nm,q_nm))
            #max and min vals - physical limitations
            min_val,max_val = self.max_min_Qvalues(q_arr_list[el])
            gos_data[el]['axis']['Qax'] = np.linspace(min_val,max_val,q_nm)
            #Interpolation on the Q axis
            for j,gos_el in enumerate(gos_arr_list[el]):
                #The extrapolate keyword is responsible for some of 
                # the linear deviations we may see at the end ... 
                temp_q_function = interpolate.interp1d(\
                                q_arr_list[el][j],\
                                gos_el,kind = 1,\
                                #bounds_error = False,\
                                fill_value = 'extrapolate',)
                Qintermedium[el].append(temp_q_function(\
                gos_data[el]['axis']['Qax']))
            #Interpolation on energy axis
            E_axis0 = self.gos_subshells[el]['Eaxis']
            gos_Q0 = np.array(Qintermedium[el])
            gos_data[el]['axis']['Eax'] = \
                np.linspace(E_axis0[0],E_axis0[-1],q_nm)
            for k in range(q_nm):
                '''temp_E_function = (interpolate.interp1d(E_axis0,\
                                gos_Q0[:,k], kind = 'linear',\
                                #bounds_error = False,\
                                fill_value = 'extrapolate',))
                '''
                temp_E_function = interpolate.InterpolatedUnivariateSpline(\
                                E_axis0, gos_Q0[:,k], k = 3,\
                                ext = 'zeros',)
                gos_data[el]['data'][:,k] = \
                temp_E_function(gos_data[el]['axis']['Eax'])
        return gos_data

    def max_min_Qvalues(self,lista_array = None):
        # Docstring listed as Method-9
        if not lista_array:
            return
        mini_lista = [np.amin(el) for el in lista_array]
        maxi_lista = [np.amax(el) for el in lista_array]
        return min(mini_lista),max(maxi_lista)

    def interpolation_betaCutoff(self,subsll_list = list(),\
        data_dictionary = dict(),factor = False,*args,**kwargs):
        # Docstring listed as Method-12
        
        new_dictionary = dict()
        if factor:
            #this is for the case of calculating the surface for the factor
            #Where the integration limit is done afterwards up to alpha+beta,
            #And it is the effect of the geometric factor over the df/dsigdE
            #what get's the upper limit
            ang = self.beta+self.alpha
            #ang = self.beta
        else:
            ang = self.beta
        if not all(el in self.el_subshell for el in subsll_list):
            str0 = 'Not all the elements coincide with ilsted elementes\n'
            str1 = 'Check if the list introduced is correct.\n'
            str2 = 'Introduced list : {}\n'
            str3 = 'Listed elements : {}\n'

            return print(''.join([str0,str1,str2,str3]).\
                        format(subsll_list,self.el_subshell))

        else:
            for el in subsll_list:
                eax = data_dictionary[el]['axis']['Eax']
                qax = data_dictionary[el]['axis']['Qax']

                #Set_up_new_dictionary
                new_dictionary[el] = dict()
                new_dictionary[el]['data'] =\
                np.zeros(data_dictionary[el]['data'].shape)
                new_dictionary[el]['axis'] = dict()
                new_dictionary[el]['axis']['Eax'] = eax
                new_dictionary[el]['axis']['Qax'] = qax

                lnqa0sq_cutoff_max = np.zeros(eax.shape)
                lnqa0sq_cutoff_min = np.zeros(eax.shape)
                for i,energy_val in enumerate(eax):
                    qa0_minmax_temp = self.qa0sq_min_max(energy_val,\
                            self.T,self.gamma,self.m_ev,ang*1E-3)

                    #lnqa0sq_cutoff_max[i] = np.log(qa0_minmax_temp[-1]**2)
                    #lnqa0sq_cutoff_min[i] = np.log(qa0_minmax_temp[0]**2)
                    lnqa0sq_cutoff_max[i] = np.log(qa0_minmax_temp[-1])
                    lnqa0sq_cutoff_min[i] = np.log(qa0_minmax_temp[0])
                    
                #print(lnqa0sq_cutoff_max)
                #print(lnqa0sq_cutoff_min)
                sorted_min = np.searchsorted(qax,lnqa0sq_cutoff_min)
                #print(sorted_min)
                sorted_max = np.searchsorted(qax,lnqa0sq_cutoff_max)
                #print(sorted_max)
                for j in range(sorted_max.shape[0]):
                    i_min = sorted_min[j] 
                    i_max = sorted_max[j]
                    new_dictionary[el]['data'][j,i_min:i_max] =\
                    data_dictionary[el]['data'][j,i_min:i_max]
            self.pruebilla = cp.deepcopy(new_dictionary)
            return new_dictionary

    '''
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                        DOCUMENTATION - DOCSTRINGS
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


    To keep all the above code as compact as possible, the docstrings for the
    methods are listed bellow, categorized with the numbers listed bellow
    the statements

    '''


    # Method-1
    exclude_subshells.__doc__ =\
    '''
    This method is valid to limit the number of subshells on the
    computations.

    Parameters
    ----------
    lista = list(). 
        List of the subshells we want to exclude from
        the computations. Default: list()
        The format of the strings for subshells must only
        include the subshell designation (i.e. ['M5','M4']) 

    '''

    # Method-2
    exp_parameters.__doc__ =\
    '''
    Method to get the parameters for the limit calculations
    for the transfered momentum.

    Parameters
    ----------
        E0 = float(). Beam energy (keV).
        beta = float(). Collection semiangle (mrad).
        alpha = float(). Convergence semiangle (mrad).


        beta_max = value for an extremely large aperture that is
                    set to plot the whole bethe surface without
                    aperture limitations

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%    
    DEFINITION of parameters depending on the incident beam
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        Mass of electron (m_ev) in eV/c^2
        Relativistic gamma (unitless)
        gamma = (1 - (v/c)**2) ** (-1/2)

        From Egerton 3.134 -  conservation of energy
        W = gamma * m0 * c**2 = E0 +  m0 * c**2
       *thus

     !! gamma = 1 + E0/(m0 * c**2)
      * Carefully selecting mass units en eV/c^2,
      * we can cancell out c**2 in the denominator

        Efective incident energy - Egerton section 3.6.2.1
        T = m0 * v**2 / 2                          thus
     !! T = 0.5 * m0 * (1 - 1 / gamma**2) * c**2

      **Taking into account the units is important
        c**2 is cancelled out if the mass is expresed
        in eV/c^2
    '''

    #Method-5
    gos_readout.__doc__ =\
    '''
    Method to read the files, and prepare data for processing.
    '''

    #Method-6
    axis_management.__doc__=\
    '''
    This method serves to plot the Bethe surface
    without the inference of experimental parameters
    other than the incident beam energy. That way
    we have a tool to decide which apertures could
    be used in an experimental setup

    Paramerters:
    --------------
    limiting_angle = float() - angle in mrad
        Angle for the maximum allowed scatt.
        This allow to evaluate theoretical and
        experimental (angle limited) Bethe
        surfaces. Given in mrad

    Return:
    -------------
    logqaxis_dict = dict()
        Dictionary, where the keys are the
        subshells names under evaluation.
        This dict() contains lists of np.arrays()
        with the values of log((q_ax * a0) ** 2)
        for each of the ionization energies evaluated

    gos_dict      = dict()
        Dictionary, where the keys are the
        subshells names under evaluation.
        This dict() contains lists of np.arrays()
        with the values of GOS for the 'q' evaluated


    Considerations
    --------------
    This is taken primarly from integrateq in hyperspy

    The reason to copy here this code, is that we want
    to extract bethe surfaces and integrate on a
    different way to that programed in hyperspy - and also
    be in control of the whole calculations 

    Hyperspy fails in the calculations of X-sections, mainly
    due to missmanagement of angles for the q_max and errors
    on physical constant management
    '''


    # Method-7
    qa0sq_min_max.__doc__ =\
    '''
    This method allows for a compact and repeateable calculation
    of the (qa0)^2 maximum and minimum allowed by relativistic
    kinematic considerations, and energy conservation
    %%%%%%
    Egerton chapter 3 - 3.6.2
    %%%%%%

    Parameters
    ----------
    energy = float()
        Value for the electron energy loss

    T = float()
        Value of the effective kinetic energy
        It is calcuated somewhere else

    gamma = float()
        Relativistic gamma coefficient
    
    m_ev = float()
        electron mass in eV/ c**2 
    
    lim_angle = float()
        limiting angle, given usually by the collection
        aperture angle defined by the electron EELS detector
        and the camera length in the experiment

    Returns
    ----------

    qa0sq_min = float()
                value of (qa0)**2 minimum
    qa0sq_max = float()
                value of (qa0)**2 maximum
    '''

    # Method-8  
    q_E_interpolation.__doc__ =\
    '''
    Method to interpolate new values of GOS for extended
    resolution on the q and E axis.

    Parameters
    ----------
    q_arr_list = dict().
        dictionary containing for each subshell under 
        evaluation the data for the log(a0q)**2 axis
        It is ordered as a list of np.array() for each 
        energy loss tabulated.  

    gos_arr_list = dict().
        dictionary containing for each subshell under 
        evaluation the data for the gos values in each 
        point of the log(a0q)**2 axis tabulated
        It is ordered as a list of np.array() for each 
        energy loss tabulated and log(qa0)**2

    Returns
    ---------
    gos_data  = dict().
        dictionary containing all the data for a 3D
        representation of the Bethe surface for all and
        each of the subshells selected by the program to
        be evaluated 

    '''

    # Method-9
    max_min_Qvalues.__doc__ =\
    '''
    Method that, given a list of arrays, gets the maximum and
    minimum value.


    Now the max and min values to interpolate
    in the q-axis.
    The existing problem with the current data
    base, is that it doesn't allow for a 
    regular grid to be shaped. Thus this trick is
    used to localize the max val in ALL of the 
    arrays

    Parameters
    ----------
    lista_array = list(). List containing arrays with the qaxis
                        for each of constant-energy curves
    '''

    
    # Method-12
    interpolation_betaCutoff.__doc__=\
    '''
    Method for an initial inspection of the effect of an existing
    collection aperture
    The data intended in this case is the interpolated data.
    The idea is to interpolate with the whole set of theoretical
    values available, to avoid artefacts, and then cutoff in a 
    'hard' way by calculating in the new energy axis the q_max_min

    Parameters
    ----------
    data_dictionary = dict()
        Dictionary containing the gos data, and the 
        energy and q axes parametrizations
        It is intended to be a dictionary with the already
        interpolated data

    subsll_list     = list()
        List of strings with the subshell to be calculated.
        This way we can select how many subshells we want
        to analyze experimentally

    '''
    # Method-14

    calculate_fator_F.__doc__ =\
    '''
    Method to calcualate the geometric correction factor for each 
    subshell considered. It calles the function (writen elsewhere) 
    geometric_X_correlation_Correction_function, to include the effects
    of having a finite convergence angle alpha in the range of the
    finite collection angle beta

    Parameters
    -----------

    lista_sshells = list()
        List of strings for the subshells we want to compute
        Default, empty list

    reference_data = dict()
        Dictionary containing the data of gos, q-axis and E-axis for each
        subshell under investigation
        It must contain the keys:
            ['element_subshell']['data']
            ['element_subshell']['axis']['Eax']
            ['element_subshell']['axis']['Qax']

    beta_corrected_surface = dict()
        Dictionary containing the data of the surface where the beta 
        cutoff has already been conducted
        Default = None
        If we do not specify a dictionary, the correction will be applied to
        the theoretical data reference

    Return
    --------
    factor : dict()
        Dictionary, where the keys are the subshell strings under consideration
        and each key contains a np.array with the data for the correction factor

    factorized_surface : dict()
        Dictionary with the same keys as the reference_data or the 
        beta_corrected_surface, depending on the input for the function.
        The keys are:
            [subshell string]['data']        = np.array
            [subshell string]['axis']['Qax'] = np.array
            [subshell string]['axis']['Eax'] = np.array


    '''

    #Method-15
    integration_X_section.__doc__ =\
    '''
        Method to perform the integration of the x_section, which at
        the end means integrate the area under the surface for a given
        energy range. The limits on the qs are already taken into account
        when calculating the surfaces, and so the calculations are not
        repeated

        Parameters
        ----------
        energy_range = float() 
            value for the energy range to be integrated
            Default = 100 eV
            
        GOS_data_dict = dictionary with the GOS data to be integrate
            dictionary with the data of GOS (generallized oscilaltor strenth)
            to be integrated. It must contain the keys:

            [sshell]['data']        = np.array
            [sshell]['axis']['Qax'] = np.array
            [sshell]['axis']['Eax'] = np.array

        sshell = str()
            subshell string trings for the subshells we want to compute.

        integrate = bool()
            Boolean comand that states if we want to compute the integrated
            in E X-section in the energy range specified.
            Default = False

        Return
        ---------

        curve_GOS_E = dict()
            Integrated in q GOS, df/dE, giving the typic look of the curve in
            DM_suite
            Keys:
            ['gos'] = np.array()
            ['Eax'] = np.array()
            


        x_section = dict()
            Dictionary containing the float values of the integrated cross sections
            for each subshell in the list sshell, and the initial E0 and final E1
            for the energy integration range
            Keys:
            ['value'] = float()
            ['E_limits'] = tuple()
        '''
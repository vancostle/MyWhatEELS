import copy as cp
import xarray as xr
import numpy as np
#Hyperspy **************************************
from Library.Database.elements import elements
#lmfit *****************************************
from lmfit import Model
from lmfit.models import PowerLawModel
from lmfit.models import GaussianModel,LorentzianModel,PseudoVoigtModel,SplitLorentzianModel
#Local import *********** My stuff
from Library.cross_sections import bethe_surface_calculations
#Scipy **********************
from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.ndimage import gaussian_filter1d
#Possible future imports
'''
import panel as pn4
import holoviews as hv
from holoviews import streams, opts, dim
from holoviews.streams import Selection1D
from holoviews.streams import Stream,param
import pandas as pd
import bokeh, param, lmfit
'''
class NLLS_fitting():
    def __init__(self,data):
        """NLLS_fitting is initialized with an external dataset
        This init function deals with the extenal data, not the elements
        in the model. those are added afterwards

        Args:
            data (xarray): Contains the data for the whole spectra.
        """
        self.ds = data
        self.fitting_elements = dict()    #Will be later used
        self.bethe = dict()
        self.bethe_extra = dict()  #Better to have a second object, to avoid overwritting
        self.gos_curves = dict()
        self.scaling_factor = dict()
        self.models_components = dict()
        self.models = dict()
        self.pars = dict()
        self.valid_types_comps = ['gaussian','lorentzian','pseudovoigt','splitlorentzian']
        self.ref_spectra = dict()
        self.ref_results = dict()
        self.areas = dict()
        self.results = dict()
        self.results_modified = dict()
        self.results_final_modified = dict() #The final results including the modifications of rerun
        self.ref_matrices = dict()
        self.red_chi_sqr = dict()
        self.residuals = dict()   
        self.best_fits = dict()
        self.param_values = dict()
        self.param_errRel = dict()
        self.component_eval = dict()
        self.extra_modified_model_components = dict()
        self.parameters_modified = dict()
        self.models_modified = dict()
        #For the rerun fittings - adjusting the first fit
        self.param_values_re = dict()
        self.param_errRel_re = dict()
        self.component_eval_re = dict()
        self.best_fits_re = dict()
        self.residuals_re = dict()
        self.red_chi_sqr_re = dict()
        #For the anaylsis functions
        self.ref_components = {'multi':dict(),'rerun':dict()}
        # For later quantification
        self.x_section_fullSet = dict()
        self.scalings_fullSet = dict()
        #Let's begin the initialization now
        try:
            #If the given data does not contain this labels, the program can't continue
            self.Eloss = data.Eloss.values
            self.spec = data.ElectronCount.values
            #E0,beta,alpha
            self.exp_param = [self.ds.attrs['beam_energy'],\
                self.ds.attrs['collection_angle'],\
                self.ds.attrs['convergence_angle']] 
        except AttributeError:
            msg0 = 'The data given is not in the supported format'
            msg1 = 'A xarray dataset is expected, with the elements:'
            msg2 = '1- data.Eloss - For the Energy loss axis'
            msg3 = '2- data.ElectronCount - For the actual electron counts'
            msg4 = 'RE-RUN the class from the beginning, using a xarray'
            print('\n'.join([msg0,msg1,msg2,msg3,msg4]))
            return
        else:
            #Let's check if we have a single spectra, spectrum line or spectrum image
            #1- Single spetrum - 'single'
            #2- Spectrum line  - 'SLine'
            #3- Spectrum image - 'SImage'
            xlen = data.x.values.size
            ylen = data.y.values.size
            if xlen == ylen == 1:
                self.im_type = 'single'
                self.initial_reference_spectra = self.ds.ElectronCount.data
            elif xlen!=ylen and any([i==1 for i in [xlen,ylen]]):
                self.im_type = 'SLine'
                if xlen == 1:
                    sli0 = int(1*ylen/3)
                    sli1 =  int(2*ylen/3)
                    self.initial_reference_spectra = self.ds.isel(x = 0,y = slice(sli0,sli1)).\
                        sum('y').ElectronCount.values / max(sli1-sli0,1)
                else:
                    sli0 = int(1*xlen/3)
                    sli1 =  int(2*xlen/3)
                    self.initial_reference_spectra = self.ds.isel(y = 0,x = slice(sli0,sli1)).\
                        sum('x').ElectronCount.values / max(sli1-sli0,1)
                    
            else:
                self.im_type = 'SImage'
                slix0 = int(2*xlen/5)
                slix1 = int(3*xlen/5)
                sliy0 = int(2*ylen/5)
                sliy1 = int(3*ylen/5)
                self.initial_reference_spectra = self.ds.sel(x = slice(slix0,slix1),y = slice(sliy0,sliy1)).\
                        sum(dim = ['x','y']).ElectronCount.data / max((slix1-slix0)*(sliy1-sliy0),1)                
        #In the program, a new reference spectra can be selected, but to begin with ...

    def add_element(self,element,sshells):
        """This is the method to add elements and select
        subshell that will be computed

        Args:
            element (str): Name of the element added (e.g. Ce,Cd,Li,...)
            sshells (list): list of subshells that will we added to the GOS calculation
        """
        #Correction, in case of the user letting out bounded sshells e.g. M5 always with M4 ...
        for ssh in sshells:
            #Only 4 possible corrections. Having 5 and not 4, having 3 and not 2 and viceversa on both.
            if ssh[-1] == '5' and ''.join([ssh[0],'4']) not in sshells:
                sshells.append(''.join([ssh[0],'4']))
            elif ssh[-1] == '4' and ''.join([ssh[0],'5']) not in sshells:
                sshells.append(''.join([ssh[0],'5']))
            elif ssh[-1] == '3' and ''.join([ssh[0],'2']) not in sshells:
                sshells.append(''.join([ssh[0],'2']))
            elif ssh[-1] == '2' and ''.join([ssh[0],'3']) not in sshells:
                sshells.append(''.join([ssh[0],'3']))
            else:
                pass
        self.fitting_elements[element] = sshells
        self.bethe[element] = bethe_surface_calculations.bethe_surface(element) #Already considers both always
        

    def ready_elements(self,type_surface = 'theoretical',extension = True,max_Eloss = 3000,mesh_p = 250):
        """Simple function that tells the program to calculate now the GOS curves

        Args:
            type_surface (str, optional): Select the GOS curve to return. Defaults to 'theoretical'.
                There are 3 options:
                1 theoretical (from purely theoretical Bethe surface calculations)
                2 beta-cut    (Cuts the theoretical in a hard limit by beta*)
                3 F-factor    (Cuts the theoretical by another surface - beam geometry considerations)
            extension (bool, optional) : Allows for an extrapolation of points further from the edge in 
                the data base for high energy losses.
            max_Eloss (float, optional) : The Energy Loss value set as limit for the optional extrapolation.
        """
        pwlaw_A = 1        #For the extension model (Powerlaw) amplitude
        pwlaw_exp = -2     #For the extension model (Powerlaw) exponent
        fromonset = 100    #Distance from onset to start the powerlaw
        for el in self.fitting_elements.keys():
            veto_list = [elem for elem in self.bethe[el].subshells if elem not in self.fitting_elements[el]]
            gos_arrays = self.bethe[el].autorun_gosCurves(exp_param=self.exp_param,\
                veto_sshell_list=veto_list,printout_review = False,\
                surfaceTOuse = type_surface,mesh_p = mesh_p)
            self.gos_curves[el] = dict()
            self.scaling_factor[el] = dict()
            #We use UnivariateSplines for the GOS function calculation from arrays
            for sshell in self.fitting_elements[el]:
                if extension:
                    #Usually, 100eV from the onset we are in a Powerlaw-like curve
                    #far from the ELNES
                    ''' Legacy - this part was used before...but caused problems with some edges
                    inilen = gos_arrays['_'.join([el,sshell])]['Eax'].size
                    idx = np.searchsorted(gos_arrays['_'.join([el,sshell])]['Eax'],\
                        gos_arrays['_'.join([el,sshell])]['Eax'][0]+fromonset)
                    #We are using lmfit, exceptionally fast and accurate
                    mod = PowerLawModel()
                    pars = mod.make_params(amplitude = pwlaw_A, exponent = pwlaw_exp)
                    pars['exponent'].min = -3
                    pars['exponent'].max = -1.5
                    mod_res = mod.fit(gos_arrays['_'.join([el,sshell])]['gos'][idx:],\
                        params = pars, x = gos_arrays['_'.join([el,sshell])]['Eax'][idx:])
                    extra_E = np.linspace(gos_arrays['_'.join([el,sshell])]['Eax'][idx+1],\
                        max_Eloss,int(inilen-idx) * 2)
                    gos_arrays['_'.join([el,sshell])]['gos'] =\
                        np.append(gos_arrays['_'.join([el,sshell])]['gos'][:idx],\
                        mod_res.eval(x = extra_E))
                    gos_arrays['_'.join([el,sshell])]['Eax'] =\
                        np.append(gos_arrays['_'.join([el,sshell])]['Eax'][:idx],\
                        extra_E)
                    '''
                    #Improved version
                    #inilen = gos_arrays['_'.join([el,sshell])]['Eax'].size
                    step_E = gos_arrays['_'.join([el,sshell])]['Eax'][1] -\
                        gos_arrays['_'.join([el,sshell])]['Eax'][0]
                    E_bckg_0 = gos_arrays['_'.join([el,sshell])]['Eax'][-1] - 50
                    if E_bckg_0 < gos_arrays['_'.join([el,sshell])]['Eax'][0] + fromonset:
                        E_bckg_0 = gos_arrays['_'.join([el,sshell])]['Eax'][0] + fromonset
                    else:
                        pass
                    idx = np.searchsorted(gos_arrays['_'.join([el,sshell])]['Eax'],E_bckg_0)
                    #We are using lmfit, exceptionally fast and accurate
                    mod = PowerLawModel()
                    pars = mod.make_params(amplitude = pwlaw_A, exponent = pwlaw_exp)
                    pars['exponent'].min = -3
                    pars['exponent'].max = -1.5
                    mod_res = mod.fit(gos_arrays['_'.join([el,sshell])]['gos'][idx:],\
                        params = pars, x = gos_arrays['_'.join([el,sshell])]['Eax'][idx:])
                    extra_E = np.arange(gos_arrays['_'.join([el,sshell])]['Eax'][idx+1],\
                        max_Eloss,step_E)
                    gos_arrays['_'.join([el,sshell])]['gos'] =\
                        np.append(gos_arrays['_'.join([el,sshell])]['gos'][:idx],\
                        mod_res.eval(x = extra_E))
                    gos_arrays['_'.join([el,sshell])]['Eax'] =\
                        np.append(gos_arrays['_'.join([el,sshell])]['Eax'][:idx],\
                        extra_E)
                '''
                self.orden_listas.append('_'.join([el,sshell]))
                self.lista_gos.append(InterpolatedUnivariateSpline(gos_arrays['_'.join([el,sshell])]['Eax'],\
                    gos_arrays['_'.join([el,sshell])]['gos'], k =3,ext = 1))
                self.lista_factor.append(self.bethe[el].factor_subshell['_'.join([el,sshell])])
                '''
                '''
                #Newly added
                if sshell == 'L1': clave = 'L11'
                else: clave = sshell
                '''
                
                self.gos_curves[el][sshell] =\
                    InterpolatedUnivariateSpline(gos_arrays['_'.join([el,sshell])]['Eax'],\
                    gos_arrays['_'.join([el,sshell])]['gos'], k =3,ext = 1)
                #This should be somewhere else, but as the Bethe class was alreday done ...
                self.scaling_factor[el][sshell] = self.bethe[el].factor_subshell['_'.join([el,sshell])]


    def ready_full_set_Xsections(self,elementos = [],extension = True,max_Eloss = 3000):
        """Simple function that tells the program to calculate now the GOS curves for the whole
        set of possible subshells of elements in the program - for later quantification.
        Still...we can veto some of the edges, if it results that their onsets are outside
        the enregy range under consideration  to speed up calculations

        Args:
            elementos (list, optional): The elements to be considered. List that needs to be specified
                from the outside 
            extension (bool, optional) : Allows for an extrapolation of points further from the edge in 
                the data base for high energy losses.
            max_Eloss (float, optional) : The Energy Loss value set as limit for the optional extrapolation.
        """
        #This will make the calculations for all the subshells, no veto
        for el in elementos:
            self.bethe_extra[el] = bethe_surface_calculations.bethe_surface(el) 
        pwlaw_A = 1        #For the extension model (Powerlaw) amplitude
        pwlaw_exp = -2     #For the extension model (Powerlaw) exponent
        fromonset = 100    #Distance from onset to start the powerlaw
        lista_possibilities = ['theoretical','beta-cut','F-factor']
        Emin = self.ds.Eloss.values[0]
        Emax = self.ds.Eloss.values[-1]
        #Some caution here- if the main_feature of the edge on the onset is removed,\
        #the second will be removed as well, and if it stays, teh second stays as well
        self.veto_dictio = dict()
        for el in elementos:
            self.veto_dictio[el] = list()
            for ssh in self.bethe_extra[el].subshells:
                ons = elements[el]['Atomic_properties']\
                    ['Binding_energies'][ssh]['onset_energy (eV)']
                if (ons > Emax or ons < Emin) and \
                not any([num_min in list(ssh) for num_min in ['4','2']]):
                    if any(num_maj in list(ssh) for num_maj in ['5','3']):
                        self.veto_dictio[el].append(ssh)
                        next_ssh = str(int(ssh[-1])-1)
                        self.veto_dictio[el].append(''.join([ssh[0],next_ssh]))
                    else:
                        #This takes care of K and L1 edges
                        self.veto_dictio[el].append(ssh)
                else: pass
                    
        for num_el,sf in enumerate(lista_possibilities):
            self.x_section_fullSet[sf] = dict()
            for el in elementos:
                veto_list = self.veto_dictio[el]
                self.x_section_fullSet[sf][el] = dict()
                if num_el == 0: 
                    self.scalings_fullSet[el] = dict()
                    gos_arrays = cp.deepcopy(self.bethe_extra[el].autorun_gosCurves(exp_param=self.exp_param,\
                        veto_sshell_list = veto_list,printout_review = False,surfaceTOuse = sf))
                else:
                    gos_arrays = cp.deepcopy(self.bethe_extra[el].autorun_gosCurves(exp_param=self.exp_param,\
                        veto_sshell_list = [],printout_review = False,surfaceTOuse = sf))
                #We use UnivariateSplines for the GOS function calculation from arrays
                #We the whole set of possible subshells
                subshell_lista = [ssh for ssh in self.bethe_extra[el].subshells \
                    if ssh not in veto_list]
                for sshell in subshell_lista:
                    if extension:
                        #Usually, 100eV from the onset we are in a Powerlaw-like curve
                        #far from the ELNES
                        inilen = gos_arrays['_'.join([el,sshell])]['Eax'].size
                        idx = np.searchsorted(gos_arrays['_'.join([el,sshell])]['Eax'],\
                            gos_arrays['_'.join([el,sshell])]['Eax'][0]+fromonset)
                        #We are using lmfit, exceptionally fast and accurate
                        mod = PowerLawModel()
                        pars = mod.make_params(amplitude = pwlaw_A, exponent = pwlaw_exp)
                        pars['exponent'].min = -3
                        pars['exponent'].max = -1.5
                        mod_res = mod.fit(gos_arrays['_'.join([el,sshell])]['gos'][idx:],\
                            params = pars, x = gos_arrays['_'.join([el,sshell])]['Eax'][idx:])
                        extra_E = np.linspace(gos_arrays['_'.join([el,sshell])]['Eax'][idx+1],\
                            max_Eloss,int(inilen-idx) * 2)
                        gos_arrays['_'.join([el,sshell])]['gos'] =\
                            np.append(gos_arrays['_'.join([el,sshell])]['gos'][:idx],\
                            mod_res.eval(x = extra_E))
                        gos_arrays['_'.join([el,sshell])]['Eax'] =\
                            np.append(gos_arrays['_'.join([el,sshell])]['Eax'][:idx],\
                            extra_E)
                    self.x_section_fullSet[sf][el][sshell] =\
                        InterpolatedUnivariateSpline(gos_arrays['_'.join([el,sshell])]['Eax'],\
                        gos_arrays['_'.join([el,sshell])]['gos'], k =3,ext = 1)
                    #This should be somewhere else, but as the Bethe class was alreday done ...
                    if num_el == 0:
                        self.scalings_fullSet[el][sshell] =\
                        self.bethe_extra[el].factor_subshell['_'.join([el,sshell])]

    
    def create_components(self,spectrum,default_compo_type = 'gaussian',\
        flex = 'medium',name_area = 'default',excluded_elements = [],soften = None, soften_val = None):
        print(f'Soften {soften}')
        print(f'Soften-val {soften_val}')
        self.models_components[name_area] = dict()
        dictionary = self.models_components
        self.ref_spectra[name_area] = cp.deepcopy(spectrum)
        self.create_continuum_components(dictionary[name_area],excluded_elements,soften,soften_val)
        self.add_ELNES(spectrum,dictionary[name_area],default_compo_type,flex,excluded_elements)
        if name_area == 'default':
            #In case of being in the default configuration i.e. initial config
            ref = np.ones(self.ds.ElectronCount.values.shape[:-1])
            self.add_reference_keyMatrix(ref,name_area='default')
        else: pass #This is done somewhere else for the rest of the possible areas
        #self.create_model(name_area,flex)

    def create_components_and_model(self,spectrum,default_compo_type = 'gaussian',\
        flex = 'medium',name_area = 'default',excluded_elements = [],soften = None,soften_val = None):
        self.models_components[name_area] = dict()
        dictionary = self.models_components
        self.ref_spectra[name_area] = cp.deepcopy(spectrum)
        self.create_continuum_components(dictionary[name_area],excluded_elements,soften, soften_val)
        self.add_ELNES(spectrum,dictionary[name_area],default_compo_type,flex,excluded_elements)
        if name_area == 'default':
            #In case of being in the default configuration i.e. initial config
            ref = np.ones(self.ds.ElectronCount.values.shape[:-1])
            self.add_reference_keyMatrix(ref,name_area='default')
        else: pass
        self.create_model(name_area,flex)

    '''
    def create_continuum_components(self,dictionary,excluded_elements = [],soften = True):
        """Method that creates the Continuum components, based on GOS calculations

        Args:
            dictionary (dict): The dictionary for the potential area that is being added to the model
            excluded_elements (list, optional): Possible elements excluded from the fitting. Defaults to [].
                Serves as a way to exclude certain elements from the fitting on a certain area.
        """
        dob_sshells = ['L','M','N','O']
        sin_sshells = ['K']
        el_lista = [i for i in self.fitting_elements.keys() if i not in excluded_elements]
        for el in el_lista:
            dictionary[el] = dict()
            dictionary[el]['continuum'] = dict()
            for ssh in self.fitting_elements[el]:
                #Now, the pair lookout and lambda function creation
                #We need some sort of closures, so python remembers the local vars at the time of creation
                if ssh[0] in dob_sshells and ssh[-1] == '5':
                    ssh2 = ''.join([ssh[0],'4'])
                    dictionary[el]['continuum'][''.join([ssh[0],'54'])] =\
                    lambda x, A = 1, chem = 0, el = el, ssh = ssh,ssh2 = ssh2:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh]+\
                        self.gos_curves[el][ssh2](x+chem) * self.scaling_factor[el][ssh2])

                elif ssh[0] in dob_sshells and ssh[-1] == '3':
                    ssh2 = ''.join([ssh[0],'2'])
                    dictionary[el]['continuum'][''.join([ssh[0],'32'])] =\
                    lambda x, A = 1, chem = 0, el = el, ssh = ssh,ssh2 = ssh2:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh]+\
                        self.gos_curves[el][ssh2](x+chem) * self.scaling_factor[el][ssh2])
                elif ssh[-1] == '1':
                    #Changes to differenciate the L1 component
                    #Newly added
                    clave = ssh
                    #'{}1'.format(ssh)
                    dictionary[el]['continuum'][clave] =\
                    lambda x, A = 1, chem = 0, el = el, ssh = clave,ssh2 = None:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh])
                elif ssh[0] in sin_sshells:
                    dictionary[el]['continuum'][ssh] =\
                    lambda x, A = 1, chem = 0, el = el, ssh = ssh,ssh2 = None:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh])
                else:
                    #print('else',ssh)
                    pass
        self.initial_constraints_continuum(dictionary)
        '''
    def create_continuum_components(self,dictionary,excluded_elements = [],soften = None,soften_val = None):
        """Method that creates the Continuum components, based on GOS calculations

        Args:
            dictionary (dict): The dictionary for the potential area that is being added to the model
            excluded_elements (list, optional): Possible elements excluded from the fitting. Defaults to [].
                Serves as a way to exclude certain elements from the fitting on a certain area.
        """
        print('inside continuum compos')
        print(f'Soften {soften}')
        print(f'Soften-val {soften_val}')
        dictio_data_soft = dict()
        dob_sshells = ['L','M','N','O']
        sin_sshells = ['K']
        el_lista = [i for i in self.fitting_elements.keys() if i not in excluded_elements]
        for el in el_lista:
            func = None
            dictionary[el] = dict()
            dictionary[el]['continuum'] = dict()
            for ssh in self.fitting_elements[el]:
                #Now, the pair lookout and lambda function creation
                #We need some sort of closures, so python remembers the local vars at the time of creation
                if ssh[0] in dob_sshells and ssh[-1] == '5':
                    clav = ''.join([ssh[0],'54'])
                    ssh2 = ''.join([ssh[0],'4'])
                    if soften:
                        #print('softening')
                        data_c = cp.deepcopy(self.gos_curves[el][ssh](self.Eloss) * self.scaling_factor[el][ssh]+\
                            self.gos_curves[el][ssh2](self.Eloss) * self.scaling_factor[el][ssh2])
                        dat = self._soften_x_sections(data_c,self.Eloss,soften_val).copy()
                        if el not in dictio_data_soft: dictio_data_soft[el] = dict()
                        if clav not in dictio_data_soft[el]: 
                            dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self.Eloss,dat)
                        func = lambda x, A = 1, chem = 0,el = el,clav = clav, : A*(dictio_data_soft[el][clav](x+chem))
                    else:
                        func = lambda x, A = 1, chem = 0,el = el, ssh = ssh,ssh2 = ssh2:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh]+\
                        self.gos_curves[el][ssh2](x+chem) * self.scaling_factor[el][ssh2])
                    dictionary[el]['continuum'][clav] = cp.deepcopy(func)

                elif ssh[0] in dob_sshells and ssh[-1] == '3':
                    clav = ''.join([ssh[0],'32'])
                    ssh2 = ''.join([ssh[0],'2'])
                    if soften:
                        #print('softening')
                        #print('softening')
                        data_c = cp.deepcopy(self.gos_curves[el][ssh](self.Eloss) * self.scaling_factor[el][ssh]+\
                            self.gos_curves[el][ssh2](self.Eloss) * self.scaling_factor[el][ssh2])
                        dat = self._soften_x_sections(data_c,self.Eloss,soften_val).copy()
                        if el not in dictio_data_soft: dictio_data_soft[el] = dict()
                        if clav not in dictio_data_soft[el]: 
                            dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self.Eloss,dat)
                        func = lambda x, A = 1, chem = 0,el = el,clav = clav, : A*(dictio_data_soft[el][clav](x+chem))
                    else:
                        func = lambda x, A = 1, chem = 0,el = el, ssh = ssh,ssh2 = ssh2:\
                        self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh]+\
                        self.gos_curves[el][ssh2](x+chem) * self.scaling_factor[el][ssh2]
                    dictionary[el]['continuum'][clav] = cp.deepcopy(func)

                elif ssh[0] in dob_sshells and ssh[-1] == '1':
                    #Changes to differenciate the L1 component
                    #Newly added
                    clav = ssh
                    ssh2 = None
                    if soften:
                        #print('softening')
                        data_c = cp.deepcopy(self.gos_curves[el][ssh](self.Eloss) * self.scaling_factor[el][ssh])
                        dat = self._soften_x_sections(data_c,self.Eloss,soften_val).copy()
                        if el not in dictio_data_soft: dictio_data_soft[el] = dict()
                        if clav not in dictio_data_soft[el]: 
                            dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self.Eloss,dat)
                        func = lambda x, A = 1, chem = 0,el = el,clav = clav, : A*(dictio_data_soft[el][clav](x+chem))
                    else:
                        func = lambda x, A = 1, chem = 0, el = el, ssh = clave,ssh2 = ssh2:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh])
                    dictionary[el]['continuum'][ssh] = cp.deepcopy(func)

                elif ssh[0] in sin_sshells:
                    clav = ssh
                    ssh2 = None
                    if soften:
                        #print('softening')
                        data_c = cp.deepcopy(self.gos_curves[el][ssh](self.Eloss) * self.scaling_factor[el][ssh])
                        dat = self._soften_x_sections(data_c,self.Eloss,soften_val).copy()
                        if el not in dictio_data_soft: dictio_data_soft[el] = dict()
                        if clav not in dictio_data_soft[el]: 
                            dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self.Eloss,dat)
                        func = lambda x, A = 1, chem = 0,el = el,clav = clav, : A*(dictio_data_soft[el][clav](x+chem))
                    else:
                        func = lambda x, A = 1, chem = 0, el = el, ssh = ssh,ssh2 = ssh2:\
                        A*(self.gos_curves[el][ssh](x+chem) * self.scaling_factor[el][ssh])
                    dictionary[el]['continuum'][ssh] = cp.deepcopy(func)
                else: pass
        self.initial_constraints_continuum(dictionary)

    def _soften_x_sections(self,cont_data,x = None,soften_val = None):
        """
        Method that softens the cross sections calculated to be better integrated in an NLLS fitting
        """
        #if any([el for el in [func,x]]): return
        if soften_val: 
            sigma = 4*soften_val / np.sqrt(np.log(256))
            print(f'val_given - val {soften_val} - sigma - {sigma}')
        else: 
            sigma = 4*1.5 / np.sqrt(np.log(256))
            print('val not given - val {soften_val} - sigma - {sigma}')

        
        #cont_data = func(x)
        #print('calculated soft data')
        soft_data = gaussian_filter1d(cont_data,sigma=sigma)
        #print('applied filter')
        return soft_data

    def add_ELNES(self,spectrum,dictionary,default_compotype = 'gaussian',\
        flex = 'medium',excluded_elements = []):
        """This method creates the ELNES components for the WL in the model

        Args:
            spectrum (np.array) : This is the spectrum used as reference to get
                the initial parameters of the fitting
            default_compotype (str, optional): This parameter controls the type of curve fittet by
                default to the WL component. Defaults to 'gaussian'.
                The allowed options are: gaussian,lorentzian,pseudovoigt,splitlorentzian
            flex (str, optional): This parameter controls the 'flexibility' of the imposed constraints
                to be later used in the model fitting process
        """
        dob_sshells = ['L','M','N','O']
        #sin_sshells = ['K']
        #Initially, let's check if we added info from the zeroloss
        if default_compotype not in self.valid_types_comps:
            print('Invalid type of component')
            return
        lista_el = [i for i in self.fitting_elements if i not in excluded_elements] 
        for el in lista_el:
            dictionary[el]['ELNES'] = dict()
            for ssh in self.fitting_elements[el]:
                #Again, we have everithing labeled by element and subshell
                if ssh[0] in dob_sshells and ssh[-1] != 1:
                    #Case of a valid subshell for possible white line
                    center = self.gos_curves[el][ssh].get_knots()[0]
                    dictionary[el]['ELNES'][ssh] = dict()
                    cen,sigm,amp = self.determine_compo_parameters(spectrum,default_compotype,center)
                    dictionary[el]['ELNES'][ssh]['type_compo'] = default_compotype
                    dictionary[el]['ELNES'][ssh]['center']    = cen
                    dictionary[el]['ELNES'][ssh]['sigma']     = sigm
                    dictionary[el]['ELNES'][ssh]['amplitude'] = amp
                else:
                    pass
        self.initial_constraints_WL(dictionary,constraint_flex = flex)

    def determine_compo_parameters(self,spectrum,compo_type,Eloss_center):
        """This method makes an estimation of the initial parameter values (pre_fit) 
        of a certain component of the model, knowing only the type of component
        and the energy loss (aprox.) of the center for that component

        Args:
            compo_type (str): Type of component to be created/ whose parameters need guessing
                3 categories:
                symetrical-gaussian     : -str- gaussian
                symmetrical-nonGaussian : -str- lorentzian, pseudovoigt
                asymmetrical            : -str- splitlorentzian 
            Eloss_center ([type]): Energy Loss position in which we stimate the center of the component
                e.g. CeM5 - Eloss_center = 884.0 (Ce4+ in non reduced CeO2)
        """
        try:
            #In case of having info from the ZeroLossPeak
            fwhm = self.ds.attrs['fwhm_from_0loss']
        except KeyError:
            #If no ZeroLoss was analysed or included, let's guess
            fwhm      = 1.2 * 4  # Standard ELoss resolution ... around 1.2 eV in NonCorrected non FEG
            #fwhm_min = 0.7 * 2  # Going to Cold_FEG ranges of resolution in non monochromated
            #fwhm_max = 2.5 * 2  # Really badly calibrated acquisition or poor instrumentation 
        finally:
            #Let's analyse the possible cases

            
            e_idx  = np.searchsorted(self.Eloss,Eloss_center) #Positional index E axis
            
            #delta_e = self.Eloss[1]-self.Eloss[1]
            cent = Eloss_center 
            print(self.Eloss[0],self.Eloss[-1],cent,e_idx,self.Eloss.size)

            h_eidx = max(0,spectrum[e_idx])
            if compo_type == 'gaussian':
                sig = fwhm / np.sqrt(np.log(256))                 # fwhm   = 2*np.sqrt(2*log(2)) * sigma
                amp = h_eidx * max(2E-16,sig) * np.sqrt(2*np.pi)  # height = 1/sqrt(2*pi) * A / max(0,sigma)
                return [cent,sig,amp]
            elif compo_type == 'lorentzian':
                sig = fwhm / 2                                    # sigma  = 2*np.sqrt(2*log(2))
                amp = h_eidx * max(2E-16,sig) * np.pi
                return [cent,sig,amp]             # height = 1/pi * A / max(0,sigma)
            elif compo_type == 'pseudovoigt':
                sig = fwhm / 2                                    # sigma  = 2*np.sqrt(2*log(2))
                factor1 = max(2E-16,(sig*np.sqrt(np.pi/np.log(2))))
                factor2 = max(2E-16,(np.pi*sig))
                amp = 2 * h_eidx * factor1 * factor2 / (factor1 + factor2) 
                #As given by lmfit relation if fraction = 0.5
                return [cent,sig,amp]
            elif compo_type == 'splitlorentzian':
                #We start with a symmetric distrib -sigma = sigma_r = fwhm/2
                sig = fwhm / 2                             # fwhm = sigma + sigma_r
                amp = np.pi*h_eidx*max(2E-16,sig*2) / 2    # h = 2*A/pi/max(0,sigma+sigma_r)
                return [cent,sig,amp]
            else:
                print('NO valid component given')
                raise KeyError

    def initial_constraints_continuum(self,dictionary):
        """This method creates the initial values and constrainst used 
        in the WL components. They can always be modified
        At first, all continuum components are initialized the same, but then may
        be changed ... 
        Args:
            dictionary: The dictionary of the area where this method is called
        """ 
        for el in dictionary:
            dictionary[el]['continuum_init_const'] = dict()
            for ssh in dictionary[el]['continuum']:
                dictionary[el]['continuum_init_const'][ssh] = dict()
                dictionary[el]['continuum_init_const'][ssh]['A'] = 1
                dictionary[el]['continuum_init_const'][ssh]['A_min'] = 0
                dictionary[el]['continuum_init_const'][ssh]['vary_A'] = True 
                dictionary[el]['continuum_init_const'][ssh]['chem'] = 0
                dictionary[el]['continuum_init_const'][ssh]['allow_chem'] = False 

    def initial_constraints_WL(self,dictionary,constraint_flex = 'medium'):
        """This method creates the initial constraints used in the WL components. They can always be modified

        Args:
            constraint_flex (str, optional): Controls how strict are the constraints. Defaults to 'medium'.
                Four possible options
                1- 'low' : 
                    center.min|max varies 0.1 % of the center.value (initial)
                    sigma.min|max varies 10 % of the sigma.value (initial)
                2- 'medium': -------------------------------------------------Default
                    center.min|max varies 1 % of the center.value (initial)
                    sigma.min|max varies 75 % of the sigma.value (initial)
                3- 'high':
                    center.min|max varies 5 % of the center.value (initial)
                    sigma.max varies 125 % of the sigma.value (initial)
                    sigma.min = 0
                3- 'maximum': ------------------------------------------------No constraints
                    center.min|max = +-np.inf
                    sigma.max = np.inf
                    sigma.min = 0
                low and medium are recomended. When needed, high may be used as default. maximum is
                probably going to fail in any case-scenario, as the algorithm is unable to converge.
                Amplitude is always varied between 0 (avoid non physical components) and np.inf
        """ 
        #4 elements in the lists in dict_var[flex][cent.min,cent.max,sig.min,sig.max]
        dict_var = {'low':[3,3,0.1,0.1],\
            'medium'  : [7,7,1,1.25],\
            'high'    : [15,15,1,3],\
            'maximum' : [np.inf,np.inf,1,np.inf]}
        try:
            dict_var[constraint_flex]
        except KeyError:
            #We force the default if by any reason the input is erroneous
            constraint_flex = 'medium'
        finally:
            for el in dictionary:
                dictionary[el]['ELNES_init_const'] = dict()
                for ssh in dictionary[el]['ELNES']:
                    cent = dictionary[el]['ELNES'][ssh]['center']
                    sigm = dictionary[el]['ELNES'][ssh]['sigma']
                    dictionary[el]['ELNES_init_const'][ssh] = dict()
                    '''
                    dictionary[el]['ELNES_init_const'][ssh]['center_min'] =\
                        cent - cent*dict_var[constraint_flex][0]
                    dictionary[el]['ELNES_init_const'][ssh]['center_max'] =\
                        cent + cent*dict_var[constraint_flex][1]
                    '''
                    dictionary[el]['ELNES_init_const'][ssh]['center_min'] =\
                        cent - dict_var[constraint_flex][0]
                    dictionary[el]['ELNES_init_const'][ssh]['center_max'] =\
                        cent + dict_var[constraint_flex][1]
                    dictionary[el]['ELNES_init_const'][ssh]['sigma_min'] = 0.5
                    #sigm - sigm*dict_var[constraint_flex][2]
                    dictionary[el]['ELNES_init_const'][ssh]['sigma_max'] =\
                        sigm + sigm*dict_var[constraint_flex][3]
                    dictionary[el]['ELNES_init_const'][ssh]['amplitude_min'] = 0
                    dictionary[el]['ELNES_init_const'][ssh]['amplitude_max'] = np.inf

    def create_model(self,name_area,auto_constraints = True, flex = 'medium',constraints_dictionary = dict()):
        """This method creates the model to be fitted by lmsfit, using the parameters and functions previously set.

        Args:
            name_area (str): Is a label for the area of the possible spectrum image to be fitted. It allows
                to carry out initial fits to get parameters close to equilibrium and speed up convergence
                in large SImages or SLines. It works well with cluster-separated areas -- each cluster zone
                can be individually initialized.
            auto_constraints (bool, optional): Decides if the constraints are calculated automatically
                for the parameters in the fitting components. Defaults to True.
                Advice: Let it go automatically at first, and then correct constraints if neccesary
            flex (str, optional): controls how stiff the constraints in the fittings are. Defaults to 'medium'.
            constraints_dictionary ([type], optional): possible dictionary of constraints. Defaults to dict().
                Not implemented yet, but will allow a modification of parameters for the fitting by an external user

        Raises:
            KeyError: If the dictionary does not contain a certain ELNES component, the keyError raise is avoided,
            as it may have being deleted on purpose by the user (ELNES is not always desired)
        """
        mod_cont_list     = list()
        mod_elnes_list    = list()
        params_cont_list  = list()
        params_elnes_list = list()
        #First add the continuum components
        try:
            self.models_components[name_area]
        except:
            print('No valid named area was provided. Run previous steps and configure a valid area')
            raise
        else:
            dictionary = cp.deepcopy(self.models_components[name_area])
            for el in dictionary:
                for subsh in dictionary[el]['continuum']:
                    pref = ''.join([el,subsh,'_cont_'])
                    mod = Model(dictionary[el]['continuum'][subsh],\
                        prefix = pref,nan_policy='omit')
                    pars = mod.make_params()
                    #Experience says this is a sensible choice of parameters
                    pars[''.join([pref,'A'])].value   =\
                        dictionary[el]['continuum_init_const'][subsh]['A']
                    pars[''.join([pref,'A'])].min     =\
                        dictionary[el]['continuum_init_const'][subsh]['A_min']
                    pars[''.join([pref,'A'])].vary =\
                        dictionary[el]['continuum_init_const'][subsh]['vary_A']
                    pars[''.join([pref,'chem'])].value =\
                        dictionary[el]['continuum_init_const'][subsh]['chem']
                    pars[''.join([pref,'chem'])].vary =\
                        dictionary[el]['continuum_init_const'][subsh]['allow_chem']
                    mod_cont_list.append(mod)
                    params_cont_list.append(pars)
            #Now the ELNES counterpart - if it exists
                try:
                    dictionary[el]['ELNES']
                except KeyError:
                    #If the ELNES component (e.g. a gaussian component ...) does not exist
                    #Nothing is added. No problem
                    pass
                else:
                    for subsh in dictionary[el]['ELNES']:
                        tipo = dictionary[el]['ELNES'][subsh]['type_compo']
                        '''
                        cent = dictionary[el]['ELNES'][subsh]['center']
                        sigm = dictionary[el]['ELNES'][subsh]['sigma']
                        amp  = dictionary[el]['ELNES'][subsh]['amplitude']
                        '''
                        pref = ''.join([el,subsh,'_'])
                        #We have to select the model created
                        if tipo == 'gaussian':
                            mod = GaussianModel(prefix = pref)
                        elif tipo == 'lorentzian':
                            mod = LorentzianModel(prefix = pref)
                        elif tipo == 'pseudovoigt':
                            mod = PseudoVoigtModel(prefix = pref)
                        elif tipo == 'splitlorentzian':
                            mod = SplitLorentzianModel(prefix = pref)
                        else:
                            #In case of not being one of this, by now, raise
                            raise KeyError
                        pars = mod.make_params()
                        for clave in list(dictionary[el]['ELNES'][subsh].keys())[1:]:
                            pars[''.join([pref,clave])].value =\
                            dictionary[el]['ELNES'][subsh][clave]
                            pars[''.join([pref,clave])].min =\
                            dictionary[el]['ELNES_init_const'][subsh]['_'.join([clave,'min'])]
                            pars[''.join([pref,clave])].max =\
                            dictionary[el]['ELNES_init_const'][subsh]['_'.join([clave,'max'])]
                        #We append now the componets to the list
                        mod_elnes_list.append(mod)
                        params_elnes_list.append(pars)
            #We start by created a single component model, and add the rest
            #First, continuum models
            self.models[name_area] = mod_cont_list[0]
            for mod in mod_cont_list[1:]:
                self.models[name_area] += mod
            #Now, the elnes counterparts
            for mod in mod_elnes_list:
                self.models[name_area] += mod
            #Make the parameters
            self.pars[name_area] = self.models[name_area].make_params()
            #Set the same contitions in the global model as in the intial ones
            #ELNES
            for pos in params_elnes_list:
                for par in pos:
                    self.pars[name_area][par].value = pos[par].value
                    self.pars[name_area][par].min = pos[par].min
                    self.pars[name_area][par].max = pos[par].max
            #Continuum
            for pos in params_cont_list:
                for par in pos:
                    self.pars[name_area][par].value = pos[par].value
                    self.pars[name_area][par].min = pos[par].min
                    self.pars[name_area][par].max = pos[par].max
                    #Here we ensure an initial fit without chemical displacement
                    self.pars[name_area][par].vary = pos[par].vary

    def create_extra_component(self,element,name,eloss,\
        name_area = 'default',type_predet = 'gaussian',flex = 'medium',fix_amp = False):
        """Method that creates an extra component other than the expected WL for compatible
        subshells and sets the constraint for later model fitting.

        Args:
            element (str): Element to which we attach this new component. 
                This is a mandatory aspect of the function, and ensures that we can 
                proceed with the rest of the methods as expected.
            name (str): Name we give to the created component
            eloss (float): Possition in the energy axis we want this component to be
            type_predet (str, optional): Type of curve we are fitting to this component.
                Defaults to 'gaussian'.
            flex (str, optional): Flexibility in the constraints. Available choices are:
                'low','medium','high' and 'maximum'. Defaults to 'medium'.
            fix_amp (bool, optional): Controls if we want the amplitude of the component to be limited.
                It may help to avoid divergence when we place a component close to an existing WL.
                Defaults to False.
        """
        spectrum = self.ref_spectra[name_area]
        dict_var = {'low':[3,3,0.1,0.1],\
            'medium'  : [7,7,1,1.25],\
            'high'    : [15,15,1,3],\
            'maximum' : [np.inf,np.inf,1,np.inf]}
        try:
            dict_var[flex]
        except KeyError:
            #We force the default if by any reason the input is erroneous
            flex = 'medium'
        try:    
            self.models_components[name_area][element]
        except KeyError:
            print('We need an actual element of the model to hold this new component')
            raise
        try:
            self.models_components[name_area][element]['ELNES']
        except:
            #In case of not holding any ELNES structure whatsoever up to this point
            self.models_components[name_area][element]['ELNES'] = dict()
        try:
            self.models_components[name_area][element]['ELNES_init_const']
        except:
            self.models_components[name_area][element]['ELNES_init_const'] = dict()

        #Adding the name of the component to the ELNES dict
        self.models_components[name_area][element]['ELNES'][name] = dict()
        #Let's do some calculations
        cent,sigm,amp = self.determine_compo_parameters(spectrum,type_predet,eloss)
        self.models_components[name_area][element]['ELNES'][name]['type_compo'] = type_predet
        self.models_components[name_area][element]['ELNES'][name]['center']    = cent
        self.models_components[name_area][element]['ELNES'][name]['sigma']     = sigm
        self.models_components[name_area][element]['ELNES'][name]['amplitude'] = amp
        self.models_components[name_area][element]['ELNES_init_const'][name] = dict()
        self.models_components[name_area][element]['ELNES_init_const'][name]['center_min'] =\
            cent - cent*dict_var[flex][0]
        self.models_components[name_area][element]['ELNES_init_const'][name]['center_max'] =\
            cent + cent*dict_var[flex][1]
        self.models_components[name_area][element]['ELNES_init_const'][name]['sigma_min'] =\
            sigm - sigm*dict_var[flex][2]
        self.models_components[name_area][element]['ELNES_init_const'][name]['sigma_max'] =\
            sigm + sigm*dict_var[flex][3]
        if not fix_amp:
            self.models_components[name_area][element]['ELNES_init_const'][name]['amplitude_min'] = 0
            self.models_components[name_area][element]['ELNES_init_const'][name]['amplitude_max'] = np.inf
        else:
            self.models_components[name_area][element]['ELNES_init_const'][name]['amplitude_min'] = 0
            self.models_components[name_area][element]['ELNES_init_const'][name]['amplitude_max'] = amp*1.2
    

    def create_extra_component_second_model(self,element,name,eloss,\
            name_area = 'default',type_predet = 'gaussian',flex = 'medium',fix_amp = False):
            """Method that creates an extra component other than the expected WL for compatible
            subshells and sets the constraint for later model fitting.

            Args:
                element (str): Element to which we attach this new component. 
                    This is a mandatory aspect of the function, and ensures that we can 
                    proceed with the rest of the methods as expected.
                name (str): Name we give to the created component
                eloss (float): Possition in the energy axis we want this component to be
                type_predet (str, optional): Type of curve we are fitting to this component.
                    Defaults to 'gaussian'.
                flex (str, optional): Flexibility in the constraints. Available choices are:
                    'low','medium','high' and 'maximum'. Defaults to 'medium'.
                fix_amp (bool, optional): Controls if we want the amplitude of the component to be limited.
                    It may help to avoid divergence when we place a component close to an existing WL.
                    Defaults to False.
            """
            spectrum = self.ref_spectra[name_area]
            dict_var = {'low':[3,3,0.1,0.1],\
                'medium'  : [7,7,1,1.25],\
                'high'    : [15,15,1,3],\
                'maximum' : [np.inf,np.inf,1,np.inf]}
            try:
                dict_var[flex]
            except KeyError:
                #We force the default if by any reason the input is erroneous
                flex = 'medium'
            try:
                self.extra_modified_model_components[name_area] 
            except:
                #In case of being the first component added to the dictionary for this
                #particular area
                self.extra_modified_model_components[name_area] = dict()
            #Let's do some calculations
            #The values are stored as center,sigma and amplitude, in that order
            parameters_model = ['center','sigma','amplitude']
            cent,sigm,amp = self.determine_compo_parameters(spectrum,type_predet,eloss)
            list_of_values = [cent,sigm,amp]
            #Now, the important thing is to create this component, and store it into a dictionary
            #This dictionary must also contain the constraints to be used in the fitting
            if name[-1] == '_':
                fullname = ''.join([element,name])
            else:
                fullname = ''.join([element,name,'_'])
            if type_predet == 'lorentzian':
                self.extra_modified_model_components[name_area][fullname] =  [LorentzianModel(prefix = fullname),]
            elif type_predet == 'pseudovoigt':
                self.extra_modified_model_components[name_area][fullname] =  [PseudoVoigtModel(prefix = fullname),]
            elif type_predet == 'splitlorentzian':
                self.extra_modified_model_components[name_area][fullname] =  [SplitLorentzianModel(prefix = fullname),]
            else:
                #By default we go back to the gaussian model
                self.extra_modified_model_components[name_area][fullname] =  [GaussianModel(prefix = fullname),]
            #Now we have to append the parameter dictioary, to be able later to perform the multifit
            parameters_constraints =\
                [[cent - dict_var[flex][0],cent + dict_var[flex][1]],\
                [max(sigm - sigm*dict_var[flex][2],0),sigm + sigm*dict_var[flex][3]],\
                [0,np.inf]]
            
            for idx,paramet in enumerate(parameters_model):
                clave = ''.join([fullname,paramet])
                self.extra_modified_model_components[name_area][fullname][0]\
                .set_param_hint(clave,value = list_of_values[idx],\
                    min = parameters_constraints[idx][0],\
                    max = parameters_constraints[idx][1])
            self.extra_modified_model_components[name_area][fullname].append(\
            self.extra_modified_model_components[name_area][fullname][0].make_params())



    def delete_component(self,element,name,area_name= 'default'):
        """Method that allows to remove a certain component from the fitting.
        it also removes the constraints from the model dictionary.

        Args:
            element (str): Element to which we have attached this component.
                This helps with the component identification in the inner loop
            name (str): name of the component to be eliminated.
            area_name (str, optional): Label of the area from where we want to remove the component.
                Defaults to 'default'.
        """
        list_to_delete = []
        try:
            dictionary = self.models_components[area_name][element]
        except:
            print('The given element, or name of the area are wrong')
            print('\nCheck those fields and re-run')
            raise
        else:
            for compType in dictionary:
                for key in dictionary[compType]:
                    if name == key:
                        list_to_delete.append((compType,key))
                    else: pass
            for de in list_to_delete:
                dictionary[de[0]].pop(de[1])

    def add_reference_keyMatrix(self,matrix,name_area):
        """Method that adds the positional reference matrix to the model
        This matrix allows us to know the positions in a SI/SL to be fitted
        by a certain reference model, so we can potentially speed-up convergence

        Args:
            matrix (np.ndarray): Positional array of ones and zeros.
                One:signals a pixel to be fitted in the SI/SL under the current model
                Zero: pixel to avoid in the fitting, potentially belonging
                to a different area (name_area)
            name_area (str): Label of the reference area
        """
        self.ref_matrices[name_area] = matrix

    def fit_reference(self,name_area = 'default'):
        """Method that carries out the initial fitting for the reference spectra
        of a certain reference area

        Args:
            name_area (str, optional): Label of the reference area selected.
                Defaults to 'default'.
        """
        try:
            self.ref_spectra[name_area]
        except:
            #Case of being signaling an incorrect place
            raise
        else:
            self.ref_results[name_area] =\
                self.models[name_area].fit(self.ref_spectra[name_area],\
                params = self.pars[name_area],x = self.Eloss)

    def multifit_area(self,name_area = 'default'):
        """Method to run a loop through the SI/SL and fit all the pixels
        belonging to the reference area signaled by name_area

        Args:
            name_area (str, optional): Controls the area to be fitted.Label coinciding
                with the different reference models created previously. Defaults to 'default'.
        """
        try: 
            array_area = self.ref_matrices[name_area]
        except:
            #IN case of not having a reference matrix set, let's fit the whole SI, SL ..
            array_area = np.ones(self.ds.ElectronCount.data.shape[:-1])
        dimx,dimy = array_area.shape
        self.results[name_area] = list()
        for i in range(dimx):
            #We do this at the begining of each row, since it is more likely to be 
            # closer to the reference than to the last pixel of the row 
            paramet = self.ref_results[name_area].params
            self.results[name_area].append(list())
            for j in range(dimy):
                if array_area[i,j] == 1:
                    y = self.ds.sel(x = j, y = i).ElectronCount.data
                    res = self.models[name_area].fit(y,params = paramet, x = self.Eloss)
                    self.results[name_area][i].append(res)
                    #We advance the parameters to be the ones in the later fit.
                    #This way, and assuming a certain degree of continuity in the 
                    #material, we are close to equilibrium conditions in the next fit
                    #by expecting the spectrum image - spectra to vary continuously.
                    paramet = res.params
                else:
                    #In case of being in pixel outside the fitting range, append none.
                    self.results[name_area][i].append(None)
    '''
    #This method does not exists for the non interactive version yet
    def multifit_area_modified(self,name_area,locking_dict):
        pass
    '''
    def add_clustering_references(self,clustering_ds,**kwargs):
        self.ds_clust = clustering_ds
        for el in self.ds_clust.label_number.values:
            zone_name = 'cluster_{}'.format(el)
            self.create_components(self.ds_clust['ElectronCount_norm_Centroids']\
                .sel(label_number = el).values,name_area=zone_name,\
                **kwargs)
            mat = np.zeros(self.ds_clust.labs.values.shape)
            mat[self.ds_clust.labs.values == el] = 1
            self.add_reference_keyMatrix(mat,name_area = zone_name)
    
    def fit_cluster_reference_spectra(self):
        for el in self.ds_clust.label_number.values:
            zone_name = 'cluster_{}'.format(el)
            self.fit_reference(name_area = zone_name)
        
    # TODO The removal of a labeled zone
    def remove_clustering_references(self,name):
        pass

    def add_new_reference_area_SI(self,name,top_corner,bottom_corner):
        """This method works with Spectrum Images, and allows to select
            an specific area to perform the fitting, by giving the x and y 
            coordinates (area with a box shape, with a top-left corner and 
            bottom-righ corner clearly defined)

        Args:
            name (str): Name of the area, to be used later as identifier
            top_corner (tupple or list): Tuple or list of with the top corner
                of the box selected as fitting area
            bottom_corner (tupple or list): Tuple or list of with the bottom corner
                of the box selected as fitting area
        """
        x0,y0 = top_corner
        x1,y1 = bottom_corner
        #Let's adjust in case of recieving a box out of bounds
        if x0 < 0: x0 = 0
        if y0 < 0: y0 = 0
        if x1 > self.ds.x.data[-1]: x1 = self.ds.x.data[-1]
        if y1 > self.ds.y.data[-1]: y1 = self.ds.y.data[-1]
        #And now we can select reference, and all that chain of orders...
        area_s = self.ds.sel(x = slice(x0,x1),y = slice(y0,y1)).ElectronCount.data
        ref_s = np.mean(area_s,axis = (0,1))
        self.create_components_and_model(ref_s,name_area=name)
        self.fit_reference(name_area = name)
        mat = np.zeros(self.ds.ElectronCount.data.shape)
        mat[y0:y1,x0:x1] = 1
        self.add_reference_keyMatrix(mat,name_area = name)

    def finalize_fit(self,list_labels,name):
        self.results[name] = list()
        dimx,dimy = self.ds.ElectronCount.data.shape[:-1]
        for i in range(dimx):
            self.results[name].append(list())
            for j in range(dimy):
                for lab in list_labels:
                    prev = self.results[lab][i][j]
                    if prev != None:
                        self.results[name][i].append(prev)
                    else: pass
                try:
                    self.results[name][i][j]
                except:
                    self.results[name][i].append(None)
    
    def _create_reference_components_1strun(self,area,type_run = 'multi'):
        dictio = dict()
        for el in self.fitting_elements:
            dictio[el] =\
            {'ELNES' : list(self.models_components[area][el]['ELNES'].keys()),\
            'continuum' : list(self.models_components[area][el]['continuum'].keys())}
        if type_run == 'multi':
            self.ref_components['multi'][area] = cp.deepcopy(dictio)
            self.ref_components['rerun'][area] = cp.deepcopy(dictio)
        #We already create the possible rerun-dict ... since most probably we will use it later
        elif type_run == 'rerun':
            self.ref_components['rerun'][area] = cp.deepcopy(dictio)

    def _add_toReference_extra_compos(self,area,element,new_comp):
        lista = self.ref_components['rerun'][area][element]['ELNES']
        if new_comp not in lista:
            self.ref_components['rerun'][area][element]['ELNES'].append(new_comp)
    
    def get_RCS_maps(self,area_name,reference_dict,type_run = 'multi',type_data = 'SIm'):
        """Thie method gets the reduced chi square value for the spectrum image
        and generates a matrix of values - stored in an xarray - for later display

        Args:
            area_name (str): Area name, where the red chi square coefficient is going to
            be investigated
        """
        l1 = len(reference_dict[area_name])
        l2 = len(reference_dict[area_name][0])
        zer = np.zeros((l1,l2))
        for i,row in enumerate(reference_dict[area_name]):
            for j,el in enumerate(row):
                if el != None:
                    zer[i,j] = el.redchi
                else:
                    zer[i,j] = np.NaN
        #Now let's create the data structure of xarray
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        if type_data == 'SIm':
            lista_kdims = ['y','x']
        elif type_data == 'SLi':
            lista_kdims = ['x','y']
        if type_run == 'multi':
            self.red_chi_sqr[area_name] =\
                xr.Dataset({'ReducedXiSq':(lista_kdims,zer)},coords = {'x':j_xs,'y':i_ys})
        elif type_run == 'rerun':
            self.red_chi_sqr_re[area_name] =\
                xr.Dataset({'ReducedXiSq':(lista_kdims,zer)},coords = {'x':j_xs,'y':i_ys})
        
    def get_residual_signals(self,area_name,reference_dict,type_run = 'multi',type_data = 'SIm'):
        """Thie method gets the residual signals from the fitting
        and generates a matrix of values - stored in an xarray - for later display

        Args:
            area_name (str): Area name, where the red chi square coefficient is going to
            be investigated
        """
        l1 = len(reference_dict[area_name])
        l2 = len(reference_dict[area_name][0])
        l3 = self.Eloss.size
        zer = np.zeros((l1,l2,l3))
        for i,row in enumerate(reference_dict[area_name]):
            for j,el in enumerate(row):
                if el != None:
                    zer[i,j,:] = el.residual
                else:
                    arr_nan = np.empty_like(self.Eloss)
                    arr_nan[:] = np.NaN
                    zer[i,j,:] = arr_nan
        #Now let's create the data structure of xarray
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        if type_data == 'SIm':
            lista_kdims = ['y','x','Eloss']
        elif type_data == 'SLi':
            lista_kdims = ['x','y','Eloss']
        if type_run == 'multi':
            self.residuals[area_name] =\
                xr.Dataset({'Residuals':(lista_kdims,zer)},\
                coords = {'x':j_xs,'y':i_ys,'Eloss':self.Eloss})
        elif type_run == 'rerun':
            self.residuals_re[area_name] =\
                xr.Dataset({'Residuals':(lista_kdims,zer)},\
                coords = {'x':j_xs,'y':i_ys,'Eloss':self.Eloss})

    def get_best_fit_signals(self,area_name,reference_dict,type_run = 'multi',type_data = 'SIm'):
        """This method gets the best fit signals from the multifitting
        and generates a matrix of values - stored in an xarray - for later display

        Args:
            area_name (str): Area name, where the red chi square coefficient is going to
            be investigated
        """
        l1 = len(reference_dict[area_name])
        l2 = len(reference_dict[area_name][0])
        l3 = self.Eloss.size
        zer = np.zeros((l1,l2,l3))
        for i,row in enumerate(reference_dict[area_name]):
            for j,el in enumerate(row):
                if el != None:
                    zer[i,j,:] = el.best_fit
                else:
                    arr_nan = np.empty_like(self.Eloss)
                    arr_nan[:] = np.NaN
                    zer[i,j,:] = arr_nan
        #Now let's create the data structure of xarray
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        if type_data == 'SIm':
            lista_kdims = ['y','x','Eloss']
        elif type_data == 'SLi':
            lista_kdims = ['x','y','Eloss']
        if type_run == 'multi':
            self.best_fits[area_name] =\
                xr.Dataset({'Best_fit':(lista_kdims,zer)},\
                coords = {'x':j_xs,'y':i_ys,'Eloss':self.Eloss})
        elif type_run == 'rerun':
            self.best_fits_re[area_name] =\
                xr.Dataset({'Best_fit':(lista_kdims,zer)},\
                coords = {'x':j_xs,'y':i_ys,'Eloss':self.Eloss})

    def get_best_fit_components(self,area_name,reference_dict,type_run = 'multi',type_data = 'SIm'):
        """This method gets the best fit per component from the multifitting
        and generates a matrix of values - stored in an xarray - for later display

        Args:
            area_name (str): Area name, where the red chi square coefficient is going to
            be investigated
        """
        l1 = len(reference_dict[area_name])
        l2 = len(reference_dict[area_name][0])
        l3 = self.Eloss.size
        #Second, we generate the dictionary keys to be filled
        self.zer = dict() # To fill later the xr.Dataset
        for el in self.fitting_elements:
            #So we get every component generated
            ssh_list = self.ref_components[type_run][area_name][el]['ELNES']
            for ssh in ssh_list:
                clave = ''.join([el,ssh,'_'])
                self.zer[clave] = np.zeros((l1,l2,l3))
            cont_compo = self.ref_components[type_run][area_name][el]['continuum']
            for cont in cont_compo:
                clave = ''.join([el,cont,'_cont_'])
                self.zer[clave] = np.zeros((l1,l2,l3))
        #Now the evaluation of components
        for i,row in enumerate(reference_dict[area_name]):
            for j,el in enumerate(row):
                if el != None:
                    compo_dict = el.eval_components()
                    for clave in self.zer:
                        self.zer[clave][i,j,:] = compo_dict[clave]
                else:
                    for clave in self.zer:
                        arr_nan = np.empty_like(self.Eloss)
                        arr_nan[:] = np.NaN
                        self.zer[clave][i,j,:] = arr_nan
        #Now let's create the data structure of xarray
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        expanded_dictio = dict()
        
        for name in self.zer:   
            if type_data == 'SIm':
                expanded_dictio[name] = (['y','x','Eloss'],self.zer[name])
            elif type_data == 'SLi':
                #Added so the Slines still work on this same funciton
                expanded_dictio[name] = (['x','y','Eloss'],self.zer[name])
        if type_run == 'multi':
            self.component_eval[area_name] =\
                xr.Dataset(expanded_dictio,\
                coords = {'x':j_xs,'y':i_ys,'Eloss':self.Eloss})
        elif type_run == 'rerun':
            self.component_eval_re[area_name] =\
                xr.Dataset(expanded_dictio,\
                coords = {'x':j_xs,'y':i_ys,'Eloss':self.Eloss})

    def get_values_and_stderr_components_per_area(self,area_name,reference_dict,type_run = 'multi',type_data = 'SIm'):
        """This method gets the best fit signals from the multifitting
        and generates a matrix of values - stored in an xarray - for later display

        Args:
            area_name (str): Area name, where the red chi square coefficient is going to
            be investigated
        """
        #First we get the dimensions of the matrices filled
        l1 = len(reference_dict[area_name])
        l2 = len(reference_dict[area_name][0])
        #Second, we generate the dictionary keys to be filled
        dictio_val = dict() # To fill later the xr.Dataset
        dictio_std = dict()
        for el in self.fitting_elements:
            #So we get every component generated
            ssh_list = self.ref_components[type_run][area_name][el]['ELNES']
            for ssh in ssh_list:
                for para in ['center','sigma','amplitude']:
                    clave = ''.join([el,ssh,'_',para])
                    dictio_val[clave] = np.zeros((l1,l2))
                    dictio_std[clave] = np.zeros((l1,l2)) 

        #Fill of these newly generated dictionaries per list element in the results
        for i,row in enumerate(reference_dict[area_name]):
            for j,el in enumerate(row):
                if el != None:
                    #Here, we have to further check the elements
                    for par in list(el.params.keys()):
                        #We just want the ELNES paramenters to be evaluated
                        accepted_par = ['center','sigma','amplitude']
                        add_pass = any([el in par for el in accepted_par])
                        if ('cont' not in par) and add_pass:
                            #in stderr and values dict we have the same keys
                            val = el.params[par].value
                            dictio_val[par][i,j] = val
                            try:
                                #It may happen that no std error is retrieved - so do nothing then
                                dictio_std[par][i,j] = 100 * el.params[par].stderr/val
                            except:
                                dictio_std[par][i,j] = np.NaN
                        else: pass
                else:
                    for clav in list(dictio_std.keys()):
                        #Every element in this dictionary is 0 in this position
                        dictio_std[clav][i,j] = np.NaN
                    for clav2 in list(dictio_val.keys()):
                        #Every element in this dictionary is 0 in this position
                        dictio_val[clav2][i,j] = np.NaN
                    
        #Now let's create the data structure of xarray - for all this madness
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        #if it has a key in the std dict, it also is in the values dict
        if type_data == 'SIm':
            lista_kdims  = ['y','x']
        elif type_data == 'SLi':
            lista_kdims  = ['x','y']
        expanded_dictio = dict()
        for name in list(dictio_std.keys()): 
            expanded_dictio[name] = (lista_kdims,dictio_std[name])
        if type_run == 'multi':
            self.param_errRel[area_name] =\
            xr.Dataset(expanded_dictio,coords = {'x':j_xs,'y':i_ys})
            expanded_dictio = dict()
            for name in list(dictio_val.keys()): 
                expanded_dictio[name] = (lista_kdims,dictio_val[name])
            self.param_values[area_name] =\
                xr.Dataset(expanded_dictio,\
                coords = {'x':j_xs,'y':i_ys})
        elif type_run == 'rerun':
            self.param_errRel_re[area_name] =\
            xr.Dataset(expanded_dictio,coords = {'x':j_xs,'y':i_ys})
            expanded_dictio = dict()
            for name in list(dictio_val.keys()): 
                expanded_dictio[name] = (lista_kdims,dictio_val[name])
            self.param_values_re[area_name] =\
                xr.Dataset(expanded_dictio,\
                coords = {'x':j_xs,'y':i_ys})
    
    def get_full_results_data(self,type_result = 'single'):
        #This method serves to extract in a single Dataset the whole data structure\
        #  needed for results analysis
        #type result controls the result accessed for the final data constructor
        #single - all those areas that were fitted only once, and\
        #  the first fits of those fitted several times - using self.results
        #modif - all those areas that were fitted at some point,\
        #  keeping the last fit for those fitted several times
        #The rerun key dictionary is always created at the same time as the multi\
        # - so we are good to go
        #The multi key, on the other hand, is no longer modified after the 1st single multifit
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        l1,l2,l3 = self.ds.ElectronCount.values.shape
        dictio_components = cp.deepcopy(self.ref_components['rerun'])
        list_params = ['center','sigma','amplitude','fwhm']
        dict_comp_mat = dict()     #For the components in each pixel
        dict_param_values = dict() #For the values of the parameters
        dict_param_err = dict()    # For the errors of the parameters
        list_of_compos_toFollow = []
        if type_result == 'single':
            res_lista = self.results
            for area in self.ref_components['multi']:
                # replacing the 'rerun' components
                dictio_components[area] = self.ref_components['multi'][area]
        elif type_result == 'modif':
            res_lista = self.results_final_modified
        #Here we prepare a dictionary of matrices for the compenents that will be extracted
        for area in dictio_components:
            for elem in dictio_components[area]:
                #elnes
                for ssh in dictio_components[area][elem]['ELNES']:
                    clave = ''.join([elem,ssh,'_'])
                    if clave not in list_of_compos_toFollow:
                        list_of_compos_toFollow.append(clave)
                        clave2 = clave+'component'
                        dict_comp_mat[clave2] = (['y','x','Eloss'],np.empty((l1,l2,l3)))
                        dict_comp_mat[clave2][1][:] = np.NaN
                        #Now for the parameters dictionary
                        for par in list_params:
                            clv  = ''.join([clave,par])
                            clv2 = ''.join([clave,par,'_relError%'])
                            dict_param_values[clv] = (['y','x'],np.empty((l1,l2)))
                            dict_param_values[clv][1][:] = np.NaN
                            dict_param_err[clv2] = cp.deepcopy(dict_param_values[clv])
                    else: pass
                for cont in dictio_components[area][elem]['continuum']:
                    clave = ''.join([elem,cont,'_cont_'])
                    if clave not in list_of_compos_toFollow:
                        list_of_compos_toFollow.append(clave)
                        clave2 = clave+'component'
                        clv  = clave+'A'
                        clv2 = clave+'A_relError%'
                        dict_comp_mat[clave2] = (['y','x','Eloss'],np.empty((l1,l2,l3)))
                        dict_comp_mat[clave2][1][:] = np.NaN
                        dict_param_values[clv] = (['y','x'],np.empty((l1,l2)))
                        dict_param_values[clv][1][:] = np.NaN 
                        dict_param_err[clv2] = cp.deepcopy(dict_param_values[clv])
                    else: pass
        mat_bestfit = np.empty((l1,l2,l3))
        mat_residual = np.empty_like(mat_bestfit)
        mat_chi = np.empty((l1,l2))
        mat_chi[:] = np.NaN
        mat_bestfit[:] = np.NaN
        mat_residual[:] = np.NaN
        #Let's make sure we only do once the whole loop of results
        for i in range(l1):
            for j in range(l2):
                #We created this dictio with only the needed areas
                for area in dictio_components:
                    if self.ref_matrices[area][i,j] != 0:
                        #This controls the access at all the possible clusters
                        res = res_lista[area][i][j]
                        #here we do stuff
                        mat_chi[i,j] = res.redchi
                        mat_bestfit[i,j,:] = res.best_fit
                        mat_residual[i,j,:] = res.residual
                        compos = res.eval_components()
                        for comp in compos:
                            clav = comp+'component'
                            dict_comp_mat[clav][1][i,j,:] = compos[comp]
                        for par in dict_param_values:
                            #We get the evaluations of those parameters
                            if par in res.params:
                                dict_param_values[par][1][i,j] = res.params[par].value 
                                try:
                                    par2 = par+'_relError%'
                                    dict_param_err[par2][1][i,j] =\
                                    max(abs(res.params[par].stderr/res.params[par].value)*100,0) 
                                except:
                                    #It may happen that no stderr is calculated
                                    pass
                            else: pass
        mat_clust = np.empty_like(mat_chi)
        for clust in self.ref_matrices:
            if clust != 'default':
                number = int(clust.split('_')[-1])
                mat_clust[self.ref_matrices[clust] == 1] = number
            else: pass
        dictio_final = {'OriginalData':(['y','x','Eloss'],self.ds.ElectronCount.values),\
            'ClustersMatrix':(['y','x'],mat_clust),\
            'ReducedChiSquare':(['y','x'],mat_chi),\
            'BestFit':(['y','x','Eloss'],mat_bestfit),\
            'Residuals':(['y','x','Eloss'],mat_residual)}
        dictio_ds = {**dictio_final,**dict_comp_mat,**dict_param_values,**dict_param_err}
        if type_result == 'single':
            self.ds_singles = xr.Dataset(dictio_ds,\
                coords={'x':j_xs,'y':i_ys,'Eloss':self.ds.Eloss.values})
            self.ds_singles.attrs = self.ds.attrs
        elif type_result == 'modif':
            self.ds_modif = xr.Dataset(dictio_ds,\
                coords={'x':j_xs,'y':i_ys,'Eloss':self.ds.Eloss.values})
            self.ds_modif.attrs = self.ds.attrs
    
    def get_full_results_data_SLines(self,type_result = 'single'):
        #This method serves to extract in a single Dataset the whole data structure\
        #  needed for results analysis - sutied for the structures of spectrum lines
        #type result controls the result accessed for the final data constructor
        #single - all those areas that were fitted only once, and\
        #  the first fits of those fitted several times - using self.results
        #modif - all those areas that were fitted at some point,\
        #  keeping the last fit for those fitted several times
        #The rerun key dictionary is always created at the same time as the multi\
        # - so we are good to go
        #The multi key, on the other hand, is no longer modified after the 1st single multifit
        j_xs = self.ds.x.values
        i_ys = self.ds.y.values
        l1,l2,l3 = self.ds.ElectronCount.values.shape
        dictio_components = cp.deepcopy(self.ref_components['rerun'])
        list_params = ['center','sigma','amplitude','fwhm']
        dict_comp_mat = dict()     #For the components in each pixel
        dict_param_values = dict() #For the values of the parameters
        dict_param_err = dict()    # For the errors of the parameters
        list_of_compos_toFollow = []
        if type_result == 'single':
            res_lista = self.results
            for area in self.ref_components['multi']:
                # replacing the 'rerun' components
                dictio_components[area] = self.ref_components['multi'][area]
        elif type_result == 'modif':
            res_lista = self.results_final_modified
        #Here we prepare a dictionary of matrices for the compenents that will be extracted
        for area in dictio_components:
            for elem in dictio_components[area]:
                #elnes
                for ssh in dictio_components[area][elem]['ELNES']:
                    clave = ''.join([elem,ssh,'_'])
                    if clave not in list_of_compos_toFollow:
                        list_of_compos_toFollow.append(clave)
                        clave2 = clave+'component'
                        dict_comp_mat[clave2] = (['y','x','Eloss'],np.empty((l1,l2,l3)))
                        dict_comp_mat[clave2][1][:] = np.NaN
                        #Now for the parameters dictionary
                        for par in list_params:
                            clv  = ''.join([clave,par])
                            clv2 = ''.join([clave,par,'_relError%'])
                            dict_param_values[clv] = (['y','Eloss'],np.empty((l1,l3)))
                            dict_param_values[clv][1][:] = np.NaN
                            dict_param_err[clv2] = cp.deepcopy(dict_param_values[clv])
                    else: pass
                for cont in dictio_components[area][elem]['continuum']:
                    clave = ''.join([elem,cont,'_cont_'])
                    if clave not in list_of_compos_toFollow:
                        list_of_compos_toFollow.append(clave)
                        clave2 = clave+'component'
                        clv  = clave+'A'
                        clv2 = clave+'A_relError%'
                        dict_comp_mat[clave2] = (['y','x','Eloss'],np.empty((l1,l2,l3)))
                        dict_comp_mat[clave2][1][:] = np.NaN
                        dict_param_values[clv] = (['y','Eloss'],np.empty((l1,l3)))
                        dict_param_values[clv][1][:] = np.NaN 
                        dict_param_err[clv2] = cp.deepcopy(dict_param_values[clv])
                    else: pass
        mat_bestfit = np.empty((l1,l2,l3))
        mat_residual = np.empty_like(mat_bestfit)
        mat_chi = np.empty((l1,l3))
        mat_chi[:] = np.NaN
        mat_bestfit[:] = np.NaN
        mat_residual[:] = np.NaN
        #Let's make sure we only do once the whole loop of results
        for i in range(1):
            for j in range(l1):
                #We created this dictio with only the needed areas
                for area in dictio_components:
                    if self.ref_matrices[area][j,i] != 0:
                        #This controls the access at all the possible clusters
                        res = res_lista[area][i][j]
                        #here we do stuff
                        mat_chi[j,:] = res.redchi
                        mat_bestfit[j,i,:] = res.best_fit
                        mat_residual[j,i,:] = res.residual
                        compos = res.eval_components()
                        for comp in compos:
                            clav = comp+'component'
                            dict_comp_mat[clav][1][j,i,:] = compos[comp]
                        for par in dict_param_values:
                            #We get the evaluations of those parameters
                            if par in res.params:
                                dict_param_values[par][1][j,:] = res.params[par].value 
                                try:
                                    par2 = par+'_relError%'
                                    dict_param_err[par2][1][j,:] =\
                                    max(abs(res.params[par].stderr/res.params[par].value)*100,0) 
                                except:
                                    #It may happen that no stderr is calculated
                                    pass
                            else: pass
        mat_clust = np.empty((l1,l3))
        for clust in self.ref_matrices:
            if clust != 'default':
                number = int(clust.split('_')[-1])
                mat_clust[self.ref_matrices[clust] == 1] = number
            else: pass
        dictio_final = {'OriginalData':(['y','x','Eloss'],self.ds.ElectronCount.values),\
            'ClustersMatrix':(['y','Eloss'],mat_clust),\
            'ReducedChiSquare':(['y','Eloss'],mat_chi),\
            'BestFit':(['y','x','Eloss'],mat_bestfit),\
            'Residuals':(['y','x','Eloss'],mat_residual)}
        dictio_ds = {**dictio_final,**dict_comp_mat,**dict_param_values,**dict_param_err}
        if type_result == 'single':
            self.ds_singles = xr.Dataset(dictio_ds,\
                coords={'x':j_xs,'y':i_ys,'Eloss':self.ds.Eloss.values})
            self.ds_singles.attrs = self.ds.attrs
        elif type_result == 'modif':
            self.ds_modif = xr.Dataset(dictio_ds,\
                coords={'x':j_xs,'y':i_ys,'Eloss':self.ds.Eloss.values})
            self.ds_modif.attrs = self.ds.attrs
    
    #########################################################################################
    ## Attemp of multiprocessing


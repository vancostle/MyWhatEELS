import sys
import json
import os
from physical_constants import R
import time
import holoviews as hv
hv.extension()
from holoviews.streams import param
import panel as pn
import param

import copy as cp
import xarray as xr
import numpy as np


#WhatEELS Library files
from interactive_NLLS_SImages import oxi_panel as oxiSIm_panel
from interactive_NLLS_SLines  import oxi_panel as oxiSLi_panel
from GOS_surfaces import GOS_surface_analyser
from clustering_panel_Spectrum_images import Make_clusters as mk_cl_SI
from clustering_panel_Spectrum_lines  import Make_clusters as mk_cl_SL
from initialization_panel import Fileinput
from results_app import Results_panel
#from initialization_panel_new import formatter,formatter2

#We are going to define some globals here now for the widget configuration through css
try:
    root_css = [el for el in sys.path if r'\Library\css' in el][0]
except Exception as e:
    print('No root for css found. Skipping loading')
    print(e)
else:
    css_file = '{}\\css_styling.css'.format(root_css)
    css_files = getattr(pn.config, 'css_files', None)
    if isinstance(css_files, list) and css_file not in css_files:
        css_files.append(css_file)

class main_hub(param.Parameterized):
    shortcut_directory = param.String('./')
    def __init__(self):
        super().__init__()
        #The model creation and constructor buttons  - NLLS
        self.type_dataset = 'None'
        self.first_creation = True
        self.button_model_constructor    = pn.widgets.Button(name = 'Model Constructor')
        self.button_model_constructor.on_click(self._callback_create_model_panel)
        self.button_model_constructor.button_type = 'success'
        self.button_model_constructor.disabled = True
        #--------------------------------------------------------#
        #### Botones de ML: 
        self.button_launch_svm = pn.widgets.Button(name = 'SVM')
        self.button_launch_svm.on_click(self._callback_create_svm_panel) ####ESTO HAY Q CREARLO
        self.button_launch_svm.button_type = 'success'
        self.button_launch_svm.disabled = True


        #### Botones de ML: 
        self.button_launch_GAN = pn.widgets.Button(name = 'GAN')
        self.button_launch_GAN.on_click(self._callback_create_gan_panel) ####ESTO HAY Q CREARLO
        self.button_launch_GAN.button_type = 'success'
        self.button_launch_GAN.disabled = True
        #--------------------------------------------------------#

        #'\u03c7\u00b2 - xi squared
        self.button_analyser_constructor =\
            pn.widgets.Button(name = 'Pre-Analysis',width = 115)
        self.button_analyser_constructor.on_click(self._callback_create_analyser_panel)
        self.button_analyser_constructor.button_type = 'warning'
        self.button_analyser_constructor.disabled = True
        self.button_new_model_creator =\
            pn.widgets.Button(name = 'Expand Model',width = 115,margin = (5,10,5,15))
        self.button_new_model_creator.on_click(self._callback_modified_model_creator)
        self.button_new_model_creator.button_type = 'warning'
        self.button_new_model_creator.disabled =True
        self.button_results_app = pn.widgets.Button(name = 'Results')
        self.button_results_app.button_type = 'success'
        self.button_results_app.on_click(self._callback_NLLSresults)
        self.button_results_app.disabled = True
        self.button_results_app_saved =\
            pn.widgets.Button(name = 'Results From Saved State',\
            button_type = 'danger',disabled = True,css_classes = ['custom_button_bokeh_black_light',\
            'custom_button_bokeh_black_inter_dis'])
        self.button_results_app_saved.on_click(self._callback_savedNLLSresults)
        #The buttons for the clustering app
        self.button_clustering_app = pn.widgets.Button(name = 'Clustering')
        self.button_clustering_app.button_type = 'primary'
        self.button_clustering_app.disabled = True
        self.button_clustering_app.on_click(self._callback_clustering_app)
        #The button that allow the access to the different apps.
        self.button_collect_start = pn.widgets.Button(name = 'Boot Apps',height = 35)
        self.button_collect_start.button_type = 'success'
        self.button_collect_start.on_click(self._callback_kickstart_app)
        #Button to launch the GOS application
        self.button_launch_GOS = pn.widgets.Button(name = 'GOS analysis tools',\
            button_type = 'warning')
        self.button_launch_GOS.on_click(self._callback_launch_gosAPP)
        '''
        self.button_change_extension = pn.widgets.Button(name = 'Extension',\
            button_type = 'danger',disabled = True,width = 100)
        self.button_change_extension.on_click(self.change_extension)
        '''
        #The side panel for the model loading
        self.fli = Fileinput()
        self.fli.create_layout()
        #The info buttons for each of the apps
        self.button_info_GOS = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_GOS.on_click(self._callback_info_GOS)
        self.button_info_clust = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_clust.on_click(self._callback_info_clust)
        #-----------------------------------------------------------#
        self.button_info_svm = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_svm.on_click(self._callback_info_svm)
        self.button_info_GAN = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_GAN.on_click(self._callback_info_GAN)
        #--------------------------------------------+-------------#
        self.button_info_NLLSmodel = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_NLLSmodel.on_click(self._callback_info_NLLSmodel)
        self.button_info_NLLSmodel.on_click(self._callback_info_NLLSmodel)
        self.button_info_NLLSnewmodel = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_NLLSnewmodel.on_click(self._callback_info_NLLSnewmodel)
        self.button_info_NLLSanalysis = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_NLLSanalysis.on_click(self._callback_info_NLLSanalysis)
        self.button_info_Boot = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger',height = 35)
        self.button_info_Boot.on_click(self._callback_info_Boot)
        self.button_info_NLLSresult = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_NLLSresult.on_click(self._callback_info_NLLSresults)
        self.button_info_NLLSresult_load = pn.widgets.Button(name = '\u2139',width = 25,\
            button_type = 'danger')
        self.button_info_NLLSresult_load.on_click(self._callback_info_NLLSresults_load)
        ini_chain = '#### Wellcome to WhatEELS<br>Relax,\
        get yourself a cup of coffee<br>\
        and get ready to analyse some EELS data.'
        self.default_message =\
            pn.pane.Markdown(ini_chain,margin = (0,10),width = 320)
        #Now, let's creaty the widget to acccess saved data of EELS and go directly to results
        self.shortcut_results_wid = pn.Param(self.param['shortcut_directory'],\
            widgets = {'shortcut_directory':pn.widgets.TextInput},\
            parameters = ['shortcut_directory'],width = 360,height = 45,\
            show_name = False,show_labels = False,margin = (5,0))
        self.shortcut_results_wid[0].height = 35
        self.shortcut_results_wid[0].width = 300
        self.shortcut_results_wid[0].margin = (5,50,5,10)
        self.shortcut_results_wid[0].css_classes = ['input_custom_1']

    @param.depends('shortcut_directory',watch = True)
    def watcher_results_loading_dir(self):
        '''
        This function will look inside the directory provided.
        If a config file for reuslts is found, the results launcher
        will be unlocked - and launched for analysis.
        '''
        #It starts with a set of try - except to catch exceptions
        try:
            lista = os.listdir(self.shortcut_directory)
        except Exception as e:
            print(e)
            self.button_results_app_saved.button_type = 'danger'
            self.button_results_app_saved.disabled = True
            self.default_message.object =\
            """#### Invalid directory address. It could not be found"""
        else:
            if 'results_config.json' not in lista:
                self.default_message.object =\
                '#### The provided directory does not contain a\
                results_config.json file.'
                self.button_results_app_saved.button_type = 'danger'
                self.button_results_app_saved.disabled = True
            else:
                self.button_results_app_saved.button_type = 'success'
                self.button_results_app_saved.disabled = False
                self.default_message.object =\
                '#### Everything looks fine. Proceed.'

    def _callback_savedNLLSresults(self,event):
        """Method called when we want to launch the NLLS results
        panel from a saved file state.
        Initially, it tries to load all the data. If something fails, 
        it stops execution and prints error message in the info panel.
        
        If everthing is allright, it will also try to set the app to 
        a suitable directory, so subsequent saves are stored in the same 
        set of folders.
        """
        #Let's try to load the files
        dirname = self.shortcut_directory.strip('\\').strip('/')
        try:
            jname = r"""{}\results_config.json""".format(dirname)
            with open(jname,'r') as f:
                dictio = json.load(f)
                elem_li = dictio['elements']
                gos_scalings = dictio['gos_sacalings']
                onsets = dictio['onsets']
                color_list = dictio['colors']
                dataset_type = dictio['dataset_type']
                if dictio['fittings_available'] == 'single':
                    clav = False
                elif dictio['fittings_available'] == 'multiple':
                    clav = True
            #Now, let's try the xarray datasets
            dname = r"""{}\ds.nc""".format(dirname)
            fsname = r"""{}\ds_first.nc""".format(dirname)
            mname = r"""{}\ds_modi.nc""".format(dirname)
            if clav:
                ds_modi = xr.load_dataset(mname)
            else: ds_modi = None 
            ds_first = xr.load_dataset(fsname)
            ds = xr.load_dataset(dname)
            #And finally the dictionaries stored with numpy
            gosf_dir = r"""{}\gos_func.npy""".format(dirname)
            gosd_dir = r"""{}\gos_dict.npy""".format(dirname)
            openf = np.load(gosf_dir,allow_pickle=True)
            gos_funcs = openf[()]
            opend = np.load(gosd_dir,allow_pickle=True)
            gos_dicts = opend[()]
        except Exception as e:
            #We disable the button so we do not keep doing the same mistake
            self.button_results_app_saved.button_type = 'danger'
            self.button_results_app_saved.disabled = True
            print(e)
            self.default_message.object =\
                '#### Something went wrong in the loading process.<br>\
                check that in the given directory\
                the following files are present :\
                <br> -- **results_config.json** -- <br>\
                 -- **ds.nc** -- <br>\
                 -- **ds_first** -- <br>\
                 -- **ds_modi** -- (optional) <br>\
                 -- **gos_dict.npy** -- <br>\
                 -- **gos_func.npy** -- <br>\
                If any is absent, the loading fails.<br>\
                Change directory and try again'
        else:
            #We create the results panel
            self.loaded_res =Results_panel(ds = ds,ds_first=ds_first,ds_modi=ds_modi,\
                colores=color_list,elementos_li=elem_li,onsets=onsets,\
                gos_dictionaries=gos_dicts,gos_functions=gos_funcs,\
                gos_scales=gos_scalings,from_saved=True,dataset_type = dataset_type)
        finally:
            #We get the folders list 
            list_dir = [el2 for el in dirname.split('/') for el2 in el.split('\\')]
            if len(list_dir) >= 3:
                self.fli.directory_access = '{}'.format("\\".join(list_dir[:-3]))
                self.fli._callback_go(True)
            else:
                self.default_message.object =\
                '#### Caution!!!<br>Unable to set the local directory.<br>\
                Subsequent saves may be done in different folders.'
            #And we launch the results panel
            self.loaded_res.create_launch_layout()
            self.loaded_res.layout.show(title='Results Analysis from file',\
            threaded=True,verbose=False)

    def _callback_launch_gosAPP(self,event):
        hv.extension("plotly",logo = False)
        self.gos_app = GOS_surface_analyser()
        self.gos_app.create_layout()

    def change_extension(self):
        #If we launched plotly, we need to go back
        hv.extension('bokeh',logo = False)

    #Callbacks to info functions
    def _callback_info_clust(self,event):
        mss = 'The clustering app requires a valid dateset loaded. \
        It allows for a quick pixel classification attending to spectral \
        characteristics in spectrum images or spectrum lines by using the \
        KMeans, Agglomerative or Spectral clustering algorithms.'
        self.default_message.object = mss

    def _callback_info_NLLSmodel(self,event):
        mss = 'The model creation app launches the panel for the first \
        step in the NLLS analysis routine - It holds the controls for the creation \
        of the model to be fitted. The inclusion of clustering-separated regions may \
        increase the overall speed of convergence for the model in large datasets.'
        self.default_message.object = mss

    def _callback_info_NLLSnewmodel(self,event):
        mss = 'The modified model creator app controls the addition of extra components \
        to the already fitted regions in the model. It also allows to fit some extra regions \
        previously added in the model creation panel. Locking the parameters for the already \
        fitted components may speed up model-convergence.'
        self.default_message.object = mss
    
    def _callback_info_NLLSanalysis(self,event):
        mss = 'The analysis panel allows an assesment of the model goodness after \
        fitting by pressenting the reduced chi squared mappings and residual functions \
        (both for the initial fit from the model-creator and an eventual second \
        fit run from the modified-model-creator).'
        self.default_message.object = mss
    
    def _callback_info_Boot(self,event):
        mss = 'This button gets the current loaded dataset and initializes the available apps.'
        self.default_message.object = mss

    def _callback_info_GOS(self,event):
        mss = 'This button launches an independent app to analyse the generalized oscillator strength \
            (GOS) surfaces and the effects of the experimental parameters on them. \
            The app read the databases of the classic Digital Micrograph suit. If they are \
            not available, it won\'t be launched'
        self.default_message.object = mss

    def _callback_info_NLLSresults(self,event):
        mss = 'The results panel contains several tools for the elemental quantification \
        and oxidation state analysis, based on the of information contained in the fitted \
        models. It also allows the \'goodness\' comparative analysis between the initial and \
        secondary fitting runs'
        self.default_message.object = mss

    def _callback_info_NLLSresults_load(self,event):
        mss = 'We can access the results panel from an already saved state.\
        Copy the folder direction (can be the global direction, from C:\\, or local)\
        and if it contains the needed files, the results panel will be launched'
        self.default_message.object = mss

    def _callback_info_svm(self,event):
        mss = 'SVM analysis'
        self.default_message.object = mss
    
    def _callback_info_GAN(self,event):
        mss = 'GAN analysis'
        self.default_message.object = mss

    def _GOS_data_calculations(self):
        self.gos_data_dict = dict()
        self.onsets = dict()
        for el in self.ox.param['model_element'].objects:    
            self.gos_data_dict[el] = dict()
            self.onsets[el] = self.ox.NLLS.bethe[el].onsets
            sshells = self.ox.NLLS.bethe[el].subshells
            for sshell in sshells:
                #All Qax and Eax are the same, in the whole pack of surfaces
                clave = '_'.join([el,sshell])
                #clave2 = ' '.join([clave,])
                self.gos_data_dict[el][clave] =\
                {'theoretical':cp.deepcopy(self.ox.NLLS.bethe[el]\
                    .theoretical_surf[clave]['data']),\
                'beta-cut':cp.deepcopy(self.ox.NLLS.bethe[el]\
                    .beta_surf[clave]['data']),\
                'F-factor':cp.deepcopy(self.ox.NLLS.bethe[el]\
                    .factor[clave]['data']),\
                'beta-F':cp.deepcopy(self.ox.NLLS.bethe[el]\
                    .factorized_betacut_surface[clave]['data']),\
                'Qax':cp.deepcopy(self.ox.NLLS.bethe[el]\
                    .theoretical_surf[clave]['axis']['Qax']),\
                'Eax':cp.deepcopy((self.ox.NLLS.bethe[el]\
                    .theoretical_surf[clave]['axis']['Eax']-self.onsets[el][clave])/R)}

    def _callback_NLLSresults(self,event):
        #We have to try and extract the data 
        self.change_extension()
        try:
            #We are going to try to get the surfaces for the bethe surface display
            self._GOS_data_calculations()    
        except:
            #In case of no surface available - which should not be the case at this point\
            # - empty dict()
            self.gos_data_dict = dict()
            self.onsets = dict()
        #First fit
        self.button_results_app.name = 'Calculating - WAIT'
        self.button_results_app.button_type = 'warning'
        self.button_results_app.disabled = True
        try:
            self.cols = cp.deepcopy(self.ox.colordict)
        except:
            self.cols = dict()
        if self.type_dataset == 'SIm':
            self._create_results_panels_SIm()
        elif self.type_dataset == 'SLi':
            self._create_results_panels_SLi()

    def _create_results_panels_SIm(self):
        if self.ox.multifit_performed:
            self.ox.NLLS.get_full_results_data()
            self.ox.NLLS.ready_full_set_Xsections(elementos=\
                self.ox.param['model_element'].objects)
            ds_ori = cp.deepcopy(self.ox.NLLS.ds_singles)
            elems = cp.deepcopy(list(self.ox.param['model_element'].objects))
            self.multifit1_done = True
            if self.ox.multifit_rerun:
                self.ox.NLLS.get_full_results_data(type_result='modif')
                ds_modi = cp.deepcopy(self.ox.NLLS.ds_modif)
                self.multifit2_done = True
            else:
                self.multifit2_done = False
        else:
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
            return
        #IN case of having at least one multifit done
        if self.multifit1_done and not self.multifit2_done:
            #We have to calculate the actual whole set of surfaces -\
            #that are compatible with Eloss axis
            self.res = Results_panel(ds  = self.ox.ds,ds_first=ds_ori,\
                colores=self.cols,elementos_li=elems,onsets=self.onsets,\
                gos_dictionaries=self.gos_data_dict,\
                gos_functions=self.ox.NLLS.x_section_fullSet,\
                gos_scales=self.ox.NLLS.scalings_fullSet)
            self.res.create_launch_layout()
            self.res.layout.show(title='Results Analysis Launcher',\
                threaded=True,verbose=False)
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
        elif self.multifit1_done and self.multifit2_done:
            self.res = Results_panel(ds  = self.ox.ds,ds_first=ds_ori,\
                ds_modi = ds_modi,colores=self.cols,elementos_li=elems,\
                onsets=self.onsets,gos_dictionaries=self.gos_data_dict,\
                gos_functions=self.ox.NLLS.x_section_fullSet,\
                gos_scales=self.ox.NLLS.scalings_fullSet)
            self.res.create_launch_layout()
            self.res.layout.show(title='Results Analysis Launcher',\
                threaded=True,verbose=False)
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
        else:
            #Double safety standard - not really neaded...but in place just in case
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
            return

    def _create_results_panels_SLi(self):
        if self.ox.multifit_performed:
            self.ox.NLLS.get_full_results_data_SLines()
            self.ox.NLLS.ready_full_set_Xsections(elementos=\
                self.ox.param['model_element'].objects)
            ds_ori = cp.deepcopy(self.ox.NLLS.ds_singles)
            elems = cp.deepcopy(list(self.ox.param['model_element'].objects))
            self.multifit1_done = True
            if self.ox.multifit_rerun:
                self.ox.NLLS.get_full_results_data(type_result='modif')
                #ds_modi = cp.deepcopy(self.ox.NLLS.ds_modif)
                self.multifit2_done = True
            else:
                self.multifit2_done = False
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
        else:
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
            return
        if self.multifit1_done:
            #We have to calculate the actual whole set of surfaces -\
            #that are compatible with Eloss axis
            self.res = Results_panel(ds  = self.ox.ds,ds_first=ds_ori,\
                colores=self.cols,elementos_li=elems,onsets=self.onsets,\
                gos_dictionaries=self.gos_data_dict,\
                gos_functions=self.ox.NLLS.x_section_fullSet,\
                gos_scales=self.ox.NLLS.scalings_fullSet,dataset_type = 'SLi')
            self.res.create_launch_layout()
            self.res.layout.show(title='Results Analysis Launcher',\
                threaded=True,verbose=False)
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
        else:
            #Double safety standard - not really neaded...but in place just in case
            self.button_results_app.disabled = False
            self.button_results_app.name = 'Results'
            self.button_results_app.button_type = 'success'
            return
        

    def _callback_kickstart_app(self,event):
        print(self.fli.beam_energy,self.fli.convergence_angle,self.fli.collection_angle)
        if any([val <= 0 for val in \
            [self.fli.beam_energy,self.fli.convergence_angle,self.fli.collection_angle]]):
            #Safe mode
            self.button_collect_start.button_type = 'warning'
            self.button_collect_start.name = 'Parameter-Error'
            self.button_collect_start.disabled = True
            mss = 'One (or more) of the experimental parameters is not defined.\
                Beam energy       : {} keV\n\
                Convergence angle : {} mrad\n\
                Collection angle  : {} mrad\n\
                Check the data provided and try again'\
                .format(*[self.fli.beam_energy,self.fli.convergence_angle,self.fli.collection_angle])
            self.default_message.object = mss
            self.default_message.style = {'color':'coral','text-align':'justify'}
            time.sleep(3)
            self.button_collect_start.disabled = False
            self.button_collect_start.button_type = 'success'
            self.button_collect_start.name = 'Boot Apps'
            return

        self.change_extension()
        if self.fli.active_file:
            #print('Booting app')
            #Once it is booted... we need to create the saving file system
            if 'Savings-Workspace' not in os.listdir():
                os.mkdir('Savings-Workspace')
            try:
                name = self.fli.ds.attrs['original_name'].split('.')[0]
            except Exception as e:
                print(e)
                name = 'Sample_NoName'
            finally:
                if name not in os.listdir('./Savings-Workspace'):
                    os.mkdir('./Savings-Workspace/{}'.format(name))
            #### Now to the apps booting
            if self.fli.type_dataset == 'SLi':
                self.type_dataset = 'SLi'
                self.start_SL_apps()
            elif self.fli.type_dataset == 'SIm':
                #print('Booting SI')
                self.type_dataset = 'SIm'
                self.start_SI_apps()
            else:
                #By now we do not want single spectrum initializating anything
                return
            #self.panel_new_mod  = self.ox._new_model_panel_constructor()
            
        else:
            self.button_clustering_app.disabled = True
            self.button_model_constructor.disabled = True
            self.button_analyser_constructor.disabled = True
            self.button_new_model_creator.disabled = True
            self.button_results_app.disabled = True
            self.button_collect_start.button_type = 'success'
            self.button_collect_start.name = 'Boot Apps'
            return

    def start_SI_apps(self): 
        #print('Booting clustp')
        self.mkclust = mk_cl_SI(self.fli.ds)
        self.mkclust.create_panel()
        #print('Booting oxi panel')
        self.ox = oxiSIm_panel(self.fli.ds)
        #print('creating panel model')
        self.panel_mod  = self.ox._model_panel_constructor()
        #print('creting analysis panel')
        self.panel_analysis = self.ox._result_analysis_panel_construction()
        self.button_clustering_app.disabled = False
        self.button_model_constructor.disabled = False
        self.button_analyser_constructor.disabled = False
        self.button_new_model_creator.disabled = False
        self.button_results_app.disabled = False
        self.button_collect_start.button_type = 'success'
        self.button_collect_start.name = 'Reboot Apps'

    def start_SL_apps(self):
        self.mkclust = mk_cl_SL(self.fli.ds)
        self.mkclust.create_panel()
        self.ox = oxiSLi_panel(self.fli.ds)
        self.panel_mod  = self.ox._model_panel_constructor()
        self.button_clustering_app.disabled = False
        '''
        self.button_analyser_constructor.disabled = False
        self.button_new_model_creator.disabled = False
        '''
        self.button_model_constructor.disabled = False
        self.button_results_app.disabled = False
        self.button_collect_start.button_type = 'success'
        self.button_collect_start.name = 'Reboot Apps'
    
    def _callback_clustering_app(self,event):
        try:
            if 'clustering_saves'.casefold() not in [el.casefold() for el in os.listdir()]:
                #So we cannot overwrite existing folders
                os.mkdir('clustering_saves')
            self.change_extension()
            self.mkclust.cluster_layout.show(title = 'Clustering App',threaded=True)
            #Let's create the folder to save in the current workspace

        except: return

    def _callback_create_model_panel(self,event):
        try:
            self.change_extension()
            self.panel_mod.show(title = 'Model Constructor',\
                threaded = True,verbose = False)
        except: return
        '''
        else:
            if self.type_dataset == 'SIm':
                #This is a little trick to bump the image to the right place
                self.ox.def_image_placeholder.object =\
                self.ox.def_image_placeholder.object
            else:
                pass
        '''
        
    def _callback_create_analyser_panel(self,event):
        if not self.ox.multifit_performed:
            return
        try:
            self.change_extension()
            self.panel_analysis.show(title = 'Fitting Analyser',\
                threaded = True,verbose = False)
            self.button_new_model_creator.disabled = False
            self.button_results_app.disabled = False
        except: return

    def _callback_modified_model_creator(self,event):
        try:
            self.change_extension()
            self.ox.panel_new_mod.show(title = 'Modified Model Constructor',\
                threaded = True,verbose = False)
        except: return

    #--------------------------ML--------------------------------#

    def _callback_create_svm_panel(self,event):
        try:
            self.change_extension()
            self.panel_mod.show(title = 'SVM analysis',\
                threaded = True,verbose = False)
        except: return

    def _callback_create_gan_panel(self,event):
        try:
            self.change_extension()
            self.panel_mod.show(title = 'GAN Model',\
                threaded = True,verbose = False)
        except: return
    #--------------------------ML--------------------------------#

    def _app_building(self):
        boot_button = pn.Row(
            self.button_collect_start, self.button_info_Boot,
            width=360, margin=(10, 20), height=45,
            styles={"background": "#e3f2fd"}  # light blue
        )
        peripheral_column = pn.Column(
            pn.Row(self.button_launch_GOS, self.button_info_GOS),
            pn.Row(self.button_clustering_app, self.button_info_clust),
            width=360, height=275, margin=(5, 0),
            styles={"background": "#fce4ec"}  # light pink
        )
        NLLS_column = pn.Column(
            pn.Row(self.button_model_constructor, self.button_info_NLLSmodel),
            pn.Row(self.button_analyser_constructor, self.button_info_NLLSanalysis,
                   self.button_new_model_creator, self.button_info_NLLSnewmodel),
            pn.Row(self.button_results_app, self.button_info_NLLSresult),
            pn.pane.Markdown('#### Folder container of saved results',
                            margin=(0, 10), width=300, height=30),
            self.shortcut_results_wid,
            pn.Row(self.button_results_app_saved, self.button_info_NLLSresult_load),
            width=360, height=275, margin=(5, 0),
            styles={"background": "#e8f5e9"}  # light green
        )
        machine_learning = pn.Column(
            pn.Row(self.button_launch_svm, self.button_info_svm),
            pn.Row(self.button_launch_GAN, self.button_info_GAN),
            width=360, height=275, margin=(5, 0),
            styles={"background": "#fff3e0"}  # light orange
        )
        tabs = pn.Tabs(
            ('Peripheral Modules', peripheral_column),
            ('NLLS', NLLS_column),
            ('Machine Leaarning', machine_learning),
            width=360, margin=(10, 20, 5, 20), height=325, tabs_location='above',
            css_classes=['mainHUB_tabs'],
            styles={"background": "#ede7f6"}  # light purple
        )
        info_column = pn.Column(
            pn.layout.Divider(height=3, margin=(0, 5)),
            pn.pane.Markdown('#### Info ', width=250, margin=5, height=25),
            pn.Column(self.default_message, margin=0, height=130, width=360,
                      css_classes=['scrollable_onlyY']),
            pn.layout.Divider(height=3, min_width=200, margin=(0, 5)),
            width=360, margin=(0, 20), height=205,
            styles={"background": "#f9fbe7"}  # light yellow
        )
        app_HUB = pn.Column(
            pn.pane.Markdown('## <span style="display:inline-block;width:1cm;"></span>WhatEELS Control HUB',
                            height=45, margin=(5, 15, 0, 25), width=300),
            boot_button,
            tabs, info_column,
            margin=0, height=725, width=400,
            styles={"background": "#f5f5f5"}  # very light gray
        )
        self.app_layout = pn.Row(app_HUB, self.fli.layout,
                                 styles={"background": "#e0f7fa"})  # cyan
        self.app_layout.show(title='Full app', threaded=True, verbose=False)

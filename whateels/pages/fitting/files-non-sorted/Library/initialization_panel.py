import sys
import time
import os
import hyperspy.api as hs
import holoviews as hv
from holoviews import streams, opts, dim
from holoviews.streams import Selection1D
from holoviews.streams import Stream,param
import panel as pn
import pandas as pd
import bokeh, param
from bokeh.models import HoverTool

import copy as cp
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from random import choice

from visual_displays import formatter,formatter2,Visual_loading

from Loader.src.fileReaders.dmReader.readers import DM_EELS_Reader
###############################################################################

print('Importing - Initializer panel')
hv.extension("bokeh",logo = False)
#Loading the icons

root = [el for el in sys.path if r'\Library\icons' in el][0]


folder_im = pn.pane.SVG('\\'.join([root,'folder-line.svg']),width = 25)
file_correct = pn.pane.SVG('\\'.join([root,'database-setting.svg']),width = 25)
file_incorrect = pn.pane.SVG('\\'.join([root,'unknown-file.svg']),width = 25)

class Fileinput(param.Parameterized):
    #input_name = param.String(default='')
    directory_access = param.String()
    current_dir_fils = param.ObjectSelector()
    current_dir_dirs = param.ObjectSelector()
    convergence_angle = param.Number(default=0.,step = 0.01,bounds = (0.,None))
    beam_energy = param.Integer(default=0,bounds = (0,None))
    collection_angle = param.Number(default=0.,step = 0.01,bounds = (0.,None))
    
    def __init__(self):
        super().__init__()
        hv.extension('bokeh')
        #This 3 class parameters control the relative position of the
        #current folder
        self.default_directory = os.getcwd()
        self.directory_order = [os.getcwd()]
        self.current_position = 0
        #We use the loaded (outside) images for the icons
        self.folder_icon = folder_im
        self.file_icon =  file_correct
        #Accepted_extensions
        self.accepted_extensions = ('hspy','dm3','dm4','msa','hdf5')
        #button reset initial directory
        self.button_reset_dir = pn.widgets.Button(name = '\u2b6e',width = 30,height = 30,align='center')
        self.button_reset_dir.on_click(self._callback_resetdir)
        #button_go to directory written
        self.button_go = pn.widgets.Button(name = 'Go',button_type = 'success',width = 30,height = 30,align='center')
        self.button_go.on_click(self._callback_go)
        self.button_go.disabled = False
        #Previous directory button
        self.button_dir_prev = pn.widgets.Button(name = '\u2bc7',width = 30,height = 30,align='center')
        self.button_dir_prev.on_click(self._callback_prevdir)
        self.button_dir_prev.disabled = True
        #Next directory button
        self.button_dir_next = pn.widgets.Button(name = '\u2bc8',width = 30,height = 30,align='center')
        self.button_dir_next.on_click(self._callback_nextdir)
        self.button_dir_next.disabled = True
        #Select direcctory
        self.button_dir_pick= pn.widgets.Button(name = '\u2bc6',width = 30,height = 30,align='center')
        self.button_dir_pick.on_click(self._callback_seldir)
        #Loading button
        self.button_load_file = pn.widgets.Button(name = 'Load',height = 30,align='center',width  =75)
        self.button_load_file.disabled = True
        self.button_load_file.on_click(self._callback_loadfile)
        #current positions at the beginning
        self.directory_access = os.getcwd()
        self.change_directories_files_available()
        self.sel_dir_wid = pn.Param(self.param['current_dir_dirs'],\
            widgets = {'current_dir_dirs':pn.widgets.Select},\
            parameters = ['current_dir_dirs'],\
            show_name = False,show_labels = False,width = 400)
        self.sel_fil_wid = pn.Param(self.param['current_dir_fils'],\
            widgets = {'current_dir_fils':pn.widgets.Select},\
            parameters = ['current_dir_fils'],\
            show_name = False,show_labels = False,width = 400)
        self.sel_dir_wid[0].height = 35
        self.sel_fil_wid[0].height = 35
        #initializing in current directory
        self.param['directory_access'].default = os.getcwd() 
        self.directory_input = pn.Param(self.param['directory_access'],\
            widgets = {'directory_access':pn.widgets.TextInput},\
            parameters = ('directory_access'),\
            show_name = False,show_labels = False,\
            max_width = 1100,width_policy = 'max',width = 850)
        self.directory_input[0].height = 35
        #Widgets for the experimental setup
        self.titulo = pn.pane.Markdown('### No data selected',width=200,min_width=200)
        self.beam_ener_wid = pn.Param(self.param['beam_energy'],\
            widgets = {'beam_energy':pn.widgets.Spinner},\
            parameters = ['beam_energy'],name = 'BeamEnergy-E0 keV',\
            show_labels = False,show_name = True,width = 215)
        self.beam_ener_wid[1].disabled = True
        self.conv_angl_wid = pn.Param(self.param['convergence_angle'],\
            widgets = {'convergence_angle':pn.widgets.Spinner},\
            parameters = ['convergence_angle'],name = 'Convergence-\u03B1 mrad',\
            show_labels = False,show_name = True,width = 215)
        self.conv_angl_wid[1].disabled = True
        self.coll_angl_wid = pn.Param(self.param['collection_angle'],\
            widgets = {'collection_angle':pn.widgets.Spinner},\
            parameters = ['collection_angle'],name = 'Collection-\u03B2 mrad',\
            show_labels = False,show_name = True,width = 215)
        self.coll_angl_wid[1].disabled = True
        #initial assesment of the visualizaed file
        if self.current_dir_fils.split('.')[-1] in self.accepted_extensions:
            self.button_load_file.disabled = False
            self.button_load_file.button_type = 'success'
        else: pass
        #This parameter serves to watch if we had loaded any file
        self.active_file = False
    
    @param.depends('current_dir_fils',watch = True)
    def _allow_loading(self):
        #method watching if the file is actually a valid type for loading
        extension = self.current_dir_fils.split('.')[-1]
        if extension in self.accepted_extensions:
            self.button_load_file.disabled = False
            self.button_load_file.button_type = 'success'
        else:
            self.button_load_file.disabled = True
            self.button_load_file.button_type = 'default'

    def change_directories_files_available(self):
        lista_dir = []
        lista_file = []
        for direct in os.listdir():
            if os.path.isdir(direct):
                lista_dir.append(direct)
            else:
                lista_file.append(direct)
        self.param['current_dir_dirs'].objects = lista_dir
        if len(lista_dir) != 0:
            self.current_dir_dirs = lista_dir[0]
        self.param['current_dir_fils'].objects = lista_file
        if len(lista_file)!= 0:
            self.current_dir_fils = lista_file[0]
    
    def _callback_go(self,event):
        try:
            os.chdir(self.directory_access)
        except:
            self.directory_access = os.getcwd()
        else:
            self.directory_order = [self.directory_access,]
            self.current_position = 0
            self.change_directories_files_available()
            self.button_dir_next.disabled = True
            self.button_dir_prev.disabled = True

    def _callback_resetdir(self,event):
        self.button_dir_next.disabled = True
        self.button_dir_prev.disabled = True
        if os.getcwd() != self.default_directory:
            os.chdir(self.default_directory)
            self.directory_access = self.default_directory
            self.directory_order = [self.default_directory,]
            self.current_position = 0
            self.change_directories_files_available()
    
    def _callback_prevdir(self,event):
        self.current_position -= 1
        os.chdir('../')
        self.directory_access = os.getcwd()
        self.change_directories_files_available()
        self.button_dir_next.disabled = False
        if self.current_position == 0:
            self.button_dir_prev.disabled = True
        
    def _callback_nextdir(self,event):
        self.current_position += 1
        self.button_dir_prev.disabled = False
        os.chdir(self.directory_order[self.current_position])
        self.change_directories_files_available()
        self.directory_access = os.getcwd()
        if os.getcwd() == self.directory_order[-1]:
            self.button_dir_next.disabled = True

    def create_ds(self,name):
        #MEthod to create the xarray dataset from the file given
        try:
            #si = hs.load(name)
            si = DM_EELS_Reader(name).read_data()
        except:
            return 0
        else:
            data = si.data #shape (Eloss,Y,X) 
            data = data.transpose((1, 2, 0)) #shape (y,x,eloss) se tiene que cambiar o xarray no va
            #E = si.axes_manager[-1].axis
            E = si.energy_axis
            #as - SImages (Eloss,Y,X)=(0,1,2) - SLines(Eloss,X) - SingleSpectrum (Eloss,)
            if len(data.shape) == 3:
                self.type_dataset = 'SIm' #SpectrumImage
                ys = np.arange(0,data.shape[0])
                xs = np.arange(0,data.shape[1])
            elif len(data.shape) == 2:
                self.type_dataset = 'SLi' #SpectrumLine
                ys = np.arange(0,data.shape[0])
                xs = np.zeros((1),dtype = np.int32)
                shap = list(data.shape)
                shap.insert(1,1)
                data = data.reshape(shap)
            elif len(data.shape) == 1:
                self.type_dataset = 'SSp' #SingleSpectrum
                xs = np.zeros((1),dtype = np.int32)
                ys = np.zeros((1),dtype = np.int32)
                shap = [1,1]
                shap.extend(list(data.shape))
                data = data.reshape(shap)
            else:
                return 0
            ds = xr.Dataset({'ElectronCount':(['y','x','Eloss'],data)},\
            #ds = xr.Dataset({'ElectronCount':(['x','y','Eloss'],data)},\
            coords= {'y' : ys, 'x' : xs,'Eloss' : E})
            metadata = si
            #metadata = si.metadata
            #ds.attrs['original_axes_manager'] = si.axes_manager
            ds.attrs['original_name'] = name
            ds = self._loading_EELS_instrumental_parameters(ds,metadata)
            return ds

    """   
    def create_ds(self,name):
        #MEthod to create the xarray dataset from the file given
        try:
            #si = hs.load(name)
            si = DM_EELS_Reader(name).read_data()
        except:
            return 0
        else:
            data = si.data
            data = data.reshape(())
            #E = si.axes_manager[-1].axis
            E = si.energy_axis
            #as - SImages (Eloss,Y,X)=(0,1,2) - SLines(Eloss,X) - SingleSpectrum (Eloss,)
            if len(data.shape) == 3:
                self.type_dataset = 'SIm' #SpectrumImage
                ys = np.arange(0,data.shape[1])
                xs = np.arange(0,data.shape[-1])
            elif len(data.shape) == 2:
                self.type_dataset = 'SLi' #SpectrumLine
                ys = np.arange(0,data.shape[0])
                xs = np.zeros((1),dtype = np.int32)
                shap = list(data.shape)
                shap.insert(1,1)
                data = data.reshape(shap)
            elif len(data.shape) == 1:
                self.type_dataset = 'SSp' #SingleSpectrum
                xs = np.zeros((1),dtype = np.int32)
                ys = np.zeros((1),dtype = np.int32)
                shap = [1,1]
                shap.extend(list(data.shape))
                data = data.reshape(shap)
            else:
                return 0
            ds = xr.Dataset({'ElectronCount':(['y','x','Eloss'],data)},\
            coords= {'Eloss' : E,  'y' : ys, 'x' : xs})
            #ds = xr.Dataset({'ElectronCount':(['x','y','Eloss'],data)},\
            #coords= {'Eloss' : E,  'y' : ys, 'x' : xs})
            #metadata = si
            #metadata = si.metadata
            #ds.attrs['original_axes_manager'] = si.axes_manager
            ds.attrs['original_name'] = name
            ds = self._loading_EELS_instrumental_parameters(ds,si)
            return ds
    """ 
    def _callback_loadfile(self,event):
        hv.extension('bokeh')
        result = self.create_ds(self.current_dir_fils)
        if type(result) != xr.core.dataset.Dataset:
            return
        else:
            self.active_file = True    
            self.ds = result
            #self._loading_EELS_instrumental_parameters(self.ds)
            #Let's create the structures
            self.beam_energy = self.ds.attrs['beam_energy']
            self.collection_angle = self.ds.attrs['collection_angle']
            self.convergence_angle = self.ds.attrs['convergence_angle']
            self.pl = Visual_loading(self.ds)  
            self.pl.create_panels()
            #Unlocking the panels for teh exp parameters
            self.beam_ener_wid[1].disabled = False
            self.conv_angl_wid[1].disabled = False
            self.coll_angl_wid[1].disabled = False
            if self.pl.type_dataset == 'SIm':
                self.titulo.object = '### Spectrum Image'
            elif self.pl.type_dataset == 'SLi':
                self.titulo.object = '### Spectrum Line'
            elif self.pl.type_dataset == 'SSp':
                self.titulo.object = '### Single Spectrum'
            try:
                #Trying to display visually the loaded panel
                self.visualization_panel.pop(0)
                self.visualization_panel.append(self.pl.struc)
            except:
                pass
    
    def _loading_EELS_instrumental_parameters(self,ds,si):
        '''
        Method that searchs for the instrumental parameters in the metadata of the loaded spectra.
        The following are expected  - Beam-energy
                                    - Collection angle
                                    - Convergence angle
        If some is not present, it is initialized to 0 by default
        '''
        #I didn't came up with an elegant way, so the course one it is ...
        #Collection angle
        try:     collection_angle =\
            round(float(si.collection_angle),2)
        except Exception as e:
            print(e)  
            collection_angle = 0.
        finally: ds.attrs['collection_angle'] = collection_angle 
        #Beam energy
        try:     beam_energy = int(si.beam_energy)
        except Exception as e:
            print(e)
            beam_energy = 0
        finally: ds.attrs['beam_energy'] = beam_energy
        #Convergence angle
        try:     convergence_angle =\
            round(float(si.convergence_angle),2)
        except Exception as e:
            print(e)
            convergence_angle = 0.
        finally: ds.attrs['convergence_angle'] = convergence_angle
        #We return now the modified ds
        return ds

    @param.depends('beam_energy', watch=True)
    def _manual_setting_EELS_beam(self):
        ''' Interactive method
        This is a reactive method. Each time we change manually in the dashboard the values of
        Beam energy 
        They are updated in the self.ds attributes
        '''
        self.ds.attrs['beam_energy']       = int(self.beam_energy)
        #self.ds.attrs['convergence_angle'] = round(self.convergence_angle,2)
        #self.ds.attrs['collection_angle']  = round(self.collection_angle,2)

    @param.depends('convergence_angle', watch=True)
    def _manual_setting_EELS_convergence(self):
        ''' Interactive method
        This is a reactive method. Each time we change manually in the dashboard the values of
        Convergence angle
        They are updated in the self.ds attributes
        '''
        #self.ds.attrs['beam_energy']       = int(self.beam_energy)
        self.ds.attrs['convergence_angle'] = round(self.convergence_angle,2)
        #self.ds.attrs['collection_angle']  = round(self.collection_angle,2)

    @param.depends('collection_angle', watch=True)
    def _manual_setting_EELS_collection(self):
        ''' Interactive method
        This is a reactive method. Each time we change manually in the dashboard the values of
        Collection angle
        They are updated in the self.ds attributes
        '''
        #self.ds.attrs['beam_energy']       = int(self.beam_energy)
        #self.ds.attrs['convergence_angle'] = round(self.convergence_angle,2)
        self.ds.attrs['collection_angle']  = round(self.collection_angle,2)

    def _callback_seldir(self,event):
        try:
            #In case of having an actual directory selected
            os.chdir(self.current_dir_dirs)
        except:
            return
        else:
            self.directory_access = os.getcwd()
            self.button_dir_prev.disabled = False
            self.current_position+=1
            self.directory_order = self.directory_order[:self.current_position]
            self.directory_order.append(os.getcwd())
            self.change_directories_files_available()

    def create_layout(self):
        up_bar = pn.Row(self.button_dir_prev, self.button_dir_next,\
            self.button_reset_dir, self.button_go, self.directory_input,\
            width=1100)
        
        next_row = pn.Row(pn.Spacer(width=15, height=35),\
            pn.Row(self.folder_icon, width=35, height=35, align='center'),\
            self.sel_dir_wid, self.button_dir_pick,\
            pn.Spacer(width=25, height=35),\
            pn.Row(self.file_icon, width=35, height=35, align='center'),\
            self.sel_fil_wid, self.button_load_file,\
            width=1100)
        self.parameters_visual = pn.Row(\
            pn.Row(self.titulo, width=290, min_width=205, align='center'),\
            self.beam_ener_wid, self.conv_angl_wid, self.coll_angl_wid,\
            align='center', width=1100)
        self.parameters_visual[0].margin = (0,0,0,105)
        self.visualization_panel = pn.Column(\
            pn.Spacer(height=445, width=890),\
            height=550, width=1000, min_width=900)
        self.layout = pn.Column(up_bar, next_row, self.parameters_visual, self.visualization_panel)
        self.layout[-1].margin = (10,15,0,50)
        #self.pan.show()

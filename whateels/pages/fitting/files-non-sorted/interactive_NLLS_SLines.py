import sys
import time
import os
import hyperspy.api as hs
from Library.Database.elements import elements

import holoviews as hv
from holoviews import streams, opts, dim
from holoviews.streams import Selection1D
from holoviews.streams import Stream,param
import hvplot.xarray
import panel as pn
import pandas as pd
import bokeh, param
import hvplot.networkx as hvnx
import networkx as nx
from bokeh.models import HoverTool

import copy as cp
import xarray as xr
import numpy as np
import lmfit
import matplotlib.pyplot as plt
from random import choice

from lmfit import Model
from lmfit.models import ExponentialModel,PowerLawModel,ConstantModel
from lmfit.models import GaussianModel,LorentzianModel,BreitWignerModel,SplitLorentzianModel

from nlls_functions import NLLS_fitting

from scipy.signal import medfilt
from scipy.integrate import simpson
from scipy.interpolate import InterpolatedUnivariateSpline

print('Importing - Shell for the model constructor of Spectrum Lines')
hv.extension("bokeh",logo = False)
try:
    root_css = [el for el in sys.path if r'\Library\css' in el][0]
except Exception as e:
    print('No root for css found. Skipping loading')
    print(e)
else:
    css_file = '{}\\css_styling.css'.format(root_css)
    if css_file not in pn.config.css_files:
        pn.config.css_files.append(css_file)


#These functions, classes and class-methods create some of the interactive plotting widgets
def formatter(value):
    #Method to format the yaxis format (Electron Counts)
    return '{:+.2e}'.format(value)

def formatter_Sli_xax(value):
    #Method to format the yaxis format (Electron Counts)
    return '{:.0f}'.format(value)

def hook_black_image(plot, element):
    plot.handles['plot'].border_fill_color = 'black'
    plot.handles['xaxis'].axis_label_text_color = 'white'
    plot.handles['yaxis'].axis_label_text_color = 'white'
    plot.handles['xaxis'].major_label_text_color = 'white'
    plot.handles['yaxis'].major_label_text_color = 'white'
    plot.handles['xaxis'].axis_line_color = 'white'
    plot.handles['yaxis'].axis_line_color = 'white'
    plot.handles['yaxis'].major_tick_line_color = 'white'
    plot.handles['xaxis'].major_tick_line_color = 'white'
    plot.handles['yaxis'].minor_tick_line_color = 'white'
    plot.handles['xaxis'].minor_tick_line_color = 'white'
    plot.handles['xaxis'].axis_label_text_font_style = 'bold'
    plot.handles['yaxis'].axis_label_text_font_style = 'bold'

def hook_full_black_black_with_legend(plot, element):
    plot.handles['plot'].border_fill_color = 'black'
    plot.handles['xaxis'].axis_label_text_color = 'white'
    plot.handles['yaxis'].axis_label_text_color = 'white'
    plot.handles['xaxis'].major_label_text_color = 'white'
    plot.handles['yaxis'].major_label_text_color = 'white'
    plot.handles['plot'].title.text_color = 'white'
    plot.handles['xaxis'].axis_line_color = 'white'
    plot.handles['yaxis'].axis_line_color = 'white'
    plot.handles['yaxis'].major_tick_line_color = 'white'
    plot.handles['xaxis'].major_tick_line_color = 'white'
    plot.handles['yaxis'].minor_tick_line_color = 'white'
    plot.handles['xaxis'].minor_tick_line_color = 'white'
    plot.handles['xaxis'].axis_label_text_font_style = 'bold'
    plot.handles['yaxis'].axis_label_text_font_style = 'bold'
    plot.handles['plot'].legend.background_fill_alpha = 1
    plot.handles['plot'].legend.background_fill_color = 'black'
    plot.handles['plot'].legend.inactive_fill_alpha = 0.5
    plot.handles['plot'].legend.inactive_fill_color = 'black'
    plot.handles['plot'].legend.label_text_alpha = 1
    plot.handles['plot'].legend.label_text_color = 'white'
    plot.handles['plot'].legend.label_text_font_style = 'bold'
    
def hook_full_black(plot, element):
    #This serves to give format to a plotting object in the dark-theme config
    plot.handles['plot'].border_fill_color = 'black'
    plot.handles['xaxis'].axis_label_text_color = 'white'
    plot.handles['yaxis'].axis_label_text_color = 'white'
    plot.handles['xaxis'].major_label_text_color = 'white'
    plot.handles['yaxis'].major_label_text_color = 'white'
    plot.handles['plot'].title.text_color = 'white'
    plot.handles['xaxis'].axis_line_color = 'white'
    plot.handles['yaxis'].axis_line_color = 'white'
    plot.handles['yaxis'].major_tick_line_color = 'white'
    plot.handles['xaxis'].major_tick_line_color = 'white'
    plot.handles['yaxis'].minor_tick_line_color = 'white'
    plot.handles['xaxis'].minor_tick_line_color = 'white'
    plot.handles['xaxis'].axis_label_text_font_style = 'bold'
    plot.handles['yaxis'].axis_label_text_font_style = 'bold'

#########################################################################################
#Plotting_stuff
#########################################################################################
class plotting(param.Parameterized):
    #This class takes the original SI and shows a plot of the components
    def __init__(self, ds):
        self.ds = ds
        #These are the reference images.
        #First thing's first - padding calculations
        self.im = hv.Image(self.ds.ElectronCount,kdims = ['Eloss','y'])\
            .opts(cmap = 'Greys_r',framewise = True,\
                invert_yaxis=True,shared_axes= False,\
                ylabel = 'Line pixel #',\
                frame_width = 600,frame_height = 125,yformatter=formatter_Sli_xax,\
                xaxis = None,toolbar = 'right',alpha = 1,bgcolor = 'grey',\
                hooks = [hook_black_image])
        
        #We also define here the streams that make the graphs reactive
        #self.hovering = streams.DoubleTap(x = 0, y = 0, source = self.im)
        self.tap = streams.SingleTap(x = self.ds.Eloss.values[0],y = -1, source = self.im)
        self.hov_lims = (self.ds.Eloss.data[0],self.ds.Eloss.data[-1],\
            self.ds.y.data[0]-0.5,self.ds.y.data[-1]+0.5)
        
    def plot_curve(self,x,y):
        #Method in charge of plotting the spectrum when hovering over the image
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            curve = hv.Area([], 'Eloss', 'ElectronCount')\
                .opts(yformatter=formatter,frame_width = 600,shared_axes = False)
            curve.relabel('Tick formatters')
            return curve
        elif y >= yf or y <= yi:
            curve = hv.Area([], 'Eloss', 'ElectronCount')\
                .opts(yformatter=formatter,frame_width = 600,shared_axes = False)
            curve.relabel('Tick formatters')
            return curve
        else:
            E0,y0 = self.im.closest((x,y))
            #col = self.colores[int(self.ds['labs'].isel(y = int(y0),Eloss = int(E0)).values)]
            curve = hv.Area(self.ds.ElectronCount.isel(x = 0,y = int(y0)))\
            .opts(fill_color = 'lavender',line_color = 'white',line_width = 1.25,\
            fill_alpha = 0.75,yformatter=formatter,frame_width = 600,\
            framewise = True,shared_axes = False)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve    

    def create_panel(self):
        #this method creates the objects for the panel
        self.din2 = hv.DynamicMap(self.plot_curve,streams=[self.tap])\
            .opts(frame_height= 250,frame_width = 600,\
            framewise=True,yformatter=formatter,\
            shared_axes=False,show_grid = True,\
            toolbar = 'right',\
            hooks = [hook_full_black],bgcolor = 'black')
        return (self.im,self.din2)
    
class residual_plotting(param.Parameterized):
    def __init__(self,ds_totals):
        self.ds_totals = cp.deepcopy(ds_totals)
        xsize = self.ds_totals.x.values.size
        ysize = self.ds_totals.y.values.size
        dist = abs(ysize-xsize)
        if xsize < ysize:
            self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
            self.ylims = (-0.5,ysize-0.5)
        else:
            self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
            self.xlims = (-0.5,xsize-0.5)
        #self.ds_compos = cp.deepcopy(ds_total_components)
        #self.ds_stderr = cp.deepcopy(ds_stderr_matrices)
        #Heatmap of the total assembly of clusters - redChi
        self.hmap = hv.HeatMap(self.ds_totals.ReducedChiSq)\
            .opts(aspect = 'equal',xaxis=None,yaxis=None,\
            invert_yaxis=True,tools=['hover','tap'],\
            frame_height = 300,\
            xlim = self.xlims,ylim = self.ylims,\
            shared_axes=False,cmap = 'cividis',\
            nonselection_line_color = 'white',\
            selection_alpha = 1,nonselection_alpha = 0.5,\
            selection_line_alpha=1,selection_line_color='red',line_width=0.5,\
            nonselection_line_alpha=0.20)
        
        self.str_tap = streams.SingleTap(x = -1,y = -1,source = self.hmap)
        #self.str_hover = streams.PointerXY(x = 0,y = 0,source =self.hmap)
        
        self.hov_lims = (self.ds_totals.x.data[0]-0.5,self.ds_totals.x.data[-1]+0.5,\
            self.ds_totals.y.data[0]-0.5,self.ds_totals.y.data[-1]+0.5)
        
        self.image_ref = hv.Image(self.ds_totals.ReducedChiSq)\
            .opts(aspect = 'equal',xaxis=False,yaxis=False,\
            invert_yaxis=True,tools=['hover','tap'],\
            xlim = self.xlims,ylim = self.ylims,\
            frame_height = 300,shared_axes=False)
    
    def _return_residual(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            curve = hv.Curve([], 'Eloss', 'ElectronCount').opts(shared_axes=False)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve
        elif y >= yf or y <= yi:
            curve = hv.Curve([], 'Eloss', 'ElectronCount').opts(shared_axes=False)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve
        else:
            x0,y0 = self.image_ref.closest((x,y))
            self.x_idx = int(x0)
            self.y_idx = int(y0)
            curve = hv.Curve(self.ds_totals.Residuals.isel(x = int(x0),y = int(y0)))\
            .opts(shared_axes=False,color = 'red')
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve

    def _return_signal_best_fit(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            curve = hv.Curve([], 'Eloss', 'ElectronCounts (BestFit)').opts(shared_axes=False)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve
        elif y >= yf or y <= yi:
            curve = hv.Curve([], 'Eloss', 'ElectronCounts (BestFit)').opts(shared_axes=False)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve
        else:
            x0,y0 = self.image_ref.closest((x,y))
            curve1 = hv.Curve(self.ds_totals['ElectronCounts (BestFit)'].isel(x = int(x0),y = int(y0)))\
                .opts(color = 'orange',shared_axes=False)
            curve1.relabel('Tick formatters').opts(yformatter=formatter)
            return curve1

    def _return_signal(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            curve2 = hv.Area([], 'Eloss', 'ElectronCount').opts(shared_axes=False)
            curve2.relabel('Tick formatters').opts(yformatter=formatter)
            return curve2
        elif y >= yf or y <= yi:
            curve2 = hv.Area([], 'Eloss', 'ElectronCount').opts(shared_axes=False)
            curve2.relabel('Tick formatters').opts(yformatter=formatter)
            return curve2
        else:
            x0,y0 = self.image_ref.closest((x,y))
            curve2 = hv.Area(self.ds_totals['ElectronCounts [a.u.]'].isel(x = int(x0),y = int(y0)))\
                .opts(fill_alpha = 0.15,color = 'navy',shared_axes=False)
            curve2.relabel('Tick formatters').opts(yformatter=formatter)
            return curve2
    
    
    def create_panel(self):
        #this method creates the objects for the panel
        '''#Legacy options .... they work poorly
        self.widget_indices = pn.Param(self.param,\
            widgets = {'x_idx':pn.widgets.Spinner,'y_idx':pn.widgets.Spinner},\
            parameters = ['x_idx','y_idx'],show_labels = False, show_name = False)
        dinmap_residual = hv.DynamicMap(self._return_residual,streams=[self.str_hover])\
            .opts(frame_height= 250,frame_width = 300,framewise=True,yformatter=formatter,\
            show_grid = True,shared_axes=False)
        dinmap_best_signal = hv.DynamicMap(self._return_signal_best_fit,streams=[self.str_hover])\
            .opts(frame_height= 250,frame_width = 300,framewise=True,yformatter=formatter,\
            show_grid = True,shared_axes=False)
        dinmap_signal  = hv.DynamicMap(self._return_signal,streams=[self.str_hover])\
            .opts(frame_height= 250,frame_width = 300,framewise=True,yformatter=formatter,\
            show_grid = True,shared_axes=False)
        '''
        #Static version for carefull analysis
        dinmap_resi_static = hv.DynamicMap(self._return_residual,streams=[self.str_tap])\
            .opts(frame_height= 300,frame_width = 625,framewise=True,yformatter=formatter,\
            show_grid = True,shared_axes=False)
        dinmap_best_static = hv.DynamicMap(self._return_signal_best_fit,streams=[self.str_tap])\
            .opts(frame_height= 300,frame_width = 625,framewise=True,yformatter=formatter,\
            show_grid = True,shared_axes=False)
        dinmap_signal_static = hv.DynamicMap(self._return_signal,streams=[self.str_tap])\
            .opts(frame_height= 300,frame_width = 625,framewise=True,yformatter=formatter,\
            show_grid = True,shared_axes=False)
        
        return self.hmap,dinmap_resi_static,dinmap_best_static,dinmap_signal_static

'''    
def hook_full_black(plot, element):
    #This serves to give format to a plotting object in the dark-theme config
    plot.handles['plot'].border_fill_color = 'black'
    plot.handles['xaxis'].axis_label_text_color = 'white'
    plot.handles['yaxis'].axis_label_text_color = 'white'
    plot.handles['xaxis'].major_label_text_color = 'white'
    plot.handles['yaxis'].major_label_text_color = 'white'
'''

#########################################################################################
#########################################################################################
#########################################################################################
#Actual Class for the app
#########################################################################################
#This is the part for teh panel creation
#########################################################################################
#########################################################################################
#########################################################################################
#########################################################################################

class oxi_panel(param.Parameterized):
    #Parameters for the interactive functionalities of this class
    elemento = param.ObjectSelector(default='C',objects=sorted(elements.keys()))
    subshell = param.ListSelector(default=[],objects = ['K','K1a'])
    model_element = param.ObjectSelector(objects=['NoElement'])
    model_type_component = param.ObjectSelector(default='continuum',objects=['continuum','ELNES'])
    model_component = param.ObjectSelector(objects=['Empty'])
    #Parameters for the model options exposed - initial values and constraints
    center = param.Number(0.)
    amplitude = param.Number(0.,step = 1)
    sigma = param.Number(0.,step = 0.01)
    model_comp_func = param.ObjectSelector(default='Gaussian component',\
        objects=['Gaussian component','Lorentzian component',\
            'Pseudovoigt component','Splitlorentzian component'])
    center_max_min = param.Range(default=(0, 5.))
    amplitude_min = param.Number(default=0.)
    flat_component = param.Boolean(default= False) #This will lock amp = 0 of a component
    sigma_max_min = param.Range(default=(0, 1.))
    allow__parameter_modifications = param.Boolean(default=False)
    A = param.Number(0.,step = 0.25)
    A_min = param.Number(default=0.,step = 0.25)
    chem = param.Number(0.)
    allow_chem = param.Boolean(default=False)
    area = param.ObjectSelector(default='default',objects=['default'])
    file_clust = param.ObjectSelector(default='NoFile',objects=['NoFile',])
    path_toClust = param.String(default='./')
    show_center = param.Boolean()
    show_fwhm = param.Boolean()
    #Parameters to create new components
    new_compo_areas = param.ListSelector(default=['default'],objects=['default'])
    new_compo_name = param.String(default = '')
    new_compo_func = param.ObjectSelector(default='gaussian',\
        objects=['gaussian','lorentzian',\
            'pseudovoigt','splitlorentzian'])
    new_compo_energy = param.Number(default = 0.)
    new_compo_elements = param.ObjectSelector(default = 'NoElement',objects = ['NoElement'])
    new_compo_flex = param.ObjectSelector(default = 'low',objects = ['low','medium','high'])
    new_compo_toggle = param.Boolean(False)
    #Parameters for the multifit interactive tab
    multifit_area = param.ListSelector(objects=[])
    prog = param.Integer(default = 0)
    ETC = param.String(default = 'ETC : None s (None s total)')
    list_of_ETCs = param.String(default = '')
    #Analysis panel parameters
    multifit_performed = param.Boolean(default = False)
    multifit_rerun = param.Boolean(default = False)
    fitted_areas_list = param.ListSelector(objects=[])
    fitted_areas_list2 = param.ObjectSelector(objects=[])
    red_chi_sq_cmap = param.ObjectSelector(default='cividis',\
        objects = ['plasma','inferno','viridis','cividis','gray','magma'])
    red_chi_theme = param.ObjectSelector(default='light',objects=['dark','light','gray'])
    change_analysis_disp_graph = param.Boolean(default = False)
    full_median_text = param.String(default = 'Median Reduced \u03A7\u00b2 : -- ')
    full_time_text = param.String(default = 'Total fitting elapsed time : -- s')
    partial_median_text = param.String(default = 'Median Reduced \u03A7\u00b2<br>for cluster -- : -- ')
    partial_time_text = param.String(default = 'Elapsed time on cluster -- fitting : -- s')
    overlay_clusters_RCS = param.Boolean(False)
    element_analysis = param.ObjectSelector(default = 'NoElement',objects = ['NoElement'])
    param_analysis = param.ListSelector(objects = ['center','amplitude','sigma'])
    param_cmap_upperLimit = param.Integer(default=100)
    result_ELNES_compo = param.ObjectSelector(default = 'NoELNES',objects = ['NoELNES'])
    #Parameters to lock components in a second re-run of multifit
    lock_ELNES     = param.ListSelector(objects = ['center','amplitude','sigma'])
    #lock_all        = param.Boolean(default = False)
    lock_continuum  = param.Boolean(default = False)
    analysis_chem   = param.Number(default=0,bounds = (-10,10))
    elements_re_run = param.ObjectSelector(default = 'NoElements',objects = ['NoElements'])
    elnes_re_run    = param.ObjectSelector(default = 'NoELNES',objects = ['NoELNES'])
    continuum_re_run = param.ObjectSelector(default = 'NoComponent',objects = ['NoComponent'])
    fitted_areas_list3 = param.ObjectSelector(objects = [])
    type_tree = param.ObjectSelector(default = 'tree',objects=['tree','spring-like','radial'])
    #NOw the controls to actually add the clusters/compos to the mix and start the fitting
    clusters_with_newcomps = param.ObjectSelector(default = 'NoCluster',objects=['NoCluster'])
    added_list_compos = param.ListSelector(objects=['NoNewComponents'])
    current_added_component = param.DataFrame()
    non_fitted_clusters = param.ObjectSelector(objects=[])
    non_fitted_clusters_list = param.ListSelector(objects=[])
    use_locking_dictionary = param.Boolean(default = True)
    #Parameters for the progress bars in the new multifit launch
    progress_preparing = param.Integer(default = 0)
    progress_multifitting_prev = param.Integer(default = 0)
    progress_newModels = param.Integer(default = 0)
    fitted_areas_list_last = param.ListSelector(objects=[])
    #These parameters are added with the spectrum line developement effort
    overlay_cluster_on_image = param.Boolean(default = False)
    #To Change the x-section used in the models and activate the soften option
    soft_edges = param.Boolean(default = True)
    x_section_type = param.ObjectSelector(default = 'beta-cut',objects = ['theoretical','beta-cut','F-factor'])

    def __init__(self,ds):
        super().__init__()
        self.current_el = self.elemento        
        #The subshell dictionary form the listed elements in hyperspy
        self.subshell_dictionary = dict()
        self.ref_fit_area = 'Selected Area'
        for el in elements:
            try:
                elements[el]['Atomic_properties']['Binding_energies']
            except:
                pass
            else:
                self.subshell_dictionary[el] = []
                for ssh in elements[el]['Atomic_properties']['Binding_energies']:
                    #onset = elements[el]['Atomic_properties']['Binding_energies']\
                    #[ssh]['onset_energy (eV)']
                    if '5' == ssh[-1]:
                        #self.subshell_dictionary[el].append('{}54 - {} eV'.format(ssh[0],onset))
                        self.subshell_dictionary[el].append('{}54'.format(ssh[0]))
                    elif '3' == ssh[-1]:
                        #self.subshell_dictionary[el].append('{}32 - {} eV'.format(ssh[0],onset))
                        self.subshell_dictionary[el].append('{}32'.format(ssh[0]))
                    elif '2' == ssh[-1] or '4' == ssh[-1]:
                        pass
                    else:
                        self.subshell_dictionary[el].append('{}'.format(ssh))
        #Once Solved the available elements - those with actual subshells listed
        self.param['elemento'].objects = sorted(self.subshell_dictionary.keys())
        #The data -----------------------------------------------------------------------
        self.ds = cp.deepcopy(ds)
        xsize = self.ds.x.values.size
        ysize = self.ds.y.values.size
        dist = abs(ysize-xsize)
        if xsize < ysize:
            self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
            self.ylims = (-0.5,ysize-0.5)
        else:
            self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
            self.xlims = (-0.5,xsize-0.5)
        self.pl = plotting(ds)
        #self.default_image,self.point_image,self.dynamic_graphs_1 = self.pl.create_panel()
        self.default_image,self.dynamic_graphs_1 = self.pl.create_panel()
        self.Eini = self.ds.Eloss.data[0]
        self.Eend = self.ds.Eloss.data[-1]
        self.new_compo_energy = int(self.Eini + (self.Eend-self.Eini)/2) 
        self.param['new_compo_energy'].bounds = (self.Eini,self.Eend)
        self.param['new_compo_energy'].step = self.ds.Eloss.data[1] - self.ds.Eloss.data[0]
        self.param['center'].step =  self.ds.Eloss.data[1] - self.ds.Eloss.data[0]
        self.param['chem'].step =  self.ds.Eloss.data[1] - self.ds.Eloss.data[0]
        self.NLLS = NLLS_fitting(self.ds)
        self.param['analysis_chem'].step = self.ds.Eloss.data[1] - self.ds.Eloss.data[0]
        #Dictionary for the analysis tab - Rerun lock components
        self.locking_dict = dict()
        #Buttons ------------------------------------------------------------------------
        #Add element
        self.button_add_element = pn.widgets.Button(name = 'Add element',\
            disabled=False,button_type='primary')
        self.button_add_element.on_click(self._callback_select_element)
        #Create model_components
        self.button_create_model = pn.widgets.Button(name = 'Create model components',\
            disabled=True,button_type='default')
        self.button_create_model.on_click(self._callback_create_default_model)
        #Remove component from model
        self.button_remove_component = pn.widgets.Button(name = 'Remove component',\
            disabled=True,button_type='danger')
        self.button_remove_component.on_click(self._callback_remove_component_model)
        #Reset to empty model
        self.button_reset = pn.widgets.Button(name = 'Delete model?',\
            disabled=True,button_type='default')
        self.button_reset.disabled = True
        self.button_reset.on_click(self._callback_enable_delete_model)
        self.button_delete_model = pn.widgets.Button(name = 'Delete',\
            disabled=True,button_type='default')
        self.button_delete_model.disabled = True
        self.button_delete_model.on_click(self._callback_delete)
        self.button_deactivate_delete = pn.widgets.Button(name = 'Back',\
            disabled=True,button_type='default')
        self.button_deactivate_delete.disabled = True
        self.button_deactivate_delete.on_click(self._callback_deactivate_delete)
        #Loading clustering components
        self.button_load_cluster = pn.widgets.Button(name = 'Load cluster file',\
            button_type='default')
        self.button_load_cluster.disabled = True
        self.button_load_cluster.on_click(self._callback_open_cluster_ref)
        self.button_add_clusters = pn.widgets.Button(name = 'Add clusters to models',\
            button_type='default')
        self.button_add_clusters.disabled = True
        self.button_add_clusters.on_click(self._callback_add_clusters_ref)
        #Reset initial values for the paramenters
        self.button_reset_parameters = pn.widgets.Button(name = 'Reset parameters',\
            button_type= 'warning')
        self.button_reset_parameters.on_click(self._callback_resert_param_values)
        self.button_reset_parameters.disabled = True 
        #Fit current references
        self.button_fit_references = pn.widgets.Button(name = 'Fit Reference Spectra',\
            button_type = 'default')
        self.button_fit_references.disabled = True 
        self.button_fit_references.on_click(self._callback_fit_references)
        self.button_fit_ref_select_area = pn.widgets.Button(name = self.ref_fit_area,\
            button_type = 'default')
        self.button_fit_ref_select_area.on_click(self._callback_select_fit_ref_areas)
        self.button_fit_ref_select_area.disabled = True
        #This is a special button
        self.button_show_center = pn.Param(self.param,widgets={'show_center':pn.widgets.Toggle},\
            parameters = ['show_center'],show_name = False,\
            show_labels = False,width = 150,margin = (5,10))
        self.button_show_sigmas = pn.Param(self.param,widgets={'show_fwhm':pn.widgets.Toggle},\
            parameters = ['show_fwhm'],show_name = False,\
            show_labels = False,width = 150,margin = (5,10))
        #Button to add components
        self.button_add_extra_compo = pn.widgets.Button(name = 'Add extra component',\
            button_type = 'default')
        self.button_add_extra_compo.disabled = True
        self.button_add_extra_compo.on_click(self._callback_create_extra_component)
        #Button to add extra components in a rerun
        '''
        self.button_add_extra_compo_rerun = pn.widgets.Button(name = 'Add new component / re-Run',\
            button_type = 'default')
        self.button_add_extra_compo_rerun.disabled = True
        self.button_add_extra_compo_rerun.on_click(self._callback_create_extra_component_rerun)
        '''
        #Button to activate the second model fitting
        #Button to be clicked to start the multifit
        self.button_multifit = pn.widgets.Button(name = 'MultiFit',\
            button_type = 'default')
        self.button_multifit.disabled = True
        self.button_multifit.on_click(self._callback_multifit)
        #Button for the rerun
        #TODO impleent it in the tab structure
        #Button toggle for the new component center to be displayed
        self.button_new_compo_center_show = pn.Param(self.param['new_compo_toggle'],\
            widgets = {'new_compo_toggle':pn.widgets.Toggle},\
            parameters = ['new_compo_toggle'],\
            show_labels = False,width = 50)
        self.button_new_compo_center_show[0].name = 'Show'
        self.button_new_compo_center_show[0].disabled = True
        self.button_new_compo_center_show[0].button_type = 'default'
        self.button_overlay_clusters_model = pn.Param(\
            self.param['overlay_cluster_on_image'],\
            widgets = {'overlay_cluster_on_image':pn.widgets.Toggle},\
            parameters = ['overlay_cluster_on_image'],width = 150,show_name = False,\
            show_labels = False,margin = (5,10))
        self.button_overlay_clusters_model[0].button_type = 'primary'
        self.button_overlay_clusters_model[0].name = 'Overlay clusters'
        self.button_overlay_clusters_model[0].disabled = True

        #Button forcing the display of reduced chi square solutions
        #Legacy app - no longer available
        '''
        self.button_show_chi_sqr = pn.widgets.Button(name = 'Show red.ChiSq maps',\
            width = 250)
        self.button_show_chi_sqr.on_click(self._callback_show_redChisqr)
        self.button_show_chi_sqr.button_type = 'default'
        self.button_show_chi_sqr.disabled = True
        '''
        #To enable the multifit run analysis
        '''
        self.button_analysis_run = pn.widgets.Button(name = 'Get multifit results for analysis',\
            width = 275)
        self.button_analysis_run.disabled = True
        self.button_analysis_run.on_click(self._callback_get_analysis_data)
        '''
        #Button to get the results after rerunning
        '''
        self.button_analysis_rerun = pn.widgets.Button(name = 'Get \'Re-Run\' results for analysis',\
            width = 275)
        self.button_analysis_rerun.disabled = True
        self.button_analysis_rerun.on_click(self._callback_get_analysis_rerun_data)
        '''
        #This button changes the displayed graph in the analysis tab lateral bar
        self.button_change_info_display = pn.Param(self.param['change_analysis_disp_graph'],\
            widgets = {'change_analysis_disp_graph':pn.widgets.Toggle},\
            parameters = ['change_analysis_disp_graph'],\
            show_labels = False,width = 275,margin = (0,37))
        self.button_change_info_display[0].name = 'Showing fitted areas'
        self.button_change_info_display[0].disabled = True
        #This button changes the style of the total red-chi-square heatmap
        '''
        self.button_change_styling_RCS = pn.widgets.Button(name = 'Change Style',width = 275)
        self.button_change_styling_RCS.disabled = True
        self.button_change_styling_RCS.on_click(self._callback_change_styles_totRCS)
        '''
        #This button overlays cluster limits with the RCS mappings
        self.button_overlay_cluster_RCS = pn.Param(self.param['overlay_clusters_RCS'],\
            widgets = {'overlay_clusters_RCS':pn.widgets.Toggle},\
            parameters = ['overlay_clusters_RCS'],show_labels = False, show_name = False,width = 275)
        self.button_overlay_cluster_RCS[0].disabled = True
        self.button_overlay_cluster_RCS[0].button_type = 'default'
        #This button adds a new column of Error Heatmaps
        '''
        self.button_add_column_errormaps = pn.widgets.Button(name = 'Add Error mapping',width = 235)
        self.button_add_column_errormaps.disabled = True
        self.button_add_column_errormaps.on_click(self._callback_add_errormaps)
        '''
        #This button erase a column of error maps
        '''
        self.button_erase_column_errormaps = pn.widgets.Button(name = 'Erase Error mapping',width = 235)
        self.button_erase_column_errormaps.disabled = True
        self.button_erase_column_errormaps.on_click(self._callback_erase_errormaps)
        '''
        #BUtton to activate possible rerun
        '''
        self.button_activate_rerun = pn.widgets.Button(name = 'Begin New/Modified model configuration',\
            width = 300)
        self.button_activate_rerun.disabled = True
        self.button_activate_rerun.on_click(self._callback_activate_possible_rerun)
        '''
        #Buttons to lock all components and unlock all components
        '''
        self.button_lock_all = pn.widgets.Button(name = 'Lock All',width = 135)
        self.button_lock_all.disabled = True
        self.button_lock_all.on_click(self._callback_lock_all_comp)
        self.button_unlock_all = pn.widgets.Button(name = 'Unlock All',width = 135)
        self.button_unlock_all.disabled = True
        self.button_unlock_all.on_click(self._callback_unlock_all_comp)
        '''
        #Control of the model in this class ----------------------------------------------
        self.model_element_dict = {'default':dict()}
        self.model = False
        #Interactive elements -------------------------------------------------------------
        #Energy onset display widget
        self.text_pane = pn.pane.Markdown('Choose Subshell/s',\
            margin = (0,0,10,20),\
            sizing_mode="stretch_width",\
            height_policy='fit',styles={'font-family': "Arial",'color' : 'white'})
        #Model element-type-component selection buttons
        self.mod_el = pn.Param(self.param,\
            widgets={'model_element' : pn.widgets.RadioButtonGroup,\
                'model_type_component' : pn.widgets.RadioButtonGroup,\
                'model_component': pn.widgets.RadioButtonGroup},\
            parameters = ['model_element','model_type_component','model_component'],\
            show_name = False,default_layout = pn.GridBox)
        self.mod_el[0][2].disabled = True
        #ELNES Parameter values
        #And customization --------------------------------------------------------------
        self.model_ELNES_parameters = pn.Param(self.param,\
            widgets={'center' : pn.widgets.FloatSlider,\
                'center_max_min' : pn.widgets.RangeSlider,\
                'amplitude' : pn.widgets.FloatSlider,\
                'amplitude_min' : pn.widgets.FloatSlider,\
                'sigma' : pn.widgets.FloatSlider,\
                'sigma_max_min' : pn.widgets.RangeSlider},\
            parameters = ['center','center_max_min','amplitude',\
                'amplitude_min','sigma','sigma_max_min' ],\
            show_name = False,default_layout = pn.GridBox)
        for el in self.model_ELNES_parameters[0]:
            if 'enter' in el.name:
                el.bar_color = '#009F93'
            elif 'mplitude' in el.name:
                el.bar_color = '#F9546B'
            elif 'igma' in el.name:
                el.bar_color = '#FFDB60'
        for el in self.model_ELNES_parameters[0]:
            if 'max min' in el.name:
                el.name = ''
            elif 'Amplitude min' == el.name:
                el.name = 'Min'
        self.model_ELNES_parameters.layout.objects[0].ncols = 3
        for el in self.model_ELNES_parameters[0]:
            el.disabled = True
        #Continuum Parameter values
        #And customization --------------------------------------------------------------
        self.model_continuum_parameters = pn.Param(self.param,\
            widgets={'A' : pn.widgets.FloatSlider,\
                'A_min' : pn.widgets.FloatSlider,\
                'chem' : pn.widgets.FloatSlider,\
                'allow_chem' : pn.widgets.Toggle},\
            parameters = ['A','A_min','chem','allow_chem'],\
            show_name = False,default_layout = pn.GridBox)
        for el in self.model_continuum_parameters[0]:
            if 'Chem' == el.name:
                el.bar_color = '#FC7651'
            elif 'A' == el.name[0]:
                el.bar_color = '#F9546B'
        self.model_continuum_parameters[0][0].name = 'Amplitude'
        self.model_continuum_parameters.layout.objects[0].ncols = 2
        for el in self.model_continuum_parameters[0]:
            el.disabled = True
        #By default
        self.parameter_configurator =\
        self.model_continuum_parameters
        self.parameter_configurator.default_layout.ncols = 1
        #Creation of the tools for clustering loading
        path_widget = pn.Param(self.param,widgets={'path_toClust' : pn.widgets.TextInput},\
            parameters = ['path_toClust'],show_name = False, name = 'Path to clustering file')
        file_widget = pn.Param(self.param,widgets={'file_clust':pn.widgets.Select},\
            parameters = ['file_clust'],show_name = False, name = 'File foulder to load')
        #For the overlay between SI and masks of different areas
        '''
        image_xr = xr.Dataset({'counts':(['y','x'],\
            self.ds.sum('Eloss').ElectronCount.values)},\
            coords = {'x':self.ds.x.values,'y':self.ds.y.values})
        self.image_SI = hv.Image(image_xr,kdims=['x','y']).\
            opts(aspect = 'equal',invert_yaxis=True,cmap = 'Greys_r',\
            xaxis=None, yaxis=None,\
            xlim = self.xlims,ylim = self.ylims)
        self.image_for_analysis = hv.Image(image_xr,kdims=['x','y']).\
            opts(aspect = 'equal',invert_yaxis=True,cmap = 'Greys_r',\
            xaxis=None, yaxis=None,frame_width = 225,\
            xlim = self.xlims,ylim = self.ylims)
        '''
        self.cmap_binary = ['black','aquamarine']
        '''
        self.overlay_image = hv.Overlay([self.image_SI]).\
            opts(frame_height = 250)
        '''
        self.area_selector = pn.Param(self.param['area'],\
            widgets={'area':pn.widgets.Select},\
            parameters=['area'], show_name = False,\
            show_labels = False,width = 150,margin = (5,10))
        self.area_selector[0].disabled = True
        '''
        self.area_selector = pn.Column(\
            pn.pane.Markdown('### Model Configuration Panel'),\
            pn.layout.Divider(margin = (-10,0,0,0)),\
            pn.pane.Markdown('### Area Selector'),\
            
            self.overlay_image,\
            margin = (0,0,10,0))
        self.area_selector[-2].show_labels = False
        self.area_selector[2].margin = (5,15)
        '''
        #For the clustering area selector
        #The loading cluster box - defined here to be addressed at any time
        file_widget.name = ''
        path_widget.name = ''
        file_widget.show_labels = False
        path_widget.show_labels = False
        #widget_box to load cluster
        self.colores = [] #Initialized empty to avoid local variable undefined error
        self.colordict = dict()
        self.box = pn.Column('### Cluster-loading path & file',\
            path_widget,file_widget,\
            pn.Row(self.button_load_cluster,self.button_add_clusters,width = 250),\
            margin = (0,0,30,0),background = 'black')
        self.box[0][0].margin = (0,5,-10,5)
        self.box[0].style = ({'color' : 'white'})
        self.box.margin = (5,15)
        self.def_cluster_im = hv.Image(self.ds.ElectronCount,kdims = ['y','Eloss'])\
            .opts(cmap = 'Greys_r',alpha = 0,\
            xaxis=None, yaxis=None,frame_height = 75,frame_width = 250,\
            bgcolor = 'black',\
            xlim = self.xlims,ylim = self.ylims,\
            border = 0, toolbar = None)

        self.cluster_placeholder = pn.pane.HoloViews(self.def_cluster_im,margin = (75,25))
        self.cluster_box_pane = pn.Row(self.box,self.cluster_placeholder,\
            background='black',width = 665)
        #The sign that shows the current model area displaying parameters
        self.mk1 = pn.pane.Markdown('#### _Selected area_ :',\
            style={'font-family': "Arial",'color':'white','height' : '25px','padding':'0px 10px 5px 10px'})
        style = {'font-family':'Arial','color':self.cmap_binary[-1],\
            'background':'black',\
            #'border-radius': '10px','border': '1px white solid',\
            'height' : '25px','padding':'0px 10px 5px 10px'}
        self.mk2 = pn.pane.Markdown('#### - {} -'.format(self.area),\
            style = style,width = 150)
        self.current_area_mkdwn = pn.GridBox(self.mk1,self.mk2,background = 'black',\
            ncols=2,height = 40,width = 290)
        #The component type of funtion for the ELNES elements
        self.default_compo_funcs = cp.deepcopy(self.param['model_comp_func'].objects)
        self.button_compo_func = pn.Param(self.param,\
            widgets = {'model_comp_func' : pn.widgets.Select},\
            parameters = ['model_comp_func'],\
            default_layout=pn.GridBox,show_labels = False,\
            show_name = False)
        self.button_compo_func.disabled = True
        #Extra dictionary for fwhm from sigmas
        self.fwhm_dict = {'Gaussian':(lambda sig: 2*sig*np.sqrt(2*np.log(2))),\
            'Lorentzian':(lambda sig: 2*sig),\
            'Pseudovoigt':(lambda sig: 2*sig),\
            'Splitlorentzian':(lambda sig: 2*sig)}
        #For the overlay of reference spectra
        empty_ds = xr.Dataset({'Empty Curves':\
            (['Eloss'],np.zeros_like(self.ds.Eloss.values))},\
            coords = {'Eloss':cp.deepcopy(self.ds.Eloss.values)})
        self.default_curve_references = hv.Curve(empty_ds)\
            .opts(frame_height = 250,frame_width = 600,\
            show_grid = True,yformatter=formatter,bgcolor = 'black',\
            hooks = [hook_full_black],\
            ylabel = 'Electron Counts',xlabel = 'Electron Energy Loss [eV]') 
        self.dictionary_references = {'empty':self.default_curve_references}
        #Dictionaries to store fittings of the reference spectra
        self.dictionary_fitted_ref = dict()
        self.dictionary_fitted_ref_compos = dict()
        self.dictionary_fitted_ref_overall = dict()
        #The progress bar
        self.prog_bar = pn.Param(self.param['prog'],\
            widgets = {'prog':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['prog'])
        #This two variables control if the multifit run is fresh or is a re-fit
        self.run_dict = dict()
        self.fresh = True #is it a fresh run? or a re-run (self.fresh = False)
        #This is the placeholder image for the info panel in the analysis window
        '''
        self.init_info_fill_image =  hv.Image(self.ds.ElectronCount.sum(dim = 'Eloss'))\
            .opts(bgcolor = 'black',aspect = 'equal',\
                invert_axes=True,invert_yaxis=True,cmap = 'greys_r',\
                xaxis = None,yaxis = None,padding = 0,frame_height = 200,border = 0,\
                xlim = self.ylims,ylim = self.xlims,\
                hooks = [hook_full_black],shared_axes = False)
        '''
        #These widgets are for locking components in a rerun after analysis
        self.ticking_elnes_boxes = pn.Param(self.param['lock_ELNES'],\
            widgets = {'lock_ELNES':pn.widgets.CheckBoxGroup},
            parameters = ['lock_ELNES'],show_name = False,\
            show_labels = False,width = 150)
        self.param['lock_continuum'].label = 'continuum amplitude'
        self.ticking_continuum = pn.Param(self.param['lock_continuum'],\
            widgets = {'lock_continuum':pn.widgets.Checkbox},
            parameters = ['lock_continuum'],\
            show_labels = True,width = 150)
        self.select_area_fixing = pn.Param(self.param['fitted_areas_list3'],\
            widgets = {'fitted_areas_list3':pn.widgets.Select},\
            parameters = ['fitted_areas_list3'],\
            name = 'Select Area',show_name = True,show_labels = False,width = 270)
        self.select_elements_rerun = pn.Param(self.param['elements_re_run'],\
            widgets = {'elements_re_run':pn.widgets.RadioButtonGroup},\
            parameters = ['elements_re_run'],name = 'Element',\
            show_name = True,show_labels = False,width = 290)
        self.select_elnes_rerun = pn.Param(self.param['elnes_re_run'],\
            widgets = {'elnes_re_run':pn.widgets.RadioButtonGroup},\
            parameters = ['elnes_re_run'],name = 'ELNES parameter controls',\
            show_name = True,show_labels = False,width = 290)
        self.select_continuum_rerun = pn.Param(self.param['continuum_re_run'],\
            widgets = {'continuum_re_run':pn.widgets.RadioButtonGroup},\
            parameters = ['continuum_re_run'],name = 'Continuum parameter controls',\
            show_name = True,show_labels = False,width = 290)
        self.ticking_elnes_boxes[0].disabled = True
        self.ticking_continuum.disabled = True
        self.select_area_fixing[0].disabled = True
        self.select_elements_rerun[1].disabled = True
        self.select_elnes_rerun[1].disabled = True
        self.select_continuum_rerun[1].disabled = True
        self.flag_truth_table = False
        self.flag_component_display = False
        self.extra_added_components_multifit = dict()
        #The indicator for the first fit
        self.first_fit = True
        self.first_fit_rerun = True

    def _callback_select_element(self,event):
        #The elements for the model
        if self.subshell != []:
            lista  = []
            #The elements created must be added everywhere - default
            self.model_element_dict['default'][self.elemento] = dict()
            for ssh in self.subshell:
                if ssh[-1] == '4':
                    inner = [''.join([ssh[0],el]) for el in ['5','4']]
                    lista.extend(inner)
                elif ssh[-1] == '2':
                    inner = [''.join([ssh[0],el]) for el in ['3','2']]
                    lista.extend(inner)
                else:
                    lista.append(ssh)
            #Now we have the sshells and element in the desired format
            self.NLLS.add_element(self.elemento,lista)
            if 'NoElement' in self.param['model_element'].objects: 
                nom = self.elemento
                self.param['model_element'].objects = list(self.model_element_dict['default'].keys())
                self.model_element = nom
                #self.param['model_element'].objects.remove('NoElement')
                
            else:
                self.param['model_element'].objects = list(self.model_element_dict['default'].keys())
        else: pass
    
    def _callback_open_cluster_ref(self,event):
        try:
            self.dsCluster = xr.open_zarr('/'.join([self.path_toClust,self.file_clust]))
            self.button_add_clusters.disabled = False
            self.button_add_clusters.button_type = 'primary'
        except:
            self.button_add_clusters.disabled = True
            self.button_add_clusters.button_type = 'default'
            self.cluster_im = self.def_cluster_im
        else:
            #IN case of having an actual cluster ds
            #Let's configure colors to be displayed
            cluster_number = self.dsCluster['label_number'].values
            long =  cluster_number.size
            #My default selected colors
            self.colores = ['navy','gold','deepskyblue','crimson','lawngreen',\
                'orange','blueviolet','forestgreen','silver']
            #In case of having more clusters than elements in self.colores
            #- random choice to fill list
            while long > len(self.colores):
                selection = choice(bokeh.colors.named.__all__)
                if selection not in self.colores:
                    #So we do not repeat colors
                    self.colores.append(selection)
                else: pass
            #Now, let's add the image to the place it belongs
            self.cluster_im = hv.Image(self.dsCluster['labs'])\
                .opts(\
                    invert_yaxis = True,\
                    xaxis=None, yaxis=None,cmap = self.colores[:long],\
                    #xlim = self.xlims,ylim = self.ylims,\
                    shared_axes= False,\
                    frame_height = 75,frame_width = 250,\
                    alpha = 0.60,\
                    bgcolor = 'white',\
                    border = 0, toolbar = None\
                    )
            self.cluster_placeholder.object = self.cluster_im
            self.button_overlay_clusters_model[0].disabled = False
            #self.cluster_box_pane.pop(-1)
            #self.cluster_box_pane.append(self.cluster_im)
            #self.cluster_box_pane[-1].margin = (15,70,10,70)

    def _callback_add_clusters_ref(self,event):
        lista = ['default']
        try:
            self.NLLS.add_clustering_references(self.dsCluster)
        except:
            return #Safety measure for the button, in case of malfunctioning
        else:
            #In case of having added something - we need to modify the defaults dict
            #Carefull - when adding a new reference with lower cluster numbers, the 
            #options to modify the previous extra clusters are hidden...but they still exist
            #within the NLLS model class
            for el in self.dsCluster.label_number.values:
                ar = 'cluster_{}'.format(el)
                self.model_element_dict[ar] =\
                    cp.deepcopy(self.model_element_dict['default'])
                lista.append(ar)
                #Safety measure for the amplitudes
                for elem in self.param['model_element'].objects:
                    for ssh in self.NLLS.models_components[ar][elem]['ELNES']:
                        amp = self.NLLS.models_components[ar][elem]\
                            ['ELNES'][ssh]['amplitude']
                        self.model_element_dict[ar][elem]\
                            ['ELNES'][ssh]['amplitude'] = amp
        finally:
            #Let's add the new buttons to the area selector
            self.area_selector[0].disabled = False
            self.param['area'].objects =\
                cp.deepcopy(lista)
            self.area = self.param['area'].objects[0]
            self.param['new_compo_areas'].objects = cp.deepcopy(lista)
            self.new_compo_areas = []
            #Let's add the references as well to the SI visualization tab
            #Let's delete the previous posible clusters from the dictionary
            
            for i,el in enumerate(self.param['area'].objects):
                if el != 'default':
                    self.colordict[el] = self.colores[i-1]
                    self.dictionary_references[el] =\
                        hv.Area(data = xr.Dataset({'ElectronCounts':(['Eloss [eV]'],\
                            self.NLLS.ref_spectra[el])}\
                        ,coords = {'Eloss [eV]':self.NLLS.Eloss}))\
                        .opts(yformatter=formatter,\
                        shared_axes=False,\
                        #responsive = True,\
                        show_grid = True,line_color = 'white',line_width = 1,\
                        fill_color = self.colores[i-1],frame_height = 250,\
                        frame_width = 600,selection_fill_alpha = 1,\
                        nonselection_fill_alpha = 0.2,nonselection_line_alpha = 0.2,\
                        selection_line_alpha = 1)
                else:
                    self.colordict[el] = 'aquamarine'
            self.dyn_refs_placeholder.object =\
                hv.NdOverlay(self.dictionary_references)\
                .opts(legend_muted = True,shared_axes = False,\
                bgcolor = 'black',hooks = [hook_full_black_black_with_legend])
            #Let's add the new areas to the new_elements selector
    
    def _callback_create_default_model(self,event):
        #This controls what happens with the app when creating a model ---- a lot!
        self.button_create_model.name = 'Creating model components - WAIT'
        self.button_create_model.button_type = 'warning'
        self.button_create_model.disabled = True 
        #beta-cut is chosen a-priori,since it is the minimun correction always in place
        self.NLLS.ready_elements(type_surface ='beta-cut',extension=True,mesh_p = 256)
        self.NLLS.create_components(self.NLLS.initial_reference_spectra)
        self.button_create_model.disabled = False
        self.button_create_model.name = 'Create model components'
        self.button_create_model.button_type = 'success'
        #As soon as we create components, we get the initial values for the parameters
        #Important - to later hit default button and restore initial param values
        for el in self.NLLS.models_components[self.area]:
            for type_c in self.NLLS.models_components[self.area][el]:
                if '_init_' not in type_c:
                    self.model_element_dict[self.area][el][type_c] = dict()
                    for compo in self.NLLS.models_components[self.area][el][type_c]:
                        self.model_element_dict[self.area][el][type_c][compo] = dict()
                        if type_c == 'continuum':
                            A,chem = cp.deepcopy(self.NLLS.models_components[self.area]\
                                [el][type_c][compo].__defaults__[:2])
                            allow_c = cp.deepcopy(self.NLLS.models_components[self.area]\
                                [el]['continuum_init_const'][compo]['allow_chem'])
                            a_min = cp.deepcopy(self.NLLS.models_components[self.area]\
                                [el]['continuum_init_const'][compo]['A_min'])
                            self.model_element_dict[self.area][el][type_c][compo]['A'] = A
                            self.model_element_dict[self.area][el][type_c][compo]['chem'] = chem
                            self.model_element_dict[self.area][el][type_c][compo]['allow_chem'] = allow_c
                            self.model_element_dict[self.area][el][type_c][compo]['A_min'] = a_min
                        elif type_c == 'ELNES':
                            self.model_element_dict[self.area][el][type_c][compo] =\
                            cp.deepcopy(self.NLLS.models_components[self.area]\
                                [el][type_c][compo])
        #Forcing the update of area to be fitted
        vals = np.ones((self.NLLS.ref_matrices[self.area].shape[0],self.ds.Eloss.size))
        self.NLLS.add_reference_keyMatrix(vals,'default')
        vals[vals == 0] = np.NaN
        xs = self.ds.x.values
        ys = self.ds.y.values
        Eloss = self.ds.Eloss.values
        mask = xr.Dataset({'mask':(['y','Eloss'],vals)},\
                    coords = {'Eloss':Eloss,'y':ys})

        self.mask_im = hv.Image(mask,kdims=['y','Eloss']).opts(aspect = 'equal',\
            invert_yaxis=True,frame_width = 600,\
            cmap = self.cmap_binary,\
            #xlim = self.xlims,ylim = self.ylims,\
            alpha = 0.5)
        '''
        self.overlay_image = hv.Overlay([self.mask_im]).\
            opts(frame_height = 250)
        '''
        #self.overlay_image = hv.Overlay([self.image_SI,self.mask_im]).\
        #    opts(frame_height = 250)
        #TODO come back here to fix the overlay of heatmaps 
        #self.area_selector.pop(-1)
        #self.area_selector.append(self.overlay_image)
        #self.area_selector[-1].margin = (0,0,0,25)
        #Now let's move on
        #Buttons control
        self.button_create_model.disabled = True
        self.button_create_model.button_type = 'default'
        self.button_load_cluster.disabled = False
        self.button_remove_component.disabled = False
        self.button_reset_parameters.disabled = False
        self.model = True
        self.model_element = self.param['model_element'].objects[0]
        for el in self.mod_el[0]:
            el.disabled = False
        self.button_add_element.disabled = True
        self.button_add_element.button_type = 'default'
        self.button_reset.disabled = False
        self.button_reset.button_type = 'warning'
        #The first time we run, we force the creation of the components
        self.param['model_component'].objects =\
                list(self.NLLS.models_components[self.area][self.model_element]\
                [self.model_type_component].keys())
        try:
            self.model_component = self.param['model_component'].objects[0]
        except:
            #This is for the case of having an element without ELNES or continuum components
            self.param['model_component'].objects = ['Empty']
            self.model_component = self.param['model_component'].objects[0]
        #Enabling the parameter modification in case of having components to address
        if self.mod_el[0][2].value != 'Empty':
            for el in self.model_continuum_parameters[0]:
                    el.disabled = False
            for el in self.model_ELNES_parameters[0]:
                el.disabled = False
        else: pass
        #We enable reference fitting controls
        self.button_fit_ref_select_area.disabled = False
        self.button_fit_references.disabled = False
        self.button_fit_references.button_type = 'success'
        #We show the first of the references - the default reference
        self.dictionary_references.pop('empty')
        self.dictionary_references['default'] =\
            hv.Area(data = xr.Dataset({'ElectronCounts':(['Eloss [eV]'],\
                self.NLLS.ref_spectra['default'])}\
            ,coords = {'Eloss [eV]':self.NLLS.Eloss}))\
            .opts(yformatter=formatter,\
            shared_axes=False,\
            selection_fill_alpha = 0.25,\
            nonselection_fill_alpha = 0.1,\
            show_grid = True,line_color = 'white',line_width = 1,\
            fill_color = self.cmap_binary[-1],frame_height = 250,frame_width = 600)
        self.dyn_refs_placeholder.object =\
            hv.NdOverlay(self.dictionary_references)\
            .opts(bgcolor = 'black',hooks = [hook_full_black])
        #Activation of the possibility of viewing the centers
        self.button_show_sigmas[0].disabled = False
        self.button_show_center[0].disabled = False
        #Let's also add the elements to the possible pool of elements of extra components
        self.param['new_compo_elements'].objects =\
            cp.deepcopy(self.param['model_element'].objects)
        self.new_compo_elements = self.param['new_compo_elements'].objects[0]
        #And we allow these components to be added
        self.button_add_extra_compo.disabled = False
        self.button_add_extra_compo.button_type = 'success'
        #We add the default region to the multifit posible regions
        self.param['multifit_area'].objects = ['default']
        #We allow the show button in the new compo center to be activated
        self.button_new_compo_center_show[0].disabled = False
        #Adding the default as an option in the new component areas
        self.param['new_compo_areas'].objects = ['default']
        #setting the path to load cluster files
        self.path_toClust = './clustering_saves'
        
    def _callback_remove_component_model(self,event):
        #Method that allows us to remve a certain component from a certain area in the model
        if self.model_type_component == 'ELNES':
            self.NLLS.delete_component(self.model_element,self.model_component,self.area)
        else:
            return
        #Now...we have to change the component panel, so we avoid any exception raise
        #A good way of doing this, is simply going to the continuum part. We can only remove ELNES
        self.model_type_component = 'continuum'
    
    def _callback_resert_param_values(self,event):
        #Resets the parameters to the initial values
        #It takes the values for the boundaries described as medium flex in the oxispy machinery
        dictio = self.model_element_dict[self.area][self.model_element]\
            [self.model_type_component][self.model_component]
        if self.model_type_component == 'continuum' and self.model_component != 'Empty':
            self.A = round(dictio['A'])
            self.A_min = dictio['A_min']
            self.chem = dictio['chem']
            self.allow_chem = dictio['allow_chem']
        elif self.model_type_component == 'ELNES' and self.model_component != 'Empty':
            self.amplitude = round(dictio['amplitude'])
            self.center = dictio['center']
            self.sigma = dictio['sigma']
            self.model_comp_func =\
                (lambda keyword: ' '.join([keyword.capitalize(),'component']))\
                (dictio['type']) 
        else: pass
        
    def _callback_enable_delete_model(self,event):
        #Small function that controls the flow of info to delete models
        self.button_delete_model.disabled = False
        self.button_delete_model.button_type = 'danger'
        self.button_deactivate_delete.disabled = False
        self.button_deactivate_delete.button_type = 'success'
        self.button_reset.disabled = True
        self.button_reset.button_type = 'default'
        
    def _callback_deactivate_delete(self,event):
        #Small function disabling the deletion of the model
        self.button_reset.disabled = False
        self.button_reset.button_type = 'warning'
        self.button_delete_model.disabled = True
        self.button_delete_model.button_type = 'default'
        self.button_deactivate_delete.disabled = True
        self.button_deactivate_delete.button_type = 'default'
        
    def _callback_delete(self,event):
        #Funtion that deletes the model
        self.model = False
        #Let's disable all the model controls 
        for el in self.model_config_widgets[1][0]:
            el.disabled = True
        self.model_config_widgets[2][0].disabled = True
        self.model_config_widgets[2][1].disabled = True
        for el in self.model_config_widgets[-1][0]:
            el.disabled = True
        #We change the button options, so we do not get errors afterwards
        self.param['model_element'].objects = ['NoElement']
        self.model_element = 'NoElement'
        self.param['model_component'].objects = ['empty']
        self.model_component = 'empty'
        #We need to eleminate the possible cluster references added
        #We also want to clean the reference spectra area
        self.dyn_best_placeholder.object = self.default_curve_references
        self.dyn_best_mkdown.object =\
            '#### Best fit for the reference spectra of the **{}** area'\
            .format(' - None - ')
        self.dyn_best_mkdown.style = {'color':'grey'}
        self.dyn_comp_placeholder.object = self.default_curve_references
        self.dyn_comp_mkdown.object =\
            '#### Fitted individual components for the reference spectra \
            of the **{}** area'.format(' - None - ')
        #And set the area to default
        self.dictionary_references = {'empty':self.default_curve_references}
        self.dictionary_fitted_ref = dict()
        self.dictionary_fitted_ref_compos = dict()
        self.dictionary_fitted_ref_overall = dict()
        '''
        self.dyn_refs_placeholder.object =\
            hv.NdOverlay(self.dictionary_references)\
            .opts(legend_muted = True,shared_axes = False,\
                bgcolor = 'black',hooks = [hook_full_black])
        '''
        self.area = 'default'
        self.param['area'].objects = ['default']
        #Deleting the model - the whole NLLS class
        #And starting again - a lot to be replaced
        self.dictionary_references = {'empty':self.default_curve_references}
        self.dyn_refs_placeholder.object =\
            hv.NdOverlay(self.dictionary_references)\
            .opts(legend_muted = True,shared_axes = False,\
                bgcolor = 'black',hooks = [hook_full_black])
        self.NLLS = NLLS_fitting(self.ds)
        #This is important to avoid conflicts when recreating the model
        self.model_element_dict = {'default' : dict()}
        #Controls of the buttons in the main select element menu
        self.button_add_element.disabled = False
        self.button_add_element.button_type = 'primary'
        self.button_create_model.disabled = True
        self.button_create_model.button_type = 'default' 
        self.button_reset.disabled = True
        self.button_reset.button_type = 'default'
        self.button_delete_model.disabled = True
        self.button_delete_model.button_type = 'default'
        self.button_deactivate_delete.disabled = True
        self.button_deactivate_delete.button_type = 'default'
        self.button_fit_ref_select_area.disabled = True
        self.button_fit_ref_select_area.button_type = 'default'
        self.button_fit_references.disabled = True
        self.button_fit_references.button_type = 'default'
        #Disabling the buttons in the clustering loading window
        self.button_load_cluster.disabled = True
        self.button_load_cluster.button_type = 'default'
        self.button_add_clusters.disabled = True
        self.button_add_clusters.button_type = 'default'
        #Delete and disable the extra components values
        self.button_add_extra_compo.disabled = True
        self.button_add_extra_compo.button_type = 'default'
        self.new_compo_name = ''
        self.param['new_compo_elements'].objects = ['NoElement'] 
        self.new_compo_elements = 'NoElement'
        self.param['new_compo_areas'].objects = ['default']
        self.new_compo_areas = ['default']
        self.button_new_compo_center_show[0].disabled = True
        self.new_compo_toggle = False
        self.button_new_compo_center_show[0].button_type = 'default'
        #The multifit area
        self.list_of_ETCs = ''
        self.button_multifit.disabled = True
        self.button_multifit.button_type = 'default'
        self.multifit_area = []
        self.param['multifit_area'].objects = []
        self.ETC = self.param['ETC'].default
        #The visualization buttons for the center and the sigmas
        self.show_fwhm = False
        self.show_center = False
        self.button_show_center[0].button_type = 'default'
        self.button_show_sigmas[0].button_type = 'default'
        self.button_show_center[0].disabled = True
        self.button_show_sigmas[0].disabled = True
        #Disable multifitting options until new run
        self.multifit_performed = False
        ''' Legacy app - no longer available
        self.button_show_chi_sqr.button_type = 'default'
        self.button_show_chi_sqr.disabled = True
        '''
        #Disable analysis results retrieval
        '''
        self.button_analysis_run.disabled = True
        self.button_analysis_run.button_type = 'default'
        '''
    def _callback_fit_references(self,event):
        #Fits the references available and allows 
        self.button_fit_references.disabled = True
        self.button_fit_references.button_type = 'default'
        self.button_fit_ref_select_area.disabled = True
        if self.ref_fit_area == 'Selected Area':
            self.NLLS.create_model(name_area = self.area)
            self.NLLS.fit_reference(name_area = self.area)
        elif self.ref_fit_area == '  All Areas  ':
            for ars in list(self.NLLS.models_components.keys()):
                self.NLLS.create_model(name_area = ars)
                self.NLLS.fit_reference(name_area = ars)
        else:
            #in case of malfunction do nothing
            pass
        #Now we have fitted the references .... time to retrieve the components back
        #Each time this is called ... the actual references fitted must be refreshed
        for el in self.NLLS.ref_results:
            #We may be overwritting, no problem .... as long as it is updated
            self.dictionary_fitted_ref[el] = cp.deepcopy(self.NLLS.ref_results[el])
            #Now, let's create the dictionary to hold the separated components
            #and the overall result, for the NdOverlays
            #Overall
            try:
                #In case of not adding clustering refs
                self.colordict[el]
            except:
                self.colordict[el] = 'aquamarine'
            ds_counts = xr.Dataset({'ElectronCounts':(['Eloss [eV]'],\
                self.NLLS.ref_spectra[el])}\
                ,coords = {'Eloss [eV]':self.NLLS.Eloss})
            counts_area = hv.Area(data = ds_counts)\
                .opts(yformatter=formatter,\
                shared_axes=False,\
                selection_fill_alpha = 0.5,\
                nonselection_fill_alpha = 0.1,\
                fill_alpha = 0.25,line_width = 1,\
                show_grid = True,line_color = 'white',\
                fill_color = self.colordict[el],\
                frame_height = 250,frame_width = 600,\
                hooks = [hook_full_black])
            overall_fit = hv.Curve(data =\
                xr.Dataset({'ElectronCounts':(['Eloss [eV]'],\
                    self.NLLS.ref_results[el].best_fit)},\
                    coords = {'Eloss [eV]':self.NLLS.Eloss}))\
                .opts(color = 'r',\
                    bgcolor = 'black',\
                    ylabel = 'Electron Counts',xlabel = 'Electron Energy Loss [eV]',\
                    hooks = [hook_full_black],\
                    shared_axes = False)
            self.dictionary_fitted_ref_overall[el] = counts_area*overall_fit
            #Components
            compos  = self.NLLS.ref_results[el].eval_components()
            NdOver_dict = dict()
            for comp in compos:
                ds_comp = xr.Dataset({'ElectronCounts':(['Eloss [eV]'],\
                compos[comp])},coords = {'Eloss [eV]':self.NLLS.Eloss})
                try:
                    idx = comp.index('_')
                except:
                    idx = -1
                NdOver_dict[comp[:idx]] = hv.Area(data = ds_comp)\
                    .opts(yformatter=formatter,\
                    shared_axes=False,\
                    selection_fill_alpha = 0.5,\
                    nonselection_fill_alpha = 0.1,\
                    show_grid = True,\
                    frame_height = 250,frame_width = 600,\
                    bgcolor = 'black',\
                    ylabel = 'Electron Counts',xlabel = 'Electron Energy Loss [eV]',\
                    hooks = [hook_full_black_black_with_legend])
                
            self.dictionary_fitted_ref_compos[el] =\
            hv.Curve(data = ds_counts)\
                .opts(color = 'dodgerblue',alpha = 1,line_width = 2,\
                bgcolor = 'black',\
                ylabel = 'Electron Counts',xlabel = 'Electron Energy Loss [eV]',\
                hooks = [hook_full_black],\
                shared_axes = False)*\
            overall_fit*\
            hv.NdOverlay(NdOver_dict).opts(legend_muted=True)
        #Once created all these components and dictionaries, let's add the current
        #one selected to the display
        if (self.area != 'default') and ('_' in self.area):
            nombre = ' '.join(self.area.capitalize().split('_'))
        else:
            nombre = self.area 
        self.dyn_best_placeholder.object = self.dictionary_fitted_ref_overall[self.area]
        self.dyn_best_mkdown.object =\
            '#### Best fit for the reference spectra of the - **{}** - area'.format(nombre)
        self.dyn_best_mkdown.style = {'color':'white'}
        self.dyn_comp_placeholder.object = self.dictionary_fitted_ref_compos[self.area]
        self.dyn_comp_mkdown.object =\
            '#### Fitted individual components for the reference \
            spectra of the **{}** area'.format(nombre)
        #We recover the button functionality
        self.button_fit_references.disabled = False
        self.button_fit_references.button_type = 'success'
        self.button_fit_ref_select_area.disabled = False
        #We allow the multifit to be done
        self.button_multifit.disabled = False
        self.button_multifit.button_type = 'success'
        #We update the available areas for the multifit
        self.param['multifit_area'].objects = list(self.NLLS.ref_results.keys())
        self.multifit_area = []
        
    def _callback_select_fit_ref_areas(self,event):
        #Changes the area to be fitted on clicks for the reference spectra
        if self.ref_fit_area == 'Selected Area':
            self.ref_fit_area = '  All Areas  '
            self.button_fit_ref_select_area.name = self.ref_fit_area
            self.button_fit_ref_select_area.button_type = 'primary'
        elif self.ref_fit_area == '  All Areas  ':
            self.ref_fit_area = 'Selected Area'
            self.button_fit_ref_select_area.name = self.ref_fit_area
            self.button_fit_ref_select_area.button_type = 'default'
        #If something happens and it get's out of balance - do nothing
        else:pass
    
    def _callback_create_extra_component(self,event):
        if self.model:
            self.button_add_extra_compo.disabled = True
            self.button_add_extra_compo.button_type = 'warning'
            self.button_add_extra_compo.name = 'Adding component'
            for el in self.new_compo_areas:
                self.NLLS.create_extra_component(element = self.new_compo_elements,\
                    name = self.new_compo_name,eloss=self.new_compo_energy,\
                    name_area = el, type_predet = self.new_compo_func,\
                    flex = self.new_compo_flex)
                self.model_element_dict[el][self.new_compo_elements]\
                    ['ELNES'][self.new_compo_name] =\
                cp.deepcopy(self.NLLS.models_components[el][self.new_compo_elements]\
                    ['ELNES'][self.new_compo_name])
            self.button_add_extra_compo.disabled = False
            self.button_add_extra_compo.button_type = 'success'
            self.button_add_extra_compo.name = 'Add extra component'
            self.model_type_component = 'continuum'
    
    #This function - multifit -  is also buriend inside the NLLS_functions library
    #It is repeated here only to be able to see the progress in a progress bar
    #and calculate an estimated time of completion ETC
    
    #def preparing_new_results_multifit(self):
        
    #def multifit_modified(self):
    
    #def multifit_2(self):
    
    #def _callback_multifit_rerun(self,event):
    

    def _callback_multifit(self,event):
        """Method to run a loop through the SI/SL and fit all the pixels
        belonging to the reference area signaled by name_area

        Args:
            name_area (str, optional): Controls the area to be fitted.Label coinciding
                with the different reference models created previously. Defaults to 'default'.
        """
        self.time_per_cluster = dict()
        self.total_time_accumulated = 0
        self.multifit_rerun = False
        self.fresh = True
        self.list_of_ETCs = ''
        self.button_multifit.disabled = True
        self.button_multifit.button_type = 'warning'
        bar_colors = ['primary', 'secondary', 'success', 'info', 'warning', 'danger', 'light', 'dark']
        color_i = 0
        for name_area in self.multifit_area:
            self.button_multifit.name = 'MultiFit on area - {} -'.format(name_area)
            self.prog = 0
            try: 
                array_area = cp.deepcopy(self.NLLS.ref_matrices[name_area][:,0])
            except:
                #IN case of not having a reference matrix set, let's avoid fitting - so no time
                #conumption is spent on nothing
                array_area = np.zeros((self.NLLS.ds.y.values.size,))
            #Now let's select the color of the progress-bar 
            #so the iteration of colors is done properly
            try:
                bar_colors[color_i]
            except:
                color_i = 0
            self.prog_bar[0].bar_color = bar_colors[color_i]
            dimy = array_area.size
            #The number of elements to be fitted for any particular reference, can be known
            #by the sum of the reference matrix - as it is a matrix of ones and zeros 
            tot_iter = array_area[array_area != 0].size
            #num_10per = max(int(tot_iter*0.1),1) #10% of total iterations-to update ETC
            self.prog_bar[0].max = int(tot_iter)
            self.NLLS.results[name_area] = list()
            
            idx_etc = 0
            paramet = self.NLLS.ref_results[name_area].params
            #self.NLLS.results[name_area].append(list())
            self.NLLS.results[name_area] = [[None for _ in range(self.NLLS.ref_matrices[name_area].shape[0])],]
            lista_idxs = list(np.where(self.NLLS.ref_matrices[name_area][:,0] == 1)[0])
            t0 = time.time()
            #for j in range(dimy):
            for j in lista_idxs:
                #t00 = time.time()
                y = self.NLLS.ds.sel(x = 0, y = j).ElectronCount.values
                res = self.NLLS.models[name_area]\
                    .fit(y,params = paramet, x = self.NLLS.Eloss)
                self.NLLS.results[name_area][0][j] = res
                #t01 = time.time()
                idx_etc +=1
                self.prog += 1
                '''    #The progress bar advances
                etc_tot = tot_iter * (t01-t00)
                etc_comp = etc_tot - idx_etc*(t01-t00)
                if idx_etc % num_10per == 0:
                    #So it is not changing every other iteration.
                    self.ETC = 'ETC : {} s ({} s total)'.format(round(etc_comp,2),round(etc_tot,2))
                else: pass
                '''
                #We advance the parameters to be the ones in the later fit.
                #This way, and assuming a certain degree of continuity in the 
                #material, we are close to equilibrium conditions in the next fit
                #by expecting the spectrum image - spectra to vary continuously.
                '''
                if array_area[j] == 1:
                    t00 = time.time()
                    y = self.NLLS.ds.sel(x = 0, y = j).ElectronCount.values
                    res = self.NLLS.models[name_area]\
                        .fit(y,params = paramet, x = self.NLLS.Eloss)
                    self.NLLS.results[name_area][0].append(res)
                    t01 = time.time()
                    idx_etc +=1
                    self.prog += 1    #The progress bar advances
                    etc_tot = tot_iter * (t01-t00)
                    etc_comp = etc_tot - idx_etc*(t01-t00)
                    if idx_etc % num_10per == 0:
                        #So it is not changing every other iteration.
                        self.ETC = 'ETC : {} s ({} s total)'.format(round(etc_comp,2),round(etc_tot,2))
                    else: pass
                    #We advance the parameters to be the ones in the later fit.
                    #This way, and assuming a certain degree of continuity in the 
                    #material, we are close to equilibrium conditions in the next fit
                    #by expecting the spectrum image - spectra to vary continuously.
                    paramet = res.params
                else:
                    #In case of being in pixel outside the fitting range, append none.
                    self.NLLS.results[name_area][0].append(None)
                '''
            t1 = time.time()
            color_i += 1
            tot_time_area = round((t1-t0),2)
            string_to_attach =\
            ' '.join(['Elapsed time of',name_area,': {} s'.format(tot_time_area),'<br>'])
            self.list_of_ETCs += string_to_attach
            self.time_per_cluster[name_area] = tot_time_area
            self.total_time_accumulated += tot_time_area
            #We create the references so we have access later to the analysis params
            self.NLLS._create_reference_components_1strun(name_area,'multi')
        self.button_multifit.name ='MultiFit'
        self.button_multifit.disabled = False
        self.button_multifit.button_type = 'success'
        #Let's run now the reduce_chi_square calculations (extraction)
        #self.dictionaries_RCS_prerun = cp.deepcopy(self.dictionaries_RCS) 
        #Now a parameter that will allow changes in the result analysis panel
        self.multifit_performed = True
        #More post_multifit button management
        #self.button_analysis_run.disabled = False
        #self.button_analysis_run.button_type = 'success'
        #Changes here
        self._callback_get_analysis_data(None)
        
        #self.NLLS.ref_components['rerun'] = cp.deepcopy(self.NLLS.ref_components['multi'])

    def _get_list_areas_first(self):
        """This method modifies a fundamental parameter for later widgets,
        and prepares the data to be displayed in the results window
        """
        self.areas_being_fitted = [area for area in self.NLLS.results]
        self.first_fit = False

    def _callback_get_analysis_data(self,event):
        #This method gets the results of multifit and prepare the visualizations
        #Initialize the dictionaries fot visual objects
        # working here
        '''
        if self.first_fit:
            self._get_list_areas_first()
            #self.panel_new_mod  = self._new_model_panel_constructor()
        else: pass
        '''
        self._get_list_areas_first()
        self._analysis_calculations(self.areas_being_fitted,self.NLLS.results,type_run = 'multi')
        '''
        if not self.first_fit_rerun:
            #In case of having done a rerun already ... reset the tab
            self.analysis_tabs.append(self.show_Error_param_pane)
            self.button_analysis_rerun.disabled = False
            self.button_analysis_rerun.button_type = 'warning'
        else: pass
        

        self._visual_changes_analysis(self.areas_being_fitted)
        self.button_analysis_run.disabled = True
        self.button_analysis_run.button_type = 'default'
        '''

    def _analysis_calculations(self,areas_list,target_results,type_run = 'multi'):
        #The function called to create the data structures needed for the visual representation
        total_red_chi = np.zeros(self.ds.ElectronCount.values.shape[:-1])
        total_resid = np.zeros_like(self.ds.ElectronCount.values)
        total_best_fits = np.zeros_like(self.ds.ElectronCount.values)
        total_compo_eval = dict()
        total_params_eval = dict()
        self.masks_per_area = dict()
        #Calling the info extraction methods and ordering data
        xs_j = self.ds.x.values
        ys_i = self.ds.y.values
        #We need to do this here so we can get the matrices
        for name_area in areas_list:
            self.NLLS.get_best_fit_components(name_area,target_results,type_run,type_data = 'SLi')
            self.NLLS.get_values_and_stderr_components_per_area(name_area,target_results,type_run,type_data = 'SLi')
            if type_run == 'multi':
                for el in self.NLLS.component_eval[name_area]:
                    #Carefull - if we dont have a component in one area, that shouldn't matter
                    total_compo_eval[el[:-1]] = np.zeros_like(self.ds.ElectronCount.values)
                for par in self.NLLS.param_errRel[name_area]:
                    total_params_eval[par] = np.zeros(self.ds.ElectronCount.values.shape[:-1])
            elif type_run == 'rerun':
                for el in self.NLLS.component_eval_re[name_area]:
                    #Carefull - if we dont have a component in one area, that shouldn't matter
                    total_compo_eval[el[:-1]] = np.zeros_like(self.ds.ElectronCount.values)
                for par in self.NLLS.param_errRel_re[name_area]:
                    total_params_eval[par] = np.zeros(self.ds.ElectronCount.values.shape[:-1])
                    #once all areas are scanned...all possible are initialized to 0
        #Now we prepare again the whole dataset
        dictio_info_image = dict()
        for name_area in areas_list:
            #Calling the method per area
            self.NLLS.get_RCS_maps(name_area,target_results,type_run,type_data = 'SLi')
            self.NLLS.get_residual_signals(name_area,target_results,type_run,type_data = 'SLi')
            self.NLLS.get_best_fit_signals(name_area,target_results,type_run,type_data = 'SLi')
            #let's get also the matrix for the mask overlaying 
            mat = cp.deepcopy(self.NLLS.ref_matrices[name_area])
            mat[mat == 0] = np.NaN
            '''
            mat_ds = xr.Dataset({'mask_cluster':(['y','x'],mat)},\
                coords = {'x':xs_j,'y':ys_i})
            #masking maps
            dictio_info_image[name_area] = (['y','x'],mat)
            
            self.masks_per_area[name_area] = hv.Image(mat_ds)\
                .opts(aspect = 'equal',invert_yaxis=True,frame_width=225,\
                xlim = self.xlims,ylim = self.ylims,\
                xaxis=None, yaxis=None,show_title = False,\
                cmap = ['black',self.colordict[name_area]],alpha = 0.25)
            '''
            #Now the total_reduce_chi_sq matrix - later to be implemented as a xr.Dataset
            #if type_run == 'multi':
            ref_mat = cp.deepcopy(self.NLLS.red_chi_sqr[name_area].ReducedXiSq.values)
            ref_res_mat = cp.deepcopy(self.NLLS.residuals[name_area].Residuals.values)
            ref_best_fit = cp.deepcopy(self.NLLS.best_fits[name_area].Best_fit.values)

            ref_mat = np.transpose(ref_mat)
            ref_res_mat = np.transpose(ref_res_mat,axes=[1,0,2])
            ref_best_fit = np.transpose(ref_best_fit,axes=[1,0,2])
            '''
            elif type_run == 'rerun':
                ref_mat = self.NLLS.red_chi_sqr_re[name_area].ReducedXiSq.values
                ref_res_mat = self.NLLS.residuals_re[name_area].Residuals.values
                ref_best_fit = self.NLLS.best_fits_re[name_area].Best_fit.values
            '''
            total_red_chi[np.isnan(ref_mat) == False] =\
                ref_mat[np.isnan(ref_mat) == False]
            total_resid[np.isnan(ref_res_mat) == False] =\
                ref_res_mat[np.isnan(ref_res_mat) == False]
            total_best_fits[np.isnan(ref_best_fit) == False]=\
                ref_best_fit[np.isnan(ref_best_fit) == False]
            #if type_run == 'multi':
            for el in self.NLLS.component_eval[name_area]:
                ref_compo = cp.deepcopy(self.NLLS.component_eval[name_area][el].values)
                ref_compo = np.transpose(ref_compo,axes=[1,0,2])
                total_compo_eval[el[:-1]][np.isnan(ref_compo) == False] =\
                    ref_compo[np.isnan(ref_compo) == False]
            for par in self.NLLS.param_errRel[name_area]:
                ref_err = cp.deepcopy(self.NLLS.param_errRel[name_area][par].values)
                try:
                    total_params_eval[par][np.isnan(ref_err) == False] =\
                        ref_err[np.isnan(ref_err) == False]
                except:
                    ref_err = np.transpose(ref_err)
                    total_params_eval[par][np.isnan(ref_err) == False] =\
                        ref_err[np.isnan(ref_err) == False]
            '''
            elif type_run == 'rerun':
                for el in self.NLLS.component_eval_re[name_area]:
                    ref_compo = self.NLLS.component_eval_re[name_area][el].values
                    total_compo_eval[el[:-1]][np.isnan(ref_compo) == False] =\
                        ref_compo[np.isnan(ref_compo) == False]
                for par in self.NLLS.param_errRel_re[name_area]:
                    ref_err = self.NLLS.param_errRel_re[name_area][par].values
                    total_params_eval[par][np.isnan(ref_err) == False] =\
                        ref_err[np.isnan(ref_err) == False]
            '''
        #The default image of the SI area
        '''
        dictio_info_image['SI'] = (['y','x'],self.ds.ElectronCount.values.sum(-1))
        self.total_dataset_mask = xr.Dataset(dictio_info_image,\
            coords = {'x':self.ds.x.values,'y':self.ds.y.values})
        '''
        total_red_chi[total_red_chi == 0] = np.nan #Setting the 0 to NaN for optimum overlay
        for par in total_params_eval:
            total_params_eval[par][total_params_eval[par] == 0] = np.nan #for optimum overlay
        extended_dict = dict()
        for el in total_compo_eval:
            extended_dict['Component {}'.format(el)] =\
            (['y','x','Eloss'],total_compo_eval[el])
        self.total_res_components = xr.Dataset(extended_dict,\
            coords = {'x':xs_j,'y':ys_i,'Eloss':self.ds.Eloss.values})
        extended_dict_params = dict()
        for par in total_params_eval:
            extended_dict_params['Relative error of {}'.format(par)] =\
            (['y','x'],total_params_eval[par])
        self.total_param_relSTDERR = xr.Dataset(extended_dict_params,\
            coords = {'x':xs_j,'y':ys_i})
        self.total_res_analysis = xr.Dataset({'ReducedChiSq':(['y','x'],total_red_chi),\
            'Residuals':(['y','x','Eloss'],total_resid),\
            'ElectronCounts (BestFit)':(['y','x','Eloss'],total_best_fits),\
            'ElectronCounts [a.u.]':(['y','x','Eloss'],self.ds.ElectronCount.values)},\
            coords = {'x':xs_j,'y':ys_i,'Eloss':self.ds.Eloss.values})

    #####################################################################################
    #####################################################################################
    #Buttons in the analysis tab
    #####################################################################################
    #def _callback_lock_all_comp(self,event):
        

    #def _callback_unlock_all_comp(self,event):
        

    #def _callaback_AddToNewModel(self,event):
        
        
    #def _callaback_RemoveFromNewModel(self,event):
        
            
    #def _callback_show_prev_compos(self,event):
        

    #def _callback_show_prev_bestfit(self,event):
        
            
    #def _callback_Refresh_selection_show(self,event):
        
    #def _callback_create_extra_component_rerun(self,event):
    
    #def _update_connectivity_graph(self,area_name):
    
    
    
    
    
    #def _get_list_areas_rerun(self):
    
    
    #def _visual_changes_analysis(self,areas_list):
    

    
    
    #def _callback_get_analysis_rerun_data(self,event):


    #def _get_connectivity_graph(self):
    

    #def _create_locking_dict(self):
    
    #def _callback_update_truth_table(self,event):
    
    
    #def _callback_change_tree(self,event):
    
        
    
    #def _callback_activate_possible_rerun(self,event):
    
    
    #def _callback_change_styles_totRCS(self,event):

    #Cropped here : 
    #def _callback_add_errormaps(self,event):
            
    #def _callback_erase_errormaps(self,event):


    #####################################################################################
    #####################################################################################
    # Responsive methods                             - For the model creator
    #####################################################################################
    #@param.depends('use_locking_dictionary',watch = True)
    #def _change_locking_button_style(self):

    @param.depends('clusters_with_newcomps',watch = True)
    def _change_newCompo_buttons_selection(self):
        try:
            lista = list(self.NLLS.extra_modified_model_components\
                [self.clusters_with_newcomps].keys())
        except:
            self.param['added_list_compos'].objects = ['NoNewComponents']
            lista = []
        else:
            self.param['added_list_compos'].objects =\
                [na[:-1] for na in lista]
        finally:
            self.added_list_compos = []

    #@param.depends('type_tree',watch = True)
    #def allow_show_tree(self):
    

    @param.depends('area',watch = True)
    def change_area(self):
        #Method that changes the area to be displayed in images..parameters..etc
        #Changing the overlay of images
        #self.button_overlay_clusters_model[0].disabled = False
        vals = cp.deepcopy(self.NLLS.ref_matrices[self.area])
        vals[self.NLLS.ref_matrices[self.area] == 0] = np.NaN
        #xs = self.ds.x.values
        #ys = self.ds.y.values
        self.mask = xr.Dataset({self.area:(['y','Eloss'],vals)},\
            coords={'y':self.ds.y.values,'Eloss':self.ds.Eloss.values})
        #self.mask = xr.Dataset({'mask':(['y','x'],vals)},\
        #            coords = {'x':xs,'y':ys})
        #Let's select the color for the binary cmap
        if 'cluster' in self.area:
            idx = int(self.area[self.area.index('_') + 1:])
            self.cmap_binary = ['black',self.colores[idx]]
            #For the display sign in the parameter config window
            idx2 = self.area.index('_')
            string = ' '.join([self.area[:idx2].capitalize(),self.area[idx2+1:]])
            style = {'font-family':'Arial','color':self.colores[int(self.area[idx2+1:])],\
                #'border-radius': '10px','border': '1px white solid',\
                'height' : '25px','padding':'0px 10px 5px 10px'}
        else:
            self.cmap_binary = ['black','aquamarine']
            string = self.area
            #self.cmap_binary = ['black',self.colores[idx]]
            style = {'font-family':'Arial','color':self.cmap_binary[-1],\
                'background':'black',\
                #'border-radius': '10px','border': '1px white solid',\
                'height' : '25px','padding':'0px 10px 5px 10px'}
        self.mask_im = hv.Image(self.mask,kdims = ['Eloss','y'])\
            .opts(invert_yaxis = True,\
            cmap = self.cmap_binary,\
            frame_width = 600,frame_height = 125,
            alpha = 0.5,xaxis = None,\
            yformatter = formatter_Sli_xax,ylabel = 'Line pixel #',\
            shared_axes= False,framewise = True,\
            toolbar = 'right',bgcolor = 'grey',hooks = [hook_black_image])
        #raster is refreshed
        self.mk2.object = '#### - {} -'.format(string)
        self.mk2.style = style
        if self.overlay_cluster_on_image:
            self.SL_image_placeholder.object = self.default_image*self.mask_im
        else:
            self.SL_image_placeholder.object = self.default_image
        self.model_type_component = 'continuum'
    
    @param.depends('overlay_cluster_on_image',watch = True)
    def _change_overlaying_cluster_model_panel(self):
        try:
            print('trying')
            vals = cp.deepcopy(self.NLLS.ref_matrices[self.area])
            vals[vals == 0] = np.NaN
            self.mask = xr.Dataset({self.area:(['y','Eloss'],vals)},\
                coords={'y':self.ds.y.values,'Eloss':self.ds.Eloss.values})
            if self.area != 'default':
                idx = int(self.area[self.area.index('_') + 1:])
                self.cmap_binary = ['black',self.colores[idx]]
            else:
                self.cmap_binary = ['black','aquamarine']
        except:
            print('failing')
            #Do nothing if exception raised
            return
        else: 
            
            if self.overlay_cluster_on_image:
                print('doing it')
                self.mask_im = hv.Image(self.mask,kdims = ['Eloss','y'])\
                .opts(invert_yaxis = True,\
                cmap = self.cmap_binary,\
                frame_width = 600,frame_height = 125,
                alpha = 0.5,xaxis = None,\
                yformatter = formatter_Sli_xax,ylabel = 'Line pixel #',\
                shared_axes= False,framewise = True,\
                toolbar = 'right',bgcolor = 'grey',hooks = [hook_black_image])
                self.SL_image_placeholder.object = self.default_image*self.mask_im
            else:
                print(' not doing it')
                self.SL_image_placeholder.object = self.default_image

        
    @param.depends('elemento',watch = True) 
    def change_element(self):
        #Changes the buttons for subshells per element in selection-window
        subshells = self.subshell_dictionary[self.elemento]
        self.param['subshell'].objects = subshells
        self.subshell = []
        
    @param.depends('subshell',watch = True)
    def change_info(self):
        #Changes the info displayed of onset energies in the current selected subshells
        if self.subshell == []:
            self.text_pane.object = 'Choose Subshell/s'
        else:
            lista  = []
            onsets = []
            for ssh in self.subshell:
                if ssh[-1] == '4':
                    dominant = ''.join([ssh[0],'5'])
                    dic = elements[self.elemento]['Atomic_properties']['Binding_energies']
                    lista.append(ssh)
                    onsets.append(dic[dominant]['onset_energy (eV)'])
                elif ssh[-1] == '2':
                    dominant = ''.join([ssh[0],'3'])
                    dic = elements[self.elemento]['Atomic_properties']['Binding_energies']
                    lista.append(ssh)
                    onsets.append(dic[dominant]['onset_energy (eV)'])
                else:
                    lista.append(ssh)
                    onsets.append(elements[self.elemento]['Atomic_properties']\
                        ['Binding_energies'][ssh]['onset_energy (eV)'])
            self.text_pane.object = '<br />'.join(['{} onset energy : {} eV'\
                .format(subs,en) for subs,en in zip(lista,onsets)])
    
    @param.depends('model_element',watch = True)
    def watch_create_model(self):
        #This first part only affects the initial stages
        #Allows for the model creation button to be clicked
        if not self.model:
            if 'NoElement' not in self.param['model_element'].objects:
                self.button_create_model.disabled = False
                self.button_create_model.button_type = 'success'
            else:
                self.button_create_model.disabled = True
                self.button_create_model.button_type = 'default'
        else:
            pass
        
    @param.depends('model_element','model_type_component',watch = True)    
    def watch_changes_model_buttons(self):
        #Now, what happens when changing element tabs in the model section
        if self.model:
            self.param['model_component'].objects =\
                list(self.NLLS.models_components[self.area][self.model_element]\
                [self.model_type_component].keys())
            try:
                self.model_component = self.param['model_component'].objects[0]
                self.mod_el[0][2].disabled = False
                for el in self.model_continuum_parameters[0]:
                    el.disabled = False
                for el in self.model_ELNES_parameters[0]:
                    el.disabled = False
            except:
                #This is for the case of having an element without ELNES or continuum components
                self.param['model_component'].objects = ['Empty']
                self.model_component = self.param['model_component'].objects[0]
                self.mod_el[0][2].disabled = True
                for el in self.model_continuum_parameters[0]:
                    el.disabled = True
                for el in self.model_ELNES_parameters[0]:
                    el.disabled = True
        else: pass
        
    @param.depends('model_type_component',watch = True)
    def watch_changes_type_component(self):
        #Controls de parameter-value/bonds widgets that are displayed
        if self.model:
            if self.model_type_component == 'continuum':
                self.parameter_configurator = self.model_continuum_parameters
                self.model_config_widgets.objects = self.model_config_widgets.objects[:-1] + [self.parameter_configurator]
                #self.model_config_widgets.objects = self.model_config_widgets.objects[:-1].append(self.parameter_configurator)
            elif self.model_type_component == 'ELNES':
                self.parameter_configurator = self.model_ELNES_parameters
                self.model_config_widgets.objects = self.model_config_widgets.objects[:-1] + [self.parameter_configurator]
                #self.model_config_widgets.objects = self.model_config_widgets.objects[:-1].append(self.parameter_configurator)
            else:
                pass

    #Now....the parameter change when jumping between elements
    @param.depends('area','model_element','model_type_component','model_component',watch = True)
    def watch_parameter_changes(self):
        if self.model:
            #In case of an empty component, do nothing
            if self.model_component != 'Empty' and self.model_type_component == 'ELNES':
                self.button_reset_parameters.disabled = False
                #We activate the function_type selector
                keyword = self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['type']
                self.param['model_comp_func'].objects = self.default_compo_funcs
                self.model_comp_func =\
                (lambda keyword: ' '.join([keyword.capitalize(),'component']))(keyword)
                self.model_config_widgets[5][0][0].disabled = False
                #We need to modify the bounds so it does not explode each time we change tab
                #We have a limiting constraint - the initial values -+ 35 eV
                new_cent = self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['center']
                def_cent = self.model_element_dict[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['center']
                self.param['center'].bounds =\
                (max(def_cent - 15,self.Eini),min(def_cent + 15,self.Eend))
                self.param['center_max_min'].bounds =\
                (max(def_cent - 25,self.Eini),min(def_cent + 25,self.Eend))
                maxi_cent = round(self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['center_max'])
                mini_cent = round(self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['center_min'])
                self.center_max_min = (mini_cent,maxi_cent)
                self.center = new_cent
                '''
                new_cent = self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['center']
                def_cent = self.model_element_dict[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['center']
                self.param['center'].bounds =\
                (max(def_cent - 35,self.Eini),min(def_cent + 35,self.Eend))
                self.param['center_max_min'].bounds =\
                (max(def_cent - 45,self.Eini),min(def_cent + 45,self.Eend))
                maxi_cent = round(self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['center_max'])
                mini_cent = round(self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['center_min'])
                self.center_max_min = (mini_cent,maxi_cent)
                self.center = new_cent
                '''
                #The same for sigma
                new_sig = self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['sigma']
                def_sig = self.model_element_dict[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['sigma']
                self.param['sigma_max_min'].bounds =\
                    (0,\
                    self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['sigma_max']+3)
                self.sigma_max_min =\
                    (self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['sigma_min'],\
                    self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES_init_const'][self.model_component]['sigma_max'])
                self.param['sigma'].bounds = (0,10 * def_sig)
                self.sigma = new_sig
                '''
                new_sig = self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['sigma']
                def_sig = self.model_element_dict[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['sigma']
                self.param['sigma'].bounds = (0,10 * def_sig)
                self.sigma = new_sig
                '''
                #The amplitude has no bounds...so no problem
                #We allow the amplitude to be modified by hand from 0 to 
                #2.5 times the initial guess
                amp = round(cp.deepcopy(self.NLLS.models_components[self.area]\
                    [self.model_element]['ELNES'][self.model_component]['amplitude']))
                self.param['amplitude'].bounds = (0 , 2*amp +1)
                self.amplitude = amp
            elif self.model_component != 'Empty' and self.model_type_component == 'continuum':
                self.button_reset_parameters.disabled = False
                #Component function types -disabled and empty
                self.model_config_widgets[5][0][0].disabled = True
                self.param['model_comp_func'].objects = ['Hartree/Hydrogenic']
                self.model_comp_func = 'Hartree/Hydrogenic'
                #Now the continuum paramenters
                new_A = self.NLLS.models_components[self.area][self.model_element]\
                    ['continuum_init_const'][self.model_component]['A']
                new_chem = self.NLLS.models_components[self.area][self.model_element]\
                    ['continuum_init_const'][self.model_component]['chem']
                new_allow_chem = self.NLLS.models_components[self.area][self.model_element]\
                    ['continuum_init_const'][self.model_component]['allow_chem']
                new_A_min = self.NLLS.models_components[self.area][self.model_element]\
                    ['continuum_init_const'][self.model_component]['A_min']
                self.param['A'].bounds = (0,10*new_A +1)
                self.A = new_A
                self.param['chem'].bounds = (-25,25)
                self.chem = new_chem
                self.allow_chem = new_allow_chem
                self.param['A_min'].bounds = (0,5*new_A)
                self.A_min = new_A_min
            else:
                self.button_reset_parameters.disabled = True
                self.model_config_widgets[5][0][0].disabled = True
                
    #ELNES parameters variation controls ---------------------------------------------
    @param.depends('center',watch = True)
    def _center_changes(self):
        #Rememer the maximum allowed change in center was 0.05
        #by default in high flexibility. Here, let's limit it a bit
        #It will always place limits in medium flexibility
        cen = self.center
        #In case of having moved the center out of the bounds, let's move the bound affected
        #at the same rate than the center
        bds = self.center_max_min
        dis = bds[1]-bds[0]
        #Relocating limits, so we do not end up with unconfortable parameters
        if cen > bds[1]: self.center_max_min = (round(cen+1-dis),round(cen+1))
        elif cen < bds[0]: self.center_max_min = (round(cen-1),round(cen-1+dis))
        #Let's change the paramenters in the dictionary created in NLLS
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES'][self.model_component]['center'] = cen
    
    @param.depends('sigma',watch = True)
    def _sigma_changes(self):
        #Rememer the maximum allowed change in center was 0.05
        #by default in high flexibility. Here, let's limit it a bit
        #It will always place limits in medium flexibility
        sig = self.sigma
        mini_s_b = 0 #Avoids out of bounds
        maxi_s_b = 3.5*sig #Avoids out of bounds
        minis,maxis = self.sigma_max_min
        if sig > maxis:
            self.param['sigma_max_min'].bounds = (mini_s_b,round(3+sig,2))
            self.sigma_max_min = (minis,round(1.5+sig,2))
        elif sig < minis:
            self.param['sigma_max_min'].bounds =\
            (mini_s_b,self.param['sigma_max_min'].bounds[1])
            self.sigma_max_min = (max(0,round(sig-0.5,2)),maxis)
        else:
            pass
        #Let's change the paramenters in the dictionary created in NLLS
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES'][self.model_component]['sigma'] = sig

        '''
        sig = self.sigma
        mini_s_b = 0 #Avoids out of bounds
        maxi_s_b = 3.5*sig #Avoids out of bounds
        self.param['sigma_max_min'].bounds = (mini_s_b,maxi_s_b)
        self.sigma_max_min = (0,sig*2.25)
        #Let's change the paramenters in the dictionary created in NLLS
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES'][self.model_component]['sigma'] = sig
        '''

    @param.depends('amplitude',watch = True)
    def _ELNES_amplitude_changes(self):
        #With the amplitude, we only change the value itself
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES'][self.model_component]['amplitude'] = self.amplitude
    
    @param.depends('center_max_min',watch = True)
    def _center_constraints(self):
        self.center_max_min = (\
        round(self.center_max_min[0]),\
        round(self.center_max_min[1]))                     
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['center_min'] =\
            self.center_max_min[0]
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['center_max'] =\
            self.center_max_min[1]
        
    
    @param.depends('sigma_max_min',watch = True)
    def _sigma_constraints(self):
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['sigma_min'] =\
            self.sigma_max_min[0]
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['sigma_max'] =\
            self.sigma_max_min[1]
        '''    
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['sigma_min'] =\
            self.sigma_max_min[0]
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['sigma_max'] =\
            self.sigma_max_min[1]
        '''

    @param.depends('amplitude_min',watch = True)
    def _amplitude_constraints(self):
        self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES_init_const'][self.model_component]['amplitude_min'] =\
            self.amplitude_min
    
    #Continuum parameters variation controls ---------------------------------------------
    @param.depends('A',watch = True)
    def _amplitude_changes(self):
        #With the amplitude, we only change the value itself
        self.NLLS.models_components[self.area][self.model_element]\
            ['continuum_init_const'][self.model_component]['A'] = self.A

    @param.depends('A_min',watch = True)
    def _continuum_amplitude_changes(self):
        #With the amplitude, we only change the value itself
        self.NLLS.models_components[self.area][self.model_element]\
            ['continuum_init_const'][self.model_component]['A_min'] = self.A_min
        
    @param.depends('allow_chem',watch = True)
    def _allowing_continuum_onset_variation(self):
        self.NLLS.models_components[self.area][self.model_element]\
            ['continuum_init_const'][self.model_component]['allow_chem'] = self.allow_chem
        
    @param.depends('chem',watch = True)
    def _chemical_displacement(self):
        self.NLLS.models_components[self.area][self.model_element]\
            ['continuum_init_const'][self.model_component]['chem'] = self.chem
    
    @param.depends('model_comp_func',watch = True)
    def _type_of_component_ELNES(self):
        #method that changes the type of component for a certain
        #ELNES model component - chosing between 4 options
        if self.model_type_component == 'ELNES':
            #We only want changes when this is true
            self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES'][self.model_component]['type'] =\
            (lambda keyword: keyword[:keyword.index(' ')].casefold())\
                (self.model_comp_func)
        else:
            pass
    
    #Controls for the clustering file selector
    @param.depends('path_toClust',watch = True)
    def _control_path_imput(self):
        try:
            os.listdir(self.path_toClust)
        except:
            print('here - no path')
            self.path_toClust = self.param['path_toClust'].default
        finally:
            self.param['file_clust'].objects = os.listdir(self.path_toClust)
            self.file_clust = self.param['file_clust'].objects[0]
    
    @param.depends('center','show_center',watch = True)
    def _return_center_vline(self):
        #Method that ensures the component center line is shown when asked
        #First -  the change of colour
        if self.show_center:
            self.button_show_center[0].button_type = 'success'
        else:
            self.button_show_center[0].button_type = 'default'
        #Now, the changes in the display of lines
        if self.show_center and self.model_type_component == 'ELNES':
            return hv.VLine(self.center).opts(line_alpha = 1,line_width=1,line_color = 'green')
        else:
            return hv.VLine(self.center).opts(line_alpha = 0,line_width=1,line_color = 'green')
    
    @param.depends('center','sigma','show_fwhm','model_comp_func',watch = True)
    def _return_sigmas_vline(self):
        #Method that ensures the component fwhm lines are shown when asked
        '''It is trickier than the center ones. Mainly, each compo function computes the
        fwhm differently, taking the sigma as the model parameter.
        We also have to ensure that the center is part of the function, as changing it
        changes the position of the fwhm lines
        '''
        #Calculations
        try:
            #This is to be if we are in ELNES component, otherwise-not interested
            idx = self.model_comp_func.index(' ')
            keyword = self.model_comp_func[:idx]
        except:
            vline1 = hv.VLine(self.center - 1).opts(line_alpha = 0)
            vline2 = hv.VLine(self.center - 1).opts(line_alpha = 0)
            overlay = hv.Overlay([vline1,vline2])  
        else:
            if self.show_fwhm:
                alph = 1
            else:
                alph = 0
            fwhm = self.fwhm_dict[keyword](self.sigma)
            vline1 = hv.VLine(self.center - fwhm/2)\
                .opts(line_alpha = alph,line_width=1,line_color = 'orange')
            vline2 = hv.VLine(self.center + fwhm/2)\
                .opts(line_alpha = alph,line_width=1,line_color = 'orange')
            overlay = hv.Overlay([vline1,vline2])  
        finally:
            #Change of color in the buttons and return of the information
            if self.show_fwhm:
                self.button_show_sigmas[0].button_type = 'warning'
            else:
                self.button_show_sigmas[0].button_type = 'default'
            return overlay
    
    @param.depends('area',watch = True)
    def _control_references_fitted_displays(self):
        #This method changes the displayed reference spectra after fitting when
        #changing the selected area in the area tab
        try:
            #If one exists...the other is also in the reference dictionaries
            
            curve2 = self.dictionary_fitted_ref_compos[self.area]
            curve1 = self.dictionary_fitted_ref_overall[self.area]
            nombre = self.area
        except:
            curve1 = self.default_curve_references
            curve2 = self.default_curve_references
            nombre = 'None'
        finally:
            self.dyn_best_placeholder.object = curve1
            self.dyn_best_mkdown.object =\
                '#### Best fit for the reference spectra of the - **{}** - area'\
                .format(nombre)
            self.dyn_best_mkdown.style = {'color':'white'}
            self.dyn_comp_placeholder.object = curve2
            self.dyn_comp_mkdown.object =\
                '#### Fitted individual components for the reference spectra \
                of the **{}** area'
            self.dyn_comp_mkdown.style = {'color':'white'}
    
    @param.depends('new_compo_energy','new_compo_toggle',watch = True)
    def _show_new_compo_center(self):
        if self.new_compo_toggle:
            try:
                self.button_new_compo_center_show[0].button_type = 'success'
            except: pass
            return hv.VLine(self.new_compo_energy).opts(line_alpha = 1,line_width=1,line_color = 'purple')
        else:
            try:
                self.button_new_compo_center_show[0].button_type = 'default'
            except:pass
            return hv.VLine(self.new_compo_energy).opts(line_alpha = 0,line_width=0,line_color = 'purple')
    #####################################################################################
    #Responsive behaviour of analysis tools:
    ##################################################################################### 
    #Cropped here
    
    
    #Panel contructor --------------------------------------------------------------------
    ######################################################################################
    #                                                                                    #
    #               Panel constructor for SLines                                         #
    #                                                                                    #
    ######################################################################################
    def _model_panel_constructor(self):
        #Constructs the panel displayed
        sel_el = pn.Param(self.param, widgets={'elemento':pn.widgets.Select,\
                'subshell':pn.widgets.CheckButtonGroup},\
            parameters = ['elemento','subshell'],\
            show_name = False,default_layout = pn.GridBox,width = 300)
        sel_el[0][0].name = ''
        sel_el.align = 'center'
        #Widget box - Element selection
        deleteing_mod = pn.Row(self.button_reset,\
            self.button_deactivate_delete,self.button_delete_model,\
            width = 340,margin = (0,10),align='start')
        deleteing_mod[0].margin = (5,10,5,0)
        deleteing_mod[1].margin = (5,0,5,15)
        deleteing_mod[2].margin = (5,0,5,0)
        selecint_fit_area =\
        pn.Row(self.button_fit_ref_select_area,self.button_fit_references,\
            width = 340,margin = (0,10),align='start')
        selecint_fit_area[0].margin = (5,10,5,0)
        sel_el_widgets = pn.Column('### Element Selection Panel',\
            pn.layout.Divider(margin = (-10,0,0,0)),\
            sel_el,self.text_pane,\
            pn.Spacer(height = 50),\
            self.button_add_element,self.button_create_model,\
            deleteing_mod,\
            #pn.Spacer(height = 10),\
            selecint_fit_area,\
            margin = (0,0,30,0),min_height = 500,background = (0,0,0,1),\
            width = 350)
        sel_el_widgets[5].width = 300
        sel_el_widgets[6].width = 300
        sel_el_widgets[7].width = 300
        sel_el_widgets[8].width = 300
        sel_el_widgets[5].align = 'center'
        sel_el_widgets[6].align = 'center'
        sel_el_widgets[7].align = 'center'
        sel_el_widgets[8].align = 'center'
        # Standard width from now on
        #Widget box - Parameters configuration
        self.model_config_widgets = pn.Column('### Model Configuration Panel',\
            #pn.layout.Divider(margin = (-10,0,0,0)),\
            self.mod_el,\
            pn.Row(self.button_remove_component,self.button_reset_parameters,width = 300),\
            pn.pane.Markdown('#### Parameters'),\
            self.current_area_mkdwn,\
            self.button_compo_func,\
            self.parameter_configurator,\
            margin = (0,0,10,0),min_height = 500,\
            background = (255,255,255,1),\
            )
        #This is for the widgetbox for the extra_element adding
        n_comp_el = pn.Param(self.param['new_compo_elements'],\
            widgets = {'new_compo_elements':pn.widgets.Select},\
            show_labels = False, show_name = False)
        n_comp_name = pn.Param(self.param['new_compo_name'],\
            widgets={'new_compo_name':pn.widgets.TextInput},\
            show_labels = False, show_name = False)
        n_comp_name[-1].placeholder = 'Enter name'
        n_comp_areas = pn.Param(self.param['new_compo_areas'],\
            widgets={'new_compo_areas':pn.widgets.MultiChoice},\
            show_labels = False, show_name = False)
        n_comp_areas[0].height = 100
        n_comp_func = pn.Param(self.param['new_compo_func'],\
            widgets={'new_compo_func':pn.widgets.Select},\
            show_labels = False, show_name = False,width = 200)
        n_comp_energy = pn.Param(self.param['new_compo_energy'],\
            widgets = {'new_compo_energy':pn.widgets.FloatSlider},\
            show_labels = False, show_name = False,width = 150)
        n_comp_flex = pn.Param(self.param['new_compo_flex'],\
            widgets = {'new_compo_flex':pn.widgets.Select},\
            show_labels = False, show_name = False,width = 200)
        wid_new_compo = pn.Column(pn.pane.Markdown('### ELNES - New component configurator'),\
            n_comp_el,n_comp_name,n_comp_areas,\
            pn.Row(pn.widgets.StaticText(value = 'Function',width = 75),\
                n_comp_func,width = 300),\
            pn.Row(pn.widgets.StaticText(value = 'Center of E-Loss [eV]',width = 75),\
                self.button_new_compo_center_show,n_comp_energy,width = 300),\
            pn.Row(pn.widgets.StaticText(value = 'Constraints init-flexibility',width = 75),\
                n_comp_flex,width = 300),\
            self.button_add_extra_compo)
        #Some minor modifications
        wid_new_compo[0][0].margin = (10,0,5,20)
        wid_new_compo[4][0].margin = (15,5,10,20)
        wid_new_compo[5][0].margin = (15,5,10,20)
        wid_new_compo[6][0].margin = (15,5,10,20)
        #self.wid_new_compo[2][-1].placeholder = 'Enter name'
        #self.wid_new_compo[0].margin = (10,0,15,20)
        #For the multifit tab
        areas_multifit_wid = pn.Param(self.param['multifit_area'],\
            widgets = {'multifit_area':pn.widgets.MultiChoice},\
            parameters = ['multifit_area'],width = 300,show_labels = False,\
            show_name = False) 
        etc_lists_wid = pn.Param(self.param['list_of_ETCs'],\
            widgets = {'list_of_ETCs':pn.widgets.StaticText},\
            parameters = ['list_of_ETCS'],width = 250,show_labels = False,\
            show_name = False)
        message = pn.Param(self.param['ETC'],widgets = {'ETC':pn.widgets.StaticText},\
            parameters = ['ETC'],show_labels = False,show_name = False,width = 300)
        multi = pn.Column(pn.pane.Markdown('### Multifit controls'),\
            pn.pane.Markdown('#### Select areas'),areas_multifit_wid,\
            #pn.Spacer(background='white',width = 300,height = 35),\
            pn.layout.Divider(width = 200, margin = (-10,10,0,15)),\
            self.button_multifit,self.prog_bar,message,\
            pn.pane.Markdown('#### Fitting times per area (s)'),\
            pn.Column(etc_lists_wid,height = 100,min_width=200,width_policy='fit'\
                ,scroll=True))
        #Configurations for the multifit tab
        self.button_multifit.width = 300
        multi[0][0].margin = (10,0,5,20)
        multi[1][0].margin = (0,20)
        multi[2][0].margin = (-5,10,15,10)
        multi[2][0].height = 125
        multi[3].margin = 0
        multi[3].height = 15
        multi[7][0].margin = (-5,15)
        multi[8][0].margin = (-5,15)
        multi[8][0].width = 300
        multi[5][0].margin = (5,5)
        multi[5][0].width = 300
        multi[8].margin = (0,10)
        multi[8].width = 310
        multi[8].background = 'lightgray'
        multi[8].height = 75
        #Configuring widget boxes
        sel_el_widgets[0][0].margin = (10,0,15,20)
        sel_el_widgets[0][0].style = {'color' : 'white'}
        # TODO This whole mess just to configure the layout of this tab ..
        #There must be a better way, but right now I don't know
        self.model_config_widgets[2].margin = (-10,0,0,15)
        self.model_config_widgets[3].margin = (0,0,0,15)
        self.model_config_widgets[0].margin = 0
        self.model_config_widgets[4].width_policy = 'max'
        self.model_config_widgets[4].min_width = 250
        self.model_config_widgets[4].height  = 45
        self.model_config_widgets[4].margin = (0,5,5,20)
        self.model_config_widgets[5].margin = (-10,15)
        self.model_config_widgets[0].margin = (10,0,15,20)
        self.model_config_widgets[3][0][0].margin = (0,0,-5,15)
        self.model_config_widgets[5][0][0].margin = (0,0,-5,10)
        self.model_config_widgets[5][0][0].disabled = True
        self.model_config_widgets.frame_width = 500
        #self.area_selector[0][0].margin = (10,0,15,20)
        self.mod_el[0][0].disabled = True
        self.mod_el[0][1].disabled = True
        #self.area_selector[-1].margin = (0,0,0,25)
        self.cluster_box_pane[0].width = 350
        #self.cluster_box_pane[-1].margin = (15,70,10,70)
        self.cluster_box_pane[0][0].margin = (0,15)
        #panel assembly
        #*self.point_image),\
        '''
        visual = pn.Column('### Visualization',pn.pane.HoloViews(self.default_image),\
            '#### Interactive display options',self.button_show_center,\
            self.button_show_sigmas)
        visual[0].margin = (10,0,15,20)
        visual[1].margin = (0,0,0,25)
        visual[2].margin = (-10,0,0,25)
        visual[3].show_name = False
        visual[4].show_name = False
        visual[3].margin = (-20,0,0,5)
        visual[4].margin = (-20,0,0,5)
        visual[3][0].disabled = True
        visual[4][0].disabled = True
        '''
        #Extra styling for a smooth tab transition in the model section
        multi.width = 320
        wid_new_compo.width = 320
        #The tabs
        self.tabs = pn.Tabs(\
            ('Components',self.model_config_widgets),\
            #('Area',self.area_selector),\
            #('Visualization',visual),\
            ('Add-Compo',wid_new_compo),\
            ('Multifit',multi),\
            active = 0,\
            tabs_location='right',dynamic = True)
        self.cluster_box_pane[0][0][0].margin = (0,15,-15,15)
        #self.cluster_box_pane[0][1].margin = (0,5,-5,5)
        #self.cluster_box_pane[0][2].margin = (0,5,-10,5)
        #self.cluster_box_pane.margin = (-10,0,0,0)
        self.panel1 = pn.Column(pn.Row(sel_el_widgets,self.tabs),self.cluster_box_pane)
        #Dynamic maps to show the center and sigma lines
        self.center_Vline = hv.DynamicMap(self._return_center_vline)
        self.sigmas_Vlines = hv.DynamicMap(self._return_sigmas_vline)
        self.new_center_Vline = hv.DynamicMap(self._show_new_compo_center)
        #Tabs for the reference spectra overlays
        self.dyn_refs_mkdown = pn.pane.Markdown('#### Reference spectra',\
            width = 600,style = {'color':'lightgrey'})
        self.dyn_best_mkdown = pn.pane.Markdown(\
            '#### Best fit for the reference spectra of the \
            **{}** area'.format(' - None - '),\
            width = 600,style = {'color':'lightgrey'})
        self.dyn_comp_mkdown = pn.pane.Markdown(\
            '#### Fitted individual components for the reference spectra \
            of the **{}** area'.format(' - None - '),\
            width = 600,style = {'color':'lightgrey'})
        self.dyn_refs_placeholder =\
            pn.pane.HoloViews(\
                hv.NdOverlay(self.dictionary_references)\
                .opts(bgcolor = 'black',hooks = [hook_full_black]),\
                margin = (0,0,5,15),width = 700,align = 'end')
        self.dyn_best_placeholder =\
            pn.pane.HoloViews(self.default_curve_references,\
                margin = (0,0,5,15),width = 700,align = 'end')
        self.dyn_comp_placeholder =\
            pn.pane.HoloViews(self.default_curve_references,\
                margin = (0,0,5,15),width = 700,align = 'end')
        self.graph_placeholder =\
            pn.pane.HoloViews(self.dynamic_graphs_1.opts(shared_axes = False,framewise = True)\
            *self.center_Vline*self.sigmas_Vlines*self.new_center_Vline,\
            margin = (0,0,5,15),width = 700,align = 'end')
        self.SL_image_placeholder = pn.pane.HoloViews(self.default_image,\
            align = 'end',margin = (0,25,10,25))
        self.tabs_references = pn.Tabs(\
            ('Spectra',pn.Column(pn.pane.Markdown('#### Spectra visalization',\
                width = 500,style = {'color':'grey'}),\
            self.graph_placeholder,width = 725,align = 'end',margin = (0,5))),\
            ('References',\
            pn.Column(self.dyn_refs_mkdown,self.dyn_refs_placeholder,\
                width = 725,align = 'end',margin = (0,5))),\
            ('Best Fit',\
            pn.Column(self.dyn_best_mkdown,self.dyn_best_placeholder,\
                width = 725,align = 'end',margin = (0,5))),\
            ('Fitted components ',\
            pn.Column(self.dyn_comp_mkdown,self.dyn_comp_placeholder,\
                width = 725,align = 'end',margin = (0,5))),\
        dynamic = True,margin = 0,width = 730)
        self.panel2_1 = pn.Column(\
            pn.Row(pn.pane.Markdown('### Spectral Visualization Tools',\
                margin = (5,5,0,15),width = 300,style = {'color':'white'}),\
                width = 675,margin = 0),\
            pn.Row(pn.pane.Markdown('#### Area/cluster options',width = 400,\
                style = {'color':'white'},margin = (0,15))),\
            pn.Row(self.area_selector,self.button_overlay_clusters_model,\
                self.button_show_center,self.button_show_sigmas,\
                width = 720,margin = (0,10)),\
            pn.layout.Divider(width = 710,margin = (0,10)),\
            self.SL_image_placeholder,\
            margin = 0,background = 'black',width = 730)
        #self.graph_placeholder)

        self.panel2 = pn.Column(\
            self.panel2_1,\
            self.tabs_references,\
            background = 'black',margin = 0,width = 730)

        self.panel1[1].margin = (-20,0,0,0)
        self.panel1.background = 'black'
        self.panel1[0].background = 'black'
        self.panel1[0][1].background = 'white'
        self.panel1[0][1].height = 500
        self.panel1[0][1][0][1].margin = (-15,5,5,5)
        self.panel1[0][1][0][0].margin = (10, 0, 10, 20)
        self.panel2.margin = (0,0,0,25)
        panel_mod = pn.Row(self.panel1,self.panel2)
        return panel_mod
    

    #Cropped from here - NO anaylsis - No Results

    #def _result_analysis_panel_construction(self):
        
import sys
import time
import os
import json
from Library.Database.elements import elements

import holoviews as hv
from holoviews import streams
from holoviews.streams import param
import panel as pn
import pandas as pd
import bokeh, param
import hvplot.networkx as hvnx
import networkx as nx
from bokeh.models import HoverTool

import copy as cp
import xarray as xr
import numpy as np
from random import choice

from nlls_functions import NLLS_fitting
from Library.saving_routines import Saving_panel

print('Importing - Shell for the model constructor of Spectrum Images')
# Use only supported arguments for hv.extension
hv.extension()

# Only add CSS file if pn.config.css_files exists and is a list
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
    
#These functions, classes and class-methods create some of the interactive plotting widgets
def formatter(value):
        #Method to format the yaxis format (Electron Counts)
        return '{:.2e}'.format(value)

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
    
def hook_full_black_black(plot, element):
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
    

def hook_black_image(plot, element):
    plot.handles['plot'].border_fill_color = 'black'
#########################################################################################
#Plotting_stuff
#########################################################################################

class plotting(param.Parameterized):
    #This class takes the original SI and shows a plot of the components
    def __init__(self, ds):
        self.ds = ds
        #These are the reference images.
        #First thing's first - padding calculations
        xsize = self.ds.x.values.size
        ysize = self.ds.y.values.size
        dist = abs(ysize-xsize)
        if xsize < ysize:
            self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
            self.ylims = (-0.5,ysize-0.5)
        else:
            self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
            self.xlims = (-0.5,xsize-0.5)
        self.im = hv.Image(self.ds.sum(dim = 'Eloss'),kdims = ['x','y'])\
            .opts(cmap = 'plasma',alpha = 0,\
            frame_height = 250,aspect='equal',\
            invert_yaxis=True,\
            xlim = self.xlims,ylim = self.ylims,\
            xaxis=None, yaxis=None,shared_axes = False)
        self.puntos = hv.HeatMap(self.ds.sum(dim = 'Eloss'),kdims = ['x','y'])\
            .opts(cmap = 'Greys_r',\
            frame_height = 250,\
            invert_yaxis=True,\
            aspect='equal',\
            xlim = self.xlims,ylim = self.ylims,\
            xaxis=None, yaxis=None,\
            hover_line_color = 'green',\
            line_width = 1.25,line_alpha = 0,fill_alpha = 1,hover_line_alpha = 1,\
            selection_line_color = 'red',selection_line_alpha = 1,\
            nonselection_line_alpha = 0,selection_alpha = 1,\
            nonselection_alpha = 0.75,tools = ['hover','tap'])
        '''
        self.puntos = hv.Points(self.ds, kdims=['y','x'])\
            .opts(tools=['tap'],\
            frame_height = 250,\
            size = 7.5,\
            alpha = 0.1,\
            selection_color= 'red',\
            selection_alpha=1,\
            nonselection_alpha= 0.05,\
            nonselection_fill_alpha= 0.05,\
            nonselection_color='blue')
        '''
        #We also define here the streams that make the graphs reactive
        #self.hovering = streams.DoubleTap(x = 0, y = 0, source = self.im)
        self.tap = streams.SingleTap(x = -1,y = -1,source = self.im)
        self.hov_lims = (self.ds.x.data[0]-0.5,self.ds.x.data[-1]+\
        0.5,self.ds.y.data[0]-0.5,self.ds.y.data[-1]+0.5)
    
    def plot_curve(self,x,y):
        #Method in charge of plotting the spectrum when hovering over the image
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return None
        elif y >= yf or y <= yi:
            return None
        else:
            x0, y0 = int(round(x)), int(round(y))
            arr = self.ds.ElectronCount.isel(x=int(x0), y=int(y0)).squeeze()
            curve = hv.Area(arr, kdims='Eloss', vdims='ElectronCount')\
                .opts(color='blue',\
                fill_alpha=0.5,\
                #line_color=ox.colores[i-1]\
                line_color='white',\
                fill_color = 'red',\
                bgcolor = 'black',hooks = [hook_full_black_black])
            return curve
    
    def create_panel(self):
        #this method creates the objects for the panel
        '''
        self.din = hv.DynamicMap(self.plot_curve,streams=[self.hovering])\
            .opts(frame_height= 250,\
            #min_width = 400,\
            #max_width = 700,\
            frame_width = 600,\
            framewise=True,\
            yformatter=formatter,\
            shared_axes=False,\
            #responsive = True,\
            show_grid = True)
        '''
        self.din2 = hv.DynamicMap(self.plot_curve,streams=[self.tap])\
            .opts(frame_height= 250,\
            #min_width = 400,\
            #max_width = 700,\
            frame_width = 600,\
            framewise=True,\
            yformatter=formatter,\
            shared_axes=False,\
            #responsive = True,\
            show_grid = True,\
            #color = 'red',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        #return (self.im,self.din2)
        
        #return (self.im,self.puntos,self.din*self.din2)
        return (self.im,self.puntos,self.din2)
    
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
            return None
        elif y >= yf or y <= yi:
            return None
        else:
            x0, y0 = int(round(x)), int(round(y))
            arr = self.ds_totals.Residuals.isel(x=int(x0), y=int(y0)).squeeze()
            self.x_idx = int(x0)
            self.y_idx = int(y0)
            curve = hv.Curve(arr, kdims='Eloss', vdims='Residuals').opts(shared_axes=False,color = 'red')
            return curve

    def _return_signal_best_fit(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return None
        elif y >= yf or y <= yi:
            return None
        else:
            x0, y0 = int(round(x)), int(round(y))
            arr = self.ds_totals['ElectronCounts (BestFit)'].isel(x=int(x0), y=int(y0)).squeeze()
            curve1 = hv.Curve(arr, kdims='Eloss', vdims='ElectronCounts (BestFit)').opts(color = 'orange',shared_axes=False)
            return curve1

    def _return_signal(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return None
        elif y >= yf or y <= yi:
            return None
        else:
            x0, y0 = int(round(x)), int(round(y))
            arr = self.ds_totals['ElectronCounts [a.u.]'].isel(x=int(x0), y=int(y0)).squeeze()
            curve2 = hv.Area(arr, kdims='Eloss', vdims='ElectronCounts [a.u.]').opts(fill_alpha = 0.15,color = 'navy',shared_axes=False)
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
    
def hook_full_black(plot, element):
    #This serves to give format to a plotting object in the dark-theme config
    plot.handles['plot'].border_fill_color = 'black'
    plot.handles['xaxis'].axis_label_text_color = 'white'
    plot.handles['yaxis'].axis_label_text_color = 'white'
    plot.handles['xaxis'].major_label_text_color = 'white'
    plot.handles['yaxis'].major_label_text_color = 'white'


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
    type_compo = param.ObjectSelector(default='Gaussian component',\
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
    #To toggle overlay - clusters
    overlay_clust_bool = param.Boolean(default = False)
    #To Change the x-section used in the models and activate the soften option
    soft_edges = param.Boolean(default = True)
    x_section_type = param.ObjectSelector(default = 'beta-cut',objects = ['theoretical','beta-cut','F-factor'])
    soften_strength = param.Number(default = 1.5,bounds = (.10,15),step = .1)

    def __init__(self,ds):
        super().__init__()
        self.current_el = self.elemento        
        #The subshell dictionary form the listed elements in hyperspy
        self.subshell_dictionary = dict()
        #New dictionaries additions
        self.dictio_stimator = dict()
        self.dictio_order_tuples = dict()
        self.dictio_order_matrices = dict()
        #######
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
        self.default_image = hv.Image(ds.sum('Eloss'),\
            kdims = ['x','y']).opts(\
            invert_yaxis = True,\
            cmap = 'Greys_r',alpha = 1,\
            frame_height = 250,aspect='equal',\
            xlim = self.xlims,ylim = self.ylims,\
            xaxis=None, yaxis=None,shared_axes = False,\
            hooks = [hook_black_image])
        self.hmap_im = hv.HeatMap(ds.sum('Eloss'),\
            kdims = ['x','y']).opts(\
            show_grid = False,bgcolor = 'black',\
            invert_yaxis = True,\
            cmap = 'Greys_r',frame_height = 250,\
            aspect='equal',xlim = self.xlims,ylim = self.ylims,\
            xaxis=None, yaxis=None,shared_axes = False,\
            hover_line_color = 'green',\
            line_width = 1.25,line_alpha = 0,fill_alpha = 1,hover_line_alpha = 1,\
            selection_line_color = 'red',selection_line_alpha = 1,\
            nonselection_line_alpha = 0,selection_alpha = 1,\
            nonselection_alpha = 0.75,tools = ['hover','tap'],\
            hooks = [hook_black_image])
        self.def_image_placeholder =\
            pn.pane.HoloViews(self.hmap_im)
        self.tap = streams.SingleTap(x = -1,y = -1,source = self.hmap_im)
        self.hov_lims = (self.ds.x.data[0]-0.5,self.ds.x.data[-1]+0.5,\
            self.ds.y.data[0]-0.5,self.ds.y.data[-1]+0.5)
        self.dynamic_graphs_1 = hv.DynamicMap(self.plot_dynamic_spectrum,streams=[self.tap])\
            .opts(frame_height= 250,frame_width = 600,framewise=True,\
            yformatter=formatter,shared_axes=False,show_grid = True,\
            bgcolor = 'black',hooks = [hook_full_black_black])
        '''
        self.pl = plotting(self.ds)
        self.default_image,self.point_image,self.dynamic_graphs_1 = self.pl.create_panel()
        '''

        #self.default_image,self.dynamic_graphs_1 = self.pl.create_panel()
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
            disabled=False,button_type='primary',width = 100,\
            margin = (5,5,5,0))
        self.button_add_element.on_click(self._callback_select_element)
        #Create model_components
        self.button_create_model = pn.widgets.Button(name = 'Create Model',\
            disabled=True,button_type='default',width = 100,\
            margin = 5)
        self.button_create_model.on_click(self._callback_create_default_model)
        
        self.soft_edges_button = pn.Param(self.param,\
            widgets={'soft_edges':pn.widgets.Toggle},\
            parameters = ['soft_edges'],show_name = False,\
                show_labels = True,width = 75,margin = 0)
        self.soft_edges_button[0].margin = 0
        self.soft_edges_button[0].name = 'On'
        self.soft_edges_button[0].button_type = 'success'
        self.soft_edges_button[0].width = 75
        self.soften_val_wid = pn.Param(self.param,\
            widgets={'soften_strength':pn.widgets.Spinner},\
            parameters = ['soften_strength'],show_name = False,\
            show_labels = False,width = 90,margin = (0,5))
        self.soften_val_wid[0].margin = 0

        self.x_sec_selector = pn.Param(self.param,\
            widgets={'x_section_type':pn.widgets.Select},\
            parameters = ['x_section_type'],show_name = False,\
            #name = 'X-section model',\
            show_labels = False,width = 100,margin = (0,0,0,25))
        self.x_sec_selector[0].margin = 0


        #Remove component from model
        self.button_remove_component = pn.widgets.Button(name = 'Remove component',\
            disabled=True,button_type='danger')
        self.button_remove_component.on_click(self._callback_remove_component_model)
        #Reset to empty model
        '''
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
        '''
        #Loading clustering components
        self.button_load_cluster = pn.widgets.Button(name = 'Load cluster file',\
            button_type='default',width = 210,margin = (0,10,5,10))
        self.button_load_cluster.disabled = True
        self.button_load_cluster.on_click(self._callback_open_cluster_ref)
        # To add the whole clustering information
        self.button_add_clusters = pn.widgets.Button(name = 'Full clustering',\
            button_type='default',width = 210,margin = (10,10,0,10))
        self.button_add_clusters.disabled = True
        self.button_add_clusters.on_click(self._callback_add_clusters_ref)
        #To add only the labelling map for the new image
        '''
        self.button_add_mapping = pn.widgets.Button(name = 'Label Map',\
            button_type='default',width = 95,margin = (10,10,0,10))
        self.button_add_mapping.disabled = True
        self.button_add_mapping.on_click(self._callback_add_clusters_ref)
        '''
        #Reset initial values for the paramenters
        self.button_reset_parameters = pn.widgets.Button(name = 'Reset parameters',\
            button_type= 'warning')
        self.button_reset_parameters.on_click(self._callback_resert_param_values)
        self.button_reset_parameters.disabled = True 
        #Fit current references
        self.button_fit_references = pn.widgets.Button(name = 'Fit Reference Spectra',\
            button_type = 'default',width = 155,margin = (10,15))
        self.button_fit_references.disabled = True 
        self.button_fit_references.on_click(self._callback_fit_references)
        self.button_fit_ref_select_area = pn.widgets.Button(name = self.ref_fit_area,\
            button_type = 'default',width = 155,margin = (10,15))
        self.button_fit_ref_select_area.on_click(self._callback_select_fit_ref_areas)
        self.button_fit_ref_select_area.disabled = True
        #This is a special button
        self.button_show_center = pn.Param(self.param,widgets={'show_center':pn.widgets.Toggle},\
            parameters = ['show_center'],show_name = False,show_labels = False,width = 175)
        self.button_show_center[0].name = 'Component-center'
        #self.button_show_center[0].width = 150  
        self.button_show_center[0].button_type = 'default'
        self.button_show_sigmas = pn.Param(self.param,widgets={'show_fwhm':pn.widgets.Toggle},\
            parameters = ['show_fwhm'],show_name = False,show_labels = False,width = 175)
        self.button_show_sigmas[0].button_type = 'default'
        self.button_show_sigmas[0].name = 'Component-fwhm'
        #self.button_show_sigmas[0].width = 150  
        #Button to add components
        self.button_add_extra_compo = pn.widgets.Button(name = 'Add extra component',\
            button_type = 'default')
        self.button_add_extra_compo.disabled = True
        self.button_add_extra_compo.on_click(self._callback_create_extra_component)
        #Button to add extra components in a rerun
        self.button_add_extra_compo_rerun = pn.widgets.Button(name = 'Add new component / re-Run',\
            button_type = 'default')
        self.button_add_extra_compo_rerun.disabled = True
        self.button_add_extra_compo_rerun.on_click(self._callback_create_extra_component_rerun)
        #Button to activate the second model fitting
        #Button to be clicked to start the multifit
        self.button_multifit = pn.widgets.Button(name = 'MultiFit',\
            button_type = 'default',width = 280,margin = (5,20))
        self.button_multifit.disabled = True
        self.button_multifit.on_click(self._callback_multifit)
        self.button_save_data = pn.widgets.Button(name = 'Save Data-Images',\
            button_type = 'default',disabled = True,width = 335,\
            height = 35,margin = (10,20,0,30),\
            css_classes = ['custom_button_bokeh_black'])
        self.button_save_config = pn.widgets.Button(name = 'Save Config.',\
            button_type = 'default',disabled = True,width = 100,\
            height = 35,margin = (5,10),css_classes = ['custom_button_bokeh_white',\
            'custom_button_bokeh_white_enabled'])
        self.button_save_model = pn.widgets.Button(name = 'Save',\
            button_type = 'default',disabled = True,width = 60,\
            height = 33,margin = (5,0,5,20),css_classes = ['custom_button_bokeh_black'])
        self.button_save_data.on_click(self._callback_save_data_images)
        self.button_save_config.on_click(self._callback_save_config)
        self.button_save_model.on_click(self._callback_save_model)
        '''
        self.button_load_mod = pn.widgets.Button(name = 'Load-Model',width = 100,\
            height = 35,margin = (10,0,15,20),css_classes = ['custom_button_bokeh_black'])
        self.button_load_mod.on_click(self._callback_load_prepared_model_config)
        '''
        #Button toggle for the new component center to be displayed
        self.button_new_compo_center_show = pn.Param(self.param['new_compo_toggle'],\
            widgets = {'new_compo_toggle':pn.widgets.Toggle},\
            parameters = ['new_compo_toggle'],\
            show_labels = False,width = 50)
        self.button_new_compo_center_show[0].name = 'Show'
        self.button_new_compo_center_show[0].disabled = True
        self.button_new_compo_center_show[0].button_type = 'default'
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
        self.button_analysis_run = pn.widgets.Button(name = 'Get multifit results for analysis',\
            width = 275)
        self.button_analysis_run.disabled = True
        self.button_analysis_run.on_click(self._callback_get_analysis_data)
        #Button to get the results after rerunning
        self.button_analysis_rerun = pn.widgets.Button(name = 'Get \'Re-Run\' results for analysis',\
            width = 275)
        self.button_analysis_rerun.disabled = True
        self.button_analysis_rerun.on_click(self._callback_get_analysis_rerun_data)
        #This button changes the displayed graph in the analysis tab lateral bar
        self.button_change_info_display = pn.Param(self.param['change_analysis_disp_graph'],\
            widgets = {'change_analysis_disp_graph':pn.widgets.Toggle},\
            parameters = ['change_analysis_disp_graph'],\
            show_labels = False,width = 275,margin = (0,37))
        self.button_change_info_display[0].name = 'Showing fitted areas'
        self.button_change_info_display[0].disabled = True
        #This button changes the style of the total red-chi-square heatmap
        self.button_change_styling_RCS = pn.widgets.Button(name = 'Change Style',width = 275)
        self.button_change_styling_RCS.disabled = True
        self.button_change_styling_RCS.on_click(self._callback_change_styles_totRCS)
        #This button overlays cluster limits with the RCS mappings
        self.button_overlay_cluster_RCS = pn.Param(self.param['overlay_clusters_RCS'],\
            widgets = {'overlay_clusters_RCS':pn.widgets.Toggle},\
            parameters = ['overlay_clusters_RCS'],show_labels = False, show_name = False,width = 275)
        self.button_overlay_cluster_RCS[0].disabled = True
        self.button_overlay_cluster_RCS[0].button_type = 'default'
        #This button adds a new column of Error Heatmaps
        self.button_add_column_errormaps = pn.widgets.Button(name = 'Add Error mapping',width = 235)
        self.button_add_column_errormaps.disabled = True
        self.button_add_column_errormaps.on_click(self._callback_add_errormaps)
        #This button erase a column of error maps
        self.button_erase_column_errormaps = pn.widgets.Button(name = 'Erase Error mapping',width = 235)
        self.button_erase_column_errormaps.disabled = True
        self.button_erase_column_errormaps.on_click(self._callback_erase_errormaps)
        #BUtton to activate possible rerun
        self.button_activate_rerun = pn.widgets.Button(name = 'Begin New/Modified model configuration',\
            width = 300)
        self.button_activate_rerun.disabled = True
        self.button_activate_rerun.on_click(self._callback_activate_possible_rerun)
        #Buttons to lock all components and unlock all components
        self.button_lock_all = pn.widgets.Button(name = 'Lock All',width = 135)
        self.button_lock_all.disabled = True
        self.button_lock_all.on_click(self._callback_lock_all_comp)
        self.button_unlock_all = pn.widgets.Button(name = 'Unlock All',width = 135)
        self.button_unlock_all.disabled = True
        self.button_unlock_all.on_click(self._callback_unlock_all_comp)
        self.button_overlay_clusters_active = pn.Param(self.param['overlay_clust_bool'],\
            widgets = {'overlay_clust_bool':pn.widgets.Toggle},\
            parameters = ['overlay_clust_bool'],show_name = False,show_labels = False,\
            width = 175)
        self.button_overlay_clusters_active[0].width = 150    
        self.button_overlay_clusters_active[0].name = 'Overlay Cluster Map'
        self.button_overlay_clusters_active[0].button_type = 'default'
        self.button_overlay_clusters_active[0].disabled = True
        #Control of the model in this class ----------------------------------------------
        self.model_element_dict = {'default':dict()}
        self.model = False
        #Interactive elements -------------------------------------------------------------
        #Energy onset display widget
        self.text_pane = pn.pane.Markdown('Choose Subshell/s',\
            margin = (0,25),\
            styles={'color' : 'white'},\
            width = 300,height = 125)
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
            show_name = False,default_layout = pn.GridBox,\
            height = 120,margin = (5,10),width = 300)
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
        #self.model_ELNES_parameters.ncols = 3
        self.model_ELNES_parameters[0].width = 280
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
            show_name = False,default_layout = pn.GridBox,\
            height = 120,margin = (5,10),width = 300)
        for el in self.model_continuum_parameters[0]:
            if 'Chem' == el.name:
                el.bar_color = '#FC7651'
            elif 'A' == el.name[0]:
                el.bar_color = '#F9546B'
        self.model_continuum_parameters[0][0].name = 'Amplitude'
        self.model_continuum_parameters.layout.objects[0].ncols = 2
        self.model_continuum_parameters[0].width = 280
        for el in self.model_continuum_parameters[0]:
            el.disabled = True
        #By default
        #TODO changes here - check stability
        #self.model_continuum_parameters.default_layout.ncols = 1
        self.parameter_configurator = self.model_continuum_parameters
        
        #Creation of the tools for clustering loading
        self.path_widget = pn.Param(self.param['path_toClust'],\
            widgets={'path_toClust' : pn.widgets.TextInput},\
            parameters = ['path_toClust'],show_name = True,\
            name = 'Path to clustering segmentation file',\
            show_labels = False,width = 320,margin = (0,15,5,15))
        self.path_widget[0].margin = (2,10)
        self.path_widget[0].style = {'color':'white'}
        self.path_widget[1].margin = (2,10)
        self.file_widget = pn.Param(self.param['file_clust'],\
            widgets={'file_clust':pn.widgets.Select},\
            parameters = ['file_clust'],show_name = True,\
            name = 'Clustering segmentation file',\
            show_labels = False,width = 320,margin = (5,15))
        self.file_widget[0].margin = (2,10)
        self.file_widget[0].style = {'color':'white'}
        self.file_widget[1].margin = (2,10)
        #For the overlay between SI and masks of different areas
        image_xr = xr.Dataset({'counts':(['y','x'],\
            self.ds.sum('Eloss').ElectronCount.values)},\
            coords = {'x':self.ds.x.values,'y':self.ds.y.values})
        '''
        self.image_SI = hv.Image(image_xr,kdims=['x','y']).\
            opts(aspect = 'equal',invert_yaxis=True,cmap = 'Greys_r',\
            xaxis=None, yaxis=None,\
            xlim = self.xlims,ylim = self.ylims)
        '''
        self.image_for_analysis = hv.Image(image_xr,kdims=['x','y']).\
            opts(aspect = 'equal',invert_yaxis=True,cmap = 'Greys_r',\
            xaxis=None, yaxis=None,frame_width = 225,\
            xlim = self.xlims,ylim = self.ylims)
        self.cmap_binary = ['black','aquamarine']
        '''
        self.overlay_image = hv.Overlay([self.image_SI]).\
            opts(frame_height = 250)
        '''
        self.area_sel_wid = pn.Param(self.param,\
            widgets={'area':pn.widgets.Select},\
            parameters=['area'], show_name = False,\
            show_labels = False,width = 175)
        '''
        self.area_selector = pn.Column(\
            pn.pane.Markdown('### Model Configuration Panel'),\
            pn.layout.Divider(margin = (-10,0,0,0)),\
            pn.pane.Markdown('### Area Selector'),\
            self.area_sel_wid,\
            self.overlay_image,\
            margin = (0,0,10,0))
        self.area_selector[-2].show_labels = False
        self.area_selector[2].margin = (5,15)
        '''
        #widget_box to load cluster
        self.colores = [] #Initialized empty to avoid local variable undefined error
        self.colordict = dict()

        #Deprecated panel structure
        
        '''
        self.box[0][0].margin = (0,5,-10,5)
        self.box[0].style = ({'color' : 'white'})
        '''
        self.def_cluster_im =\
        hv.Image(xr.Dataset({'None':(['y','x'],\
            np.zeros_like(self.ds.ElectronCount.sum('Eloss').values))},\
            coords = {'x':self.ds.x.values,'y':self.ds.y.values}),\
        kdims = ['x','y'])\
        .opts(aspect = 'equal',\
        xaxis=None, yaxis=None,frame_height = 80,bgcolor = 'black',\
        xlim = self.xlims,ylim = self.ylims,\
        border = 0, toolbar = None,cmap = 'Greys')
        self.clust_im_placeholder = pn.pane.HoloViews(self.def_cluster_im)
        self.box = pn.Column(\
            pn.layout.Divider(margin = (5,5,10,5),height = 10),\
            self.path_widget,self.file_widget,\
            pn.Row(pn.Column(self.button_load_cluster,\
                self.button_add_clusters),\
                self.clust_im_placeholder,margin = (5,15)),\
            margin = (10,0),width = 350, styles={'background': 'black'})
        
        #self.cluster_box_pane = pn.Row(self.box,self.def_cluster_im,background='black',width = 665)
        

        #The sign that shows the current model area displaying parameters
        self.mk1 = pn.pane.Markdown('#### _Selected area_ :',\
            styles={'color':'black'},height = 25,width = 100,margin = (0,10)) 
        self.mk2 = pn.pane.Markdown('#### - {} -'.format(self.area),\
            styles = {'color':self.cmap_binary[-1]},\
            width = 155,height = 25,margin = 0)
        self.current_area_mkdwn = pn.Row(self.mk1,self.mk2,\
            height = 35,width = 290,margin = (5,15,0,15),\
            css_classes = ['custom_box_model_param'], styles={'background': 'white'})
        #The component type of funtion for the ELNES elements
        self.default_compo_funcs = cp.deepcopy(self.param['type_compo'].objects)
        self.button_compo_func = pn.Param(self.param,\
            widgets = {'type_compo' : pn.widgets.Select},\
            parameters = ['type_compo'],\
            show_labels = False,show_name = False,\
            margin = (15,25,5,25),width = 270)
        self.button_compo_func[0].margin = 0
        self.button_compo_func[0].disabled = True


        #Extra dictionary for fwhm from sigmas
        self.fwhm_dict = {'Gaussian':(lambda sig: 2*sig*np.sqrt(2*np.log(2))),\
            'Lorentzian':(lambda sig: 2*sig),\
            'Pseudovoigt':(lambda sig: 2*sig),\
            'Splitlorentzian':(lambda sig: 2*sig)}
        #For the overlay of reference spectra
        # Create a 1D xarray Dataset for default_curve_references to avoid HoloViews/xarray dimension errors
        empty_curve_ds = xr.Dataset({'ElectronCounts': (['Eloss'], np.zeros(10))}, coords={'Eloss': np.arange(10)})
        self.default_curve_references = hv.Curve(empty_curve_ds, kdims='Eloss', vdims='ElectronCounts')\
            .opts(frame_height=250, frame_width=600,\
                  show_grid=True, yformatter=formatter,\
                  bgcolor='black', hooks=[hook_full_black_black])
        self.dictionary_references = {'empty':self.default_curve_references}
        #Dictionaries to store fittings of the reference spectra
        self.dictionary_fitted_ref = dict()
        self.dictionary_fitted_ref_compos = dict()
        self.dictionary_fitted_ref_overall = dict()
        #The progress bar
        self.prog_bar = pn.Param(self.param['prog'],\
            widgets = {'prog':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['prog'],width = 280,margin = (5,20))
        self.prog_bar[0].width =280
        self.prog_bar[0].margin = 0
        #This two variables control if the multifit run is fresh or is a re-fit
        self.run_dict = dict()
        self.fresh = True #is it a fresh run? or a re-run (self.fresh = False)
        #This is the placeholder image for the info panel in the analysis window
        self.init_info_fill_image =  hv.Image(self.ds.ElectronCount.sum(dim = 'Eloss'),\
            kdims = ['x','y'])\
            .opts(bgcolor = 'black',aspect = 'equal',\
                invert_yaxis=True,cmap = 'greys_r',\
                xaxis = None,yaxis = None,padding = 0,frame_height = 200,border = 0,\
                xlim = self.xlims,ylim = self.ylims,\
                hooks = [hook_full_black],shared_axes = False)
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
        self.clustering_in_place = False
        #widgets and widgetbox to load configuration for the model creator
        self.dictio_loaded_model = dict()
        self.fileinp = pn.widgets.FileInput(css_classes=['pnx-file-load-model'],\
                width = 75,height = 35,margin = (5,10,5,5),accept='.json')
        self.button_load_model_fromfile = pn.widgets.Button(name = 'Load-Model',\
            disabled = True,width = 210,height = 35,margin = (5,10),\
            css_classes = ['custom_button_bokeh_black'])
        self.button_load_model_fromfile .on_click(self._callback_button_load)
        self.mkdown_click = pn.pane.Markdown('#### Load FromFile:',\
            width = 100,height = 30,margin = 0,styles = {'color':'white'})
        self.mkdown_file_picked = pn.pane.Markdown('#### NoFile',\
            height = 30,width = 180,margin = (0,15,0,10),\
            styles = {'color':'white','overflow':'hidden'})
        self.fileinp.link(self.mkdown_file_picked,\
            callbacks={'filename': self._callback_change_Loadfilename})
        self.widget_box_load_model =\
        pn.Column(pn.Row(self.mkdown_click,self.mkdown_file_picked, styles={'background': 'black'}),\
            pn.Row(self.fileinp,self.button_load_model_fromfile),\
            width = 320,height = 80,margin = (0,15))
        #widgets and widgetbox for the model configurator loader
        self.button_load_model_config = pn.widgets.Button(name = 'Load-Configuration',\
            disabled = True,width = 205,height = 35,margin = (5,10),\
            css_classes = ['custom_button_bokeh_white','custom_button_bokeh_white_enabled'])
        self.button_load_model_config.on_click(self._callback_load_prepared_model_config)
        self.configinp = pn.widgets.FileInput(css_classes=['pnx-file-load-config'],\
                width = 75,height = 35,margin = (5,10,5,5),accept='.json',\
                disabled = True)
        self.mkdown_config_messages = pn.pane.Markdown('#### Load cluster file to unlock config',\
            width = 280,margin = (5,10),\
            styles = {'color':'crimson','overflow':'hidden'})
        self.mkdown_config_picked = pn.pane.Markdown('#### NoConfigFile',\
            height = 30,width = 180,margin = (0,15,0,10),\
            styles = {'color':'lightgrey','overflow':'hidden'})
        self.configinp.link(self.mkdown_config_messages,\
            callbacks={'filename': self._callback_change_Configfilename})
        mkdown_click2 = pn.pane.Markdown('#### Select file :',\
            width = 75,height = 30,margin = (0,5,0,10),styles = {'color':'black'})
        self.widget_box_load_configuration =\
        pn.Column(pn.layout.Divider(margin = (0,10)),self.mkdown_config_messages,\
            pn.Row(mkdown_click2,self.mkdown_config_picked),\
            pn.Row(self.configinp,self.button_load_model_config),width = 320)
    
    @param.depends('soft_edges',watch = True)
    def control_soften_edges(self):
        #Method controloing the button for the 'softening' of edges
        if self.soft_edges:
            self.soft_edges_button[0].name = 'On'
            self.soft_edges_button[0].button_type = 'success'
        else:
            self.soft_edges_button[0].name = 'Off'
            self.soft_edges_button[0].button_type = 'danger'
    

    def plot_dynamic_spectrum(self,x,y):
        #Method in charge of plotting the spectrum when hovering over the image
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            curve = hv.Area([], 'Eloss', 'ElectronCount')\
                .opts(color='blue',fill_alpha=0.5,line_color='black',\
                bgcolor = 'black',hooks = [hook_full_black_black])
            # Removed .opts on DynamicMap/None
            return curve
        elif y >= yf or y <= yi:
            curve = hv.Area([], 'Eloss', 'ElectronCount')\
                .opts(color='blue',fill_alpha=0.5,line_color='black',\
                bgcolor = 'black',hooks = [hook_full_black_black])
            # Removed .opts on DynamicMap/None
            return curve
        else:
            x0, y0 = int(round(x)), int(round(y))
            curve = hv.Area(self.ds.isel(x = int(x0),y = int(y0)))\
                .opts(color='blue',fill_alpha=0.5,line_color='white',\
                fill_color = 'red',\
                bgcolor = 'black',hooks = [hook_full_black_black])
            # Removed .opts on DynamicMap/None
            return curve

    def _callback_save_model(self,event):
        #Checking the saving direction
        if 'Savings-Workspace' not in os.listdir():
            os.mkdir('Savings-Workspace')
        try:
            name = self.ds.attrs['original_name'].split('.')[0]
        except Exception as e:
            print(e)
            name = 'Sample_NoName'
        finally:
            if name not in os.listdir('./Savings-Workspace'):
                os.mkdir('./Savings-Workspace/{}'.format(name))
            if 'Config_Files' not in os.listdir('./Savings-Workspace/{}'.format(name)):
                os.mkdir('./Savings-Workspace/{}/Config_Files'.format(name))
        folder = './Savings-Workspace/{}/Config_Files'.format(name) 
        dictio_m = dict()
        dictio_m['elements'] = dict()
        for elm in self.param['model_element'].objects:
            dictio_m['elements'][elm] =\
            list(self.NLLS.models_components['default'][elm]['continuum'].keys())
        lista_name = ['{}{}'.format(el,''.join(dictio_m[el])) for el in dictio_m]
        model_name = '{}/{}.json'.format(folder,'-'.join(lista_name))
        with open(model_name,'w') as f:
            json.dump(dictio_m,f)

    

    def _callback_button_load(self,event):
        """This method is called by the loading model button,
        in order to generate the model (elements and subshells)
        from the previosly loaded dictionary from json
        """
        for el in self.dictio_loaded_model['elements']:
            self.elemento = el
            self.subshell = self.dictio_loaded_model['elements'][el]
            self._callback_select_element(True)
        self._callback_create_default_model(True)
            
        
    def _callback_change_Loadfilename(self,target, event):
        """Callback method to unlock the model file loader
        It is called by the watcher in fileinp, and automatically
        reads the json selected to get the model components ready
        for the loading callback method
        """
        #Now .. let's try to extract the possible model from the file
        self.dictio_loaded_model = json.loads(self.fileinp.value)
        if 'elements' in self.dictio_loaded_model:
            target.object = '#### {}'.format(event.new)
            self.button_load_model_fromfile.disabled = False
        else:
            target.object = '#### Invalid format'
            self.button_load_model_fromfile.disabled = True

    def _callback_change_Configfilename(self,target, event):
        """Callback method to unlock the model file loader
        It is called by the watcher in fileinp, and automatically
        reads the json selected to get the model components ready
        for the loading callback method
        """
        #Now .. let's try to extract the possible model from the file
        dictio_loaded_config = cp.deepcopy(json.loads(self.configinp.value))
        #Let's check that we are dealing with the same bunch of elements
        if 'elements' not in dictio_loaded_config:
            target.object = 'Non-valid file'
            target.styles = {'color':'crimson'}
            self.dictio_loaded_config = dict()
            self.mkdown_config_picked.object =\
                '#### {}'.format(event.new)  
            self.mkdown_config_picked.styles =\
                {'color':'crimson','overflow':'hidden'}
            return
        else:
            elems_list = list(dictio_loaded_config['elements'])
            elems_list.sort()
            ssh_list = []
            #print(elems_list)
            
            for el in elems_list:
                #print(dictio_loaded_config['elements'])
                listo = cp.deepcopy(list(dictio_loaded_config['elements'][el]))
                listo.sort()
                ssh_list.extend(listo)
            lista_el = cp.deepcopy(list(self.param['model_element'].objects))
            lista_el.sort()
            lista_ssh = []
            for el in lista_el:
                listo2 =\
                cp.deepcopy(list(self.NLLS.models_components['default'][el]['continuum']))
                listo2.sort()
                lista_ssh.extend(listo2)
            #Time to evaluate
            if elems_list != lista_el:
                target.object = 'Non-valid file - different elements'
                target.s = {'color':'crimson'}
                self.dictio_loaded_config = dict()
                self.mkdown_config_picked.object =\
                    '#### {}'.format(event.new)  
                self.mkdown_config_picked.styles =\
                    {'color':'crimson','overflow':'hidden'}
            elif elems_list == lista_el and lista_ssh != ssh_list:
                target.object = 'Non-valid file - different subshells'
                target.styles = {'color':'crimson'}
                self.dictio_loaded_config = dict()
                self.mkdown_config_picked.object =\
                    '#### {}'.format(event.new)  
                self.mkdown_config_picked.styles =\
                    {'color':'crimson','overflow':'hidden'}
            else: pass
        #Next criteria
        try:
            #We only hit this part when dictio loaded is a promissing option
            sname = dictio_loaded_config['clustering']['cname']
        except:
            target.object = '#### No-cluster data found'
            target.styles = {'color':'crimson'}
            self.button_load_model_config.button_type = 'default'
            self.button_load_model_config.disabled = True
            self.dictio_loaded_config = dict()
            self.mkdown_config_picked.styles =\
                {'color':'crimson','overflow':'hidden'}
        else:
            if sname == self.file_clust:
                target.object = '#### Valid file loaded - proceed'
                target.styles = {'color':'limegreen'}
                self.button_load_model_config.disabled = False
                self.button_load_model_config.button_type = 'success'
                self.dictio_loaded_config = dictio_loaded_config
                self.mkdown_config_picked.styles =\
                    {'color':'limegreen','overflow':'hidden'}
            else:
                target.object = '#### Different cluster references'
                target.styles = {'color':'crimson'}
                self.dictio_loaded_config = dict()
                self.button_load_model_config.button_type = 'default'
                self.button_load_model_config.disabled = True
                self.mkdown_config_picked.styles =\
                    {'color':'crimson','overflow':'hidden'}
        finally:
            self.mkdown_config_picked.object =\
                '#### {}'.format(event.new)  
            

    def _callback_load_prepared_model_config(self,event):
        #First, let's adjust the current component
        #Work in progress
        areas = self.dictio_loaded_config['areas']
        elmts = list(self.dictio_loaded_config['elements'])
        for ar in areas:
            for el in elmts:
                #Continuum 
                for cpar in self.dictio_loaded_config[ar][el]['continuum_init_const']:
                    for para in self.dictio_loaded_config[ar][el]['continuum_init_const'][cpar]:
                        self.NLLS.models_components[ar][el]['continuum_init_const'][cpar][para] =\
                        cp.deepcopy(self.dictio_loaded_config[ar][el]['continuum_init_const'][cpar][para])
                #Checking if we have removed any element
                #ELNES
                curr_keys = list(self.NLLS.models_components[ar][el]['ELNES'])
                for cmp in curr_keys:
                    if cmp not in self.dictio_loaded_config[ar][el]['ELNES']:
                        print(ar,el,cmp,'deleting!')
                        self.NLLS.delete_component(el,cmp,ar)
                        
                #Checking if we have to add any component
                cmps_ext = list(self.dictio_loaded_config[ar][el]['ELNES'])
                for cmpx in cmps_ext:
                    if cmpx not in self.NLLS.models_components[ar][el]['ELNES']:
                        print(ar,el,cmpx,'Adding!')
                        eloss = cp.deepcopy(\
                            self.dictio_loaded_config[ar][el]['ELNES'][cmpx]['center'])
                        tipo = cp.deepcopy(\
                            self.dictio_loaded_config[ar][el]['ELNES'][cmpx]['type_compo'])
                        self.NLLS.create_extra_component(element = el,\
                            name = cmpx, eloss = eloss,name_area = ar, type_predet = tipo,\
                            flex = 'medium')
                        self.model_element_dict[ar][el]['ELNES'][cmpx] =\
                        cp.deepcopy(self.NLLS.models_components[ar][el]\
                            ['ELNES'][cmpx])
                #Changing parameters
                for par in self.dictio_loaded_config[ar][el]['ELNES']:
                    if par in self.NLLS.models_components[ar][el]['ELNES']:
                        for para in self.dictio_loaded_config[ar][el]['ELNES'][par]:
                            self.NLLS.models_components[ar][el]['ELNES'][par][para] =\
                            cp.deepcopy(self.dictio_loaded_config[ar][el]['ELNES'][par][para])
                #ELNES bounds loading
                for par_i in self.dictio_loaded_config[ar][el]['ELNES_init_const']:
                    if par_i in self.NLLS.models_components[ar][el]['ELNES_init_const']:
                        for parai in self.dictio_loaded_config[ar][el]['ELNES_init_const'][par_i]:
                            val = self.dictio_loaded_config[ar][el]['ELNES_init_const'][par][parai]
                            if val == 'inf':
                                self.NLLS.models_components[ar][el]['ELNES_init_const']\
                                [par][parai] = float('inf')
                            elif val == '-inf':
                                self.NLLS.models_components[ar][el]['ELNES_init_const']\
                                [par][parai] = float('-inf')
                            else:
                                self.NLLS.models_components[ar][el]['ELNES_init_const']\
                                [par][parai] = cp.deepcopy(val)

        if self.model_type_component == 'continuum':
            self.model_type_component = 'ELNES'
        if self.model_type_component == 'ELNES':
            self.model_type_component = 'continuum'

    def _callback_save_config(self,event):
        #Changing and creating the needed folders
        if 'Savings-Workspace' not in os.listdir():
            os.mkdir('Savings-Workspace')
        try:
            name = self.ds.attrs['original_name'].split('.')[0]
        except Exception as e:
            print(e)
            name = 'Sample_NoName'
        finally:
            if name not in os.listdir('./Savings-Workspace'):
                os.mkdir('./Savings-Workspace/{}'.format(name))
            if 'Config_Files' not in os.listdir('./Savings-Workspace/{}'.format(name)):
                os.mkdir('./Savings-Workspace/{}/Config_Files'.format(name))
        folder = './Savings-Workspace/{}/Config_Files'.format(name) 
        #Work in progress
        dictio_c = dict()
        dictio_c['elements'] = dict()
        for elm in self.param['model_element'].objects:
            dictio_c['elements'][elm] =\
            list(self.NLLS.models_components['default'][elm]['continuum'].keys())
        dictio_c['areas'] = self.param['area'].objects
        if self.clustering_in_place:
            dictio_c['clustering'] =\
            {'fname':self.ds.attrs['original_name'].split('.')[0],\
            'cname':self.clustering_name,'directory':self.clustering_directory}
        for ar in self.param['area'].objects:
            dictio_c[ar] = dict()
            for el in self.param['model_element'].objects:
                dictio_c[ar][el] = dict()
                dictio_c[ar][el]['ELNES'] =\
                    cp.deepcopy(self.NLLS.models_components[ar][el]['ELNES'])
                dictio_c[ar][el]['continuum_init_const'] =\
                    cp.deepcopy(self.NLLS.models_components[ar][el]['continuum_init_const'])
                dictio_c[ar][el]['ELNES_init_const'] =\
                    cp.deepcopy(self.NLLS.models_components[ar][el]['ELNES_init_const'])
                #To catch the infinities and set them to a reasonable number
                for ssh in dictio_c[ar][el]['ELNES_init_const']:
                    for par in dictio_c[ar][el]['ELNES_init_const'][ssh]:
                        val = dictio_c[ar][el]['ELNES_init_const'][ssh][par] 
                        if val == float('-inf'):
                            dictio_c[ar][el]['ELNES_init_const'][ssh][par] = '-inf'
                        elif val == float('inf'):
                            dictio_c[ar][el]['ELNES_init_const'][ssh][par] = 'inf'
                        else: pass
        #Setting the file name and path
        nclust = int(len(self.param['area'].objects) - 1)
        oname =  ''.join(list(dictio_c['elements']))
        time_string = '{}_{}'.format(time.strftime('%Y%m%d',time.gmtime()),\
            time.strftime('%H\'%M\'%S',time.gmtime()))
        config_name = '{}/{}_{}clst_{}.json'.format(folder,oname,nclust,time_string)
        with open(config_name,'w') as f:
            json.dump(dictio_c,f,allow_nan= False)

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

    def _callback_save_data_images(self,event):
        #Here we have to select tha actual data to be passes to the saving module
        #############################################
        #Data selection
        if len(list(self.dictionary_fitted_ref_overall.keys())) < 1:
            #Safety measure ... in case of not having any fitted data
            return
        ds_list = []
        for el in self.dictionary_fitted_ref_compos:
            ds_list.append(\
                self.dictionary_fitted_ref_overall[el].data[('Curve', 'I')].data\
                .rename({'ElectronCounts':'{} BestFit'.format(el)}))
        ds_copy = cp.deepcopy(self.ds)
        #This should be deprecated in a near future...
        #as those hyperspy objects shouldn't be mixed here.
        #They are part of a legacy feature
        if 'original_metadata' in ds_copy.attrs:
            ds_copy.attrs.pop('original_metadata')
        if 'original_axes_manager' in ds_copy.attrs:
            ds_copy.attrs.pop('original_axes_manager')
        ds_list.append(ds_copy)
        ##########################################
        #Images selection
        lista_images = []
        lista_nombres = []
        for ele in self.dictionary_fitted_ref_compos:
            lista_images.append(hv.Overlay.clone(self.dictionary_fitted_ref_compos[ele]))
            lista_nombres.append('Components {}'.format(ele))
            lista_images.append(hv.Overlay.clone(self.dictionary_fitted_ref_overall[ele]))
            lista_nombres.append('BestFit {}'.format(ele))
        ds_to_save = xr.merge(ds_list)
        if ds_to_save.attrs == dict():
            #In case of xarray dropping the attributes as it used to do
            ds_to_save.attrs = self.ds.attrs
        sv = Saving_panel(ds = ds_to_save,\
            figures = lista_images, figures_names = lista_nombres,\
            name_panel = 'model-constructor')
        sv.create_layout()


    def _callback_open_cluster_ref(self,event):
        try:
            self.dsCluster = xr.load_dataset('/'.join([self.path_toClust,self.file_clust]))
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
            long =  len(cluster_number)
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
            self.cluster_im = hv.Image(self.dsCluster['labs'],kdims = ['x','y'])\
                .opts(aspect = 'equal',invert_yaxis=True,\
                    xaxis=None, yaxis=None,cmap = self.colores[:long],\
                    xlim = self.xlims,ylim = self.ylims,\
                    shared_axes= False,\
                    frame_height = 80,\
                    alpha = 0.60,\
                    bgcolor = 'lightgrey',\
                    border = 0, toolbar = None)
            self.clust_im_placeholder.object = self.cluster_im
            #NOw the modification of the file, in case of having a different ref cluster im
            str_clu = ''.join(self.file_clust.split('.')[:-1])
            if f'{str_clu}.json' in os.listdir(self.path_toClust):
                #Having checked that we have the json file needed
                #Loading the json info
                with open('/'.join([self.path_toClust,f'{str_clu}.json'])) as f:
                    info_clst = json.load(f) 
                if ''.join(self.ds.original_name.split('.')[:-1]) != info_clst['Original_name']:
                    #Now the triky part... changing the references in self.dsCluster
                    #It may even happend that teh Eloss axis is different
                    new_ds = xr.Dataset({\
                        'labs':(['y','x'],self.dsCluster.labs.values.copy()),\
                        'Centroids':(['label_number','Eloss'],\
                            np.zeros((self.dsCluster.label_number.values.copy().size,\
                            self.ds.Eloss.values.size))),\
                        'ElectronCount':(['y','x','Eloss'],self.ds.ElectronCount.values.copy())\
                        },\
                        coords={'Eloss':self.ds.Eloss.values.copy(),\
                            'x':self.ds.x.values.copy(),\
                            'y':self.ds.y.values.copy(),\
                            'label_number':self.dsCluster.label_number.values.copy()})
                    zer_Ecounts = np.zeros_like(self.ds.ElectronCount.values)
                    zer_cents = np.zeros((new_ds.label_number.values.size,self.ds.Eloss.values.size))
                    for el in self.dsCluster.label_number.values:
                        #Let's get the new centroids going
                        zer_cents[el,:] = new_ds.ElectronCount.values[new_ds.labs.values == el,:].mean(axis = 0)
                        zer_Ecounts[new_ds.labs.values == el,:] = zer_cents[el,:]
                    #Let's integrate it
                    new_ds['ElectronCount_norm_Centroids'] = (['label_number','Eloss'],zer_cents)
                    new_ds['Centroid_pixel'] = (['y','x','Eloss'],zer_Ecounts)
                    #And the replacement
                    self.dsCluster = new_ds
                
    

    def _callback_add_clusters_ref(self,event):
        lista = ['default']
        try:
            self.NLLS.add_clustering_references(self.dsCluster,soften = self.soft_edges, soften_val = self.soften_strength)
        except Exception as e:
            print(e)
            return #Safety measure for the button, in case of malfunctioning
        else:
            #In case of having added something - we need to modify the defaults dict
            #Carefull - when adding a new reference with lower cluster numbers, the 
            #options to modify the previous extra clusters are hidden...but they still exist
            #within the NLLS model class
            self.clustering_in_place = True
            self.clustering_name = cp.deepcopy(self.file_clust)
            self.clustering_directory = cp.deepcopy(self.path_toClust)

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
                        hv.Area(data = xr.Dataset({'ElectronCounts':(['Eloss'],\
                            self.NLLS.ref_spectra[el])}\
                        ,coords = {'Eloss':self.NLLS.Eloss}))\
                        .opts(yformatter=formatter,\
                        shared_axes=False,\
                        #responsive = True,\
                        show_grid = True,\
                        color = self.colores[i-1],frame_height = 250,\
                        frame_width = 600,selection_fill_alpha = 1,\
                        nonselection_fill_alpha = 0.1)
                else:
                    self.colordict[el] = 'aquamarine'
            #self.tabs_references[0].pop(0)
            #self.tabs_references[0].pop(-1)
            self.ref_overlay_placeholder.object =\
                hv.NdOverlay(self.dictionary_references)\
                .opts(legend_muted = True,shared_axes = False,\
                hooks = [hook_full_black_black_with_legend],bgcolor = 'black')
            self.button_overlay_clusters_active[0].disabled = False
            #Modi
            #At the end of the day...we need a dataset for the masks
            dicti_for_masks = dict()
            for area_m in self.NLLS.ref_matrices:
                vals = np.ones_like(self.NLLS.ref_matrices[area_m])
                vals[self.NLLS.ref_matrices[area_m] == 0] = np.NaN
                dicti_for_masks[area_m] = (['y','x'],cp.deepcopy(vals))
            xs = self.ds.x.values
            ys = self.ds.y.values
            self.ds_masks = xr.Dataset(dicti_for_masks,\
                        coords = {'x':xs,'y':ys})
            self.configinp.disabled = False
            self.mkdown_config_messages.object = '#### Loaded cluster file - proceed'
            self.mkdown_config_messages.style = {'color':'limegreen'}
            self.button_save_config.disabled = False
            self.button_save_config.button_type = 'success'
            
            
    def search_fit_order(self,name_area):
        stimator_mat = np.zeros_like(self.NLLS.ref_matrices[name_area])
        stimator_mat[:] = -1 #So we now that that point is not in the current cluster
        stimator_mat[self.NLLS.ref_matrices[name_area] == 1] =\
            np.sum(np.square(self.ds.ElectronCount.values[self.NLLS.ref_matrices[name_area] == 1]\
                - self.NLLS.ref_spectra[name_area]),axis = -1)\
            /(self.NLLS.ref_spectra[name_area].size-1)
        #flat_stim = np.sort(stimator_mat[stimator_mat > 0])
        order_mat = np.argsort(stimator_mat[stimator_mat > 0])
        indices_tup = np.where(stimator_mat > 0)
        self.dictio_stimator[name_area] = cp.deepcopy(stimator_mat)
        self.dictio_order_tuples[name_area] = cp.deepcopy(indices_tup)
        self.dictio_order_matrices[name_area] = cp.deepcopy(order_mat)
        

    def _callback_create_default_model(self,event):
        #This controls what happens with the app when creating a model ---- a lot!
        self.button_create_model.name = 'WAIT'
        self.button_create_model.button_type = 'warning'
        self.button_create_model.disabled = True 
        self.soften_val_wid[0].disabled = True
        self.soft_edges_button[0].disabled = True
        #beta-cut is chosen a-priori,since it is the minimun correction always in place
        self.NLLS.ready_elements(type_surface =self.x_section_type,extension=True,mesh_p = 256)
        self.NLLS.create_components(self.NLLS.initial_reference_spectra,\
            soften =self.soft_edges,soften_val = self.soften_strength)
        self.button_create_model.disabled = False
        self.button_create_model.name = 'Model created'
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
        #self.button_reset.disabled = False
        #self.button_reset.button_type = 'warning'
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
            hv.Area(data = xr.Dataset({'ElectronCounts':(['Eloss'],\
                self.NLLS.ref_spectra['default'])}\
            ,coords = {'Eloss':self.NLLS.Eloss}))\
            .opts(yformatter=formatter,\
            shared_axes=False,\
            selection_fill_alpha = 0.5,\
            nonselection_fill_alpha = 0.1,\
            show_grid = True,\
            color = self.cmap_binary[-1],frame_height = 250,frame_width = 600)
        #self.tabs_references[0].pop(0)
        #self.tabs_references[0].pop(-1)
        self.ref_overlay_placeholder.object =\
                hv.NdOverlay(self.dictionary_references)\
                .opts(legend_muted = True,shared_axes = False,\
                hooks = [hook_full_black_black_with_legend],bgcolor = 'black')
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
        self.path_toClust = './clustering_saves'
        #allow creation of config files
        self.button_save_model.disabled = False
        self.fileinp.disabled = True
        self.button_load_model_fromfile.disabled = True
        #self.button_save_config.css_classes = ['custom_button_bokeh_2']
        
    def _callback_remove_component_model(self,event):
        #Method that allows us to remve a certain component from a certain area in the model
        if self.model_type_component == 'ELNES':
            '''
            #TODO new added - check stability
            self.model_element_dict[self.area][self.model_element]['ELNES'].pop(self.model_component)
            '''
            ##
            self.NLLS.delete_component(self.model_element,self.model_component,self.area)
            self.model_element_dict[self.area][self.model_element]['ELNES'].pop(self.model_component)
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
            self.type_compo =\
                (lambda keyword: ' '.join([keyword.capitalize(),'component']))\
                (dictio['type_compo']) 
        else: pass
    
    ''' #Deprecated section - to eliminate model, reboot from the main app
    # It is safer and more stable
    def _callback_enable_delete_model(self,event):
        #Small function that controls the flow of info to delete models
        self.button_delete_model.disabled = False
        self.button_delete_model.button_type = 'danger'
        self.button_deactivate_delete.disabled = False
        self.button_deactivate_delete.button_type = 'success'
        #self.button_reset.disabled = True
        #self.button_reset.button_type = 'default'
        
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
        #self.tabs_references[1].pop(-1)
        #self.tabs_references[1].pop(0)
        self.mkdown_BestFit.object = '#### &nbsp;&nbsp;&nbsp;&nbsp;\
            Best fit for the reference spectra of the - **{}** - area'\
        .format('None')
        self.mkdown_BestFit.style = {'color':'darkgrey'}
        self.best_fit_placeholder.object = self.default_curve_references
        self.mkdown_Compos.object = '#### &nbsp;&nbsp;&nbsp;&nbsp;\
        Fitted individual components for the reference spectra of the **{}** area'\
        .format('None')
        self.mkdown_Compos.style = {'color':'darkgrey'}
        self.compos_placeholder.object = self.default_curve_references
        #And set the area to default
        self.dictionary_references = {'empty':self.default_curve_references}
        self.dictionary_fitted_ref = dict()
        self.dictionary_fitted_ref_compos = dict()
        self.dictionary_fitted_ref_overall = dict()
        self.ref_overlay_placeholder.object =\
                hv.NdOverlay(self.dictionary_references)\
                .opts(legend_muted = True,shared_axes = False,\
                hooks = [hook_full_black_black_with_legend],bgcolor = 'black')
        #self.tabs_references[0].pop(-1)
        #self.tabs_references[0].pop(0)
        self.param['area'].objects = ['None','default']
        self.area = 'None'
        #Deleting the model - the whole NLLS class
        #And starting again - a lot to be replaced
        self.dictionary_references = {'empty':self.default_curve_references}
        del self.NLLS
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
        #Disable analysis results retrieval
        self.button_analysis_run.disabled = True
        self.button_analysis_run.button_type = 'default'
        self.overlay_clust_bool = False
        self.button_overlay_clusters_active[0].button_type = 'default'
        self.button_overlay_clusters_active[0].disabled = True
    '''

    def _callback_fit_references(self,event):
        #Fits the references available and allows 
        self.button_fit_references.disabled = True
        self.button_fit_references.button_type = 'default'
        self.button_fit_ref_select_area.disabled = True
        if self.ref_fit_area == 'Selected Area':
            self.NLLS.create_model(name_area = self.area)
            self.NLLS.fit_reference(name_area = self.area)
            self.search_fit_order(self.area)
        elif self.ref_fit_area == '  All Areas  ':
            for ars in list(self.NLLS.models_components.keys()):
                self.NLLS.create_model(name_area = ars)
                self.NLLS.fit_reference(name_area = ars)
                self.search_fit_order(ars)
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
            ds_counts = xr.Dataset({'ElectronCounts':(['Eloss'],\
                self.NLLS.ref_spectra[el])}\
                ,coords = {'Eloss':self.NLLS.Eloss})
            counts_area = hv.Area(data = ds_counts)\
                .opts(yformatter=formatter,\
                selection_fill_alpha = 0.5,\
                nonselection_fill_alpha = 0.1,\
                fill_alpha = 0.25,\
                show_grid = True,\
                fill_color = self.colordict[el],\
                line_color = 'grey',\
                frame_height = 250,frame_width = 600,\
                bgcolor = 'black',hooks = [hook_full_black_black],\
                shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
                ylabel = 'Electron Counts [a.u.]')
            overall_fit = hv.Curve(data =\
                xr.Dataset({'ElectronCounts':(['Eloss'],\
                    self.NLLS.ref_results[el].best_fit)},\
                    coords = {'Eloss':self.NLLS.Eloss}))\
                .opts(color = 'r',\
                bgcolor = 'black',hooks = [hook_full_black_black],\
                shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
                ylabel = 'Electron Counts [a.u.]')
            self.dictionary_fitted_ref_overall[el] = counts_area*overall_fit
            #Components
            compos  = self.NLLS.ref_results[el].eval_components()
            NdOver_dict = dict()
            if len(compos) > 5:
                legd_col = True
            else: legd_col = False
            for comp in compos:
                ds_comp = xr.Dataset({'ElectronCounts':(['Eloss'],\
                compos[comp])},coords = {'Eloss':self.NLLS.Eloss})
                #Newly added
                lista_clav = comp.split('_')
                if 'cont' in lista_clav and 'L1' in lista_clav[0]:
                    clav_graph = '{}c'.format(lista_clav[0])
                else: clav_graph = lista_clav[0]
                
                NdOver_dict[clav_graph] = hv.Area(data = ds_comp)\
                    .opts(yformatter=formatter,\
                    shared_axes=False,\
                    selection_fill_alpha = 0.5,\
                    nonselection_fill_alpha = 0.1,\
                    show_grid = True,\
                    frame_height = 250,frame_width = 600,\
                    xlabel = 'Electron Energy Loss [eV]',\
                    ylabel = 'Electron Counts [a.u.]')
            
            self.dictionary_fitted_ref_compos[el] =\
            hv.Curve(data = ds_counts)\
                .opts(line_width = 2,line_color = 'lightgrey',\
                alpha = 0.75,\
                shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
                ylabel = 'Electron Counts [a.u.]')*\
            overall_fit*\
            hv.NdOverlay(NdOver_dict).opts(legend_muted=True,legend_cols = legd_col,\
                shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
                ylabel = 'Electron Counts [a.u.]')
        #Once created all these components and dictionaries, let's add the current
        #one selected to the display
        if (self.area != 'default') and ('_' in self.area):
            nombre = ' '.join(self.area.capitalize().split('_'))
        else:
            nombre = self.area

        self.mkdown_BestFit.object = '#### &nbsp;&nbsp;&nbsp;&nbsp;\
        Best fit for the reference spectra of the - **{}** - area'\
        .format(nombre)
        self.mkdown_BestFit.styles = {'color':'white'}
        self.best_fit_placeholder.object =\
            self.dictionary_fitted_ref_overall[self.area]\
            .opts(shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
            ylabel = 'Electron Counts [a.u.]')
        self.mkdown_Compos.object = '#### &nbsp;&nbsp;&nbsp;&nbsp;\
        Fitted individual components for the reference spectra of the **{}** area'\
        .format(nombre)
        self.mkdown_Compos.styles = {'color':'white'}
        self.compos_placeholder.object =\
            self.dictionary_fitted_ref_compos[self.area]\
            .opts(shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
            ylabel = 'Electron Counts [a.u.]',\
            hooks = [hook_full_black_black_with_legend])
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
        #Unlocking the saving button as soon as we may have a single dataset to be saved
        self.button_save_data.disabled = False
        
        
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
    def preparing_new_results_multifit(self):
        #in case actually doing something 
        areas = list(self.fitted_areas_list_last)
        for clust in areas:
            array_area = self.NLLS.ref_matrices[clust]
            tot_iter = array_area.sum(axis = (0,1))
            dimx,dimy = array_area.shape
            self.progress_bar_0[0].max = int(tot_iter)
            self.NLLS.models_modified[clust] = list()
            self.NLLS.parameters_modified[clust] = list()
            self.progress_preparing = 0
            for x_i in range(dimx):
                self.NLLS.models_modified[clust].append(list())
                self.NLLS.parameters_modified[clust].append(list())
                for y_i in range(dimy):
                    if self.NLLS.results[clust][x_i][y_i] == None:
                        self.NLLS.models_modified[clust][x_i].append(None)
                        self.NLLS.parameters_modified[clust][x_i].append(None)
                    else:
                        mod = cp.deepcopy(self.NLLS.results[clust][x_i][y_i].model)
                        pars = cp.deepcopy(self.NLLS.results[clust][x_i][y_i].params)
                        #model copied - now let's expand it and lock components
                        for newcomp in self.extra_added_components_multifit[clust]:
                            mod = mod + self.NLLS.extra_modified_model_components[clust][newcomp][0] 
                            #Each newcomponent added has a set of parameters that we have to add to the mix
                            for par in self.NLLS.extra_modified_model_components[clust][newcomp][1].keys():
                                val = self.NLLS.extra_modified_model_components[clust][newcomp][1][par].value
                                maxi = self.NLLS.extra_modified_model_components[clust][newcomp][1][par].max
                                mini = self.NLLS.extra_modified_model_components[clust][newcomp][1][par].min
                                varying = self.NLLS.extra_modified_model_components[clust][newcomp][1][par].vary
                                pars.add(par,value = val,max = maxi,min = mini,vary = varying)
                        #Locking dictionaries
                        if self.use_locking_dictionary:
                            for el in self.locking_dict[clust]:
                                for compo in self.locking_dict[clust][el]:
                                    for para in self.locking_dict[clust][el][compo]:
                                        clave = ''.join([el,compo,'_',para])
                                        pars[clave].vary =\
                                        not self.locking_dict[clust][el][compo][para]
                        self.NLLS.models_modified[clust][x_i].append(mod)
                        self.NLLS.parameters_modified[clust][x_i].append(pars)
                        self.progress_preparing +=1
            #Here we prepare add the extra components to the reference dictiorary down in NLLS
            #lista_new_compos = [el[:-1] for el in self.extra_added_components_multifit[clust]]
            #self.NLLS._add_toReference_extra_compos(clust,lista_new_compos)

    def multifit_modified(self):
        Eloss_x = self.ds.Eloss.data
        areas = list(self.fitted_areas_list_last)
        for clust in areas:
            self.button_new_multifit_button.name =\
                'Fitting Modified {}'.format(''.join(clust.split('_')).capitalize())
            array_area = self.NLLS.ref_matrices[clust]
            tot_iter = array_area.sum(axis = (0,1))
            dimx,dimy = array_area.shape
            self.progress_bar_1[0].max = int(tot_iter)
            self.NLLS.results_modified[clust] = list()
            self.progress_newModels = 0
            for x_i in range(dimx):
                self.NLLS.results_modified[clust].append(list())
                for y_i in range(dimy):
                    if self.NLLS.models_modified[clust][x_i][y_i] == None:
                        self.NLLS.results_modified[clust][x_i].append(None)
                    else:
                        mod = cp.deepcopy(self.NLLS.models_modified[clust][x_i][y_i])
                        pars = cp.deepcopy(self.NLLS.parameters_modified[clust][x_i][y_i])
                        #model copied - now let's expand it and lock components
                        data_y = self.ds.ElectronCount.data[x_i,y_i]
                        res = mod.fit(data = data_y,params = pars,x = Eloss_x)
                        self.progress_newModels +=1
                        self.NLLS.results_modified[clust][x_i].append(res)
    
    def multifit_2(self):
        lista = list(self.non_fitted_clusters_list)
        for name_area in lista:
            self.button_new_multifit_button.name =\
                'Fitting {}'.format(''.join(name_area.split('_')).capitalize())
            array_area = self.NLLS.ref_matrices[name_area]
            dimx,dimy = array_area.shape
            #The number of elements to be fitted for any particular reference, can be known
            #by the sum of the reference matrix - as it is a matrix of ones and zeros 
            tot_iter = array_area.sum(axis = (0,1))
            self.progress_multifitting_prev = 0
            self.progress_bar_2[0].max = int(tot_iter)
            self.NLLS.results[name_area] = list()
            #t0 = time.time()
            for i in range(dimx):
                paramet = self.NLLS.ref_results[name_area].params
                self.NLLS.results[name_area].append(list())
                for j in range(dimy):
                    if array_area[i,j] == 1:
                        #t00 = time.time()
                        y = self.NLLS.ds.sel(x = j, y = i).ElectronCount.data
                        res = self.NLLS.models[name_area]\
                            .fit(y,params = paramet, x = self.NLLS.Eloss)
                        self.progress_multifitting_prev +=1
                        self.NLLS.results[name_area][i].append(res)
                        #t01 = time.time()
                        '''
                        etc_tot = tot_iter * (t01-t00)
                        etc_comp = etc_tot - idx_etc*(t01-t00)
                        '''
                        paramet = res.params
                    else:
                        #In case of being in pixel outside the fitting range, append none.
                        self.NLLS.results[name_area][i].append(None)
            #t1 = time.time()
            #tot_time_area = round((t1-t0),2)
            self.NLLS._create_reference_components_1strun(name_area,'rerun')

    def _callback_multifit_rerun(self,event):
        self.button_new_multifit_button.disabled = True
        #prepare new elements?
        cond_prepare1 = self.fitted_areas_list_last != []
        cond_prepare2 = self.fitted_areas_list_last != None
        cond_prepare3 = self.extra_added_components_multifit != dict()
        cond_prepare4 = self.non_fitted_clusters_list != []
        cond_prepare5 = self.non_fitted_clusters_list != None
        if all([cond_prepare1,cond_prepare2,cond_prepare3]):
            self.button_new_multifit_button.name = 'Preparing modified components'
            self.button_new_multifit_button.button_type = 'warning'
            self.preparing_new_results_multifit()
            self.button_new_multifit_button.button_type = 'primary'
            self.multifit_modified()
            self.multifit_rerun = True
        else: pass
        if cond_prepare4 and cond_prepare5:
            self.button_new_multifit_button.button_type = 'danger'
            self.multifit_2()
        #Now we have to retrieve the information
        self.button_new_multifit_button.name = 'Preparing results'
        self.button_new_multifit_button.button_type = 'warning'
        # working here
        try:
            for newarea in list(self.fitted_areas_list_last):
                self.NLLS.results_final_modified[newarea] =\
                cp.deepcopy(self.NLLS.results_modified[newarea])
        except:
            #IN the case of not having a newlist configured - by not adding any component 
            pass
        for area in self.NLLS.results:
            if area not in list(self.fitted_areas_list_last):
                #since we may have added other regions
                self.NLLS.results_final_modified[area] =\
                cp.deepcopy(self.NLLS.results[area])
        #Now we have the new results matrix - so we can compare results or go to results analysis
        self.button_new_multifit_button.disabled = False
        self.button_new_multifit_button.name = 'MultiFit'
        self.button_new_multifit_button.button_type = 'success'
        self.button_analysis_rerun.disabled = False
        self.button_analysis_rerun.button_type = 'warning'
    
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
        #bar_colors = ['primary', 'secondary', 'success', 'info',\
        #'warning', 'danger', 'light', 'dark']
        #color_i = 0
        self.prog_bar[0].bar_color = 'success'
        self.time_matrices = np.zeros_like(self.NLLS.ref_matrices['default'])
        self.time_matrices[:] = np.nan
        #Pre_process
        for name_area in self.multifit_area:
            self.button_multifit.name = 'MultiFit on area - {} -'.format(name_area)
            self.prog = 0
            try: 
                array_area = self.NLLS.ref_matrices[name_area]
            except:
                array_area = np.zeros(self.NLLS.ds.ElectronCount.data.shape[:-1])
            #The number of elements to be fitted for any particular reference, can be known
            #by the sum of the reference matrix - as it is a matrix of ones and zeros 
            tot_iter = array_area.sum(axis = (0,1))
            #num_10per = int(tot_iter*0.1) #10% of total iterations-to update ETC
            self.prog_bar[0].max = int(tot_iter)
            #self.NLLS.results[name_area] = list()
            self.NLLS.results[name_area] =\
                [[None for _ in range(len(self.ds.x))] for _ in range(len(self.ds.y))]
            #Now...let's uncover where the indices are, so we don't run the whole loop all over again and again
            tup_indices = np.where(array_area == 1)
            #tup_indices = self.dictio_order_tuples[name_area]
            lista_inidices= [(id1,id2) for id1,id2 in zip(tup_indices[0],tup_indices[1])]
            #lista_time_pix = []
            paramet = self.NLLS.ref_results[name_area].params
            t0 = time.time()
            #idx_etc = 0
            #dictio_results = dict()
            for idxs in lista_inidices:
            #for idm in self.dictio_order_matrices[name_area]:
                t00 = time.time()
                y = self.NLLS.ds.ElectronCount.isel(x = idxs[1], y = idxs[0]).values
                res = self.NLLS.models[name_area]\
                    .fit(y,params = paramet, x = self.NLLS.Eloss)
                #paramet = res.params
                #dictio_results[idxs] = res
                self.NLLS.results[name_area][idxs[0]][idxs[1]] = res
                t01 = time.time()
                self.time_matrices[idxs[0],idxs[1]] = t01-t00
                #idx_etc +=1
                self.prog += 1    #The progress bar advances
                # If we activate this option...we start the next pixel form the previous solution 
                #paramet = res.params  
            t1 = time.time()
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
        self.button_analysis_run.disabled = False
        self.button_analysis_run.button_type = 'success'
        #Changes here
        self._callback_get_analysis_data(None)
        

    #####################################################################################
    #####################################################################################
    #Buttons in the analysis tab
    #####################################################################################
    def _callback_lock_all_comp(self,event):
        #This method allows a quick lock of the current cluster parameters
        #Locking all ELNES and continuum
        for elem in self.param['elements_re_run'].objects:
            for ssh in self.param['elnes_re_run'].objects:
                for parameter in self.param['lock_ELNES'].objects:
                    try:
                        #It may be that a certain area does not have a certain compo
                        self.locking_dict[self.fitted_areas_list3][elem]\
                        [ssh][parameter] = True
                    except: pass
            for conti in self.param['continuum_re_run'].objects:
                try:
                    self.locking_dict[self.fitted_areas_list3][elem]\
                    [conti]['cont_A'] = True
                except:
                    pass
        #To force the refresh of the current display
        self.lock_ELNES = ['center','amplitude','sigma']
        self.lock_continuum = True
        self.button_show_truth_table.disabled = False
        self.button_show_truth_table.button_type = 'success'
        self.button_show_truth_table.name = 'Update truth table'

    def _callback_unlock_all_comp(self,event):
        #This method allows a quick unlock of the current cluster parameters
        #Locking all ELNES and continuum
        for elem in self.param['elements_re_run'].objects:
            for ssh in self.param['elnes_re_run'].objects:
                for parameter in self.param['lock_ELNES'].objects:
                    try:
                        self.locking_dict[self.fitted_areas_list3][elem]\
                        [ssh][parameter] = False
                    except:
                        pass
            for conti in self.param['continuum_re_run'].objects:
                try:
                    self.locking_dict[self.fitted_areas_list3][elem]\
                    [conti]['cont_A'] = False
                except:
                    pass
        #To force the refresh of the current display
        self.lock_ELNES = []
        self.lock_continuum = False
        self.button_show_truth_table.disabled = False
        self.button_show_truth_table.button_type = 'success'
        self.button_show_truth_table.name = 'Update truth table'

    def _callaback_AddToNewModel(self,event):
        #Method to add to the new extra model fitting the components created and display the df
        try:
            self.extra_added_components_multifit[self.clusters_with_newcomps]
        except:
            #We prepare the dict to be used with the NLLS
            self.extra_added_components_multifit[self.clusters_with_newcomps] =\
                [comp+'_' for comp in self.added_list_compos]
        else:
            for compo in self.added_list_compos:
                if compo+'_' not in self.extra_added_components_multifit\
                [self.clusters_with_newcomps]:
                    self.extra_added_components_multifit[self.clusters_with_newcomps]\
                    .append(compo+'_')
                else:
                    pass
        #Now the display of this info
        dictio_for_df = dict()
        for clv in self.extra_added_components_multifit:
            dictio_for_df[clv] = ' '.join(self.extra_added_components_multifit[clv])
        df = pd.DataFrame(dictio_for_df,index=['Components added']).transpose()
        self.current_added_component = df
        self.data_frame_info.object = df
        #self.re_New_mod[1][2][0][4].pop(0)
        #self.re_New_mod[1][2][0][4].append(pn.pane.DataFrame(df,\
        #    width = 250))
        self.param['fitted_areas_list_last'].objects =\
            cp.deepcopy(list(self.extra_added_components_multifit.keys()))
        
    def _callaback_RemoveFromNewModel(self,event):
        #Method to remove the components from the dictionary controlling
        #the new components per cluster
        try:
            self.extra_added_components_multifit[self.clusters_with_newcomps]
        except:
            print('we are in return')
            return
        else:
            for comp in self.added_list_compos:
                if comp+'_' in self.extra_added_components_multifit[self.clusters_with_newcomps]:
                    self.extra_added_components_multifit[self.clusters_with_newcomps]\
                    .remove(comp+'_')
                else: pass
            print('the dictio is now',self.extra_added_components_multifit)
            #In case of having lost the entirity of a cluster keys:
            if self.extra_added_components_multifit[self.clusters_with_newcomps] == []:
                self.extra_added_components_multifit.pop(self.clusters_with_newcomps)
            else: pass
            print('the dictio is now2',self.extra_added_components_multifit)
            #Now the tricky part - the df again
            dictio_for_df = dict()
            for clv in self.extra_added_components_multifit:
                dictio_for_df[clv] = ' '.join(self.extra_added_components_multifit[clv])
            df = pd.DataFrame(dictio_for_df,index=['Components added']).transpose()
            self.current_added_component = df
            self.re_New_mod[1][2][0][4].pop(0)
            self.re_New_mod[1][2][0][4].append(pn.pane.DataFrame\
                (df,width = 225))
            #Setting the possible options for the multifit
            self.param['fitted_areas_list_last'].objects =\
            cp.deepcopy(list(self.extra_added_components_multifit.keys()))
            
    def _callback_show_prev_compos(self,event):
        #Method to show the previous spectra non fitted references
        try:
            #If it doesn't exists, better do nothing
            compos = self.NLLS.ref_results[self.non_fitted_clusters].eval_components()
        except:
            return
        else:
            chain = str(self.non_fitted_clusters)
            clave_ejey = ' '.join(chain.split('_')).capitalize()
            Eaxis = self.NLLS.Eloss
            raw = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
                ('Eloss',self.NLLS.ref_spectra[self.non_fitted_clusters])},\
                coords = {'Eloss':Eaxis})
            figure = hv.Area(raw)\
                .opts(frame_width = 650,line_alpha = 0.5,line_color = 'black',\
                yformatter=formatter,fill_alpha = 0.20,\
                fill_color = self.colordict[self.non_fitted_clusters])
            for comp in compos:
                comp_patch = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
                ('Eloss',compos[comp])},\
                coords = {'Eloss':Eaxis})
                figure*= hv.Area(comp_patch,label = comp)\
                .opts(alpha = 0.75,yformatter=formatter)
            figure.opts(frame_height = 225,\
            title = 'Graphical display of non-fitted previous components')
            #Now the part when we add this new figure
            self.re_New_mod[1][2][1][1].pop(0)
            self.re_New_mod[1][2][1][1].append(figure)

    def _callback_show_prev_bestfit(self,event):
        #Method to show the previous spectra non fitted references
        try:
            #If it doesn't exists, better do nothing
            mod = self.NLLS.ref_results[self.non_fitted_clusters]
        except:
            return
        else:
            chain = str(self.non_fitted_clusters)
            clave_ejey = ' '.join(chain.split('_')).capitalize()
            Eaxis = self.NLLS.Eloss
            raw = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
                ('Eloss',self.NLLS.ref_spectra[self.non_fitted_clusters])},\
                coords = {'Eloss':Eaxis})
            best_fit = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
                ('Eloss',mod.best_fit)},\
                coords = {'Eloss':Eaxis})
            figure = hv.Area(raw,label='Raw data {}'.format(clave_ejey))\
                .opts(frame_width = 650,line_alpha = 0.5,line_color = 'black',\
                yformatter=formatter,fill_alpha = 0.20,\
                fill_color = self.colordict[self.non_fitted_clusters])\
            *hv.Curve(best_fit,label='Best-Fit')\
                .opts(alpha = 0.75,color = 'limegreen',yformatter=formatter)
            figure.opts(frame_height = 225,\
            title = 'Graphical display of non-fitted previous components')
            #Now the part when we add this new figure
            self.re_New_mod[1][2][1][1].pop(0)
            self.re_New_mod[1][2][1][1].append(figure)
            
    def _callback_Refresh_selection_show(self,event):
        #The first time is called - this hover tool is created
        TT2 = [("Cluster","{}".format(' '.join("@cluster".split('_')).capitalize())),\
            ("Component-Name","@componame"),\
            ("Center","{} +- {} eV".format("@center","@centerdiff")),\
            ("Sigma","@sigma"),\
            ("Sigma-MaxMin","max : {} | min : {}".format("@sigmamax","@sigmamin"))]
        self.hover_tip2 = HoverTool(tooltips=TT2)
        if self.clusters_with_newcomps == 'NoCluster':
            #safety in case of not having any cluster in selection...
            return
        #Now the actual code for the case of having a cluster selected
        #First-let's build teh data and the graphs
        clave_ejey = ' '.join(self.clusters_with_newcomps.split('_')).capitalize()
        dataBF  = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
            ('Eloss',self.NLLS.ref_results[self.clusters_with_newcomps].best_fit)},\
            coords={'Eloss':self.NLLS.Eloss})
        dataRaw = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
            ('Eloss',self.NLLS.ref_spectra[self.clusters_with_newcomps])},\
            coords={'Eloss':self.NLLS.Eloss})
        figure = hv.Area(dataRaw,label='Reference Data')\
            .opts(frame_width = 650,line_alpha = 1,line_color = 'black',yformatter=formatter,\
            fill_alpha = 0.30,fill_color = self.colordict[self.clusters_with_newcomps])\
        * hv.Curve(dataBF,label='Best-Fit')\
            .opts(alpha = 0.75,color = 'limegreen',yformatter=formatter)
        #Now the new components selected
        if self.added_list_compos != None: #safety measure
            for newcomp in self.added_list_compos:
                if newcomp != 'NoNewComponents':
                    cent_mat = np.empty_like(self.NLLS.Eloss)
                    sig_mat = np.empty_like(self.NLLS.Eloss)
                    sig_max  = np.empty_like(self.NLLS.Eloss)
                    sig_min = np.empty_like(self.NLLS.Eloss)
                    cent_dif = np.empty_like(self.NLLS.Eloss)
                    data_eval = self.NLLS.extra_modified_model_components\
                        [self.clusters_with_newcomps][newcomp+'_'][0]\
                        .eval(x = self.NLLS.Eloss,params =\
                        self.NLLS.extra_modified_model_components\
                            [self.clusters_with_newcomps][newcomp+'_'][1])
                    
                    cent_mat[:] = round(self.NLLS.extra_modified_model_components\
                        [self.clusters_with_newcomps][newcomp+'_'][1][newcomp+'_center'].value,2)
                    sig_mat[:] = round(self.NLLS.extra_modified_model_components\
                        [self.clusters_with_newcomps][newcomp+'_'][1][newcomp+'_sigma'].value,3)
                    sig_max[:] = round(self.NLLS.extra_modified_model_components\
                        [self.clusters_with_newcomps][newcomp+'_'][1][newcomp+'_sigma'].max,3)
                    sig_min[:] = round(self.NLLS.extra_modified_model_components\
                        [self.clusters_with_newcomps][newcomp+'_'][1][newcomp+'_sigma'].min,3)
                    cent_dif[:] = cent_mat - round(self.NLLS.extra_modified_model_components\
                        [self.clusters_with_newcomps][newcomp+'_'][1][newcomp+'_center'].min,2)
                    data_Set_compo = xr.Dataset({'ElectronCounts {}'.format(clave_ejey):\
                        ('Eloss',data_eval),\
                        'cluster':('Eloss',[self.clusters_with_newcomps for i in range(self.NLLS.Eloss.size)]),\
                        'componame':('Eloss',[newcomp for i in range(self.NLLS.Eloss.size)]),\
                        'center':('Eloss',cent_mat),\
                        'sigma':('Eloss',sig_mat),\
                        'centerdiff':('Eloss',cent_dif),\
                        'sigmamin':('Eloss',sig_min),\
                        'sigmamax':('Eloss',sig_max)},\
                        coords={'Eloss':self.NLLS.Eloss})
                    figure *= hv.Area(data_Set_compo['ElectronCounts {}'.format(clave_ejey)],\
                        label=newcomp).opts(alpha = 0.75,yformatter=formatter)
                    figure *= hv.Curve(data_Set_compo,\
                        label=newcomp).opts(alpha = 0.75,tools=[self.hover_tip2],\
                        yformatter=formatter)
                else: pass
        #Now the part when the graph is actually displayed
        figure.opts(frame_height = 225,title = 'Graphical display of new components')
        self.re_New_mod[1][2][1][0].pop(0)
        self.re_New_mod[1][2][1][0].append(figure)

    def _callback_create_extra_component_rerun(self,event):
        #This method calls the NLLS method that creates components for a possible new rerun
        #Safeties -  empty stuff that makes this mathod do nothing
        if self.new_compo_name == None or self.new_compo_name == '':
            return
        if self.fitted_areas_list == [] or self.fitted_areas_list == None:
            return
        previous_lista = list(self.dictio_newcomps_area.keys())
        compo_name_display = '-'.join([self.new_compo_elements,self.new_compo_name,'New'])
        possible_previous_compo = '-'.join([self.new_compo_elements,self.new_compo_name])
        for area in self.fitted_areas_list:
            if (area,possible_previous_compo) in self.G.edges:
                #Already exist this component with this conection
                pass
            else:
                if compo_name_display not in previous_lista: 
                    self.dictio_newcomps_area[compo_name_display]=[area]
                else:
                    self.dictio_newcomps_area[compo_name_display].append(area)
                #Now the creation of the actual component
                self.NLLS.create_extra_component_second_model(self.new_compo_elements,\
                    self.new_compo_name,self.new_compo_energy,\
                    area,self.new_compo_func,self.new_compo_flex)
                self.NLLS._add_toReference_extra_compos(area,\
                    self.new_compo_elements,self.new_compo_name)
                #updating the conenctivity G graph
                self._update_connectivity_graph(area)
        #This has effectively created a dictionary with models and parameters stored
        #Now we change the graphs and allow a refresh in the display
        self.tree = hvnx.draw(self.G,pos=self.positions_tree,\
            node_color = 'color',edge_color = 'grey',\
            node_size = hv.dim('size')*2,node_alpha = 'alpha',node_marker = 'node_shape',\
            edge_width=hv.dim('weight')*2.5)\
            .opts(frame_height=450,frame_width=850,edge_color = 'weight',edge_cmap='jet',\
                edge_hover_line_color='lime',node_selection_line_color='white',\
                node_selection_alpha = 1,node_fill_color = 'white',\
                node_selection_fill_color = 'color',node_line_width = 4,\
                node_nonselection_fill_color = 'white',\
                node_line_color='color',tools= [self.hover_tip,'tap'],\
                toolbar = 'left',shared_axes = False)
        new_positions = nx.spring_layout(self.G,iterations=150,weight='weight')
        self.spring_graph = hvnx.draw(self.G,pos = new_positions,\
            node_size = hv.dim('size')*2,node_alpha = 'alpha',node_marker = 'node_shape')\
            .opts(frame_height=450,frame_width=850,edge_color = 'weight',edge_cmap='jet',\
                edge_hover_line_color='lime',node_selection_line_color='white',\
                node_selection_alpha = 1,node_fill_color = 'white',\
                node_selection_fill_color = 'color',node_line_width = 4,\
                node_nonselection_fill_color = 'white',\
                node_line_color='color',tools= [self.hover_tip,'tap'],\
                toolbar = 'left',shared_axes = False)
        st_shell  = [clust for clust in self.NLLS.ref_results.keys()]
        nd_shell  = [node for node in list(self.G.nodes.keys()) if ('New' not in node and node not in st_shell)]
        rth_shell = [node for node in list(self.G.nodes.keys()) if 'New' in node]
        self.shell_structure = [st_shell,nd_shell,rth_shell]
        self.radial_graph = hvnx.draw_shell(self.G,nlist = self.shell_structure,\
            node_color = 'color',node_marker = 'node_shape',edge_color = 'grey',\
            node_size = hv.dim('size')*1.5,\
            node_alpha = 'alpha',edge_width=hv.dim('weight')*5)\
            .opts(frame_height=450,frame_width=850,edge_color = 'weight',edge_cmap='jet',\
                edge_hover_line_color='lime',node_selection_line_color='white',\
                node_selection_alpha = 1,node_fill_color = 'white',\
                node_selection_fill_color = 'color',node_line_width = 4,\
                node_nonselection_fill_color = 'white',\
                node_line_color='color',tools= [self.hover_tip,'tap'],\
                toolbar = 'left',shared_axes = False)
        #Allowing the refresh button to be clicked
        self.button_show_tree.disabled = False
        self.button_show_tree.name = 'Refresh component display'
        self.button_show_tree.button_type = 'primary'
        self.clusters_additions[0].disabled = False
        self.clusters_additions[0].button_type = 'success'
        self.components_additions[0].disabled = False
        self.components_additions[0].button_type = 'warning'
        #We also have to update the available components to be added to the model
        list_clusters_modifications = self.param['clusters_with_newcomps'].objects
        if all([el == 'NoCluster' for el in list_clusters_modifications]):
            #If no cluster has been added yet to the list - eliminates the nocluster option
            lista_clusters_toadd = [clust for clust in self.fitted_areas_list if\
                (clust,possible_previous_compo) not in self.G.edges]
            #We do not want the already stablished pairs -cluster compos in the mix
            #Another safety measure
            if lista_clusters_toadd == []:
                lista_clusters_toadd = ['NoCluster']
            self.param['clusters_with_newcomps'].objects = lista_clusters_toadd
        else:
            #Some cluster is already in the list
            for clust in self.fitted_areas_list:
                if clust not in list_clusters_modifications \
                and (clust,possible_previous_compo) not in self.G.edges:
                    list_clusters_modifications.append(clust)
                    self.clusters_additions[0].options[clust] = clust
                else: pass
            self.param['clusters_with_newcomps'].objects = list_clusters_modifications
        #safety measure - get to the list 1st element
        self.clusters_with_newcomps = self.param['clusters_with_newcomps'].objects[0]
        #If we only have one component - force the refresh of the names available
        if len(self.param['clusters_with_newcomps'].objects) <= 1 \
        and self.clusters_with_newcomps != 'NoCluster':
            self.param['added_list_compos'].objects =\
                [na[:-1] for na in list(self.NLLS.extra_modified_model_components\
                [self.clusters_with_newcomps].keys())]
            self.added_list_compos = []  #It is a list selector - defaulting to nothing
        else: pass #The other case is managed by an interactive @param method
        self.button_show_new_comps_selected.disabled = False
        self.button_show_new_comps_selected.button_type = 'primary'
        self.button_cluster_to_newMod.disabled = False
        self.button_cluster_to_newMod.button_type = 'success'
        self.button_cluster_to_newMod_erase.disabled = False
        self.button_cluster_to_newMod_erase.button_type = 'danger'
        self.button_show_prev_comps_selected.disabled = False
        self.button_show_prev_comps_selected.button_type = 'primary'
        self.button_show_prev_bestfit_selected.disabled = False
        self.button_show_prev_bestfit_selected.button_type = 'primary'

    def _update_connectivity_graph(self,area_name):
        #updates the connectivity graphs - to be able to add component to the graph
        #First we check if we are going to add an already existing component
        siz = 400
        alph = 0.25
        current_nodes = cp.deepcopy(list(self.G.nodes.keys()))
        clave_elnes = '-'.join([self.new_compo_elements,self.new_compo_name,'New'])
        #Truth conditions
        condition_1 =\
            '-'.join([self.new_compo_elements,self.new_compo_name]) in self.initial_nodes
        condition_2 =\
            clave_elnes in current_nodes
        #Now the decision tree
        if condition_1 and condition_2:
            #Node already exists in initial graph and in new selection
            self.G.add_edge(area_name,clave_elnes,alpha = alph, weight = 0.25)
        elif condition_1 and not condition_2:
            #Create the new node, and connect it with the initial one and the area
            self.G.add_node(clave_elnes,type_node = 'New-ELNES-Component',\
                state = 'Non-fitted',name = clave_elnes,size = siz,color = 'black',\
                alpha = alph,node_shape = 'circle_cross',node_line_color = 'black',\
                node_line_width = 2)
            self.G.add_edge(area_name,clave_elnes,alpha = alph, weight = 0.25)
            self.G.add_edge(''.join(clave_elnes.split('-New')),clave_elnes,alpha = alph, weight = 0.15)
            #Added position and the position marker advances
            self.positions_tree[clave_elnes] =  (self.new_elnes_idx,0)
            self.new_elnes_idx += 1
        elif not condition_1 and not condition_2:
            #When it isn't in the initial bundle or the current one
            self.G.add_node(clave_elnes,type_node = 'New-ELNES-Component',\
                state = 'Non-fitted',name = clave_elnes,size = siz,color = 'black',\
                alpha = alph,node_shape = 'circle_cross',node_line_color = 'black',\
                node_line_width = 2)
            self.G.add_edge(area_name,clave_elnes,alpha = alph, weight = 0.25)
            #Added position and the position marker advances
            self.positions_tree[clave_elnes] =  (self.new_elnes_idx,0)
            self.new_elnes_idx += 1
        else:
            self.G.add_edge(area_name,clave_elnes,alpha = alph, weight = 0.25)
    
    def _get_list_areas_first(self):
        self.areas_being_fitted = [area for area in self.NLLS.results]
        self.first_fit = False

    def _get_list_areas_rerun(self):
        self.areas_being_fitted_re = [area for area in self.NLLS.results_final_modified]
        self.first_fit_rerun = False
    
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
            self.NLLS.get_best_fit_components(name_area,target_results,type_run)
            self.NLLS.get_values_and_stderr_components_per_area(name_area,target_results,type_run)
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
            self.NLLS.get_RCS_maps(name_area,target_results,type_run)
            self.NLLS.get_residual_signals(name_area,target_results,type_run)
            self.NLLS.get_best_fit_signals(name_area,target_results,type_run)
            #let's get also the matrix for the mask overlaying 
            mat = cp.deepcopy(self.NLLS.ref_matrices[name_area])
            mat[mat == 0] = np.NaN
            mat_ds = xr.Dataset({'mask_cluster':(['y','x'],mat)},\
                coords = {'x':xs_j,'y':ys_i})
            #masking maps
            dictio_info_image[name_area] = (['y','x'],mat)
            self.masks_per_area[name_area] = hv.Image(mat_ds)\
                .opts(aspect = 'equal',invert_yaxis=True,frame_width=225,\
                xlim = self.xlims,ylim = self.ylims,\
                xaxis=None, yaxis=None,show_title = False,\
                cmap = ['black',self.colordict[name_area]],alpha = 0.25)
            #Now the total_reduce_chi_sq matrix - later to be implemented as a xr.Dataset
            if type_run == 'multi':
                ref_mat = self.NLLS.red_chi_sqr[name_area].ReducedXiSq.values
                ref_res_mat = self.NLLS.residuals[name_area].Residuals.values
                ref_best_fit = self.NLLS.best_fits[name_area].Best_fit.values
            elif type_run == 'rerun':
                ref_mat = self.NLLS.red_chi_sqr_re[name_area].ReducedXiSq.values
                ref_res_mat = self.NLLS.residuals_re[name_area].Residuals.values
                ref_best_fit = self.NLLS.best_fits_re[name_area].Best_fit.values
            total_red_chi[np.isnan(ref_mat) == False] =\
                ref_mat[np.isnan(ref_mat) == False]
            total_resid[np.isnan(ref_res_mat) == False] =\
                ref_res_mat[np.isnan(ref_res_mat) == False]
            total_best_fits[np.isnan(ref_best_fit) == False]=\
                ref_best_fit[np.isnan(ref_best_fit) == False]
            if type_run == 'multi':
                for el in self.NLLS.component_eval[name_area]:
                    ref_compo = self.NLLS.component_eval[name_area][el].values
                    total_compo_eval[el[:-1]][np.isnan(ref_compo) == False] =\
                        ref_compo[np.isnan(ref_compo) == False]
                for par in self.NLLS.param_errRel[name_area]:
                    ref_err = self.NLLS.param_errRel[name_area][par].values
                    total_params_eval[par][np.isnan(ref_err) == False] =\
                        ref_err[np.isnan(ref_err) == False]
            elif type_run == 'rerun':
                for el in self.NLLS.component_eval_re[name_area]:
                    ref_compo = self.NLLS.component_eval_re[name_area][el].values
                    total_compo_eval[el[:-1]][np.isnan(ref_compo) == False] =\
                        ref_compo[np.isnan(ref_compo) == False]
                for par in self.NLLS.param_errRel_re[name_area]:
                    ref_err = self.NLLS.param_errRel_re[name_area][par].values
                    total_params_eval[par][np.isnan(ref_err) == False] =\
                        ref_err[np.isnan(ref_err) == False]
        #The default image of the SI area
        dictio_info_image['SI'] = (['y','x'],self.ds.ElectronCount.values.sum(-1))
        self.total_dataset_mask = xr.Dataset(dictio_info_image,\
            coords = {'x':self.ds.x.values,'y':self.ds.y.values})
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

    def _visual_changes_analysis(self,areas_list):
        #Here we separate the two functions, so we can call it again later
        #Let's update the parameters for teh info display and options selection at analysis
        self.param['fitted_areas_list'].objects =\
        [name_area for name_area in areas_list] #used t be self.multifit_area param
        self.param['element_analysis'].objects = self.param['model_element'].objects
        self.param['fitted_areas_list2'].objects =\
        [name_area for name_area in areas_list] #used t be self.multifit_area param
        self.fitted_areas_list2 =\
            self.param['fitted_areas_list2'].objects[0]
        self.param['fitted_areas_list3'].objects =\
        [name_area for name_area in areas_list] #used t be self.multifit_area param
        #self.fitted_areas_list3 =\
        #    self.param['fitted_areas_list3'].objects[0]
        self.button_change_info_display[0].disabled = False
        self.button_change_info_display[0].button_type = 'success'
        #Now some changes in the analysis info display
        self.full_time_text = 'Total fitting elapsed time : {} s'\
            .format(round(self.total_time_accumulated,1))
        #Let's get the median
        mat = self.total_res_analysis.ReducedChiSq.values
        self.full_median_text = 'Median Reduced \u03A7\u00b2 : {} '\
            .format(round(np.median(mat[np.isnan(mat) == False]),2))
        #Now the image displayed in the info area from the dictio_info_image dict of the loop
        lista = []
        for el in self.total_dataset_mask:
            if el != 'SI':
                lista.append(hv.Image(self.total_dataset_mask[el])\
                    .opts(xaxis = None,yaxis = None,border = 0,hooks=[hook_full_black],\
                    invert_yaxis = True,aspect = 'equal',frame_height=200,\
                    xlim = self.xlims,ylim = self.ylims,\
                    cmap = ['white',self.colordict[el]],alpha = 0.25))
        im0 = hv.Image(self.total_dataset_mask['SI'])\
            .opts(xaxis = None,yaxis = None,border = 0,hooks=[hook_full_black],\
            xlim = self.xlims,ylim = self.ylims,\
            invert_yaxis = True,aspect = 'equal',frame_height=200,\
            cmap = 'greys_r',alpha = 1)\
        *hv.Overlay(lista)
        self.init_info_fill_image = im0
        self.lateral.pop(-1)
        self.lateral.append(self.init_info_fill_image)
        self.lateral[-1].margin = (20,70)
        #Now we have to get the residual plotting panels
        self.res_plot = residual_plotting(self.total_res_analysis)
        self.tot_RCS_hmap,*lista_dinamic_maps = self.res_plot.create_panel()
        #Now the actual panel structure and it's placement in the tab section
        self.button_change_styling_RCS.disabled = False
        self.button_change_styling_RCS.button_type = 'primary'
        self.button_overlay_cluster_RCS[0].disabled = False
        self.button_overlay_cluster_RCS[0].button_type = 'danger'
        row_panel_interactive = pn.Row(self.tot_RCS_hmap,\
            hv.Overlay(lista_dinamic_maps).collate().opts(toolbar = 'right'))
        self.analysis_tabs[0].pop(-1)
        self.analysis_tabs[0].append(row_panel_interactive)
        self.analysis_tabs[0][-1].margin = (25,5)
        self.analysis_tabs[0][-1][0].margin = (5,25)
        #Now the part when we get activate the functionality in the component analysis tab
        self.param['element_analysis'].objects = list(self.NLLS.fitting_elements.keys())
        self.element_analysis = self.param['element_analysis'].objects[0]
        for el in self.element_toggle:
            el.disabled = False
        for i,el in enumerate(['danger','default','success']):
            self.element_toggle[i].button_type = el
        self.analysis_tabs[1][1][0].append(\
        pn.GridBox(*[pn.widgets.StaticText(value = ' '.join(el.split('_')).capitalize(),\
        styles={'color':self.colordict[el]})\
        for el in self.param['fitted_areas_list'].objects],\
        ncols = 3))
        self.analysis_tabs[1][1][0][-1].margin = (5,0,5,15)
        self.button_activate_rerun.disabled = False
        self.button_activate_rerun.button_type = 'success'
        #self._get_connectivity_graph()
        #self.button_new_model_creator.disabled = False
        #self.button_new_model_creator.button_type = 'warning'
        #self._create_locking_dict()

    def _callback_get_analysis_data(self,event):
        #This method gets the results of multifit and prepare the visualizations
        #Initialize the dictionaries fot visual objects
        # working here
        if self.first_fit:
            self._get_list_areas_first()
            self.panel_new_mod  = self._new_model_panel_constructor()
        else: pass
        self._analysis_calculations(self.areas_being_fitted,self.NLLS.results,type_run = 'multi')
        if not self.first_fit_rerun:
            #In case of having done a rerun already ... reset the tab
            self.analysis_tabs.append(self.show_Error_param_pane)
            self.button_analysis_rerun.disabled = False
            self.button_analysis_rerun.button_type = 'warning'
        else: pass
        self._visual_changes_analysis(self.areas_being_fitted)
        self.button_analysis_run.disabled = True
        self.button_analysis_run.button_type = 'default'
        
        
        
    
    def _callback_get_analysis_rerun_data(self,event):
        if self.first_fit_rerun:
            self._get_list_areas_rerun()
        else: pass
        self._analysis_calculations(self.areas_being_fitted_re,\
            self.NLLS.results_final_modified,type_run = 'rerun')
        self._visual_changes_analysis(self.areas_being_fitted_re)
        #Now we need to visually deny access to the error analysis tool
        self.analysis_tabs.pop(-1)
        #We enable the previous button to be clicked
        self.button_analysis_run.disabled = False
        self.button_analysis_run.button_type = 'success'
        self.button_analysis_rerun.disabled = True
        self.button_analysis_rerun.button_type = 'default'


    def _get_connectivity_graph(self):
        #This method takes care of getting the connectivity graph after multifit
        areas_fitted = cp.deepcopy(self.param['fitted_areas_list3'].objects)
        areas_fitted.sort()
        areas_nonfitted = [ar for ar in list(self.NLLS.models_components.keys()) if ar not in areas_fitted]
        self.G = nx.Graph()
        self.positions_tree = dict()       #- for the positions in the tree representation
        node_list_elnes = list()
        node_list_conti = list()
        count_elnes = 0
        count_cont = 0
        #Add elnes
        for i,area in enumerate(areas_fitted):
            siz = 400
            alph = 1
            clave_nombre = ' '.join(area.split('_')).capitalize()
            self.G.add_node(area,type_node = 'SI-Area',name = clave_nombre,size = siz*2,\
                state = 'fitted',color = self.colordict[area],alpha = alph,\
                node_shape = 'square')
            self.positions_tree[area] = (i,1)
            for elem in self.NLLS.models_components[area]:
                for elnes in self.NLLS.models_components[area][elem]['ELNES']:
                    clave_elnes = '-'.join([elem,elnes])
                    if clave_elnes not in node_list_elnes:
                        node_list_elnes.append(clave_elnes)
                        self.G.add_node(clave_elnes,type_node = 'ELNES-Component',\
                            name=clave_elnes,state = 'fitted',size = siz,color = 'black',\
                            alpha = alph,node_shape = 'circle',node_line_color = 'black',\
                            node_line_width = 2)
                        self.positions_tree[clave_elnes] = (count_elnes,0.5)
                        count_elnes+=1
                    self.G.add_edge(area,clave_elnes,alpha = 1,weight = 0.75)
        #Add continuum
        for i,area in enumerate(areas_fitted):
            for elem in self.NLLS.models_components[area]:
                for cont in self.NLLS.models_components[area][elem]['continuum']:
                    clave_cont = '-'.join([elem,cont])
                    if clave_cont not in node_list_conti:
                        node_list_conti.append(clave_cont)
                        self.G.add_node(clave_cont,type_node = 'Continuum-Component',\
                            name=clave_cont,state = 'fitted',size = siz,color = 'grey',\
                            alpha = 1,node_shape = 'hex',node_line_color = 'black')
                        self.positions_tree[clave_cont] = ((count_elnes)*1.5 + count_cont  ,0.5)
                        count_cont+=1
                    self.G.add_edge(area,clave_cont,alpha = 1,weight = 0.75)
        #Non fitted areas
        #Elnes
        for i,area in enumerate(areas_nonfitted):
            siz = 400
            alph = 0.25
            clave_nombre = ' '.join(area.split('_')).capitalize()
            self.G.add_node(area,type_node = 'SI-Area',name = clave_nombre,\
                state = 'Non-fitted',size = siz*2,color = self.colordict[area],\
                alpha = alph,node_shape = 'square_x')
            self.positions_tree[area] = (i + len(areas_fitted),1)
            for elem in self.NLLS.models_components[area]:
                for elnes in self.NLLS.models_components[area][elem]['ELNES']:
                    clave_elnes = '-'.join([elem,elnes])
                    if clave_elnes not in node_list_elnes:
                        node_list_elnes.append(clave_elnes)
                        self.G.add_node(clave_elnes,type_node = 'ELNES-Component',\
                            state = 'Non-fitted',name = clave_elnes,size = siz,\
                            color = 'black',\
                            alpha = alph,node_shape = 'circle_cross',node_line_color = 'black',\
                            node_line_width = 2)
                        self.positions_tree[clave_elnes] = (count_elnes,0.5)
                        count_elnes+=1
                    self.G.add_edge(area,clave_elnes,alpha = alph,weight = 0.5)
        #Add continuum
        for i,area in enumerate(areas_nonfitted):
            for elem in self.NLLS.models_components[area]:
                for cont in self.NLLS.models_components[area][elem]['continuum']:
                    clave_cont = '-'.join([elem,cont])
                    if clave_cont not in node_list_conti:
                        node_list_conti.append(clave_cont)
                        self.G.add_node(clave_cont,type_node = 'Continuum-Component',\
                            state = 'Non-fitted',name = clave_cont,\
                            size = siz,color = 'grey',alpha = 1,\
                            node_shape = 'hex',node_line_color = 'black')
                        self.positions_tree[clave_cont] = ((count_elnes)*1.5 + count_cont  ,0.5)
                        count_cont+=1
                    self.G.add_edge(area,clave_cont,alpha = alph,weight = 0.5)
        #Now the actual representation
        #The hover tool
        TT = [("Node-Name","@name"),("Node-Type","@type_node"),("Fitting-state","@state")]
        self.hover_tip = HoverTool(tooltips=TT)
        self.tree = hvnx.draw(self.G,pos=self.positions_tree,\
            node_color = 'color',edge_color = 'grey',\
            node_size = hv.dim('size')*2,node_alpha = 'alpha',node_marker = 'node_shape',\
            edge_width=hv.dim('weight')*2.5)\
            .opts(frame_height=450,frame_width=850,edge_color = 'weight',edge_cmap='jet',\
                edge_hover_line_color='lime',node_selection_line_color='white',\
                node_selection_alpha = 1,node_fill_color = 'white',\
                node_selection_fill_color = 'color',node_line_width = 4,\
                node_nonselection_fill_color = 'white',\
                node_line_color='color',tools= [self.hover_tip,'tap'],\
                toolbar = 'left',shared_axes = False)
        pos2 = nx.spring_layout(self.G,iterations=150,weight='weight')
        self.spring_graph = hvnx.draw(self.G,pos = pos2,\
            node_size = hv.dim('size')*2,node_alpha = 'alpha',node_marker = 'node_shape')\
            .opts(frame_height=450,frame_width=850,edge_color = 'weight',edge_cmap='jet',\
                edge_hover_line_color='lime',node_selection_line_color='white',\
                node_selection_alpha = 1,node_fill_color = 'white',\
                node_selection_fill_color = 'color',node_line_width = 4,\
                node_nonselection_fill_color = 'white',\
                node_line_color='color',tools= [self.hover_tip,'tap'],\
                toolbar = 'left',shared_axes = False)
        
        st_shell = [clust for clust in self.NLLS.ref_results.keys()]
        nd_shell = [node for node in list(self.G.nodes.keys()) if  node not in st_shell]
        self.shell_structure = [st_shell,nd_shell]
        self.radial_graph = hvnx.draw_shell(self.G,nlist = self.shell_structure,\
            node_color = 'color',node_marker = 'node_shape',edge_color = 'grey',\
            node_size = hv.dim('size')*1.5,\
            node_alpha = 'alpha',edge_width=hv.dim('weight')*5)\
            .opts(frame_height=450,frame_width=850,edge_color = 'weight',edge_cmap='jet',\
                edge_hover_line_color='lime',node_selection_line_color='white',\
                node_selection_alpha = 1,node_fill_color = 'white',\
                node_selection_fill_color = 'color',node_line_width = 4,\
                node_nonselection_fill_color = 'white',\
                node_line_color='color',tools= [self.hover_tip,'tap'],\
                toolbar = 'left',shared_axes = False)
        #Getting the default initial nodes so we can expand on them later on when addding components
        self.initial_nodes = cp.deepcopy(list(self.G.nodes.keys()))
        self.new_elnes_idx = 0.5

    def _create_locking_dict(self):
        #This method creates the initial locking dict, after the 1st multifit run
        #Let's populate the dictionary of paramter variations
        for area in self.param['fitted_areas_list3'].objects:
            self.locking_dict[area] = dict()
            for elem in self.NLLS.models_components[area].keys():
                self.locking_dict[area][elem] = dict()
                #We always have continuum component of the actual element fitted
                lista = list(self.NLLS.models_components[area][elem]['continuum'].keys())
                for conti in lista:
                    #There should be only one, but just in case, a loop is called here
                    #A True value indicates that the parameter can be varied - default
                    key_to_cont = '_'.join(['cont','A'])
                    self.locking_dict[area][elem][conti] = {key_to_cont : False}
                #Let's try, so we do not encounter keyerrors
                try:
                    lista2 =\
                    list(self.NLLS.models_components[area][elem]['ELNES'].keys())
                except:
                    pass
                else:
                    for ssh in lista2: 
                        #A True value indicates that the parameter can be varied - default
                        self.locking_dict[area][elem][ssh] =\
                        {'center':False,'amplitude':False,'sigma':False}
        #NOw let's create the initial figure for the locking ticks
    def _callback_update_truth_table(self,event):
        #Building the truthtable
        #If no components are selected ... show nothing - do nothing
        if self.fitted_areas_list == [] or self.fitted_areas_list == None:
            #safety measure - doing nothing
            return
        self.button_show_truth_table.disabled = True
        self.button_show_truth_table.button_type = 'danger'
        self.button_show_truth_table.name = 'Updating truth table'
        list_heatmaps = []
        #The fitted areas are the one that we can show here
        list_areas = cp.deepcopy(self.param['fitted_areas_list3'].objects)
        list_areas.sort()
        lista_elnes = ['center','amplitude','sigma','cont_A']
        for a,area in enumerate(self.fitted_areas_list):
            dictio = dict()
            for elem in self.locking_dict[area]:
                for compo in self.locking_dict[area][elem]:
                    dictio[''.join([elem,compo])] = list()
                    for paramet in lista_elnes:
                        if paramet in self.locking_dict[area][elem][compo]:
                            dictio[''.join([elem,compo])].append(\
                            not(self.locking_dict[area][elem][compo][paramet]))
                        else:
                            dictio[''.join([elem,compo])].append(None)
            lista_param_names = ['Center','Amplitude','Sigma','Continuum']
            df = pd.DataFrame(dictio,index=['center','amplitude','sigma','cont_A'])
            arr = df.to_numpy()
            data_set = xr.Dataset({'Vary':(['Parameter','Component'],arr)},\
                coords={'Component':list(dictio.keys()),'Parameter':lista_param_names})
            hmap = hv.HeatMap(data_set)\
            .opts(aspect = 1,cmap = ['red','green'],clim=(0,1),xlabel='',\
                ylabel='',clipping_colors={'NaN':'white'},tools = ['hover'],\
                #xlim = self.xlims,ylim = self.ylims,\
                frame_width = 200,border = 5,xrotation = 60,bgcolor = 'white')
            #We build it in sets of 4 columns
            if a < 4 and len(self.fitted_areas_list) > 4:
                hmap.opts(xaxis=None)
            if a%4 != 0:
                hmap.opts(yaxis = None)
            if a <= 7:
                list_heatmaps.append(hmap*hv.Text(x = ''.join(list(dictio.keys())[1].split('-')),\
                    y = 'Continuum',text='-'.join(area.split('_')).capitalize())\
                .opts(color = self.colordict[area]))
        lay = hv.Layout(list_heatmaps).cols(4)
        lay.opts(toolbar = 'right') 
        #Now the actual substitution    
        if not self.flag_truth_table:
            #1st iteration - add stuff
            self.re_New_mod[1][1][1].append(lay)
            self.flag_truth_table = True
        else:
            self.re_New_mod[1][1][1].pop(-1)
            self.re_New_mod[1][1][1].append(lay)
        #recovering functionality
        self.button_show_truth_table.disabled = False
        self.button_show_truth_table.button_type = 'success'
        self.button_show_truth_table.name = 'Update truth table'
    
    def _callback_change_tree(self,event):
        if not self.flag_component_display:
            self.flag_component_display = True
            if self.type_tree == 'tree':
                self.re_New_mod[1][0][1].append(self.tree)
            elif self.type_tree == 'radial':
                self.re_New_mod[1][0][1].append(self.radial_graph)
            else:
                self.re_New_mod[1][0][1].append(self.spring_graph)
            self.button_show_tree.disabled = True
            self.button_show_tree.button_type = 'default'
        else:
            self.re_New_mod[1][0][1].pop(-1)
            if self.type_tree == 'tree':
                self.re_New_mod[1][0][1].append(self.tree)
            elif self.type_tree == 'radial':
                self.re_New_mod[1][0][1].append(self.radial_graph)
            else:
                self.re_New_mod[1][0][1].append(self.spring_graph)
            self.button_show_tree.disabled = True
            self.button_show_tree.button_type = 'default'
        
    def _callback_activate_possible_rerun(self,event):
        #This method controls the activation of the rerun tabs
        #Now lets update the lock selector panel info by forcing a selection
        # working here
        self._create_locking_dict()
        self.fitted_areas_list3 = self.param['fitted_areas_list3'].objects[0]
        self.button_lock_all.disabled = False
        self.button_lock_all.button_type = 'success'
        self.button_unlock_all.disabled = False
        self.button_unlock_all.button_type = 'warning'
        self.ticking_elnes_boxes[0].disabled = False
        self.ticking_continuum.disabled = False
        self.select_area_fixing[0].disabled = False
        self.select_elements_rerun[1].disabled = False
        self.select_elnes_rerun[1].disabled = False
        self.select_continuum_rerun[1].disabled = False
        self.button_add_extra_compo_rerun.disabled = False
        self.button_add_extra_compo_rerun.button_type = 'primary'
        self.button_show_tree.disabled = False
        self.button_show_tree.button_type = 'success'
        self.type_tree_button[0].disabled = False
        #here we create the dictionary for the component control
        self.dictio_newcomps_area = dict()
        #This is to ensure reboot when clicked the right button
        self.NLLS.extra_modified_model_components = {}   #Reset
        self._get_connectivity_graph()
        self.button_activate_rerun.button_type = 'danger'
        self.button_activate_rerun.name = 'Reboot new model'
        self.button_show_truth_table.disabled = False
        self.button_show_truth_table.button_type = 'success'
        self.clusters_additions[0].disabled = True
        self.clusters_additions[0].button_type = 'default'
        self.components_additions[0].disabled = True
        self.components_additions[0].button_type = 'default'
        self.param['clusters_with_newcomps'].objects=['NoCluster']
        self.param['added_list_compos'].objects = ['NoNewComponents'] 
        self.added_list_compos = ['NoNewComponents']
        self.clusters_with_newcomps = 'NoCluster'
        self.toggle_use_locking[0].disabled = False
        #NOw the actual button, so it doesn't get stucked
        self.clusters_additions[0].options = {'NoCluster':'NoCluster'}
        self.button_show_new_comps_selected.disabled = True
        #Now the configuration of these 2 param variables for the new fitting
        #They control the non fitted clusters up to now
        self.param['non_fitted_clusters'].objects =\
            [el for el in self.NLLS.models_components.keys()\
            if el not in self.param['fitted_areas_list3'].objects]
        self.param['non_fitted_clusters_list'].objects = \
            self.param['non_fitted_clusters'].objects
        self.param['added_list_compos'].objects = []
        #To be able to reboot model rerun
        self.current_added_component =\
            pd.DataFrame(data = ['NoData'],columns=['NoCluster'],\
            index=['Components added']).transpose()
        self.data_frame_info.object = self.current_added_component
    
    def _callback_change_styles_totRCS(self,event):
        #Setting the thematic changes
        if self.red_chi_theme == 'dark': clip_grid = [{'NaN': 'black'},'black']
        elif self.red_chi_theme == 'light': clip_grid = [{'NaN': 'white'},'white']
        elif self.red_chi_theme == 'gray': clip_grid = [{'NaN': 'lightgray'},'gray']
        else: clip_grid = [{'NaN': 'white'},'white'] #defaults to light   
        #Now applying them
        im = self.tot_RCS_hmap.opts(colorbar=False,\
            line_color = clip_grid[1],\
            clipping_colors = clip_grid[0],cmap = self.red_chi_sq_cmap)
        self.analysis_tabs[0][-1].pop(0)
        self.analysis_tabs[0][-1].insert(0,im)
        self.analysis_tabs[0][-1][0].margin = (5,5,5,25)
        
    def _callback_add_errormaps(self,event):
        #Method to add error maps to the displayed info in the relative error tab
        self.button_erase_column_errormaps.disabled = False
        self.button_erase_column_errormaps.button_type = 'warning'
        if len(self.analysis_tabs[1][1][1]) >= 3:
            #Do nothing...maximum capacity achieved - erase element to add new ones
            return
        #Theme selection
        if self.red_chi_theme == 'dark': clip_grid = [{'NaN': 'black'},'white']
        elif self.red_chi_theme == 'light': clip_grid = [{'NaN': 'white'},'black']
        elif self.red_chi_theme == 'gray': clip_grid = [{'NaN': 'lightgray'},'white']
        else: clip_grid = [{'NaN': 'white'},'black'] #defaults to light   
        cmap_per_param = {'center':'viridis','sigma':'cividis','amplitude':'plasma'}
        
        fila = pn.Row(margin = (5,15))
        for el in self.param_analysis:
            limit = max(self.param_cmap_upperLimit,1)
            string = 'Relative error of '
            title_string = '{} : {}'.format(''.join([self.element_analysis,self.result_ELNES_compo]), el.capitalize())
            name = ''.join([string,self.element_analysis,self.result_ELNES_compo,'_',el])
            fila.append(hv.HeatMap(self.total_param_relSTDERR[name])
                .opts(cmap=cmap_per_param[el],aspect='equal',invert_yaxis=True,tools=['hover'],
                      xlim = self.xlims,ylim = self.ylims,
                      xaxis = None, yaxis = None,border = 10,colorbar = True,
                      toolbar = 'below',title = title_string,show_title = True,
                      clim=(0,limit),frame_height = 215,shared_axes = False,
                      line_color = clip_grid[1],line_width = 0.05,clipping_colors = clip_grid[0]))
        self.analysis_tabs[1][1][1].append(fila)
        if len(self.analysis_tabs[1][1][1]) >= 3:
            #Deactivate button until some row is deleted, double safety we have in place
            self.button_add_column_errormaps.disabled = True
            self.button_add_column_errormaps.button_type = 'default'
            
    def _callback_erase_errormaps(self,event):
        #Method to erase a column of error maps in the relative error tab
        self.analysis_tabs[1][1][1].pop(-1)
        if len(self.analysis_tabs[1][1][1]) < 3:
            #Reacitvates the possibility of adding columns
            self.button_add_column_errormaps.disabled = False
            self.button_add_column_errormaps.button_type = 'primary'
        if len(self.analysis_tabs[1][1][1]) <= 1:
            #Deactivates the error erase button if no further maps are available
            self.button_erase_column_errormaps.disabled = True
            self.button_erase_column_errormaps.button_type = 'default'
    #####################################################################################
    #####################################################################################
    # Responsive methods
    #####################################################################################
    @param.depends('use_locking_dictionary',watch = True)
    def _change_locking_button_style(self):
        try:
            #If it exists already
            self.toggle_use_locking[0].disabled
        except:
            #Do nothing
            return
        else:
            if self.use_locking_dictionary: 
                self.toggle_use_locking[0].button_type = 'success'
                self.toggle_use_locking[0].name = 'Components Locked'
            else: 
                self.toggle_use_locking[0].button_type = 'danger'
                self.toggle_use_locking[0].name = 'Components Unlocked'

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

    @param.depends('type_tree',watch = True)
    def allow_show_tree(self):
        try:
            self.button_show_tree.disabled = False
            self.button_show_tree.button_type = 'success'
            self.button_show_tree.name = 'Show components display'
        except: pass
    @param.depends('area',watch = True)
    def change_area(self):
        #Method that changes the area to be displayed in images..parameters..etc
        #Changing the overlay of images
        #Modi
        '''
        vals = np.ones_like(self.NLLS.ref_matrices[self.area])
        vals[self.NLLS.ref_matrices[self.area] == 0] = np.NaN
        xs = self.ds.x.values
        ys = self.ds.y.values
        self.mask = xr.Dataset({'mask':(['y','x'],vals)},\
                    coords = {'x':xs,'y':ys})
        '''
        if self.area == 'None':
            self.def_image_placeholder.object =\
            self.hmap_im
            #self.point_image*
            return
        #Let's select the color for the binary cmap
        if 'cluster' in self.area:
            idx = int(self.area[self.area.index('_') + 1:])
            self.cmap_binary = ['black',self.colores[idx]]
            #For the display sign in the parameter config window
            idx2 = self.area.index('_')
            string = ' '.join([self.area[:idx2].capitalize(),self.area[idx2+1:]])
            style = {'color':self.colores[int(self.area[idx2+1:])]}
        else:
            self.cmap_binary = ['black','aquamarine']
            string = self.area
            #self.cmap_binary = ['black',self.colores[idx]]
            style = {'color':self.cmap_binary[-1]}
        '''
        self.mask_im = hv.Image(self.mask,kdims=['x','y']).opts(aspect = 'equal',\
            invert_yaxis=True,cmap = self.cmap_binary,\
            xlim = self.xlims,ylim = self.ylims,\
            alpha = 0.5,show_grid = True)
        self.overlay_image = hv.Overlay([self.image_SI,self.mask_im])\
            .opts(frame_height=250)
        self.area_selector.pop(-1)
        self.area_selector.append(self.overlay_image)
        self.area_selector[-1].margin = (0,0,0,25)
        '''
        if self.overlay_clust_bool:
            self.mask_new_im =  hv.Image(self.ds_masks[self.area],\
                kdims=['x','y']).opts(aspect = 'equal',\
                invert_yaxis=True,cmap = self.cmap_binary,\
                xlim = self.xlims,ylim = self.ylims,\
                alpha = 0.5,show_grid = False,\
                hooks = [hook_black_image],bgcolor = 'black')
            self.def_image_placeholder.object =\
            self.hmap_im*self.mask_new_im
            #self.point_image*self.default_image*self.mask_new_im
        else:
            self.def_image_placeholder.object =\
            self.hmap_im
        self.mk2.object = '#### - {} -'.format(string)
        self.mk2.style = style
        #This is also important - let's change the compo_type so the button
        #raster is refreshed
        self.model_type_component = 'continuum'
        
    @param.depends('overlay_clust_bool',watch = True)
    def _change_overlay_of_clusters(self):
        if self.overlay_clust_bool:
            self.button_overlay_clusters_active[0].button_type = 'success'
            self.mask_new_im =  hv.Image(self.ds_masks[self.area],kdims=['x','y'])\
                .opts(aspect = 'equal',\
                invert_yaxis=True,cmap = self.cmap_binary,\
                xlim = self.xlims,ylim = self.ylims,shared_axes = False,\
                xaxis = None,yaxis = None,\
                alpha = 0.5,show_grid = False,\
                hooks = [hook_black_image],bgcolor = 'black')
            self.def_image_placeholder.object =\
            self.hmap_im*self.mask_new_im
        else:
            self.button_overlay_clusters_active[0].button_type = 'default'
            self.def_image_placeholder.object =\
            self.hmap_im

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
            self.text_pane.object = '**Choose Subshell/s**'
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
            texto = '<br />'.join(['{} onset energy : {} eV'\
                .format(subs,en) for subs,en in zip(lista,onsets)])
            texto = '**{}**'.format(texto)
            self.text_pane.object = texto 
    
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
                self.model_config_widgets.objects = self.model_config_widgets.objects[:-1] + [self.parameter_configurator,]
                #self.parameter_configurator.objects = self.model_continuum_parameters
                #self.model_config_widgets.objects = self.model_config_widgets.objects[:-1].append(self.parameter_configurator)
            elif self.model_type_component == 'ELNES':
                self.parameter_configurator = self.model_ELNES_parameters
                self.model_config_widgets.objects = self.model_config_widgets.objects[:-1] + [self.parameter_configurator,]
                #self.model_config_widgets.objects = self.model_config_widgets.objects[:-1].append(self.parameter_configurator)
                #self.parameter_configurator.objects = self.model_ELNES_parameters
            else:
                pass

    #Now....the parameter change when jumping between elements
    @param.depends('area','model_element','model_type_component','model_component',watch = True)
    def watch_parameter_changes(self):
        if self.area == 'None':
            #Do nothing
            return
        if self.model:
            #In case of an empty component, do nothing
            if self.model_component != 'Empty' and self.model_type_component == 'ELNES':
                self.button_reset_parameters.disabled = False
                #We activate the function_type selector
                keyword = self.NLLS.models_components[self.area][self.model_element]\
                    ['ELNES'][self.model_component]['type_compo']
                self.param['type_compo'].objects = self.default_compo_funcs
                self.type_compo =\
                (lambda keyword: ' '.join([keyword.capitalize(),'component']))(keyword)
                self.button_compo_func[0].disabled = False
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
                self.button_compo_func[0].disabled = True
                self.param['type_compo'].objects = ['Hartree/Hydrogenic']
                self.type_compo = 'Hartree/Hydrogenic'
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
                self.button_compo_func[0].disabled = True
                
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
        #maxi_s_b = 3.5*sig #Avoids out of bounds
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
    
    @param.depends('type_compo',watch = True)
    def _type_of_component_ELNES(self):
        #method that changes the type of component for a certain
        #ELNES model component - chosing between 4 options
        if self.model_type_component == 'ELNES':
            #We only want changes when this is true
            self.NLLS.models_components[self.area][self.model_element]\
            ['ELNES'][self.model_component]['type_compo'] =\
            (lambda keyword: keyword[:keyword.index(' ')].casefold())\
                (self.type_compo)
        else:
            pass
    
    #Controls for the clustering file selector
    @param.depends('path_toClust',watch = True)
    def _control_path_imput(self):
        try:
            os.listdir(self.path_toClust)
        except Exception as e:
            #print(e)
            self.path_toClust = self.param['path_toClust'].default
        finally:
            lista = [el for el in os.listdir(self.path_toClust) if '.nc' in el]
            self.param['file_clust'].objects = lista
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
            return hv.VLine(self.center).opts(line_alpha = 1,line_width=1,line_color = 'green',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        else:
            return hv.VLine(self.center).opts(line_alpha = 0,\
            bgcolor = 'black',hooks = [hook_full_black_black])
    
    @param.depends('center','sigma','show_fwhm','type_compo',watch = True)
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
            idx = self.type_compo.index(' ')
            keyword = self.type_compo[:idx]
        except:
            vline1 = hv.VLine(self.center - 1).opts(line_alpha = 0,\
            bgcolor = 'black',hooks = [hook_full_black_black])
            vline2 = hv.VLine(self.center - 1).opts(line_alpha = 0,\
            bgcolor = 'black',hooks = [hook_full_black_black])
            overlay = hv.Overlay([vline1,vline2])  
        else:
            if self.show_fwhm:
                alph = 1
            else:
                alph = 0
            fwhm = self.fwhm_dict[keyword](self.sigma)
            vline1 = hv.VLine(self.center - fwhm/2)\
                .opts(line_alpha = alph,line_width=1,line_color = 'orange',\
            bgcolor = 'black',hooks = [hook_full_black_black])
            vline2 = hv.VLine(self.center + fwhm/2)\
                .opts(line_alpha = alph,line_width=1,line_color = 'orange',\
            bgcolor = 'black',hooks = [hook_full_black_black])
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
            curve2 = self.dictionary_fitted_ref_compos[self.area]\
                .opts(hooks = [hook_full_black_black_with_legend],\
                shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
                ylabel = 'Electron Counts [a.u.]')
            curve1 = self.dictionary_fitted_ref_overall[self.area]\
                .opts(shared_axes = False,xlabel = 'Electron Energy Loss [eV]',\
                ylabel = 'Electron Counts [a.u.]')
            nombre = self.area
        except:
            curve1 = self.default_curve_references
            curve2 = self.default_curve_references
            nombre = 'None'
        finally:
            '''
            self.tabs_references[1].pop(-1)
            self.tabs_references[1].pop(0)
            self.tabs_references[1].extend([
            pn.pane.Markdown('#### Best fit for the reference spectra of the - **{}** - area'.format(nombre)),\
                curve1])
            '''
            self.mkdown_BestFit.object = '#### &nbsp;&nbsp;&nbsp;&nbsp;\
                Best fit for the reference spectra of the - **{}** - area'\
                .format(nombre)
            self.mkdown_BestFit.style = {'color':'white'}
            self.best_fit_placeholder.object = curve1
            self.mkdown_Compos.object = '#### &nbsp;&nbsp;&nbsp;&nbsp;\
                Fitted individual components for the reference spectra of the **{}** area'\
                .format(nombre)
            self.mkdown_Compos.style = {'color':'white'}
            self.compos_placeholder.object = curve2
            '''
            self.tabs_references[2].pop(-1)
            self.tabs_references[2].pop(0)
            self.tabs_references[2].extend([
            pn.pane.Markdown('#### Fitted individual components for the reference spectra of the **{}** area'\
                .format(nombre)),\
                curve2])
            '''
    @param.depends('new_compo_energy','new_compo_toggle',watch = True)
    def _show_new_compo_center(self):
        if self.new_compo_toggle:
            try:
                self.button_new_compo_center_show[0].button_type = 'success'
            except: pass
            return hv.VLine(self.new_compo_energy).opts(line_alpha = 1,line_width=1,line_color = 'purple',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        else:
            try:
                self.button_new_compo_center_show[0].button_type = 'default'
            except:pass
            return hv.VLine(self.new_compo_energy).opts(line_alpha = 0,line_width=0,line_color = 'purple',\
            bgcolor = 'black',hooks = [hook_full_black_black])
    #####################################################################################
    #Responsive behaviour of analysis tools:
    #####################################################################################
    @param.depends('multifit_performed',watch = True)
    #Monitors changes in the fitted regions and allows us to change the accesible info
    def _change_fitted_areas(self):
        if self.multifit_performed:
            self.param['fitted_areas_list'].objects = \
                list(self.NLLS.results.keys())
        else:
            self.param['fitted_areas_list'].objects = []
            self.fitted_areas_list = self.param['fitted_areas_list'].objects
    
    @param.depends('fitted_areas_list2',watch = True)
    def _change_string_structure_info_display(self):
        #Method tho change the median and time displayed in the info lateral
        try:
            area = self.fitted_areas_list2
            string_cluster =\
                ''.join(area.split('_')).capitalize()
            self.partial_time_text =\
            'Elapsed time on {} - fitting : {} s'\
            .format(string_cluster,round(self.time_per_cluster[area],1))
        except:
            pass
        try:
            #Let's get the median
            area = self.fitted_areas_list2
            string_cluster =\
                ''.join(area.split('_')).capitalize()
            zer = np.zeros_like(self.total_res_analysis.ReducedChiSq.values)
            zer[np.isnan(self.masks_per_area[area].data.mask_cluster.values) == False] =\
                self.total_res_analysis.ReducedChiSq.values\
                [np.isnan(self.masks_per_area[area].data.mask_cluster.values) == False]
            med = np.median(zer[zer != 0])
            self.partial_median_text = 'Median Reduced \u03A7\u00b2<br> for {} : {} '\
                .format(string_cluster,round(med,2))
        except: pass
            
    @param.depends('change_analysis_disp_graph','fitted_areas_list2',watch = True)
    def _change_info_display_graph(self):
        if self.button_change_info_display[0].disabled:
            #Do nothing is disabled....no matter what
            return
        if self.change_analysis_disp_graph:
            self.button_change_info_display[0].button_type = 'success'
            self.button_change_info_display[0].name = 'Showing fitted areas'
            list_areas = []
            for el in self.total_dataset_mask:
                if el != 'SI' and el == self.fitted_areas_list2:
                    list_areas.append(hv.Image(self.total_dataset_mask[el])\
                    .opts(aspect = 'equal',frame_height = 200,hooks=[hook_full_black],\
                    invert_yaxis = True,xaxis = None,yaxis = None,alpha = 1,\
                    xlim = self.xlims,ylim = self.ylims,\
                    cmap = ['black',self.colordict[el]],border = 0))
                elif el != 'SI':
                    list_areas.append(hv.Image(self.total_dataset_mask[el])\
                    .opts(aspect = 'equal',frame_height = 200,hooks=[hook_full_black],\
                    invert_yaxis = True,xaxis = None,yaxis = None,alpha = 0.25,\
                    xlim = self.xlims,ylim = self.ylims,\
                    cmap = ['black',self.colordict[el]],border = 0))
            list_overlay = [hv.Image(self.total_dataset_mask['SI'])\
                    .opts(aspect = 1,frame_height = 200,hooks = [hook_full_black],\
                    invert_yaxis = True,xaxis = None,yaxis = None,alpha = 1,\
                    xlim = self.xlims,ylim = self.ylims,\
                    cmap = 'greys_r'),]
            list_overlay.extend(list_areas)
            self.lateral.pop(-1)
            self.lateral.append(hv.Overlay(list_overlay))
            self.lateral[-1].margin = (20,70)
        else:
            self.button_change_info_display[0].button_type = 'warning'
            area = self.fitted_areas_list2
            self.button_change_info_display[0].name =\
            '{} r-\u03A7\u00b2 histogram'.format(''.join(area.split('_')).capitalize())
            #Now... all the calculations for the histogram
            area = self.fitted_areas_list2
            zer = np.zeros_like(self.total_res_analysis.ReducedChiSq.values)
            zer[np.isnan(self.masks_per_area[area].data.mask_cluster.values) == False] =\
                self.total_res_analysis.ReducedChiSq.values\
                [np.isnan(self.masks_per_area[area].data.mask_cluster.values) == False]
            #The number of bins are related to the np.sqrt(N_elements in cluster not NaN)
            hist = np.histogram(zer[zer != 0],bins=max(1,int(np.sqrt(zer[zer != 0].size))))
            histo = hv.Histogram(hist,kdims='Reduced Chi Square',vdims='Absolute Frequency')\
                .opts(border = 10,frame_height = 100,frame_width = 200,bgcolor='black',\
                    color=self.colordict[area],gridstyle = {'color':'white'},\
                    show_grid = True,fill_alpha = 0.75,\
                    toolbar = 'above',hooks =[hook_full_black])
            #Now, we replace the last element in the lateral bar by this histogram
            self.lateral.pop(-1)
            self.lateral.append(histo)
            self.lateral[-1].margin = (5,37)
            
    @param.depends('overlay_clusters_RCS',watch = True)
    def _callback_overlay_cluster_RCS(self):
        if self.overlay_clusters_RCS:
            #We disable the change style tab and overlay heatmaps
            self.button_change_styling_RCS.disabled = True
            list_of_clusters = list()
            list_of_clusters.append(self.tot_RCS_hmap)
            for el in self.total_dataset_mask:
                if el != 'SI':
                    list_of_clusters.append(hv.Image(self.total_dataset_mask[el])\
                    .opts(aspect = 'equal',frame_height = 300,\
                    invert_yaxis = True,xaxis = None,yaxis = None,alpha = 0.45,\
                    xlim = self.xlims,ylim = self.ylims,\
                    cmap = ['black',self.colordict[el]]))
            
            overlay_HMAP_cluster = hv.Overlay(list_of_clusters).opts(toolbar='right')
            self.analysis_tabs[0][-1].pop(0)
            self.analysis_tabs[0][-1].insert(0,overlay_HMAP_cluster)
            self.analysis_tabs[0][-1][0].margin = (5,5,5,25)
        else:
            self.button_change_styling_RCS.disabled = False
            self.analysis_tabs[0][-1].pop(0)
            self.analysis_tabs[0][-1].insert(0,self.tot_RCS_hmap)
            self.analysis_tabs[0][-1][0].margin = (5,5,5,25)

    @param.depends('element_analysis',watch = True)
    def _change_element_analysis_display(self):
        #Some clusters may have more ELNES structures than others, but in the overall 
        #picture for the whole SI we need all of them
        #We run over the fitted elements only
        lista_init = []
        for areas in self.param['fitted_areas_list'].objects:
            try:
                #It may happen that an element is not present in a cluster, and thus:
                elnes_list = list(self.NLLS.models_components[areas]\
                    [self.element_analysis]['ELNES'].keys())
            except:
                pass
            else:
                for elnes in elnes_list:
                    if elnes not in lista_init:
                        lista_init.append(elnes)
                        
        #Control over allowing display
        if lista_init == []: lista_init = ['NoELNES'] 
        self.param['result_ELNES_compo'].objects = lista_init
        self.result_ELNES_compo = lista_init[0]
        self.param_analysis = [] #Empties the parameter selection
        
    @param.depends('result_ELNES_compo','param_analysis',watch = True)
    def _disable_adding_button(self):
        #Controls if we disable the add error panel button or not
        if self.result_ELNES_compo == 'NoELNES' or self.param_analysis == []:
            self.button_add_column_errormaps.disabled = True
            self.button_add_column_errormaps.button_type = 'default'
            self.cmap_upper_lim[0].disabled = True
        else:
            self.button_add_column_errormaps.disabled = False
            self.button_add_column_errormaps.button_type = 'primary'
            self.cmap_upper_lim[0].disabled = False
            
    @param.depends('fitted_areas_list3',watch = True)
    def _change_re_run_area_selection(self):
        #The element ELNES and continuum components display are controlled here
        self.param['elements_re_run'].objects =\
            list(self.locking_dict[self.fitted_areas_list3].keys())
        self.elements_re_run = self.param['elements_re_run'].objects[0] 
        try:
            self.param['elnes_re_run'].objects = list(self.NLLS.models_components\
                [self.fitted_areas_list3][self.elements_re_run]['ELNES'].keys())
        except:
            #If no ELNES components - disable the ticking box so we do not collide
            self.ticking_elnes_boxes[0].disabled = True
        finally:
            self.param['continuum_re_run'].objects = list(self.NLLS.models_components\
                [self.fitted_areas_list3][self.elements_re_run]['continuum'].keys())
            self.continuum_re_run = self.param['continuum_re_run'].objects[0]
        
    @param.depends('elements_re_run',watch = True)
    def _change_re_run_element(self):
        #Controls the element change - so changes the ELNES and continuum possibilities
        try:
            self.param['elnes_re_run'].objects = list(self.NLLS.models_components\
                [self.fitted_areas_list3][self.elements_re_run]['ELNES'].keys())
        except:
            #If no ELNES components - disable the ticking box so we do not collide
            self.ticking_elnes_boxes[0].disabled = True
        else:
            self.ticking_elnes_boxes[0].disabled = False
            self.elnes_re_run = self.param['elnes_re_run'].objects[0]
        finally:
            #We will always have a continuum component
            self.ticking_continuum.disabed = False
            self.param['continuum_re_run'].objects = list(self.NLLS.models_components\
                [self.fitted_areas_list3][self.elements_re_run]['continuum'].keys())
            self.continuum_re_run = self.param['continuum_re_run'].objects[0]
            
    @param.depends('fitted_areas_list3','elements_re_run','elnes_re_run',watch = True)
    def _change_re_run_ELNES(self):
        #Controls the ticking display in the locking tab
        if self.elnes_re_run == 'NoELNES':
            self.ticking_elnes_boxes[0].disabled = True
            return #basically, a do nothing safety measurement
        else:
            self.ticking_elnes_boxes[0].disabled = False
            #Get the current boolean values in the dictionary
            current_list = list()
            try:
                #If the current selection of elnes is not in the changed area...
                self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                [self.elnes_re_run]
            except:
                #Let's pick the first element in this specific area
                self.elnes_re_run = self.param['elnes_re_run'].objects[0]
            finally:
                for el in self.param['lock_ELNES'].objects:
                    if self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                    [self.elnes_re_run][el]: 
                        current_list.append(el)
                    else: pass
                self.lock_ELNES = current_list
            
    @param.depends('fitted_areas_list3','elements_re_run','continuum_re_run',watch = True)
    def _change_re_run_continuum(self):
        #Controls the loading of ticks to the continuum locking panel
        try:
            self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                [self.continuum_re_run]['cont_A']
        except:
            #In case of not existing that component...do nothing
            pass 
        else:
            self.ticking_continuum.disabled = False
            self.lock_continuum = self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                    [self.continuum_re_run]['cont_A']
    
    @param.depends('lock_ELNES',watch = True)
    def _change_elnes_ticks(self):
        #Controls the changes in the ticking of ELNES components
        for parameter in self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
        [self.elnes_re_run]:
            if parameter in self.lock_ELNES:
                self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                [self.elnes_re_run][parameter] = True
            else:
                self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                [self.elnes_re_run][parameter] = False

    @param.depends('lock_continuum',watch = True)
    def _change_continuum_ticks(self):
        try:
            self.locking_dict[self.fitted_areas_list3][self.elements_re_run]\
                [self.continuum_re_run]['cont_A'] = self.lock_continuum
        except:
            pass
    
    #Panel contructor --------------------------------------------------------------------
    def _model_panel_constructor(self):
        #Constructs the panel displayed
        '''
        sel_el = pn.Param(self.param, widgets={'elemento':pn.widgets.Select,\
                'subshell':pn.widgets.CheckButtonGroup},\
            parameters = ['elemento','subshell'],\
            show_name = False,default_layout = pn.GridBox,name = '',\
            show_labels = False,margin = 0,align = 'start')
        sel_el[0].margin = (5,15)
        sel_el[0].width = 320
        '''
        sel_el = pn.Param(self.param, widgets={'elemento':pn.widgets.Select},\
            parameters = ['elemento'],\
            show_name = False,name = '',\
            show_labels = False,margin = 0,width = 75)
        sel_el[0].margin = 0
        sel_el[0].width = 75

        sel_ssh = pn.Param(self.param, widgets={'subshell':pn.widgets.CheckButtonGroup},\
            parameters = ['subshell'],\
            show_name = False,name = '',\
            show_labels = False,margin = 0,width = 200)
        sel_ssh[0].margin = 0
        sel_ssh[0].width = 225
        sel_ssh[0].button_type = 'primary'
        #'subshell':pn.widgets.CheckButtonGroup

        '''
        for el in sel_el:
            el.show_name = False
            el.name = ''
            el.show_labels = False
        '''
        #Widget box - Element selection
        '''
        deleteing_mod = pn.Row(self.button_reset,\
            self.button_deactivate_delete,self.button_delete_model,\
            width = 340,margin = (0,10),align='start')
        deleteing_mod[0].margin = (5,10,5,0)
        deleteing_mod[1].margin = (5,0,5,15)
        deleteing_mod[2].margin = (5,0,5,0)
        '''
        self.mkdwn_model_constructor =\
            pn.pane.Markdown('### Element Selection Panel',\
            width = 200,margin = (5,5,0,15),style = {'color':'white'},height = 35)
        sel_el_widgets = pn.Column(\
            self.mkdwn_model_constructor,\
            pn.layout.Divider(margin = (5,10)),\
            self.widget_box_load_model,pn.layout.Divider(margin = (0,5)),\
            #sel_el,\
            pn.Row(sel_el,sel_ssh,margin = (0,25),width = 300),\
            self.text_pane,\
            pn.Row(pn.pane.Markdown('Soft-Edge',style = {'color':'white'},\
                    width = 75,height = 35,margin = (5,0)),\
                pn.pane.Markdown('X-section type',style = {'color':'white'},\
                    width = 200,height = 35,margin = (5,0,5,25)),\
                margin = (0,25),width = 300),\
            pn.Row(self.soft_edges_button,self.soften_val_wid,self.x_sec_selector,margin = (0,25)),\
            pn.Row(self.button_add_element,self.button_create_model,\
                self.button_save_model,width = 300,margin = (5,25)),\
            self.box,\
            pn.layout.Divider(margin = (0,5,0,5)),\
            margin = (0,0,30,0),height = 720,\
            background = 'black',\
            width = 350)
        #Widgets for model configurations
        self.model_config_widgets = pn.Column(\
            pn.Row(pn.pane.Markdown('### Model Configuration',\
                width = 150,margin = (5,15),height = 35),\
                self.button_save_config,height = 45,width  = 320,margin = 0),\
            self.mod_el,\
            pn.Row(self.button_remove_component,self.button_reset_parameters,\
                width = 300,margin = (0,10)),\
            pn.pane.Markdown('### Parameters',width = 225,height = 35,margin = (0,20)),\
            self.current_area_mkdwn,\
            self.button_compo_func,\
            self.parameter_configurator,\
            margin = 0,background = 'white',width = 320)
        self.mod_el[0][0].disabled = True
        self.mod_el[0][1].disabled = True
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
            self.button_add_extra_compo,\
            width = 320,height = 720,margin = 0)
        #Some minor modifications
        wid_new_compo[0][0].margin = (10,0,5,20)
        wid_new_compo[4][0].margin = (15,5,10,20)
        wid_new_compo[5][0].margin = (15,5,10,20)
        wid_new_compo[6][0].margin = (15,5,10,20)
        #For the multifit tab
        areas_multifit_wid = pn.Param(self.param['multifit_area'],\
            widgets = {'multifit_area':pn.widgets.MultiChoice},\
            parameters = ['multifit_area'],width = 300,show_labels = False,\
            show_name = True,name = 'Select Areas for MultiFit',\
            margin = (5,10),height = 250)
        areas_multifit_wid[0].margin = (0,15)
        areas_multifit_wid[0].width = 250
        areas_multifit_wid[1].width = 250
        areas_multifit_wid[1].margin = (5,15)
        etc_lists_wid = pn.Param(self.param['list_of_ETCs'],\
            widgets = {'list_of_ETCs':pn.widgets.StaticText},\
            parameters = ['list_of_ETCS'],width = 280,\
            show_labels = False,show_name = False,\
            margin = (0,5,0,20))
        '''
        message = pn.Param(self.param['ETC'],widgets = {'ETC':pn.widgets.StaticText},\
            parameters = ['ETC'],show_labels = False,show_name = False,width = 300)
        '''
        multi = pn.Column(\
            pn.pane.Markdown('### Multifit controls',width = 200,\
                margin = (5,5,0,20),style = {'color':'black'},height = 35),\
            pn.layout.Divider(margin = (5,20)),\
            areas_multifit_wid,\
            pn.layout.Divider(margin = (5,20)),\
            self.button_multifit,\
            self.prog_bar,\
            #message,\
            pn.pane.Markdown('#### Fitting times per area (s)',\
                width = 250,margin = (5,15,0,20)),\
            pn.Column(etc_lists_wid,height = 250,width= 320,\
                margin = 0,css_classes = ['scrollable_onlyY']),\
            height = 720,width = 320,margin = 0)
        #The tabs
        self.tabs = pn.Tabs(\
            ('Components',pn.Column(self.model_config_widgets,\
                self.widget_box_load_configuration,\
                height = 720,width = 320,margin = 0,background = 'white')),\
            #('Area',self.area_selector),\
            #('Visualization',visual),\
            ('Extra-Compo',wid_new_compo),\
            ('Multifit',multi),\
            active = 0,margin = 0, height = 720,width = 435,\
            tabs_location='right',dynamic = True)
        #Panel1
        self.panel1 = pn.Row(sel_el_widgets,self.tabs)
        #Dynamic maps to show the center and sigma lines
        self.center_Vline = hv.DynamicMap(self._return_center_vline)
        self.sigmas_Vlines = hv.DynamicMap(self._return_sigmas_vline)
        self.new_center_Vline = hv.DynamicMap(self._show_new_compo_center)
        #Tabs for the reference spectra overlays
        self.dynamic_placeholder = pn.pane.HoloViews(self.dynamic_graphs_1
            *self.center_Vline
            *self.sigmas_Vlines
            *self.new_center_Vline)
        self.ref_overlay_placeholder = pn.pane.HoloViews(
            hv.NdOverlay(self.dictionary_references)
            .opts(hooks=[hook_full_black_black_with_legend], bgcolor='black')
        )
        self.mkdown_BestFit = pn.pane.Markdown(
            '#### &nbsp;&nbsp;&nbsp;&nbsp;Best fit for the reference spectra of the **{}** area'.format(' - None - '),
            style={'color': 'darkgrey'}, width=700)
        self.mkdown_Compos = pn.pane.Markdown(
            '#### &nbsp;&nbsp;&nbsp;&nbsp;Fitted individual components for the reference spectra of the **{}** area'.format(' - None - '),
            style={'color': 'darkgrey'}, width=700)
        # Fix: always squeeze to 1D and select only 'Eloss' for HoloViews
        default_curve = self.default_curve_references
        if hasattr(default_curve, 'dims'):
            if 'x' in default_curve.dims:
                # If 2D, select the first x or squeeze
                default_curve = default_curve.isel(x=0).squeeze()
            elif 'Eloss' in default_curve.dims:
                default_curve = default_curve.squeeze()
        self.best_fit_placeholder = pn.pane.HoloViews(
            hv.Curve(default_curve, kdims='Eloss', vdims='ElectronCounts') if hasattr(default_curve, 'dims') and 'Eloss' in default_curve.dims else default_curve
        )
        self.compos_placeholder = pn.pane.HoloViews(
            hv.Curve(default_curve, kdims='Eloss', vdims='ElectronCounts') if hasattr(default_curve, 'dims') and 'Eloss' in default_curve.dims else default_curve
        )
        self.tabs_references = pn.Tabs(\
            ('Spectrum',pn.Column(pn.pane.Markdown('####  &nbsp;&nbsp;&nbsp;&nbsp;\
            Interactive Spectrum',style = {'color':'white'},width = 700),\
            self.dynamic_placeholder,align = 'end')),\
            ('References',pn.Column(pn.pane.Markdown('#### &nbsp;&nbsp;&nbsp;&nbsp;\
            All-areas Reference spectra',style = {'color':'white'},width = 700),\
                self.ref_overlay_placeholder,align = 'end')),\
            ('Best Fit',pn.Column(\
                self.mkdown_BestFit,\
                self.best_fit_placeholder,align = 'end')),\
            ('Fitted components ',pn.Column(\
                self.mkdown_Compos,self.compos_placeholder,align = 'end')),\
            )
        #Button column for the visualization area
        columna_botones = pn.Column(pn.pane.Markdown('#### Area / Cluster - selector',\
                    style = {'color':'white'},margin = (5,15,-5,15),height = 30,width = 350),\
                pn.Row(self.area_sel_wid,self.button_overlay_clusters_active),\
                pn.pane.Markdown('#### ELNES parameter-visualization',\
                    style = {'color':'white'},margin = (5,15,-5,15),height = 30,width = 350),\
                pn.Row(self.button_show_center,self.button_show_sigmas),\
                pn.pane.Markdown('#### Reference spectra fitting',\
                    style = {'color':'white'},margin = (5,15,-5,15),height = 30,width = 350),\
                pn.Row(self.button_fit_ref_select_area,self.button_fit_references))
        #image area config
        fila_images = pn.Row(self.def_image_placeholder,columna_botones,margin  = (5,15))
        self.panel2 = pn.Column(\
            pn.Row(pn.pane.Markdown('### Spectral Visualization Tools',\
                width = 260,height = 35,style = {'color':'white'},margin = (5,15)),\
                self.button_save_data,height = 45,margin = 0,width = 725),\
            fila_images,\
            self.tabs_references,\
            background = 'black',margin = (0,0,0,25),width = 725)
        panel_mod = pn.Row(self.panel1,self.panel2)
        return panel_mod
    
    def _result_analysis_panel_construction(self):
        #Function that builds the panel for the results analysis - after multifit
        #Let's add a selection tool for the different areas
        #Some widgets created for the different tabs
        selection_area_chi = pn.Param(self.param['fitted_areas_list'],\
            widgets = {'fitted_areas_list':pn.widgets.MultiChoice},\
            parameters = ['fitted_areas_list'],show_labels = False,show_name = True,\
            name = 'Fitted areas',width = 250)
        selection_area_chi[0].max_items = 5
        selection_area_chi[0].margin = (-5,10)
        selection_area_info = pn.Param(self.param['fitted_areas_list2'],\
            widgets = {'fitted_areas_list2':pn.widgets.Select},\
            parameters = ['fitted_areas_list2'],show_labels = False,show_name = False,\
            width = 150)
        theme_wid_1 = pn.Param(self.param['red_chi_theme'],\
            widgets = {'red_chi_theme':pn.widgets.Select},parameters=['red_chi_theme'],\
            show_labels = False, show_name = True,name = 'Theme',width = 125,)
        cmap_wid_1 = pn.Param(self.param['red_chi_sq_cmap'],\
            widgets = {'red_chi_sq_cmap':pn.widgets.Select},parameters=['red_chi_sq_cmap'],\
            show_labels = False, show_name = True, name = 'Colormap',width = 125)
        #PerCluster RED CHI SQ tab ################################################################
        ''' Legacy - no longer active tab
        custom_chisq = pn.Column(\
            pn.pane.Markdown('#### Plot Customization'),\
            self.button_show_chi_sqr,\
            pn.GridBox(theme_wid_1,cmap_wid_1,width = 265,ncols=2),\
            selection_area_chi,\
            width = 275,margin = 0,background = 'whitesmoke',height = 634)
        custom_chisq[-1].margin = (-5,5)
        custom_chisq[0].margin = (5,10)
        self.init_redChi_panel =\
            pn.Column(pn.pane.Markdown('### Reduced Chi Square',margin = (5,15)),\
                pn.Row(custom_chisq,self.image_for_analysis),\
                width = 1080)
        '''
        #TOTAL RED CHI SQ tab ################################################################
        self.total_chisq = pn.Row(pn.pane.Markdown('#### Heatmap<br>Customization<br>Controls'),\
            theme_wid_1,cmap_wid_1,\
            self.button_change_styling_RCS,self.button_overlay_cluster_RCS,\
            background = 'whitesmoke',width = 1080)
        self.total_chisq[0].margin = (5,5,5,15)
        self.total_chisq[-2].margin = (38,5,5,5)
        self.total_chisq[-1][0].margin = (33,5,5,5)
        self.init_residual_panel =\
        pn.Column(pn.pane.Markdown('### Fit-Residual function analysis',margin = (5,15)),\
            self.total_chisq,\
            pn.Row(hv.Image([]).opts(frame_height=300,toolbar='right',\
                xlim = self.xlims,ylim = self.ylims,\
                xaxis = None,yaxis = None,border = 5),\
                hv.Curve([],kdims = 'Eloss',vdims = 'ElectronCounts')\
                .opts(frame_height = 300,frame_width = 625,\
                yformatter=formatter ,border = 5,toolbar = 'right')))
        self.init_residual_panel[2].margin = (25,5)
        #LATERAL INFO
        #Adaptable texts for multifit info lateral
        self.text_median = pn.Param(self.param['full_median_text'],\
            widgets = {'full_median_text':pn.widgets.StaticText},\
            parameters = ['full_median_text'],width = 275,\
            show_name = False,show_labels = False,margin = (0,37))
        self.text_median[0].style = {'color':'white','font-weight':'bold'}
        self.text_time = pn.Param(self.param['full_time_text'],\
            widgets = {'full_time_text':pn.widgets.StaticText},\
            parameters = ['full_time_text'],width = 275,\
            show_name = False,show_labels = False,margin = (0,37))
        self.text_time[0].style = {'color':'white','font-weight':'bold'}
        self.text_cluster_median = pn.Param(self.param['partial_median_text'],\
            widgets = {'partial_median_text':pn.widgets.StaticText},\
            parameters = ['partial_median_text'],width = 275,\
            show_name = False,show_labels = False,margin = (0,37))
        self.text_cluster_median[0].style = {'color':'white','font-weight':'bold'}
        self.text_cluster_time = pn.Param(self.param['partial_time_text'],\
            widgets = {'partial_time_text':pn.widgets.StaticText},\
            parameters = ['partial_time_text'],width = 275,\
            show_name = False,show_labels = False,margin = (0,37))
        self.text_cluster_time[0].style = {'color':'white','font-weight':'bold'}
        #Now the actual lateral info display
        self.lateral = pn.Column(
            pn.pane.Markdown('### General Information', styles={'color':'white'}),
            self.button_analysis_run, self.button_analysis_rerun,
            self.text_time,
            self.text_median,
            pn.layout.Divider(margin=(-5, 0, -5, 0)),
            pn.Row(pn.pane.Markdown('#### Cluster<br>Select', styles={'color':'white'}), selection_area_info, width=275),
            self.text_cluster_median,
            self.text_cluster_time,
            pn.layout.Divider(margin=(-5, 0, -5, 0)),
            self.button_change_info_display,
            self.init_info_fill_image,
            width=350, height=720
        )
        #RELATIVE ERROR analysis TAB
        self.element_toggle = pn.Param(
            self.param,
            widgets={
                'element_analysis': pn.widgets.RadioButtonGroup,
                'result_ELNES_compo': pn.widgets.RadioButtonGroup,
                'param_analysis': pn.widgets.CheckButtonGroup
            },
            parameters=['element_analysis', 'result_ELNES_compo', 'param_analysis'],
            show_name=False, show_labels=False,
            default_layout=pn.Column, margin=(5, 15), width=235
        )
        for el in self.element_toggle:
            el.disabled = True
        self.cmap_upper_lim = pn.Param(
            self.param['param_cmap_upperLimit'],
            widgets={'param_cmap_upperLimit': pn.widgets.IntSlider(start=0, end=100, step=1, name='Cmap Upper Limit')},
            parameters=['param_cmap_upperLimit'],
            width=235, margin=(5, 15), name='Cmap Upper Limit',
            styles=None
        )
        self.cmap_upper_lim[0].disabled = True
        self.show_Error_param_pane = pn.Column(
            pn.pane.Markdown('### Model ELNES components - Parameter Relative Error heatmaps', margin=(5, 15)),
            pn.Row(
                pn.Column(
                    pn.pane.Markdown('#### ELNES Model component', margin=(5, 25)),
                    self.element_toggle, self.cmap_upper_lim,
                    theme_wid_1,
                    self.button_add_column_errormaps, self.button_erase_column_errormaps,
                    pn.pane.Markdown('#### Fitted Clusters', margin=(5, 0, 5, 25)),
                    background='whitesmoke', width=275, height=634
                ),
                pn.Column(pn.pane.Markdown('#### Computed Relative Errors (%) on display', margin=(5, 15, -5, 25)))
            ),
            width=1080, name='Relative Err'
        )
        self.show_Error_param_pane[1][0][4].margin = (5, 20)
        self.show_Error_param_pane[1][0][5].margin = (5, 20)
        #The final Assembly - TABS creation
        self.analysis_tabs = pn.Tabs(
            ('Residual functions', self.init_residual_panel),
            #('R-Chi-Sq / Area',self.init_redChi_panel), #Legacy - no longer available
            ('Relative Err', self.show_Error_param_pane),
            #('New Model Creator',re_New_mod),
            dynamic=True
        )
        self.panel_analys = pn.Row(self.lateral, self.analysis_tabs, margin=0)
        return self.panel_analys
    
    def _new_model_panel_constructor(self):
        #This is the constructor for the modified model creator panel
        #New component configurator for the Re-Run model
        #Button for the refresh 
        self.button_show_truth_table = pn.widgets.Button(name = 'Show truth table')
        self.button_show_truth_table.on_click(self._callback_update_truth_table)
        self.button_show_truth_table.disabled = True
        self.button_show_tree = pn.widgets.Button(name = 'Show components display')
        self.button_show_tree.on_click(self._callback_change_tree)
        self.button_show_tree.disabled = True
        self.type_tree_button = pn.Param(self.param['type_tree'],\
            widgets = {'type_tree':pn.widgets.RadioButtonGroup},\
            parameters = ['type_tree'],show_labels = False)
        self.type_tree_button[0].disabled = True
        truth_table_area = pn.Param(self.param['fitted_areas_list'],\
            widgets = {'fitted_areas_list':pn.widgets.MultiChoice},
            parameters = ['fitted_areas_list'],width = 850,height = 75,\
            show_labels = False)
        truth_table_area[0].max_items = 8
        comp_areas_new_mod = pn.Param(self.param['fitted_areas_list'],\
            widgets={'fitted_areas_list':pn.widgets.MultiChoice},\
            parameters = ['fitted_areas_list'],show_name = False,\
            show_labels = False,width = 250,height = 150)
        #Widgets for the new component adding in the possible re-run tab
        n_comp_el = pn.Param(self.param['new_compo_elements'],\
            widgets = {'new_compo_elements':pn.widgets.Select},\
            show_labels = False, show_name = False)
        n_comp_name = pn.Param(self.param['new_compo_name'],\
            widgets={'new_compo_name':pn.widgets.TextInput},\
            show_labels = False, show_name = False)
        n_comp_name[-1].placeholder = 'Enter name'
        n_comp_func = pn.Param(self.param['new_compo_func'],\
            widgets={'new_compo_func':pn.widgets.Select},\
            show_labels = False, show_name = False,width = 200)
        n_comp_energy = pn.Param(self.param['new_compo_energy'],\
            widgets = {'new_compo_energy':pn.widgets.FloatSlider},\
            show_labels = False, show_name = False,width = 150)
        n_comp_flex = pn.Param(self.param['new_compo_flex'],\
            widgets = {'new_compo_flex':pn.widgets.Select},\
            show_labels = False, show_name = False,width = 200)
        #New compo widget assembly
        wid_new_compo_rerun = pn.Column(pn.pane.Markdown('### ELNES - New component configurator'),\
            n_comp_el,n_comp_name,\
            pn.widgets.StaticText(value = 'Only already fitted areas are<br>allowed to be modified here'),\
            comp_areas_new_mod,\
            pn.Row(pn.widgets.StaticText(value = 'Function',width = 75),\
                n_comp_func,width = 300),\
            pn.Row(pn.widgets.StaticText(value = 'Center of E-Loss [eV]',width = 75),\
                n_comp_energy,width = 300),\
            pn.Row(pn.widgets.StaticText(value = 'Constraints init-flexibility',width = 75),\
                n_comp_flex,width = 300),\
            self.button_add_extra_compo_rerun)
        #Widget for fixing components
        message1_0 = 'Tick a box to<br>lock the ELNES<br>component parameter<br>for the selected<br>'
        message1_1 = 'area and element'
        message1   = ''.join([message1_0,message1_1]) 
        message2_0   = 'Tick the box to<br>lock the continuum<br>component for the<br>'
        message2_1 = 'selected area<br>and element'
        message2   = ''.join([message2_0,message2_1]) 
        elnes_col = pn.Column(self.select_elnes_rerun,\
            pn.Row(pn.widgets.StaticText(value = message1),\
            self.ticking_elnes_boxes),width = 300)
        conti_col = pn.Column(self.select_continuum_rerun,\
            pn.Row(pn.widgets.StaticText(value = message2),\
            self.ticking_continuum),width = 300)
        locking_panel = pn.Column(pn.pane.Markdown('### Locking configurator'),\
            self.select_area_fixing,\
            pn.Row(self.button_lock_all,self.button_unlock_all,margin = 0),\
            self.select_elements_rerun,\
            elnes_col,conti_col)
        locking_panel[1][0].margin = (0,0,0,15)
        locking_panel[1][1].margin = 0
        #The tabs to display the graphs as well
        locking_tab = pn.Row(locking_panel,\
            pn.Column(pn.pane.Markdown('### Truth Table - locked components visual display'),\
                pn.Row(self.button_show_truth_table,truth_table_area,min_width = 1080)),\
            width = 1456)
        new_comp_tab = pn.Row(wid_new_compo_rerun,\
            pn.Column(pn.pane.Markdown('### Components and clusters - visual display'),\
                pn.Row(self.button_show_tree,self.type_tree_button),min_width = 900),\
            width = 1500)
        for col in new_comp_tab[-1]: 
            col.margin = (5,10)
        #The list of components added to the model
        #Init - data frame is empty
        #The widgets for the previous clusters non fitted
        prev_clusters_nonfitted = pn.Param(self.param['non_fitted_clusters'],\
            widgets = {'non_fitted_clusters':pn.widgets.Select},\
            parameters  = ['non_fitted_clusters'],width = 300,show_labels = False)
        prev_clusters_selector = pn.Param(self.param['non_fitted_clusters_list'],\
            widgets = {'non_fitted_clusters_list':pn.widgets.MultiChoice},\
            parameters  = ['non_fitted_clusters_list'],\
                name = 'Previous non-fitted areas',show_name = True,\
                width = 300,show_labels = False,min_height = 150,height = 150)
        prev_clusters_selector[0].styles = {'color':'white'}
        #Now the whole part that launches the new model fitting
        self.button_cluster_to_newMod = pn.widgets.Button(name = 'Add')
        self.button_cluster_to_newMod.disabled = True
        self.button_cluster_to_newMod.on_click(self._callaback_AddToNewModel)
        self.button_cluster_to_newMod_erase = pn.widgets.Button(name = 'Remove')
        self.button_cluster_to_newMod_erase.disabled = True
        self.button_cluster_to_newMod_erase.on_click(self._callaback_RemoveFromNewModel)
        self.button_show_new_comps_selected = pn.widgets.Button(name = 'Show')
        self.button_show_new_comps_selected.disabled = True
        self.button_show_new_comps_selected.on_click(self._callback_Refresh_selection_show)
        self.button_show_prev_comps_selected = pn.widgets.Button(name = 'Show Components')
        self.button_show_prev_comps_selected.disabled = True
        self.button_show_prev_comps_selected.on_click(self._callback_show_prev_compos)
        self.button_show_prev_bestfit_selected = pn.widgets.Button(name = 'Show BestFit')
        self.button_show_prev_bestfit_selected.disabled = True
        self.button_show_prev_bestfit_selected.on_click(self._callback_show_prev_bestfit)
        self.clusters_additions = pn.Param(self.param['clusters_with_newcomps'],\
            widgets = {'clusters_with_newcomps':pn.widgets.Select},\
            parameters = ['clusters_with_newcomps'],width = 300,\
            show_name = False,show_labels = False)
        self.components_additions = pn.Param(self.param['added_list_compos'],\
            widgets = {'added_list_compos':pn.widgets.MultiSelect},\
            parameters = ['added_list_compos'],width = 300,\
            show_name = False,show_labels = False)
        self.toggle_use_locking = pn.Param(self.param['use_locking_dictionary'],\
            widgets = {'use_locking_dictionary':pn.widgets.Toggle},\
            parameters = ['use_locking_dictionary'],\
            width = 320,show_labels = False)
        self.toggle_use_locking[0].name = 'Components Locked'
        self.toggle_use_locking[0].button_type = 'success' #Initially locked
        self.toggle_use_locking[0].disabled = True
        self.clusters_additions[0].disabled = True
        self.components_additions[0].disabled = True
        self.data_frame_info = pn.pane.DataFrame(self.current_added_component,\
            width = 250)
        model_control_column = pn.Column(pn.pane.Markdown('### New model additions'),\
            self.clusters_additions,self.components_additions,\
            pn.Row(self.button_cluster_to_newMod,\
            self.button_cluster_to_newMod_erase,\
            self.button_show_new_comps_selected,width = 300),\
            pn.Column(self.data_frame_info,\
            min_width = 300,width = 300,height = 225,scroll = True),\
            pn.pane.Markdown('### NonFitted Clusters'),\
            prev_clusters_nonfitted,\
            pn.Row(self.button_show_prev_bestfit_selected,\
                self.button_show_prev_comps_selected,\
                width = 300), width = 325)
        # Ensure 1D xarray for HoloViews
        eloss = self.NLLS.Eloss
        zeros = np.zeros_like(eloss)
        ds = xr.Dataset({'ElectronCounts': ('Eloss', zeros)}, coords={'Eloss': eloss})
        # Squeeze to 1D and select only 'Eloss' for plotting
        curve1 = hv.Curve(ds['ElectronCounts'].squeeze(), kdims='Eloss', vdims='ElectronCounts')\
            .opts(yformatter=formatter, frame_width=650, frame_height=225, title='Graphical display of new components')
        curve2 = hv.Curve(ds['ElectronCounts'].squeeze(), kdims='Eloss', vdims='ElectronCounts')\
            .opts(yformatter=formatter, frame_width=650, frame_height=225, title='Graphical display of non-fitted previous components')
        display_newcompos_panel = pn.Column(
            pn.Column(curve1, min_width=750, min_height=310),
            pn.Column(curve2, min_width=750, min_height=310)
        )
        #New column to actually launch the multifitting for the second time, with
        #modified versions of the models
        self.progress_bar_0 = pn.Param(self.param['progress_preparing'],\
            widgets = {'progress_preparing':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['progress_preparing'])
        self.progress_bar_1 = pn.Param(self.param['progress_newModels'],\
            widgets = {'progress_newModels':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['progress_newModels'])
        self.progress_bar_2 = pn.Param(self.param['progress_multifitting_prev'],\
            widgets = {'progress_multifitting_prev':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['progress_multifitting_prev'])
        self.progress_bar_0[0].bar_color = 'secondary'
        self.progress_bar_1[0].bar_color = 'info'
        self.progress_bar_2[0].bar_color = 'danger'
        self.progress_bar_0[0].width = 150
        self.progress_bar_1[0].width = 150
        self.progress_bar_2[0].width = 150
        self.button_new_multifit_button = pn.widgets.Button(name = 'MultiFit')
        self.button_new_multifit_button.on_click(self._callback_multifit_rerun)
        select_new_model_areas = pn.Param(self.param['fitted_areas_list_last'],\
            widgets={'fitted_areas_list_last':pn.widgets.MultiChoice},\
            parameters = ['fitted_areas_list_last'],\
            name = 'Modified Areas',show_name = True,\
            show_labels = False,width = 300,height = 150)
        select_new_model_areas[0].style = {'color':'white'}
        prog_bars_column = pn.Row(pn.Column(\
            pn.widgets.StaticText(style = {'font-weight':'bold','color':'white'},\
            value = 'Model Preparation'),\
            pn.widgets.StaticText(style = {'font-weight':'bold','color':'white'},\
            value = 'Modified Model Multifit'),\
            pn.widgets.StaticText(style = {'font-weight':'bold','color':'white'},\
            value = 'Previous Model Multifit'),width = 150,background = 'black'),\
            pn.Column(self.progress_bar_0,self.progress_bar_1,self.progress_bar_2,\
            width = 150,background = 'black'),width = 325,background = 'black') 
        launch_multifit_re = pn.Column(\
            pn.pane.Markdown('### Model Fit',style = {'color':'white'}),\
            select_new_model_areas,self.toggle_use_locking,\
            prev_clusters_selector,self.button_new_multifit_button,\
            prog_bars_column,\
            width = 325,background = 'black',height = 634)
        new_multifit_tab = pn.Row(model_control_column,\
            display_newcompos_panel,\
            launch_multifit_re,width = 1500)
        #now the actual tab widget
        tabs_mod_constructor = pn.Tabs(\
            ('Create component',new_comp_tab),\
            ('Lock components',locking_tab),\
            ('Multifitting Configurator',new_multifit_tab),\
            dynamic=True) 
        self.re_New_mod = pn.Column(\
            pn.Row(pn.pane.Markdown('### Create new model from the previous iteration',min_width = 400),\
                self.button_activate_rerun,width = 1080),\
            tabs_mod_constructor,\
            width = 1500)
        #Some external extra configurations for the 'looks'
        self.re_New_mod[1][1][0][0].margin = (5,15)
        self.re_New_mod[1][0][0][0].margin = (5,15)
        self.re_New_mod[1][1][1][1][0].margin = (15,5,5,10)
        self.re_New_mod[1][1][1][1][0].margin = (15,5,5,10)
        self.re_New_mod[1][1][0].background = 'lightgrey'
        self.re_New_mod[1][1][0].height = 625
        self.re_New_mod[1][0][0].background = 'lightgrey'
        self.re_New_mod[1][0][0].height = 625
        self.re_New_mod[0].width = 1500
        self.re_New_mod[0].background = 'black'
        self.re_New_mod[0][0].style = {'color':'white'}
        self.re_New_mod[0][0].margin = (7,5,5,25)
        self.re_New_mod[0][1].margin = (12,5,5,5)
        self.re_New_mod[1][2][0][3].margin = (5,5)
        #More configurations
        self.re_New_mod[1][2][1].margin = (10,50)
        self.re_New_mod[1][2][0].background = 'whitesmoke'
        for el in self.re_New_mod[1][2][0]:
            el.margin = (5,10)
        self.re_New_mod[1][2][2][0].margin = (5,15)
        #NOw let's return it
        return self.re_New_mod
    #Launcher Buttons controls
    ''' #Deprecated .....when the model constructor was a standalone app
    def _callback_create_model_panel(self,event):
        self.panel_mod.show(title = 'Model Constructor',\
            threaded = True,verbose = False)
        
    def _callback_create_analyser_panel(self,event):
        self.panel_analysis.show(title = 'Fitting Analyser',\
            threaded = True,verbose = False)
        
    def _callback_modified_model_creator(self,event):
        self.panel_new_mod.show(title = 'Modified Model Constructor',\
            threaded = True,verbose = False)
        
    def _app_building(self):
        self.button_model_constructor    = pn.widgets.Button(name = 'Model Constructor')
        self.button_analyser_constructor = pn.widgets.Button(name = 'Analysis Tab')
        self.button_new_model_creator    = pn.widgets.Button(name = 'Modified model creator')
        self.button_model_constructor.button_type = 'success'
        self.button_analyser_constructor.button_type = 'warning'
        self.button_new_model_creator.button_type = 'warning'
        self.button_new_model_creator.disabled = True
        self.button_model_constructor.on_click(self._callback_create_model_panel)
        self.button_analyser_constructor.on_click(self._callback_create_analyser_panel)
        self.button_new_model_creator.on_click(self._callback_modified_model_creator)
        
        self.app_HUB = pn.Column(pn.pane.Markdown('## Main HUB control',style = {'color':'white'}),\
            pn.pane.Markdown('#### Wellcome to Oxispy,<br>the ultimate FREE NLLS tool for ELNES analysis',\
                style = {'color':'white'}),\
            self.button_model_constructor,\
            pn.Column(self.button_analyser_constructor,self.button_new_model_creator,margin = (5,10),\
                background = 'black'),
            margin = (10,10),background = 'black',height = 725,width = 400)
        self.app_HUB.margin = 0
        self.app_HUB[1].margin = (5,15)
        self.app_HUB[0].margin = (5,15)
        self.panel_mod      = self._model_panel_constructor()
        self.panel_analysis = self._result_analysis_panel_construction()
        self.panel_new_mod  = self._new_model_panel_constructor()
        #self.tab_app = pn.Tabs(('Model',self.panel_mod),('Results',self.panel_analysis),tabs_location='left',dynamic = True)
        self.app_HUB.show(title = 'Main HUB',threaded = True,verbose = False)
    '''
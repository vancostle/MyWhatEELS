import sys
import time
import json
from time import sleep
import os
import hyperspy.api as hs
import holoviews as hv
from holoviews import streams, opts, dim
from holoviews.streams import Stream,param
import hvplot.xarray
import panel as pn
import pandas as pd
import bokeh, param
from bokeh.models import HoverTool

import copy as cp
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from random import choice
#From out own created library
from Library.saving_routines import Saving_panel
from Library.visual_displays import Visual_distance_results,Visual_WL_ratio
from Library.visual_displays import Visual_distance_results_SLines
from Library.quantification_tool import Quantification_app
from Library.visual_displays import formatter,formatter2,formatter3,formatter4

from Library.physical_constants import R, a0, m0

hv.extension("bokeh",logo = False)
print('Importing - Results analyser for NLLS fittings : panels and tools')
try:
    root_css = [el for el in sys.path if r'\Library\css' in el][0]
except Exception as e:
    print('No root for css found. Skipping loading')
    print(e)
else:
    css_file = '{}\\css_styling.css'.format(root_css)
    if css_file not in pn.config.css_files:
        pn.config.css_files.append(css_file)

def change_extension():
    sleep(5)
    hv.extension('bokeh')
    
def hooks_plotly_surfaces1(plot,element):
        plot.handles['layout']['scene'] =\
        dict(xaxis = dict(backgroundcolor="lightgray",gridcolor="white",\
            showbackground=True,zerolinecolor="red",zerolinewidth = 1,\
            tickfont={'color':'indianred'},spikecolor ='indianred'),\
        yaxis = dict(backgroundcolor='whitesmoke',gridcolor="white",\
            showbackground=True,zerolinecolor="blue",zerolinewidth = 1,\
            tickfont={'color':'slateblue'},
            spikecolor = 'slateblue'),\
        zaxis = dict(backgroundcolor='darkgrey',gridcolor="white",\
            showbackground=True,zerolinecolor="green",zerolinewidth = 1,\
            tickfont={'color':'limegreen'},spikecolor ='limegreen'),\
        xaxis_title='\u03b5 /R',\
        yaxis_title = 'log(q \u22c5 a\u2080)\u00b2',\
        zaxis_title = 'd\u00b2f / (dEdq)',\
        aspectmode = 'manual',aspectratio = {'x':1,'y':1,'z':0.66})
        plot.handles['layout']['margin'] = dict(r=0, l=50, b=30, t=0)
        plot.handles['layout']['scene_camera'] = dict(eye=dict(x=1.3, y=1.3, z=1), center=dict(x=0, y=0, z=-0.1))
        #plot.handles['fig']['layout']['zaxis'] = {'hoverlabel':'right'}
        print(plot.handles['layout']['title'])
        
        
def hooks_plotly_surfacesf(plot,element):
        plot.handles['layout']['scene'] =\
        dict(xaxis = dict(backgroundcolor="lightgray",gridcolor="white",\
            showbackground=True,zerolinecolor="red",zerolinewidth = 1,\
            tickfont={'color':'indianred'},spikecolor ='indianred'),\
        yaxis = dict(backgroundcolor='whitesmoke',gridcolor="white",\
            showbackground=True,zerolinecolor="blue",zerolinewidth = 1,\
            tickfont={'color':'slateblue'},
            spikecolor = 'slateblue'),\
        zaxis = dict(backgroundcolor='darkgrey',gridcolor="white",\
            showbackground=True,zerolinecolor="green",zerolinewidth = 1,\
            tickfont={'color':'limegreen'},spikecolor ='limegreen'),\
        xaxis_title='\u03b5 /R',\
        yaxis_title = 'log(q \u22c5 a\u2080)\u00b2',\
        zaxis_title = 'F-factor [a.u.]',\
        aspectmode = 'manual',aspectratio = {'x':1,'y':1,'z':0.66})
        plot.handles['layout']['margin'] = dict(r=0, l=50, b=30, t=0)
        plot.handles['layout']['scene_camera'] = dict(eye=dict(x=1.3, y=1.3, z=1), center=dict(x=0, y=0, z=-0.1))
        #plot.handles['fig']['layout']['zaxis'] = {'hoverlabel':'right'}
        print(plot.handles['layout']['title'])


class Results_panel(param.Parameterized):
    active_dataset = param.ObjectSelector(objects=['First-Fit','Modified-Fit'])
    overlay_clust = param.Boolean(default=False)
    colormaps_xi = param.ObjectSelector(default='jet',objects=['jet'])
    #charact_active_dataset = param.String('None')
    #Now some parameters for the 3D bethe surfaces
    elems_gos = param.ObjectSelector()
    subshell = param.ObjectSelector()
    surfaces = param.ListSelector(['theoretical'],\
    objects=['theoretical','beta-cut','F-factor','beta-F'])

    def __init__(self,ds,ds_first = None,ds_modi = None,colores = dict(),\
        elementos_li = list(),onsets = dict(),gos_dictionaries = dict(),\
        gos_functions = dict(),gos_scales = dict(),dataset_type = 'SIm',from_saved = False):
        super().__init__()
        self.dataset_type = dataset_type
        self.gos_data_dict = gos_dictionaries
        self.gos_functions = gos_functions
        self.gos_scalings  = gos_scales
        self.onsets = onsets
        self.ds = ds
        #For the hovertip tool
        '''
        TT_xi = [("Reduced \u03c7\u00b2","@ReducedChiSquare"),\
            ("Pixel #","@y")]
        TT_clust = [("Cluster #","@ClustersMatrix"),\
            ("Pixel #","@y")]
        self.hover_tipXi = HoverTool(tooltips=TT_xi,mode='hline')
        self.hover_tipclust = HoverTool(tooltips=TT_clust,mode='hline')
        
        TT = [("Line","@y"),\
            ("Cluster","@ClustersMatrix"),\
            ("Reduced-Chi Squared","@ReducedChiSquare")]
        self.custom_hover = HoverTool(tooltips=TT)
        '''
        if self.dataset_type == 'SIm':
            xsize = self.ds.x.values.size
            ysize = self.ds.y.values.size
            dist = abs(ysize-xsize)
            if xsize < ysize:
                self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
                self.ylims = (-0.5,ysize-0.5)
            else:
                self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
                self.xlims = (-0.5,xsize-0.5)
        else:
            pass
        self.elements_list = elementos_li
        self.param['elems_gos'].objects = elementos_li
        self.elems_gos = elementos_li[0]
        #colormaps for the clustering representation
        self.cmap_clust = []
        if len(colores.keys()) > 1:
            for el in colores:
                if el != 'default':
                    self.cmap_clust.append(colores[el])
                else: pass
        else:
            self.cmap_clust = ['black','aquamarine']
        self.colores = colores
        #Buttons to launch apps
        self.button_center_analysis = pn.widgets.Button(name = 'Center Analysis',\
            disabled = True,width = 140,margin = (5,5,5,10),\
            css_classes = ['custom_button_bokeh_black_inter'])
        self.button_center_analysis.on_click(self._launch_center_analysisTOOL)
        self.button_WL_analysis = pn.widgets.Button(name = 'WL Analysis',\
            disabled = True,width = 140,margin = (5,0),\
            css_classes = ['custom_button_bokeh_black_inter'])
        self.button_WL_analysis.on_click(self._launch_wl_analysisTOOL)
        self.button_quantification = pn.widgets.Button(name = 'Quantification',\
            disabled = True,width = 140,margin = (5,10,5,5),\
            css_classes = ['custom_button_bokeh_black_inter'])
        self.button_quantification.on_click(self._launch_quant_analysisTOOL)
        #Saving and loading buttons
        self.button_save_workspace = pn.widgets.Button(name = 'Save-Multifit',\
            button_type = 'default',width = 180,margin = (5,10,5,35),\
            css_classes = ['custom_button_bokeh_black_inter',\
            'custom_button_bokeh_black_inter_dis'])
        self.button_save_workspace.on_click(self._callback_save_results_workspace)
        if from_saved:
            #So we cannot overwrite the directory
            self.button_save_workspace.button_type = 'danger'
            self.button_save_workspace.disabled = True
        self.button_save_data = pn.widgets.Button(name = 'Save-Data-Images',\
            button_type = 'default',width = 180,margin = (5,35,5,10),\
            css_classes = ['custom_button_bokeh_black_inter',\
            'custom_button_bokeh_black_inter_dis'])
        self.button_save_data.on_click(self._callback_save_data_im)
        #Some more objects for the functionality
        self.message_selection_first =\
            pn.pane.Markdown('### Selected pixel |- x : \u2205 -|- y : \u2205 -|',\
            width = 500,style = {'color':'grey'})
        self.message_selection_modif =\
            pn.pane.Markdown('### Selected pixel |- x : \u2205 -|- y : \u2205 -|',\
            width = 500,style = {'color':'grey'})
        self.message_selection_SL =\
            pn.pane.Markdown('### Selected Line |- # position : \u2205 -|',\
            width = 500,style = {'color':'grey'})
        self.overlay_clust_wid = pn.Param(self.param['overlay_clust'],\
            widgets = {'overlay_clust':pn.widgets.Toggle},\
            parameters = ['overlay_clust'],\
            show_name = False,show_labels = False,\
            width = 185,margin = (25,15,5,10),height = 30)
        self.overlay_clust_wid[0].disabled = True
        self.overlay_clust_wid[0].name = 'Overlay Clusters'
        self.overlay_clust_wid[0].margin = 0
        self.overlay_clust_wid[0].width = 185
        self.overlay_clust_wid[0].height = 30
        if self.dataset_type == 'SIm':
            self.hov_lims = (self.ds.x.values[0]-0.5,self.ds.x.values[-1]+\
                    0.5,self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        elif self.dataset_type == 'SLi':
            self.hov_lims = (self.ds.Eloss.values[0],self.ds.Eloss.values[-1],\
            self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        self.dataset_widget = pn.Param(self.param['active_dataset'],\
            widgets = {'active_dataset':pn.widgets.RadioButtonGroup},\
            parameters = ['active_dataset'],\
            show_name = False,show_labels = False,\
            width = 275,margin = 5)
        self.dataset_widget[0].width = 275
        self.dataset_widget[0].margin = 0
        #We extend the possible colormaps to be selected
        lista_cmaps = ['jet']
        lista_cmaps.extend(hv.plotting.util.list_cmaps(category='Uniform Sequential'))
        self.param['colormaps_xi'].objects = lista_cmaps
        self.colormap_sel = pn.Param(self.param['colormaps_xi'],\
            widgets = {'colormaps_xi':pn.widgets.Select},\
            parameters = ['colormaps_xi'],name = 'Select cmap',show_name = True,\
            show_labels = False,margin = (0,25,0,15),width = 185)
        self.colormap_sel[1].disabled = True
        self.colormap_sel[0].style = {'color':'white'}
        self.colormap_sel[0].margin = (5,0,0,0)
        self.colormap_sel[1].height = 30
        self.colormap_sel[1].width  = 185
        self.colormap_sel[1].margin = 0
        '''
        self.message_active_dataset = pn.pane.Markdown(\
            '### Active dataset : {}'.format('None'),\
            style = {'color':'lightgrey'},width = 215,\
            align = 'center',margin = (0,5))
        '''
        #We prepare the important empty data structures
        if self.dataset_type == 'SIm':
            #Espectrum images reasults panel contruction pipeline
            self._ready_empty_data_SI()
            self._loading_SI(ds_first,ds_modi)
            self._panel_construction_SI()
        elif self.dataset_type == 'SLi':
            #Espectrum lines reasults panel contruction pipeline
            self._ready_empty_data_SL()
            self._loading_SL(ds_first)
            self._panel_construction_SL()
        else:
            #At this point ... not having an actual panel to load means 
            #an automatic raise of error
            raise ValueError('No valid dataset was introduced. SI or SL are expected')
        
        #Some extra configurations for the Bethe-surface launch system
        self.button_show_surfaces = pn.widgets.Button(name = 'Inspect Bethe surfaces',\
            align = 'start',button_type = 'warning',margin = (5,10))
        self.button_show_surfaces.on_click(self._callback_show_bethe)
        self.surface_select_wid = pn.Param(self.param['surfaces'],\
            widgets = {'surfaces':pn.widgets.MultiChoice},\
            parameters = ['surfaces'],width = 400,height = 125,align = 'center',\
            show_name = True, name = 'Choose the 3D surfaces to display',\
            show_labels = False)
        self.surface_select_wid[1].width = 375
        self.surface_select_wid[0].style = {'color':'white'}
        self.surface_select_wid[1].margin = (5,0)
        self.surface_select_wid[0].margin = 5
        #self.surface_select_wid[1].height = 125
        self.elementos_gos_wid = pn.Param(self.param['elems_gos'],\
            widgets = {'elems_gos':pn.widgets.RadioButtonGroup},\
            parameters = ['elems_gos'],show_labels = False,show_name = False,\
            width = 400,align = 'center')
        self.elementos_gos_wid[0].width = 350
        self.elementos_gos_wid[0].align = 'center'
        self.elementos_gos_wid[0].margin = (0,20)
        self.sshells_gos_wid = pn.Param(self.param['subshell'],\
            widgets = {'subshell':pn.widgets.RadioButtonGroup},\
            parameters = ['subshell'],show_labels = False,show_name = False,\
            width = 400,align = 'center')
        self.sshells_gos_wid[0].width = 350
        self.sshells_gos_wid[0].align = 'center'
        self.sshells_gos_wid[0].margin = (0,20)

    def _callback_save_data_im(self,event):
        #Let's get the ds
        if self.ds_modi:
            dsm = self.ds_modi.rename(dict([(el,'{}_modif'.format(el)) for el in self.ds_modi.data_vars]))
            dsv = xr.merge([self.ds_first,dsm])
            dsv.attrs = self.ds_first.attrs
        else:
            dsv = self.ds_first.copy(deep = True)
        sv = Saving_panel(dsv,name_panel= 'results',\
        figures=[hv.Image.clone(self.im_first,link=False),self.din_first,self.din_first_best],\
        figures_names = ['RedXiSq','Residual','BestFit'])
        sv.create_layout()
        

    def _callback_save_results_workspace(self,event):
        #Folder navigation and creation
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
        time_string = '{}_{}'.format(time.strftime('%Y%b%d',time.gmtime()),\
                time.strftime('%H\'%M\'%S',time.gmtime()))
        folder_save = 'MultifitResults-{}'.format(time_string)
        if folder_save not in os.listdir('./Savings-Workspace/{}'.format(name)):
            os.mkdir('./Savings-Workspace/{}/{}'.format(name,folder_save))
        #NOw, let's pile the whole data to be saved....and save it already
        if self.ds_modi:
            clave = 'multiple'
        else:
            clave = 'single'
        #Let's create the full dictionary for a json object
        list_4_json = {'fittings_available':clave,'elements':self.elements_list,\
            'gos_sacalings':self.gos_scalings,'onsets':self.onsets,\
            'colors':self.colores,'dataset_type':self.dataset_type}
        json_name = './Savings-Workspace/{}/{}/results_config.json'.format(name,folder_save)
        with open(json_name,'w') as jf:
            json.dump(list_4_json,jf)
        #Now the rest of the data
        #The xarray datasets
        ds_fst_name = './Savings-Workspace/{}/{}/ds_first.nc'.format(name,folder_save)
        ds_mod_name = './Savings-Workspace/{}/{}/ds_modi.nc'.format(name,folder_save)
        ds_name     = './Savings-Workspace/{}/{}/ds.nc'.format(name,folder_save)
        self.ds_first.to_netcdf(path = ds_fst_name,format="NETCDF4")
        self.ds.to_netcdf(path = ds_name,format="NETCDF4")
        if self.ds_modi:
            self.ds_modi.to_netcdf(path = ds_mod_name,format="NETCDF4")
        #And now the rest ... the gos dictionaries and functions - we use numpy for that
        gos_f_name = './Savings-Workspace/{}/{}/gos_func.npy'.format(name,folder_save)
        gos_d_name = './Savings-Workspace/{}/{}/gos_dict.npy'.format(name,folder_save)
        np.save(gos_f_name,np.array(self.gos_functions))
        np.save(gos_d_name,np.array(self.gos_data_dict))
        self.button_save_workspace.button_type = 'danger'
        self.button_save_workspace.disabled = True

    def _panel_construction_SI(self):
        #this method builds the panel for the graphs display (red_xi_sq and cluster overlays)
        row_1 = pn.Row(pn.Spacer(width = 20,height = 225),self.ima_place1,self.din_place1)
        row_2 = pn.Row(pn.Spacer(width = 20,height = 225),self.ima_place2,self.din_place2)
        self.graph_panel = pn.Column(\
            pn.Row(pn.pane.Markdown(\
                '### First fit - Reduced Chi Squared and Residuals \u03c7\u00b2',\
                width = 500,margin = (5,0,0,25)),\
                self.message_selection_first),\
            row_1,\
            pn.Row(pn.pane.Markdown(\
                '### Modified fit - Reduced Chi Squared and Residuals \u03c7\u00b2',\
                width = 500,margin = (5,0,0,25)),\
                self.message_selection_modif),\
            row_2,\
            width = 1200)
        # Parameters for the visualization - dual set of dynamic maps at the same time
        self.bol1 = True
        self.bol2 = True
        self.bol1_ori = True
        self.bol2_ori = True
        self.bol1_best = True
        self.bol2_best = True

    def _panel_construction_SL(self):
        '''Method for the construction of the visualization
        panel for the spectrum lines.
        In principle, with spectrum lines we won't ever have a re-run
        and thus we only need half of the items compared to the 
        SI case 
        '''
        #row_1 = pn.Row(self.ima_place1,self.din_place1)
        #row_2 = pn.Row(pn.Spacer(width = 20,height = 225),self.ima_place2,self.din_place2)
        self.graph_panel = pn.Column(\
            pn.Row(pn.pane.Markdown(\
                '### Reduced Chi Squared and Residuals \u03c7\u00b2',\
                width = 500,margin = (5,0,0,25)),\
                self.message_selection_SL,width = 1000,margin = 0),\
            self.ima_place1,self.din_place1,\
            width = 1200,margin = (0,15))
        

    def _ready_empty_data_SI(self):
        empty_Data = xr.Dataset({'EmptyData':(['y','x','Eloss'],\
        np.zeros_like(self.ds.ElectronCount.values))},\
        coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
        'Eloss':self.ds.Eloss.values})
        self.im_empty = hv.Image(empty_Data.EmptyData.sum('Eloss'))\
        .opts(cmap = self.colormaps_xi,invert_yaxis=True,\
            xaxis = None,yaxis = None,toolbar = 'below',shared_axes = False,\
            xlim = self.xlims,ylim = self.ylims,\
            aspect = 'equal',frame_height = 225,\
            colorbar = True,colorbar_position = 'right')
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
            framewise = True,yformatter=formatter,show_grid = True,\
            xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
        '''
        self.scatter_empty = hv.Scatter(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 225,frame_width = 500,show_grid = True,\
            yformatter=formatter4,shared_axes = False,framewise = True)
        '''
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
            framewise = True,yformatter=formatter,show_grid = True,\
            xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black')
        #Finished the creation of the empty_datasets

    def _ready_empty_data_SL(self):
        #Method to create the empty data estructures here
        empty_Data = xr.Dataset({'EmptyData':(['y','x','Eloss'],\
        np.zeros_like(self.ds.ElectronCount.values))},\
        coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
        'Eloss':self.ds.Eloss.values})
        self.im_empty = hv.Image(empty_Data.EmptyData,kdims=['Eloss','y'])\
            .opts(ylabel = 'Pixel #',xlabel ='Electron Energy Loss [eV]',\
            cmap = self.colormaps_xi,colorbar = True,shared_axes = False,\
            colorbar_opts = {'height':25,'major_label_text_color':'black',\
            #'major_label_text_font_style':'italic',\
            'border_line_alpha':1,'label_standoff':-15,'scale_alpha':1,\
            'major_tick_line_width':2,'padding':15,\
            'bar_line_width':0,'bar_line_color':'white'},\
            colorbar_position = 'top',frame_height = 125,frame_width = 850,\
            yformatter=formatter)
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
            framewise = True,yformatter=formatter,show_grid = True,\
            xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
            framewise = True,yformatter=formatter,show_grid = True,\
            xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black')
        '''
        self.im_empty = hv.Image(empty_Data.EmptyData,kdims = ['Eloss','y'])\
        .opts(cmap = self.colormaps_xi,invert_yaxis=True,\
            toolbar = 'below',shared_axes = False,ylabel = 'Pixel #',\
            frame_height = 75,\
            colorbar = True,colorbar_position = '')
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 225,frame_width = 500,show_grid = True,\
            shared_axes = False,yformatter=formatter)
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 225,frame_width = 500,show_grid = True,\
            shared_axes = False,yformatter=formatter,\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black')
        '''

    @param.depends('elems_gos',watch = True)
    def _change_available_sshells(self):
        self.param['subshell'].objects =\
        list(self.gos_data_dict[self.elems_gos].keys())
        self.subshell = self.param['subshell'].objects[0]
        
    @param.depends('colormaps_xi',watch = True)
    def _change_cmap(self):
        if self.dataset_type == 'SIm':
            self.ima_place1.object = self.ima_place1.object.opts(cmap = self.colormaps_xi)
            self.ima_place2.object = self.ima_place2.object.opts(cmap = self.colormaps_xi)
        elif self.dataset_type == 'SLi':
            self.ima_place1.object =\
                self.im_SL+self.clust_bar+self.im_first.opts(cmap = self.colormaps_xi)
                
    
    @param.depends('overlay_clust',watch = True)
    def _overlay_clust(self):
        if self.overlay_clust:
            #We disable the cmap changes and set the camps as greys for optimum overlay
            self.colormap_sel[1].disabled = True
            self.overlay_clust_wid[0].button_type = 'warning'
            self.overlay_clust_wid[0].name  = 'Loading - wait'
            self.overlay_clust_wid[0].disabled = True
            #We have to know which places we want to overlay
            if self.ds_modi != None and self.ds_first != None:
                self.ima_place1.object = self.ima_place1.object\
                    .opts(cmap = 'greys_r',colorbar = False)*self.hmap
                self.ima_place2.object = self.ima_place2.object\
                    .opts(cmap = 'greys_r',colorbar = False)*self.hmap
            elif self.ds_first != None:
                self.ima_place1.object = self.ima_place1.object\
                    .opts(cmap = 'greys_r',colorbar = False)*self.hmap
            elif self.ds_modi != None:
                self.ima_place2.object = self.ima_place2.object\
                    .opts(cmap = 'greys_r',colorbar = False)*self.hmap
            else: pass
            self.overlay_clust_wid[0].button_type = 'success'
            self.overlay_clust_wid[0].name  = 'Overlay Clusters'
            self.overlay_clust_wid[0].disabled = False
        else:
            #We allow once again color changes in the cmap
            self.overlay_clust_wid[0].button_type = 'warning'
            self.overlay_clust_wid[0].name  = 'Loading - wait'
            self.overlay_clust_wid[0].disabled = True
            if self.ds_modi != None and self.ds_first != None:
                self.ima_place1.object = self.im_first\
                    .opts(cmap = self.colormaps_xi,colorbar = True)
                self.ima_place2.object = self.im_modi\
                    .opts(cmap = self.colormaps_xi,colorbar = True)
            elif self.ds_first != None:
                self.ima_place1.object = self.im_first\
                    .opts(cmap = self.colormaps_xi,colorbar = True)
            elif self.ds_modi != None:
                self.ima_place2.object = self.im_modi\
                    .opts(cmap = self.colormaps_xi,colorbar = True)
            else: pass
            self.colormap_sel[1].disabled = False
            self.overlay_clust_wid[0].button_type = 'primary'
            self.overlay_clust_wid[0].name  = 'Overlay Clusters'
            self.overlay_clust_wid[0].disabled = False
    
    def plot_residual_SL(self,x,y):
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            self.message_selection_SL.object =\
            '### Selected Line |- # position : \u2205 -|'
            self.message_selection_SL.style = {'color':'grey'}
            return self.curve_empty
        elif y >= yf or y <= yi:
            self.message_selection_SL.object =\
            '### Selected Line |- # position : \u2205 -|'
            self.message_selection_SL.style = {'color':'grey'}
            return self.curve_empty
        else:
            E0,y0 = self.im_first.closest((x,y))
            self.message_selection_SL.object =\
            '### Selected Line |- # position : {} -|'.format(int(y0))
            self.message_selection_SL.style = {'color':'green'}
            curva = hv.Curve(self.ds_first.Residuals.isel(x = 0,y = int(y0)))\
                .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_width=1.,line_alpha = 1,line_color = 'red')
            return curva

    def plot_best_SL(self,x,y):
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.curve_empty
        elif y >= yf or y <= yi:
            return self.curve_empty
        else:
            E0,y0 = self.im_first.closest((x,y))
            #Dinmaps changes
            curva = hv.Curve(self.ds_first.BestFit.isel(x = 0,y = int(y0)))\
                .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_width=2.,line_alpha = 1,line_color = 'limegreen')
            return curva
    
    def plot_ori_SL(self,x,y):
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            E0,y0 = self.im_first.closest((x,y))
            #Dinmaps changes
            area = hv.Area(self.ds_first.OriginalData.isel(x = 0,y = int(y0)))\
                .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_alpha = 0,fill_color = 'grey',fill_alpha = 0.5)
            return area

    def plot_residual_first(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            self.message_selection_first.object =\
            '### Selected pixel |- x : \u2205 -|- y : \u2205 -|'
            self.message_selection_first.style = {'color':'grey'}
            return self.curve_empty
        elif y >= yf or y <= yi:
            self.message_selection_first.object =\
            '### Selected pixel |- x : \u2205 -|- y : \u2205 -|'
            self.message_selection_first.style = {'color':'grey'}
            return self.curve_empty
        else:
            self.bol1 = False
            if self.bol2:
                try:
                    self.din_modi.event(x = x, y = y)
                except:
                    pass
            x0,y0 = self.im_first.closest((x,y))
            self.message_selection_first.object =\
            '### Selected pixel |- x : {} -|- y : {} -|'.format(x0,y0)
            self.message_selection_first.style = {'color':'red'}
            #Dinmaps changes
            curva = hv.Curve(self.ds_first.Residuals.isel(x = int(x0),y = int(y0)))\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_width=1.,\
                line_alpha = 1,line_color = 'red')
            self.bol1 = True
            return curva
            
    
    def plot_residual_modi(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            self.message_selection_modif.object =\
            '### Selected pixel |- x : \u2205 -|- y : \u2205 -|'
            self.message_selection_modif.style = {'color':'grey'}
            return self.curve_empty
        elif y >= yf or y <= yi:
            self.message_selection_modif.object =\
            '### Selected pixel |- x : \u2205 -|- y : \u2205 -|'
            self.message_selection_first.style = {'color':'grey'}
            return self.curve_empty
        else:
            self.bol2 = False
            if self.bol1:
                try:
                    self.din_first.event(x = x, y = y)
                except:
                    pass
            x0,y0 = self.im_modi.closest((x,y))
            self.message_selection_modif.object =\
            '### Selected pixel |- x : {} -|- y : {} -|'.format(x0,y0)
            self.message_selection_modif.style = {'color':'red'}
            curva = hv.Curve(self.ds_modi.Residuals.isel(x = int(x0),y = int(y0)))\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_width=1.,line_alpha = 1,line_color = 'red')
            self.bol2 = True
            return curva
            
    def plot_best_modi(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.curve_empty
        elif y >= yf or y <= yi:
            return self.curve_empty
        else:
            self.bol2_best = False
            if self.bol1_best:
                try:
                    self.din_first_best.event(x = x, y = y)
                except:
                    pass
            x0,y0 = self.im_modi.closest((x,y))
            curva = hv.Curve(self.ds_modi.BestFit.isel(x = int(x0),y = int(y0)))\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_width=2.,line_alpha = 1,\
                line_color = 'limegreen')
            self.bol2_best = True
            return curva
    
    def plot_best_first(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.curve_empty
        elif y >= yf or y <= yi:
            return self.curve_empty
        else:
            self.bol1_best = False
            if self.bol2_best:
                try:
                    self.din_modif_best.event(x = x, y = y)
                except:
                    pass
            x0,y0 = self.im_first.closest((x,y))
            #Dinmaps changes
            curva = hv.Curve(self.ds_first.BestFit.isel(x = int(x0),y = int(y0)))\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',\
                show_title=False,line_width=2.,line_alpha = 1,line_color = 'limegreen')
            self.bol1_best = True
            return curva
        
    def plot_ori_first(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            self.bol1_ori = False
            if self.bol2_ori:
                try:
                    self.din_modif_ori.event(x = x, y = y)
                except:
                    pass
            x0,y0 = self.im_first.closest((x,y))
            #Dinmaps changes
            area = hv.Area(self.ds_first.OriginalData.isel(x = int(x0),y = int(y0)))\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',
                show_title=False,line_alpha = 0,fill_color = 'grey',fill_alpha = 0.5)
            self.bol1_ori = True
            return area
        
    def plot_ori_modi(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            self.bol2_ori = False
            if self.bol1_ori:
                try:
                    self.din_first_ori.event(x = x, y = y)
                except:
                    pass
            x0,y0 = self.im_modi.closest((x,y))
            area = hv.Area(self.ds_modi.OriginalData.isel(x = int(x0),y = int(y0)))\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]',
                show_title=False,line_alpha = 0,fill_color = 'grey',fill_alpha = 0.5)
            self.bol2_ori = True
            return area

    def _create_surface_data_structures(self):
        #Method that creates the DataSet structures for the diplay of Bethe surfaces
        dictio_for_dataset = dict()
        titles = dict()
        cmaps_surf = dict()
        #self.subshell.split('_')[0]
        for surf in list(self.surfaces):   
            ['theoretical','beta-cut','F-factor','beta-F']
            #We prepare the correct identification keywords-to be used as 
            if surf == 'theoretical':
                title = 'Bethe Surface'
                cmp = 'autumn_r'
            elif surf == 'beta-cut':
                title = 'Bethe Surface \u03b2-Truncated'
                #cmp ='YlGn'
                cmp = 'winter_r'
            elif surf == 'F-factor':
                title = 'Geometric Correction F-factor'
                #cmp ='OrRd'
                cmp = 'spring_r'
            elif surf == 'beta-F':
                title = 'Bethe Surface \u03b2-Truncated .and. F-Corrected'
                cmp = 'summer_r'
            else:
                title = 'Unknown surface ?'  
                cmp = 'jet'
            clave = ' '.join([self.subshell,surf])
            dictio_for_dataset[clave] =\
            (['Qax','Eax'],np.transpose(self.gos_data_dict[self.elems_gos][self.subshell][surf]))
            titles[clave] = title
            cmaps_surf[clave] = cmp
        coordis = {'Eax':self.gos_data_dict[self.elems_gos][self.subshell]['Eax'],\
            'Qax':self.gos_data_dict[self.elems_gos][self.subshell]['Qax']}
        dictio_atts = {'titles':titles,'cmaps':cmaps_surf}
        ds_surf = xr.Dataset(dictio_for_dataset,coords=coordis,attrs=dictio_atts)
        return ds_surf
    
    def _callback_show_bethe(self,event):
        if len(self.surfaces) == 0:
            return
        else:
            #We create the surfaces to be shown and the overall structure of the panel,\
            #and we launch it threaded- so we can go back to the bokeh backend
            self.button_show_surfaces.name = 'Plotly backend - WAIT for config'
            self.button_show_surfaces.button_type = 'danger'
            self.button_show_surfaces.disabled = True
            dats_ds = self._create_surface_data_structures()
            self.dats_ds = dats_ds
            E0 = self.ds.attrs['beam_energy']
            beta_coll = self.ds.attrs['collection_angle']
            alpha_conv = self.ds.attrs['convergence_angle']
            #Now we switch on the plotly backend
            hv.extension('plotly')
            list_of_surfaces = list()
            if len(self.surfaces) >3:
                f_h = 350
                ncol_n = 2
                f_w = 500
            else:
                f_h = 400
                ncol_n = 3
                f_w = 500
                
            for surf in dats_ds:
                if 'F-factor' in surf:
                    surface = hv.Surface(dats_ds[surf])\
                        .opts(cmap = dats_ds.attrs['cmaps'][surf],\
                        hooks = [hooks_plotly_surfacesf],projection = '',\
                        alpha = 0.75,height = f_h,width = f_w)   
                else:
                    surface = hv.Surface(dats_ds[surf])\
                        .opts(cmap = dats_ds.attrs['cmaps'][surf],\
                        hooks = [hooks_plotly_surfaces1],projection = '',\
                        alpha = 0.75,height = f_h,width = f_w)
                mkdow = pn.pane.Markdown('### {}'.format(dats_ds.attrs['titles'][surf])\
                    ,align='start',margin = (5,25,-10,25),width = 500)
                list_of_surfaces.append(pn.Column(mkdow,surface,margin = (5,0)))
            gir = pn.GridBox(*list_of_surfaces,ncols=ncol_n)
            ele,shs = self.subshell.split('_')
            pan = pn.Row(pn.Column(\
                pn.pane.Markdown('# {} - {}'.format(ele,shs),\
                style = {'color':'white'},margin = 15),\
                pn.pane.Markdown('## Bethe Surfaces',\
                style = {'color':'white'},margin = 15),\
                pn.pane.Markdown('### Beam Energy<br>E\u2080 = {} keV'.format(E0),\
                style = {'color':'white'},margin = (5,15)),\
                pn.pane.Markdown('### Convergence angle<br>\u03b1 = {} mrad'.format(alpha_conv),\
                style = {'color':'white'},margin = (5,15)),\
                pn.pane.Markdown('### Collection angle<br>\u03b2 = {} mrad'.format(beta_coll),\
                style = {'color':'white'},margin = (5,15)),\
                height = 850,background = 'black',width = 150),gir,width = 1250)
            pan.show(title = '{}{} Bethe Surface'.format(ele,shs),threaded = True,verbose = False)
            #At the end, we get back the nice bokeh backend
            change_extension()
            self.button_show_surfaces.name = 'Inspect Bethe surfaces'
            self.button_show_surfaces.button_type = 'warning'
            self.button_show_surfaces.disabled = False
            

    def _extract_clustering_info(self,ref = 'st'):
        #Method to prepare the clustering info and heatmap
        if ref == 'st':
            maxi_clst = np.unique(self.ds_first.ClustersMatrix.values).size - 0.5
            mini_clst = -0.5
            self.hmap  = hv.HeatMap(self.ds_first.ClustersMatrix)\
                .opts(colorbar=True,line_width=1,line_alpha = 1,\
                alpha=0.25,cmap=self.cmap_clust,line_color = 'ClustersMatrix',\
                invert_yaxis = True,aspect='equal',xaxis=None,yaxis=None,\
                xlim = self.xlims,ylim = self.ylims,\
                clim = (mini_clst,maxi_clst))
            self.overlay_clust_wid[0].disabled = False
            self.overlay_clust_wid[0].button_type = 'primary'
        elif ref == 'mod':
            maxi_clst = np.unique(self.ds_modi.ClustersMatrix.values).size - 0.5
            mini_clst = -0.5
            self.hmap  = hv.HeatMap(self.ds_modi.ClustersMatrix)\
                .opts(colorbar=True,line_width=1,line_alpha = 1,\
                alpha=0.25,cmap=self.cmap_clust,line_color = 'ClustersMatrix',\
                invert_yaxis = True,aspect='equal',xaxis=None,yaxis=None,\
                xlim = self.xlims,ylim = self.ylims,\
                clim = (mini_clst,maxi_clst))
            self.overlay_clust_wid[0].disabled = False
            self.overlay_clust_wid[0].button_type = 'primary'
        else: return #Do nothing and do not activate the clustering overlay option
    
    def _loading_SL(self,ds_first):
        self.din_place1 = pn.pane.HoloViews(self.curve_empty)
        #self.din_place2 = pn.pane.HoloViews(self.curve_empty)
        self.ima_place1 = pn.pane.HoloViews(self.im_empty)
        #self.ima_place2 = pn.pane.HoloViews(self.im_empty)
        self.dataset_widget[0].disabled = True
        if type(ds_first) == xr.core.dataset.Dataset:
            self.colormap_sel[1].disabled = False
            self.ds_first = ds_first
            #maxi = np.nanmax(self.ds_first.ReducedChiSquare.values)
            #mini = np.nanmin(self.ds_first.ReducedChiSquare.values)
            self.active_dataset = 'First-Fit'
            #Let's create the clusters matrix
            TT = [("Line","$y"),\
            ("Cluster","@ClustersMatrix"),\
            ("Reduced-Chi Squared","@ReducedChiSquare")]
            self.custom_hover = HoverTool(tooltips=TT)
            '''
            maxi_clst = np.unique(self.ds_first.ClustersMatrix.values).size - 0.5
            mini_clst = -0.5
            self.hmap  = hv.HeatMap(self.ds_first.ClustersMatrix)\
                .opts(colorbar=True,line_width=1,line_alpha = 1,\
                alpha=0.25,cmap=self.cmap_clust,line_color = 'ClustersMatrix',\
                invert_yaxis = True,aspect='equal',xaxis=None,yaxis=None,\
                xlim = self.xlims,ylim = self.ylims,\
                clim = (mini_clst,maxi_clst))
            self.overlay_clust_wid[0].disabled = False
            self.overlay_clust_wid[0].button_type = 'primary'
            self._extract_clustering_info(ref = 'st')
            '''
            '''
            self.im_first = hv.Image(self.ds_first.ReducedChiSquare,kdims = ['Eloss','y'])\
                .opts(invert_yaxis = True,ylabel = 'Pixel #',xlabel ='Electron Energy Loss [eV]',\
                cmap = self.colormaps_xi,colorbar = True,shared_axes = False,\
                colorbar_opts = {'height':25,'major_label_text_color':'black',\
                'border_line_alpha':1,'label_standoff':-15,'scale_alpha':1,\
                'major_tick_line_width':2,'padding':15,\
                'bar_line_width':0,'bar_line_color':'white'},\
                colorbar_position = 'top',frame_height = 125,frame_width = 950,\
                yformatter=formatter,clipping_colors = {'NaN': 'black'},clim = (mini,maxi),\
                alpha = 0.5)
            '''
            self.im_first =\
            hv.Image(self.ds_first.isel(Eloss = slice(0,5)),\
            kdims = ['Eloss','y'],vdims = ['ReducedChiSquare'])\
                .opts(invert_yaxis = True,yaxis = None,xaxis = None,frame_height = 125,\
                frame_width = 50,shared_axes = False, framewise = True,\
                colorbar = True,colorbar_position = 'right',\
                colorbar_opts = {'height':100,'width':25,'major_label_text_color':'black',\
                    'border_line_alpha':0,'label_standoff':10,'scale_alpha':1,\
                    'major_tick_line_width':2,'padding':15,\
                    'bar_line_width':0,'bar_line_color':'white'},\
                tools = ['hover'])
            self.im_SL =\
            hv.Image(self.ds_first,\
            kdims = ['Eloss','y'],vdims = ['OriginalData'])\
                .opts(invert_yaxis = True,ylabel = 'Pixel #',xlabel ='Electron Energy Loss [eV]',\
                cmap = 'Greys_r',shared_axes = False,\
                frame_height = 125,frame_width = 850,\
                yformatter=formatter,alpha = 1,tools = ['hover'])
            self.clust_bar  =\
            hv.Image(self.ds_first.isel(Eloss = slice(0,5)),\
            kdims = ['Eloss','y'],vdims = ['ClustersMatrix'])\
                .opts(cmap = self.cmap_clust,invert_yaxis = True,yaxis = None,xaxis = None,\
                frame_height = 125,frame_width = 50,\
                shared_axes = False, framewise = True,tools = ['hover'])
            self.stream_tap_SL = streams.SingleTap(x = -1,y = -1,source = self.im_SL)
            #self.stream_first_best = streams.SingleTap(x = -1,y = -1,source = self.im_first)
            #self.stream_first_ori = streams.SingleTap(x = -1,y = -1,source = self.im_first)
            self.din_first =\
            hv.DynamicMap(self.plot_residual_SL,streams = [self.stream_tap_SL])\
                .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_first_best =\
            hv.DynamicMap(self.plot_best_SL,streams=[self.stream_tap_SL])\
                .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_first_ori =\
            hv.DynamicMap(self.plot_ori_SL,streams=[self.stream_tap_SL])\
                .opts(frame_height = 300,shared_axes = False,frame_width = 850,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_place1.object = self.din_first_ori*self.din_first*self.din_first_best
            self.ima_place1.object = self.im_SL+self.clust_bar+self.im_first
            self.ds_modi = None
            self.button_center_analysis.disabled = False
            self.button_WL_analysis.disabled = False
            self.button_quantification.disabled = False
        else:
            #Case of not having an actual dataset to be shown
            self.colormap_sel[1].disabled = True
            self.ds_modi = None
            self.ds_first = None
            self.button_center_analysis.disabled = True
            self.button_WL_analysis.disabled = True
            self.button_quantification.disabled = True

    def _loading_SI(self,ds_first,ds_modi):
        #Initial loading
        self.din_place1 = pn.pane.HoloViews(self.curve_empty)
        self.din_place2 = pn.pane.HoloViews(self.curve_empty)
        self.ima_place1 = pn.pane.HoloViews(self.im_empty)
        self.ima_place2 = pn.pane.HoloViews(self.im_empty)
        if all([type(el) == xr.core.dataset.Dataset for el in [ds_first,ds_modi]]):
            self.dataset_widget[0].disabled = False
            self.colormap_sel[1].disabled = False
            self.active_dataset = 'First-Fit'
            self.ds_first = ds_first
            self.ds_modi = ds_modi
            #Let's create the clusters matrix
            self._extract_clustering_info(ref = 'st')
            #So they share the same colorbar
            maxi = max(np.nanmax(self.ds_first.ReducedChiSquare.values),\
                np.nanmax(self.ds_modi.ReducedChiSquare.values))
            mini = max(np.nanmin(self.ds_first.ReducedChiSquare.values),\
                np.nanmin(self.ds_modi.ReducedChiSquare.values))
            self.im_first = hv.Image(self.ds_first.ReducedChiSquare)\
            .opts(cmap = self.colormaps_xi,invert_yaxis=True,tools = ['hover'],\
                xaxis = None,yaxis = None,toolbar = 'below',shared_axes = False,\
                xlim = self.xlims,ylim = self.ylims,\
                aspect = 'equal',frame_height = 225,clipping_colors = {'NaN': 'black'},\
                colorbar = True,colorbar_position = 'right',clim = (mini,maxi))
            self.im_modi = hv.Image(self.ds_modi.ReducedChiSquare)\
            .opts(cmap = self.colormaps_xi,invert_yaxis=True,tools = ['hover'],\
                xaxis = None,yaxis = None,toolbar = 'below',shared_axes = False,\
                xlim = self.xlims,ylim = self.ylims,\
                aspect = 'equal',frame_height = 225,clipping_colors = {'NaN': 'black'},\
                colorbar = True,colorbar_position = 'right',clim = (mini,maxi))
            self.stream_first = streams.SingleTap(x = -1,y = -1,source = self.im_first)
            self.stream_modi = streams.SingleTap(x = -1,y = -1,source = self.im_modi)
            self.stream_first_best = streams.SingleTap(x = -1,y = -1,source = self.im_first)
            self.stream_modi_best = streams.SingleTap(x = -1,y = -1,source = self.im_modi)
            self.stream_first_ori = streams.SingleTap(x = -1,y = -1,source = self.im_first)
            self.stream_modi_ori = streams.SingleTap(x = -1,y = -1,source = self.im_modi)
            self.din_first = hv.DynamicMap(self.plot_residual_first,streams = [self.stream_first])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_modi = hv.DynamicMap(self.plot_residual_modi,streams = [self.stream_modi])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_first_best = hv.DynamicMap(self.plot_best_first,streams=[self.stream_first_best])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_modif_best = hv.DynamicMap(self.plot_best_modi,streams=[self.stream_modi_best])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_first_ori = hv.DynamicMap(self.plot_ori_first,streams=[self.stream_first_ori])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            self.din_modif_ori = hv.DynamicMap(self.plot_ori_modi,streams=[self.stream_modi_ori])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                framewise = True,yformatter=formatter,show_grid = True,\
                xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
            #now let's substitute the plots
            self.din_place1.object = self.din_first_ori*self.din_first*self.din_first_best
            self.din_place2.object = self.din_modif_ori*self.din_modi*self.din_modif_best
            self.ima_place1.object = self.im_first
            self.ima_place2.object = self.im_modi
            self.button_center_analysis.disabled = False
            self.button_WL_analysis.disabled = False
            self.button_quantification.disabled = False
        else:
            self.dataset_widget[0].disabled = True
            if type(ds_first) == xr.core.dataset.Dataset:
                self.colormap_sel[1].disabled = False
                self.ds_first = ds_first
                maxi = np.nanmax(self.ds_first.ReducedChiSquare.values)
                mini = np.nanmin(self.ds_first.ReducedChiSquare.values)
                self.active_dataset = 'First-Fit'
                #Let's create the clusters matrix
                self._extract_clustering_info(ref = 'st')
                self.im_first = hv.Image(self.ds_first.ReducedChiSquare)\
                .opts(cmap = self.colormaps_xi,invert_yaxis=True,tools = ['hover'],\
                    xaxis = None,yaxis = None,toolbar = 'below',shared_axes = False,\
                    xlim = self.xlims,ylim = self.ylims,\
                    aspect = 'equal',frame_height = 225,clipping_colors = {'NaN': 'black'},\
                    colorbar = True,colorbar_position = 'right',clim = (mini,maxi))
                self.stream_first = streams.SingleTap(x = -1,y = -1,source = self.im_first)
                self.stream_first_best = streams.SingleTap(x = -1,y = -1,source = self.im_first)
                self.stream_first_ori = streams.SingleTap(x = -1,y = -1,source = self.im_first)
                self.din_first = hv.DynamicMap(self.plot_residual_first,\
                    streams = [self.stream_first])\
                .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                    framewise = True,\
                    yformatter=formatter)
                self.din_first_best = hv.DynamicMap(self.plot_best_first,\
                    streams=[self.stream_first_best])
                self.din_first_ori = hv.DynamicMap(self.plot_ori_first,\
                    streams=[self.stream_first_ori])
                self.din_place1.object = self.din_first_ori*self.din_first*self.din_first_best
                self.ima_place1.object = self.im_first
                self.ds_modi = None
                self.button_center_analysis.disabled = False
                self.button_WL_analysis.disabled = False
                self.button_quantification.disabled = False
            elif type(ds_modi) == xr.core.dataset.Dataset:
                self.ds_modi = ds_modi
                self.colormap_sel[1].disabled = False
                maxi = np.nanmax(self.ds_modi.ReducedChiSquare.values)
                mini = np.nanmin(self.ds_modi.ReducedChiSquare.values)
                self.active_dataset = 'Modified-Fit'
                #Let's create the clusters matrix
                self._extract_clustering_info(ref = 'mod')
                self.im_modi = hv.Image(self.ds_modi.ReducedChiSquare)\
                .opts(cmap = self.colormaps_xi,invert_yaxis=True,tools = ['hover'],\
                    xaxis = None,yaxis = None,toolbar = 'below',shared_axes = False,\
                    xlim = self.xlims,ylim = self.ylims,\
                    aspect = 'equal',frame_height = 225,clipping_colors = {'NaN': 'black'},\
                    colorbar = True,colorbar_position = 'right',clim = (mini,maxi))
                self.stream_modi = streams.SingleTap(x = -1,y = -1,source = self.im_modi)
                self.stream_modi_best = streams.SingleTap(x = -1,y = -1,source = self.im_modi)
                self.stream_modi_ori = streams.SingleTap(x = -1,y = -1,source = self.im_modi)
                self.din_modi = hv.DynamicMap(self.plot_residual_modi,streams = [self.stream_modi])\
                    .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                    framewise = True,yformatter=formatter,show_grid = True,\
                    xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
                self.din_modif_best = hv.DynamicMap(self.plot_best_modi,streams=[self.stream_modi_best])\
                    .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                    framewise = True,yformatter=formatter,show_grid = True,\
                    xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
                self.din_modif_ori = hv.DynamicMap(self.plot_ori_modi,streams=[self.stream_modi_ori])\
                    .opts(frame_height = 225,shared_axes = False,frame_width = 500,\
                    framewise = True,yformatter=formatter,show_grid = True,\
                    xlabel = 'Electron Energy Loss [eV]',ylabel = 'Electron Counts [a.u.]')
                self.din_place2.object = self.din_modif_ori*self.din_modi*self.din_modif_best
                self.ima_place2.object = self.im_modi
                self.ds_first = None
                self.button_center_analysis.disabled = False
                self.button_WL_analysis = False
                self.button_quantification.disabled = False
            else:
                self.colormap_sel[1].disabled = True
                self.ds_modi = None
                self.ds_first = None
                self.button_center_analysis.disabled = True
                self.button_WL_analysis.disabled = True
                self.button_quantification.disabled = True
                pass

    def _launch_quant_analysisTOOL(self,event):
        if self.active_dataset == 'First-Fit':
            self.quant = Quantification_app(self.ds_first,self.gos_functions,\
                self.elements_list,self.gos_scalings)
        elif self.active_dataset == 'Modified-Fit':
            self.quant = Quantification_app(self.ds_modi,self.gos_functions,\
                self.elements_list,self.gos_scalings)
        self.quant.create_layout()
        self.quant.layout.show(title = 'Advance Quantification Tool',\
                threaded=True,verbose=False)
    
    def _launch_center_analysisTOOL(self,event):
        #This will launch the center analysis app with the current selected
        # dataset
        if self.dataset_type == 'SIm':
            if len(self.elements_list) == 0: 
                return #Safety measure - if we do not have an actual model linked
            else: pass
            #Let's get only elements with possible ratios to be measured - those with more than one
            #Component in the subshell 'bank'
            if self.active_dataset == 'First-Fit':
                self.visRes =\
                Visual_distance_results(self.ds_first,self.elements_list,self.colores)
                self.visRes.create_feature_distances_panel()
                self.visRes.distance_panel.show(title = 'Center-Eloss Analyser',\
                    threaded=True,verbose=False)
            elif self.active_dataset == 'Modified-Fit':
                self.visRes =\
                Visual_distance_results(self.ds_modi,self.elements_list,self.colores)
                self.visRes.create_feature_distances_panel()
                self.visRes.distance_panel.show(title = 'Center-Eloss Analyser',\
                    threaded=True,verbose=False)
            else:
                return
        elif self.dataset_type == 'SLi':
            if len(self.elements_list) == 0: 
                return
            else:
                self.visRes =\
                Visual_distance_results_SLines(self.ds_first,self.elements_list,self.colores)
                self.visRes.create_feature_distances_panel()
                self.visRes.distance_panel.show(title = 'Center-Eloss Analyser',\
                    threaded=True,verbose=False)

    def _launch_wl_analysisTOOL(self,event):
        if len(self.elements_list) == 0: 
            return #Safety measure - if we do not have an actual model linked
        else: pass
        #Let's pass only elements with plausible components to be comapared
        elemento_to_pass = [el for el in\
            self.elements_list if len(list(self.gos_data_dict[el].keys())) >1 ]
        if self.active_dataset == 'First-Fit':
            self.visWL =\
            Visual_WL_ratio(self.ds_first,elems =\
                elemento_to_pass,colores = self.colores)
            self.visWL.create_launch_layout()
            self.visWL.layout.show(title = 'WL analyser',\
                threaded=True,verbose = False)

        elif self.active_dataset == 'Modified-Fit':
            self.visWL =\
            Visual_WL_ratio(self.ds_modi,elems =\
                elemento_to_pass,colores = self.colores)
            self.visWL.create_launch_layout()
            self.visWL.layout.show(title = 'WL analyser',\
                threaded=True,verbose = False)
        else:
            return
    '''   
    @param.depends('active_dataset',watch = True)
    def _change_active_dataset_message(self):
        try:
            self.message_active_dataset.object =\
            '### Active dataset : {}'.format(self.active_dataset)
            if self.active_dataset != None:
                self.message_active_dataset.style = {'color':'lime'}
            else:
                self.message_active_dataset.style = {'color':'lightgrey'}
        except: pass
    '''
    
    def _create_button_column_SI(self):
        self.button_save_workspace
        self.button_save_data
        self.col_buttons = pn.Column(\
            pn.pane.Markdown('### Results panel HUB',\
                width = 350,margin = (0,5,0,25),style = {'color':'white'}),\
            pn.layout.Divider(margin = (0,15)),\
            pn.Row(self.button_save_workspace,self.button_save_data,\
                height = 45,margin = 0),\
            pn.layout.Divider(margin = (0,15)),\
            pn.pane.Markdown('#### Fittings Reduced \u03c7\u00b2 Controls',\
                width = 200,margin = (0,5,0,25),height = 30,style = {'color':'white'}),\
            pn.Row(self.colormap_sel,self.overlay_clust_wid,width = 430,margin = (0,10)),\
            pn.layout.Divider(margin = (0,15)),\
            pn.Row(pn.pane.Markdown('### Analysis apps',\
                width = 120,margin = (5,5,5,15),style = {'color':'white'}),\
            self.dataset_widget),\
            pn.Row(self.button_center_analysis,self.button_WL_analysis,\
                self.button_quantification,width = 450,margin = (5,0)),\
            pn.layout.Divider(margin = (0,25)),\
            pn.Column(\
                pn.pane.Markdown('#### Bethe Surface Analyser', width = 350,\
                    margin = (5,25,-5,25),style = {'color':'white'}),\
                self.elementos_gos_wid,self.sshells_gos_wid,\
                self.button_show_surfaces,self.surface_select_wid,\
                align = 'center',width =400,margin = 0),\
            width = 450,background = 'black',height = 680)
        '''
        self.col_buttons = pn.Column(\
            pn.pane.Markdown('### Fittings Reduced \u03c7\u00b2 Controls',\
                width = 300,margin = (5,5,5,25),style = {'color':'white'}),\
            pn.layout.Divider(width = 350,height = 3,margin = (-5,10,15,20)),\
            pn.Row(self.overlay_clust_wid,self.colormap_sel,width = 380,margin = (5,10,5,10)),\
            self.dataset_widget,\
            pn.Row(pn.pane.Markdown('### Analysis apps',\
                width = 125,margin = (5,5,5,25),style = {'color':'white'}),\
            self.message_active_dataset),\
            pn.layout.Divider(width = 350,height = 3,margin = (-5,10,15,20)),\
            self.button_center_analysis,self.button_WL_analysis,self.button_quantification,\
            pn.layout.Divider(width = 350,height = 3,margin = (-5,10,15,20)),\
            pn.Column(\
                pn.pane.Markdown('#### Bethe Surface Analyser', width = 350,\
                    margin = (5,25,-5,25),style = {'color':'white'}),\
                self.elementos_gos_wid,self.sshells_gos_wid,\
                self.button_show_surfaces,self.surface_select_wid,\
                align = 'center',width =400,margin = 0),\
            width = 400,background = 'black',height = 680)
        '''
    
    def _create_button_column_SL(self):
        self.col_buttons = pn.Column(\
            pn.pane.Markdown('### Fittings Reduced \u03c7\u00b2 Controls',\
                width = 300,margin = (5,5,5,25),style = {'color':'white'}),\
            pn.layout.Divider(width = 350,height = 3,margin = (-5,10,15,20)),\
            pn.Row(self.colormap_sel,width = 380,margin = (5,10,5,10)),\
            pn.layout.Divider(width = 350,height = 3,margin = (-5,10,15,20)),\
            self.button_center_analysis,self.button_WL_analysis,self.button_quantification,\
            pn.layout.Divider(width = 350,height = 3,margin = (-5,10,15,20)),\
            pn.Column(\
                pn.pane.Markdown('#### Bethe Surface Analyser', width = 350,\
                    margin = (5,25,-5,25),style = {'color':'white'}),\
                self.elementos_gos_wid,self.sshells_gos_wid,\
                self.button_show_surfaces,self.surface_select_wid,\
                align = 'center',width =400,margin = 0),\
            width = 400,background = 'black',height = 680)
        pass

    def create_launch_layout(self):
        #Small modifications to the layout objects
        #Let's create the actual layout
        if self.dataset_type == 'SIm':
            self._create_button_column_SI()
        else:
            self._create_button_column_SL()
        self.layout = pn.Row(self.col_buttons,self.graph_panel)
        
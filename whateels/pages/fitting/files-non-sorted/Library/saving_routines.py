import sys
'''
if '../Library/' not in sys.path:
    sys.path.append("../Library/")   #So we are able to work with the local path
'''
import os
import param
import time

import copy as cp
import xarray as xr
import panel as pn
import numpy as np
import pandas as pd
import bokeh as bk
import holoviews as hv

from bokeh.io import export_png
from bokeh.io import export_svgs
from holoviews import streams

hv.extension('bokeh',logo=False)
#Let's look up if the css style is already loaded ... if not, we add it here now

try:
    root_css = [el for el in sys.path if r'\Library\css' in el][0]
except Exception as e:
    print('No root for css found. Skipping loading')
    print(e)
else:
    css_file = '{}\\css_styling.css'.format(root_css)
    if css_file not in pn.config.css_files:
        pn.config.css_files.append(css_file)

def _hook_trial(plot, element):
    #This serves to give format to a plotting object in the dark-theme config
    plot.handles['plot'].border_fill_color = (23, 36, 42)
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

def hook_full_with_legend(plot, element):
    plot.handles['plot'].border_fill_color = (23, 36, 42)
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
    #plot.handles['xaxis'].axis_label_text_font_style = 'bold'
    #plot.handles['yaxis'].axis_label_text_font_style = 'bold'
    plot.handles['plot'].legend.background_fill_alpha = 1
    plot.handles['plot'].legend.background_fill_color = (23 , 36, 42)
    plot.handles['plot'].legend.inactive_fill_alpha = 0.5
    plot.handles['plot'].legend.inactive_fill_color = (23 , 36, 42)
    plot.handles['plot'].legend.label_text_alpha = 1
    plot.handles['plot'].legend.label_text_color = 'white'
    #plot.handles['plot'].legend.label_text_font_style = 'bold'

def export_images(obj, filename,backend = 'svg',size = 'medium'):
    plot_state = hv.renderer('bokeh').get_plot(obj).state
    plot_state.toolbar_location = None   # We do not want the toolbar in our images
    mult_dict = {'small':0.5,'medium':1,'large':2}
    mult = mult_dict[size]
    lista_i = [hv.element.raster.Image,hv.element.raster.HeatMap]
    if type(obj) == hv.core.overlay.Overlay:
        if any([type(el) in lista_i for el in list(obj)]):
            if plot_state.frame_height == plot_state.frame_width:
                #1- case of having a image for an SI - Square area always
                #plot_state.aspect_ratio = 1
                w,h = [int((650+95)*mult),int(650*mult)]
                #plot_state.plot_height = h
                #plot_state.plot_width = h
                #w,h = [int(650*mult),None]
            else:
                #2- case of having a image for an SL - Band
                w,h = [int(800*mult),int(200*mult)] 
            for el in plot_state.right:
                if type(el) == bk.models.annotations.ColorBar:
                    #To modify any possible existing colorbar textstyle
                    el.major_label_text_font_size = '{}pt'.format(int(24*mult))
                    el.major_label_text_font_style = 'bold'
                    el.major_label_text_font = 'Arial'
                    el.width = int(45*mult)
                    el.label_standoff = int(25*mult)
        else:
            plot_state.xaxis.axis_label_text_font = 'Arial'
            plot_state.xaxis.axis_label_text_font_size = '{}pt'.format(int(18*mult))
            plot_state.xaxis.axis_label_text_font_style = 'bold'
            plot_state.xaxis.major_label_text_font = 'Arial'
            plot_state.xaxis.major_label_text_font_size = '{}pt'.format(int(12*mult))
            plot_state.yaxis.axis_label_text_font = 'Arial'
            plot_state.yaxis.axis_label_text_font_size = '{}pt'.format(int(18*mult))
            plot_state.yaxis.axis_label_text_font_style = 'bold'
            plot_state.yaxis.major_label_text_font = 'Arial'
            plot_state.yaxis.major_label_text_font_size = '{}pt'.format(int(12*mult))
            w = int(800*mult)
            h = int(350*mult)
    elif type(obj) in lista_i:
        #For images and heatmaps
        if plot_state.frame_height == plot_state.frame_width:
            #1- case of having a image for an SI - Square area always
            #plot_state.aspect_ratio = 1
            w,h = [int((650+95)*mult),int(650*mult)]
            #plot_state.plot_height = h
            #plot_state.plot_width = h
            #w,h = [int(650*mult),None]
        else:
            #2- case of having a image for an SL - Band
            w,h = [int(800*mult),int(200*mult)] 
        for el in plot_state.right:
            if type(el) == bk.models.annotations.ColorBar:
                #To modify any possible existing colorbar textstyle
                el.major_label_text_font_size = '{}pt'.format(int(24*mult))
                el.major_label_text_font_style = 'bold'
                el.major_label_text_font = 'Arial'
                el.width = int(45*mult)
                el.label_standoff = int(25*mult)
    else:
        #The rest of possible saves:
        #Curves
        #Areas
        #Scatter plots
        #Dynamic maps ...
        plot_state.xaxis.axis_label_text_font = 'Arial'
        plot_state.xaxis.axis_label_text_font_size = '{}pt'.format(int(18*mult))
        plot_state.xaxis.axis_label_text_font_style = 'bold'
        plot_state.xaxis.major_label_text_font = 'Arial'
        plot_state.xaxis.major_label_text_font_size = '{}pt'.format(int(12*mult))
        plot_state.yaxis.axis_label_text_font = 'Arial'
        plot_state.yaxis.axis_label_text_font_size = '{}pt'.format(int(18*mult))
        plot_state.yaxis.axis_label_text_font_style = 'bold'
        plot_state.yaxis.major_label_text_font = 'Arial'
        plot_state.yaxis.major_label_text_font_size = '{}pt'.format(int(12*mult))
        w = int(800*mult)
        h = int(350*mult)
        
    if backend == 'svg':
        if filename[-4:] != '.svg':
            filename = '{}.svg'.format('_'.join(filename.split('.')))    
        plot_state.output_backend = backend
        export_svgs(plot_state, filename=filename, width = w,height = h)
    else:
        if filename[-4:] != '.png':
            #This will check if a . is present...avoid confusion, and add .png
            filename = '{}.png'.format('_'.join(filename.split('.')))    
        export_png(plot_state, filename=filename,width = w,height = h)
    
class Saving_panel(param.Parameterized):
    tick_all = param.Boolean(default=False)
    ticks_save = param.ListSelector(objects=[])
    current_dir = param.String(default='./')
    format_selector = param.ObjectSelector(default='xarray.NETCDF4',\
        objects=['xarray.NETCDF4','numpy','csv','excel/xlsx'])
    #folder_name = param.String(default='Data-Images_saves')
    saving_name = param.String(default='')
    format_selector_images = param.ObjectSelector(default='svg',\
        objects=['svg','png'])
    size_selector_images = param.ObjectSelector(default='medium',\
        objects=['small','medium','large']) 
    ticks_image_saves = param.ListSelector(objects=[])
    #extra_chain = param.String(default='_0')
    def __init__(self,ds,figures = None, figures_names = None ,name_panel = 'NoName'):
        super().__init__()
        #First of all, let's identify possible objects in the list that are not datasets
        if type(ds) != xr.core.dataset.Dataset: return
        self.ds = cp.deepcopy(ds)
        for el in ['original_metadata','original_axes_manager']: 
            if el in self.ds.attrs:
                self.ds.attrs.pop(el)
        self.original_directory = os.getcwd()
        self.current_dir = self.original_directory
        self.name_panel_saves = name_panel
        '''
        try:
            self.saving_name = self.ds.attrs['original_name'].split('.')[0]
        except:
            nombre = name_panel.replace(' ','_')
            self.saving_name = nombre
        '''
        #Let's get the variables, shapes and coordinates
        lista_vars = [el for el in self.ds.data_vars]
        list_coor = []
        list_shapes = []
        for var in lista_vars:
            coords = [(el,self.ds.coords[el].size) for el in self.ds[var].coords]
            list_coor.append('({})'.format(','.join([co[0] for co in coords])))
            list_shapes.append(tuple([co[1] for co in coords]))
        #We stablish here some widgets
        self.button_refresh = pn.widgets.Button(name = '\u27F3',\
            height = 40,width = 40,margin = (5,0),\
            css_classes = ['custom_button_bokeh_darkBluish'])
        self.button_refresh.on_click(self._callback_refresh_directory)
        self.current_dir_wid = pn.Param(self.param['current_dir'],\
            widgets = {'current_dir':pn.widgets.TextInput},\
            parameters = ['current_dir'],width = 500,margin = (0,5),\
            height = 50,show_labels = False,show_name = False)
        self.current_dir_wid[0].margin = (5,0)
        self.current_dir_wid[0].width = 500
        self.current_dir_wid[0].height = 40
        #self.folder_name = 'Data-Images_saves'
        '''
        self.folder_save_wid = pn.Param(self.param['folder_name'],\
            widgets = {'folder_name':pn.widgets.TextInput},\
            parameters = ['folder_name'],width = 250,margin = 5,\
            height = 40,show_labels = False,show_name = False)
        self.folder_save_wid[0].margin = 0
        self.folder_save_wid[0].width = 250
        self.folder_save_wid[0].height = 40
        '''
        self.name_save_wid = pn.Param(self.param['saving_name'],\
            widgets = {'saving_name':pn.widgets.TextInput},\
            parameters = ['saving_name'],width = 210,margin = (5,5,5,0),\
            height = 45,show_labels = False,show_name = False)
        self.name_save_wid[0].margin = (5,0)
        self.name_save_wid[0].width = 210
        self.name_save_wid[0].height = 35
        self.button_save_images = pn.widgets.Button(name = 'Save-Images',\
            height = 35,width = 100,margin = (10,5),\
            css_classes=['custom_button_bokeh_darkGreen'])
        self.button_save_images.on_click(self._callback_save_images)
        self.button_save_data = pn.widgets.Button(name = 'Save-Data',\
            height = 35,width = 100,margin = (10,5),\
            css_classes = ['custom_button_bokeh_darkBluish'])
        self.button_save_data.on_click(self._callback_save_data)
        self.param['ticks_save'].objects = lista_vars
        self.tick_all_wid = pn.Param(self.param['tick_all'],\
            widgets = {'tick_all':pn.widgets.Toggle},\
            parameters = ['tick_all'],width = 100,margin = 5,\
            show_labels = False)
        self.tick_all_wid[0].name = 'Select all'
        self.tick_all_wid[0].button_type = 'default'
        self.tick_all_wid[0].css_classes=['custom_button_bokeh_vibrantGreen',\
            'custom_button_bokeh_vibrantGreenToggled']
        self.tick_all_wid[0].height = 30
        self.tick_all_wid[0].margin = 0
        self.button_clear_all = pn.widgets.Button(name = 'Clear all',\
            width = 100,height = 30,margin = 5,\
            css_classes=['custom_button_bokeh_paleBlue'])
        self.button_clear_all.on_click(self._callback_clearAll)
        self.ticks_wid = pn.Param(self.param['ticks_save'],\
            widgets = {'ticks_save':pn.widgets.CheckBoxGroup},\
            parameters = ['ticks_save'],margin = (10,5,6,5),show_name = False)
        self.mkdown_coords =\
            pn.pane.Markdown('**{}**'.format('<br>'.join(list_coor)),\
                width = 140,margin = (0,15),style = {'font-family':'sans-serif'})
        self.mkdown_shapes =\
            pn.pane.Markdown('**{}**'.format('<br>'.join([str(el) for el in list_shapes])),\
                width = 140,margin = (0,15),style = {'font-family':'sans-serif'})
        self.banner = pn.pane.Markdown(\
            '## Saving - {} - panel'.format(str(name_panel)),\
            width = 350,margin = (5,15),height = 40,style = {'color':'white'})
        self.selector_data_format = pn.Param(self.param['format_selector'],\
            widgets = {'format_selector':pn.widgets.Select},\
            parameters = ['format_selector'],width  = 150,height = 40,\
            show_name = False, show_labels = False,margin = 10)
        self.selector_data_format[0].width = 150
        self.selector_data_format[0].height = 35
        self.selector_data_format[0].margin = 0 
        self.selector_image_format = pn.Param(self.param['format_selector_images'],\
            widgets = {'format_selector_images':pn.widgets.Select},\
            parameters = ['format_selector_images'],width  = 120,height = 40,\
            show_name = False, show_labels = False,margin = 10)
        self.selector_image_format[0].width = 120
        self.selector_image_format[0].height = 35
        self.selector_image_format[0].margin = 0
        self.selector_image_format[0].disabled = True
        self.selector_image_size = pn.Param(self.param['size_selector_images'],\
            widgets = {'size_selector_images':pn.widgets.Select},\
            parameters = ['size_selector_images'],width  = 120,height = 40,\
            show_name = False, show_labels = False,margin = 10)
        self.selector_image_size[0].width = 120
        self.selector_image_size[0].height = 35
        self.selector_image_size[0].margin = 0
        self.selector_image_size[0].disabled = True
        self.panel_figuras = pn.Spacer(height = 610,width = 818,margin = 0,background=(44, 53, 50))
        self.ticks_images = pn.Param(self.param['ticks_image_saves'],\
            widgets = {'ticks_image_saves':pn.widgets.MultiChoice},\
            parameters = ['ticks_image_saves'],\
            width = 750,height = 135,
            margin = (0,25),show_name = False,show_labels = False)
        self.ticks_images[0].css_classes = ['multiChoice_tag_DarkGreen']
        self.ticks_images[0].width = 750
        self.ticks_images[0].height = 135
        self.ticks_images[0].margin = 0
        '''
        self.extra_chain_wid = pn.Param(self.param['extra_chain'],\
            widgets = {'extra_chain':pn.widgets.TextInput},parameters = ['extra_chain'],\
            width = 150,margin = (0,5),height = 45,show_labels = False,show_name = False)
        self.extra_chain_wid[0].margin = 0
        self.extra_chain_wid[0].width = 150
        self.extra_chain_wid[0].height = 45
        self.extra_chain_wid[0].disabled = True   
        '''
        self.subindex = 0
        self.flag = False
        self.colorbar_styling = {'border_line_alpha':0.,'bar_line_alpha':0,\
            'major_label_text_font_style':'bold','major_tick_line_color':'white',\
            'major_tick_line_width':2,'major_label_text_color':'white',\
            'background_fill_color':(23, 36, 42)}
        if (type(figures_names) == list and type(figures) == list):
            if len(figures_names) == len(figures):
                #self.extra_chain_wid[0].disabled = False
                self.selector_image_format[0].disabled = False
                self.selector_image_size[0].disabled = False
                self.param['ticks_image_saves'].objects = figures_names
                self.fig_list = figures
                self.fig_list_nam = figures_names
                self._create_figures_panel()
        
    def _create_figures_panel(self):
        types_images = [hv.element.raster.HeatMap,hv.element.raster.Image]
        #types_images_string = ['HeatMap','Image']
        types_curves = [hv.element.chart.Curve,\
            hv.element.chart.Scatter,hv.element.chart.Area]
        self.mkdwn_images_selector = pn.pane.Markdown(\
            '### Images selector',width = 300,\
                margin = (0,5,0,25),height = 40,style = {'color':'white'})
        lista_images_loaded = list()
        for el in self.fig_list:
            if type(el) in types_curves:
                lista_images_loaded\
                .append(el.opts(bgcolor = (75, 91, 86),hooks = [_hook_trial]))
            elif type(el) in types_images:
                lista_images_loaded\
                .append(el.opts(bgcolor = (75, 91, 86),hooks = [_hook_trial],\
                colorbar_opts = self.colorbar_styling,colorbar_position = 'right'))
            elif type(el) == hv.core.overlay.NdOverlay:
                lista_images_loaded\
                .append(el.opts(bgcolor = (75, 91, 86),hooks = [hook_full_with_legend]))
            elif type(el) == hv.core.overlay.Overlay:
                #This is the difficult one ... we have to check the type of overlay
                if any([type(lay) in types_images for lay in list(el)]):
                    #We have images ...
                    lista_images_loaded\
                    .append(hv.Overlay([el2.opts(bgcolor = (75, 91, 86),hooks = [_hook_trial],\
                    colorbar_opts = self.colorbar_styling) for el2 in list(el)]))
                else:
                    lista_images_loaded\
                    .append(hv.Overlay([el2.opts(bgcolor = (75, 91, 86),hooks = [_hook_trial],\
                    ) for el2 in list(el)]))
            else:
                #safety mode - no extra formatting
                lista_images_loaded\
                .append(el)
        self.images_tab = pn.Tabs(*zip(self.fig_list_nam,\
            lista_images_loaded),\
            dynamic=True,scroll = True,margin = (0,25,10,25),\
            height = 315,width = 768,tabs_location = 'left',background = (23, 36, 42),\
            css_classes = ['tab_button_active_DarkGreen'])
        
        self.panel_figuras = pn.Column(\
            pn.Row(self.mkdwn_images_selector,width = 818,margin = 0,height = 40),\
                self.ticks_images,\
            pn.Column(\
                pn.Row(pn.pane.Markdown('### Images preview',width = 500,\
                    style = {'color':'white'},margin = (10,10,0,25)),\
                width = 768,height = 45,margin = (0,25),background = (23, 36, 42)),\
                self.images_tab,\
            width = 818,height = 390,background = (23, 36, 42)),\
            height = 570,width = 818,margin = 0,background=(23, 36, 42))
        
    def _callback_save_images(self,event):
        types_images = [hv.element.raster.HeatMap,hv.element.raster.Image]
        types_curves = [hv.element.chart.Curve,hv.element.chart.Scatter,\
            hv.element.chart.Area]
        if type(self.ticks_image_saves) != list:
            return
        elif len(list(self.ticks_image_saves)) < 1:
            #Safety .... do not save if there's nothing to be saved
            return
        try:
            self.button_save_images.name = 'Saving'
            self.button_save_images.button_type = 'warning'
            self.button_save_images.disabled = True
            self.directory_navigation_creation()
            if 'Images_saves' not in os.listdir():
                os.mkdir('Images_saves')
            else: pass
            #print('going to images saves')
            os.chdir('./Images_saves')
            if self.name_panel_saves not in os.listdir():
                os.mkdir('./{}'.format(self.name_panel_saves))
            os.chdir(self.name_panel_saves)
            #self.name_panel_saves
            #print('we are in images saves')
            t_formated = '_'.join(time.ctime().split(' ')).replace(':','-')
            for el in self.ticks_image_saves: # pylint: disable= not-an-iterable
                idx = self.fig_list_nam.index(el)
                file_name = '{}_{}'.format(el,t_formated)
                lista_names_now = os.listdir()
                if file_name in lista_names_now:
                    self.flag = True
                    file_name + '_{}'.format(self.subindex)
                #print(el,idx,file_name)
                #print('exporting')
                if type(self.fig_list[idx]) in types_images:
                    objeto = self.fig_list[idx]\
                        .opts(bgcolor = 'white',hooks = [],\
                        colorbar_opts = {})
                elif type(self.fig_list[idx]) in types_curves:
                    objeto = self.fig_list[idx]\
                        .opts(bgcolor = 'white',hooks = [])
                elif type(self.fig_list[idx]) == hv.core.overlay.NdOverlay:
                    objeto = self.fig_list[idx].opts(bgcolor = 'white',hooks = [])
                elif type(self.fig_list[idx]) == hv.core.overlay.Overlay:
                    #This is the difficult one ... we have to check the type of overlay
                    if any([type(lay) in types_images for lay in list(self.fig_list[idx])]):
                        #We have images ...
                        objeto = hv.Overlay([el2.opts(bgcolor = 'white',hooks = [],\
                            colorbar_opts = {}) for el2 in list(self.fig_list[idx])])
                    else:
                        objeto = self.fig_list[idx].opts(bgcolor = 'white',hooks = [])
                else:
                    #In case of not finding the type...do not save it
                    continue
                export_images(\
                    obj = objeto,\
                    filename = file_name,\
                    backend=self.format_selector_images,\
                    size = self.size_selector_images)
                if type(self.fig_list[idx]) in types_images:
                    self.fig_list[idx]\
                    .opts(bgcolor = (75, 91, 86),hooks = [_hook_trial],\
                        colorbar_opts = self.colorbar_styling,colorbar_position = 'right')
                elif type(self.fig_list[idx]) in types_curves:
                    self.fig_list[idx]\
                    .opts(bgcolor = (75, 91, 86),hooks = [_hook_trial])
                elif type(self.fig_list[idx]) == hv.core.overlay.NdOverlay:
                    self.fig_list[idx].opts(bgcolor = (75, 91, 86),hooks = [hook_full_with_legend])
                elif type(self.fig_list[idx]) == hv.core.overlay.Overlay:
                    #This is the difficult one ... we have to check the type of overlay
                    if any([type(lay) in types_images for lay in list(self.fig_list[idx])]):
                        #We have images ...
                        for el2 in list(self.fig_list[idx]):
                            el2.opts(bgcolor = (75, 91, 86),hooks = [_hook_trial],\
                            colorbar_opts = self.colorbar_styling,colorbar_position = 'right')
                    else:
                        self.fig_list[idx].opts(bgcolor = (75, 91, 86),hooks = [_hook_trial])
                else:
                    pass
            if self.flag: 
                self.subindex+=1
                self.flag = False
        except Exception as e:
            self.button_save_images.disabled = False
            self.button_save_images.name = 'Failed!'
            self.button_save_images.button_type = 'danger'
            self.button_save_images.disabled = True
            print(e)
            time.sleep(3)
            pass    
        finally:
            self.button_save_images.disabled = False
            self.button_save_images.name = 'Save-Images'
            self.button_save_images.button_type = 'default'
            os.chdir(self.current_dir)
    
    def _callback_save_data(self,event):
        #First of all...navigation to the right folder  
        if len(self.ticks_save) < 1:
            #Safety .... do not save if there's nothing to be saved
            return
        #self.button_save_data.button_type = 'warning'
        self.button_save_data.name = 'Saving'
        self.button_save_data.disabled = True
        try:
            self.directory_navigation_creation()
            if 'Data_saves' not in os.listdir():
                os.mkdir('Data_saves')
            os.chdir('./Data_saves')
            if self.name_panel_saves not in os.listdir():
                os.mkdir('./{}'.format(self.name_panel_saves))
            os.chdir(self.name_panel_saves)
            if self.format_selector == 'xarray.NETCDF4':
                self.save_netcdf4_dataset()
            elif self.format_selector == 'numpy':
                self.save_numpy()
            elif self.format_selector == 'csv':
                self.save_csv()
            elif self.format_selector == 'excel/xlsx':
                self.save_excel()
            '''
            elif self.format_selector =='xarray.ZARR':
                self.save_zarr_dataset()        
            '''
        except Exception as e:
            self.button_save_data.disabled = False
            self.button_save_data.button_type = 'danger'
            self.button_save_data.name = 'Failed!'
            self.button_save_data.disabled = True
            print(e)
            time.sleep(5)
            pass
        finally:
            #No matter what ... go back to the workspace directory
            self.button_save_data.disabled = False
            self.button_save_data.button_type = 'default'
            self.button_save_data.name = 'Save-Data'
            os.chdir(self.current_dir)
            
    def save_netcdf4_dataset(self):
        #Get saving time chain
        time_s = '{}-{}'.format(time.strftime('%Y%b%d',time.gmtime()),\
            time.strftime('%H\'%M\'%S',time.gmtime()))
        name = './{}'.format('ds-{}-{}.nc'.format(self.saving_name,time_s))
        self.ds[self.ticks_save].\
            to_netcdf(path = '{}'.format(name),format="NETCDF4")
        
    def save_numpy(self):
        time_s = '{}-{}'.format(time.strftime('%Y%b%d',time.gmtime()),\
            time.strftime('%H\'%M\'%S',time.gmtime()))
        foldname = 'np_bundle_{}'.format(time_s)
        try:
            os.mkdir(foldname)
        except Exception as e:
            print(e)
        try:
            np.save('./{}/ELoss.npy'.format(foldname),\
                self.ds.Eloss.values,allow_pickle=False)
        except Exception as e: 
            print(e)
        for el in self.ds[self.ticks_save]:
            clave = ''.join(el.split(' '))
            clave = clave.replace('.','')
            np.save('./{}/{}.npy'.format(foldname,clave),self.ds[el].values,\
                allow_pickle=False)
        
    def save_csv(self):
        #As we have to implement different formats for each dimensionality case...
        time_s = '{}-{}'.format(time.strftime('%Y%b%d',time.gmtime()),\
            time.strftime('%H\'%M\'%S',time.gmtime()))
        foldname = 'csv_bundle_{}'.format(time_s)
        try:
            os.mkdir(foldname)
        except Exception as e:
            print(e)
        for el in self.ds[self.ticks_save]:
            if len(self.ds[el].coords) == 3 and 'Eloss' in self.ds[el].coords:
                #Data Cube case - spectrum image/like structures
                df = self.get_df_3D(name = el)
                clave_name = cp.deepcopy(el)
                clave_name = clave_name.replace('/','_')
                clave_name = clave_name.replace('.','_')
                df.to_csv('./{}/{}.csv'.format(foldname,clave_name),index=False)
            elif len(self.ds[el].coords) == 2 and 'Eloss' not in self.ds[el].coords:
                df = self.get_df_2D_mapping(name = el)
                clave_name = cp.deepcopy(el)
                clave_name = clave_name.replace('/','_')
                clave_name = clave_name.replace('.','_')
                df.to_csv('./{}/{}.csv'.format(foldname,clave_name),index=False,header=True)
        #Now let's pick every single spectra and bunddle them toguether
        bundle = [el for el in self.ticks_save \
            if (len(self.ds[el].coords) == 1 and 'Eloss' in self.ds[el].coords)]
        if len(bundle) >= 1:
            df = self.ds[bundle].to_dataframe()
            df.to_csv('./{}/bundled_spectra.csv'.format(foldname),index=True,header=True)

    '''#Pending idea ...
    def save_zarr_dataset(self):
        pass
    '''

    def save_excel(self):
        time_s = '{}-{}'.format(time.strftime('%Y%b%d',time.gmtime()),\
            time.strftime('%H\'%M\'%S',time.gmtime()))
        with pd.ExcelWriter("Data-{}-{}.xlsx"\
            .format(self.saving_name,time_s), engine='xlsxwriter') as writer: # pylint: disable=abstract-class-instantiated    
            #writer.book = book
            for el in self.ds[self.ticks_save]:
                if len(self.ds[el].coords) == 3 and 'Eloss' in self.ds[el].coords:
                    #Data Cube case - spectrum image/like structures
                    df = self.get_df_3D(name = el)
                    df.to_excel(writer,index=False,sheet_name = el)
                elif len(self.ds[el].coords) == 2 and 'Eloss' not in self.ds[el].coords:
                    df = self.get_df_2D_mapping(name = el)
                    df.to_excel(writer,index=True,sheet_name = el)
            bundle = [el for el in self.ticks_save \
            if (len(self.ds[el].coords) == 1 and 'Eloss' in self.ds[el].coords)]
            if len(bundle) >= 1:
                df = self.ds[bundle].to_dataframe()
                df.to_excel(writer,index=True,sheet_name = 'bundled_spectra')
            writer.save()
        
    #Methods to be called to same 3D structures
    def get_df_3D(self,name):
        data = self.ds[name].values
        data2 = data.reshape(-1, data.shape[-1])
        Eloss = self.ds.Eloss.values
        index_list = [el for el in zip(np.indices(data.shape[:-1])[0].flatten(),\
            np.indices(data.shape[:-1])[1].flatten())]
        df = pd.DataFrame(data2.T,columns=index_list)
        df.insert(loc = 0,column='ELoss [eV]',value = Eloss)
        return df
        
    def get_df_2D_mapping(self,name):
        df = pd.DataFrame(self.ds[name].values)
        return df
        
    def directory_navigation_creation(self):
        #First, investigate if we have a valid worksaving
        if 'Savings-Workspace' not in os.listdir(self.current_dir):
            os.mkdir('Savings-Workspace')
        os.chdir('./Savings-Workspace')
        try:
            name = self.ds.attrs['original_name'].split('.')[0]
        except Exception as e:
            #print(e)
            name = 'Sample_NoName'
        finally:
            if name not in os.listdir():
                os.mkdir(name)
            os.chdir(name) 
        '''
        list_new_path = self.folder_name.split('\\')
        direct = os.getcwd().strip('\\')
        for el in list_new_path:
            list_folders = os.listdir(direct)
            direct = '\\'.join([direct.strip('\\'),el])
            if el not in list_folders:
                os.mkdir(direct)
                os.chdir(direct)
            else:
                os.chdir(direct)
        '''
    
    def _callback_refresh_directory(self,event):
        self.current_dir = self.original_directory
        
    def _callback_clearAll(self,event):
        self.ticks_save = []
        if self.tick_all:
            self.tick_all = False
        else: pass
        
    @param.depends('tick_all',watch = True)
    def _tick_all(self):
        if self.tick_all:
            self.tick_all_wid[0].button_type = 'primary'
            lista = self.param['ticks_save'].objects
            self.ticks_save = lista
        else:
            self.tick_all_wid[0].button_type = 'default'
            pass
        
    def create_layout(self):
        '''
        self.fila_buttons_selection =\
            pn.Row(self.tick_all_wid,self.button_clear_all,width = 375,\
            margin = 0,background = (221, 112, 53))
        '''
        
        self.mkdwn_directory = pn.pane.Markdown('### WorkSpace Directory',\
            margin = (5,10),width = 160,height = 40,style = {'color':'white'})
        self.mkdwn_folder = pn.pane.Markdown('### Saving folder',\
            margin = (5,10,5,25),width = 100,height = 40,style = {'color':'white'})
        self.mkdwn_name = pn.pane.Markdown('### Saving name',\
            margin = (8,5,5,15),width = 115,height = 35,style = {'color':'white'})
        self.mkdwn_format_data = pn.pane.Markdown('### Format',\
            margin = (8,5,5,25),width = 60,height = 35,style = {'color':'white'})
        self.mkdwn_im_form = pn.pane.Markdown('### Image extension',\
            margin = (8,5,5,25),width = 145,height = 35,style = {'color':'white'})
        self.mkdown_raw_data= pn.pane.Markdown('### Raw-Data',\
            margin = (5,15),width = 145,height = 35,style = {'color':'white'})
        self.mkdown_raw_images= pn.pane.Markdown('### Images-Available',\
            margin = (5,25),width = 145,height = 35,style = {'color':'white'})
        self.mkdwn_im_size = pn.pane.Markdown('### Size',\
            margin = (8,5,5,5),width = 85,height = 35,style = {'color':'white'})
        self.banner_row = pn.Row(self.banner,self.mkdwn_directory,\
            self.current_dir_wid,self.button_refresh,\
            #self.mkdwn_folder,self.folder_save_wid,\
            self.mkdwn_folder,\
            width = 1550,margin = 0,background=(23, 36, 42),height = 75)
        
        self.fila_save_raw =\
            pn.Row(self.mkdwn_name,self.name_save_wid,\
            self.mkdwn_format_data,self.selector_data_format,\
            self.button_save_data,height = 55,width = 732,\
            margin = 0,background = (43, 122, 119))
        self.fila_save_ima =\
            pn.Row(self.mkdwn_im_form,self.selector_image_format,\
            self.mkdwn_im_size,self.selector_image_size,\
            self.button_save_images,margin = 0,\
            width = 818,height = 55,background = (23, 36, 42))
        self.fila_save = pn.Row(self.fila_save_raw,self.fila_save_ima,\
            width = 1550,margin = 0,height = 55)

        self.fila_names = pn.Row(\
            pn.Row(pn.pane.Markdown('### Data variables',width = 110,\
                margin = (0,5,0,15),height = 40,style = {'color':'white'}),\
                self.tick_all_wid,self.button_clear_all,\
                width = 375,margin = 0,height = 40,background = (43, 122, 119)),\
            pn.Row(pn.pane.Markdown('### Data shape',width = 140,\
                margin = (0,15),height = 40,style = {'color':(43, 122, 119)}),\
                width = 170,margin = 0,height = 40,background=(222, 242, 241)),\
            pn.Row(pn.pane.Markdown('### Coord.names',width = 140,\
                margin = (0,15),height = 40,style = {'color':'white'}),\
                width = 170,margin = 0,height = 40,background = (43, 122, 119)))
        
        self.block_data = pn.Row(\
            pn.Column(self.ticks_wid,width = 375,background = (222, 242, 241)),\
            pn.Column(self.mkdown_shapes,width = 170,background = 'white'),\
            #(186, 208, 226)
            pn.Column(self.mkdown_coords,width = 170,background = (222, 242, 241)),\
            scroll=True,background = (51, 147, 143),\
            min_height = 250,max_height = 530,width = 732)
        
        self.fila_mkd_row = pn.Row(self.mkdown_raw_data,\
            width = 732,height = 45,margin = 0,background =(43, 122, 119))
        self.fila_mkd_ima = pn.Row(self.mkdown_raw_images,\
            width = 818,height = 45,margin = 0,background = (23, 36, 42))
        self.layout = pn.Column(\
            self.banner_row,\
            pn.Row(self.fila_mkd_row,self.fila_mkd_ima,\
                margin = 0,width = 1550,height = 45),\
            self.fila_save,\
            pn.Row(pn.Column(self.fila_names,self.block_data,\
                        margin = 0,background = (43, 122, 119),height = 570),\
                    self.panel_figuras,margin = 0))
        self.layout.show(title = 'SavingPanel',\
            threaded = True,verbose = False)    
import sys
import time
import os
import hyperspy.api as hs
import holoviews as hv
from holoviews import streams, opts, dim
from holoviews.streams import Selection1D
from holoviews.streams import Stream,param
# import hvplot.xarray
import panel as pn
import pandas as pd
import bokeh, param
from bokeh.models import HoverTool

import copy as cp
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from random import choice

from scipy.integrate import simpson

hv.extension("bokeh",logo = False)
print('Importing - Visualization tools')

#Formatters for the axes
def formatter(value):
        #Method to format the yaxis format (Electron Counts)
        return '{:+.1e}'.format(value)

def formatter_y_SL(value):
    return '{:.0f}'.format(value)
    
def formatter2(value):
        #Method to format the yaxis format -\
        # only use ir with in axes with fully integer numbers
        return '      {:.0f}'.format(value)
        
def hook_full_black_1(plot, element):
    #This serves to give format to a plotting object in the dark-theme config
    plot.handles['plot'].border_fill_color = 'grey'
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

def formatter3(value):
    return '{:5d}'.format(value)

def formatter4(value):
    return '{:9.2f}'.format(value)

class Visual_loading(param.Parameterized):
    click_text = param.String()

    def __init__(self,ds):
        super().__init__()
        # hv.extension('plotly',logo = False)
        self.ds = ds
        self.ds_emptyCurve =\
            xr.Dataset({'ElectronCount':(['Eloss'],np.zeros_like(self.ds.Eloss.values))},\
            coords = {'Eloss':self.ds.Eloss.values})
        self.message_click = pn.Param(self.param['click_text'],\
            widgets = {'click_text':pn.widgets.StaticText},\
            parameters = ['click_text'],show_labels = False,show_name = False)
        self.message_click[0].style = {'font-weight':'bold','color':'grey'}
        if ds.x.values.size == 1 and ds.y.values.size == 1:
            self.type_dataset = 'SSp' #Single spectrum
            self.create_SSp()
        elif ds.x.values.size == 1 and ds.y.values.size != 1:
            self.type_dataset = 'SLi' #Spectrum line
            self.click_text = '|- y : None -|'
            self.create_SLi()
            self.hov_lims = (self.ds.Eloss.values[0]-0.5,self.ds.Eloss.values[-1]+\
                0.5,self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        elif ds.x.values.size != 1 and ds.y.values.size != 1:
            #We make a simple calculation to know how to padd the image
            xsize = self.ds.x.values.size
            ysize = self.ds.y.values.size
            dist = abs(ysize-xsize)
            if xsize < ysize:
                self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
                self.ylims = (-0.5,ysize-0.5)
            else:
                self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
                self.xlims = (-0.5,xsize-0.5)
            self.type_dataset = 'SIm' #Spectrum image
            self.click_text = '|- x : None -|- y : None -|'
            self.create_SIm()
            self.hov_lims = (self.ds.x.values[0]-0.5,self.ds.x.values[-1]+\
                0.5,self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        else:
            return
        
    def create_SIm(self):
        self.im_ref = hv.Image(self.ds.ElectronCount.sum('Eloss'),kdims = ['x','y'])\
            .opts(cmap = 'Greys_r',invert_yaxis=True,\
            xaxis = None,yaxis = None,\
            xlim = self.xlims,ylim = self.ylims)
        self.im = hv.HeatMap(self.ds.ElectronCount.sum('Eloss'),kdims = ['x','y'])\
            .opts(cmap = 'Greys_r',invert_yaxis=True,\
            xaxis = None,yaxis = None,\
            xlim = self.xlims,ylim = self.ylims,\
            line_width = 1.5,\
            fill_alpha = 0.5,line_alpha = 0.1,bgcolor = 'darkgrey',\
            hover_line_color = 'limegreen',hover_line_alpha = 1,\
            hover_fill_alpha = 1,\
            selection_line_alpha = 1,selection_line_color = 'red',\
            selection_fill_alpha = 1,nonselection_line_alpha = 0.1,\
            nonselection_line_color = 'white',nonselection_fill_alpha = 0.5,\
            tools = ['hover','tap'])
        self.empty_spectrum =\
            hv.Area(self.ds_emptyCurve)\
            .opts(frame_height = 300,yformatter = formatter,frame_width = 600,\
                shared_axes=False,framewise = True,show_grid = True,\
                color='grey',fill_alpha=0.75,line_width = 0)
        self.empty_curve = hv.Curve(self.ds_emptyCurve)\
            .opts(frame_height = 300,yformatter = formatter,frame_width = 600,\
                shared_axes=False,framewise = True,show_grid = True,\
                color='black',line_width=2.)
        self.tap = streams.Tap(x = -1,y = -1,source = self.im)
        self.hov = streams.PointerXY(x = -1,y = -1,source = self.im)
        self.spectrum_hover = hv.DynamicMap(self._callback_hover_2d,streams=[self.hov])\
            .opts(frame_height = 300,yformatter = formatter,frame_width = 600,\
            shared_axes=False,framewise = True,show_grid = True)
        self.spectrum_tap = hv.DynamicMap(self._callback_tap_2d,streams=[self.tap])\
            .opts(frame_height = 300,yformatter = formatter,frame_width = 600,\
            shared_axes=False,framewise = True,show_grid = True)
        
    def create_SLi(self):
        self.im = hv.Image(self.ds.ElectronCount,kdims = ['y','Eloss'])\
            .opts(cmap = 'Greys_r',invert_axes=True,invert_yaxis=True,\
                frame_width = 900,frame_height = 125,yformatter = formatter2,\
                xaxis = None,toolbar = None,bgcolor = 'ghostwhite')
        self.empty_spectrum =\
            hv.Area(self.ds_emptyCurve)\
            .opts(frame_height = 250,yformatter = formatter,frame_width = 900,\
                shared_axes=False,framewise = True,show_grid = True,\
                color='grey',fill_alpha=0.75,line_width = 0)
        self.empty_curve = hv.Curve(self.ds_emptyCurve)\
            .opts(frame_height = 250,yformatter = formatter,frame_width = 900,\
                shared_axes=False,framewise = True,show_grid = True,\
                color='black',line_width=2.)
        self.tap = streams.Tap(x = -1,y = -1,source = self.im)
        self.hov = streams.PointerXY(x = -1,y = -1,source = self.im)
        self.spectrum_hover = hv.DynamicMap(self._callback_hover_1d,streams=[self.hov])\
            .opts(frame_height = 250,yformatter = formatter,frame_width = 900,\
            shared_axes=False,framewise = True,show_grid = True)
        self.spectrum_tap = hv.DynamicMap(self._callback_tap_1d,streams=[self.tap])\
            .opts(frame_height = 250,yformatter = formatter,frame_width = 900,\
            shared_axes=False,framewise = True,show_grid = True)
        
    def create_SSp(self):
        self.spectrum = hv.Area(self.ds.ElectronCount.isel(x = 0,y = 0))\
            .opts(color='limegreen',fill_alpha=0.5,line_color='black',\
                frame_width = 900,frame_height = 350,yformatter = formatter,\
                framewise = True,shared_axes = False,show_grid = True)
        
    def _callback_tap_2d(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            x0,y0 = self.im_ref.closest((x,y))
            self.click_text = '|- x : {} -|- y : {} -|'.format('None','None')
            try:
                self.message_click[0].style = {'font-weight':'bold','color':'grey'}
            except:
                pass
            finally:
                return self.empty_spectrum
        elif y >= yf or y <= yi:
            x0,y0 = self.im_ref.closest((x,y))
            self.click_text = '|- x : {} -|- y : {} -|'.format('None','None')
            try:
                self.message_click[0].style = {'font-weight':'bold','color':'grey'}
            except:
                pass
            finally:
                return self.empty_spectrum
        else:
            x0,y0 = self.im_ref.closest((x,y))
            self.click_text = '|- x : {} -|- y : {} -|'.format(str(int(x0)),str(int(y0)))
            curve = hv.Area(self.ds.isel(x = int(x0),y = int(y0)))\
            .opts(fill_color= 'orangered',fill_alpha = 0.5,line_color = 'darkred',\
            line_width=1.5,line_alpha = 1)
            #.opts(color='darkred',fill_alpha=0.5,line_color='black')
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            try:
                self.message_click[0].style = {'font-weight':'bold','color':'darkred'}
            except:
                pass
            finally:
                return curve

    def _callback_hover_2d(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_spectrum
        elif y >= yf or y <= yi:            
            return self.empty_spectrum
        else:
            x0,y0 = self.im_ref.closest((x,y))
            curve = hv.Area(self.ds.isel(x = int(x0),y = int(y0)))\
            .opts(fill_color='limegreen',fill_alpha=0.5,line_width = 0)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve

    def _callback_tap_1d(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            y0 = self.im.closest((x,y))[1]
            self.click_text = '|- y : {} -|'.format('None')
            try:
                self.message_click[0].style = {'font-weight':'bold','color':'grey'}
            except:
                pass
            finally:
                return self.empty_curve
        elif y >= yf or y <= yi:
            y0 = self.im.closest((x,y))[1]
            self.click_text = '|- y : {} -|'.format('None')
            try:
                self.message_click[0].style = {'font-weight':'bold','color':'grey'}
            except:
                pass
            finally:
                return self.empty_curve
        else:
            y0 = self.im.closest((x,y))[1]
            self.click_text = '|- y : {} -|'.format(str(int(y0)))
            curve = hv.Curve(self.ds.isel(y = int(y0),x = 0))\
            .opts(color='midnightblue',line_width = 2.)
            #.opts(color='midnightblue',fill_alpha=0.5,line_color='black')
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            try:
                self.message_click[0].style = {'font-weight':'bold','color':'midnightblue'}
            except:
                pass
            finally:
                return curve

    def _callback_hover_1d(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_spectrum
        elif y >= yf or y <= yi:
            return self.empty_spectrum
        else:
            y0 = self.im.closest((x,y))[1]
            curve = hv.Area(self.ds.isel(y = int(y0),x = 0))\
            .opts(color='grey',fill_alpha=0.75,line_width = 0)
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve
        
    def create_panels(self):
        self.message_click[0].margin = (0,10,5,10)
        or_name_message = pn.widgets.StaticText(value = 'DataSet on Display',\
            style = {'font-weight' : 'bold'})
        text_tap = pn.widgets.StaticText(value = 'Selected data',\
            style = {'font-weight' : 'bold'})
        original_name_str = pn.widgets.StaticText(value = self.ds.original_name,\
            style = {'font-weight' : 'bold','color':'grey'})
        if self.type_dataset == 'SSp':
            fila = pn.Row(or_name_message,original_name_str,width = 1000)
            self.struc = pn.Column(fila,self.spectrum,width = 1000,height = 550)
        elif self.type_dataset == 'SIm':
            fila = pn.Column(pn.Row(or_name_message,original_name_str),\
                pn.Row(text_tap,self.message_click),width = 1000)
            self.struc = pn.Column(fila,\
                pn.Row(self.im,self.spectrum_hover*self.spectrum_tap,\
                width = 1000,height = 450),width = 1000,height = 550)
        elif self.type_dataset == 'SLi':
            fila = pn.Column(pn.Row(or_name_message,original_name_str),
                pn.Row(text_tap,self.message_click),width = 1000)
            self.struc = pn.Column(fila,\
                self.im,self.spectrum_hover*self.spectrum_tap,\
                width = 1000,height = 550)
        else:
            self.struc = pn.Spacer(width = 1000,height = 550,background = 'gainsboro') 
        
#################################################################################################
#                                                                                               #
#                                                                                               #
#                      Display for the center analysis tool                                     #
#                                                                                               #
#                                                                                               #
#################################################################################################
class Visual_distance_results(param.Parameterized):
    #Class for the visualization functions used for
    #Comparative parameters selectors
    components1 = param.ListSelector()
    components2 = param.ListSelector()
    element1   = param.ObjectSelector()
    element2   = param.ObjectSelector()
    range_cmap1    = param.Range(label = 'Colorbar range [eV] ')
    range_cmap2    = param.Range(label = 'Colorbar range [eV] ')
    range_cmapDiff = param.Range(label = 'Colorbar range [eV] ')
    colormap_1 = param.ObjectSelector(default= 'viridis',objects=['viridis'])
    colormap_2 = param.ObjectSelector(default= 'cividis',objects=['cividis'])
    colormap_diff = param.ObjectSelector(default= 'cividis',objects=['cividis'])
    coor_x = param.String(default=' - ')
    coor_y = param.String(default=' - ')
    vert_x0 = param.String(default=' - ')
    vert_x1 = param.String(default=' - ')
    vert_y0 = param.String(default=' - ')
    vert_y1 = param.String(default=' - ')
    dynamic_displays = param.ObjectSelector(default='Best',\
        objects=['Best','Comps.'])
    line_displays = param.ObjectSelector(objects=[])
    
    ###################################
    def __init__(self,ds,elem,colores):
        super().__init__()
        #Data and original image
        #self.ds = ds
        self.list_compos = []
        self.list_ds = [cp.deepcopy(ds),]
        for comp in ds.data_vars:
            if '_component' in comp and '_cont' not in comp:
                self.list_compos.append(comp.split('_component')[0])
            elif 'K_' in comp and '_component' in comp:
                #This is new, controls when we add the onsets for K edges
                self.list_compos.append(comp.split('_cont_component')[0])
                self._create_onset_ds(ds,comp,'K-type')
            else:pass

        self.ds = xr.merge(self.list_ds)
        xsize = self.ds.x.values.size
        ysize = self.ds.y.values.size
        dist = abs(ysize-xsize)
        if xsize < ysize:
            self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
            self.ylims = (-0.5,ysize-0.5)
        else:
            self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
            self.xlims = (-0.5,xsize-0.5)
        self.step = ds.Eloss.values[1]-ds.Eloss.values[0]
        self.im0 = hv.Image(self.ds.OriginalData.sum('Eloss'))\
            .opts(cmap = 'Greys_r',invert_yaxis=True,\
            xaxis = None,yaxis = None,shared_axes = False,\
            xlim = self.xlims,ylim = self.ylims,\
            frame_width = 250)
        empty_Data =\
            xr.Dataset({'EmptyData':(['y','x','Eloss'],\
            np.zeros_like(self.ds.OriginalData.values))},\
            coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
            'Eloss':self.ds.Eloss.values})
        self.im_empty = hv.Image(empty_Data.EmptyData.sum('Eloss'))\
        .opts(cmap = 'Greys_r',invert_yaxis=True,\
            xaxis = None,yaxis = None,toolbar = 'below',shared_axes = False,\
            frame_width = 250,title = 'Empty image',\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar = True,colorbar_position = 'right')
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,\
            shared_axes = False,title = 'Dynamic selection',yformatter=formatter)
        self.scatter_empty = hv.Scatter(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,yformatter=formatter4,\
            shared_axes = False,title = 'Line Selection',framewise = True)
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,\
            shared_axes = False,title = 'Dynamic selection',yformatter=formatter,\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black')
        self.im_empty_diff = hv.Image(empty_Data.EmptyData.sum('Eloss'))\
        .opts(cmap = 'Greys_r',invert_yaxis=True,\
            xaxis = None,yaxis = None,toolbar = 'right',shared_axes = False,\
            frame_width = 450,title = 'Empty distance image',\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar = True,colorbar_position = 'right')
        if type(colores) == dict:
            self.cmap_clusters =\
            [colores[el] for el in colores if el != 'default']
        elif type(colores) == list:
            self.cmap_clusters = colores
        #Colormaps to be selected
        self.param['colormap_1'].objects = hv.plotting.util.list_cmaps(category='Uniform Sequential')
        self.param['colormap_2'].objects = hv.plotting.util.list_cmaps(category='Uniform Sequential')
        self.param['colormap_diff'].objects = hv.plotting.util.list_cmaps(category='Uniform Sequential')
        #Now the possible components to be displayed in results 
        '''
        self.list_compos = []
        for comp in self.ds.data_vars:
            if '_component' in comp and '_cont' not in comp:
                self.list_compos.append(comp.split('_component')[0])
            else:pass
        '''
        ##### Time to set up some of the options in the parameters
        self.param['element1'].objects = elem
        self.element1 = elem[0]
        self.param['element2'].objects = elem
        self.element2 = elem[0]

    def _create_onset_ds(self,ds,clave,type_compo):
        '''This method creates the onset data structures,
        so we can use onsets to measure distances'''
        #This conditional will allow an expansion to include 
        #onsets for elements with elnes in the future
        if type_compo == 'K-type':
            vals = ds[clave].values
            diff2 = np.zeros_like(vals)
            diff2[:,:,2:] = np.diff(np.diff(vals))
            onsets = np.zeros(vals.shape[:-1])
            indices = np.nanargmin(np.abs(diff2 -\
                np.nanmax(diff2,axis=-1)[:,:,None]),axis= -1)
            onsets = ds.Eloss.values[indices]
            onsets[onsets == ds.Eloss.values[0]] = np.nan
            new_clave = ''.join([clave.split('_')[0],'_onset'])
            dsons = xr.Dataset({new_clave:(['y','x'],onsets)},\
                coords = {'y':ds.y.values,'x':ds.x.values})
            self.list_ds.append(dsons)

    def algorithm_DDA(self,xi,xf,yi,yf):
        #Digital differential analyzer (DDA) - getting the pixels in the line
        dx = (xf-xi)
        dy = (yf-yi)
        if abs(dx) >= abs(dy):
            step = abs(dx)
        else:
            step = abs(dy)
        dx /= step
        dy /= step
        list_x = []
        list_y = []
        idx_im = []
        i = 1
        x = xi
        y = yi
        while i<= step:
            list_x.append(x)
            list_y.append(y)
            x += dx
            y += dy
            #to make them integers
            #x,y = im.closest((x,y))
            i += 1
        #At the end, we correct to get the actual pixel possitions
        for i,el in enumerate(list_x):
            #We are applying this to the image we are interest on
            idx_im.append(self.image_diff_small.closest((el,list_y[i])))
        x,y = self.image_diff_small.closest((xf,yf))
        idx_im.append((x,y))
        return idx_im

    @param.depends('element1',watch = True)
    def _change_compos_available1(self):
        self.components1 = []
        self.param['components1'].objects =\
        [comp.split(self.element1)[1] for comp in self.list_compos if self.element1 in comp]
        try:
            self.button_show_distances_panel.disabled = True
        except: pass
        
    @param.depends('element2',watch = True)
    def _change_compos_available2(self):
        self.components2 = []
        self.param['components2'].objects =\
        [comp.split(self.element2)[1] for comp in self.list_compos if self.element2 in comp]
        try:
            self.button_show_distances_panel.disabled = True
        except: pass
        
    @param.depends('components1',watch = True)
    def _activate_show_button_distance_1(self):
        try:
            if self.components1 != []:
                self.button_show_1.disabled = False
                self.button_show_1.button_type = 'primary'
            else:
                self.button_show_1.disabled = True
                self.button_show_1.button_type = 'default'
        except: pass
        finally:
            try:
                self.button_show_distances_panel.disabled = True
            except: pass
        
    @param.depends('components2',watch = True)
    def _activate_show_button_distance_2(self):
        try:
            if self.components2 != []:
                self.button_show_2.disabled = False
                self.button_show_2.button_type = 'primary'
            else:
                self.button_show_2.disabled = True
                self.button_show_2.button_type = 'default'
        except: pass
        finally:
            try:
                self.button_show_distances_panel.disabled = True
            except: pass
    
    @param.depends('range_cmap1','colormap_1',watch = True)
    def _modify_lim_slide1(self):
        try:
            self.image_placeholder1.object =\
            self.image_placeholder1.object\
            .opts(clim = tuple([el for el in self.range_cmap1]),\
            cmap = self.colormap_1)
        except:
            pass
        
    @param.depends('range_cmap2','colormap_2',watch = True)
    def _modify_lim_slide2(self):
        try:
            self.image_placeholder2.object =\
            self.image_placeholder2.object\
            .opts(clim = tuple([el for el in self.range_cmap2]),\
            cmap = self.colormap_2)
        except:
            pass
    
    @param.depends('range_cmapDiff','colormap_diff',watch = True)
    def _modify_lim_slide_diff(self):
        try:
            self.image_placeholder_diff.object =\
            self.image_placeholder_diff.object\
            .opts(clim = tuple([el for el in self.range_cmapDiff]),\
            cmap = self.colormap_diff)
        except:
            pass
        
    @param.depends('components1','components2',watch = True)
    def _activate_show_button_distances(self):
        try:
            if self.components2 != [] and self.components1 != []:
                self.button_dist_compos.disabled = False
                self.button_dist_compos.button_type = 'success'
            else:
                self.button_dist_compos.disabled = True
                self.button_dist_compos.button_type = 'default'
        except: pass  
        
    
    def _callback_get_distances(self,event):
        #We have to compute the distances - \
        # and get the image of distance difference, as well as a histogram
        self.cmap_seldiff[0].disabled = False
        self.slider_diff[0].disabled = False
        if self.components2[0] == 'K':
            tag2 = ''.join([self.element2,self.components2[0],'_onset'])
        else:
            tag2 = ''.join([self.element2,self.components2[0],'_center'])
        if self.components1[0] == 'K':
            tag1 = ''.join([self.element1,self.components1[0],'_onset'])
        else:
            tag1 = ''.join([self.element1,self.components1[0],'_center'])
        '''tag1 = ''.join([self.element1,self.components1[0],'_center'])
        tag2 = ''.join([self.element2,self.components2[0],'_center'])'''
        titl = ''.join(['Distance ',self.element1,self.components1[0],'-',\
            self.element2,self.components2[0]])
        #xrArr = xr.ufuncs.fabs(self.ds[tag1]-self.ds[tag2])  #Deprecated
        xrArr = abs(self.ds[tag1]-self.ds[tag2])
        self.ds_dist = xrArr.to_dataset(name = 'Distances')
        maxi = round(np.nanmax(self.ds_dist.Distances.values))
        mini = round(np.nanmin(self.ds_dist.Distances.values))
        diff_var = (maxi-mini) * 0.1
        self.param['range_cmapDiff'].bounds = (mini-diff_var,maxi+diff_var)
        self.range_cmapDiff = (mini,maxi)
        self.image_diff = hv.Image(self.ds_dist.Distances)\
        .opts(cmap = self.colormap_diff,invert_yaxis=True,\
            xaxis = None,yaxis = None,toolbar = 'right',\
            frame_width = 450,title = titl,\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar = True,colorbar_position = 'right',\
            shared_axes = False,clipping_colors = {'NaN': 'black'})
        self.image_placeholder_diff.object = self.image_diff 
        #We get also the dynamic maps
        self.tag_din1 = ''.join([self.element1,self.components1[0],'_component'])
        self.tag_din2 = ''.join([self.element2,self.components2[0],'_component'])
        self.hov_lims = (self.ds.x.values[0]-0.5,self.ds.x.values[-1]+\
                0.5,self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        self.button_show_distances_panel.disabled = False
        self.current_selection = titl
    
    @param.depends('coor_x','coor_y',watch = True)
    def _change_coor_message(self):
        try:
            self.message.object =\
            '#### Selected |- x : {} -|- y : {} -|'\
            .format(self.coor_x,self.coor_y)
            if self.coor_x != ' - ' and self.coor_y != None:
                self.message.style = {'color':'darkorange'}
            else:
                self.message.style = {'color':'grey'}
        except:
            pass
    
    @param.depends('vert_x0','vert_x1','vert_y0','vert_y1',watch = True)
    def _change_coor_message_line(self):
        try:
            self.message_line.object =\
            '#### Selected line |- v0 : ({},{}) -|- v1 : ({},{}) -|'\
            .format(self.vert_x0,self.vert_y0,self.vert_x1,self.vert_y1)
            lista = [self.vert_x0,self.vert_x1,self.vert_y0,self.vert_y1]
            if all([el != ' - ' for el in lista]):
                self.message_line.style = {'color':'limegreen'}
            else:
                self.message_line.style = {'color':'grey'}
        except:
            pass
        
    # Plots for the dynamic maps
    #Best fit
    def _plot_best(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi: return self.curve_empty
        elif y >= yf or y <= yi: return self.curve_empty
        else:
            x0,y0 = self.image_diff_small.closest((x,y))
            self.coor_x = str(x0)
            self.coor_y = str(y0)
            curve = hv.Curve(self.ds.BestFit.isel(x = int(x0),y = int(y0)),label='BestFit')\
            .opts(color='limegreen',line_width=1.)
            #.opts(color='darkred',fill_alpha=0.5,line_color='black')
            curve.relabel('Tick formatters').opts(yformatter=formatter)
            return curve

    #Original data
    def _plot_original(self,x,y):
        #Let this function have the indicator for coordinate change
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            self.coor_x = ' - '
            self.coor_y = ' - '
            return self.area_empty
        elif y >= yf or y <= yi:
            self.coor_x = ' - '
            self.coor_y = ' - '
            return self.area_empty
        else:
            x0,y0 = self.image_diff_small.closest((x,y))
            self.coor_x = str(x0)
            self.coor_y = str(y0)
            area = hv.Area(self.ds.OriginalData.isel(x = int(x0),y = int(y0)),\
                label = 'OriginalData')\
            .opts(line_width=1.,line_alpha = 0.5,fill_alpha = 0.25,\
            fill_color = 'grey',line_color = 'black')
            #.opts(color='darkred',fill_alpha=0.5,line_color='black')
            area.relabel('Tick formatters').opts(yformatter=formatter)
            return area
    
    #Components fitted
    def _plot_compos(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi: return self.area_empty*self.area_empty
        elif y >= yf or y <= yi: return self.area_empty*self.area_empty
        else:
            x0,y0 = self.image_diff_small.closest((x,y))
            tag1 = ''.join([self.element1,self.components1[0],'_component'])
            tag2 = ''.join([self.element2,self.components2[0],'_component'])
            self.coor_x = str(x0)
            self.coor_y = str(y0)
            area1 = hv.Area(self.ds[tag1].isel(x = int(x0),y = int(y0)),\
                label = tag1.split('_component')[0])\
            .opts(line_color = 'navy',line_width=1.,line_alpha = 1,fill_alpha = 0.5,\
            fill_color = 'royalblue')
            area2 = hv.Area(self.ds[tag2].isel(x = int(x0),y = int(y0)),\
                label = tag2.split('_component')[0])\
            .opts(line_color = 'orange',line_width=1.,line_alpha = 1,fill_alpha = 0.5,\
            fill_color = 'gold')
            #.opts(color='darkred',fill_alpha=0.5,line_color='black')
            area1.relabel('Tick formatters').opts(yformatter=formatter)
            area2.relabel('Tick formatters').opts(yformatter=formatter)
            return area1*area2
    
    #Component 1 - center scatter plot
    def _plot_compo_val1(self,data):
        #Method for the dynamic map of SINGLE lines plotted
        try:
            if len(data['xs']) != 1:
                self.vert_x0 = ' - '
                self.vert_x1 = ' - '
                self.vert_y0 = ' - '
                self.vert_y1 = ' - '
                return self.scatter_empty
            else: 
                #Case of not having an entire segment yet - selection pending of completion
                if data['xs'][0][0] == data['xs'][0][1] and data['ys'][0][0] == data['ys'][0][1]:
                    return self.scatter_empty
                else:pass
            #We only support one segment
            x0,y0 = [data['xs'][0][0],data['ys'][0][0]]
            x1,y1 = [data['xs'][0][1],data['ys'][0][1]]
            vals = []
            list_segment_coords = self.algorithm_DDA(x0,x1,y0,y1)
            self.vert_x0 = str(list_segment_coords[0][0])
            self.vert_x1 = str(list_segment_coords[-1][0])
            self.vert_y0 = str(list_segment_coords[0][1])
            self.vert_y1 = str(list_segment_coords[-1][1])
            clave = ''.join([self.element1,self.components1[0],' Eloss center [eV]'])
            clav = ''.join([self.element1,self.components1[0],'_center'])
            for pon in list_segment_coords:
                vals.append(round(self.ds[clav].values[int(pon[1]),int(pon[0])],2))
            #.opts(size = 7.5,shared_axes = False,framewise = True,frame_width = 550,frame_height = )
            scat = hv.Scatter(xr.Dataset({clave:('x',np.array(vals))},coords={'x':np.arange(0,len(vals))}))\
            .opts(size = 9,frame_height = 275,frame_width = 550,show_grid = True,line_color = 'black',\
                shared_axes = False,title = 'Line Selection',yformatter=formatter4,\
                framewise = True,fill_color = 'royalblue')
            return scat
        except:
            return self.scatter_empty
    
    #Component 2 - center scatter plot
    def _plot_compo_val2(self,data):
        #Method for the dynamic map of SINGLE lines plotted
        try:
            if len(data['xs']) != 1:
                return self.scatter_empty
            else: 
                #Case of not having an entire segment yet - selection pending of completion
                if data['xs'][0][0] == data['xs'][0][1] and data['ys'][0][0] == data['ys'][0][1]:
                    return self.scatter_empty
                else:pass
            #We only support one segment
            x0,y0 = [data['xs'][0][0],data['ys'][0][0]]
            x1,y1 = [data['xs'][0][1],data['ys'][0][1]]
            vals = []
            list_segment_coords = self.algorithm_DDA(x0,x1,y0,y1)
            clave = ''.join([self.element2,self.components2[0],' Eloss center [eV]'])
            clav = ''.join([self.element2,self.components2[0],'_center'])
            for pon in list_segment_coords:
                vals.append(round(self.ds[clav].values[int(pon[1]),int(pon[0])],2))
            #.opts(size = 7.5,shared_axes = False,framewise = True,frame_width = 550,frame_height = )
            scat = hv.Scatter(xr.Dataset({clave:('x',np.array(vals))},coords={'x':np.arange(0,len(vals))}))\
            .opts(size = 9,frame_height = 275,frame_width = 550,show_grid = True,line_color = 'black',\
                shared_axes = False,title = 'Line Selection',framewise = True,\
                marker = 's',fill_color = 'gold',yformatter=formatter4)
            return scat
        except:
            return self.scatter_empty
    
    def _callback_show_comp2_feature(self,event):
        if self.components2[0] == 'K':
            clave11 = ''.join([self.element2,self.components2[0],'_onset'])
            clave12 = ''.join([self.element2,self.components2[0],' : Continuum-onset'])
        else:
            clave11 = ''.join([self.element2,self.components2[0],'_center'])
            clave12 = ''.join([self.element2,self.components2[0],' : ELNES-center'])

        data = self.ds[clave11]
        titl = clave12
        maxi = round(np.nanmax(data.values))
        mini = round(np.nanmin(data.values))
        self.param['range_cmap2'].bounds = (mini-5,maxi+5) 
        self.range_cmap2 = (mini,maxi)
        im = hv.Image(data)\
        .opts(cmap = self.colormap_2,invert_yaxis = True,\
            frame_width = 250,xaxis = None,yaxis = None,colorbar = True,\
            colorbar_position = 'right',toolbar = 'below',shared_axes = False,\
            xlim = self.xlims,ylim = self.ylims,\
            clim = (mini,maxi),clipping_colors = {'NaN': 'black'},title = titl)
        self.image_placeholder2.object = im
        self.slider_im2[0].disabled = False
        self.cmap_sel2[1].disabled = False
        
    def _callback_show_comp1_feature(self,event):
        if self.components1[0] == 'K':
            clave11 = ''.join([self.element1,self.components1[0],'_onset'])
            clave12 = ''.join([self.element1,self.components1[0],' : Continuum-onset'])
        else:
            clave11 = ''.join([self.element1,self.components1[0],'_center'])
            clave12 = ''.join([self.element1,self.components1[0],' : ELNES-center'])
        data = self.ds[clave11]
        titl = clave12
        maxi = round(np.nanmax(data.values))
        mini = round(np.nanmin(data.values))
        self.param['range_cmap1'].bounds = (mini-5,maxi+5) 
        self.range_cmap1 = (mini,maxi)
        im = hv.Image(data)\
        .opts(cmap = self.colormap_1,invert_yaxis = True,\
            frame_width = 250,xaxis = None,yaxis = None,colorbar = True,\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar_position = 'right',toolbar = 'below',shared_axes = False,\
            clim = (mini,maxi),clipping_colors = {'NaN': 'black'},title = titl)
        self.image_placeholder1.object = im
        self.slider_im1[0].disabled = False
        self.cmap_sel1[1].disabled = False
        
    @param.depends('dynamic_displays',watch = True)
    def _change_dyn_display(self):
        try:
            if self.dynamic_displays == 'Best':
                self.dinamic_struc.object = self.din_ori*self.din_best
            elif self.dynamic_displays == 'Comps.':
                self.dinamic_struc.object = self.din_ori*self.din_compos
            else:
                self.dinamic_struc.object = self.curve_empty
        except: 
            return
            
    def _create_dinmaps(self):
        self.path = hv.Path([[(0,0),(0,0)]]).opts(color = 'lime')
        self.path_stream =\
        streams.PolyDraw(source=self.path, drag=True,\
            vertex_style = {'color':'limegreen'},show_vertices=True,num_objects=1)
        self.message = pn.pane.Markdown('#### Selected pixel |- x : {} -|- y : {} -|'\
            .format(self.coor_x,self.coor_y),style = {'color':'grey'},width = 315,\
            margin = (5,5,5,25))
        self.message_line = pn.pane.Markdown(\
            '#### Selected line |- v0 : ({},{}) -|- v1 : ({},{}) -|'\
            .format(self.vert_x0,self.vert_y0,self.vert_x1,self.vert_y1),\
            style = {'color':'grey'},width = 315,margin = (5,5,5,25))
        self.image_diff_small = hv.Image(self.ds_dist.Distances)\
        .opts(cmap = self.colormap_diff,invert_yaxis=True,\
            xaxis = None,yaxis = None,toolbar = 'right',\
            frame_width = 275,title = self.current_selection,\
            colorbar = True,colorbar_position = 'right',\
            xlim = self.xlims,ylim = self.ylims,\
            shared_axes = False,clim = self.range_cmapDiff,\
            clipping_colors = {'NaN': 'black'},tools = ['tap'])
        self.tapxy = streams.SingleTap(x = -1,y = -1,source = self.image_diff_small)
        self.din_best = hv.DynamicMap(self._plot_best,\
            streams = [self.tapxy])\
        .opts(frame_height = 275,shared_axes = False,frame_width = 550,\
            framewise = True,show_title = True,title = 'Single pixel selection',\
            yformatter=formatter)
        self.din_ori = hv.DynamicMap(self._plot_original,\
            streams = [self.tapxy])\
        .opts(frame_height = 275,shared_axes = False,frame_width = 550,\
            framewise = True,show_title = True,title = 'Single pixel selection',\
            yformatter=formatter)
        self.din_compos = hv.DynamicMap(self._plot_compos,\
            streams = [self.tapxy])\
        .opts(frame_height = 275,shared_axes = False,frame_width = 550,\
            framewise = True,title = 'Single pixel selection',show_legend = True,\
            yformatter=formatter)
        self.din_draw = hv.DynamicMap(self._plot_compo_val1,streams=[self.path_stream])\
        .opts(frame_height = 275,shared_axes = False,frame_width = 550,\
            framewise = True,title = 'Dynamic line selection : center',\
            yformatter=formatter4)
        self.din_draw_2 = hv.DynamicMap(self._plot_compo_val2,streams=[self.path_stream])\
        .opts(frame_height = 275,shared_axes = False,frame_width = 550,\
            framewise = True,title = 'Dynamic line selection : center',\
            yformatter=formatter4)
        self.dinamic_struc = pn.pane.HoloViews(\
            self.din_ori*self.din_best,width = 625)
        self.dinamic_line_struc = pn.pane.HoloViews(\
            self.din_draw,width = 625)
    
    @param.depends('line_displays',watch = True)
    def _change_line_display(self):
        try:
            if self.line_displays == ''.join([self.element1,self.components1[0]]):
                self.dinamic_line_struc.object = self.din_draw
            elif self.line_displays == ''.join([self.element2,self.components2[0]]):
                self.dinamic_line_struc.object = self.din_draw_2
            else:
                self.dinamic_line_struc.object = self.scatter_empty
        except:
            return
                
    def _callback_show_diff_stats(self,event):
        clav1 = ''.join([self.element1,self.components1[0]])
        clav2 = ''.join([self.element2,self.components2[0]])
        self._create_dinmaps()
        self.param['line_displays'].objects = [clav1,clav2]
        self.line_displays = clav1
        self.button_selector_line_display = pn.Param(self.param['line_displays'],\
            widgets = {'line_displays':pn.widgets.RadioButtonGroup},\
            parameters = ['line_displays'],show_name = False, show_labels = False,\
            name = 'Dynamic line selection component',\
            width = 215,align = 'center')
        self.button_selector_line_display[0].button_type = 'warning'
        #self.button_selector_line_display[0].style = {'color':'white'}
        self.button_selector_dinamic_display = pn.Param(self.param['dynamic_displays'],\
            widgets = {'dynamic_displays':pn.widgets.RadioButtonGroup},\
            parameters = ['dynamic_displays'],show_name = False, show_labels = False,\
            name = 'Single pixel selection visualization',\
            width = 215,align = 'center')
        self.button_selector_dinamic_display[0].button_type = 'success'
        #self.button_selector_dinamic_display[0].style = {'color':'white'}
        #We create now the histograms
        if self.components2[0] == 'K':
            tag2 = ''.join([self.element2,self.components2[0],'_onset'])
        else:
            tag2 = ''.join([self.element2,self.components2[0],'_center'])
        if self.components1[0] == 'K':
            tag1 = ''.join([self.element1,self.components1[0],'_onset'])
        else:
            tag1 = ''.join([self.element1,self.components1[0],'_center'])
        mat_dist = np.nan_to_num(self.ds_dist.Distances.values)
        mat_compo1 = np.nan_to_num(self.ds[tag1].values)
        mat_compo2 =np.nan_to_num(self.ds[tag2].values)
        hist_dist = np.histogram(mat_dist[mat_dist != 0],\
            bins = max(1,int(np.sqrt(mat_dist[mat_dist != 0].size)))) 
        hist_compo1    = np.histogram(mat_compo1[mat_compo1 != 0],\
            bins = max(1,int(np.sqrt(mat_compo1[mat_compo1 != 0].size)))) 
        hist_compo2    = np.histogram(mat_compo2[mat_compo2 != 0],\
            bins = max(1,int(np.sqrt(mat_compo2[mat_compo2 != 0].size)))) 
        self.histo_dist =\
        hv.Histogram(hist_dist,kdims='Eloss [eV]',vdims='Absolute frequency')\
            .opts(border = 10,frame_height = 150,frame_width = 315,\
            gridstyle = {'color':'white'},show_grid = True,fill_alpha = 0.75,\
            cmap = self.colormap_diff,color = 'Eloss [eV]',\
            toolbar = 'right',bgcolor = 'grey',\
            default_tools = ['pan','wheel_zoom','box_zoom','reset'],\
            shared_axes = False,framewise = True,title = 'Components E-distance',\
            hooks =[hook_full_black_1],yformatter = formatter3)
        self.histo_comp1 =\
        hv.Histogram(hist_compo1,kdims='Eloss [eV]',vdims='Absolute frequency')\
            .opts(border = 10,frame_height = 150,frame_width = 315,\
            gridstyle = {'color':'white'},show_grid = True,fill_alpha = 0.75,\
            fill_color = 'royalblue',toolbar = 'right',bgcolor = 'grey',\
            shared_axes = False,framewise = True,yformatter = formatter3,\
            default_tools = ['pan','wheel_zoom','box_zoom','reset'],\
            title = ''.join([clav1,' central Eloss']),hooks =[hook_full_black_1])
        self.histo_comp2 =\
        hv.Histogram(hist_compo2,kdims='Eloss [eV]',vdims='Absolute frequency')\
            .opts(border = 10,frame_height = 150,frame_width = 315,\
            gridstyle = {'color':'white'},show_grid = True,fill_alpha = 0.75,\
            fill_color = 'gold',toolbar = 'right',bgcolor = 'grey',\
            default_tools = ['pan','wheel_zoom','box_zoom','reset'],\
            shared_axes = False,framewise = True,yformatter = formatter3,\
            title = ''.join([clav2,' central Eloss']),hooks =[hook_full_black_1])
        self._create_panel_structure_and_show()
        
    def _create_panel_structure_and_show(self):
        fila1 = pn.Row(pn.Column(self.image_diff_small*self.path,width = 400),self.dinamic_struc)
        fila2 = pn.Row(pn.Column(pn.pane.Markdown('### Select Displayed info',\
            width = 350,margin = 10),\
            pn.layout.Divider(height = 3,width = 340,align = 'center',margin = (-10,5,10,5)),\
            self.message, self.message_line,\
            pn.Row(pn.Spacer(height = 40,width = 15),pn.pane.Markdown('#### Single pixel'),\
                self.button_selector_dinamic_display),\
            pn.Row(pn.Spacer(height = 40,width = 15),pn.pane.Markdown('#### Single pixel'),\
                self.button_selector_line_display),\
            width = 400),\
        self.dinamic_line_struc)
        fila2[0][0].margin = (10,10,5,25)
        col1 = pn.Column(fila1,fila2)
        col1.margin = (0,10)
        col2 = pn.Column(self.histo_dist,self.histo_comp1,self.histo_comp2,\
            width = 425,background = 'grey',align = 'center')
        col2.margin = (0,0,0,35)
        banner = pn.Row(pn.pane.Markdown('### {} - {} Component center advanced analysis'\
            .format(''.join([self.element1,self.components1[0]]),\
                ''.join([self.element2,self.components2[0]])),\
                style = {'color':'white'},align = 'center',margin = (5,35),width = 1200),\
            background = 'black',height = 55,width = 1517,margin = 0)
        self.advance_panel = pn.Column(banner,\
            pn.Row(pn.Spacer(width = 25,height = 700 ,background='black'),col1,col2))
        self.advance_panel[1].margin = 0
        self.advance_panel[1][0].margin = 0
        self.advance_panel[0].margin = 0
        for el in self.advance_panel[1][-1]:
            el.margin = (0,15)
        self.advance_panel.show(title = 'Advanced Center-Eloss Analyser',threaded=True,verbose=False)
    
    def create_feature_distances_panel(self):
        #Method that creates the panel for the analysis of distances\
        # between components centers
        #Widgets for the center - distance calculators
        self.wid_el1 = pn.Param(self.param['element1'],\
            widgets = {'element1':pn.widgets.RadioButtonGroup},\
            parameters = ['element1'],width = 300,\
            show_name = False,show_labels = False,\
            margin = (5,5,0,5))
        self.wid_el1[0].height = 40
        self.wid_el2 = pn.Param(self.param['element2'],\
            widgets = {'element2':pn.widgets.RadioButtonGroup},\
            parameters = ['element2'],width = 300,\
            show_name = False,show_labels = False,\
            margin = (5,5,0,5))
        self.wid_el2[0].height = 40
        self.wid_compos1 = pn.Param(self.param['components1'],\
            widgets = {'components1':pn.widgets.MultiChoice},\
            parameters = ['components1'],width = 220,\
            show_name = False,show_labels = False)
        self.wid_compos2 = pn.Param(self.param['components2'],\
            widgets = {'components2':pn.widgets.MultiChoice},\
            parameters = ['components2'],width = 220,\
            show_name = False,show_labels = False)
        self.wid_compos1[0].max_items = 1
        self.wid_compos2[0].max_items = 1
        #widgets for the cmap
        # - limits sliders
        self.slider_im1 = pn.Param(self.param['range_cmap1'],\
            widgets = {'range_cmap1':pn.widgets.RangeSlider},\
            parameters = ['range_cmap1'],show_labels = True,\
            width = 250)
        self.slider_im2 = pn.Param(self.param['range_cmap2'],\
            widgets = {'range_cmap2':pn.widgets.RangeSlider},\
            parameters = ['range_cmap2'],show_labels = True,\
            width = 250)
        self.slider_im1[0].disabled = True
        self.slider_im2[0].disabled = True
        self.slider_im2[0].step = self.step
        self.slider_im1[0].step = self.step
        self.slider_diff = pn.Param(self.param['range_cmapDiff'],\
            widgets = {'range_cmapDiff':pn.widgets.RangeSlider},\
            parameters = ['range_cmapDiff'],show_labels = True,\
            width = 250)
        self.slider_diff[0].disabled = True
        self.slider_diff[0].step = self.step
        # - colormaps
        self.cmap_sel1 = pn.Param(self.param['colormap_1'],\
            widgets = {'colormap_1':pn.widgets.Select},\
            parameters = ['colormap_1'],width = 250,\
            name = 'Visual config',show_labels = False,show_name = True)
        self.cmap_sel2 = pn.Param(self.param['colormap_2'],\
            widgets = {'colormap_2':pn.widgets.Select},\
            parameters = ['colormap_2'],width = 250,\
            name = 'Visual config',show_labels = False,show_name = True)
        self.cmap_seldiff = pn.Param(self.param['colormap_diff'],\
            widgets = {'colormap_diff':pn.widgets.Select},\
            parameters = ['colormap_diff'],width = 250,\
            name = 'Visual config',show_labels = False,show_name = False)
        self.cmap_sel1[1].disabled = True
        self.cmap_sel2[1].disabled = True
        self.cmap_seldiff[0].disabled = True
        #Now a button to create the distance image
        self.button_dist_compos = pn.widgets.Button(name = 'Get distances',\
            align = 'center',height = 40,width = 220)
        self.button_dist_compos.on_click(self._callback_get_distances)
        self.button_dist_compos.disabled = True
        self.button_show_1 = pn.widgets.Button(name = 'Show',\
            align = 'center',disabled = True,width = 45,height = 40)
        self.button_show_1.on_click(self._callback_show_comp1_feature)
        self.button_show_2 = pn.widgets.Button(name = 'Show',\
            align = 'center',disabled = True,width = 45,height = 40)
        self.button_show_2.on_click(self._callback_show_comp2_feature)
        self.button_show_distances_panel =\
        pn.widgets.Button(name = 'Launch advanced analyser',\
            align = 'center',height = 40,width = 220)
        self.button_show_distances_panel.disabled = True
        self.button_show_distances_panel.on_click(self._callback_show_diff_stats)
        #Let's build the structure
        self.image_placeholder1     = pn.pane.HoloViews(self.im_empty)
        self.image_placeholder2     = pn.pane.HoloViews(self.im_empty)
        self.image_placeholder_diff = pn.pane.HoloViews(self.im_empty_diff)
        self.compo_row = pn.Row(\
            pn.Column(\
                self.wid_el1,\
                pn.Row(self.wid_compos1,self.button_show_1),\
                self.image_placeholder1,self.cmap_sel1,\
                self.slider_im1,width  =350),\
            pn.Column(\
                self.wid_el2,\
                pn.Row(self.wid_compos2,self.button_show_2),\
                self.image_placeholder2,self.cmap_sel2,\
                self.slider_im2,width  =350),margin = (10,15))
        for el in self.compo_row:
            el.margin = (0,15)
        diff_panel = pn.Column(\
            pn.Row(self.button_dist_compos,self.button_show_distances_panel),\
            self.image_placeholder_diff,\
            pn.Row(self.cmap_seldiff,self.slider_diff),\
            margin = (15,15))
        self.distance_panel = pn.Column(\
                pn.Row(pn.pane.Markdown('### Distance between components analyser',\
                style = {'color':'white'},align = 'center',margin =(5,35))\
                ,background = 'black',height = 55,width = 1500),\
            pn.Row(pn.Spacer(width = 25,height = 650 ,background='black'),\
                self.compo_row,diff_panel,margin = 0))
        self.distance_panel[1][0].margin = 0

#################################################################################################
#                                                                                               #
#                                                                                               #
#                      Display for the WL  Advanced FWHM analysis tool                          #
#                                                                                               #
#                                                                                               #
#################################################################################################
class Advanced_visualizer_WL_ratio_FWHM(param.Parameterized):
    numb = param.Integer(default=0)
    data_disp = param.Boolean(default=False)
    
    def __init__(self,original_ds,ratios_ds,cmap):
        self.ds = original_ds
        xsize = self.ds.x.values.size
        ysize = self.ds.y.values.size
        dist = abs(ysize-xsize)
        if xsize < ysize:
            self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
            self.ylims = (-0.5,ysize-0.5)
        else:
            self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
            self.xlims = (-0.5,xsize-0.5)
        int_dataset =\
            ((ratios_ds['EnergyLimits'].isel(lim = 1)\
            -ratios_ds['EnergyLimits'].isel(lim = 0))/2)\
            .to_dataset(name = 'Integration_ranges')
        self.dataset_auto = xr.merge([ratios_ds,int_dataset])
        self.cmap_introd = cmap
        self.limsE_axis = (self.ds.Eloss.values[0],self.ds.Eloss.values[-1])
        self.multi_complex = cp.deepcopy(self.dataset_auto.mult.values)
        #Creation of some tooltips to inspect data
        TT_coords = [("x","@x"),("y","@y")]
        TT_ratio = [("x","@x"),("y","@y"),("Ratio","@Components_Ratios")]
        TT_ratio_i = [("x","@x"),("y","@y"),("Ratio","@Components_Inverted_Ratios")]
        TT_scatter = [("Multiplier","@mult"),("Ratio","@Components_Ratios")]
        TT_scatter_i = [("Multiplier","@mult"),("Ratio","@Components_Inverted_Ratios")]
        self.hover_tip_coords = HoverTool(tooltips=TT_coords)
        self.hover_ratio = HoverTool(tooltips=TT_ratio)
        self.hover_ratio_i = HoverTool(tooltips=TT_ratio_i)
        self.hover_scatter = HoverTool(tooltips = TT_scatter, mode = 'vline')
        self.hover_scatter_i = HoverTool(tooltips = TT_scatter_i, mode = 'vline')
        #Creation of the images to gloss over
        self.im = hv.Image(self.ds.OriginalData.sum('Eloss'))\
            .opts(cmap = 'greys_r',invert_yaxis = True,\
            frame_height=275, xlim = self.xlims,ylim = self.ylims,\
            xaxis = None,yaxis = None,alpha = 0,shared_axes = False)
        self.hmap = hv.HeatMap(self.ds.OriginalData.sum('Eloss'))\
            .opts(cmap = 'greys_r',invert_yaxis = True,frame_height=275,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                xlim = self.xlims,ylim = self.ylims,\
                nonselection_fill_alpha = 0.75,line_width = 1.25,\
                line_color = 'grey',selection_line_color = 'red',\
                nonselection_line_color = 'grey',alpha = 0.75,\
                hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = ['tap',self.hover_tip_coords],shared_axes = False)
        #Data for the empty curves
        self.hov_lims = (self.ds.x.values[0]-0.5,self.ds.x.values[-1]+\
                0.5,self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        empty_Data =\
            xr.Dataset({'EmptyData':(['y','x','Eloss'],\
            np.zeros_like(self.ds.OriginalData.values)),\
            'EmptyScatter':(['mult'],np.zeros_like(self.multi_complex))},\
            coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
            'Eloss':self.ds.Eloss.values,'mult':self.multi_complex})
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True)
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,\
            shared_axes = False,yformatter=formatter,\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black',framewise = True)
        self.scatter_empty = hv.Scatter(empty_Data.EmptyScatter)\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True,\
            tools = [self.hover_scatter],\
            line_color = 'black',fill_color = 'white',size = 7.5)
        self.scatter_curve_empty = hv.Curve(empty_Data.EmptyScatter)\
        .opts(frame_height = 275,frame_width = 550,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True,\
            tools = [self.hover_scatter],line_color = 'black')
        self.scatter_line_empty = hv.Scatter([])\
            .opts(xlabel='Position along line (pixel)',ylabel = 'Components Ratio',\
                size = 9,frame_height = 150,frame_width = 250,\
                line_color = 'darkgreen',fill_color = 'lime',fill_alpha = 0.5,\
                shared_axes = False,yformatter=formatter4,\
                framewise = True,gridstyle = {'color':'white'},show_grid = True,\
                bgcolor = 'grey',hooks =[hook_full_black_1],\
                title = 'None Line selected')
        #hv.Image(self.ds.OriginalData.sum('Eloss'))\
        self.im_empty = hv.Image(empty_Data.EmptyData.sum('Eloss'))\
            .opts(cmap = 'greys_r',invert_axes = True,invert_yaxis = True,\
            frame_height=275,xaxis = None,yaxis = None,shared_axes = False,\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar = True,colorbar_position = 'bottom')
        self.empty_VLine = hv.VLine(self.ds.Eloss.values[-1])\
            .opts(color = 'black',line_alpha = 0,line_width = 0,\
            shared_axes = False,frame_width=550,frame_height=275)
        empty_vspan = hv.VSpan(self.ds.Eloss.values[0],self.ds.Eloss.values[-1])\
        .opts(shared_axes = False,frame_width=550,frame_height=275,fill_alpha = 0,line_alpha = 0)
        self.empty_vspan = empty_vspan*empty_vspan
        self.stream_tapping  = streams.SingleTap(x = -1,y = -1,source = self.im)
        self.path = hv.Path([[(0,0),(0,0)]]).opts(color = 'gold',\
            line_width = 4,line_alpha = 0.5)
        self.path_stream =\
        streams.PolyDraw(source=self.path, drag=True,\
            vertex_style = {'color':'gold','line_color':'orangered'},\
            show_vertices=True,num_objects=1)
        #We begin here with the mods needed
        self.param['numb'].label = 'Positional index'
        self.param['numb'].bounds = (0,int(self.multi_complex.size)-1)
        self.slider_number = pn.Param(self.param['numb'],\
            widgets = {'numb':pn.widgets.IntSlider},\
            parameters = ['numb'],show_name = False,show_labels = True,\
            align = 'center',width = 200)
        self.slider_number[0].bar_color = '#FFFFFF'
        self.slider_number[0].formatter = ('formatter_trial')
        self.numb_markdown = pn.pane.Markdown('#### FWHM multiplier',width = 90,\
            style = {'color':'white'},margin= (5,0,5,35))
        #Some buttons
        self.button_refresh_scatter_line = pn.widgets.Button(name = '\u21bb',\
            align = 'center',button_type = 'warning',width = 50,margin = (5,0))
        self.button_refresh_scatter_line.on_click(self._callback_resfresh_ratio_line)
        self.button_invert_ratio_shown = pn.widgets.Button(name = 'Invert ratio shown',\
            align = 'center',width = 150,button_type = 'warning')
        self.button_invert_ratio_shown.on_click(self._callback_invert_ratio_show)
        self.button_data_displayed = pn.widgets.Button(name = 'Original data',\
            width  =150,align='center')
        self.button_data_displayed.on_click(self._callback_show_integrated_data_overlayed)
        #The markdown for the shown ratio
        comp1_str = self.dataset_auto.comp.values[1]
        comp0_str = self.dataset_auto.comp.values[0]
        self.shown_ratio = pn.pane.Markdown('#### Ratio on display : {} / {}'\
            .format(comp1_str,comp0_str),style = {'color':'orange'},margin = (0,25),\
            height = 35,width = 325)
        self.direct_image = True
    
    def _callback_show_integrated_data_overlayed(self,event):
        if not self.data_disp:
            self.button_data_displayed.button_type = 'danger'
            self.button_data_displayed.name = 'Inegrated data'
            self.spectra_pane.object = self.dyn_data*self.dyn_fwhm*\
                self.dyn_data_int
            self.data_disp = True
        else:
            self.button_data_displayed.button_type = 'default'
            self.button_data_displayed.name = 'Original data'
            self.spectra_pane.object = self.dyn_data*self.dyn_fwhm
            self.data_disp = False
    
    def _callback_resfresh_ratio_line(self,event):
        #self.din_modif_ori.event(x = x, y = y)
        if self.direct_image:
            prev_data = cp.deepcopy(self.path_stream.data)
            self.dyn_draw.event(data = {'x0':[0],'y0':[0]})
            self.dyn_draw.event(data = prev_data)
            self.dynamic_line_pane.object = self.dyn_draw
        else:
            prev_data = cp.deepcopy(self.path_stream.data)
            self.dyn_draw_i.event(data = {'x0':[0],'y0':[0]})
            self.dyn_draw_i.event(data = prev_data)
            self.dynamic_line_pane.object = self.dyn_draw_i
    
    def _callback_invert_ratio_show(self,event):
        if self.direct_image:
            self.image_rat_pane.object = self.dyn_image_ratios_i*self.path
            self.scatter_pane.object = self.dyn_ratios_scatt_i\
            .opts(framewise = True,shared_axes = False,\
            tools = [self.hover_scatter_i],frame_width = 550,frame_height = 275)\
            *self.dyn_vline
            self.dynamic_line_pane.object = self.dyn_draw_i
            self.direct_image = False
            self._callback_resfresh_ratio_line(None)
            comp1_str = self.dataset_auto.comp.values[1]
            comp0_str = self.dataset_auto.comp.values[0]
            self.shown_ratio.object = '#### Ratio on display : {} / {}'\
                .format(comp0_str,comp1_str)
        else:
            self.image_rat_pane.object = self.dyn_image_ratios*self.path
            self.scatter_pane.object = self.dyn_ratios_scatt\
            .opts(framewise = True,shared_axes = False,\
            tools = [self.hover_scatter_i],frame_width = 550,frame_height = 275)\
            *self.dyn_vline_i
            self.dynamic_line_pane.object = self.dyn_draw
            self.direct_image = True
            self._callback_resfresh_ratio_line(None)
            comp1_str = self.dataset_auto.comp.values[1]
            comp0_str = self.dataset_auto.comp.values[0]
            self.shown_ratio.object = '#### Ratio on display : {} / {}'\
                .format(comp1_str,comp0_str)
    
    @param.depends('numb',watch = True)
    def _plot_vline_ratio_postition(self):
        linea = hv.VLine(x = self.dataset_auto.mult.values[self.numb])\
            .opts(line_width = 1.25,line_alpha = 1,line_color = 'red',\
            framewise = True,frame_width = 550,frame_height = 275,shared_axes = False)
        return linea
    
    @param.depends('numb',watch = True)
    def _plot_vline_inverted_ratio_postition(self):
        linea = hv.VLine(x = self.dataset_auto.mult.values[self.numb])\
            .opts(line_width = 1.25,line_alpha = 1,line_color = 'red',\
            framewise = True,frame_width = 550,frame_height = 275,shared_axes = False)
        return linea
    
    @param.depends('numb',watch = True)  
    def _plot_int_windows_fwhm(self,x = -1,y = -1):
        #print('changing')
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_vspan
        elif y >= yf or y <= yi:
            return self.empty_vspan
        else:
            x0,y0 = self.im.closest((x,y))
            x0 = int(x0)
            y0 = int(y0)
            #print(x0,y0)
            try:
                lim00,lim10 = self.dataset_auto.isel(x = x0,y = y0,mult = self.numb)\
                .EnergyLimits.values[0]
                lim01,lim11 = self.dataset_auto.isel(x = x0,y = y0,mult = self.numb)\
                .EnergyLimits.values[1]
            except:
                return self.empty_vspan
            else:
                if any([el.astype('int32') < 0 for el in [lim00,lim01,lim10,lim11]]):
                    #This is to avoid the nan values of non fitted areas
                    return self.empty_vspan
                else:
                    span1 = hv.VSpan(x1 = lim00,x2 = lim01)\
                    .opts(shared_axes=False,fill_alpha = 0.25,fill_color = 'dodgerblue',\
                    line_alpha = 1,line_color = 'blue')
                    span2 = hv.VSpan(x1 = lim10,x2 = lim11)\
                    .opts(fill_alpha = 0.25,fill_color = 'limegreen',\
                    line_alpha = 1,line_color = 'darkgreen',shared_axes = False)
                    return span1*span2
    
    def _plot_curve(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            x0,y0 = self.im.closest((x,y))
            self.x_pos = int(x0)
            self.y_pos = int(y0)
            area = hv.Area(self.ds.OriginalData.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,line_width=1,\
                line_alpha = 0,yformatter=formatter,line_color = 'black',\
                shared_axes = False,framewise = True,fill_color = 'grey',fill_alpha = 0.75)
            return area
    
    
    @param.depends('numb',watch = True)
    def _plot_histo_comp1(self):
        ima_his1 = hv.Image(self.dataset_auto['Integration_ranges']\
        .isel(comp = 0,mult = self.numb))\
        .opts(invert_yaxis = True,xaxis = None,yaxis = None,\
            clipping_colors = {'NaN':'black'},cmap = 'jet',frame_height = 268,\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar = True,colorbar_position='bottom')
        hito1 = ima_his1.hist(adjoin=False)
        return hito1.opts(frame_height = 150,frame_width = 215,\
            toolbar = None,yaxis = None,hooks =[hook_full_black_1],\
            yformatter = formatter3,bgcolor = 'grey',color = 'dodgerblue',\
            gridstyle = {'color':'white'},show_grid = True,\
            fill_alpha = 0.75,xlabel = 'Integration semiwidth [eV]',\
            title = 'Component : {}'.format(self.dataset_auto.comp.values[0]))
    
    @param.depends('numb',watch = True)
    def _plot_histo_comp2(self):
        ima_his2 = hv.Image(self.dataset_auto['Integration_ranges']\
        .isel(comp = 1,mult = self.numb))\
        .opts(invert_yaxis = True,xaxis = None,yaxis = None,\
            clipping_colors = {'NaN':'black'},cmap = 'jet',frame_height = 268,\
            xlim = self.xlims,ylim = self.ylims,\
            colorbar = True,colorbar_position='bottom')
        hito2 = ima_his2.hist(adjoin=False)
        return hito2.opts(frame_height = 150,frame_width = 215,\
            toolbar = None,yaxis = None,hooks =[hook_full_black_1],\
            yformatter = formatter3,bgcolor = 'grey',color = 'limegreen',\
            gridstyle = {'color':'white'},show_grid = True,\
            fill_alpha = 0.75,xlabel = 'Integration semiwidth [eV]',\
            title = 'Component : {}'.format(self.dataset_auto.comp.values[1]))
    
    
    @param.depends('numb',watch = True) 
    def _plot_graph_ratios(self,x = -1,y = -1):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.scatter_curve_empty*self.scatter_empty
        elif y >= yf or y <= yi:
            return self.scatter_curve_empty*self.scatter_empty
        else:
            x0,y0 = self.im.closest((x,y))
            scat = hv.Scatter(self.dataset_auto.Components_Ratios.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,yformatter=formatter,line_color = 'black',fill_color = 'white',\
                selection_fill_color = 'red',selection_fill_alpha = 1,size = 7.5,fill_alpha = 0.5,\
                shared_axes = False, framewise = True,tools = [self.hover_scatter],frame_height = 275,\
                frame_width = 550)
            curv = hv.Curve(self.dataset_auto.Components_Ratios.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,yformatter=formatter,line_color = 'black',frame_height = 275,\
                frame_width = 550,line_width = 1,shared_axes = False,\
                framewise = True,tools = [self.hover_scatter])
            return curv*scat
        
    @param.depends('numb',watch = True) 
    def _plot_graph_inverted_ratios(self,x = -1,y = -1):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.scatter_curve_empty*self.scatter_empty
        elif y >= yf or y <= yi:
            return self.scatter_curve_empty*self.scatter_empty
        else:
            x0,y0 = self.im.closest((x,y))
            scat = hv.Scatter(self.dataset_auto.Components_Inverted_Ratios.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,yformatter=formatter,line_color = 'black',fill_color = 'white',\
                selection_fill_color = 'red',selection_fill_alpha = 1,size = 7.5,fill_alpha = 0.5,\
                shared_axes = False, framewise = True,tools = [self.hover_scatter_i],\
                frame_height = 275,frame_width = 550)
            curv = hv.Curve(self.dataset_auto.Components_Inverted_Ratios.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,yformatter=formatter,line_color = 'black',\
                frame_height = 275,frame_width = 550,line_width = 1,shared_axes = False,\
                framewise = True,tools = [self.hover_scatter_i])
            return curv*scat
    
    @param.depends('numb',watch = True)
    def _plot_image_ratios(self):
        imi = hv.HeatMap(self.dataset_auto.Components_Ratios.isel(mult = self.numb))\
        .opts(cmap = self.cmap_introd,invert_yaxis = True, frame_height=275,\
            colorbar = True,colorbar_position='bottom',clipping_colors={'NaN':'black'},\
            xlim = self.xlims,ylim = self.ylims,\
            tools = [self.hover_ratio],xaxis = None,yaxis = None)
        return imi
    
    @param.depends('numb',watch = True)
    def _plot_image_inverted_ratios(self):
        imi = hv.HeatMap(self.dataset_auto.Components_Inverted_Ratios.isel(mult = self.numb))\
        .opts(cmap = self.cmap_introd,invert_yaxis = True, frame_height=275,\
            colorbar = True,colorbar_position='bottom',clipping_colors={'NaN':'black'},\
            xlim = self.xlims,ylim = self.ylims,\
            tools = [self.hover_ratio_i],xaxis = None,yaxis = None)
        return imi
    
    def _plot_integration_data(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.curve_empty*self.curve_empty
        elif y >= yf or y <= yi:
            return self.curve_empty*self.curve_empty
        else:
            x0,y0 = self.im.closest((x,y))
            self.x_pos = int(x0)
            self.y_pos = int(y0)
            compo0 = self.dataset_auto.comp.values[0]
            compo1 = self.dataset_auto.comp.values[1]
            curve0 = hv.Curve(self.dataset_auto[compo0].isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,line_width=1,\
                yformatter=formatter,line_color = 'red',\
                shared_axes = False,framewise = True)
            curve1 = hv.Curve(self.dataset_auto[compo1].isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,line_width=1,\
                yformatter=formatter,line_color = 'red',\
                shared_axes = False,framewise = True)
            return curve0*curve1
        
    def algorithm_DDA(self,xi,xf,yi,yf):
        #Digital differential analyzer (DDA) - getting the pixels in the line
        dx = (xf-xi)
        dy = (yf-yi)
        if abs(dx) >= abs(dy):
            step = abs(dx)
        else:
            step = abs(dy)
        dx /= step
        dy /= step
        list_x = []
        list_y = []
        idx_im = []
        i = 1
        x = xi
        y = yi
        while i<= step:
            list_x.append(x)
            list_y.append(y)
            x += dx
            y += dy
            #to make them integers
            #x,y = im.closest((x,y))
            i += 1
        #At the end, we correct to get the actual pixel possitions
        for i,el in enumerate(list_x):
            #We are applying this to the image we are interest on
            idx_im.append(self.im.closest((el,list_y[i])))
        x,y = self.im.closest((xf,yf))
        idx_im.append((x,y))
        return idx_im
    
    def _plot_compo_val1(self,data):
        #Method for the dynamic map of SINGLE lines plotted
        try:
            if len(data['xs']) != 1:
                self.vert_x0 = ' - '
                self.vert_x1 = ' - '
                self.vert_y0 = ' - '
                self.vert_y1 = ' - '
                return self.scatter_line_empty
            else: 
                #Case of not having an entire segment yet - selection pending of completion
                if data['xs'][0][0] == data['xs'][0][1] and data['ys'][0][0] == data['ys'][0][1]:
                    return self.scatter_line_empty
                else:pass
            #We only support one segment
            x0,y0 = [data['xs'][0][0],data['ys'][0][0]]
            x1,y1 = [data['xs'][0][1],data['ys'][0][1]]
            vals = []
            list_segment_coords = self.algorithm_DDA(x0,x1,y0,y1)
            self.vert_x0 = str(list_segment_coords[0][0])
            self.vert_x1 = str(list_segment_coords[-1][0])
            self.vert_y0 = str(list_segment_coords[0][1])
            self.vert_y1 = str(list_segment_coords[-1][1])
            #clave = ''.join([self.element1,self.components1[0],' Eloss center [eV]'])
            #clav = ''.join([self.element1,self.components1[0],'_center'])
            for pon in list_segment_coords:
                vals.append(round(self.dataset_auto.Components_Ratios.isel(mult = self.numb).values[int(pon[1]),int(pon[0])],2))
            #.opts(size = 7.5,shared_axes = False,framewise = True,frame_width = 550,frame_height = )
            scat_data = xr.Dataset({'Ratio for multiplier':('x',np.array(vals))},\
                coords={'x':np.arange(0,len(vals))})
            scat = hv.Scatter(scat_data)\
            .opts(xlabel='Position along line (pixel)',ylabel = 'Components Ratio',\
                size = 9,frame_height = 150,frame_width = 250,\
                line_color = 'orangered',fill_color = 'gold',fill_alpha = 0.5,\
                shared_axes = False,yformatter=formatter4,\
                framewise = True,gridstyle = {'color':'white'},show_grid = True,\
                bgcolor = 'grey',hooks =[hook_full_black_1],\
                title = 'Line selected - multiplier : {}'\
                    .format(str(self.multi_complex[self.numb])))
            return scat
        except:
            return self.scatter_line_empty
        
    def _plot_compo_val1_invert(self,data):
        #Method for the dynamic map of SINGLE lines plotted
        try:
            if len(data['xs']) != 1:
                self.vert_x0 = ' - '
                self.vert_x1 = ' - '
                self.vert_y0 = ' - '
                self.vert_y1 = ' - '
                return self.scatter_line_empty
            else: 
                #Case of not having an entire segment yet - selection pending of completion
                if data['xs'][0][0] == data['xs'][0][1] and data['ys'][0][0] == data['ys'][0][1]:
                    return self.scatter_line_empty
                else:pass
            #We only support one segment
            x0,y0 = [data['xs'][0][0],data['ys'][0][0]]
            x1,y1 = [data['xs'][0][1],data['ys'][0][1]]
            vals = []
            list_segment_coords = self.algorithm_DDA(x0,x1,y0,y1)
            self.vert_x0 = str(list_segment_coords[0][0])
            self.vert_x1 = str(list_segment_coords[-1][0])
            self.vert_y0 = str(list_segment_coords[0][1])
            self.vert_y1 = str(list_segment_coords[-1][1])
            #clave = ''.join([self.element1,self.components1[0],' Eloss center [eV]'])
            #clav = ''.join([self.element1,self.components1[0],'_center'])
            for pon in list_segment_coords:
                vals.append(round(self.dataset_auto.Components_Inverted_Ratios.isel(mult = self.numb).values[int(pon[1]),int(pon[0])],2))
            #.opts(size = 7.5,shared_axes = False,framewise = True,frame_width = 550,frame_height = )
            scat_data = xr.Dataset({'Ratio for multiplier':('x',np.array(vals))},\
                coords={'x':np.arange(0,len(vals))})
            scat = hv.Scatter(scat_data)\
            .opts(xlabel='Position along line (pixel)',ylabel = 'Components Ratio',\
                size = 9,frame_height = 150,frame_width = 250,\
                line_color = 'orangered',fill_color = 'gold',fill_alpha = 0.5,\
                shared_axes = False,yformatter=formatter4,\
                framewise = True,gridstyle = {'color':'white'},show_grid = True,\
                bgcolor = 'grey',hooks =[hook_full_black_1],\
                title = 'Line selected - multiplier : {}'\
                    .format(str(self.multi_complex[self.numb])))
            return scat
        except:
            return self.scatter_line_empty
    
    def create_dynamic_maps(self):
        self.dyn_draw = hv.DynamicMap(self._plot_compo_val1,streams=[self.path_stream])\
            .opts(frame_height = 175,shared_axes = False,frame_width = 300,\
            framewise = True,\
            yformatter=formatter4)
        self.dyn_draw_i = hv.DynamicMap(self._plot_compo_val1_invert,streams=[self.path_stream])\
            .opts(frame_height = 175,shared_axes = False,frame_width = 300,\
            framewise = True,\
            yformatter=formatter4)
        self.dyn_data = hv.DynamicMap(self._plot_curve,streams=[self.stream_tapping])\
            .opts(framewise = True,shared_axes = False,frame_height=275,frame_width=550)
        self.dyn_data_int = hv.DynamicMap(self._plot_integration_data,streams=[self.stream_tapping])\
            .opts(framewise = True,shared_axes = False,frame_height=275,frame_width=550)
        self.dyn_ratios_scatt = hv.DynamicMap(self._plot_graph_ratios,streams=[self.stream_tapping])\
            .opts(framewise = True,tools=['hover'],shared_axes = False,frame_height = 275,frame_width = 550)
        self.dyn_ratios_scatt_i = hv.DynamicMap(self._plot_graph_inverted_ratios,streams=[self.stream_tapping])\
            .opts(framewise = True,tools=['hover'],shared_axes = False,frame_height = 275,frame_width = 550)
        self.dyn_image_ratios = hv.DynamicMap(self._plot_image_ratios)\
            .opts(shared_axes = False,tools = [self.hover_ratio])
        self.dyn_image_ratios_i = hv.DynamicMap(self._plot_image_inverted_ratios)\
            .opts(shared_axes = False,tools = [self.hover_ratio_i])
        self.dyn_vline = hv.DynamicMap(self._plot_vline_ratio_postition)\
            .opts(framewise=True,shared_axes = False)
        self.dyn_vline_i = hv.DynamicMap(self._plot_vline_inverted_ratio_postition)\
            .opts(framewise=True,shared_axes = False)
        self.dyn_fwhm = hv.DynamicMap(self._plot_int_windows_fwhm,streams=[self.stream_tapping])\
        .opts(shared_axes = False)
        self.dyn_histo1 = hv.DynamicMap(self._plot_histo_comp1)\
        .opts(shared_axes = False,framewise = True,frame_height=150,frame_width=200)
        self.dyn_histo2 = hv.DynamicMap(self._plot_histo_comp2)\
        .opts(shared_axes = False,framewise = True,frame_height=150,frame_width=200)
        
    def layout(self):
        #Lateral Bar
        self.create_dynamic_maps()
        self.dynamic_line_pane = pn.pane.HoloViews(self.dyn_draw,align = 'center')
        self.dyn_placement_histo1 = pn.pane.HoloViews(self.dyn_histo1)
        self.dyn_placement_histo2 = pn.pane.HoloViews(self.dyn_histo2)
        self.button_column = pn.Column(\
            pn.pane.Markdown('### Statistic information and graph-controls',\
                style = {'color':'white'},width = 350,margin = (5,15,0,25)),\
            pn.Row(self.button_data_displayed,\
            self.button_invert_ratio_shown,align = 'center',width = 350),\
            self.shown_ratio,
            pn.Row(self.numb_markdown,self.slider_number,self.button_refresh_scatter_line),\
            pn.layout.Divider(width = 350,align='center'),\
            self.dynamic_line_pane,\
            pn.layout.Divider(width = 350,align='center'),\
            pn.pane.Markdown('#### Histograms for the integration widths',\
                style = {'color':'white'},width = 325,margin = (-10,25,0,25),height = 35),\
            pn.Row(self.dyn_histo1,self.dyn_histo2,align = 'center',margin = (0,20)),\
            background='grey',width = 475)
        #Now the layout building
        #self.image_pane = pn.pane.HoloViews(self.hmap*self.im*self.path)
        self.image_pane = pn.pane.HoloViews(self.hmap*self.im)
        self.image_rat_pane = pn.pane.HoloViews(self.dyn_image_ratios*self.path)
        self.scatter_pane = pn.pane.HoloViews(self.dyn_ratios_scatt*self.dyn_vline)
        self.scatter_pane.object = self.scatter_pane.object.opts(framewise = True,\
            shared_axes = False,tools = [self.hover_scatter],frame_width = 550,frame_height = 275)
        self.spectra_pane = pn.pane.HoloViews(self.dyn_data*self.dyn_fwhm)
        self.fila1 = pn.Row(self.image_pane,self.spectra_pane,height = 350)
        self.fila2 = pn.Row(self.image_rat_pane,self.scatter_pane,height = 350)
        self.fila0 = pn.Row(pn.pane.Markdown('### Advanced analysis tool - FWHM integration mode',\
            style = {'color':'white'},margin = (5,25),width = 700),\
            height = 50,width = 1000,background='grey')
        self.col1 = pn.Column(self.fila0,self.fila1,self.fila2)
        layout = pn.Row(self.col1,self.button_column)
        layout.show(title = 'Advanced FWHM-WL analyser',threaded=True,verbose = False)
        
        

#################################################################################################
#                                                                                               #
#                                                                                               #
#                      Display for the WL     analysis tool                                     #
#                                                                                               #
#                                                                                               #
#################################################################################################
class Visual_WL_ratio(param.Parameterized):
    full_edge = param.ObjectSelector()
    mode_integration  = param.ObjectSelector(default='auto',objects = ['auto','advanced'])
    width_integration = param.ObjectSelector(default='fwhm',objects = ['fwhm','manual'])
    width_manual_integration = param.ObjectSelector(default='fixed',objects=['fixed','individual'])
    computation_values = param.ObjectSelector(default='Fitted data',objects=['Fitted data','Raw data'])
    #integration_semiwidth = param.Number(default=0.00)
    integration_E0 = param.Number(default=0.00)
    integration_E1 = param.Number(default=0.00)
    fixed_integration_semiwidth = param.Number(default=4.00)
    components_per_edge = param.ObjectSelector()
    #numb = param.Number(default=0.25,bounds=(0.25,5))
    '''
    numb = param.Integer(default=0)
    numb_value = param.String(default='0.25')
    '''
    components_to_integrate = param.ListSelector()
    components_to_substract = param.ListSelector(default=[],objects=[])
    include_continuum = param.Boolean(default=False)
    #extra_corrections = param.Boolean(default=False)
    colormap_1 = param.ObjectSelector(default= 'viridis',objects=['viridis'])
    range_cmap1    = param.Range(label = 'Colorbar range [eV] ')
    #progress bars
    num_prog1 = param.Integer(default=0)
    #Showing integration windows
    show_wind = param.Boolean(default=False)
    show_centers = param.Boolean(default=False)
    #This controls some options only available when performing FWHM dependent calcuations
    fwhm_run = param.Boolean(default = False)
    
    
    def __init__(self,ds,colores = dict(),elems= list()):
        super().__init__()
        #We configure some of the elements
        self.ds = ds
        xsize = self.ds.x.values.size
        ysize = self.ds.y.values.size
        dist = abs(ysize-xsize)
        if xsize < ysize:
            self.xlims = (-0.5-dist/2,xsize-0.5+dist/2)
            self.ylims = (-0.5,ysize-0.5)
        else:
            self.ylims = (-0.5-dist/2,ysize-0.5+dist/2)
            self.xlims = (-0.5,xsize-0.5)
        self.elements_list = elems
        #This is for the multiplier - those numbers are allowed as multipliers of fwhm
        multi_simple1 = np.linspace(0.25,1,12,endpoint=False)
        multi_simple2 = np.linspace(1,6,17)
        self.multi_complex = np.concatenate((multi_simple1,multi_simple2))
        #Colormaps available
        self.param['colormap_1'].objects =\
        hv.plotting.util.list_cmaps(category='Uniform Sequential')
        #now a little trick to know the E resolution
        step = self.ds.Eloss.values[1] - self.ds.Eloss.values[0] 
        if len(str(step).split('.')) == 1:
            self.param['integration_E0'].step = 1
            self.param['integration_E1'].step = 1
            self.param['fixed_integration_semiwidth'].step = 1
        else: 
            expo = len(str(step).split('.')[-1])
            self.param['integration_E0'].step = 1/10**expo
            self.param['integration_E1'].step = 1/10**expo
            self.param['fixed_integration_semiwidth'].step = 1/10**expo
        '''
        self.param['numb'].label = 'Positional index'
        self.param['numb'].bounds = (0,int(self.multi_complex.size)-1)
        '''
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
        #Now the edges available for analysis - full edges with all the ELNES
        self.get_keywords()
        #Now we prepare the image and the heatmap
        #We desing a tooltip for hovering
        TT_coords = [("x","@x"),("y","@y")]
        TT_ratio = [("x","@x"),("y","@y"),("Ratio","@Components_Ratios")]
        TT_ratio_i = [("x","@x"),("y","@y"),("Ratio","@Components_Inverted_Ratios")]
        self.hover_tip_coords = HoverTool(tooltips=TT_coords)
        self.hover_ratio = HoverTool(tooltips=TT_ratio)
        self.hover_ratio_i = HoverTool(tooltips=TT_ratio_i)
        self.im = hv.Image(self.ds.OriginalData.sum('Eloss'))\
            .opts(cmap = 'greys_r',invert_yaxis = True, frame_height=325,\
            xlim = self.xlims,ylim = self.ylims,\
            xaxis = None,yaxis = None,alpha = 0,shared_axes = False)
        self.hmap = hv.HeatMap(self.ds.OriginalData.sum('Eloss'))\
            .opts(cmap = 'greys_r',invert_yaxis = True,frame_height=325,\
                xlim = self.xlims,ylim = self.ylims,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                nonselection_fill_alpha = 0.75,line_width = 1.25,\
                line_color = 'grey',selection_line_color = 'red',\
                nonselection_line_color = 'grey',alpha = 0.75,\
                hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = ['tap',self.hover_tip_coords],shared_axes = False)
        #Data for the empty curves
        self.hov_lims = (self.ds.x.values[0]-0.5,self.ds.x.values[-1]+\
                0.5,self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        empty_Data =\
            xr.Dataset({'EmptyData':(['y','x','Eloss'],\
            np.zeros_like(self.ds.OriginalData.values)),\
            'EmptyScatter':(['mult'],np.zeros_like(self.multi_complex))},\
            coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
            'Eloss':self.ds.Eloss.values,'mult':self.multi_complex})
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 325,frame_width = 600,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True)
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 325,frame_width = 600,show_grid = True,\
            shared_axes = False,yformatter=formatter,\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black',framewise = True)
        self.scatter_empty = hv.Scatter(empty_Data.EmptyScatter)\
        .opts(frame_height = 325,frame_width = 600,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True)
        #hv.Image(self.ds.OriginalData.sum('Eloss'))\
        self.im_empty = hv.Image(empty_Data.EmptyData.sum('Eloss'))\
            .opts(cmap = 'greys_r',invert_axes = True,invert_yaxis = True,\
            frame_height=325,xaxis = None,yaxis = None,shared_axes = False,\
            xlim = self.ylims,ylim = self.xlims,\
            colorbar = True,colorbar_position = 'bottom')
        self.empty_VLine = hv.VLine(self.ds.Eloss.values[-1])\
            .opts(color = 'black',line_alpha = 0,line_width = 0,\
            shared_axes = False,frame_width=600,frame_height=325)
        empty_vspan = hv.VSpan(self.ds.Eloss.values[0],self.ds.Eloss.values[-1])\
        .opts(shared_axes = False,frame_width=600,frame_height=325,fill_alpha = 0,line_alpha = 0)
        self.empty_vspan = empty_vspan*empty_vspan
        #self.stream_hovering = streams.PointerXY(x = -1,y = -1,source = self.im)
        self.stream_tapping  = streams.SingleTap(x = -1,y = -1,source = self.im)
        self.stream_tapcenter  = streams.SingleTap(x = -1,y = -1,source = self.im)
        #self.dynamic_hover = hv.DynamicMap(self.plot_hover,streams=[self.stream_hovering])
        self.dynamic_tap   = hv.DynamicMap(self.plot_tap,streams=[self.stream_tapping])
        self.dynamic_centers = hv.DynamicMap(self.plot_centers,\
            streams = [self.stream_tapcenter])
        ############################
        ####### Buttons ############
        #We have to create a widget for the WL edge selection
        self.edge_selection_widget = pn.Param(self.param['full_edge'],\
            widgets = {'full_edge':pn.widgets.RadioButtonGroup},\
            parameters = ['full_edge'],show_name = False,\
            show_labels = False,align = 'center')
        self.edge_selection_widget[0].button_type = 'success'
        self.mode_selector = pn.Param(self.param['mode_integration'],\
            widgets = {'mode_integration':pn.widgets.RadioButtonGroup},\
            parameters = ['mode_integration'],show_name = False,\
            show_labels = False,align = 'center')
        self.mode_selector[0].margin = (5,10,0,10)
        self.mode_selector[0].button_type = 'primary'
        self.button_compute = pn.widgets.Button(name = 'Compute values',\
            align = 'center',button_type = 'success',width = 130)
        self.button_compute.on_click(self._callback_compute_results)
        self.button_reset_widths = pn.widgets.Button(name = '\u21bb',\
            align = 'center',disabled = True,width = 50,margin = (5,0))
        self.button_reset_widths.on_click(self._callback_reset_widths)
        '''
        self.button_show_fixed_widths = pn.widgets.Button(name = 'Show',\
            align = 'center',disabled = True,width = 100,margin = (5,0))
        self.button_show_fixed_widths.on_click(self._callback_show_fixed_widths)
        '''
        self.button_include_cont = pn.Param(self.param['include_continuum'],\
            widgets = {'include_continuum':pn.widgets.Toggle},\
            parameters = ['include_continuum'],width = 130,show_name = False,\
            show_labels = False,margin = (0,10))
        self.button_include_cont[0].disabled = True
        self.button_include_cont[0].name = 'Exclude continuum'
        self.button_include_cont[0].height = 33
        self.button_include_cont[0].margin = (10,15,5,10)
        self.button_show_computed_vals = pn.widgets.Button(name = 'save results',width = 130)
        self.button_show_computed_vals.disabled = True
        self.width_selector = pn.Param(self.param['width_integration'],\
            widgets = {'width_integration':pn.widgets.RadioButtonGroup},\
            parameters = ['width_integration'],show_name = False,\
            show_labels = False,align = 'center')
        self.width_selector[0].margin = (0,10)
        self.width_selector[0].disabled = True
        self.width_manual_selector = pn.Param(self.param['width_manual_integration'],\
            widgets = {'width_manual_integration':pn.widgets.RadioButtonGroup},\
            parameters = ['width_manual_integration'],show_name = False,\
            show_labels = False,align = 'center')
        self.width_manual_selector[0].disabled = True
        self.width_manual_selector[0].margin = (0,10)
        self.button_show_windows = pn.Param(self.param['show_wind'],\
            widgets = {'show_wind':pn.widgets.Toggle},parameters = ['show_wind'],\
            align = 'center',width = 175,show_labels = False,show_name = False)
        self.button_show_windows[0].name = 'Show integration windows'
        self.button_show_windows[0].disabled = True
        self.button_show_windows[0].width = 150
        self.button_show_cents = pn.Param(self.param['show_centers'],\
            widgets = {'show_centers':pn.widgets.Toggle},parameters = ['show_centers'],\
            align = 'center',width = 175,show_labels = False,show_name = False)
        self.button_show_cents[0].name = 'Show components centers'
        self.button_show_cents[0].width = 150
        self.button_change_DirectInverse = pn.widgets.Button(name = 'Invert ratio shown',\
            align = 'center',width = 175,disabled = True)
        self.button_change_DirectInverse.on_click(self._callback_invert_display)
        self.button_launch_advanced_analyzer = pn.widgets.Button(name = 'Advanced Analyser',\
            align = 'center',width = 175,disabled = True)
        self.button_launch_advanced_analyzer.on_click(self._callback_launch_advanced)
        ############################
        ############################
        ''' #Legacy - we are changing to a configuration giving option to select beginning
        # and end of the integration windows
        self.width_configurator = pn.Param(self.param['integration_semiwidth'],\
            widgets = {'integration_semiwidth':pn.widgets.Spinner},\
            parameters = ['integration_semiwidth'],\
            name = 'Integration half-width',show_name = False,\
            show_labels = False,align = 'center',width = 90,margin = (5,0))
        '''
        self.E0_wid = pn.Param(self.param['integration_E0'],\
            widgets = {'integration_E0':pn.widgets.Spinner},\
            parameters = ['integration_E0'],\
            name = 'Integration half-width',show_name = False,\
            show_labels = False,align = 'center',width = 115,margin = (5,0))
        self.E1_wid = pn.Param(self.param['integration_E1'],\
            widgets = {'integration_E1':pn.widgets.Spinner},\
            parameters = ['integration_E1'],\
            name = 'Integration half-width',show_name = False,\
            show_labels = False,align = 'center',width = 115,margin = (5,0))
        self.fixed_width_configurator = pn.Param(self.param['fixed_integration_semiwidth'],\
            widgets = {'fixed_integration_semiwidth':pn.widgets.Spinner},\
            parameters = ['fixed_integration_semiwidth'],show_labels = False,\
            show_name = False,align = 'center',width = 90,margin = (5,0))
        #self.width_configurator[0].style = {'color':'white'}
        self.E0_wid[0].disabled = True
        self.E0_wid[0].width = 105
        self.E0_wid[0].height = 33
        self.E1_wid[0].disabled = True
        self.E1_wid[0].width = 105
        self.E1_wid[0].height = 33
        self.fixed_width_configurator[0].disabled = True
        self.fixed_width_configurator[0].width = 75
        self.component_selector = pn.Param(self.param['components_per_edge'],\
            widgets = {'components_per_edge':pn.widgets.RadioButtonGroup},\
            parameters = ['components_per_edge'],show_name = False,\
            show_labels = False,align = 'center')
        self.param['components_per_edge'].objects = self.dictio_edges[self.full_edge]
        self.components_per_edge = self.param['components_per_edge'].objects[0]
        self.component_selector[0].disabled = True
        self.component_selector[0].margin = (0,10)
        '''
        #Now some widgets for the multiplier when using an advanced-fwhm approach
        self.slider_number_value = pn.Param(self.param['numb_value'],\
            widgets = {'numb_value':pn.widgets.StaticText},\
            parameters = ['numb_value'],width = 40,show_labels = False,\
            show_name = False,align = 'center')
        self.slider_number = pn.Param(self.param['numb'],\
            widgets = {'numb':pn.widgets.IntSlider},\
            parameters = ['numb'],show_name = False,show_labels = True,\
            align = 'center',width = 135)
        self.slider_number[0].bar_color = '#FFFFFF'
        self.slider_number[0].disabled = True
        self.slider_number[0].formatter = ('formatter_trial')
        self.slider_number_value[0].margin = (5,25,5,0)
        self.slider_number_value[0].margin = (5,10,5,0)
        self.slider_number_value[0].style = {'font-weight':'bold','color':'lightgrey'}
        '''
        self.width_compo_markdown =\
            pn.pane.Markdown('#### Integration window values E0 - E1[eV]',width = 250,\
            style = {'color':'lightgrey'},align = 'start',margin = (0,25,-15,60))
        self.fixed_width_compo_markdown =\
            pn.pane.Markdown('#### WL 1/2 integration width[eV]',width = 200,\
            style = {'color':'lightgrey'})
        '''
        self.numb_markdown = pn.pane.Markdown('#### FWHM<br>multiplier',width = 80,\
                style = {'color':'lightgrey'},margin= (5,0,5,35))
        '''
        self.component_to_int_selector = pn.Param(self.param['components_to_integrate'],\
            widgets = {'components_to_integrate':pn.widgets.MultiChoice},\
            parameters = ['components_to_integrate'],width = 280,\
            name = 'Components to compare',show_name = True,show_labels = False,\
            align = 'center')
        self.components_to_substraction = pn.Param(self.param['components_to_substract'],\
            widgets = {'components_to_substract':pn.widgets.MultiChoice},\
            parameters = ['components_to_substract'],width = 280,\
            name = 'Components to correct raw signal',show_name = True,show_labels = False,\
            align = 'center')
        self.select_computation_values_widget =\
            pn.Param(self.param['computation_values'],\
            widgets = {'computation_values':pn.widgets.RadioButtonGroup},\
            parameters = ['computation_values'],\
            show_name = False,show_labels = False,align = 'center')
        self.select_computation_values_widget[0].disabled = True
        self.component_to_int_selector[0].style = {'color':'lightgrey'}
        self.component_to_int_selector[1].disabled = True
        self.component_to_int_selector[1].max_items = 2
        self.component_to_int_selector.margin = 0
        self.component_to_int_selector[0].margin = (5,0)
        self.component_to_int_selector[1].margin = 0
        self.component_to_int_selector[1].width = 263
        self.components_to_substraction[0].style = {'color':'lightgrey'}
        self.components_to_substraction[1].disabled = True
        self.components_to_substraction.margin = 0
        self.components_to_substraction[0].margin = (5,0)
        self.components_to_substraction[1].margin = 0
        self.components_to_substraction[1].width = 263
        #NOw the information panel and buttons
        self.message_display = pn.pane.Markdown('No messages',height = 200,width = 550,\
                margin = (0,15),style = {'color':'white','text-align':'justify'})
        self.info_panel = pn.Column(\
            pn.pane.Markdown('#### Info messages',style = {'color':'white'},\
                margin = (5,15,-10,15)),\
            pn.layout.Divider(height = 5,margin = (0,15,5,15)),\
            self.message_display,\
            pn.layout.Divider(height = 5,margin = (0,15)),\
            height = 325,width = 600,background = 'black',margin = (0,10))
        #We need a little panel for the graphical control - 
        # We are going to hide it in a tab in the lower row
        self.cmap_wid = pn.Param(self.param['colormap_1'],\
            widgets = {'colormap_1':pn.widgets.Select},\
            parameters = ['colormap_1'],width = 225,show_labels = False,\
            show_name = False,name = 'ColorMap')
        self.cmap_wid[0].disabled = True
        self.cbar_wid = pn.Param(self.param['range_cmap1'],\
            widgets = {'range_cmap1':pn.widgets.RangeSlider},\
            parameters = ['range_cmap1'],width = 225,show_labels = True,\
            show_name = False)
        self.cbar_wid[0].step = 0.01
        self.cbar_wid[0].disabled = True
        #The progress bar for integrations
        self.progress_bar_advanced = pn.Param(self.param['num_prog1'],\
            widgets = {'num_prog1':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['num_prog1'],align = 'center')
        self.progress_bar_advanced[0].width = 280
        self.fitting_in_place = False
        self.direct_image = True
        
    @param.depends('range_cmap1',watch = True)
    def _change_range(self):
        if self.fitting_in_place:
            self.image_ratio_placement.object =\
            self.image_ratio_placement.object.opts(clim = self.range_cmap1)
        else:
            pass
        
    @param.depends('colormap_1',watch = True)
    def _change_colormap(self):
        if self.fitting_in_place:
            self.image_ratio_placement.object =\
            self.image_ratio_placement.object.opts(cmap = self.colormap_1)
        else:
            pass
        
    @param.depends('show_wind','show_centers',watch = True)
    def _show_winds_centers(self):
        #This controls the dynamic appearance of the spectrum graphs
        if self.show_centers and not self.show_wind:
            self.button_show_cents[0].button_type = 'success'
            self.button_show_windows[0].button_type = 'default'
            self.dynamic_placement.object =\
            self.dynamic_tap*self.dynamic_centers
        elif self.show_centers and self.show_wind: 
            self.button_show_cents[0].button_type = 'success'
            self.button_show_windows[0].button_type = 'success'
            self.dynamic_placement.object =\
            self.dynamic_tap*self.dynamic_centers*self.dyn_windows
        elif self.show_wind and not self.show_centers:
            self.button_show_cents[0].button_type = 'default'
            self.button_show_windows[0].button_type = 'success'
            self.dynamic_placement.object =\
            self.dynamic_tap*self.dyn_windows
        else:
            self.button_show_cents[0].button_type = 'default'
            self.button_show_windows[0].button_type = 'default'
            self.dynamic_placement.object =\
            self.dynamic_tap
    
    @param.depends('mode_integration',watch = True)
    def _change_width_selector_availability(self):
        if self.mode_integration == 'auto':
            self.width_selector[0].disabled = True
            self.width_selector[0].button_type = 'default'
            self.components_to_integrate = []
            #We have to disable the rest of the buttons... in full auto none is available
            self.width_manual_selector[0].disabled = True
            self.width_manual_selector[0].button_type = 'default'
            self.component_selector[0].button_type = 'default'
            self.component_selector[0].disabled = True
            self.button_reset_widths.disabled = True
            '''
            self.slider_number[0].bar_color = '#FFFFFF'
            self.slider_number[0].disabled = True
            '''
            self.E0_wid[0].disabled = True
            self.E1_wid[0].disabled = True
            self.width_compo_markdown.style = {'color':'lightgrey'}
            '''
            self.numb_markdown.style = {'color':'lightgrey'}
            '''
            #We reset also the button's values so when reactivated\
            # we get the initial state again
            self.width_integration = 'fwhm'
            self.width_manual_integration = 'fixed'
            self.component_to_int_selector[0].style = {'color':'lightgrey'}
            self.component_to_int_selector[1].disabled = True
            self.select_computation_values_widget[0].disabled = True
            self.select_computation_values_widget[0].button_type = 'default'
            #self.extra_corrections_widget[0].disabled = True
            self.button_include_cont[0].disabled = True
            self.button_include_cont[0].button_type = 'default'
            self.button_include_cont[0].name = 'Exclude continuuum'
        else:
            self.width_selector[0].disabled = False
            self.width_selector[0].button_type = 'warning'
            self.component_to_int_selector[0].style = {'color':'crimson'}
            self.component_to_int_selector[1].disabled = False
            self.select_computation_values_widget[0].disabled = False
            self.select_computation_values_widget[0].button_type = 'primary'
            self.button_include_cont[0].disabled = False
            if self.include_continuum:
                self.button_include_cont[0].button_type = 'success'
                self.button_include_cont[0].name = 'Include continuuum'
            else:
                self.button_include_cont[0].button_type = 'danger'
                self.button_include_cont[0].name = 'Exclude continuuum'
            '''
            if self.width_integration == 'fwhm':
                self.slider_number[0].disabled = False
                self.slider_number[0].bar_color = '#00FF00'
                self.numb_markdown.style = {'color':'lime'}
            '''
            
            #self.extra_corrections_widget[0].disabled = False
            #self.extra_corrections_widget[0].button_type = 'danger'
    
    @param.depends('include_continuum',watch = True)
    def _change_cont_inclusion(self):
        if self.include_continuum:
            self.button_include_cont[0].button_type = 'success'
            self.button_include_cont[0].name = 'Include continuuum'
        else:
            self.button_include_cont[0].button_type = 'danger'
            self.button_include_cont[0].name = 'Exclude continuuum'

    @param.depends('components_to_integrate',watch = True)
    def _change_components_to_integrate_title(self):
        self.param['components_to_substract'].objects =\
        [el for el in self.dictio_edges[self.full_edge] \
        if el not in self.components_to_integrate]
        try:
            #May be none at the begining...so let's play safe
            long = len(self.components_to_integrate)
            if long == 2 and self.mode_integration == 'advanced':
                self.component_to_int_selector[0].style = {'color':'lime'}
            elif long != 2 and self.mode_integration == 'advanced':
                self.component_to_int_selector[0].style = {'color':'crimson'}
            else:
                self.component_to_int_selector[0].style = {'color':'lightgrey'}
        except:
            pass
        
    @param.depends('width_integration',watch = True)
    def _change_advanced_buttons_availability_1(self):
        if self.width_integration == 'fwhm' and self.mode_integration == 'advanced':
            '''
            self.slider_number[0].disabled = False
            self.slider_number[0].bar_color = '#00FF00'
            self.numb_markdown.style = {'color':'lime'}
            '''
            #NOw the other buttons
            self.width_manual_selector[0].disabled = True
            self.width_manual_selector[0].button_type = 'default'
            self.component_selector[0].disabled = True
            self.component_selector[0].button_type = 'default'
            self.width_compo_markdown.style = {'color':'lightgrey'}
            self.E0_wid[0].disabled = True
            self.E1_wid[0].disabled = True
            self.button_reset_widths.disabled = True
            self.button_reset_widths.button_type = 'default'
            '''
            self.button_show_fixed_widths.disabled = True
            self.button_show_fixed_widths.button_type = 'default'
            '''
            self.fixed_width_configurator[0].disabled = True
            self.fixed_width_compo_markdown.style = {'color':'lightgrey'}
            
        elif self.width_integration == 'manual' and self.mode_integration == 'advanced':
            '''
            self.slider_number[0].bar_color = '#FFFFFF'
            self.slider_number[0].disabled = True
            self.numb_markdown.style = {'color':'lightgrey'}
            '''
            #let's activate the possible buttons
            self.width_manual_selector[0].disabled = False
            self.width_manual_selector[0].button_type = 'primary'
            self.width_manual_integration = 'fixed'
            '''
            self.button_show_fixed_widths.disabled = False
            self.button_show_fixed_widths.button_type = 'danger'
            '''
            self.fixed_width_configurator[0].disabled = False
            self.fixed_width_compo_markdown.style = {'color':'lime'}
            
    @param.depends('width_manual_integration',watch = True)
    def _change_advanced_buttons_availability_2(self):
        if self.width_manual_integration == 'fixed' and self.mode_integration == 'advanced':
            self.component_selector[0].disabled = True
            self.button_reset_widths.disabled = True
            self.E0_wid[0].disabled = True
            self.E1_wid[0].disabled = True
            self.width_compo_markdown.style = {'color':'lightgrey'}
            self.component_selector[0].button_type = 'default'
            self.button_reset_widths.button_type = 'default'
            '''
            self.button_show_fixed_widths.disabled = False
            self.button_show_fixed_widths.button_type = 'danger'
            '''
            self.fixed_width_configurator[0].disabled = False
            self.fixed_width_compo_markdown.style = {'color':'lime'}
            
        elif self.width_manual_integration == 'individual' and self.mode_integration == 'advanced':
            self.component_selector[0].disabled = False
            self.button_reset_widths.disabled = False
            self.button_reset_widths.button_type = 'danger'
            self.E0_wid[0].disabled = False
            self.E1_wid[0].disabled = False
            self.integration_E0,self.integration_E1 =\
            self.dictio_ELNES_limits[self.full_edge][self.components_per_edge]
            self.width_compo_markdown.style = {'color':'lime'}
            self.component_selector[0].button_type = 'warning'
            '''
            self.button_show_fixed_widths.disabled = True
            self.button_show_fixed_widths.button_type = 'default'
            '''
            self.fixed_width_configurator[0].disabled = True
            self.fixed_width_compo_markdown.style = {'color':'lightgrey'}
            
            
    @param.depends('full_edge',watch = True)
    def _change_compos_buttons(self):
        self.param['components_per_edge'].objects = self.dictio_edges[self.full_edge]
        self.components_per_edge = self.param['components_per_edge'].objects[0]
        #Changes in the available components to select
        self.param['components_to_integrate'].objects = self.dictio_edges[self.full_edge]
        self.components_to_integrate = []
        
    
    @param.depends('computation_values',watch = True)
    def _allow_compo_substraction(self):
        if self.computation_values == 'Raw data':
            self.components_to_substraction[1].disabled = False
            self.components_to_substraction[0].style = {'color':'lime'}
            self.include_continuum = False
            #self.button_include_cont[0].disabled = True
        elif self.computation_values == 'Fitted data':
            self.components_to_substract = []
            self.components_to_substraction[1].disabled = True
            self.components_to_substraction[0].style = {'color':'lightgrey'}
            #self.button_include_cont[0].disabled = False
            
    @param.depends('components_per_edge',watch = True)
    def _change_number_spinner_values(self):
        try:
            self.integration_E0,self.integration_E1 =\
                self.dictio_ELNES_limits[self.full_edge][self.components_per_edge]
        except: pass
        
    @param.depends('integration_E0','integration_E1',watch = True)
    def _change_dictio_value_semiIntWidth(self):
        self.dictio_ELNES_limits[self.full_edge][self.components_per_edge] =\
        [self.integration_E0,self.integration_E1]
    
    '''
    @param.depends('numb',watch = True)
    def _change_numb_value(self):
        self.numb_value = str(self.multi_complex[self.numb])
        
    @param.depends('numb',watch = True)
    def plot_vline_ratio_postition(self):
        #print(*args,**kwargs)
        #First we get the indicesclicked
        #idx_x = abs(self.dataset.mult.values-self.stream_2.x).argmin()
        try:
            # print('changing_with numb',self.numb)
            linea = hv.VLine(x = self.dataset_auto.mult.values[self.numb])\
            .opts(line_width = 1.25,line_alpha = 1,line_color = 'lime',shared_axes = False,\
            frame_width=600,frame_height=325)
        except:
            # print('not changing_with numb',self.numb)
            linea = hv.VLine(0)\
            .opts(color = 'black',line_alpha = 0,line_width = 0,\
            shared_axes = False,frame_width=600,frame_height=325)
        finally:
            return linea
    '''
    #@param.depends('numb',watch = True)
    def plot_int_windows_fwhm(self,x = -1,y = -1):
        #print('changing')
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_vspan
        elif y >= yf or y <= yi:
            return self.empty_vspan
        else:
            x0,y0 = self.im.closest((x,y))
            x0 = int(x0)
            y0 = int(y0)
            #print(x0,y0)
            try:
                numer = int(self.multi_complex.size/2)
                lim00,lim10 = self.dataset_auto.isel(x = x0,y = y0,mult = numer)\
                .EnergyLimits.values[0]
                lim01,lim11 = self.dataset_auto.isel(x = x0,y = y0,mult = numer)\
                .EnergyLimits.values[1]
            except:
                return self.empty_vspan
            else:
                if any([el.astype('int32') < 0 for el in [lim00,lim01,lim10,lim11]]):
                    #This is to avoid the nan values of non fitted areas
                    return self.empty_vspan
                else:
                    span1 = hv.VSpan(x1 = lim00,x2 = lim01)\
                    .opts(shared_axes=False,fill_alpha = 0.25,fill_color = 'dodgerblue',\
                    line_alpha = 1,line_color = 'blue')
                    span2 = hv.VSpan(x1 = lim10,x2 = lim11)\
                    .opts(fill_alpha = 0.25,fill_color = 'limegreen',\
                    line_alpha = 1,line_color = 'limegreen',shared_axes = False)
                    return span1*span2
                
    def plot_int_windows_single(self,x = -1,y = -1):
        #print('changing')
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_vspan
        elif y >= yf or y <= yi:
            return self.empty_vspan
        else:
            x0,y0 = self.im.closest((x,y))
            x0 = int(x0)
            y0 = int(y0)
            #print(x0,y0)
            try:
                lim00,lim10 = self.dataset_auto.isel(x = x0,y = y0)\
                .EnergyLimits.values[0]
                lim01,lim11 = self.dataset_auto.isel(x = x0,y = y0)\
                .EnergyLimits.values[1]
            except:
                return self.empty_vspan
            else:
                if any([el.astype('int32') < 0 for el in [lim00,lim01,lim10,lim11]]):
                    #This is to avoid the nan values of non fitted areas
                    return self.empty_vspan
                else:
                    span1 = hv.VSpan(x1 = lim00,x2 = lim01)\
                    .opts(shared_axes=False,fill_alpha = 0.25,fill_color = 'dodgerblue',\
                    line_alpha = 1,line_color = 'blue')
                    span2 = hv.VSpan(x1 = lim10,x2 = lim11)\
                    .opts(fill_alpha = 0.25,fill_color = 'limegreen',\
                    line_alpha = 1,line_color = 'limegreen',shared_axes = False)
                    return span1*span2
    
    def show_message(self,code):
        #This is a method to show error or probem messages in the info area
        if code == 'code01':
            mess_list = ['The selected edge only has a single ELNES.',\
                'It is not a valid option for auto WL integration',\
                'If extra ELNES structures available, choose advanced',\
                'option to analyse ratios']
            mess = ' '.join(mess_list)
        elif code == 'code02':
            mess_list = ['Components error - 2 ELNES components are',\
                'required for a integration ratio comparison. Check',\
                'the - Components to compare - box, and ensure that',\
                '2 components are selected before running calculations']
            mess = ' '.join(mess_list)
        else: mess = 'No messages'
        self.message_display.object = mess
        
    
    def plot_tap(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            x0,y0 = self.im.closest((x,y))
            self.x_pos = int(x0)
            self.y_pos = int(y0)
            area = hv.Area(self.ds.OriginalData.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,line_width=1.25,\
                line_alpha = 1,yformatter=formatter,line_color = 'darkred',\
                fill_color = 'coral',fill_alpha = 0.5,shared_axes = False,\
                frame_height = 325,frame_width = 600,framewise = True)
            return area
    
    #@param.depends('full_edge',watch = True)
    def plot_centers(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_VLine*self.empty_VLine
        elif y >= yf or y <= yi:
            return self.empty_VLine*self.empty_VLine
        else:
            x0,y0 = self.im.closest((x,y))
            list_vlines = []
            for ed in self.dictio_edges:
                for ssh in self.dictio_edges[ed]:
                    clave = '_'.join([ssh,'center'])
                    val = np.nan_to_num(self.ds[clave].isel(x = int(x0),y = int(y0)), nan = -1)
                    if val > 0.0:
                        list_vlines.append(hv.VLine(val)\
                        .opts(color = 'navy',line_alpha = 1,\
                        line_width = 1))
                    else:
                        #Case of having a nan value - changed by -1 above
                        list_vlines.append(self.empty_VLine)
            objeto = list_vlines[0]
            for el in list_vlines[1:]:
                objeto *= el
            return objeto
    '''   
    def plot_graph_ratios(self,x,y):
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.curve_empty*self.scatter_empty
        elif y >= yf or y <= yi:
            return self.curve_empty*self.scatter_empty
        else:
            x0,y0 = self.im.closest((x,y))
            scat = hv.Scatter(vwl.dataset_auto.Components_Ratios.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,frame_height=325,frame_width=600,\
                yformatter=formatter,line_color = 'black',fill_color = 'grey',\
                selection_fill_color = 'red',selection_fill_alpha = 1,size = 7.5,fill_alpha = 0.5,\
                shared_axes = False,framewise = True)
            curve = hv.Curve(vwl.dataset_auto.Components_Ratios.isel(x = int(x0),y = int(y0)))\
                .opts(show_title=False,frame_height=325,frame_width=600,yformatter=formatter,line_color = 'blue',\
                shared_axes = False,framewise = True)
            return curve*scat
    
    def _callback_show_fixed_widths(self,event):
        #TODO complete this function
        pass
    '''
    def _callback_invert_display(self,event):
        if self.direct_image and not self.fwhm_run:
            #We change to the inversed ratio
            self.direct_image = False
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[0],self.dataset_auto.comp.values[1])
            mini = np.nanmin(self.dataset_auto['Components_Inverted_Ratios'].values)
            maxi = np.nanmax(self.dataset_auto['Components_Inverted_Ratios'].values)
            self.image_ratio_placement.object =\
                hv.HeatMap(self.dataset_auto.Components_Inverted_Ratios)\
                .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                    xlim = self.xlims,ylim = self.ylims,\
                    xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                    selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                    line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                    alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                    tools = [self.hover_ratio_i],shared_axes = False,\
                    colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
            
        elif not self.direct_image and not self.fwhm_run:
            self.direct_image = True
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
            mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
            maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
            self.image_ratio_placement.object =\
                hv.HeatMap(self.dataset_auto.Components_Ratios)\
                .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                    xlim = self.xlims,ylim = self.ylims,\
                    xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                    selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                    line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                    alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                    tools = [self.hover_ratio],shared_axes = False,\
                    colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
            
        elif self.direct_image and self.fwhm_run:
            multiLEN = self.multi_complex.size
            self.direct_image = False
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[0],self.dataset_auto.comp.values[1])
            mini = np.nanmin(self.dataset_auto['Components_Inverted_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            maxi = np.nanmax(self.dataset_auto['Components_Inverted_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            self.image_ratio_placement.object =\
            hv.HeatMap(self.dataset_auto.Components_Inverted_Ratios.isel(mult = int(multiLEN/2)))\
                .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                    xlim = self.xlims,ylim = self.ylims,\
                    xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                    selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                    line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                    alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                    tools = [self.hover_ratio_i],shared_axes = False,\
                    colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
        else:
            multiLEN = self.multi_complex.size
            self.direct_image = True
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
            mini = np.nanmin(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            maxi = np.nanmax(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            self.image_ratio_placement.object =\
            hv.HeatMap(self.dataset_auto.Components_Ratios.isel(mult = int(multiLEN/2)))\
                .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                    xlim = self.xlims,ylim = self.ylims,\
                    xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                    selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                    line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                    alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                    tools = [self.hover_ratio],shared_axes = False,\
                    colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
    
    def _callback_launch_advanced(self,event):
        #TODO complete the external launcher
        if not self.fwhm_run:
            #This is a safeguard
            return
        else:
            self.advanced_fwhm = Advanced_visualizer_WL_ratio_FWHM(self.ds,xr.merge([self.dataset_auto,self.ds_out]),self.colormap_1)
            self.advanced_fwhm.layout()
    
    def _callback_reset_widths(self,event):
        #Just resets the current component integration width
        self.integration_E0,self.integration_E1 =\
        self.dictio_ELNES_lims_default[self.full_edge][self.components_per_edge]
        
    def _callback_compute_results(self,event):
        #This function is just a big decission tree to select the computation\
        # parameters and call the right function
        if self.mode_integration == 'auto':
            self.compute_full_auto()
            self.direct_image = True
        elif self.mode_integration != 'auto' and len(self.components_to_integrate) != 2:
            self.show_message('code02')
            return 
        elif self.mode_integration == 'advanced' and self.width_integration == 'fwhm':
            self.ds_out = self.prepare_dateset_to_int()
            self.compute_fwhm_dependent(self.ds_out)
            self.direct_image = True
        elif self.mode_integration == 'advanced' and self.width_integration == 'manual':
            self.ds_out = self.prepare_dateset_to_int()
            if self.width_manual_integration == 'fixed':
                self.compute_manual_fixed(self.ds_out)
                self.direct_image = True
            elif self.width_manual_integration == 'individual':
                self.compute_manual_independent(self.ds_out)
                self.direct_image = True
            else:
                #TODO write in the info panel something gone wrong
                pass
        else:
            #TODO write in the info panel something gone wrong
            pass
    
    def prepare_dateset_to_int(self):
        '''
        This method pepares the data set to be integrated. The key here is to
        get the data for the different cases : 
        (1) fitted data vs raw data
        (2) raw data vs raw data - correction components
        (3) excluding continuum vs including continuum
        ----------
        return
        ----------
        The dataset with the info to be integrated
        '''
        if self.computation_values == 'Fitted data':
            ds_list = []
            for ssh in self.components_to_integrate:
                ssh_name = '_'.join([ssh,'component'])
                if self.include_continuum:
                    name_cont = self.full_edge.split(' ')
                    name_cont.append('_cont_component')
                    ds_list.append((self.ds[ssh_name] +\
                        self.ds[''.join(name_cont)])\
                        .to_dataset(name = ssh))
                else:
                    ds_list.append((self.ds[ssh_name])\
                    .to_dataset(name = ssh))
            return xr.merge(ds_list)
        elif self.computation_values == 'Raw data':
            ds_list = []
            dat_arr = cp.deepcopy(self.ds.OriginalData)
            #Continuum substraction
            if not self.include_continuum:
                name_cont = self.full_edge.split(' ')
                name_cont.append('_cont_component')
                dat_cont = cp.deepcopy(self.ds[''.join(name_cont)])
                dat_arr -= xr.apply_ufunc(np.nan_to_num,dat_cont)
            else: pass
            for el in self.components_to_substract:
                clav = '_'.join([el,'component'])
                dat_comp = cp.deepcopy(self.ds[clav])
                dat_arr -= xr.apply_ufunc(np.nan_to_num,dat_comp)
                #We now get two different components holding the same info...for integr.
            for ssh in self.components_to_integrate:
                ds_list.append(dat_arr.to_dataset(name = ssh))
            return xr.merge(ds_list)
    
    #4 different modes of computation.... in 4 paths
    def compute_full_auto(self):
        # The first step is the calculation of the integration widths
        # it is based on the sigmas 
        #Some parameter setup before the integral's calculations
        ele = self.full_edge.split(' ')[0]
        lista = list(self.full_edge.split(' ')[1])
        #Let's check if the selected edge is a valid option
        if len(lista) < 3:
            #in this case... we are in a K edge, or a single subshell edge - no WL ratio
            self.show_message('code01')  # And we stop calculations
            return
        else: pass
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        compo1 = ''.join([ele,lista[0],lista[1]])
        compo2 = ''.join([ele,lista[0],lista[2]])
        #We only do one multiplier in auto ... 2.5 which in practice showed to be enough
        #Preparing the empty matrices
        vals = np.zeros(shap)        #Center values matrices
        #sigs = np.zeros(shap)        #sigmas matrices
        #ratio = np.zeros(shap)       #integrated ratios matrices
        Ew_halfs = np.zeros(shap+(2,2)) #Energy values of integration limits
        idx_min_max_mat = np.zeros(shap+(2,2)) #indices (positional) int. limits
        # We just need 2 indices for each component...since we run along\
        # with the higher energy gap possible ... meaning the higher sigma for a
        # given component.
        #let's look for the higher values
        max_sigs = [np.nanmax(self.ds['_'.join([compo1,'fwhm'])].values),\
            np.nanmax(self.ds['_'.join([compo2,'fwhm'])].values)]
        for i,comp in enumerate([compo1,compo2]):
            vals = self.ds['_'.join([comp,'center'])].values
            Ew_halfs[:,:,0,i] = vals - 2.5625 * max_sigs[i] / 2
            Ew_halfs[:,:,1,i] = vals + 2.5625 * max_sigs[i] / 2
        idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        idx_min_max_mat = idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(2,))
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1])
        for i in range(shap[0]):
            for j in range(shap[1]):
                compo_1 = self.ds['_'.join([compo1,'component'])].values[i,j]
                compo_2 = self.ds['_'.join([compo2,'component'])].values[i,j]
                condition1 = np.nan_to_num(compo_1).sum() != 0
                condition2 = np.nan_to_num(compo_2).sum() != 0
                condition3 = idx_min_max_mat[i,j,1,0] != idx_min_max_mat[i,j,0,0]
                #if np.nan_to_num(compo_1).sum() != 0: #Avoid NaNs
                if all([condition1,condition2,condition3]):
                    #For the first component WLs
                    ints[i,j,0] = simpson(compo_1[idx_min_max_mat[i,j,0,0]:\
                        idx_min_max_mat[i,j,1,0]],\
                    Eloss[int(idx_min_max_mat[i,j,0,0]):int(idx_min_max_mat[i,j,1,0])])
                    #For the second component WL
                    ints[i,j,1] = simpson(compo_2[idx_min_max_mat[i,j,0,1]:\
                        idx_min_max_mat[i,j,1,1]],\
                    Eloss[idx_min_max_mat[i,j,0,1]:idx_min_max_mat[i,j,1,1]])
                else:
                    ints[i,j,1] = np.nan
                    ints[i,j,0] = np.nan
                self.num_prog1+=1
        #All computations done...time to get the dateset
        self.fwhm_run = False
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','comp'],ints),\
            'EnergyLimits':(['y','x','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        #Now we need to display the resublts
        #We show the actual multiplier value
        '''
        self.slider_number[0].disabled = False
        self.numb = 17
        self.slider_number[0].disabled = True
        '''
        #Create the image of ratios
        #The colorbar limits
        mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
        self.image_ratio_placement.object = hv.HeatMap(self.dataset_auto.Components_Ratios)\
            .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                xlim = self.xlims,ylim = self.ylims,\
                selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = [self.hover_ratio],shared_axes = False,\
                colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
        self.fitting_in_place = True
        self.cbar_wid[0].disabled = False
        self.cmap_wid[0].disabled = False
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_single,streams=[self.stream_tapping])
        self.button_show_windows[0].disabled = False
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.button_type = 'default'
        self.button_launch_advanced_analyzer.disabled = True
        
    def compute_fwhm_dependent(self,ds_out):
        #This method integrates for each and every value of\
        # the multi-complex array multiplied by the fwhm/2 as integration limits
        # the areas in the WL selected, for each pixel independently
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        #ele = self.full_edge.split(' ')[0]
        #lista = list(self.full_edge.split(' ')[1])
        compo1,compo2 = list(self.components_to_integrate) 
        multiLEN = self.multi_complex.size
        #Preparing the empty matrices
        vals = np.zeros(shap+(multiLEN,))        #Center values matrices
        sigs = np.zeros(shap+(multiLEN,))        #sigmas matrices
        #ratio = np.zeros(shap+(multiLEN,))       #integrated ratios matrices
        Ew_halfs = np.zeros(shap+(multiLEN,2,2)) #Energy values of integration limits
        self.idx_min_max_mat = np.zeros(shap+(multiLEN,2,2)) #indices (positional) int. limits
        #The loop run the 2 components selected
        for i,comp in enumerate([compo1,compo2]):
            vals = self.ds['_'.join([comp,'center'])].values[:,:,None]
            sigs = self.ds['_'.join([comp,'fwhm'])].values[:,:,None]
            Ew_halfs[:,:,:,0,i] = vals - self.multi_complex*sigs/2
            Ew_halfs[:,:,:,1,i] = vals + self.multi_complex*sigs/2
        self.idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        self.idx_min_max_mat = self.idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(multiLEN,2))
        #We set up the progress bar
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1]*multiLEN)
        for i in range(shap[0]):
            for j in range(shap[1]):
                #compo1,compo2 = self.components_to_integrate 
                compo_1 = ds_out[compo1].values[i,j]
                compo_2 = ds_out[compo2].values[i,j]
                for k in range(multiLEN):
                    #print(i,j,k)
                    condition1 = np.nan_to_num(compo_1).sum() != 0
                    condition2 = np.nan_to_num(compo_2).sum() != 0
                    condition3 = self.idx_min_max_mat[i,j,k,1,0] != self.idx_min_max_mat[i,j,k,0,0]
                    if all([condition1,condition2,condition3]):
                        #Avoid NaNs and non spaced indices
                        #For the first component WLs
                        ints[i,j,k,0] = simps(compo_1[self.idx_min_max_mat[i,j,k,0,0]:\
                            self.idx_min_max_mat[i,j,k,1,0]],\
                        Eloss[self.idx_min_max_mat[i,j,k,0,0]:self.idx_min_max_mat[i,j,k,1,0]])
                        #For the second component WL
                        ints[i,j,k,1] = simps(compo_2[self.idx_min_max_mat[i,j,k,0,1]:\
                            self.idx_min_max_mat[i,j,k,1,1]],\
                        Eloss[self.idx_min_max_mat[i,j,k,0,1]:self.idx_min_max_mat[i,j,k,1,1]])
                    else:
                        ints[i,j,k,1] = np.nan
                        ints[i,j,k,0] = np.nan
                    self.num_prog1+=1
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','mult','comp'],ints),\
            'EnergyLimits':(['y','x','mult','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'mult':self.multi_complex,'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        mini = np.nanmin(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
        self.image_ratio_placement.object =\
            hv.HeatMap(self.dataset_auto.Components_Ratios.isel(mult = int(multiLEN/2)))\
            .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                xlim = self.xlims,ylim = self.ylims,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = [self.hover_ratio],shared_axes = False,\
                colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
        self.cbar_wid[0].disabled = False
        self.cmap_wid[0].disabled = False
        self.fitting_in_place = True
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.fwhm_run = True
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_fwhm,streams=[self.stream_tapping])
        self.show_wind = False
        self.button_show_windows[0].disabled = True
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.disabled = False
        self.button_launch_advanced_analyzer.button_type = 'success'
        '''
        #This is all legacy. Now these configurations are part of an external launcher
        self.stream_tapping2  = streams.SingleTap(x = -1,y = -1,source = self.im)
        #We create the dinamic map
        self.dyn_fwhm_hmap = hv.DynamicMap(self.plot_ratio_heatmap)\
        .opts(shared_axes = False,framewise = True)
        self.dyn_ratio_multiplier = hv.DynamicMap(self.plot_vline_ratio_postition)\
        .opts(shared_axes = False,framewise = True)
        self.dyn_int_windows = hv.DynamicMap(self.plot_int_windows_1,streams=[self.stream_tapping2])\
        .opts(shared_axes = False,framewise = True)
        self.dyn_ratios_scatter = hv.DynamicMap(self.plot_graph_ratios,streams=[self.stream_tapping])\
        .opts(shared_axes = False,framewise = True)
        # We have to change add the ratio heatmap
        self.image_ratio_placement.object = self.dyn_fwhm_hmap.opts(shared_axes = False,framewise = True)
        self.tab_graphs[1].pop(0)
        self.tab_graphs[1].append(\
            pn.pane.HoloViews(self.dyn_ratios_scatter\
            .opts(shared_axes = False,framewise = True,frame_height=325,frame_width=600)))
        '''
    def compute_manual_fixed(self,ds_out):
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        #ele = self.full_edge.split(' ')[0]
        #lista = list(self.full_edge.split(' ')[1])
        compo1,compo2 = list(self.components_to_integrate )
        #Preparing the empty matrices
        vals = np.zeros(shap)        #Center values matrices
        Ew_halfs = np.zeros(shap+(2,2)) #Energy values of integration limits
        self.idx_min_max_mat = np.zeros(shap+(2,2)) #indices (positional) int. limits
        #The loop run the 2 components selected
        for i,comp in enumerate([compo1,compo2]):
            vals = self.ds['_'.join([comp,'center'])].values
            Ew_halfs[:,:,0,i] = vals - self.fixed_integration_semiwidth
            Ew_halfs[:,:,1,i] = vals + self.fixed_integration_semiwidth
        self.idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        self.idx_min_max_mat = self.idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(2,))
        #We set up the progress bar
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1])
        for i in range(shap[0]):
            for j in range(shap[1]):
                #compo1,compo2 = self.components_to_integrate 
                compo_1 = ds_out[compo1].values[i,j]
                compo_2 = ds_out[compo2].values[i,j]
                condition1 = np.nan_to_num(compo_1).sum() != 0
                condition2 = np.nan_to_num(compo_2).sum() != 0
                condition3 = self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]
                if all([condition1,condition2,condition3]): 
                    #Avoid NaNs and non spaced indices
                    #For the first component WLs
                    ints[i,j,0] = simps(compo_1[self.idx_min_max_mat[i,j,0,0]:\
                        self.idx_min_max_mat[i,j,1,0]],\
                    Eloss[self.idx_min_max_mat[i,j,0,0]:self.idx_min_max_mat[i,j,1,0]])
                    #For the second component WL
                    ints[i,j,1] = simps(compo_2[self.idx_min_max_mat[i,j,0,1]:\
                        self.idx_min_max_mat[i,j,1,1]],\
                    Eloss[self.idx_min_max_mat[i,j,0,1]:self.idx_min_max_mat[i,j,1,1]])
                else:
                    ints[i,j,1] = np.nan
                    ints[i,j,0] = np.nan
                self.num_prog1+=1
        self.fwhm_run = False
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','comp'],ints),\
            'EnergyLimits':(['y','x','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
        self.image_ratio_placement.object = hv.HeatMap(self.dataset_auto.Components_Ratios)\
            .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                xlim = self.xlims,ylim = self.ylims,\
                selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = [self.hover_ratio],shared_axes = False,\
                colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
        self.fitting_in_place = True
        self.cbar_wid[0].disabled = False
        self.cmap_wid[0].disabled = False
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_single,streams=[self.stream_tapping])
        self.button_show_windows[0].disabled = False
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.button_type = 'default'
        self.button_launch_advanced_analyzer.disabled = True
        
    def compute_manual_independent(self,ds_out):
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        #lista = list(self.full_edge.split(' ')[1])
        compo1,compo2 = list(self.components_to_integrate)
        #Preparing the empty matrices
        #vals = np.zeros(shap)        #Center values matrices
        Ew_halfs = np.zeros(shap+(2,2)) #Energy values of integration limits
        self.idx_min_max_mat = np.zeros(shap+(2,2)) #indices (positional) int. limits
        #The loop run the 2 components selected
        for i,comp in enumerate([compo1,compo2]):
            #vals = self.ds['_'.join([comp,'center'])].values
            Ew_halfs[:,:,0,i] = self.dictio_ELNES_limits[self.full_edge][comp][0]
            Ew_halfs[:,:,1,i] = self.dictio_ELNES_limits[self.full_edge][comp][1]
        self.idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        self.idx_min_max_mat = self.idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(2,))
        #We set up the progress bar
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1])
        for i in range(shap[0]):
            for j in range(shap[1]):
                #compo1,compo2 = self.components_to_integrate 
                compo_1 = ds_out[compo1].values[i,j]
                compo_2 = ds_out[compo2].values[i,j]
                #if (np.nan_to_num(compo_1).sum()) != 0 and (self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]): 
                #if (np.nan_to_num(compo_1).sum()) != 0 and (self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]): 
                condition1 = np.nan_to_num(compo_1).sum() != 0
                condition2 = np.nan_to_num(compo_2).sum() != 0
                condition3 = self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]
                condition4 = not self.ds['_'.join([compo1,'center'])].isel(x = j,y = i).isnull()
                condition5 = not self.ds['_'.join([compo2,'center'])].isel(x = j,y = i).isnull()
                if all([condition1,condition2,condition3,condition4,condition5]):
                    #Avoid NaNs and non spaced indices
                    #For the first component WLs
                    ints[i,j,0] = simps(compo_1[self.idx_min_max_mat[i,j,0,0]:\
                        self.idx_min_max_mat[i,j,1,0]],\
                    Eloss[self.idx_min_max_mat[i,j,0,0]:self.idx_min_max_mat[i,j,1,0]])
                    #For the second component WL
                    ints[i,j,1] = simps(compo_2[self.idx_min_max_mat[i,j,0,1]:\
                        self.idx_min_max_mat[i,j,1,1]],\
                    Eloss[self.idx_min_max_mat[i,j,0,1]:self.idx_min_max_mat[i,j,1,1]])
                else:
                    ints[i,j,1] = np.nan
                    ints[i,j,0] = np.nan
                self.num_prog1+=1
        self.fwhm_run = False
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','comp'],ints),\
            'EnergyLimits':(['y','x','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
        self.image_ratio_placement.object = hv.HeatMap(self.dataset_auto.Components_Ratios)\
            .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                xlim = self.xlims,ylim = self.ylims,\
                selection_line_alpha = 1,nonselection_line_alpha = 0,line_alpha = 0,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = [self.hover_ratio],shared_axes = False,\
                colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
        self.fitting_in_place = True
        self.cbar_wid[0].disabled = False
        self.cmap_wid[0].disabled = False
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_single,streams=[self.stream_tapping])
        self.button_show_windows[0].disabled = False
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.button_type = 'default'
        self.button_launch_advanced_analyzer.disabled = True
        
    '''
    @param.depends('numb',watch = True)
    def plot_ratio_heatmap(self):
        #We have to ensure that a calculation was made
        if not self.advancedFWHM_run:
            #basically, do nothing until we have the actual integration run completed
            return self.im_empty
        imi = hv.HeatMap(self.dataset_auto['Components_Ratios'].isel(mult = self.numb))\
        .opts(cmap = 'viridis',invert_yaxis = True, frame_height=325,\
        colorbar = True,colorbar_position = 'bottom',clipping_colors={'NaN':'black'},\
        xaxis=None,yaxis=None,alpha = 1,tools = ['hover','tap'],\
        line_width = 1.25,line_color = 'grey',selection_line_color = 'lime',\
        selection_alpha = 1, nonselection_alpha = 0.75,shared_axes = False)
        return imi
    '''
    def get_keywords(self):
        lista_edges = []
        self.dictio_edges = dict()
        self.dictio_ELNES_limits = dict()
        for elm in self.elements_list:
            for var in self.ds.data_vars:
                #The best choice is to work with the given dateset,to avoid mistakes
                lista = var.split('_')
                if elm in lista[0] and 'cont' in lista:
                    nombre = ' '.join([elm,lista[0].split(elm)[1]])
                    if nombre not in lista_edges:
                        lista_edges.append(nombre)
                        self.dictio_edges[nombre] = []
        #We have to rerun again the whole set of components
        for clave in self.dictio_edges:
            ele,edg = clave.split(' ')
            lista_ssh = [''.join([list(edg)[0],sh]) for sh in list(edg)[1:]]
            for var in self.ds.data_vars:
                for ssh in lista_ssh:
                    if all([el in var for el in [ele,'component',ssh]]) and 'cont' not in var:
                        subshell_el = var.split('_')[0]
                        self.dictio_edges[clave].append(subshell_el)
        self.param['full_edge'].objects = list(self.dictio_edges)
        self.full_edge = self.param['full_edge'].objects[0]
        #And the final rerun over the already formed dictionary - 
        # to set up the limit parameters
        for edge in self.dictio_edges:
            self.dictio_ELNES_limits[edge] = dict()
            for sshell in self.dictio_edges[edge]:
                clave1 = ''.join([sshell,'_fwhm'])
                clave2 = ''.join([sshell,'_center'])
                fw_half = np.nanmedian(self.ds[clave1].values)/2
                cent_ini = np.nanmedian(self.ds[clave2].values)
                #This is the initial value given for the integration
                # for any given component.
                self.dictio_ELNES_limits[edge][sshell] =\
                [round(cent_ini-fw_half*2.5,2),round(cent_ini+fw_half*2.5,2)]
        #A default dictionary for recovery
        self.dictio_ELNES_lims_default = cp.deepcopy(self.dictio_ELNES_limits)
        
    def create_launch_layout(self):
        self.dynamic_placement =\
            pn.pane.HoloViews(self.dynamic_tap.opts(shared_axes= False,framewise = True))
        self.image_placement   = pn.pane.HoloViews(self.hmap*self.im)
        self.image_ratio_placement = pn.pane.HoloViews(self.im_empty)
        '''
        self.scatter_analysis_placement = pn.pane.HoloViews(self.scatter_empty)
        sli_number = pn.Row(self.numb_markdown,self.slider_number_value,self.slider_number)
        '''
        self.ratio_on_display = pn.pane.Markdown('#### Ratio on display : None',\
            style = {'color':'lightgrey'},width = 200,margin = (0,35))
        butt_ons = pn.Row(self.button_show_cents,self.button_show_windows,\
            self.button_change_DirectInverse,align = 'center',margin = (5,10),width = 580)
        fila1 = pn.Row(pn.pane.Markdown('#### Ratio-map Colormap',\
                style = {'color':'white'},width = 200,margin = (5,25)),\
            self.cmap_wid,width = 575)
        fila2 = pn.Row(pn.pane.Markdown('#### Ratio-map Range',\
                style = {'color':'white'},width = 200,margin = (5,25)),\
            self.cbar_wid,width = 575)
        fila3 = pn.Row(self.ratio_on_display,self.button_launch_advanced_analyzer,\
            width = 575)
        modifs = pn.Column(fila1,fila2,width = 590,margin = 10)
        self.graph_buttons = pn.Column(\
            pn.pane.Markdown('#### Controls for the graphs on display',\
                style = {'color':'white'},margin = (5,15,-10,15),width = 550),\
            pn.layout.Divider(height = 5,margin = (0,15,5,15)),\
            butt_ons,modifs,fila3,\
            height = 325,width = 600,background = 'grey',margin = (0,10))
        
        self.tab_controls_graph = pn.Tabs(('Controls',self.graph_buttons),('Info',self.info_panel),\
            tabs_location='left',width = 705,height = 325,margin = (10,0,0,0))
        '''
        self.tab_graphs = pn.Tabs(('Spectra Analysis',pn.Row(self.dynamic_placement)),\
            ('Multiplier/Ratio Analysis',pn.Row(self.scatter_analysis_placement)))
        
        first_row = pn.Row(pn.Tabs(('Image',self.image_placement),('Info',self.info_panel)),\
            self.tab_graphs)
        '''
        first_row = pn.Row(self.image_placement,self.dynamic_placement,height = 400)
        second_row = pn.Row(self.image_ratio_placement,self.tab_controls_graph,height = 425)
        button_col = pn.Column(pn.Row(pn.pane.Markdown('### WL ratio analysis',\
                style ={'color':'white'},align = 'center',width = 150,\
                height = 40,margin = (0,0,0,15)),\
                self.button_include_cont,align = 'center',width = 380,height = 50,margin = 0),\
            pn.layout.Divider(height = 5,margin = (0,25,5,25)),\
            pn.pane.Markdown('#### Edge selector',\
                style ={'color':'white'},align = 'center',width = 350,\
                height = 25,margin = (0,25)),\
            self.edge_selection_widget,\
            pn.pane.Markdown('#### Integration mode selector and options',\
                style ={'color':'white'},align = 'center',width = 350,\
                height = 25,margin = (0,25)),\
            pn.layout.Divider(height = 5,margin = (5,25)),\
            self.mode_selector,self.width_selector,\
            self.component_to_int_selector,\
            self.width_manual_selector,\
            pn.Row(self.fixed_width_configurator,\
                self.fixed_width_compo_markdown,\
                width = 280,margin = (0,50),align = 'center'),\
            self.component_selector,self.width_compo_markdown,\
            pn.Row(self.button_reset_widths,self.E0_wid,self.E1_wid,\
                #self.width_compo_markdown,\
                width = 280,margin = (0,50),align = 'center'),\
            #This part is to be included anywhere but here...
            #pn.Row(self.numb_markdown,self.slider_number_value,\
            #    self.slider_number,width = 330,align = 'center',\
            #    margin = (0,35)),\
            self.select_computation_values_widget,\
            self.components_to_substraction,\
            pn.layout.Divider(height = 5,margin = (5,25)),\
            pn.Row(self.button_compute,self.button_show_computed_vals,align = 'center'),\
            self.progress_bar_advanced,\
            pn.Spacer(height = 9,margin = 0),\
            width = 400, background = 'grey')
        self.banner = pn.Spacer(width = 1100,height = 60, background='grey',margin = (0,0,14,0))
        self.layout = pn.Row(pn.Column(self.banner,first_row,second_row,width = 1100),\
            button_col)

        
#################################################################################################
#                                                                                               #
#                                                                                               #
#                      Display for the center analysis tool for SLines                          #
#                                                                                               #
#                                                                                               #
#################################################################################################
class Visual_distance_results_SLines(param.Parameterized):
    #Class for the visualization functions used for
    #Comparative parameters selectors
    components1 = param.ListSelector()
    components2 = param.ListSelector()
    element1   = param.ObjectSelector()
    element2   = param.ObjectSelector()
    range_cmap1    = param.Range(label = 'Colorbar range [eV] ')
    range_cmap2    = param.Range(label = 'Colorbar range [eV] ')
    range_cmapDiff = param.Range(label = 'Colorbar range [eV] ')
    colormap_1 = param.ObjectSelector(default= 'viridis',objects=['viridis'])
    colormap_2 = param.ObjectSelector(default= 'cividis',objects=['cividis'])
    colormap_diff = param.ObjectSelector(default= 'cividis',objects=['cividis'])
    coor_x = param.String(default=' - ')
    coor_y = param.String(default=' - ')
    vert_x0 = param.String(default=' - ')
    vert_x1 = param.String(default=' - ')
    vert_y0 = param.String(default=' - ')
    vert_y1 = param.String(default=' - ')
    dynamic_displays = param.ObjectSelector(default='Best',\
        objects=['Best','Comps.'])
    line_displays = param.ObjectSelector(objects=[])
    
    ###################################
    def __init__(self,ds,elem,colores):
        super().__init__()
        #Data and original image
        #Now the possible components to be displayed in results 
        self.list_compos = []
        self.list_ds = [cp.deepcopy(ds),]
        for comp in ds.data_vars:
            if '_component' in comp and '_cont' not in comp:
                self.list_compos.append(comp.split('_component')[0])
            elif 'K_' in comp and '_component' in comp:
                #This is new, controls when we add the onsets for K edges
                self.list_compos.append(comp.split('_cont_component')[0])
                self._create_onset_ds(ds,comp,'K-type')
            else:pass
        self.ds = xr.merge(self.list_ds)
        self.hov_lims = (self.ds.Eloss.values[0],self.ds.Eloss.values[-1],\
            self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        self.step = 0.05
        self.button_show_scatter = pn.widgets.Button(name = 'Show component center-distribution',\
            disabled = True,height = 32, button_type = 'default',margin = (10,25))
        self.button_show_scatter.on_click(self._show_both_center_compos)
        self.button_show_dist_scatt = pn.widgets.Button(name = 'Show distances',disabled = True,\
            height = 32, button_type = 'default',margin = (10,25))
        self.button_show_dist_scatt.on_click(self._show_compos_dists)
        self.colbaropts = {'height':85,'width':25,\
            'major_label_text_color':'black',\
            'border_line_alpha':0,'label_standoff':10,'scale_alpha':1,\
            'major_tick_line_width':2,'padding':15,\
            'bar_line_width':0,'bar_line_color':'white'}
        self.sl_image = hv.Image(self.ds,kdims = ['Eloss','y'],vdims = ['OriginalData'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',xlabel ='Electron Energy Loss [eV]',\
            cmap = 'Greys_r',shared_axes = False,xaxis = 'top',\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 100,frame_width = 375,\
            alpha = 1,tools = ['hover'],colorbar = True,colorbar_position = 'right',\
            colorbar_opts = self.colbaropts,toolbar = 'above')
        empty_Data =\
            xr.Dataset({'EmptyData':(['y','x','Eloss'],\
            np.zeros_like(self.ds.OriginalData.values))},\
            coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
            'Eloss':self.ds.Eloss.values})
        self.ds_compos = xr.Dataset({'compo1':(['y'],\
            np.zeros_like(self.ds.OriginalData.values[:,0,0])),\
            'compo2':(['y'],\
            np.zeros_like(self.ds.OriginalData.values[:,0,0])),\
            'compodiff':(['y'],\
            np.zeros_like(self.ds.OriginalData.values[:,0,0]))},\
            coords = {'y':self.ds.y.values})
        self.im_empty = hv.Image(empty_Data,kdims = ['Eloss','y'],vdims = ['EmptyData'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            cmap = 'Greys_r',shared_axes = False,\
            xaxis = None,yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 100,frame_width = 375,\
            alpha = 1,tools = ['hover'],colorbar = True,colorbar_position = 'right',\
            colorbar_opts = self.colbaropts,toolbar = 'above')
        self.curve_empty = hv.Curve(empty_Data.isel(x = 0,y = 0),\
        kdims = ['Eloss'],vdims = ['EmptyData'])\
        .opts(frame_height = 250,frame_width = 550,show_grid = True,\
            shared_axes = False,yformatter=formatter,xlabel = 'Electron Energy Loss [eV]',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        self.scatter_empty = hv.Scatter(empty_Data.isel(x = 0,Eloss = 0),\
        kdims = ['y'],vdims = ['EmptyData'])\
        .opts(frame_height = 250,frame_width = 550,show_grid = True,yformatter=formatter_y_SL,\
            shared_axes = False,framewise = True,title = 'No data',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        self.area_empty = hv.Area(empty_Data.isel(x = 0,y = 0),\
        kdims = ['Eloss'],vdims = ['EmptyData'])\
        .opts(frame_height = 250,frame_width = 550,show_grid = True,\
            shared_axes = False,yformatter=formatter,\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'lightgrey',bgcolor = 'black',hooks = [hook_full_black_black])
        #Dynamic_map_as we click the SL
        self.stream_tap_SL = streams.SingleTap(x = -1,y = -1,source = self.sl_image)
        self.dyn_ori =\
            hv.DynamicMap(self.plot_ori_SL,streams=[self.stream_tap_SL])\
            .opts(align = 'end',frame_height = 250,shared_axes = False,frame_width = 550,\
            show_grid = True,framewise = True,\
            yformatter=formatter,\
            bgcolor = 'black',hooks = [hook_full_black_black])
        #Colordictionary
        if type(colores) == dict:
            self.cmap_clusters =\
            [colores[el] for el in colores if el != 'default']
        elif type(colores) == list:
            self.cmap_clusters = colores
        #Colormaps to be selected
        self.param['colormap_1'].objects = hv.plotting.util.list_cmaps(category='Uniform Sequential')
        self.param['colormap_2'].objects = hv.plotting.util.list_cmaps(category='Uniform Sequential')
        self.param['colormap_diff'].objects = hv.plotting.util.list_cmaps(category='Uniform Sequential')
        ##### Time to set up some of the options in the parameters
        self.param['element1'].objects = elem
        self.element1 = elem[0]
        self.param['element2'].objects = elem
        self.element2 = elem[0]
        #Update_characteristics button
        
        


    def plot_ori_SL(self,x,y):
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            E0,y0 = self.sl_image.closest((x,y))
            #Dinmaps changes
            area = hv.Area(self.ds.OriginalData.isel(x = 0,y = int(y0)))\
                .opts(align = 'end',show_title=False,line_alpha = 0,fill_color = 'white',\
                fill_alpha = 0.5,yformatter=formatter,framewise = True)
            return area

    def _show_both_center_compos(self,event):
        self.button_show_scatter.button_type = 'default'
        self.button_show_scatter.disabled = True
        #Calculations for the ylims
        b1 = self.param['range_cmap1'].bounds
        b2 = self.param['range_cmap2'].bounds
        new_range = (min(b1[0],b2[0]),max(b1[1],b2[1]))
        dif = abs(new_range[0]-new_range[1])
        new_range_extended = (new_range[0]-dif*0.05,new_range[1]+dif*0.05)
        self.plot_scatter_placeholder.object =\
            self.scatter_plot2.opts(ylim = new_range_extended)\
            *self.scatter_plot1.opts(ylim = new_range_extended)
        self.button_show_dist_scatt.disabled = False
        self.button_show_dist_scatt.button_type = 'success'

    def _show_compos_dists(self,event):
        self.button_show_dist_scatt.button_type = 'default'
        self.button_show_dist_scatt.disabled = True
        self.button_show_scatter.disabled = False
        self.button_show_scatter.button_type = 'success'
        self.plot_scatter_placeholder.object = self.scatter_plotdiff\
            .opts(cmap = self.colormap_diff,clim = self.param['range_cmapDiff'].bounds)
        


    def _create_onset_ds(self,ds,clave,type_compo):
        '''This method creates the onset data structures,
        so we can use onsets to measure distances'''
        #This conditional will allow an expansion to include 
        #onsets for elements with elnes in the future
        if type_compo == 'K-type':
            vals = ds[clave].values
            diff2 = np.zeros_like(vals)
            diff2[:,:,2:] = np.diff(np.diff(vals))
            onsets = np.zeros_like(vals[:,0,:])
            indices = np.nanargmin(np.abs(diff2[:,0,:] -\
                np.nanmax(diff2[:,0,:],axis=-1)[:,None]),axis= -1)
            onsets[:] = ds.Eloss.values[indices][:,None]
            onsets[onsets == ds.Eloss.values[0]] = np.nan
            new_clave = ''.join([clave.split('_')[0],'_onset'])
            dsons = xr.Dataset({new_clave:(['y','Eloss'],onsets)},\
                coords = {'y':ds.y.values,'Eloss':ds.Eloss.values})
            self.list_ds.append(dsons)

    @param.depends('element1',watch = True)
    def _change_compos_available1(self):
        self.components1 = []
        self.param['components1'].objects =\
        [comp.split(self.element1)[1] for comp in self.list_compos if self.element1 in comp]
        '''
        try:
            self.button_show_distances_panel.disabled = True
        except: pass
        '''

    @param.depends('element2',watch = True)
    def _change_compos_available2(self):
        self.components2 = []
        self.param['components2'].objects =\
        [comp.split(self.element2)[1] for comp in self.list_compos if self.element2 in comp]
        '''
        try:
            self.button_show_distances_panel.disabled = True
        except: pass
        '''
    @param.depends('components1',watch = True)
    def _activate_show_button_distance_1(self):
        try:
            if self.components1 != []:
                self.button_show_1.disabled = False
                self.button_show_1.button_type = 'primary'
            else:
                self.button_show_1.disabled = True
                self.button_show_1.button_type = 'default'
        except: pass
        '''
        try:
            self.button_show_distances_panel.disabled = True
        except: pass
        '''
    @param.depends('components2',watch = True)
    def _activate_show_button_distance_2(self):
        try:
            if self.components2 != []:
                self.button_show_2.disabled = False
                self.button_show_2.button_type = 'primary'
            else:
                self.button_show_2.disabled = True
                self.button_show_2.button_type = 'default'
        except: pass
        '''
        try:
            self.button_show_distances_panel.disabled = True
        except: pass
        '''
    '''
    @param.depends('range_cmap1','colormap_1',watch = True)
    def _modify_lim_slide1(self):
        try:
            self.image_placeholder1.object =\
            self.image_placeholder1.object\
            .opts(clim = tuple([el for el in self.range_cmap1]),\
            cmap = self.colormap_1)
        except:
            pass
        
    @param.depends('range_cmap2','colormap_2',watch = True)
    def _modify_lim_slide2(self):
        try:
            self.image_placeholder2.object =\
            self.image_placeholder2.object\
            .opts(clim = tuple([el for el in self.range_cmap2]),\
            cmap = self.colormap_2)
        except:
            pass
    
    @param.depends('range_cmapDiff','colormap_diff',watch = True)
    def _modify_lim_slide_diff(self):
        try:
            self.image_placeholder_diff.object =\
            self.image_placeholder_diff.object\
            .opts(clim = tuple([el for el in self.range_cmapDiff]),\
            cmap = self.colormap_diff)
        except:
            pass
    '''
    @param.depends('components1','components2',watch = True)
    def _activate_show_button_distances(self):
        try:
            if self.components2 != [] and self.components1 != []:
                self.button_dist_compos.disabled = False
                self.button_dist_compos.button_type = 'success'
            else:
                self.button_dist_compos.disabled = True
                self.button_dist_compos.button_type = 'default'
        except: pass  
        
    
    def _callback_get_distances(self,event):
        #We have to compute the distances - \
        # and get the image of distance difference, as well as a histogram
        self.button_dist_compos.disabled = True
        self.cmap_seldiff[0].disabled = False
        self.slider_diff[0].disabled = False
        if self.components1[0] == 'K':
            tag1 = ''.join([self.element1,self.components1[0],'_onset'])
        else:        
            tag1 = ''.join([self.element1,self.components1[0],'_center'])
        if self.components2[0] == 'K':
            tag2 = ''.join([self.element2,self.components2[0],'_onset'])
        else:        
            tag2 = ''.join([self.element2,self.components2[0],'_center'])
        #titl = ''.join(['Distance ',self.element1,self.components1[0],'-',\
        #    self.element2,self.components2[0]])
        #xrArr = xr.ufuncs.fabs(self.ds[tag1]-self.ds[tag2])  #Deprecated
        clavediff = ' '.join(['Distance',tag1.split('_')[0],'-',tag2.split('_')[0]])
        xrArr = abs(self.ds[tag1]-self.ds[tag2])
        self.ds_dist = xrArr.to_dataset(name = 'Distances')
        maxi = round(np.nanmax(self.ds_dist.Distances.values))
        mini = round(np.nanmin(self.ds_dist.Distances.values))
        #diff_var = (maxi-mini) * 0.05
        self.param['range_cmapDiff'].bounds = (mini-2,maxi+2)
        self.range_cmapDiff = (mini,maxi)
        self.ds_compos.compodiff.values = self.ds_dist.Distances.values[:,0]
        self.image_diff = hv.Image(self.ds_dist,kdims = ['Eloss','y'],\
        vdims = ['Distances'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',xlabel ='Electron Energy Loss [eV]',\
            cmap = self.colormap_diff,shared_axes = False,\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 100,frame_width = 375,framewise = True,\
            alpha = 1,tools = ['hover'],colorbar = True,colorbar_position = 'right',\
            colorbar_opts = self.colbaropts,clipping_colors = {'NaN': 'black'},\
            clim = self.range_cmapDiff,toolbar = 'above')
        self.image_placeholder_diff.object = self.image_diff 
        self.scatter_plotdiff = hv.Scatter(self.ds_compos,kdims=['y'],vdims = ['compodiff'])\
        .opts(frame_width  = 550, frame_height = 250,size = 7,\
            marker = 's',line_width = 1.5,\
            fill_alpha = 0.5,fill_color = 'compodiff',\
            ylim = self.param['range_cmapDiff'].bounds,\
            show_grid = True,line_alpha = 1,title = clavediff,\
            cmap = self.colormap_diff,line_color = 'compodiff',\
            ylabel = 'E-loss center-value [eV]',\
            xlabel = 'Pixel number # along the spectrum-line',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        self.plot_scatter_placeholder.object = self.scatter_plotdiff
        self.button_show_scatter.disabled = False
        self.button_show_scatter.button_type = 'success'
        self.button_show_dist_scatt.button_type = 'default'
        self.button_show_dist_scatt.disabled = True
        
    def _callback_show_comp2_feature(self,event):
        if self.components2[0] == 'K':
            clave21 = ''.join([self.element2,self.components2[0],'_onset'])
            clave22 = ''.join([self.element2,self.components2[0],' : Continuum-onset'])
        else:
            clave21 = ''.join([self.element2,self.components2[0],'_center'])
            clave22 = ''.join([self.element2,self.components2[0],' : ELNES-center'])
        #titl = ''.join([self.element1,self.components1[0],' Center'])
        maxi = round(np.nanmax(self.ds[clave21].values))
        mini = round(np.nanmin(self.ds[clave21].values))
        self.param['range_cmap2'].bounds = (mini-2,maxi+2) 
        self.range_cmap2 = (mini,maxi)
        self.ds_compos.compo2.values = np.median(self.ds[clave21],axis=-1)
        im2 = hv.Image(self.ds,kdims = ['Eloss','y'],vdims = [clave21])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            cmap = 'Oranges_r',shared_axes = False,\
            xaxis = None,yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 100,frame_width = 375,alpha = 0.5,\
            tools = ['hover'],colorbar = True,colorbar_position = 'right',\
            colorbar_opts = self.colbaropts,clim = (mini,maxi),\
            clipping_colors = {'NaN': 'black'},toolbar = 'above')
        self.scatter_plot2 = hv.Scatter(self.ds_compos,kdims=['y'],vdims = ['compo2'])\
        .opts(frame_width  = 550, frame_height = 250,size = 7,\
            marker = 's',line_width = 1.5,\
            fill_alpha = 0.5,fill_color = 'compo2',\
            ylim = self.param['range_cmap2'].bounds,\
            show_grid = True,line_alpha = 1,title = clave22,\
            cmap = 'Oranges_r',line_color = 'compo2',\
            ylabel = 'E-loss center-value [eV]',\
            xlabel = 'Pixel number # along the spectrum-line',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        self.plot_scatter_placeholder.object = self.scatter_plot2
        self.image_placeholder2.object = im2
        self.slider_im2[0].disabled = False
        self.cmap_sel2[0].disabled = False
        
    def _callback_show_comp1_feature(self,event):
        #Let's check first if we are dealing with a K-Xsection or an actual ELNES feature
        if self.components1[0] == 'K':
            clave11 = ''.join([self.element1,self.components1[0],'_onset'])
            clave12 = ''.join([self.element1,self.components1[0],' : Continuum-onset'])
        else:
            clave11 = ''.join([self.element1,self.components1[0],'_center'])
            clave12 = ''.join([self.element1,self.components1[0],' : ELNES-center'])
        #titl = ''.join([self.element1,self.components1[0],' Center'])
        maxi = round(np.nanmax(self.ds[clave11].values))
        mini = round(np.nanmin(self.ds[clave11].values))
        self.param['range_cmap1'].bounds = (mini-2,maxi+2) 
        self.range_cmap1 = (mini,maxi)
        self.ds_compos.compo1.values = np.median(self.ds[clave11],axis=-1)
        im1 = hv.Image(self.ds,kdims = ['Eloss','y'],vdims = [clave11])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            cmap = 'Blues_r',shared_axes = False,\
            xaxis = None,yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 100,frame_width = 375,alpha = 0.5,\
            tools = ['hover'],colorbar = True,colorbar_position = 'right',\
            colorbar_opts = self.colbaropts,clim = (mini,maxi),\
            clipping_colors = {'NaN': 'black'},toolbar = 'above')
        self.scatter_plot1 = hv.Scatter(self.ds_compos,kdims=['y'],vdims = ['compo1'])\
        .opts(frame_width  = 550, frame_height = 250,size = 7,\
            marker = 's',line_width = 1.5,\
            fill_alpha = 0.5,fill_color = 'compo1',\
            ylim = self.param['range_cmap1'].bounds,\
            show_grid = True,line_alpha = 1,title = clave12,\
            cmap = 'Blues_r',line_color = 'compo1',\
            ylabel = 'E-loss center-value [eV]',\
            xlabel = 'Pixel number # along the spectrum-line',\
            bgcolor = 'black',hooks = [hook_full_black_black])
        self.plot_scatter_placeholder.object = self.scatter_plot1
        self.image_placeholder1.object = im1
        self.slider_im1[0].disabled = False
        self.cmap_sel1[0].disabled = False

    @param.depends('colormap_diff',watch = True)
    def _change_cmapdiff(self):
        imidiff = self.image_placeholder_diff.object
        self.image_placeholder_diff.object = imidiff.opts(cmap = self.colormap_diff)

    @param.depends('range_cmap1',watch = True)
    def _change_range1(self):
        imi1 = self.image_placeholder1.object
        self.image_placeholder1.object = imi1.opts(clim = self.range_cmap1)
    
    @param.depends('range_cmap2',watch = True)
    def _change_range2(self):
        imi2 = self.image_placeholder2.object
        self.image_placeholder2.object = imi2.opts(clim = self.range_cmap2)

    @param.depends('range_cmapDiff',watch = True)
    def _change_range_diff(self):
        imi_diff = self.image_placeholder_diff.object
        self.image_placeholder_diff.object = imi_diff.opts(clim = self.range_cmapDiff)

    def create_feature_distances_panel(self):
        #Method that creates the panel for the analysis of distances\
        # between components centers
        #Widgets for the center - distance calculators
        self.wid_el1 = pn.Param(self.param['element1'],\
            widgets = {'element1':pn.widgets.RadioButtonGroup},\
            parameters = ['element1'],width = 250,\
            show_name = False,show_labels = False,\
            margin = 0)
        self.wid_el1[0].height = 32
        self.wid_el2 = pn.Param(self.param['element2'],\
            widgets = {'element2':pn.widgets.RadioButtonGroup},\
            parameters = ['element2'],width = 250,\
            show_name = False,show_labels = False,\
            margin = 0)
        self.wid_el2[0].height = 32
        self.wid_compos1 = pn.Param(self.param['components1'],\
            widgets = {'components1':pn.widgets.MultiChoice},\
            parameters = ['components1'],width = 150,\
            show_name = False,show_labels = False,margin = 0)
        self.wid_compos2 = pn.Param(self.param['components2'],\
            widgets = {'components2':pn.widgets.MultiChoice},\
            parameters = ['components2'],width = 150,\
            show_name = False,show_labels = False,margin = 0)
        self.wid_compos1[0].max_items = 1
        self.wid_compos2[0].max_items = 1
        self.wid_compos2[0].margin = (5,10,0,10)
        self.wid_compos1[0].margin = (5,10,0,10)
        #widgets for the cmap
        # - limits sliders
        self.slider_im1 = pn.Param(self.param['range_cmap1'],\
            widgets = {'range_cmap1':pn.widgets.RangeSlider},\
            parameters = ['range_cmap1'],show_labels = False,\
            margin = (5,0),width = 25,show_name = False,height = 75)
        self.slider_im2 = pn.Param(self.param['range_cmap2'],\
            widgets = {'range_cmap2':pn.widgets.RangeSlider},\
            parameters = ['range_cmap2'],show_labels = False,\
            margin = (5,0),width = 25,show_name = False,height = 75)
        self.slider_im2[0].step = self.step
        self.slider_im1[0].step = self.step
        self.slider_im1[0].orientation = 'vertical'
        self.slider_im2[0].orientation = 'vertical'
        self.slider_im2[0].show_value = False
        self.slider_im1[0].show_value = False
        self.slider_im1[0].disabled = True
        self.slider_im2[0].disabled = True
        self.slider_diff = pn.Param(self.param['range_cmapDiff'],\
            widgets = {'range_cmapDiff':pn.widgets.RangeSlider},\
            parameters = ['range_cmapDiff'],show_labels = False,\
            margin = (5,0),height = 75,width = 25)
        self.slider_diff[0].step = self.step
        self.slider_diff[0].orientation = 'vertical'
        self.slider_diff[0].show_value = False
        self.slider_diff[0].disabled = True
        # - colormaps
        self.cmap_sel1 = pn.Param(self.param['colormap_1'],\
            widgets = {'colormap_1':pn.widgets.Select},\
            parameters = ['colormap_1'],width = 125,\
            name = 'Visual config',show_labels = False,\
            margin = (5,0),show_name = False)
        self.cmap_sel2 = pn.Param(self.param['colormap_2'],\
            widgets = {'colormap_2':pn.widgets.Select},\
            parameters = ['colormap_2'],width = 125,\
            name = 'Visual config',show_labels = False,\
            margin = (5,0),show_name = False)
        self.cmap_seldiff = pn.Param(self.param['colormap_diff'],\
            widgets = {'colormap_diff':pn.widgets.Select},\
            parameters = ['colormap_diff'],width = 125,\
            name = 'Visual config',show_labels = False,\
            margin = (5,0),show_name = False)
        self.cmap_sel1[0].disabled = True
        self.cmap_sel2[0].disabled = True
        self.cmap_seldiff[0].disabled = True
        #Now a button to create the distance image
        self.button_dist_compos = pn.widgets.Button(name = 'Compute distances',\
            align = 'center',height = 40,width = 225)
        self.button_dist_compos.on_click(self._callback_get_distances)
        self.button_dist_compos.disabled = True
        self.button_show_1 = pn.widgets.Button(name = 'Show',\
            align = 'center',disabled = True,width = 80,height = 40,margin = (6,10))
        self.button_show_1.on_click(self._callback_show_comp1_feature)
        self.button_show_2 = pn.widgets.Button(name = 'Show',\
            align = 'center',disabled = True,width = 80,height = 40,margin = (6,10))
        self.button_show_2.on_click(self._callback_show_comp2_feature)
        '''
        self.button_show_distances_panel =\
        pn.widgets.Button(name = 'Launch advanced analyser',\
            align = 'center',height = 40,width = 220)
        self.button_show_distances_panel.disabled = True
        self.button_show_distances_panel.on_click(self._callback_show_diff_stats)
        '''
        #Let's build the structure
        self.image_original_placeholder = pn.pane.HoloViews(self.sl_image)
        self.image_placeholder1     = pn.pane.HoloViews(self.im_empty)
        self.image_placeholder2     = pn.pane.HoloViews(self.im_empty)
        self.image_placeholder_diff = pn.pane.HoloViews(self.im_empty)
        self.plot_dyna_placeholder = pn.pane.HoloViews(self.dyn_ori,align = 'end')
        self.plot_scatter_placeholder = pn.pane.HoloViews(self.scatter_empty,align = 'end')
        #original_row = pn.Row(self.image_original_placeholder)
        buttons1 = pn.Column(pn.Spacer(width = 290,height = 32,margin = 0),\
            pn.Row(pn.Column(self.wid_el1,pn.Row(self.wid_compos1,self.button_show_1)),\
            self.slider_im1),width = 290,margin = 0,height = 143)
        buttons2 = pn.Column(pn.Spacer(width = 290,height = 32,margin = 0),\
            pn.Row(pn.Column(self.wid_el2,pn.Row(self.wid_compos2,self.button_show_2)),\
            self.slider_im2),width = 290,margin = 0,height = 143)
        buttons_diff = pn.Column(pn.Spacer(width = 290,height = 32,margin = 0),\
            pn.Row(pn.Column(self.button_dist_compos,self.cmap_seldiff),\
            self.slider_diff),width = 290,margin = 0,height = 143)
        #im1_row = pn.Row(self.image_placeholder1,buttons1)
        #im2_row = pn.Row(self.image_placeholder2,buttons2)
        #dif_row = pn.Row(self.image_placeholder_diff,buttons_diff)
        '''
        self.images_column = pn.Column(original_row,\
            im1_row,im2_row,dif_row,width = 800)
        '''
        self.images_column = pn.Column(self.image_original_placeholder,\
            self.image_placeholder1,self.image_placeholder2,\
            self.image_placeholder_diff,width = 510,margin = 0)
        self.buttons_column = pn.Column(\
            pn.Column(pn.Spacer(width = 290,margin = 0,height = 40),\
                self.button_show_scatter,self.button_show_dist_scatt,\
                width = 290,margin = 0,height = 184),\
            buttons1,buttons2,buttons_diff,
            width = 290,margin =0)

        self.plot_column = pn.Column(\
            pn.pane.Markdown('#### Dynamic spectrum plot',\
                margin = (10,15,-10,15),style = {'color':'white'}),\
            self.plot_dyna_placeholder,\
            self.plot_scatter_placeholder,width = 675,background = 'black')

        self.distance_panel = pn.Column(\
                pn.Row(pn.pane.Markdown('### Distance between components analyser',\
                style = {'color':'white'},align = 'center',margin =(5,35))\
                ,background = 'black',height = 55,width = 1500),\
            pn.Row(pn.Spacer(width = 25,height = 650 ,background='black'),\
                self.images_column,self.buttons_column,self.plot_column,margin = 0,width = 1250),width = 1300)
        self.distance_panel[1][0].margin = 0





#################################################################################################
#                                                                                               #
#                                                                                               #
#                      Display for the WL SLines analysis tool                                  #
#                                                                                               #
#                                                                                               #
#################################################################################################
class Visual_WL_ratio_SLines(param.Parameterized):
    full_edge = param.ObjectSelector()
    mode_integration  = param.ObjectSelector(default='auto',objects = ['auto','advanced'])
    width_integration = param.ObjectSelector(default='fwhm',objects = ['fwhm','manual'])
    width_manual_integration = param.ObjectSelector(default='fixed',objects=['fixed','individual'])
    computation_values = param.ObjectSelector(default='Fitted data',objects=['Fitted data','Raw data'])
    #integration_semiwidth = param.Number(default=0.00)
    integration_E0 = param.Number(default=0.00)
    integration_E1 = param.Number(default=0.00)
    fixed_integration_semiwidth = param.Number(default=4.00)
    components_per_edge = param.ObjectSelector()
    components_to_integrate = param.ListSelector()
    components_to_substract = param.ListSelector(default=[],objects=[])
    include_continuum = param.Boolean(default=False)
    #extra_corrections = param.Boolean(default=False)
    colormap_1 = param.ObjectSelector(default= 'viridis',objects=['viridis'])
    range_cmap1    = param.Range(label = 'Colorbar range [eV] ')
    #progress bars
    num_prog1 = param.Integer(default=0)
    #Showing integration windows
    show_wind = param.Boolean(default=False)
    show_centers = param.Boolean(default=False)
    #This controls some options only available when performing FWHM dependent calcuations
    fwhm_run = param.Boolean(default = False)
    
    
    def __init__(self,ds,colores = dict(),elems= list()):
        super().__init__()
        #We configure some of the elements
        self.ds = ds
        self.elements_list = elems
        #This is for the multiplier - those numbers are allowed as multipliers of fwhm
        multi_simple1 = np.linspace(0.25,1,12,endpoint=False)
        multi_simple2 = np.linspace(1,6,17)
        self.multi_complex = np.concatenate((multi_simple1,multi_simple2))
        #Colormaps available
        self.param['colormap_1'].objects =\
        hv.plotting.util.list_cmaps(category='Uniform Sequential')
        #now a little trick to know the E resolution
        step = self.ds.Eloss.values[1] - self.ds.Eloss.values[0] 
        self.param['integration_E0'].step = step
        self.param['integration_E1'].step = step
        self.param['fixed_integration_semiwidth'].step = step
        '''
        if len(str(step).split('.')) == 1:
            self.param['integration_E0'].step = 1
            self.param['integration_E1'].step = 1
            self.param['fixed_integration_semiwidth'].step = 1
        else: 
            expo = len(str(step).split('.')[-1])
            self.param['integration_E0'].step = 1/10**expo
            self.param['integration_E1'].step = 1/10**expo
            self.param['fixed_integration_semiwidth'].step = 1/10**expo
        '''
        '''
        self.param['numb'].label = 'Positional index'
        self.param['numb'].bounds = (0,int(self.multi_complex.size)-1)
        '''
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
        #Now the edges available for analysis - full edges with all the ELNES
        self.get_keywords()
        #Now we prepare the image and the heatmap
        #We desing a tooltip for hovering
        TT_coords = [("Energy Loss","@Eloss"),("Position # along line","@y")]
        TT_ratio = [("y","@y"),("Ratio","@Components_Ratios")]
        TT_ratio_i = [("y","@y"),("Ratio","@Components_Inverted_Ratios")]
        self.hover_tip_coords = HoverTool(tooltips=TT_coords)
        self.hover_ratio = HoverTool(tooltips=TT_ratio,mode = 'hline')
        self.hover_ratio_i = HoverTool(tooltips=TT_ratio_i,mode = 'hline')
        self.colbaropts = {'height':25,'width':590,\
            'major_label_text_color':'black',\
            'border_line_alpha':0,\
            'label_standoff':5,'scale_alpha':1,\
            'major_tick_line_width':2,'padding':5,\
            'bar_line_width':1,'bar_line_color':'black'}
        #Change here
        self.im = hv.Image(self.ds,kdims = ['Eloss','y'],vdims = ['OriginalData'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',xlabel ='Electron Energy Loss [eV]',\
            cmap = 'Greys_r',shared_axes = False,xaxis = 'top',\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 150,frame_width = 600,\
            alpha = 1,tools = [self.hover_tip_coords],colorbar = True,\
            colorbar_position = 'bottom',\
            colorbar_opts = self.colbaropts,toolbar = 'above')
        #Data for the empty curves
        self.hov_lims = (self.ds.Eloss.values[0],self.ds.Eloss.values[-1],\
            self.ds.y.values[0]-0.5,self.ds.y.values[-1]+0.5)
        empty_Data =\
            xr.Dataset({'EmptyData':(['y','x','Eloss'],\
            np.zeros_like(self.ds.OriginalData.values)),\
            'EmptyScatter':(['mult'],np.zeros_like(self.multi_complex))},\
            coords = {'y':self.ds.y.values,'x':self.ds.x.values,\
            'Eloss':self.ds.Eloss.values,'mult':self.multi_complex})
        self.im_empty = hv.Image(empty_Data,kdims = ['Eloss','y'],vdims = ['EmptyData'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            cmap = 'Greys_r',shared_axes = False,\
            xaxis = None,yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 100,frame_width = 375,\
            alpha = 1,tools = ['hover'],colorbar = True,colorbar_position = 'bottom',\
            colorbar_opts = self.colbaropts,toolbar = 'above')
        self.curve_empty = hv.Curve(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 325,frame_width = 600,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True)
        self.area_empty = hv.Area(empty_Data.EmptyData.isel(x = 0 ,y = 0))\
        .opts(frame_height = 325,frame_width = 600,show_grid = True,\
            shared_axes = False,yformatter=formatter,\
            line_width = 1.,fill_alpha = 0.1,fill_color = 'grey',\
            line_color = 'black',framewise = True)
        self.scatter_empty = hv.Scatter(empty_Data.EmptyScatter)\
        .opts(frame_height = 325,frame_width = 600,show_grid = True,\
            shared_axes = False,yformatter=formatter,framewise = True)
        #hv.Image(self.ds.OriginalData.sum('Eloss'))\
        self.empty_VLine = hv.VLine(self.ds.Eloss.values[-1])\
            .opts(color = 'black',line_alpha = 0,line_width = 0,\
            shared_axes = False,frame_width=600,frame_height=325)
        empty_vspan = hv.VSpan(self.ds.Eloss.values[0],self.ds.Eloss.values[-1])\
        .opts(shared_axes = False,frame_width=600,frame_height=325,fill_alpha = 0,line_alpha = 0)
        self.empty_vspan = empty_vspan*empty_vspan
        #self.stream_hovering = streams.PointerXY(x = -1,y = -1,source = self.im)
        self.stream_tapping  = streams.SingleTap(x = -1,y = -1,source = self.im)
        self.stream_tapcenter  = streams.SingleTap(x = -1,y = -1,source = self.im)
        #self.dynamic_hover = hv.DynamicMap(self.plot_hover,streams=[self.stream_hovering])
        self.dynamic_tap   = hv.DynamicMap(self.plot_tap,streams=[self.stream_tapping])
        self.dynamic_centers = hv.DynamicMap(self.plot_centers,\
            streams = [self.stream_tapcenter])
        ############################
        ####### Buttons ############
        #We have to create a widget for the WL edge selection
        self.edge_selection_widget = pn.Param(self.param['full_edge'],\
            widgets = {'full_edge':pn.widgets.RadioButtonGroup},\
            parameters = ['full_edge'],show_name = False,\
            show_labels = False,align = 'center')
        self.edge_selection_widget[0].button_type = 'success'
        self.mode_selector = pn.Param(self.param['mode_integration'],\
            widgets = {'mode_integration':pn.widgets.RadioButtonGroup},\
            parameters = ['mode_integration'],show_name = False,\
            show_labels = False,align = 'center')
        self.mode_selector[0].margin = (5,10,0,10)
        self.mode_selector[0].button_type = 'primary'
        self.button_compute = pn.widgets.Button(name = 'Compute values',\
            align = 'center',button_type = 'success',width = 130)
        self.button_compute.on_click(self._callback_compute_results)
        self.button_reset_widths = pn.widgets.Button(name = '\u21bb',\
            align = 'center',disabled = True,width = 50,margin = (5,0))
        self.button_reset_widths.on_click(self._callback_reset_widths)
        '''
        self.button_show_fixed_widths = pn.widgets.Button(name = 'Show',\
            align = 'center',disabled = True,width = 100,margin = (5,0))
        self.button_show_fixed_widths.on_click(self._callback_show_fixed_widths)
        '''
        self.button_include_cont = pn.Param(self.param['include_continuum'],\
            widgets = {'include_continuum':pn.widgets.Toggle},\
            parameters = ['include_continuum'],width = 130,show_name = False,\
            show_labels = False,margin = (0,10))
        self.button_include_cont[0].disabled = True
        self.button_include_cont[0].name = 'Exclude continuum'
        self.button_include_cont[0].height = 33
        self.button_include_cont[0].margin = (10,15,5,10)
        self.button_show_computed_vals = pn.widgets.Button(name = 'save results',width = 130)
        self.button_show_computed_vals.disabled = True
        self.width_selector = pn.Param(self.param['width_integration'],\
            widgets = {'width_integration':pn.widgets.RadioButtonGroup},\
            parameters = ['width_integration'],show_name = False,\
            show_labels = False,align = 'center')
        self.width_selector[0].margin = (0,10)
        self.width_selector[0].disabled = True
        self.width_manual_selector = pn.Param(self.param['width_manual_integration'],\
            widgets = {'width_manual_integration':pn.widgets.RadioButtonGroup},\
            parameters = ['width_manual_integration'],show_name = False,\
            show_labels = False,align = 'center')
        self.width_manual_selector[0].disabled = True
        self.width_manual_selector[0].margin = (0,10)
        self.button_show_windows = pn.Param(self.param['show_wind'],\
            widgets = {'show_wind':pn.widgets.Toggle},parameters = ['show_wind'],\
            align = 'center',width = 325,show_labels = False,show_name = False)
        self.button_show_windows[0].name = 'Show integration windows'
        self.button_show_windows[0].disabled = True
        self.button_show_windows[0].width = 305
        self.button_show_cents = pn.Param(self.param['show_centers'],\
            widgets = {'show_centers':pn.widgets.Toggle},parameters = ['show_centers'],\
            align = 'center',width = 325,show_labels = False,show_name = False)
        self.button_show_cents[0].name = 'Show components centers'
        self.button_show_cents[0].width = 305
        self.button_change_DirectInverse = pn.widgets.Button(name = 'Invert ratio shown',\
            align = 'center',width = 305,disabled = True)
        self.button_change_DirectInverse.on_click(self._callback_invert_display)
        self.button_launch_advanced_analyzer = pn.widgets.Button(name = 'Advanced Analyser',\
            align = 'center',width = 305,disabled = True)
        self.button_launch_advanced_analyzer.on_click(self._callback_launch_advanced)
        ##################
        self.E0_wid = pn.Param(self.param['integration_E0'],\
            widgets = {'integration_E0':pn.widgets.Spinner},\
            parameters = ['integration_E0'],\
            name = 'Integration half-width',show_name = False,\
            show_labels = False,align = 'center',width = 115,margin = (5,0))
        self.E1_wid = pn.Param(self.param['integration_E1'],\
            widgets = {'integration_E1':pn.widgets.Spinner},\
            parameters = ['integration_E1'],\
            name = 'Integration half-width',show_name = False,\
            show_labels = False,align = 'center',width = 115,margin = (5,0))
        self.fixed_width_configurator = pn.Param(self.param['fixed_integration_semiwidth'],\
            widgets = {'fixed_integration_semiwidth':pn.widgets.Spinner},\
            parameters = ['fixed_integration_semiwidth'],show_labels = False,\
            show_name = False,align = 'center',width = 90,margin = (5,0))
        self.E0_wid[0].width = 105
        self.E0_wid[0].height = 33
        self.E0_wid[0].disabled = True
        self.E1_wid[0].width = 105
        self.E1_wid[0].height = 33
        self.E1_wid[0].disabled = True
        self.fixed_width_configurator[0].disabled = True
        self.fixed_width_configurator[0].width = 75
        self.component_selector = pn.Param(self.param['components_per_edge'],\
            widgets = {'components_per_edge':pn.widgets.RadioButtonGroup},\
            parameters = ['components_per_edge'],show_name = False,\
            show_labels = False,align = 'center')
        self.param['components_per_edge'].objects = self.dictio_edges[self.full_edge]
        self.components_per_edge = self.param['components_per_edge'].objects[0]
        self.component_selector[0].disabled = True
        self.component_selector[0].margin = (0,10)
        self.width_compo_markdown =\
            pn.pane.Markdown('#### Integration window values E0 - E1[eV]',width = 250,\
            style = {'color':'lightgrey'},align = 'start',margin = (0,25,-15,60))
        self.fixed_width_compo_markdown =\
            pn.pane.Markdown('#### WL 1/2 integration width[eV]',width = 200,\
            style = {'color':'lightgrey'})
        self.component_to_int_selector = pn.Param(self.param['components_to_integrate'],\
            widgets = {'components_to_integrate':pn.widgets.MultiChoice},\
            parameters = ['components_to_integrate'],width = 280,\
            name = 'Components to compare',show_name = True,show_labels = False,\
            align = 'center')
        self.components_to_substraction = pn.Param(self.param['components_to_substract'],\
            widgets = {'components_to_substract':pn.widgets.MultiChoice},\
            parameters = ['components_to_substract'],width = 280,\
            name = 'Components to correct raw signal',show_name = True,show_labels = False,\
            align = 'center')
        self.select_computation_values_widget =\
            pn.Param(self.param['computation_values'],\
            widgets = {'computation_values':pn.widgets.RadioButtonGroup},\
            parameters = ['computation_values'],\
            show_name = False,show_labels = False,align = 'center')
        self.select_computation_values_widget[0].disabled = True
        self.component_to_int_selector[0].style = {'color':'lightgrey'}
        self.component_to_int_selector[1].disabled = True
        self.component_to_int_selector[1].max_items = 2
        self.component_to_int_selector.margin = 0
        self.component_to_int_selector[0].margin = (5,0)
        self.component_to_int_selector[1].margin = 0
        self.component_to_int_selector[1].width = 263
        self.components_to_substraction[0].style = {'color':'lightgrey'}
        self.components_to_substraction[1].disabled = True
        self.components_to_substraction.margin = 0
        self.components_to_substraction[0].margin = (5,0)
        self.components_to_substraction[1].margin = 0
        self.components_to_substraction[1].width = 263
        #NOw the information panel and buttons
        self.message_display = pn.pane.Markdown('No messages',height = 500,width = 300,\
                margin = (0,15),style = {'color':'white','text-align':'justify'})
        self.info_panel = pn.Column(\
            pn.pane.Markdown('#### Info messages',style = {'color':'white'},\
                margin = (5,15,-10,15),width = 300),\
            pn.layout.Divider(height = 5,margin = (0,15,5,15)),\
            self.message_display,\
            pn.layout.Divider(height = 5,margin = (0,15)),\
            height = 600,width = 325,background = 'black',margin = (5,10))
        #We need a little panel for the graphical control - 
        # We are going to hide it in a tab in the lower row
        self.cmap_wid = pn.Param(self.param['colormap_1'],\
            widgets = {'colormap_1':pn.widgets.Select},\
            parameters = ['colormap_1'],width = 325,show_labels = False,\
            show_name = True,name = 'Ratio-map Colormap',margin = 0)
        self.cmap_wid[0].style = {'color':'white'}
        self.cmap_wid[0].margin = (0,10)
        self.cmap_wid[1].margin = (0,10)
        self.cmap_wid[0].width = 305
        self.cmap_wid[1].width = 305
        self.cmap_wid[1].disabled = True
        self.cbar_wid = pn.Param(self.param['range_cmap1'],\
            widgets = {'range_cmap1':pn.widgets.RangeSlider},\
            parameters = ['range_cmap1'],width = 325,show_labels = True,\
            show_name = True,name = 'Ratio-map Range')
        self.cbar_wid[0].step = 0.01
        self.cbar_wid[0].style = {'color':'white'}
        self.cbar_wid[0].margin = (0,10)
        self.cbar_wid[1].margin = (0,10)
        self.cbar_wid[0].width = 305
        self.cbar_wid[1].width = 305
        self.cbar_wid[1].disabled = True
        #The progress bar for integrations
        self.progress_bar_advanced = pn.Param(self.param['num_prog1'],\
            widgets = {'num_prog1':pn.widgets.Progress(value = 0,max = 100)},\
            parameters = ['num_prog1'],align = 'center')
        self.progress_bar_advanced[0].width = 280
        self.fitting_in_place = False
        self.direct_image = True
        
    @param.depends('range_cmap1',watch = True)
    def _change_range(self):
        if self.fitting_in_place:
            self.image_ratio_placement.object =\
            self.image_ratio_placement.object.opts(clim = self.range_cmap1)
        else:
            pass
        
    @param.depends('colormap_1',watch = True)
    def _change_colormap(self):
        if self.fitting_in_place:
            self.image_ratio_placement.object =\
            self.image_ratio_placement.object.opts(cmap = self.colormap_1)
        else:
            pass
        
    @param.depends('show_wind','show_centers',watch = True)
    def _show_winds_centers(self):
        #This controls the dynamic appearance of the spectrum graphs
        if self.show_centers and not self.show_wind:
            self.button_show_cents[0].button_type = 'success'
            self.button_show_windows[0].button_type = 'default'
            self.dynamic_placement.object =\
            self.dynamic_tap*self.dynamic_centers
        elif self.show_centers and self.show_wind: 
            self.button_show_cents[0].button_type = 'success'
            self.button_show_windows[0].button_type = 'success'
            self.dynamic_placement.object =\
            self.dynamic_tap*self.dynamic_centers*self.dyn_windows
        elif self.show_wind and not self.show_centers:
            self.button_show_cents[0].button_type = 'default'
            self.button_show_windows[0].button_type = 'success'
            self.dynamic_placement.object =\
            self.dynamic_tap*self.dyn_windows
        else:
            self.button_show_cents[0].button_type = 'default'
            self.button_show_windows[0].button_type = 'default'
            self.dynamic_placement.object =\
            self.dynamic_tap
    
    @param.depends('mode_integration',watch = True)
    def _change_width_selector_availability(self):
        if self.mode_integration == 'auto':
            self.width_selector[0].disabled = True
            self.width_selector[0].button_type = 'default'
            self.components_to_integrate = []
            #We have to disable the rest of the buttons... in full auto none is available
            self.width_manual_selector[0].disabled = True
            self.width_manual_selector[0].button_type = 'default'
            self.component_selector[0].button_type = 'default'
            self.component_selector[0].disabled = True
            self.button_reset_widths.disabled = True
            '''
            self.slider_number[0].bar_color = '#FFFFFF'
            self.slider_number[0].disabled = True
            '''
            self.E0_wid[0].disabled = True
            self.E1_wid[0].disabled = True
            self.width_compo_markdown.style = {'color':'lightgrey'}
            '''
            self.numb_markdown.style = {'color':'lightgrey'}
            '''
            #We reset also the button's values so when reactivated\
            # we get the initial state again
            self.width_integration = 'fwhm'
            self.width_manual_integration = 'fixed'
            self.component_to_int_selector[0].style = {'color':'lightgrey'}
            self.component_to_int_selector[1].disabled = True
            self.select_computation_values_widget[0].disabled = True
            self.select_computation_values_widget[0].button_type = 'default'
            #self.extra_corrections_widget[0].disabled = True
            self.button_include_cont[0].disabled = True
            self.button_include_cont[0].button_type = 'default'
            self.button_include_cont[0].name = 'Exclude continuuum'
        else:
            self.width_selector[0].disabled = False
            self.width_selector[0].button_type = 'warning'
            self.component_to_int_selector[0].style = {'color':'crimson'}
            self.component_to_int_selector[1].disabled = False
            self.select_computation_values_widget[0].disabled = False
            self.select_computation_values_widget[0].button_type = 'primary'
            self.button_include_cont[0].disabled = False
            if self.include_continuum:
                self.button_include_cont[0].button_type = 'success'
                self.button_include_cont[0].name = 'Include continuuum'
            else:
                self.button_include_cont[0].button_type = 'danger'
                self.button_include_cont[0].name = 'Exclude continuuum'
            
    
    @param.depends('include_continuum',watch = True)
    def _change_cont_inclusion(self):
        if self.include_continuum:
            self.button_include_cont[0].button_type = 'success'
            self.button_include_cont[0].name = 'Include continuuum'
        else:
            self.button_include_cont[0].button_type = 'danger'
            self.button_include_cont[0].name = 'Exclude continuuum'

    @param.depends('components_to_integrate',watch = True)
    def _change_components_to_integrate_title(self):
        self.param['components_to_substract'].objects =\
        [el for el in self.dictio_edges[self.full_edge] \
        if el not in self.components_to_integrate]
        try:
            #May be none at the begining...so let's play safe
            long = len(self.components_to_integrate)
            if long == 2 and self.mode_integration == 'advanced':
                self.component_to_int_selector[0].style = {'color':'lime'}
            elif long != 2 and self.mode_integration == 'advanced':
                self.component_to_int_selector[0].style = {'color':'crimson'}
            else:
                self.component_to_int_selector[0].style = {'color':'lightgrey'}
        except:
            pass
        
    @param.depends('width_integration',watch = True)
    def _change_advanced_buttons_availability_1(self):
        if self.width_integration == 'fwhm' and self.mode_integration == 'advanced':
            #NOw the other buttons
            self.width_manual_selector[0].disabled = True
            self.width_manual_selector[0].button_type = 'default'
            self.component_selector[0].disabled = True
            self.component_selector[0].button_type = 'default'
            self.width_compo_markdown.style = {'color':'lightgrey'}
            self.E0_wid[0].disabled = True
            self.E1_wid[0].disabled = True
            self.button_reset_widths.disabled = True
            self.button_reset_widths.button_type = 'default'
            self.fixed_width_configurator[0].disabled = True
            self.fixed_width_compo_markdown.style = {'color':'lightgrey'}
            
        elif self.width_integration == 'manual' and self.mode_integration == 'advanced':
            #let's activate the possible buttons
            self.width_manual_selector[0].disabled = False
            self.width_manual_selector[0].button_type = 'primary'
            self.width_manual_integration = 'fixed'
            self.fixed_width_configurator[0].disabled = False
            self.fixed_width_compo_markdown.style = {'color':'lime'}
            
    @param.depends('width_manual_integration',watch = True)
    def _change_advanced_buttons_availability_2(self):
        if self.width_manual_integration == 'fixed' and self.mode_integration == 'advanced':
            self.component_selector[0].disabled = True
            self.button_reset_widths.disabled = True
            self.E0_wid[0].disabled = True
            self.E1_wid[0].disabled = True
            self.width_compo_markdown.style = {'color':'lightgrey'}
            self.component_selector[0].button_type = 'default'
            self.button_reset_widths.button_type = 'default'
            self.fixed_width_configurator[0].disabled = False
            self.fixed_width_compo_markdown.style = {'color':'lime'}
        elif self.width_manual_integration == 'individual' and self.mode_integration == 'advanced':
            self.component_selector[0].disabled = False
            self.button_reset_widths.disabled = False
            self.button_reset_widths.button_type = 'danger'
            self.E0_wid[0].disabled = False
            self.E1_wid[0].disabled = False
            self.integration_E0,self.integration_E1 =\
            max(self.dictio_ELNES_limits[self.full_edge][self.components_per_edge])
            self.width_compo_markdown.style = {'color':'lime'}
            self.component_selector[0].button_type = 'warning'
            self.fixed_width_configurator[0].disabled = True
            self.fixed_width_compo_markdown.style = {'color':'lightgrey'}
            
            
    @param.depends('full_edge',watch = True)
    def _change_compos_buttons(self):
        self.param['components_per_edge'].objects = self.dictio_edges[self.full_edge]
        self.components_per_edge = self.param['components_per_edge'].objects[0]
        #Changes in the available components to select
        self.param['components_to_integrate'].objects = self.dictio_edges[self.full_edge]
        self.components_to_integrate = []
        
    
    @param.depends('computation_values',watch = True)
    def _allow_compo_substraction(self):
        if self.computation_values == 'Raw data':
            self.components_to_substraction[1].disabled = False
            self.components_to_substraction[0].style = {'color':'lime'}
            self.include_continuum = False
            #self.button_include_cont[0].disabled = True
        elif self.computation_values == 'Fitted data':
            self.components_to_substract = []
            self.components_to_substraction[1].disabled = True
            self.components_to_substraction[0].style = {'color':'lightgrey'}
            #self.button_include_cont[0].disabled = False
            
    @param.depends('components_per_edge',watch = True)
    def _change_number_spinner_values(self):
        try:
            self.integration_E0,self.integration_E1 =\
                self.dictio_ELNES_limits[self.full_edge][self.components_per_edge]
        except: pass
        
    @param.depends('integration_E0','integration_E1',watch = True)
    def _change_dictio_value_semiIntWidth(self):
        self.dictio_ELNES_limits[self.full_edge][self.components_per_edge] =\
        [self.integration_E0,self.integration_E1]
    
    #TODO come back here and complete the pltting graphs according to actual dataset dimensions
    #@param.depends('numb',watch = True)
    def plot_int_windows_fwhm(self,x = -1,y = -1):
        #print('changing')
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.empty_vspan
        elif y >= yf or y <= yi:
            return self.empty_vspan
        else:
            E0,y0 = self.im.closest((x,y))
            E0 = int(E0)
            y0 = int(y0)
            #print(x0,y0)
            try:
                numer = int(self.multi_complex.size/2)
                lim00,lim10 = self.dataset_auto.isel(x = E0,y = y0,mult = numer)\
                .EnergyLimits.values[0]
                lim01,lim11 = self.dataset_auto.isel(x = E0,y = y0,mult = numer)\
                .EnergyLimits.values[1]
            except:
                return self.empty_vspan
            else:
                if any([el.astype('int32') < 0 for el in [lim00,lim01,lim10,lim11]]):
                    #This is to avoid the nan values of non fitted areas
                    return self.empty_vspan
                else:
                    span1 = hv.VSpan(x1 = lim00,x2 = lim01)\
                    .opts(shared_axes=False,fill_alpha = 0.25,fill_color = 'dodgerblue',\
                    line_alpha = 1,line_color = 'blue')
                    span2 = hv.VSpan(x1 = lim10,x2 = lim11)\
                    .opts(fill_alpha = 0.25,fill_color = 'limegreen',\
                    line_alpha = 1,line_color = 'limegreen',shared_axes = False)
                    return span1*span2
                
    def plot_int_windows_single(self,x = -1,y = -1):
        #print('changing')
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.empty_vspan
        elif y >= yf or y <= yi:
            return self.empty_vspan
        else:
            E0,y0 = self.im.closest((x,y))
            E0 = int(E0)
            y0 = int(y0)
            #print(x0,y0)
            try:
                lim00,lim10 = self.dataset_auto.isel(x = 0,y = y0)\
                .EnergyLimits.values[0]
                lim01,lim11 = self.dataset_auto.isel(x = 0,y = y0)\
                .EnergyLimits.values[1]
            except:
                return self.empty_vspan
            else:
                if any([el.astype('int32') < 0 for el in [lim00,lim01,lim10,lim11]]):
                    #This is to avoid the nan values of non fitted areas
                    return self.empty_vspan
                else:
                    span1 = hv.VSpan(x1 = lim00,x2 = lim01)\
                    .opts(shared_axes=False,fill_alpha = 0.25,fill_color = 'dodgerblue',\
                    line_alpha = 1,line_color = 'blue')
                    span2 = hv.VSpan(x1 = lim10,x2 = lim11)\
                    .opts(fill_alpha = 0.25,fill_color = 'limegreen',\
                    line_alpha = 1,line_color = 'limegreen',shared_axes = False)
                    return span1*span2
    
    def show_message(self,code):
        #This is a method to show error or probem messages in the info area
        if code == 'code01':
            mess_list = ['The selected edge only has a single ELNES.',\
                'It is not a valid option for auto WL integration',\
                'If extra ELNES structures available, choose advanced',\
                'option to analyse ratios']
            mess = ' '.join(mess_list)
        elif code == 'code02':
            mess_list = ['Components error - 2 ELNES components are',\
                'required for a integration ratio comparison. Check',\
                'the - Components to compare - box, and ensure that',\
                '2 components are selected before running calculations']
            mess = ' '.join(mess_list)
        else: mess = 'No messages'
        self.message_display.object = mess
        
    
    def plot_tap(self,x,y):
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.area_empty
        elif y >= yf or y <= yi:
            return self.area_empty
        else:
            E0,y0 = self.im.closest((x,y))
            '''
            self.x_pos = int(x0)
            self.y_pos = int(y0)
            '''
            area = hv.Area(self.ds.OriginalData.isel(x = 0,y = int(y0)))\
                .opts(show_title=False,line_width=1.25,\
                line_alpha = 1,yformatter=formatter,line_color = 'darkred',\
                fill_color = 'coral',fill_alpha = 0.5,shared_axes = False,\
                frame_height = 325,frame_width = 600,framewise = True)
            return area
    
    #@param.depends('full_edge',watch = True)
    def plot_centers(self,x,y):
        Ei,Ef,yi,yf = self.hov_lims
        if x >= Ef or x <= Ei:
            return self.empty_VLine*self.empty_VLine
        elif y >= yf or y <= yi:
            return self.empty_VLine*self.empty_VLine
        else:
            E0,y0 = self.im.closest((x,y))
            list_vlines = []
            for ed in self.dictio_edges:
                for ssh in self.dictio_edges[ed]:
                    clave = '_'.join([ssh,'center'])
                    val = np.nan_to_num(self.ds[clave].isel(x = 0,y = int(y0)), nan = -1)
                    if val > 0.0:
                        list_vlines.append(hv.VLine(val)\
                        .opts(color = 'navy',line_alpha = 1,\
                        line_width = 1))
                    else:
                        #Case of having a nan value - changed by -1 above
                        list_vlines.append(self.empty_VLine)
            objeto = list_vlines[0]
            for el in list_vlines[1:]:
                objeto *= el
            return objeto

    def _callback_invert_display(self,event):
        if self.direct_image and not self.fwhm_run:
            #We change to the inversed ratio
            self.direct_image = False
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[0],self.dataset_auto.comp.values[1])
            mini = np.nanmin(self.dataset_auto['Components_Inverted_Ratios'].values)
            maxi = np.nanmax(self.dataset_auto['Components_Inverted_Ratios'].values)
            self.image_ratio_placement.object =\
            hv.Image(self.dataset_auto,kdims = ['Eloss','y'],\
                vdims = ['Components_Inverted_Ratios'])\
            .opts(invert_yaxis = True,ylabel = 'Pixel #',\
                cmap = self.colormap_1,shared_axes = False,xaxis = None,\
                yaxis = True,yformatter = formatter_y_SL,\
                frame_height = 150,frame_width = 600,\
                alpha = 1,colorbar = True,\
                colorbar_position = 'bottom',clim = (mini,maxi),\
                colorbar_opts = self.colbaropts,toolbar = 'above',\
                tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
            #We change the range
        elif not self.direct_image and not self.fwhm_run:
            self.direct_image = True
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
            mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
            maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
            self.image_ratio_placement.object =\
            hv.Image(self.dataset_auto,kdims = ['Eloss','y'],\
                vdims = ['Components_Ratios'])\
            .opts(invert_yaxis = True,ylabel = 'Pixel #',\
                cmap = self.colormap_1,shared_axes = False,xaxis = None,\
                yaxis = True,yformatter = formatter_y_SL,\
                frame_height = 150,frame_width = 600,\
                alpha = 1,colorbar = True,\
                colorbar_position = 'bottom',clim = (mini,maxi),\
                colorbar_opts = self.colbaropts,toolbar = 'above',\
                tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
            #Changed the range again
        elif self.direct_image and self.fwhm_run:
            multiLEN = self.multi_complex.size
            self.direct_image = False
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[0],self.dataset_auto.comp.values[1])
            mini = np.nanmin(self.dataset_auto['Components_Inverted_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            maxi = np.nanmax(self.dataset_auto['Components_Inverted_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            self.image_ratio_placement.object =\
                hv.Image(self.dataset_auto.Components_Inverted_Ratios\
                    .isel(x = 0,mult = int(multiLEN/2)),kdims = ['Eloss','y'])\
                .opts(invert_yaxis = True,ylabel = 'Pixel #',\
                    #xlabel ='Electron Energy Loss [eV]',\
                    cmap = self.colormap_1,shared_axes = False,xaxis = None,\
                    yaxis = True,yformatter = formatter_y_SL,\
                    frame_height = 150,frame_width = 600,\
                    alpha = 1,colorbar = True,\
                    colorbar_position = 'bottom',clim = (mini,maxi),\
                    colorbar_opts = self.colbaropts,toolbar = 'above',\
                    tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
            '''
            self.image_ratio_placement.object =\
            hv.HeatMap(self.dataset_auto.Components_Inverted_Ratios.isel(mult = int(multiLEN/2)))\
                .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                    xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                    line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                    alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                    tools = [self.hover_ratio_i],shared_axes = False,\
                    colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
            '''
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
        else:
            multiLEN = self.multi_complex.size
            self.direct_image = True
            self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
            .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
            mini = np.nanmin(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            maxi = np.nanmax(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
            self.image_ratio_placement.object =\
                hv.Image(self.dataset_auto.Components_Ratios\
                    .isel(x = 0,mult = int(multiLEN/2)),kdims = ['Eloss','y'])\
                .opts(invert_yaxis = True,ylabel = 'Pixel #',\
                    #xlabel ='Electron Energy Loss [eV]',\
                    cmap = self.colormap_1,shared_axes = False,xaxis = None,\
                    yaxis = True,yformatter = formatter_y_SL,\
                    frame_height = 150,frame_width = 600,\
                    alpha = 1,colorbar = True,\
                    colorbar_position = 'bottom',clim = (mini,maxi),\
                    colorbar_opts = self.colbaropts,toolbar = 'above',\
                    tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
            '''
            self.image_ratio_placement.object =\
            hv.HeatMap(self.dataset_auto.Components_Ratios.isel(mult = int(multiLEN/2)))\
                .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                    xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                    line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                    alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                    tools = [self.hover_ratio],shared_axes = False,\
                    colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
            '''
            vari_mm = abs(maxi-mini)/10
            self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
            self.range_cmap1 = (mini,maxi)
    
    def _callback_launch_advanced(self,event):
        '''
        #TODO complete the external launcher
        if not self.fwhm_run:
            #This is a safeguard
            return
        else:
            self.advanced_fwhm = Advanced_visualizer_WL_ratio_FWHM(self.ds,xr.merge([self.dataset_auto,self.ds_out]),self.colormap_1)
            self.advanced_fwhm.layout()
        '''
        pass
    def _callback_reset_widths(self,event):
        #Just resets the current component integration width
        self.integration_E0,self.integration_E1 =\
        self.dictio_ELNES_lims_default[self.full_edge][self.components_per_edge]
        
    def _callback_compute_results(self,event):
        #This function is just a big decission tree to select the computation\
        # parameters and call the right function
        if self.mode_integration == 'auto':
            self.compute_full_auto()
            self.direct_image = True
        elif self.mode_integration != 'auto' and len(self.components_to_integrate) != 2:
            self.show_message('code02')
            return 
        elif self.mode_integration == 'advanced' and self.width_integration == 'fwhm':
            self.ds_out = self.prepare_dateset_to_int()
            self.compute_fwhm_dependent(self.ds_out)
            self.direct_image = True
        elif self.mode_integration == 'advanced' and self.width_integration == 'manual':
            self.ds_out = self.prepare_dateset_to_int()
            if self.width_manual_integration == 'fixed':
                self.compute_manual_fixed(self.ds_out)
                self.direct_image = True
            elif self.width_manual_integration == 'individual':
                self.compute_manual_independent(self.ds_out)
                self.direct_image = True
            else:
                #TODO write in the info panel something gone wrong
                pass
        else:
            #TODO write in the info panel something gone wrong
            pass
    
    def prepare_dateset_to_int(self):
        '''
        This method pepares the data set to be integrated. The key here is to
        get the data for the different cases : 
        (1) fitted data vs raw data
        (2) raw data vs raw data - correction components
        (3) excluding continuum vs including continuum
        ----------
        return
        ----------
        The dataset with the info to be integrated
        '''
        if self.computation_values == 'Fitted data':
            ds_list = []
            for ssh in self.components_to_integrate:
                ssh_name = '_'.join([ssh,'component'])
                if self.include_continuum:
                    name_cont = self.full_edge.split(' ')
                    name_cont.append('_cont_component')
                    ds_list.append((self.ds[ssh_name] +\
                        self.ds[''.join(name_cont)])\
                        .to_dataset(name = ssh))
                else:
                    ds_list.append((self.ds[ssh_name])\
                    .to_dataset(name = ssh))
            return xr.merge(ds_list)
        elif self.computation_values == 'Raw data':
            ds_list = []
            dat_arr = cp.deepcopy(self.ds.OriginalData)
            #Continuum substraction
            if not self.include_continuum:
                name_cont = self.full_edge.split(' ')
                name_cont.append('_cont_component')
                dat_cont = cp.deepcopy(self.ds[''.join(name_cont)])
                dat_arr -= xr.apply_ufunc(np.nan_to_num,dat_cont)
            else: pass
            for el in self.components_to_substract:
                clav = '_'.join([el,'component'])
                dat_comp = cp.deepcopy(self.ds[clav])
                dat_arr -= xr.apply_ufunc(np.nan_to_num,dat_comp)
                #We now get two different components holding the same info...for integr.
            for ssh in self.components_to_integrate:
                ds_list.append(dat_arr.to_dataset(name = ssh))
            return xr.merge(ds_list)
    
    #4 different modes of computation.... in 4 paths
    def compute_full_auto(self):
        # The first step is the calculation of the integration widths
        # it is based on the sigmas 
        #Some parameter setup before the integral's calculations
        ele = self.full_edge.split(' ')[0]
        lista = list(self.full_edge.split(' ')[1])
        #Let's check if the selected edge is a valid option
        if len(lista) < 3:
            #in this case... we are in a K edge, or a single subshell edge - no WL ratio
            self.show_message('code01')  # And we stop calculations
            return
        else: pass
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        compo1 = ''.join([ele,lista[0],lista[1]])
        compo2 = ''.join([ele,lista[0],lista[2]])
        #We only do one multiplier in auto ... 2.5 which in practice showed to be enough
        #Preparing the empty matrices
        vals = np.zeros(shap)        #Center values matrices
        Ew_halfs = np.zeros(shap+(2,2)) #Energy values of integration limits
        idx_min_max_mat = np.zeros(shap+(2,2)) #indices (positional) int. limits
        # We just need 2 indices for each component...since we run along\
        # with the higher energy gap possible ... meaning the higher sigma for a
        # given component.
        #let's look for the higher values
        max_sigs = [np.nanmax(self.ds['_'.join([compo1,'fwhm'])].values),\
            np.nanmax(self.ds['_'.join([compo2,'fwhm'])].values)]
        for i,comp in enumerate([compo1,compo2]):
            #vals suffers a slight modification given the actual shape given to centers
            #in the spectrum line deployment
            vals = self.ds['_'.join([comp,'center'])].values[:,0,None]
            Ew_halfs[:,:,0,i] = vals - 2.5625 * max_sigs[i] / 2
            Ew_halfs[:,:,1,i] = vals + 2.5625 * max_sigs[i] / 2
        idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        idx_min_max_mat = idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(2,))
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1])
        for i in range(shap[0]):
            for j in range(shap[1]):
                compo_1 = self.ds['_'.join([compo1,'component'])].values[i,j]
                compo_2 = self.ds['_'.join([compo2,'component'])].values[i,j]
                condition1 = np.nan_to_num(compo_1).sum() != 0
                condition2 = np.nan_to_num(compo_2).sum() != 0
                condition3 = idx_min_max_mat[i,j,1,0] != idx_min_max_mat[i,j,0,0]
                #if np.nan_to_num(compo_1).sum() != 0: #Avoid NaNs
                if all([condition1,condition2,condition3]):
                    #For the first component WLs
                    ints[i,j,0] = simps(compo_1[idx_min_max_mat[i,j,0,0]:\
                        idx_min_max_mat[i,j,1,0]],\
                    Eloss[int(idx_min_max_mat[i,j,0,0]):int(idx_min_max_mat[i,j,1,0])])
                    #For the second component WL
                    ints[i,j,1] = simps(compo_2[idx_min_max_mat[i,j,0,1]:\
                        idx_min_max_mat[i,j,1,1]],\
                    Eloss[idx_min_max_mat[i,j,0,1]:idx_min_max_mat[i,j,1,1]])
                else:
                    ints[i,j,1] = np.nan
                    ints[i,j,0] = np.nan
                self.num_prog1+=1
        #All computations done...time to get the dateset
        self.fwhm_run = False
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','comp'],ints),\
            'EnergyLimits':(['y','x','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        #This is also exclusive of spectrum lines - We add the extra energy dimension
        #So we can represent the ratios correctly in spectrum images
        mat_rat = np.zeros(rats.values.shape+self.ds.Eloss.shape)
        mat_rat[:,:,:] = rats.values[:,:,None]
        mat_rat_i = np.zeros(rats_inv.values.shape+self.ds.Eloss.shape)
        mat_rat_i[:,:,:] = rats_inv.values[:,:,None]
        #Now we create the raios datasets
        ratios_ds = xr.Dataset({'Components_Ratios':(['y','x','Eloss'],mat_rat),\
            'Components_Inverted_Ratios':(['y','x','Eloss'],mat_rat_i)},\
        coords = {'x':self.ds.x.values,'y':self.ds.y.values,\
            'Eloss':self.ds.Eloss.values})
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds])
        #Now we need to display the resublts
        #Create the image of ratios
        #The colorbar limits
        mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
        #It is an spectrum image now
        self.image_ratio_placement.object =\
        hv.Image(self.dataset_auto,kdims = ['Eloss','y'],\
            vdims = ['Components_Ratios'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            #xlabel ='Electron Energy Loss [eV]',\
            cmap = self.colormap_1,shared_axes = False,xaxis = None,\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 150,frame_width = 600,\
            alpha = 1,colorbar = True,\
            colorbar_position = 'bottom',clim = (mini,maxi),\
            colorbar_opts = self.colbaropts,toolbar = 'above',\
            tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
        self.fitting_in_place = True
        self.cbar_wid[1].disabled = False
        self.cmap_wid[1].disabled = False
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_single,streams=[self.stream_tapping])
        self.button_show_windows[0].disabled = False
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.button_type = 'default'
        self.button_launch_advanced_analyzer.disabled = True
        
    def compute_fwhm_dependent(self,ds_out):
        #This method integrates for each and every value of\
        # the multi-complex array multiplied by the fwhm/2 as integration limits
        # the areas in the WL selected, for each pixel independently
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        #ele = self.full_edge.split(' ')[0]
        #lista = list(self.full_edge.split(' ')[1])
        compo1,compo2 = list(self.components_to_integrate) 
        multiLEN = self.multi_complex.size
        #Preparing the empty matrices
        vals = np.zeros(shap+(multiLEN,))        #Center values matrices
        sigs = np.zeros(shap+(multiLEN,))        #sigmas matrices
        #ratio = np.zeros(shap+(multiLEN,))       #integrated ratios matrices
        Ew_halfs = np.zeros(shap+(multiLEN,2,2)) #Energy values of integration limits
        self.idx_min_max_mat = np.zeros(shap+(multiLEN,2,2)) #indices (positional) int. limits
        #The loop run the 2 components selected
        for i,comp in enumerate([compo1,compo2]):
            vals = self.ds['_'.join([comp,'center'])].values[:,0,None,None]
            sigs = self.ds['_'.join([comp,'fwhm'])].values[:,0,None,None]
            Ew_halfs[:,:,:,0,i] = vals - self.multi_complex*sigs/2
            Ew_halfs[:,:,:,1,i] = vals + self.multi_complex*sigs/2
        self.idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        self.idx_min_max_mat = self.idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(multiLEN,2))
        #We set up the progress bar
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1]*multiLEN)
        for i in range(shap[0]):
            for j in range(shap[1]):
                #compo1,compo2 = self.components_to_integrate 
                compo_1 = ds_out[compo1].values[i,j]
                compo_2 = ds_out[compo2].values[i,j]
                for k in range(multiLEN):
                    #print(i,j,k)
                    condition1 = np.nan_to_num(compo_1).sum() != 0
                    condition2 = np.nan_to_num(compo_2).sum() != 0
                    condition3 = self.idx_min_max_mat[i,j,k,1,0] != self.idx_min_max_mat[i,j,k,0,0]
                    if all([condition1,condition2,condition3]):
                        #Avoid NaNs and non spaced indices
                        #For the first component WLs
                        ints[i,j,k,0] = simps(compo_1[self.idx_min_max_mat[i,j,k,0,0]:\
                            self.idx_min_max_mat[i,j,k,1,0]],\
                        Eloss[self.idx_min_max_mat[i,j,k,0,0]:self.idx_min_max_mat[i,j,k,1,0]])
                        #For the second component WL
                        ints[i,j,k,1] = simps(compo_2[self.idx_min_max_mat[i,j,k,0,1]:\
                            self.idx_min_max_mat[i,j,k,1,1]],\
                        Eloss[self.idx_min_max_mat[i,j,k,0,1]:self.idx_min_max_mat[i,j,k,1,1]])
                    else:
                        ints[i,j,k,1] = np.nan
                        ints[i,j,k,0] = np.nan
                    self.num_prog1+=1
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','mult','comp'],ints),\
            'EnergyLimits':(['y','x','mult','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'mult':self.multi_complex,'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        mat_rat = np.zeros(rats.values.shape+self.ds.Eloss.shape)
        mat_rat[:] = rats.values[:,:,:,None]
        #mat_rat[:] = rats.values[:,None]
        mat_rat_i = np.zeros(rats_inv.values.shape+self.ds.Eloss.shape)
        mat_rat_i[:] = rats_inv.values[:,:,:,None]
        #mat_rat_i[:] = rats_inv.values[:,None]
        #Now we create the raios datasets
        ratios_ds = xr.Dataset({'Components_Ratios':(['y','x','mult','Eloss'],mat_rat),\
            'Components_Inverted_Ratios':(['y','x','mult','Eloss'],mat_rat_i)},\
        coords = {'x':self.ds.x.values,'y':self.ds.y.values,\
            'Eloss':self.ds.Eloss.values,'mult':self.multi_complex})
        '''
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        '''
        #self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds])
        mini = np.nanmin(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios']\
                .isel(mult = int(multiLEN/2)).values)
        self.image_ratio_placement.object =\
        hv.Image(self.dataset_auto.Components_Ratios\
            .isel(x  = 0,mult = int(multiLEN/2)),kdims = ['Eloss','y'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            #xlabel ='Electron Energy Loss [eV]',\
            cmap = self.colormap_1,shared_axes = False,xaxis = None,\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 150,frame_width = 600,\
            alpha = 1,colorbar = True,\
            colorbar_position = 'bottom',clim = (mini,maxi),\
            colorbar_opts = self.colbaropts,toolbar = 'above',\
            tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
        self.cbar_wid[1].disabled = False
        self.cmap_wid[1].disabled = False
        self.fitting_in_place = True
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.fwhm_run = True
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_fwhm,streams=[self.stream_tapping])
        self.show_wind = False
        self.button_show_windows[0].disabled = True
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        ''' 
        #Silenced by now....no advance launcher yet
        self.button_launch_advanced_analyzer.disabled = False
        self.button_launch_advanced_analyzer.button_type = 'success'
        '''

    def compute_manual_fixed(self,ds_out):
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        #ele = self.full_edge.split(' ')[0]
        #lista = list(self.full_edge.split(' ')[1])
        compo1,compo2 = list(self.components_to_integrate )
        #Preparing the empty matrices
        vals = np.zeros(shap)        #Center values matrices
        Ew_halfs = np.zeros(shap+(2,2)) #Energy values of integration limits
        self.idx_min_max_mat = np.zeros(shap+(2,2)) #indices (positional) int. limits
        #The loop run the 2 components selected
        for i,comp in enumerate([compo1,compo2]):
            #Modification in the values matrix with respect to SIs
            vals = self.ds['_'.join([comp,'center'])].values[:,0,None]
            Ew_halfs[:,:,0,i] = vals - self.fixed_integration_semiwidth
            Ew_halfs[:,:,1,i] = vals + self.fixed_integration_semiwidth
        self.idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        self.idx_min_max_mat = self.idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(2,))
        #We set up the progress bar
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1])
        for i in range(shap[0]):
            for j in range(shap[1]):
                #compo1,compo2 = self.components_to_integrate 
                compo_1 = ds_out[compo1].values[i,j]
                compo_2 = ds_out[compo2].values[i,j]
                condition1 = np.nan_to_num(compo_1).sum() != 0
                condition2 = np.nan_to_num(compo_2).sum() != 0
                condition3 = self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]
                if all([condition1,condition2,condition3]): 
                    #Avoid NaNs and non spaced indices
                    #For the first component WLs
                    ints[i,j,0] = simps(compo_1[self.idx_min_max_mat[i,j,0,0]:\
                        self.idx_min_max_mat[i,j,1,0]],\
                    Eloss[self.idx_min_max_mat[i,j,0,0]:self.idx_min_max_mat[i,j,1,0]])
                    #For the second component WL
                    ints[i,j,1] = simps(compo_2[self.idx_min_max_mat[i,j,0,1]:\
                        self.idx_min_max_mat[i,j,1,1]],\
                    Eloss[self.idx_min_max_mat[i,j,0,1]:self.idx_min_max_mat[i,j,1,1]])
                else:
                    ints[i,j,1] = np.nan
                    ints[i,j,0] = np.nan
                self.num_prog1+=1
        self.fwhm_run = False
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','comp'],ints),\
            'EnergyLimits':(['y','x','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        #This is also exclusive of spectrum lines - We add the extra energy dimension
        #So we can represent the ratios correctly in spectrum images
        mat_rat = np.zeros(rats.values.shape+self.ds.Eloss.shape)
        mat_rat[:,:,:] = rats.values[:,:,None]
        mat_rat_i = np.zeros(rats_inv.values.shape+self.ds.Eloss.shape)
        mat_rat_i[:,:,:] = rats_inv.values[:,:,None]
        #Now we create the raios datasets
        ratios_ds = xr.Dataset({'Components_Ratios':(['y','x','Eloss'],mat_rat),\
            'Components_Inverted_Ratios':(['y','x','Eloss'],mat_rat_i)},\
        coords = {'x':self.ds.x.values,'y':self.ds.y.values,\
            'Eloss':self.ds.Eloss.values})
        '''
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        '''
        #self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds])
        mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
        '''
        self.image_ratio_placement.object = hv.HeatMap(self.dataset_auto.Components_Ratios)\
            .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = [self.hover_ratio],shared_axes = False,\
                colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
        '''
        self.image_ratio_placement.object =\
        hv.Image(self.dataset_auto,kdims = ['Eloss','y'],\
            vdims = ['Components_Ratios'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            #xlabel ='Electron Energy Loss [eV]',\
            cmap = self.colormap_1,shared_axes = False,xaxis = None,\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 150,frame_width = 600,\
            alpha = 1,colorbar = True,\
            colorbar_position = 'bottom',clim = (mini,maxi),\
            colorbar_opts = self.colbaropts,toolbar = 'above',\
            tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
        self.fitting_in_place = True
        self.cbar_wid[1].disabled = False
        self.cmap_wid[1].disabled = False
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_single,\
            streams=[self.stream_tapping])
        self.button_show_windows[0].disabled = False
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.button_type = 'default'
        self.button_launch_advanced_analyzer.disabled = True
        
    def compute_manual_independent(self,ds_out):
        Eloss =  self.ds.Eloss.values
        shap = self.ds['OriginalData'].sum(['Eloss']).values.shape
        #lista = list(self.full_edge.split(' ')[1])
        compo1,compo2 = list(self.components_to_integrate)
        #Preparing the empty matrices
        #vals = np.zeros(shap)        #Center values matrices
        Ew_halfs = np.zeros(shap+(2,2)) #Energy values of integration limits
        self.idx_min_max_mat = np.zeros(shap+(2,2)) #indices (positional) int. limits
        #The loop run the 2 components selected
        for i,comp in enumerate([compo1,compo2]):
            #vals = self.ds['_'.join([comp,'center'])].values
            Ew_halfs[:,:,0,i] = self.dictio_ELNES_limits[self.full_edge][comp][0]
            Ew_halfs[:,:,1,i] = self.dictio_ELNES_limits[self.full_edge][comp][1]
        self.idx_min_max_mat[:] = np.searchsorted(Eloss,Ew_halfs)
        self.idx_min_max_mat = self.idx_min_max_mat.astype(int)
        ints = np.zeros(shap+(2,))
        #We set up the progress bar
        self.num_prog1 = 0
        self.progress_bar_advanced[0].max = int(shap[0]*shap[1])
        for i in range(shap[0]):
            for j in range(shap[1]):
                #compo1,compo2 = self.components_to_integrate 
                compo_1 = ds_out[compo1].values[i,j]
                compo_2 = ds_out[compo2].values[i,j]
                #if (np.nan_to_num(compo_1).sum()) != 0 and (self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]): 
                #if (np.nan_to_num(compo_1).sum()) != 0 and (self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]): 
                condition1 = np.nan_to_num(compo_1).sum() != 0
                condition2 = np.nan_to_num(compo_2).sum() != 0
                condition3 = self.idx_min_max_mat[i,j,1,0] != self.idx_min_max_mat[i,j,0,0]
                condition4 = not self.ds['_'.join([compo1,'center'])].isel(x = j,y = i).isnull()
                condition5 = not self.ds['_'.join([compo2,'center'])].isel(x = j,y = i).isnull()
                if all([condition1,condition2,condition3,condition4,condition5]):
                    #Avoid NaNs and non spaced indices
                    #For the first component WLs
                    ints[i,j,0] = simps(compo_1[self.idx_min_max_mat[i,j,0,0]:\
                        self.idx_min_max_mat[i,j,1,0]],\
                    Eloss[self.idx_min_max_mat[i,j,0,0]:self.idx_min_max_mat[i,j,1,0]])
                    #For the second component WL
                    ints[i,j,1] = simps(compo_2[self.idx_min_max_mat[i,j,0,1]:\
                        self.idx_min_max_mat[i,j,1,1]],\
                    Eloss[self.idx_min_max_mat[i,j,0,1]:self.idx_min_max_mat[i,j,1,1]])
                else:
                    ints[i,j,1] = np.nan
                    ints[i,j,0] = np.nan
                self.num_prog1+=1
        self.fwhm_run = False
        dataset_orig = xr.Dataset({'integrated_values':(['y','x','comp'],ints),\
            'EnergyLimits':(['y','x','lim','comp'],Ew_halfs)},\
        coords={'x':self.ds.x.values,'y':self.ds.y.values,\
            'comp':[compo1,compo2],'lim':['lower','upper']})
        #Now the ratio_data
        rats = dataset_orig.integrated_values.isel(comp = 1)/\
            dataset_orig.integrated_values.isel(comp = 0)
        rats_inv = dataset_orig.integrated_values.isel(comp = 0)/\
            dataset_orig.integrated_values.isel(comp = 1)
        mat_rat = np.zeros(rats.values.shape+self.ds.Eloss.shape)
        #mat_rat[:,:,:] = rats.values[:,:,None]
        mat_rat[:] = rats.values[:,None]
        mat_rat_i = np.zeros(rats_inv.values.shape+self.ds.Eloss.shape)
        #mat_rat_i[:,:,:] = rats_inv.values[:,:,None]
        mat_rat_i[:] = rats_inv.values[:,None]
        #Now we create the raios datasets
        ratios_ds = xr.Dataset({'Components_Ratios':(['y','x','Eloss'],mat_rat),\
            'Components_Inverted_Ratios':(['y','x','Eloss'],mat_rat_i)},\
        coords = {'x':self.ds.x.values,'y':self.ds.y.values,\
            'Eloss':self.ds.Eloss.values})
        '''
        ratios_ds = rats.to_dataset(name = 'Components_Ratios')
        ratios_ds_inv = rats_inv.to_dataset(name = 'Components_Inverted_Ratios')
        '''
        #self.dataset_auto = xr.merge([dataset_orig,ratios_ds,ratios_ds_inv])
        self.dataset_auto = xr.merge([dataset_orig,ratios_ds])
        mini = np.nanmin(self.dataset_auto['Components_Ratios'].values)
        maxi = np.nanmax(self.dataset_auto['Components_Ratios'].values)
        '''
        self.image_ratio_placement.object = hv.HeatMap(self.dataset_auto.Components_Ratios)\
            .opts(cmap = self.colormap_1,invert_yaxis = True,frame_height=325,\
                xaxis = None,yaxis = None,selection_fill_alpha = 1,\
                line_width = 0.75,line_color = 'grey',clipping_colors = {'NaN':'black'},\
                alpha = 1,hover_fill_alpha = 1, hover_line_color = 'limegreen',\
                tools = [self.hover_ratio],shared_axes = False,\
                colorbar = True,colorbar_position = 'bottom',clim = (mini,maxi))
        '''
        self.image_ratio_placement.object =\
        hv.Image(self.dataset_auto,kdims = ['Eloss','y'],\
            vdims = ['Components_Ratios'])\
        .opts(invert_yaxis = True,ylabel = 'Pixel #',\
            #xlabel ='Electron Energy Loss [eV]',\
            cmap = self.colormap_1,shared_axes = False,xaxis = None,\
            yaxis = True,yformatter = formatter_y_SL,\
            frame_height = 150,frame_width = 600,\
            alpha = 1,colorbar = True,\
            colorbar_position = 'bottom',clim = (mini,maxi),\
            colorbar_opts = self.colbaropts,toolbar = 'above',\
            tools = [self.hover_ratio],clipping_colors = {'NaN':'black'})
        self.fitting_in_place = True
        self.cbar_wid[1].disabled = False
        self.cmap_wid[1].disabled = False
        vari_mm = abs(maxi-mini)/10
        self.param['range_cmap1'].bounds = (mini-vari_mm,maxi+vari_mm) 
        self.range_cmap1 = (mini,maxi)
        self.ratio_on_display.object = '#### Ratio on display : {} / {}'\
        .format(self.dataset_auto.comp.values[1],self.dataset_auto.comp.values[0])
        self.dyn_windows = hv.DynamicMap(self.plot_int_windows_single,streams=[self.stream_tapping])
        self.button_show_windows[0].disabled = False
        self.button_change_DirectInverse.disabled = False
        self.button_change_DirectInverse.button_type = 'warning'
        self.button_launch_advanced_analyzer.button_type = 'default'
        self.button_launch_advanced_analyzer.disabled = True
    
    def get_keywords(self):
        lista_edges = []
        self.dictio_edges = dict()
        self.dictio_ELNES_limits = dict()
        for elm in self.elements_list:
            for var in self.ds.data_vars:
                #The best choice is to work with the given dateset,to avoid mistakes
                lista = var.split('_')
                if elm in lista[0] and 'cont' in lista:
                    nombre = ' '.join([elm,lista[0].split(elm)[1]])
                    if nombre not in lista_edges:
                        lista_edges.append(nombre)
                        self.dictio_edges[nombre] = []
        #We have to rerun again the whole set of components
        for clave in self.dictio_edges:
            ele,edg = clave.split(' ')
            lista_ssh = [''.join([list(edg)[0],sh]) for sh in list(edg)[1:]]
            for var in self.ds.data_vars:
                for ssh in lista_ssh:
                    if all([el in var for el in [ele,'component',ssh]]) and 'cont' not in var:
                        subshell_el = var.split('_')[0]
                        self.dictio_edges[clave].append(subshell_el)
        self.param['full_edge'].objects = list(self.dictio_edges)
        self.full_edge = self.param['full_edge'].objects[0]
        #And the final rerun over the already formed dictionary - 
        # to set up the limit parameters
        for edge in self.dictio_edges:
            self.dictio_ELNES_limits[edge] = dict()
            for sshell in self.dictio_edges[edge]:
                clave1 = ''.join([sshell,'_fwhm'])
                clave2 = ''.join([sshell,'_center'])
                fw_half = np.nanmedian(self.ds[clave1].values)/2
                cent_ini = np.nanmedian(self.ds[clave2].values)
                #This is the initial value given for the integration
                # for any given component.
                self.dictio_ELNES_limits[edge][sshell] =\
                [round(cent_ini-fw_half*2.5,2),round(cent_ini+fw_half*2.5,2)]
        #A default dictionary for recovery
        self.dictio_ELNES_lims_default = cp.deepcopy(self.dictio_ELNES_limits)
        
    def create_launch_layout(self):
        '''
        Some major changes are in place here with respect to the SI-layout,
        to accomodate the shapes of the spectrum lines
        '''
        self.dynamic_placement =\
            pn.pane.HoloViews(self.dynamic_tap.opts(shared_axes= False,framewise = True))
        self.image_placement   = pn.pane.HoloViews(self.im)
        self.image_ratio_placement = pn.pane.HoloViews(self.im_empty)
        '''
        self.scatter_analysis_placement = pn.pane.HoloViews(self.scatter_empty)
        sli_number = pn.Row(self.numb_markdown,self.slider_number_value,self.slider_number)
        '''
        self.ratio_on_display = pn.pane.Markdown('#### Ratio on display : None',\
            style = {'color':'lightgrey'},width = 200,margin = (0,35))
        butt_ons = pn.Column(self.button_show_cents,self.button_show_windows,\
            self.button_change_DirectInverse,\
            self.ratio_on_display,\
            self.cmap_wid,self.cbar_wid,\
            align = 'center',margin = 0,width = 325)
        
        self.graph_buttons = pn.Column(\
            pn.pane.Markdown('#### Controls for the graphs on display',\
                style = {'color':'white'},margin = (5,15,-10,15),width = 295),\
            pn.layout.Divider(height = 5,margin = (0,15,5,15)),\
            butt_ons,\
            height = 700,width = 325,background = 'grey',margin = 0)
        
        self.tab_controls_graph = pn.Tabs(('Controls',self.graph_buttons),('Info',self.info_panel),\
            tabs_location='above',width = 325,height = 705,margin = (10,0,0,0))
        '''
        self.tab_graphs = pn.Tabs(('Spectra Analysis',pn.Row(self.dynamic_placement)),\
            ('Multiplier/Ratio Analysis',pn.Row(self.scatter_analysis_placement)))
        
        first_row = pn.Row(pn.Tabs(('Image',self.image_placement),('Info',self.info_panel)),\
            self.tab_graphs)
        '''
        first_column = pn.Column(self.image_placement,self.dynamic_placement,\
            self.image_ratio_placement,width = 700)
        self.button_col = pn.Column(pn.Row(pn.pane.Markdown('### WL ratio analysis',\
                style ={'color':'white'},align = 'center',width = 150,\
                height = 40,margin = (0,0,0,15)),\
                self.button_include_cont,align = 'center',width = 380,height = 50,margin = 0),\
            pn.layout.Divider(height = 5,margin = (0,25,5,25)),\
            pn.pane.Markdown('#### Edge selector',\
                style ={'color':'white'},align = 'center',width = 350,\
                height = 25,margin = (0,25)),\
            self.edge_selection_widget,\
            pn.pane.Markdown('#### Integration mode selector and options',\
                style ={'color':'white'},align = 'center',width = 350,\
                height = 25,margin = (0,25)),\
            pn.layout.Divider(height = 5,margin = (5,25)),\
            self.mode_selector,self.width_selector,\
            self.component_to_int_selector,\
            self.width_manual_selector,\
            pn.Row(self.fixed_width_configurator,\
                self.fixed_width_compo_markdown,\
                width = 280,margin = (0,50),align = 'center'),\
            self.component_selector,self.width_compo_markdown,\
            pn.Row(self.button_reset_widths,self.E0_wid,self.E1_wid,\
                #self.width_compo_markdown,\
                width = 280,margin = (0,50),align = 'center'),\
            #This part is to be included anywhere but here...
            #pn.Row(self.numb_markdown,self.slider_number_value,\
            #    self.slider_number,width = 330,align = 'center',\
            #    margin = (0,35)),\
            self.select_computation_values_widget,\
            self.components_to_substraction,\
            pn.layout.Divider(height = 5,margin = (5,25)),\
            pn.Row(self.button_compute,self.button_show_computed_vals,align = 'center'),\
            self.progress_bar_advanced,\
            pn.Spacer(height = 9,margin = 0),\
            width = 400, background = 'grey')
        self.banner = pn.Spacer(width = 1100,height = 60, background='grey',margin = (0,0,14,0))
        self.fila_graph_butt = pn.Column(self.banner,\
            pn.Row(first_column,self.tab_controls_graph,width = 1100),\
            width = 1100)
        self.layout = pn.Row(self.fila_graph_butt,self.button_col)
import sys
import os
import json
import numpy as np
import copy as cp
import xarray as xr
import pandas as pd
from random import choice
#Visualization Libraries ---
import panel as pn
import holoviews as hv
# import hvplot.xarray
import bokeh, param
from holoviews import streams, opts, dim
#Clustering tools from sklearn ---
from sklearn.cluster import KMeans,AgglomerativeClustering, SpectralClustering
from sklearn.preprocessing import normalize
from sklearn.neighbors import kneighbors_graph
#Saving routines
from saving_routines import Saving_panel
#holoviews extensions

print('Importing - Clustering Analysis panels for Spectrum Images ')
hv.extension("bokeh",logo = False)


def formatter(value):
        #Method to format the yaxis format (Electron Counts)
        return '{: >12.2e}'.format(value)

def hook_padding_graphs(plot, element):
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

class plotting_cluster():
    def __init__(self, ds,lite = False,given_colors = []):
        '''
        plotting class will be expecting a ds, xarray dataset. If none
        is given, it won't be able to be initialized
        
        self.lite controls the visualization mode
        '''
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
        self.lite = lite
        cluster_number = self.ds['label_number'].values
        self.long =  len(cluster_number)
        #My default selected colors
        if given_colors == [] or given_colors == None:
            self.colores = ['navy','gold','deepskyblue','crimson','lawngreen',\
                            'orange','blueviolet','forestgreen','silver']
            #In case of having more clusters - random choice to fill list
            while self.long > len(self.colores):
                selection = choice(bokeh.colors.named.__all__)
                if selection not in self.colores:
                    #So we do not repeat colors
                    self.colores.append(selection)
                else: pass
        elif len(given_colors) < self.long:
            self.colores = cp.deepcopy(given_colors)
            while self.long > len(self.colores):
                selection = choice(bokeh.colors.named.__all__)
                if selection not in self.colores:
                    #So we do not repeat colors
                    self.colores.append(selection)
                else: pass
        else:
            self.colores = cp.deepcopy(given_colors)
        #These are the reference images.
        self.original_im = hv.Image(self.ds['ElectronCount'].sum(dim = 'Eloss'))\
            .opts(cmap = 'Greys_r',aspect='equal',invert_axes=True,invert_yaxis=True,\
            xlim = self.ylims,ylim = self.xlims,\
            frame_height = 275,shared_axes=False,hooks = [hook_padding_graphs],bgcolor = 'gainsboro')
        self.im = hv.Image(ds['labs'])\
            .opts(tools = ['hover'],cmap = self.colores[:self.long],framewise = True,\
                xlim = self.ylims,ylim = self.xlims,\
                invert_axes=True,invert_yaxis=True,shared_axes= False,\
                frame_height = 275,aspect='equal',xaxis = None,yaxis = None,\
                hooks = [hook_padding_graphs],bgcolor = 'gainsboro')
        self.mini_image = hv.Image(ds['labs'])\
            .opts(toolbar = None,cmap = self.colores[:self.long],framewise = True,\
                invert_axes=True,invert_yaxis=True,shared_axes= False,\
                xlim = self.ylims,ylim = self.xlims,\
                frame_height = 100,aspect='equal',xaxis = None,yaxis = None,border =0)
        '''
        self.point_graph = hv.Points(self.ds['labs'])\
            .opts({'Points':dict(cmap = self.colores[:self.long],\
            xlim = self.ylims,ylim = self.xlims,\
            tools = ['hover'],size = 10,\
            color = 'labs',alpha = 0.5)})
        self.point_graph\
            .opts(tools = ['hover'],invert_axes=True,invert_yaxis=True,\
                shared_axes= False,frame_height = 275,aspect='equal',\
                xaxis = None,yaxis = None,framewise = True,padding = 0)
        '''
        self.point_graph = hv.HeatMap(ds['labs'],kdims = ['x','y'])\
            .opts(cmap = self.colores[:self.long],\
            xlim = self.xlims,ylim = self.ylims,\
            tools = ['hover'],\
            color = 'labs',fill_alpha = 0.25,line_alpha = 1,\
            line_color = 'labs',invert_yaxis = True,\
            shared_axes= False,frame_height = 275,aspect='equal',\
            xaxis = None,yaxis = None,framewise = True,\
            hooks = [hook_padding_graphs],bgcolor = 'gainsboro')

        self.doble_tap_point = streams.DoubleTap(x = 0, y = 0, source = self.point_graph)
        self.doble_tap_image = streams.DoubleTap(x = 0, y = 0, source = self.im)
        #The are the down/upper limits for hovering (xi,xf,yi,yf) - a tuple
        self.hov_lims = (self.ds.x.data[0]-0.5,self.ds.x.data[-1]+0.5,self.ds.y.data[0]-0.5,self.ds.y.data[-1]+0.5)
        curve_dict = {f: hv.Curve(self.ds['ElectronCount_norm_Centroids'][f]).\
            opts(color = self.colores[i]) for i,f in enumerate(cluster_number)}
        kdimension = hv.Dimension(('cluster_number', 'Arbitrarly given cluster number'),default=0)
        self.hmap = hv.HoloMap(curve_dict, kdims=kdimension)\
            .opts(framewise=True,frame_height = 275,\
            shared_axes=False)
        self.empty_curve = hv.Area([])\
            .opts(frame_height = 275,framewise = True,\
            shared_axes=False,fill_alpha = 0.25,frame_width = 650,\
            yformatter = formatter,show_grid = True,xlabel='E-loss [eV]',\
            ylabel = 'Electron Counts [a.u]')

    def plot_curve(self,x,y):
        #Method in charge of plotting the spectrum when hovering over the image
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.empty_curve
        elif y >= yf or y <= yi:
            return self.empty_curve
        else:
            x0,y0 = self.im.closest((x,y))
            col = self.colores[int(self.ds['labs'].isel(x = int(x0),y = int(y0)).values)]
            curve = hv.Area(self.ds['Centroid_pixel'].isel(x = int(x0),y = int(y0)))\
            .opts(fill_color = col,line_color = col,\
            line_width = 2,line_alpha = 1,\
            yformatter=formatter,frame_height = 275,\
            framewise = True,shared_axes=False,fill_alpha = 0.25,frame_width = 650,\
            show_grid = True,xlabel='E-loss [eV]',ylabel = 'Electron Counts [a.u]')
            return curve    

    def _create_dynamic_maps(self):
        self.din = hv.DynamicMap(self.plot_curve,streams=[self.doble_tap_point])\
            .opts(hooks = [hook_padding_graphs],bgcolor = 'white')
        #self.din2 = hv.DynamicMap(self.plot_curve,streams=[self.doble_tap_image])
        self.over = self.hmap.overlay('cluster_number')\
        .opts(frame_height = 275,framewise = True,\
            legend_muted = True,show_grid = True,\
            xlabel='E-loss [eV]',ylabel = 'Electron Counts [a.u]',\
            frame_width = 650,shared_axes=False,yformatter = formatter,\
            hooks = [hook_padding_graphs],bgcolor = 'white',legend_cols = True)
    
class Make_clusters(param.Parameterized):
    trigger = param.Integer(default= 0,bounds = (0,None))
    trigger_im = param.Integer(default= 0,bounds = (0,None))
    ini = param.Integer(default= 0,bounds = (0,None))
    number_of_runs = param.Integer(default = 0, bounds = (0,None))
    number_saves = param.Integer(default = 0, bounds = (0,None))
    number_tap = param.Integer(default = 0, bounds = (0,None))
    change_colomap = param.Boolean(default = False)
    
    ''' ***** Parameters for clustering analyisis *****
                    Param_name           |   Name in sklearn call |
        -----------------------------------------------------------
        1.KMeans                                                  
            * num_cluster                |        n_cluster       |
            * initialization_iterations  |        n_init          |
            * maximum_iterations         |        max_iter        |
            * initialization_method      |        init            |
            
        2.Agglomerative Clustering     
            * num_cluster                |        n_cluster       |
            * affinity_agglomerative     |        affinity        |
            * linkage                    |        linkage         |
            * connectivity_matrix        |        connectivity    |
        
        3. Spectral Clustering
            * num_cluster                |        n_cluster       |
            * initialization_iterations  |        n_init          |
            * gamma                      |        gamma           |
            * affinity_spectral          |        affinity        |
            * number_of_neighbors        |        n_neighbors     |
            * assign_labels              |        assign_labels   |
            * Zero_coefficient           |        coef0           |
            * Polynomial_degree          |        degree          |
    '''
    
    num_cluster = param.Integer(default=0,bounds = (0,None))
    initialization_iterations = param.Integer(default=10,bounds = (1,100))
    maximum_iterations = param.Integer(default=200,bounds = (100,5000))
    initialization_method = param.ObjectSelector(default = 'k-means++',objects=['k-means++','random'])
    gamma = param.Number(default=1.0,softbounds=(0,9),bounds=(0,None),step = 0.05)
    assign_labels = param.ObjectSelector(default = 'kmeans',objects=['kmeans','discretize'])
    affinity_spectral = param.ObjectSelector(default = 'nearest_neighbors',\
                                            objects=['rbf','nearest_neighbors',\
                                            #'precomputed','precomputed_nearest_neighbors',
                                            #'poly','sigmoid','laplacian',
                                            #'additive_chi2','chi2',
                                            ])
    linkage = param.ObjectSelector(default='ward',objects=['ward','complete','average','single'])
    affinity_agglomerative = param.ObjectSelector(default='euclidean',objects=['euclidean'])  #,'l1','l2'
    connectivity_matrix =param.Boolean(default=False)
    connectivity_on_normalized = param.Boolean(default = False)
    number_of_neighbors_agg = param.Integer(default=10,bounds = (0,100))
    number_of_neighbors_spec = param.Integer(default=10,bounds = (0,100),precedence = 20)
    zero_coefficient = param.Number(default=1.0,step = 0.1,precedence = -1)
    polynomial_degree = param.Integer(default=3,bounds = (0,5),precedence = -1)
    ''' ***** Parameters for prenormalization *****
    *Pre-normalization decides if a normalization is conducted in the data prior to clustering separation
    *Available norms decide the norm to be applied
    '''
    prenormalization = param.Boolean(default=False)
    available_norms = param.ObjectSelector(default = 'l2',objects = ['l1','l2','max'])
    '''***** Extra options for representation *****
    Toggle point-graph representation or normal hmap rep
    Toggle Overlay Curves representation or dinamic map of areas 
    '''
    point_graph_active  = param.Boolean(default=True)
    dynamic_curves_repr = param.Boolean(default=True)
    point_size = param.Integer(default = 10,bounds = (1,25),step = 1)
    data_frame_info = param.DataFrame()
    runs_selection = param.ObjectSelector(default = 'Run-1',objects=['Run-1'])
    saving_name = param.String()
    saving_folder = param.String('./clustering_saves')
    current_visal = param.String(default='None')

    def __init__(self,ds):
        super().__init__()
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
        ###########################################################################################
        self.im = hv.Image(self.ds.sum(dim = 'Eloss'),kdims =['x','y'])\
            .opts(cmap = 'Greys_r',aspect='equal',\
            invert_yaxis=True,frame_height  = 275,shared_axes=False,\
            xlim = self.xlims,ylim = self.ylims,\
            toolbar = 'right',xaxis = None,yaxis = None,\
            hooks = [hook_padding_graphs],bgcolor = 'gainsboro')
        self.button_cluster = pn.widgets.Button(name='Go Clustering!',\
            disabled=True,button_type='default',width_policy = 'fit',height = 45,margin = (5,5))
        self.button_cluster.on_click(self._callback_button_cluster)
        self.button_store = pn.widgets.Button(name = 'Store run',\
            disabled=True,button_type='default',width_policy = 'fit',height = 45,margin = (5,5))
        self.button_store.on_click(self._callback_button_store)
        self.button_save = pn.widgets.Button(name = 'Save Run',\
            disabled=True,button_type='default',width = 115,height = 30,\
            margin = 0,align = 'center')
        self.button_save.on_click(self._callback_button_save)
        self.button_save_data = pn.widgets.Button(name = 'Save Data',\
            disabled=True,button_type='default',width = 115,height = 30,\
            margin = 0,align = 'center')
        self.button_save_data.on_click(self._callback_button_save_data)
        self.button_show_results = pn.widgets.Button(name = 'Show Selection',\
            disabled = True, button_type = 'default',width = 115,height = 80,margin = 0)
        self.button_show_results.align = 'center'
        self.button_show_results.on_click(self._callback_show_clusters)
        self.button_change_cmap = pn.Param(self.param['change_colomap'],\
            widgets = {'change_colomap':pn.widgets.Toggle},parameters = ['change_colomap'],\
            width = 100,show_labels = False,show_name = False)
        self.button_change_cmap[0].name = 'Color'
        self.button_change_cmap[0].width = 90
        self.button_change_cmap[0].height = 30
        self.button_change_cmap[0].button_type = 'primary'
        self.button_change_cmap.margin = 5
        '''
        self.button_type_graph = pn.Param(self.param['point_graph_active'],\
            widgets = {'point_graph_active':pn.widgets.Toggle},show_labels = False,\
            parameters = ['point_graph_active'],show_name = False,\
            width = 150,height = 35)
        self.type_graph = 'PointGraph'
        self.button_type_graph[0].button_type = 'success'
        self.button_type_graph[0].name = self.type_graph
        self.button_type_graph[0].disabled = True
        self.button_type_graph[0].align = 'center'
        self.button_type_graph[0].height = 35
        '''
        self.button_type_curve = pn.Param(self.param['dynamic_curves_repr'],\
            widgets = {'dynamic_curves_repr':pn.widgets.Toggle},show_labels = False,\
            parameters = ['dynamic_curves_repr'],show_name = False,\
            width = 300,height = 35,align = 'end')
        self.button_type_curve[0].button_type = 'success'
        self.button_type_curve[0].name = 'Selected-cluster'
        self.button_type_curve[0].disabled = True
        self.button_type_curve[0].align = 'end'
        self.button_type_curve[0].height = 35
        '''
        self.type_curve = 'DynamicGraph'
        self.button_type_curve[0].button_type = 'success'
        self.button_type_curve[0].name = self.type_curve
        self.button_type_curve[0].disabled = True
        self.button_type_curve[0].align = 'center'
        self.button_type_curve[0].height = 35
        '''
        #Point size widget
        self.param['point_size'].label = 'Point size(graph)'
        '''
        self.point_size_wid = pn.Param(self.param['point_size'],\
            widgets = {'point_size':pn.widgets.IntSlider},\
            parameters = ['point_size'],width = 150,show_name = False,\
            show_labels = True)
        self.point_size_wid[0].disabled = True
        '''
        '''
        self.button_change_point_size = pn.widgets.Button(name='Update',\
            width = 75,height = 35,align = 'center')
        self.button_change_point_size.disabled = True
        self.button_change_point_size.on_click(self._callback_change_size_now)
        '''
        #The Empty data structures
        zero_data = np.zeros_like(self.ds.ElectronCount.values)
        self.ds_zero = xr.Dataset({'ElectronCount':(['y','x','Eloss'],zero_data)},\
            coords={'x':ds.x.values,'y':ds.y.values,'Eloss':ds.Eloss.values})
        self.im_default = hv.Image(self.ds_zero.sum('Eloss'),kdims = ['x','y'])\
            .opts(cmap = 'Greys_r',aspect='equal',invert_yaxis=True,\
            xlim = self.xlims,ylim = self.ylims,\
            frame_height = 275,shared_axes=False,xaxis = None,yaxis = None,\
            hooks = [hook_padding_graphs],bgcolor = 'gainsboro')
        self.mini_image_default = hv.Image(self.ds_zero.sum('Eloss'),kdims = ['x','y'])\
            .opts(cmap ='Greys',toolbar = None,aspect='equal',invert_yaxis=True,\
            xlim = self.xlims,ylim = self.ylims,\
            frame_height = 100,shared_axes=False,xaxis = None,yaxis = None,border = 0)
        self.curve_default = hv.Area(self.ds_zero.sum(['x','y']))\
            .opts(frame_height = 275,frame_width=650,xlabel='E-loss [eV]',\
            ylabel = 'Electron Counts [a.u]',shared_axes = False,\
            yformatter=formatter,show_grid = True,\
            hooks = [hook_padding_graphs],bgcolor = 'white')
        self.number_of_runs = 0
        self.saves = dict()
        lista_claves = ['Algorithm','Clusters-number','Normalized-Data','Norm','Extra-info']
        dictio_for_df = dict()
        for clav in lista_claves:
            #initialize to empty info dictionary
            dictio_for_df[clav] = ' - '
        df_initial = pd.DataFrame(dictio_for_df,index = ['NoRun'])
        self.df_widgets = pn.pane.DataFrame(df_initial,height = 100,width = 500,margin = (0,5))
        self.df_widgets.background = 'gainsboro'
        self.savname_wid = pn.Param(self.param['saving_name'],\
            widgets = {'saving_name':pn.widgets.TextInput},\
            parameters = ['saving_name'],name = 'SavingFile-Name',show_name = False,\
            show_labels = False,width = 500,margin = 0)
        self.savname_wid[0].placeholder = 'Enter File name for data saves'
        self.savfold_wid = pn.Param(self.param['saving_folder'],\
            widgets = {'saving_folder':pn.widgets.TextInput},\
            parameters = ['saving_folder'],name = 'SavingFolder-Name',show_name = False,\
            show_labels = False,width = 500,margin = 0)
        self.savfold_wid[0].placeholder =\
            'Enter folder address (global or relative to current directory) for data saves'
        #Now some initial values for the name
        try:
            identifier = self.ds.attrs['original_name'].split('\\')[-1].split('.')[0]
            self.saving_name = identifier
        except:
            #In case of not having a name in place....do nothing
            pass
        #Configuration of the SI on display visualization
        self.hmap_interactivo = hv.HeatMap(self.ds.sum(dim = 'Eloss'),kdims =['x','y'])\
            .opts(cmap = 'Greys_r',aspect='equal',\
            invert_yaxis=True,frame_height  = 275,shared_axes=False,\
            xlim = self.xlims,ylim = self.ylims,\
            toolbar = 'right',xaxis = None,yaxis = None,\
            tools = ['hover','tap'],line_alpha = 0.15,\
            line_width = (275 /ysize /10),hover_line_color = 'limegreen',\
            selection_line_color = 'red',nonselection_alpha = 0.5,selection_alpha = 1,\
            nonselection_line_alpha = 0.15,\
            hooks = [hook_padding_graphs],bgcolor = 'gainsboro')
        self.hmap_placeholder = pn.pane.HoloViews(self.hmap_interactivo,margin = (5,15))
        self.im = hv.Image(self.ds.sum(dim = 'Eloss'),kdims =['x','y'])\
            .opts(cmap = 'Greys_r',aspect='equal',\
            invert_yaxis=True,frame_height  = 275,shared_axes=False,\
            xlim = self.xlims,ylim = self.ylims,\
            toolbar = 'right',xaxis = None,yaxis = None)
        self.hov_lims = (self.ds.x.data[0]-0.5,self.ds.x.data[-1]+0.5,\
            self.ds.y.data[0]-0.5,self.ds.y.data[-1]+0.5)
        self.click_image = streams.Tap(x = -1, y = -1, source = self.hmap_interactivo)
        self.dynamic_curve = hv.DynamicMap(self.plot_pixel_spectrum,streams=[self.click_image])\
            .opts(framewise = True,shared_axes=False,show_grid = True,\
            hooks = [hook_padding_graphs],bgcolor = 'white')

    @param.depends('change_colomap',watch = True)
    def _change_cmap(self):
        """Interactive method - updates the color map of the EELS SI
        It is controlled by self.button_change_cmap 
        """
        if self.change_colomap:
            self.button_change_cmap[0].name = 'Greys'
            self.button_change_cmap[0].button_type = 'default'
            self.hmap_placeholder.object =\
                self.hmap_interactivo.opts(cmap = 'RdYlBu_r')
        else:
            self.button_change_cmap[0].name = 'Color'
            self.button_change_cmap[0].button_type = 'primary'
            self.hmap_placeholder.object =\
                self.hmap_interactivo.opts(cmap = 'Greys_r')

    def plot_pixel_spectrum(self,x,y):
        """PLotting function for the curve displayed when
        clicking on the heatmap for the EELS SI

        Args:
            x (float/int): x coordinate
            y (float/int): y coordinate

        Returns:
            holoviews/bokeh object - Area: Area for the spectra of the
            pixel clicked in the heatmap, with coordinates (x,y) 
        """
        xi,xf,yi,yf = self.hov_lims
        if x >= xf or x <= xi:
            return self.curve_default
        elif y >= yf or y <= yi:
            return self.curve_default
        else:
            x0,y0 = self.im.closest((x,y))
            curve = hv.Area(self.ds['ElectronCount'].isel(x = int(x0),y = int(y0)))\
            .opts(yformatter=formatter,frame_height = 275,frame_width=650,\
                xlabel='E-loss [eV]',ylabel = 'Electron Counts [a.u]',\
                shared_axes = False,\
                fill_color = 'red',fill_alpha = 0.5,line_alpha = 0,\
                show_grid = True,framewise = True,\
                hooks = [hook_padding_graphs],bgcolor = 'white')
            return curve    


    def _carry_on_clustering(self):
        #Let's create the name keys we need to identfy each run
        name_keys = []
        #Method that calls the corresponding clustering algorithms
        #We create this wraps around the clustering functions
        km    = lambda n_clust,**kwargs : KMeans(n_clust,**kwargs)
        agg   = lambda n_clust,**kwargs : AgglomerativeClustering(n_clust,**kwargs)
        spect = lambda n_clust,**kwargs : SpectralClustering(n_clust,**kwargs)
        data = self.ds.ElectronCount.values
        shap = data.shape
        data_flat = data.reshape(shap[0]*shap[1],shap[-1])
        if self.prenormalization:
            data_flat = normalize(data_flat,norm = self.available_norms)
            name_keys.append('[{} norm]'.format(self.available_norms))
            type_normalization = str(self.available_norms)
            normalization_done = str(self.prenormalization)
        else: 
            name_keys.append('[Not-norm]')
            type_normalization = ' - '
            normalization_done = str(self.prenormalization)
        #Now, the algorithm Selection
        if self.cluster_tab.active == 1:
            #Case of Agglomerative clustering
            algo_choice = 'Agglomerative'
            #Various cases are avalable - related with connectivity matrices mainly
            name_keys.insert(0,'Agg.Clust. n = {}'.format(self.num_cluster))
            if self.connectivity_matrix:
                #Let's decide how to get the connectivity going
                if self.connectivity_on_normalized:
                    connect = kneighbors_graph(data_flat,\
                        n_neighbors=self.number_of_neighbors_agg,\
                        include_self=False)
                    extra_data = 'Connectivity and Normalized'
                else:
                    connect = kneighbors_graph(data.reshape(shap[0]*shap[1],shap[-1]),\
                        n_neighbors=self.number_of_neighbors_agg,\
                        include_self=False)
                    extra_data = 'Connectivity Not Normalized'   
                algorithm = agg(self.num_cluster,\
                    affinity = self.affinity_agglomerative,\
                    linkage = self.linkage,connectivity = connect)
                name_keys.insert(1,'Connect.Mat.')
            else:
                algorithm = agg(self.num_cluster,\
                    affinity = self.affinity_agglomerative,\
                    linkage = self.linkage)
                extra_data = ' - '
        elif self.cluster_tab.active ==2:
            #Case of spectral clustering
            algo_choice = 'Spectral'
            if self.affinity_spectral == 'nearest_neighbors':
                extra_data = '{}Nearest Neighbors'.format(str(self.number_of_neighbors_spec))
            elif self.affinity_spectral == 'rbf':
                extra_data = 'RBF {}Gamma'.format(str(round(self.gamma,2)))
            else:
                extra_data = ' - '
            algorithm = spect(self.num_cluster,n_init = self.initialization_iterations,\
                gamma = self.gamma,affinity = self.affinity_spectral,\
                n_neighbors = self.number_of_neighbors_spec,\
                assign_labels = self.assign_labels,\
                degree = self.polynomial_degree,\
                coef0 = self.zero_coefficient, n_jobs = -1)
            name_keys.insert(0,'Spect.Clust. n = {}'.format(self.num_cluster))
        else:
            #Case of Kmeans - is the default case-scenario
            algo_choice = 'KMeans'
            extra_data = 'Init {}'.format(str(self.initialization_method))
            algorithm = km(self.num_cluster,n_init = self.initialization_iterations,\
                max_iter = self.maximum_iterations,init = self.initialization_method)
            name_keys.insert(0,'KMeans.Clust. n = {}'.format(self.num_cluster))
        ########
        self.clustered = algorithm.fit(data_flat)
        atts = self.clustered.get_params()
        self.label_map = self.clustered.labels_.reshape(shap[0],shap[1])
        try:
            self.centroides = self.clustered.cluster_centers_
        except:
            #In case of not having the method of extraction
            self.centroides = np.zeros((self.num_cluster,shap[-1]))
        #Now we need the objects to be plotted
        Eloss = self.ds.Eloss.values
        mat_cents = np.zeros(shap)                        #mapping with the centroids per image/pixel
        cents = np.zeros((self.num_cluster,shap[-1]))     #centroids signals
        cents_2 = np.zeros((self.num_cluster,shap[-1]))
        for i in range(self.num_cluster):
            '''
            mat_cents[self.label_map == i] = data[self.label_map == i].mean(axis = (0))
            cents[i,:] = data[self.label_map == i].mean(axis = (0))
            cents_2[i,:] = self.centroides[i,:]
            '''
            mediana_data = np.median(data[self.label_map == i],axis = (0))
            mat_cents[self.label_map == i] = mediana_data
            cents[i,:] = mediana_data
            cents_2[i,:] = self.centroides[i,:]
        #Remember - We have inverted the 'natural axes' - We are dealing with images
        xs = np.arange(0,shap[1])
        ys = np.arange(0,shap[0])
        lab_numer = [i for i in range(self.num_cluster)]
        self.ds_ext = xr.Dataset({'ElectronCount':(['y','x','Eloss'],data),\
            'labs':(['y','x'],self.label_map.reshape(shap[:-1])),\
            'Centroid_pixel':(['y','x','Eloss'],mat_cents),\
            'ElectronCount_norm_Centroids':(['label_number','Eloss'],cents),\
            'Centroids':(['label_number','Eloss'],cents_2)},\
        coords= {'Eloss' : Eloss,  'y' : ys,\
            'x' : xs, 'label_number' : lab_numer},\
        attrs = {'Clustering_params' : atts,\
            'name' : '\n'.join(name_keys),\
            'Run number' : self.number_of_runs + 1,\
            'original_name' : self.ds.attrs['original_name']})
        self.lista_for_df = [algo_choice,self.num_cluster,\
            normalization_done,type_normalization,extra_data]
        #Now creating the clustering displays
        self.pt = plotting_cluster(self.ds_ext)
        self.pt._create_dynamic_maps()
        self.button_show_results.disabled = False
        self.button_show_results.button_type = 'primary'
        #Now let's visualize the results
        #self.button_type_graph[0].disabled = False
        self.button_type_curve[0].disabled = False
        '''
        self.image_column[2][0].pop(0)
        self.image_column[2][0].append(self.pt.point_graph)
        '''
        self.cluster_im_placeholder.object = self.pt.point_graph
        '''
        self.image_column[2][1].pop(0)
        self.image_column[2][1].append(self.pt.din)
        '''
        self.curves_placeholder.object = self.dynamic_curve*self.pt.din
        #self.point_size_wid[0].disabled = False
        '''
        self.button_change_point_size.disabled = False
        self.button_change_point_size.button_type = 'primary'
        '''
    #Control of options in clustering setup
    ###############################################################
    #Responsive methods for the widgets and parameters changer
    #Agglomerative_clustering
    '''
    @param.depends('point_size',watch = True)
    def _change_points_size(self):
        #Method to change points size after creation in the pointgraph
        self.pt.point_graph.opts({'Points':dict(cmap = self.pt.colores[:self.pt.long],\
                tools = ['hover'],size = self.point_size,\
                color = 'labs',alpha = 0.5)})
        #It will still require to update the graph
    '''
    '''
    @param.depends('point_graph_active',watch = True)
    def _change_button_style_1(self):
        #change button style for representation
        if self.point_graph_active:
            self.type_graph = 'PointGraph'
            self.button_type_graph[0].button_type = 'success'
            self.button_type_graph[0].name = self.type_graph
            self.image_column[2][0].pop(0)
            self.image_column[2][0].append(self.pt.point_graph)
            if self.dynamic_curves_repr:
                self.image_column[2][1].pop(0)
                self.image_column[2][1].append(self.pt.din)
            else: pass
        else:
            self.type_graph = 'LabelGraph'
            self.button_type_graph[0].button_type = 'warning'
            self.button_type_graph[0].name = self.type_graph
            self.image_column[2][0].pop(0)
            self.image_column[2][0].append(self.pt.im)
            if self.dynamic_curves_repr:
                self.image_column[2][1].pop(0)
                self.image_column[2][1].append(self.pt.din2)
            else: pass
    '''

    @param.depends('dynamic_curves_repr',watch = True)
    def _change_graph_displayed(self):
        if self.dynamic_curves_repr:
            '''
            self.type_curve = 'DynamicGraph'
            self.button_type_curve[0].button_type = 'success'
            self.button_type_curve[0].name = self.type_curve
            self.image_column[2][1].pop(0)
            if self.point_graph_active:
                self.image_column[2][1].append(self.pt.din)
            else:
                self.image_column[2][1].append(self.pt.din2)
            '''
            self.button_type_curve[0].button_type = 'success'
            self.button_type_curve[0].name = 'Selected-Cluster'
            self.curves_placeholder.object = self.dynamic_curve*self.pt.din
        else:
            #self.type_curve = 'OverlayGraph'
            self.button_type_curve[0].button_type = 'warning'
            self.button_type_curve[0].name = 'Show-All-Clusters'
            self.curves_placeholder.object = self.dynamic_curve*self.pt.over
            '''
            self.image_column[2][1].pop(0)
            self.image_column[2][1].append(self.pt.over)
            '''

    @param.depends('linkage',watch = True)
    def _control_of_affinity_agglomerative_1(self):
        #This method controls that whenever we have linkage == 'ward', we only have affinity euclidean
        if self.linkage == 'ward':
            self.param['affinity_agglomerative'].objects = ['euclidean']
            self.affinity_agglomerative = 'euclidean'
        else:
            self.param['affinity_agglomerative'].objects = ['euclidean','l1','l2']
            self.affinity_agglomerative = 'euclidean'
    
    @param.depends('prenormalization',watch = True)
    def _change_button_color(self):
        if self.prenormalization:
            self.prenorm_button[0].button_type = 'success'
            self.prenorm_button[0].name = 'On'
            self.available_norms_wid[1].disabled = False
        else:
            self.prenorm_button[0].button_type = 'danger'
            self.prenorm_button[0].name = 'Off'
            self.available_norms_wid[1].disabled = True

    @param.depends('connectivity_matrix','prenormalization',watch = True)
    def _control_of_prenormalize_connectivity_matrix_calculation(self):
        if self.connectivity_matrix and self.prenormalization:
            self.connectivity_normalized_wid[0].disabled = False
        else:
            self.connectivity_on_normalized = False
            self.connectivity_normalized_wid[0].disabled = True
    
    @param.depends('connectivity_matrix',watch = True)
    def _control_of_neighbors_num_for_connectivity_agglomerative(self):
        if self.connectivity_matrix:
            self.connectivity_matrix_wid[0].button_type = 'success'
            self.connectivity_matrix_wid[0].name = 'Connectivity  On'
            self.number_neighborgs_wid[1].disabled = False
        else:
            self.connectivity_matrix_wid[0].button_type = 'danger'
            self.connectivity_matrix_wid[0].name = 'Connectivity Off'
            self.number_neighborgs_wid[1].disabled = True
            self.number_of_neighbors_agg = self.param['number_of_neighbors_agg'].default
    
    @param.depends('connectivity_on_normalized',watch = True)
    def _change_connectivity_matrix_norm_button(self):
        if self.connectivity_on_normalized:
            self.connectivity_normalized_wid[0].button_type = 'success'
            self.connectivity_normalized_wid[0].name = 'Norm-Matrix  On'
        else:
            self.connectivity_normalized_wid[0].button_type = 'danger'
            self.connectivity_normalized_wid[0].name = 'Norm-Matrix Off'
    
    @param.depends('affinity_spectral',watch = True)
    def _control_of_sepectral_affinity_kernel_parameters(self):
        if self.affinity_spectral == 'rbf':
            self.gamma_wid[1].disabled = False
            self.number_Sneighs_wid[1].disabled = True
        elif self.affinity_spectral == 'nearest_neighbors':
            self.gamma_wid[1].disabled = True
            self.number_Sneighs_wid[1].disabled = False
        else:
            self.gamma_wid[1].disabled = True
            self.number_Sneighs_wid[1].disabled = True
    
    @param.depends('num_cluster',watch = True)
    def _button_control(self):
        #Controlling the ability of performing clustering runs 
        if self.num_cluster > 0:
            #We initialize the object
            self.button_cluster.disabled = False
            self.button_cluster.button_type = 'success'
        else:
            self.button_cluster.disabled = True
            self.button_cluster.button_type = 'default'
    
    @param.depends('saving_name',watch = True)
    def allow_saving(self):
        if self.number_of_runs <= 0:
            #Do not allow saving unless we have actual runs
            return
        if self.saving_name != '': 
            self.button_save.disabled = False #We now allow global saving
            self.button_save.button_type = 'danger'
        else:
            #Do not allow savings unless we have a file name in place
            self.button_save.disabled = True
            self.button_save.button_type = 'default'

    #Callback methods - those that actually make the buttons works
    '''
    def _callback_change_size_now(self,event):
        #Just changes the graph
        if self.point_graph_active:
            self.image_column[2][0].pop(0)
            self.image_column[2][0].append(self.pt.point_graph)
        else: pass
    '''

    def _callback_show_clusters(self,event):
        #Method that controls the showing of the clustering results
        #Ass soon as we click it, it is disconected
        self.dynamic_curves_repr = True
        self.button_show_results.disabled = True
        self.button_show_results.button_type = 'default'
        #NOw the juicy part ... getting it to display the run selected below
        self.ds_ext = self.saves[self.runs_selection]['loading_info']['data']
        self.pt = plotting_cluster(ds = self.ds_ext,given_colors = self.saves[self.runs_selection]\
            ['loading_info']['colors'])
        self.pt._create_dynamic_maps()
        #Now all the possible options for
        self.cluster_im_placeholder.object = self.pt.point_graph
        self.curves_placeholder.object = self.dynamic_curve*self.pt.din
        '''
        self.image_column[2][0].pop(0)
        self.image_column[2][1].pop(0)
        if self.point_graph_active:
            self.image_column[2][0].append(self.pt.point_graph)
        else:
            self.image_column[2][0].append(self.pt.point_graph)
        if self.dynamic_curves_repr:
            if self.point_graph_active:
                self.image_column[2][1].append(self.pt.din)
            else:
                self.image_column[2][1].append(self.pt.din2)
        else:
            self.image_column[2][1].append(self.pt.over)
        '''

        self.mkdown_run.object = '### None'
        self.mkdown_run.style = {'color':'darkgrey'}
        
        self.mkdown_results.object = '### {}'.format(self.runs_selection)
        self.mkdown_results.style = {'color':'dodgerblue'}
        
    def _callback_button_cluster(self, event):
        try:
            self.dynamic_curves_repr = True
        except: pass
        self.button_cluster.disabled = True
        self.button_cluster.name = 'Running'
        self.button_cluster.button_type = 'warning'
        self._carry_on_clustering()
        self.button_cluster.name = 'Go Clustering!'
        self.button_cluster.disabled = False
        self.button_cluster.button_type = 'success'
        self.button_cluster.disabled = False
        self.button_store.disabled = False
        self.button_store.button_type = 'primary'
        #changing visual aspects
        self.mkdown_run.object = '### NOT STORED'
        self.mkdown_run.style = {'color':'red'}

        self.mkdown_results.object = '### Current Run'
        self.mkdown_results.style = {'color':'limegreen'}
        self.button_save_data.disabled = False
        self.button_save_data.button_type = 'warning'

    def _callback_button_store(self,event):
        self.number_of_runs +=1
        self.run_buttons_widgets[0].disabled = False
        clave = '-'.join(['Run',str(self.number_of_runs)])
        self.saves[clave] = dict()
        lista_claves = ['Algorithm','Clusters-number','Normalized-Data','Norm','Extra-info']
        self.saves[clave]['dataframe'] =\
            pd.DataFrame(dict([pair for pair in zip(lista_claves,self.lista_for_df)]),\
            index = [clave])
        nombre = self.ds_ext.attrs['name']
        key_list = ['name','data','colors','caption']
        lista = [nombre,cp.deepcopy(self.ds_ext),\
            cp.deepcopy(self.pt.colores),self.pt.mini_image]
        self.saves[clave]['loading_info'] =\
            dict([pair for pair in zip(key_list,lista)])
        #Now changing the visulaization in the corresponding windows
        if self.number_of_runs == 1:
            #print('#1st run')
            #Force the mincaption and dataframe
            self.cluster_layout[1][0][1][3][0].pop(0)
            ima = self.saves[self.runs_selection]['loading_info']['caption'] 
            self.cluster_layout[1][0][1][3][0].append(ima)
            self.df_widgets[0].object = self.saves[self.runs_selection]['dataframe']
        else:
            #print('exapanding #runs')
            objet = cp.deepcopy(list(self.param['runs_selection'].objects))
            objet.append(clave)
            self.param['runs_selection'].objects = objet
        self.button_store.disabled = True
        self.button_store.button_type = 'default'
        #changing visual qeues
        self.mkdown_run.object = '### STORED'
        self.mkdown_run.style = {'color':'limegreen'}
        #Now, to allow the global saving if we have an actual name 
        if self.saving_name != '': 
            self.button_save.disabled = False #We now allow global saving
            self.button_save.button_type = 'danger'
        else:
            pass

    @param.depends('runs_selection',watch = True)
    def _change_visualization_runs(self):
        try:
            self.df_widgets[0].object = self.saves[self.runs_selection]['dataframe']
            self.cluster_layout[1][0][1][3][0].pop(0)
            ima = self.saves[self.runs_selection]['loading_info']['caption'] 
            self.cluster_layout[1][0][1][3][0].append(ima)
            self.button_show_results.disabled = False
            self.button_show_results.button_type = 'primary'
        except:
            pass

    def _callback_button_save_data(self,event):
        #Let's pass the information available and the images
        #This is only available when an actual result is displayed
        #Thus ... we may call it any number of times
        list_of_images = [hv.HeatMap.clone(self.pt.point_graph,link=False),]
        list_of_names = ['LabelMap',]
        #Individual clusters
        for l in self.ds_ext.label_number.values:
            tup_idx = np.where(self.ds_ext.labs.values == l)
            list_of_images.append(self.pt.plot_curve(tup_idx[1][0],tup_idx[0][0]))
            list_of_names.append('Cluster {}'.format(l))
        #Now the overlay
        list_of_images.append(\
            hv.NdOverlay(self.pt.hmap)\
            .opts(frame_height = 300,frame_width = 650,legend_cols = True,\
            show_grid = True,ylabel = 'Electron Counts [a.u.]',xlabel = 'E-Loss [eV]'))
        list_of_names.append('Centroids_overlay')
        #And now, the data
        self.sv = Saving_panel(self.ds_ext,figures = list_of_images,\
            figures_names = list_of_names,name_panel='clustering')
        self.sv.create_layout()
        

    def _callback_button_save(self,event):
        #To save, several options are in place
        #First- let's add a simple identifier to the end of the given name
        self.button_save.disabled = True
        self.button_save.name = 'Saving'
        self.button_save.button_type = 'warning'
        lista = [str(self.saves[self.runs_selection]['dataframe'][el][self.runs_selection])\
            if str(self.saves[self.runs_selection]['dataframe'][el][self.runs_selection]) != ' - '\
            else 'NoNorm' for el in ['Algorithm','Clusters-number','Norm']]
        extra_identifier = '-'.join(lista)
        #Let's check if the current name already exists
        fname = '_'.join([self.saving_name,extra_identifier])
        try:
            #In case of existing the directory filed,
            #let's check that there are not exactly identical names inside
            if fname in os.listdir(self.saving_folder):
                num = 1
                while True:
                    #To have and endeless loop to allow savings
                    gname = '_'.join([fname,str(num)])
                    if gname in os.listdir(self.saving_folder):
                        num += 1
                    else:
                        fname = gname
                        break
        except:
            #We wrap this in a try except, to avoid problems if th directory is new
            pass
        #Now we have to modify the attrs of ds, so we can actually store it
        dss = cp.deepcopy(self.saves[self.runs_selection]['loading_info']['data'])
        orig = self.ds.attrs['original_name']
        algo_paras = [(el,dss.attrs['Clustering_params'][el])\
            for el in dss.attrs['Clustering_params']]
        algo = self.saves[self.runs_selection]['dataframe']\
            ['Algorithm'][self.runs_selection]
        attrs = dict([('Original_name',orig),('Algorithm',algo),('Parameters',algo_paras)])
        dss.attrs = list()
        #One las modification
        dirname = '/'.join(self.saving_folder.split(r'\\')) #Just to have a common format
        save_place = '/'.join([dirname,'{}.nc'.format(fname)])
        save_dict = '/'.join([dirname,'{}.json'.format(fname)])
        #dss.to_zarr(store = save_place)
        try:
            dss.to_netcdf(path = save_place)
            with open(save_dict,'w') as f:
                json.dump(attrs,f)
        except Exception as e:
            print(e)
        finally:
            self.button_save.disabled = False
            self.button_save.name = 'Save Run'
            self.button_save.button_type = 'danger'
        #We also neet to ssave teh attrs, for later use
        
        #Let's save them as netcdf objects, to be read later in the model constructor
        

        

    def _default_view(self):
        #default_cluster_im = self.im_dafault
        default_grid = pn.GridSpec(margin=(10,10),height_policy='fit',\
            width_policy='fit',min_height=250,min_width = 250)
        default_grid[0,0] = self.im_default
        default_grid[0,1:4] = hv.Curve([])\
            .opts(framewise=True,shared_axes=False)
        default_grid[1,:4] = hv.Curve([])\
            .opts(framewise=True,shared_axes=False)
        return default_grid
    
    def create_panel(self):
        #Wiget box construction for the different algorithms avaliable
        self.run_buttons_widgets = pn.Param(self.param['runs_selection'],\
            widgets = {'runs_selection':pn.widgets.Select},\
            parameters = ['runs_selection'],show_labels = False,\
            height = 35,align = 'center',show_name = False)
        self.run_buttons_widgets[0].disabled = True
        self.run_buttons_widgets[0].align = 'center'
        #Kmeans Clustering
        num_clust_wid = pn.Param(self.param['num_cluster'],\
            widgets = {'num_cluster' : pn.widgets.Spinner},\
            parameters = ['num_cluster'],\
            width = 300,show_labels = False,\
            show_name = True,name = 'Number of clusters')
        init_iter_wid = pn.Param(self.param['initialization_iterations'],\
            widgets = {'initialization_iterations' : pn.widgets.Spinner},\
            parameters = ['initialization_iterations'],\
            width = 300,show_labels = False,\
            name = 'Number of initializations',show_name = True)
        max_iter_wid = pn.Param(self.param['maximum_iterations'],\
            widgets = {'maximum_iterations' : pn.widgets.Spinner},\
            parameters = ['maximum_iterations'],\
            width = 300,show_labels = False,\
            show_name = True,name = 'Maximum number of iterations')
        init_method_wid = pn.Param(self.param['initialization_method'],\
            widgets = {'initialization_method' : pn.widgets.Select},\
            parameters = ['initialization_method'],\
            width = 300,show_labels = False,\
            show_name = True,name = 'Initialization method')
        list_widgets_kmeans = [num_clust_wid,init_iter_wid,max_iter_wid,init_method_wid]
        for el in list_widgets_kmeans:
            for i,part in enumerate(el):
                part.margin = (0,10)
                if i%2 == 0:
                    part.style = {'color':'white'}
                else: pass
        wid_kmeans =\
            pn.Column(pn.pane.Markdown('#### K-Means Parameters',\
            style = {'color':'white'},width = 200),\
            *list_widgets_kmeans,width = 330,\
            height = 415,background = 'grey')
        for el in wid_kmeans:
            el.margin = (5,15)
        #Agglomerative Clustering
        self.connectivity_matrix_wid = pn.Param(self.param['connectivity_matrix'],\
            widgets = {'connectivity_matrix':pn.widgets.Toggle},\
            parameters = ['connectivity_matrix'],\
            width = 125,show_labels = False,name = 'Connectivity Off')
        self.connectivity_matrix_wid[0].button_type = 'danger'
        self.connectivity_matrix_wid[0].name = 'Connectivity Off'
        self.number_neighborgs_wid = pn.Param(self.param['number_of_neighbors_agg'],\
            widgets = {'number_of_neighbors_agg' : pn.widgets.Spinner},\
            parameters = ['number_of_neighbors_agg'],\
            width = 300,show_labels = False,\
            show_name = True,name = 'Number of neighbors - for connectivity')
        self.number_neighborgs_wid[0].margin = 5
        self.number_neighborgs_wid[0].style = {'color':'white'}
        self.number_neighborgs_wid[1].disabled = True
        linkage_wid = pn.Param(self.param['linkage'],\
            widgets = {'linkage' : pn.widgets.Select},\
            parameters = ['linkage'],\
            width = 300,show_labels = False,\
            show_name = True,name = 'Linkage method')
        self.connectivity_normalized_wid = pn.Param(self.param['connectivity_on_normalized'],\
            widgets = {'connectivity_on_normalized':pn.widgets.Toggle},\
            parameters = ['connectivity_on_normalized'],\
            width = 125,show_labels = False,name = 'Norm-Matrix Off')
        self.connectivity_normalized_wid[0].button_type = 'danger'
        self.connectivity_normalized_wid[0].disabled = True
        self.connectivity_normalized_wid[0].name = 'Norm-Matrix Off'
        affinity_method_wid = pn.Param(self.param['affinity_agglomerative'],\
            widgets = {'affinity_agglomerative':pn.widgets.Select},\
            parameters = ['affinity_agglomerative'],\
            width = 300,show_labels = False,\
            show_name = True,name = 'Affinity metrics')
        list_agg = [num_clust_wid,linkage_wid,affinity_method_wid]
        for el in list_agg:
            for i,part in enumerate(el):
                part.margin = (0,10)
                if i%2 == 0:
                    #part.margin = 0
                    part.style = {'color':'white'}
                else: pass
        self.wid_agglomerative = pn.Column(pn.pane.Markdown('#### Agglomerative Parameters',\
            style = {'color':'white'}),\
            *list_agg,pn.Row(self.connectivity_matrix_wid,\
                self.connectivity_normalized_wid,width = 300,margin = 5),\
            self.number_neighborgs_wid,width = 330,height = 415,\
            background = 'grey')
        for el in self.wid_agglomerative:
            el.margin = (5,15)
        #Spectral Clustering  
        self.number_Sneighs_wid = pn.Param(self.param['number_of_neighbors_spec'],\
            widgets = {'number_of_neighbors_spec':pn.widgets.Spinner},\
            parameters = ['number_of_neighbors_spec'],show_labels = False,\
            name = 'Number of neighbors - for connectivity',show_name = True,width = 300)
        self.gamma_wid = pn.Param(self.param['gamma'],\
            widgets = {'gamma':pn.widgets.FloatSlider},\
            parameters = ['gamma'],show_labels = False,\
            name = 'rbf Gamma',show_name = True,width = 300)
        self.gamma_wid[1].disabled = True
        self.gamma_wid[1].show_value = False
        self.gamma_wid[1].bar_color = '#B5EAD7'
        labels_wid = pn.Param(self.param['assign_labels'],\
            widgets = {'assign_labels':pn.widgets.Select},\
            parameters = ['assign_labels'],show_labels = False,\
            name = 'Labels-assign method',show_name = True,width = 300)
        affinityS_method_wid = pn.Param(self.param['affinity_spectral'],\
            widgets = {'affinity_spectral':pn.widgets.Select},\
            parameters = ['affinity_spectral'],width = 300,show_labels = False,\
            show_name = True,name = 'Spectral affinity metrics')
        list_spec = [num_clust_wid,init_iter_wid,\
        labels_wid,affinityS_method_wid,\
        self.number_Sneighs_wid,self.gamma_wid]
        for el in list_spec:
            for i,part in enumerate(el):
                part.margin = (0,10)
                if i%2 == 0:
                    #part.margin = 0
                    part.style = {'color':'white'}
                else: pass
        wid_spectral = pn.Column(pn.pane.Markdown('#### Spectral Parameters',\
            style = {'color':'white'}),\
            *list_spec,width = 330,\
            height = 415,background = 'grey')
        for el in wid_spectral:
            el.margin = (5,15)
        wid_spectral[0].margin = (5,15,0,15)
        #Some checkpoints - Normalization
        self.prenorm_button = pn.Param(self.param['prenormalization'],\
        widgets = {'prenormalization':pn.widgets.Toggle},\
        parameters = ['prenormalization'],\
        name = 'Normalize',show_labels = False,\
        width = 150,height = 25)
        self.prenorm_button[0].name = 'Off'
        self.prenorm_button[0].button_type = 'danger'
        self.available_norms_wid = pn.Param(self.param['available_norms'],\
            widgets = {'available_norms':pn.widgets.Select},\
            parameters = ['available_norms'],width = 300,name = 'Available norms',\
            show_labels = False, show_name = True)
        self.available_norms_wid[0].style = {'color': 'white'}
        self.available_norms_wid[1].disabled = True
        self.available_norms_wid.margin = (5,15)
        #self.available_norms_wid[0].margin = (5,15)
        #NOw the actual construction of the panel
        self.cluster_tab = pn.Tabs(('KMeans',wid_kmeans),\
            ('Agglomerative',self.wid_agglomerative),\
            ('Spectral',wid_spectral),\
            #height_policy = 'min',max_height = 500,\
            width  = 330,height = 425,dynamic = True)
        self.cluster_tab.margin = 10
        #The column with the widgets and buttons
        button_column = pn.Column(pn.pane.Markdown('### Clustering Main HUB',\
            style = {'color':'white'}),\
        pn.GridBox(self.button_cluster,self.button_store,ncols = 2,width = 330,margin = (5,5)),\
        self.cluster_tab,pn.layout.Divider(height= 5,width = 300),\
        pn.Row(pn.pane.Markdown('#### Pre-Normalization',style = {'color':'white'}),\
            self.prenorm_button,width = 310,margin = (5,10)),\
        self.available_norms_wid,width = 350,height = 750,background = 'grey')
        #button_column.margin = 0
        for el in button_column:
            el.margin = (5,10)
        #button_column[5].margin = (0,5)
        saves_pan = pn.Row(pn.Column(\
            pn.Row(pn.pane.Markdown('#### FileName',width = 100,style = {'color':'white'}),\
                self.savname_wid,height = 40,margin = 0),\
            pn.Row(pn.pane.Markdown('#### FolderName',width = 100,style = {'color':'white'}),\
                self.savfold_wid,height = 40,margin = 0),\
            width = 620),\
            pn.Column(self.button_save,self.button_save_data,margin = 0,height = 80),\
            width = 800,margin = (0,15))
        current_selection_pan = pn.Row(\
            pn.Column(self.mini_image_default,width = 100,height = 100,margin = (0,5)),\
            self.df_widgets,self.button_show_results,\
            width = 800,margin = (0,15))
        select_run_pan = pn.Row(\
            pn.pane.Markdown('#### Run Selector',align = 'center',style = {'color':'white'}),\
            self.run_buttons_widgets,width = 800,margin = (0,15))
        column_saves = pn.Column(pn.pane.Markdown('### Run selection and saving HUB',\
            style = {'color':'white'},margin = (5,15,5,15)),\
        pn.layout.Divider(height = 5,margin = (-15,5,15,15),width = 750),\
        select_run_pan,current_selection_pan,\
        pn.layout.Divider(height = 5,margin = (5,5,15,15),width = 750),\
        saves_pan,\
        height = 350,width = 800,background = 'grey')
        column_area_interest = pn.Column(\
            pn.Row(pn.pane.Markdown('### Area of Interest',width = 125,\
                margin = (5,15,-10,30),style = {'color':'white'}),\
            self.button_change_cmap,width = 370,margin = 0),\
            self.hmap_placeholder,height = 350,width = 385,background = 'black') 
        area_image = pn.Row(column_area_interest,column_saves,height = 350,margin = 0)
        #PLaceholders for the holoviews objects
        self.cluster_im_placeholder = pn.pane.HoloViews(self.im_default,margin = (0,15))
        self.curves_placeholder = pn.pane.HoloViews(self.dynamic_curve,margin = 0)
        self.button_save.margin = (5,10,5,15)
        self.button_save_data.margin = (5,10,5,15)
        self.button_show_results.margin = (0,10,0,15)
        #Let's improve the visual controls a bit
        self.mkdown_results =\
            pn.pane.Markdown('### None',style={'color':'darkgrey'},width = 150)
        self.mkdown_run =\
            pn.pane.Markdown('### None',style = {'color':'darkgrey'},width = 150)
        interactive_image_row = pn.Row(self.cluster_im_placeholder,\
            self.curves_placeholder,height = 345,width = 1185,background = 'black',\
            margin = 0)
        self.visual_controls = pn.Row(\
            pn.pane.Markdown('### Results on display :',\
                width = 150,margin = (5,15,5,30),style = {'color':'white'}),\
            self.mkdown_results,\
            pn.pane.Markdown('### Run status:',width = 125,\
                style = {'color':'white'}),\
            self.mkdown_run,\
            #pn.Row(self.button_type_graph,self.button_type_curve),\
            pn.Row(self.button_type_curve),\
            #pn.Spacer(height = 30,width = 100,background = 'white',margin = 10),\
            #self.point_size_wid,self.button_change_point_size,\
            width = 1185,margin = 0,background = 'black')

        self.image_column = pn.Column(\
            area_image,self.visual_controls,interactive_image_row,\
            width = 1300,height = 750)
        #self.image_column[1].margin = (5,0,5,25)
        #self.visual_controls.margin = (0,0,0,25)
        self.cluster_layout = pn.Row(button_column,self.image_column)
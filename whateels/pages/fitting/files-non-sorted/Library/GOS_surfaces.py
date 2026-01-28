import sys
import time
from time import sleep
import os
import copy as cp
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import holoviews as hv
import panel as pn
####3
from holoviews.streams import param
from holoviews import streams, opts, dim
from Database.elements import elements
#To calculate the cross sections
from cross_sections import bethe_surface_calculations

R = 13.6056923             # Rydberg of energy in eV
e = 1.602176487*1E-19      # electron charge in C
m0 = 9.10938215*1E-31      # electron rest mass in kg
a0 = 5.2917720859*1E-11    # Bohr radius in m
c_light = 2.99792458*1E8  # speed of light in m/s


print('Importing - Generallized Oscillator Strentgh (GOS) Analysis tools')

def change_extension():
    sleep(5)
    hv.extension('bokeh',logo = False)

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
        #print(plot.handles['layout']['title'])

class GOS_surface_analyser(param.Parameterized):
    ### old things###
    #beta = param.Number(default = 0,bounds = (0,np.inf))
    #alpha = param.Number(default = 0,bounds = (0,np.inf))
    #E0 = param.Number(default = 0,bounds = (0,np.inf))

    #new thing####################
    beta = param.Number(default = 0,bounds = (0,None))
    alpha = param.Number(default = 0,bounds = (0,None))
    E0 = param.Number(default = 0,bounds = (0,None))
    #new thing####################


    elems  = param.ObjectSelector('C',['C'])
    sshell = param.ObjectSelector('K',['K'])
    zoom1 = param.Boolean(False)
    zoom2 = param.Boolean(False)
    zoom3 = param.Boolean(False)
    zoom4 = param.Boolean(False)
    number_selected = param.Integer(0)
    mesh = param.Integer(250,bounds = (100,1000))

    def __init__(self):
        super().__init__()
        # widgets
        hv.extension('plotly',logo = False)
        #hv.extension('bokeh',logo = False)
        self.param['mesh'].label = 'Mesh points number'
        self.wid_mesh_val = pn.Param(self.param['mesh'],\
            widgets = {'mesh':pn.widgets.IntSlider},\
            parameters = ['mesh'],\
            name = 'Mesh points number',\
            show_labels = False,show_name = True,\
            width = 270,margin = (5,15))
        self.wid_mesh_val[0].style = {'color':'white'}
        self.wid_mesh_val[1].show_value = False
        self.wid_mesh_val[1].step = 10
        self.wid_mesh_val[1].bar_color = '#B5EAD7'
        #style = {'color':'white'}
        self.wid_elem_sel = pn.Param(self.param['elems'],\
            widgets = {'elems':pn.widgets.Select},\
            parameters = ['elems'],name = 'Element',\
            show_name = True, show_labels = False,width = 140,\
            margin = (0,0,5,0))
        self.wid_elem_sel[0].style = {'color':'white'}
        self.wid_elem_sel[0].margin = (0,10)
        self.wid_elem_sel[1].margin = (5,10)
        #self.wid_elem_sel[1].width = 75
        self.wid_ssh_sel = pn.Param(self.param['sshell'],\
            widgets = {'sshell':pn.widgets.Select},\
            parameters = ['sshell'],name = 'Subshell',\
            show_name = True, show_labels = False,width = 140,\
            margin = (0,0,5,0))
        self.wid_ssh_sel[0].style = {'color':'white'}
        self.wid_ssh_sel[0].margin = (0,10)
        self.wid_ssh_sel[1].margin = (5,10)
        #self.wid_ssh_sel[1].width = 75
        ##cambiar cosa de int. 
        #Este ya va. 
        self.wid_E0 = pn.Param(self.param['E0'],\
            widgets = {'E0':pn.widgets.Spinner},\
            parameters = ['E0'],name = 'Beam Energy [keV]',\
            show_name = True, show_labels = False,\
            width = 270,margin = (5,15))
        self.wid_E0[0].style = {'color':'lightgrey'}
        self.wid_E0[1].step = 1

        #estos dan error: ############
        """
        self.wid_alpha = pn.Param(self.param['alpha'],\
            widgets = {'alpha':pn.widgets.Spinner},\
            parameters = ['alpha'],name = '\u03B1 [mrad]',\
            show_name = True, show_labels = False,\
            width = 130)
        self.wid_alpha[0].style = {'color':'lightgrey'}
        self.wid_alpha[1].step = 0.01
        self.wid_beta = pn.Param(self.param['beta'],\
            widgets = {'beta':pn.widgets.Spinner},\
            parameters = ['beta'],name = '\u03B2 [mrad]',\
            show_name = True, show_labels = False,\
            width = 130)
        self.wid_beta[0].style = {'color':'lightgrey'}
        self.wid_beta[1].step = 0.01"""
        #estos dan error: ############

        self.wid_alpha = pn.Param(
            self.param['alpha'],
            widgets={'alpha': pn.widgets.FloatInput},
            parameters=['alpha'],
            name='\u03B1 [mrad]',
            show_name=True,
            show_labels=False,
            width=130
        )
        self.wid_alpha[0].style = {'color': 'lightgrey'}
        self.wid_alpha[1].step = 0.01

        self.wid_beta = pn.Param(
            self.param['beta'],
            widgets={'beta': pn.widgets.FloatInput},
            parameters=['beta'],
            name='\u03B2 [mrad]',
            show_name=True,
            show_labels=False,
            width=130
        )
        self.wid_beta[0].style = {'color': 'lightgrey'}
        self.wid_beta[1].step = 0.01

        #Butttons
        self.button_show_surfaces = pn.widgets.Button(name = 'Show GOS surfaces',\
            disabled = True,button_type = 'success',width = 200)
        self.button_show_surfaces.on_click(self._call_back_show_surfaces)
        self.button_update_surfaces = pn.widgets.Button(name = '\u27F3',\
            disabled = True,button_type = 'warning',width = 35)
        self.button_update_surfaces.on_click(self._call_back_update_surfaces)
        self.button_comparative = pn.widgets.Button(name = 'Comparative Zoom',\
            disabled = True,button_type = 'default',margin = (5,15))
        self.button_comparative.on_click(self._callback_zoom_comparative)
        self.button_zoom1 = pn.Param(self.param['zoom1'],\
            widgets = {'zoom1':pn.widgets.Toggle},parameters = ['zoom1'],\
            show_name = False,show_labels = False,width = 115)
        self.button_zoom1[0].name = 'TheoreticalGOS'
        self.button_zoom1[0].width = 115
        self.button_zoom1[0].margin = 0
        self.button_zoom1[0].button_type = 'default'
        self.button_zoom1[0].disabled = True
        self.button_zoom2 = pn.Param(self.param['zoom2'],\
            widgets = {'zoom2':pn.widgets.Toggle},parameters = ['zoom2'],\
            show_name = False,show_labels = False,width = 115)
        self.button_zoom2[0].name = 'F(\u03B1,\u03B2) - factor'
        self.button_zoom2[0].width = 115
        self.button_zoom2[0].margin = 0
        self.button_zoom2[0].button_type = 'default'
        self.button_zoom2[0].disabled = True
        self.button_zoom3 = pn.Param(self.param['zoom3'],\
            widgets = {'zoom3':pn.widgets.Toggle},parameters = ['zoom3'],\
            show_name = False,show_labels = False,width = 115)
        self.button_zoom3[0].name = '\u03B2 - cut GOS'
        self.button_zoom3[0].width = 115
        self.button_zoom3[0].margin = 0
        self.button_zoom3[0].button_type = 'default'
        self.button_zoom3[0].disabled = True
        self.button_zoom4 = pn.Param(self.param['zoom4'],\
            widgets = {'zoom4':pn.widgets.Toggle},parameters = ['zoom4'],\
            show_name = False,show_labels = False,width = 115)
        self.button_zoom4[0].name = 'F(\u03B1,\u03B2) - GOS'
        self.button_zoom4[0].width = 115
        self.button_zoom4[0].margin = 0
        self.button_zoom4[0].button_type = 'default'
        self.button_zoom4[0].disabled = True
        
        '''
        self.button_zoom1 = pn.widgets.Button(name = 'Theoretical GOS',width = 110,\
            disabled = True,button_type = 'danger')
        self.button_zoom1.on_click(self._launch_zoom_1)
        self.button_zoom2 = pn.widgets.Button(name = 'F(\u03B1,\u03B2) - factor',width = 110,\
            disabled = True,button_type = 'warning')
        self.button_zoom2.on_click(self._launch_zoom_2)
        self.button_zoom3 = pn.widgets.Button(name = '\u03B2 - cut GOS',width = 110,\
            disabled = True,button_type = 'primary')
        self.button_zoom3.on_click(self._launch_zoom_3)
        self.button_zoom4 = pn.widgets.Button(name = 'F(\u03B1,\u03B2) - GOS',width = 110,\
            disabled = True,button_type = 'success')
        self.button_zoom4.on_click(self._launch_zoom_4)
        '''
        self.titles = {'theoretical':'#### GOS surface of {}',\
            'F-factor':'####  Geometric factor surface \u03B1 {} | \u03B2 {}',\
            'beta-cut':'####  GOS surface truncated | \u03B2 {} mrad',\
            'beta-F':'####  GOS surface f-modulated'}
        self.titles2 = {'theoretical':'### GOS surface',\
            'F-factor':'###  Geometric factor surface F(\u03B1,\u03B2) with \u03B1 {} [mrad] and \u03B2 {} [mrad]',\
            'beta-cut':'###  GOS surface truncated | \u03B2 {} [mrad]',\
            'beta-F':'###  GOS surface f-modulated by F(\u03B1 = {},\u03B2 = {})'}
        self.cmaps = {'theoretical':'autumn_r',\
            'F-factor':'spring_r',\
            'beta-cut': 'winter_r',\
            'beta-F':'summer_r'}
        self.data_displayed = False
        self.populate_objects()
        
        
    def populate_objects(self):
        #NOW we can begin to populate objects
        ############################################################################
        #First thing on the list - get the elements in the data bases
        #The subshell dictionary form the listed elements in hyperspy
        self.subshell_dictionary = dict()
        for el in elements:
            try:
                elements[el]['Atomic_properties']['Binding_energies']
            except:
                pass
            else:
                self.subshell_dictionary[el] = []
                for ssh in elements[el]['Atomic_properties']['Binding_energies']:
                    self.subshell_dictionary[el].append('{}'.format(ssh))
        #Once Solved the available elements - those with actual subshells listed
        self.param['elems'].objects = sorted(self.subshell_dictionary.keys())
        self.elems = self.param['elems'].objects[0]
        ############################################################################
        
    def calculate_surfaces(self):
        #initialized the calculations app
        exp_param = [self.E0,self.beta,self.alpha]
        self.veto_list = [sh for sh in self.param['sshell'].objects if sh != self.sshell]
        self.bethe = bethe_surface_calculations.bethe_surface(self.elems)
        self.bethe.autorun_gosSurfaces(exp_param=exp_param,\
            veto_sshell_list=self.veto_list,mesh_p = self.mesh)
        onset = elements[self.elems]['Atomic_properties']\
            ['Binding_energies'][self.sshell]['onset_energy (eV)']
        factor = elements[self.elems]['Atomic_properties']\
            ['Binding_energies'][self.sshell]['factor']
        clave = '_'.join([self.elems,self.sshell])
        #The calculations are done, let's create a valid data structure
        self.gos_surfs = xr.Dataset(\
            {'theoretical':(['Qax','Eax'],np.transpose(cp.deepcopy(self.bethe\
                .theoretical_surf[clave]['data']))*factor),\
            'beta-cut':(['Qax','Eax'],np.transpose(cp.deepcopy(self.bethe\
                .beta_surf[clave]['data']))*factor),\
            'F-factor':(['Qax','Eax'],np.transpose(cp.deepcopy(self.bethe\
                .factor[clave]['data']))),\
            'beta-F':(['Qax','Eax'],np.transpose(cp.deepcopy(self.bethe\
                .factorized_betacut_surface[clave]['data']))*factor)},\
            coords = {\
            'Qax':cp.deepcopy(self.bethe\
                .theoretical_surf[clave]['axis']['Qax']),\
            'Eax':(cp.deepcopy(self.bethe\
                .theoretical_surf[clave]['axis']['Eax'])-onset)/R})
    
    def _callback_zoom_comparative(self,event):
        lista_zoom = [self.zoom1,self.zoom2,self.zoom3,self.zoom4]
        lista_claves = ['theoretical','F-factor','beta-cut','beta-F']
        if self.number_selected <= 0 or self.number_selected > 2:
            #safety measurement - should not be triggered if app works properly
            self.button_comparative.button_type = 'danger'
            self.button_comparative.name = 'Error - num > 2 or < 0'
            self.button_comparative.disabled = True
            sleep(5)
            self.button_comparative.disabled = False
            self.button_comparative.name ='Comparative Zoom'
            self.button_comparative.button_type = 'default'
            return
        elif self.number_selected == 1:
            lista_cl1 = [el for i,el in enumerate(lista_claves) if lista_zoom[i]]
            if len(lista_cl1) != 1:
                #safety measurement ... never should be triggered
                self.button_comparative.button_type = 'danger'
                self.button_comparative.name = 'Error - num != 1'
                self.button_comparative.disabled = True
                sleep(5)
                self.button_comparative.disabled = False
                self.button_comparative.name ='Comparative Zoom'
                self.button_comparative.button_type = 'default'
                return
            else:
                surf = lista_cl1[0]
                if surf == 'F-factor':
                    surfi = hv.Surface(self.gos_surfs[surf],kdims=['Eax','Qax'])\
                    .opts(cmap = self.cmaps[surf],\
                    hooks = [hooks_plotly_surfacesf],projection = '',\
                    alpha = 0.75,height = 650,width = 1000)
                else:
                    surfi = hv.Surface(self.gos_surfs[surf],kdims=['Eax','Qax'])\
                    .opts(cmap = self.cmaps[surf],\
                    hooks = [hooks_plotly_surfaces1],projection = '',\
                    alpha = 0.75,height = 650,width = 1000)
                self._launch_extra_windows(lista_cl1,[surfi])
        else:
            lista_cl2 = [el for i,el in enumerate(lista_claves) if lista_zoom[i]]
            if len(lista_cl2) != 2:
                #safety measurement ... never should be triggered
                self.button_comparative.button_type = 'danger'
                self.button_comparative.name = 'Error - num != 2'
                self.button_comparative.disabled = True
                sleep(5)
                self.button_comparative.disabled = False
                self.button_comparative.name ='Comparative Zoom'
                self.button_comparative.button_type = 'default'
                return
            else:
                lista_sur = []
                for surf in lista_cl2:
                    if surf == 'F-factor':
                        lista_sur.append(\
                        hv.Surface(self.gos_surfs[surf],kdims=['Eax','Qax'])\
                        .opts(cmap = self.cmaps[surf],\
                        hooks = [hooks_plotly_surfacesf],projection = '',\
                        alpha = 0.75,height = 500,width = 700))
                    else:
                        lista_sur.append(\
                        hv.Surface(self.gos_surfs[surf],kdims=['Eax','Qax'])\
                        .opts(cmap = self.cmaps[surf],\
                        hooks = [hooks_plotly_surfaces1],projection = '',\
                        alpha = 0.75,height = 500,width = 700))
                self._launch_extra_windows(lista_cl2,lista_sur)
    
    def _launch_extra_windows(self,list_names,list_surfaces):
        print('launching')
        title_objects = {'theoretical':[' '.join([self.elems,self.sshell])],\
            'F-factor':[self.alpha,self.beta],\
            'beta-cut':[self.beta],\
            'beta-F':[self.alpha,self.beta]}
        lista_mkdown = []
        for el in list_names:
            lista_mkdown.append(pn.pane.Markdown(\
            self.titles2[el].format(*title_objects[el]),\
            width = 650,margin = (5,25),height = 50))
        mkdown_banner = pn.pane.Markdown(\
            '### Zoomed display of - {} - | \
            Parameters - E0 {} [eV] - \u03B1 {} [mrad] - \u03B2 {} [mrad] - | Mesh - {}x{} points'\
            .format(' '.join([self.elems,self.sshell]),\
            self.E0,self.alpha,self.beta,self.mesh,self.mesh),\
            style = {'color':'white'},width = 900,margin = (5,15,0,25))
        zoomed_app = pn.Column(\
            pn.Row(mkdown_banner,height = 50,width = 1400,margin = 0,\
                background = 'black'),\
            pn.Row(*lista_mkdown,width = 1400,margin = (0,0,10,0)),\
            pn.Row(*list_surfaces,\
                height = 675,width = 1400,margin = 0),\
            height = 755,width = 1400)
        zoomed_app.show()


    @param.depends('zoom1',watch = True)
    def _check_zoom1(self):
        if not self.data_displayed:
            return
        else:
            if self.zoom1:
                self.number_selected += 1
                self.button_zoom1[0].button_type = 'danger'
            else:
                self.number_selected -= 1
                self.button_zoom1[0].button_type = 'default'
    
    @param.depends('zoom2',watch = True)
    def _check_zoom2(self):
        if not self.data_displayed:
            return
        else:
            if self.zoom2:
                self.number_selected += 1
                self.button_zoom2[0].button_type = 'warning'
            else:
                self.number_selected -= 1
                self.button_zoom2[0].button_type = 'default'

    @param.depends('zoom3',watch = True)
    def _check_zoom3(self):
        if not self.data_displayed:
            return
        else:
            if self.zoom3:
                self.number_selected += 1
                self.button_zoom3[0].button_type = 'primary'
            else:
                self.number_selected -= 1
                self.button_zoom3[0].button_type = 'default'

    @param.depends('zoom4',watch = True)
    def _check_zoom4(self):
        if not self.data_displayed:
            return
        else:
            if self.zoom4:
                self.number_selected += 1
                self.button_zoom4[0].button_type = 'success'
            else:
                self.number_selected -= 1
                self.button_zoom4[0].button_type = 'default'

    @param.depends('number_selected',watch = True)
    def _disable_toggle_options(self):
        if not self.data_displayed:
            return
        if 0 < self.number_selected < 2:
            self.enable_disable_zooms(True)
            self.button_comparative.disabled = False
        elif self.number_selected >= 2:
            self.enable_disable_partial()
            self.button_comparative.disabled = False
        else:
            self.enable_disable_zooms(True)
            self.button_comparative.disabled = True
        
    def enable_disable_partial(self):
        lista_zooms = [self.zoom1,self.zoom2,self.zoom3,self.zoom4]
        lista_buttons = [self.button_zoom1,self.button_zoom2,\
            self.button_zoom3,self.button_zoom4]
        for boolean,button in zip(lista_zooms,lista_buttons):
            if boolean:
                button[0].disabled = False
            else:
                button[0].disabled = True

    def enable_disable_zooms(self, booleano):
        self.button_zoom1[0].disabled = not booleano
        self.button_zoom2[0].disabled = not booleano
        self.button_zoom3[0].disabled = not booleano
        self.button_zoom4[0].disabled = not booleano

    def launch_surfaces(self):
        #This method creates all the surfaces in plotly backend and launches them
        title_objects = {'theoretical':[' '.join([self.elems,self.sshell])],\
            'F-factor':[self.alpha,self.beta],\
            'beta-cut':[self.beta],\
            'beta-F':[None]}
        self.surfaces = []
        hv.extension('plotly',logo = False)
        for surf in self.titles.keys():
            hv.extension('plotly',logo = False)
            if surf != 'F-factor':
                surfi = hv.Surface(self.gos_surfs[surf],kdims=['Eax','Qax'])\
                    .opts(cmap = self.cmaps[surf],\
                    hooks = [hooks_plotly_surfaces1],projection = '',\
                    alpha = 0.75,height = 300,width = 500)
            else:
                surfi = hv.Surface(self.gos_surfs[surf],kdims=['Eax','Qax'])\
                    .opts(cmap = self.cmaps[surf],\
                    hooks = [hooks_plotly_surfacesf],projection = '',\
                    alpha = 0.75,height = 300,width = 500)
            self.surfaces.append(
                pn.Column(\
                    pn.pane.Markdown(self.titles[surf].format(*title_objects[surf]),\
                        width = 450,margin = (5,15),height = 25),\
                    surfi,height = 350,width = 520,margin = 5))
        new_grid = pn.GridBox(*self.surfaces,ncols = 2,nrows = 2)
        self.graphical_interfase.objects = [self.row_mkdown,new_grid]

    def _call_back_show_surfaces(self,event):
        try:
            #self._change_zoom_buttons_availability(True)
            self.enable_disable_zooms(False)
            self.button_comparative.disabled = True
            self.button_show_surfaces.button_type = 'warning'
            self.button_show_surfaces.name = 'Calculating GOS'
            self.button_show_surfaces.disabled = True
            self.calculate_surfaces()
        except:
            self._disable_toggle_options()
            '''
            if self.number_selected <= 2 and self.data_displayed:
                self.enable_disable_zooms(True)
            '''
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'danger'
            self.button_show_surfaces.name = 'Failed calculations'
            self.button_show_surfaces.disabled = True
            sleep(5)
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.name = 'Show GOS surfaces'
            return
        else:
            if not self.data_displayed: 
                self.data_displayed = True
            self.updatable = True
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.name = 'Updating graphs'
            self.button_show_surfaces.disabled = True
            #Now we create the surfaces plots
            self.launch_surfaces()
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.name = 'Show GOS surfaces'
            self.button_show_surfaces.disabled = True
            self.button_update_surfaces.disable = False
            #self._change_zoom_buttons_availability(False)
            self.mkdown_current.object =\
                '#### Currently on display - {} - | Parameters - E0 {} eV\
                - \u03B1 {} mrad - \u03B2 {} mrad - | Mesh - {}x{} points'\
                .format(' '.join([self.elems,self.sshell]),\
                    self.E0,self.alpha,self.beta,self.mesh,self.mesh)
            self.mkdown_current.style = {'color':'white'}
            self._disable_toggle_options()
            #if self.number_selected <= 2: self.enable_disable_zooms(True)
            
    def _call_back_update_surfaces(self,event):
        try:
            #self._change_zoom_buttons_availability(True)
            self.enable_disable_zooms(False)
            self.button_comparative.disabled = True
            self.button_show_surfaces.button_type = 'warning'
            self.button_show_surfaces.name = 'Calculating GOS'
            self.button_show_surfaces.disabled = True
            self.calculate_surfaces()
        except:
            #if self.number_selected <= 2: self.enable_disable_zooms(True)
            self._disable_toggle_options()
            self.button_show_surfaces.button_type = 'danger'
            self.button_show_surfaces.name = 'Failed calculations'
            self.button_show_surfaces.disabled = True
            sleep(5)
            self.button_update_surfaces.disable = False
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.name = 'Show GOS surfaces'
            self.button_show_surfaces.disabled = True
            return
        else:
            self.updatable = True
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.name = 'Updating graphs'
            self.button_show_surfaces.disabled = True
            #Now we create the surfaces plots
            self.launch_surfaces()
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.name = 'Show GOS surfaces'
            self.button_show_surfaces.disabled = True
            self.button_update_surfaces.disable = False
            #self._change_zoom_buttons_availability(False)
            #if self.number_selected <= 2: self.enable_disable_zooms(True)
            self.mkdown_current.object =\
                '#### Currently on display - {} - | Parameters - E0 {} eV\
                - \u03B1 {} mrad - \u03B2 {} mrad - | Mesh - {}x{} points'\
                .format(' '.join([self.elems,self.sshell]),\
                    self.E0,self.alpha,self.beta,self.mesh,self.mesh)
            self.mkdown_current.style = {'color':'white'}
            self._disable_toggle_options()

    @param.depends('beta',watch = True)
    def _change_beta_colour(self):
        if self.beta == 0.0:
            self.wid_beta[0].style = {'color':'lightgrey'}
        else:
            self.wid_beta[0].style = {'color':'crimson'}

    @param.depends('alpha',watch = True)
    def _change_alpha_colour(self):
        if self.alpha == 0.0:
            self.wid_alpha[0].style = {'color':'lightgrey'}
        else:
            self.wid_alpha[0].style = {'color':'orange'}

    @param.depends('E0',watch = True)
    def _change_E0_colour(self):
        if self.E0 == 0.0:
            self.wid_E0[0].style = {'color':'lightgrey'}
        else:
            self.wid_E0[0].style = {'color':'dodgerblue'}

    @param.depends('elems',watch = True)
    def change_elem(self):
        self.updatable = False
        self.button_update_surfaces.disabled = True
        self.param['sshell'].objects = list(self.subshell_dictionary[self.elems])
        self.sshell = self.param['sshell'].objects[0]
        if all([el != 0.0 for el in [self.E0,self.alpha,self.beta]]):
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'success'
        else:
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.disabled = True

    @param.depends('sshell',watch = True)
    def change_sshell(self):
        self.updatable = False
        self.button_update_surfaces.disabled = True
        if all([el != 0.0 for el in [self.E0,self.alpha,self.beta]]):
            self.button_show_surfaces.disabled = False
            self.button_show_surfaces.button_type = 'success'
        else:
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.disabled = True

    @param.depends('E0','alpha','beta','mesh',watch = True)
    def _allow_show_surfaces(self):
        if any([el == 0.0 for el in [self.E0,self.alpha,self.beta]]):
            self.button_update_surfaces.disabled = True
            self.button_show_surfaces.button_type = 'success'
            self.button_show_surfaces.disabled = True
        else:
            if self.updatable:
                self.button_update_surfaces.disabled = False
                self.button_show_surfaces.button_type = 'success'
                self.button_show_surfaces.disabled = True
            else:
                self.button_show_surfaces.disabled = False
                self.button_update_surfaces.disabled = True
                self.button_show_surfaces.button_type = 'success'

    def create_layout(self):
        self.lista_grid = []
        for _ in range(4):
            self.lista_grid.append(pn.Spacer(height = 310,width = 525,background = 'darkgrey'))
        self.grid_graphs = pn.GridBox(*self.lista_grid,ncols = 2, nrows = 2,\
            height = 670,width = 1100,margin = (5,50))
        self.configuration_column = pn.Column(\
            pn.pane.Markdown('### Generalized Oscillator Strength (GOS)',\
                    style = {'color':'white'},width = 280,margin = (5,10,0,10)),\
            pn.layout.Divider(width = 270,margin = (0,15)),\
            pn.Row(self.wid_elem_sel,self.wid_ssh_sel,\
                width = 280,margin = (0,10,5,10)),\
            pn.layout.Divider(width = 270,margin = (15,15,0,15)),\
            pn.pane.Markdown('#### Experimental parameters',\
                style={'color':'white'},width = 270,margin = (0,15,-5,15)),\
            self.wid_E0,\
            pn.Row(self.wid_alpha,self.wid_beta,width = 270,margin = (0,15)),\
            self.wid_mesh_val,\
            pn.layout.Divider(width = 270,margin = (15,15,0,15)),\
            pn.Row(self.button_show_surfaces,self.button_update_surfaces,\
                width = 270,margin = (0,15)),\
            pn.layout.Divider(width = 270,margin = (15,15,0,15)),\
            pn.pane.Markdown('#### Launch zoomed surfaces',\
                style = {'color':'white'},width = 270,margin = (-5,15,0,15)),\
            pn.Row(self.button_zoom1,self.button_zoom2,width = 270,margin = (0,25)),\
            pn.Row(self.button_zoom3,self.button_zoom4,width = 270,margin = (0,25)),\
            pn.Column(self.button_comparative,width = 270,margin = (0,15)),\
            background = 'black',width = 300,height = 730)
        self.mkdown_current = pn.pane.Markdown(\
            '#### Currently on display - {} - | Parameters - E0 {} eV\
            - \u03B1 {} mrad - \u03B2 {} mrad - | Mesh - {}x{} points'\
            .format(*['None']*4,'\u2205'*3,'\u2205'*3),\
            style = {'color':'grey'},margin = (5,25,0,350),width = 950)
        self.row_mkdown = pn.Row(self.mkdown_current,\
                height = 50,background = 'black',width = 1200,margin = 0)
        self.graphical_interfase = pn.Column(\
            self.row_mkdown,\
            self.grid_graphs,\
            height = 730,width = 1200,margin=0)
        self.layout = pn.Row(self.configuration_column,\
                self.graphical_interfase)
        self.layout.show()
        '''
        pn.pane.Markdown('#### GOS: Element and subshell',\
            style = {'color':'white'},width = 270,margin = (5,15)),\
        '''

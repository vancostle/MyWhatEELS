"""UMAP and HDBSCAN clustering for spectral imaging data.

This module provides a class for performing dimensionality reduction and clustering
on EELS (Electron Energy Loss Spectroscopy) data using UMAP and HDBSCAN algorithms.
"""

import numpy as np
import time
import pickle
import os
import umap
import hdbscan

from .colormaps import get_nclusters_cmap
from .visualizers import (
    plot_hdbscan_map_intensities,
    plot_hdbscan_map_probabilities,
    plot_hdbscan_map,
    plot_umap_embedding_with_labels,
    plot_mean_spectra_per_cluster,
    visualize_umap_embedding,
    plot_clusters_overlay
)
from .utils import (
    cut_signal,
    plot_image,
    plot_pixel_spectrum,
    plot_sum_spectrum,
    plot_cluster_dispersion_histograms,
    save_centroids
)


class UMAP_HDBSCAN:
    """
    Main class for UMAP dimensionality reduction and HDBSCAN clustering.
    
    This class handles:
    - UMAP embedding computation and visualization
    - HDBSCAN clustering on UMAP embeddings
    - Visualization of clustering results
    - Utility functions for spectral data analysis
    """
    
    def __init__(self, data, e_loss):
        """
        Initialize UMAP_HDBSCAN with numpy array data.
        
        Parameters:
        -----------
        data : np.ndarray
            3D array with shape (height, width, energy_channels) containing spectral data
        e_loss : np.ndarray
            1D array containing the energy loss axis values
        """
        self.data = data
        self.e_loss = e_loss
        self._hdbscan_results = None
        self.umap_embedding_ = None
        self.umap_shape = None
        self.umap_data_dict = None
    
    # Visualization methods - delegated to visualizers module
    def _plot_hdbscan_map_intensities(self, clustering, channel=None, cmap='cubehelix'):
        """Crear mapas ponderados por intensidad para cada cluster."""
        return plot_hdbscan_map_intensities(self.data, clustering, channel, cmap)
    
    def _plot_hdbscan_map_probabilities(self, clustering, hdbscan_results, norm='log'):
        """Visualización soft del clustering usando HDBSCAN."""
        return plot_hdbscan_map_probabilities(clustering, hdbscan_results, norm)
    
    def _plot_hdbscan_map(self, clustering, cmap_obj):
        """Plot HDBSCAN clustering map."""
        return plot_hdbscan_map(self.data, clustering, cmap_obj)
    
    def _plot_umap_embedding_with_labels(self, embedding, labels, cmap_obj, min_samp, min_clust):
        """Plot UMAP embedding colored by cluster labels."""
        return plot_umap_embedding_with_labels(embedding, labels, cmap_obj, min_samp, min_clust)
    
    def _plot_mean_spectra_per_cluster(self, clustering, cmap_obj):
        """Plot the mean spectrum for each cluster as colored curves."""
        return plot_mean_spectra_per_cluster(self.data, self.e_loss, clustering, cmap_obj)
    
    def plot_clusters_overlay(self, clustering=None, labels=None, colors=None, channel=None,
                             max_labels=6, frame_height=300, frame_width=650,
                             colorbar_width=90, colorbar_spacing=0, colorbar_position='right',
                             colorbar_side='left'):
        """Superpone varios mapas de intensidad (uno por cluster) en un único plot."""
        if clustering is None and self._hdbscan_results is not None:
            clustering = self._hdbscan_results.labels_.reshape(self.data.shape[0], self.data.shape[1])
        return plot_clusters_overlay(
            self.data, clustering, self._hdbscan_results, labels, colors, channel,
            max_labels, frame_height, frame_width, colorbar_width, colorbar_spacing,
            colorbar_position, colorbar_side
        )
    
    # Utility methods - delegated to utils module
    def cut_signal(self, x1=None, x2=None):
        """Corta la señal en el rango especificado."""
        self.data, self.e_loss = cut_signal(self.data, self.e_loss, x1, x2)
        return self.data
    
    def plot_image(self):
        """Plot summed image from 3D spectral data."""
        return plot_image(self.data)
    
    def plot_pixel_spectrum(self, pixel):
        """Plot spectrum from a single pixel."""
        return plot_pixel_spectrum(self.data, self.e_loss, pixel)
    
    def plot_sum_spectrum(self):
        """Plot sum spectrum from all pixels."""
        return plot_sum_spectrum(self.data, self.e_loss)
    
    def plot_cluster_dispersion_histograms(self, clustering=None):
        """Para cada cluster, grafica histograma de las distancias euclídeas al centroide."""
        if clustering is None and self._hdbscan_results is not None:
            clustering = self._hdbscan_results.labels_.reshape(self.data.shape[0], self.data.shape[1])
        return plot_cluster_dispersion_histograms(self.data, self.e_loss, clustering)
    
    def save_centroids(self, clustering, filename="centroids.npy"):
        """Calcula y guarda los centroides y las posiciones de los píxeles."""
        return save_centroids(self.data, self.e_loss, clustering, filename)
    
    # Colormap utility
    def _get_nclusters_cmap(self, n_clusters, cmap='tab20b'):
        """Create a colormap with n_clusters colors."""
        return get_nclusters_cmap(self._hdbscan_results, n_clusters, cmap)
    
    # Core UMAP computation methods
    def compute_umap_embedding(self, 
                               min_dist_list=[1., 0.75, 0.5, 0.25],
                               n_neighbors_list=[25, 50, 100, 150], 
                               n_components=2,
                               save=True,
                               file_path=None,
                               folder_params='umap_params/'):
        """Compute UMAP embedding of the image spectra."""
        try:
            # Si data ya es 2D, usarla directamente
            if len(self.data.shape) == 2:
                data_2d = np.array(self.data)
            # Si data es 3D, aplanar las dos primeras dimensiones
            elif len(self.data.shape) == 3:
                data_2d = np.array(self.data).reshape(
                    self.data.shape[0] * self.data.shape[1], 
                    self.data.shape[-1]
                )
            else:
                raise ValueError(f"Unexpected data shape: {self.data.shape}. Expected 2D or 3D.")
        except Exception as e:
            print(f"Data processing error: {e}")
            print(f"Data shape: {self.data.shape}")
            return

        embeddings = []
        umap_data_dict = dict()
        time_lapsed = []
        
        for min_dist in min_dist_list:
            for n_neighbors in n_neighbors_list:
                t0 = time.time()
                mapper = umap.UMAP(min_dist=min_dist,
                                   n_neighbors=n_neighbors, 
                                   n_components=n_components, 
                                   random_state=1)
                embedding = mapper.fit_transform(data_2d)
                embeddings.append(embedding)
                umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)] = mapper
                
                t1 = time.time()
                time_lapsed.append(round(t1 - t0, 2))
                print(f"UMAP embedding with min_dist={min_dist}, n_neighbors={n_neighbors}, took {t1 - t0:.2f} seconds.")

        self.umap_embedding_ = embeddings
        self.umap_shape = (self.data.shape[0], 
                           self.data.shape[1], 
                           n_components)
        self.umap_data_dict = umap_data_dict

        visualize_umap_embedding(min_dist_list, n_neighbors_list, umap_data_dict)

        if save:
            # Crear la carpeta si no existe
            if not os.path.exists(folder_params):
                os.makedirs(folder_params)
            for min_dist in min_dist_list:
                for n_neighbors in n_neighbors_list:
                    data = umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)]
                    file_name = folder_params + 'umap_dict_{}_{}.pkl'.format(min_dist, n_neighbors)
                    print("Umap embedding saved in:", file_name)
                    pickle.dump(data, open(file_name, 'wb'))

        return embeddings, umap_data_dict
    
    def _read_umap_embedding(self, min_dist_list, n_neighbors_list, folder_params):
        """Read UMAP embedding from saved files."""
        umap_data_dict = {}
        
        for min_dist in min_dist_list:
            for n_neighbors in n_neighbors_list:
                file_name = folder_params + 'umap_dict_{}_{}.pkl'.format(min_dist, n_neighbors)
                try:
                    data = pickle.load(open(file_name, 'rb'))
                    umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)] = data
                    print(f"UMAP embedding umap_dict_{min_dist}_{n_neighbors}.pkl loaded from {file_name}.")
                except FileNotFoundError:
                    print(f"File {file_name} not found.")
        
        self.umap_embedding_ = umap_data_dict
        self.umap_shape = (self.data.shape[0],
                           self.data.shape[1],
                           next(iter(umap_data_dict.values())).embedding_.shape[1])
        
        print("UMAP dict loaded successfully.")
        return umap_data_dict
    
    def _visualize_umap_embedding(self, min_dist_list, n_neighbors_list, load=False, 
                                  folder_params=None, umap_data_dict=None):
        """Visualize multiple UMAP embeddings using holoviews/bokeh."""
        if load and folder_params is not None:
            umap_data_dict = self._read_umap_embedding(min_dist_list, n_neighbors_list, folder_params)
        elif load == False and folder_params == None:
            umap_data_dict = self.umap_data_dict
        
        visualize_umap_embedding(min_dist_list, n_neighbors_list, umap_data_dict)
    
    # Core HDBSCAN methods
    def _run_hdbscan_and_plot(self, embedding, spectrum_image, min_samples, min_cluster_size):
        """Ejecuta HDBSCAN, visualiza y retorna resultados."""
        hdbscan_results = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples)
        hdbscan_results.fit(embedding)
        self._hdbscan_results = hdbscan_results
        
        print(f"HDBSCAN values: min_samples = {min_samples} and min_cluster_size = {min_cluster_size}")
        print('Cluster values:', np.unique(hdbscan_results.labels_))

        clustering = hdbscan_results.labels_.reshape(spectrum_image.shape[0], spectrum_image.shape[1])
        n_clusters = len(np.unique(hdbscan_results.labels_))
        cmap_obj = self._get_nclusters_cmap(n_clusters)

        self._plot_hdbscan_map(clustering, cmap_obj)
        self._plot_umap_embedding_with_labels(embedding, hdbscan_results.labels_, cmap_obj, min_samples, min_cluster_size)
        self._plot_mean_spectra_per_cluster(clustering, cmap_obj)
        
        return hdbscan_results, clustering

    def hdbscan_for_umap(self, n_neighbors, min_dist, min_samples=None, min_cluster_size=None):
        """Simplified HDBSCAN clustering and visualization on UMAP embedding."""
        config_dict = {
            'dpi': 500,
            'min_sample_start': 1,
            'min_sample_end': 8,
            'min_cluster_start': 100,
            'min_cluster_end': 900,
            'min_cluster_step': 100
        }

        spectrum_image = self.data
        
        if isinstance(self.umap_embedding_, dict):
            key = f"umap_data_{min_dist}_{n_neighbors}"
            if key not in self.umap_embedding_:
                raise ValueError(f"No UMAP embedding found for n_neighbors={n_neighbors}, min_dist={min_dist}")
            embedding = self.umap_embedding_[key].embedding_
        elif isinstance(self.umap_embedding_, list):
            embedding = self.umap_embedding_[0]
        else:
            embedding = self.umap_embedding_

        if min_samples is not None and min_cluster_size is not None:
            return self._run_hdbscan_and_plot(embedding, spectrum_image, min_samples, min_cluster_size)
        else:
            while True:
                eval_hdb = input("¿Quieres evaluar valores de HDBSCAN? (y/n): ")
                if eval_hdb.lower() == 'y':
                    min_sample_start = config_dict.get('min_sample_start', 1)
                    min_sample_end = config_dict.get('min_sample_end', 8)
                    min_cluster_start = config_dict.get('min_cluster_start', 100)
                    min_cluster_end = config_dict.get('min_cluster_end', 900)
                    min_cluster_step = config_dict.get('min_cluster_step', 100)
                    
                    for i in range(min_sample_start, min_sample_end):
                        for j in range(min_cluster_start, min_cluster_end + 1, min_cluster_step):
                            hdbscan_results = hdbscan.HDBSCAN(min_cluster_size=j, min_samples=i)
                            hdbscan_results.fit(embedding)
                            outliers = np.count_nonzero(hdbscan_results.labels_ == -1)
                            total_points = hdbscan_results.labels_.size
                            print(f"min_samples={i}, min_cluster_size={j}, clusters={len(np.unique(hdbscan_results.labels_))}, outliers={outliers} ({(outliers/total_points)*100:.2f}%)")
                
                min_samp = int(input("Introduce min_samples para HDBSCAN: "))
                min_clust = int(input("Introduce min_cluster_size para HDBSCAN: "))
                res = self._run_hdbscan_and_plot(embedding, spectrum_image, min_samp, min_clust)
                done = input("¿Estás satisfecho con el clustering y quieres terminar? (y/n): ")
                if done.lower() == 'y':
                    return res

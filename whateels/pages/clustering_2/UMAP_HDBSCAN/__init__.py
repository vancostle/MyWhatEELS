# Para reducción de dimensionalidad y clustering

import numpy as np
# np.random.seed(1)

import time
import matplotlib.pyplot as plt
# import numpy as np
import hyperspy.api as hs
from matplotlib.ticker import AutoMinorLocator

import umap
import hdbscan
import pickle
import holoviews as hv
import xarray as xr
from bokeh.io import show

hv.extension('bokeh')

class UMAP_HDBSCAN:
    def __init__(self, data=None, file_path=None):
        self.m = hs.load(file_path) if file_path is not None else data
        self.e_loss = self.m.axes_manager[-1].axis if file_path is not None else self.m[-1]
        self.data = self.m.data if file_path is not None else data
    
    def _plot_hdbscan_map_intensities(self, clustering, channel=None, cmap='cubehelix'):
        """
        Crear mapas ponderados por intensidad para cada cluster usando holoviews/bokeh.
        Si channel=None, usa la suma total del espectro por píxel. Si channel es un índice, usa ese canal.
        Visualiza los mapas con holoviews/bokeh.
        """
        # import holoviews as hv
        # import xarray as xr
        # from bokeh.io import show
        # import numpy as np
        data = self.data
        shape = clustering.shape
        flat_clustering = clustering.reshape(-1)
        if channel is None:
            # Intensidad integrada (suma del espectro)
            intensities = data.sum(axis=-1).reshape(-1)
        else:
            # Intensidad en un canal específico
            intensities = data[..., channel].reshape(-1)
        unique_labels = np.unique(flat_clustering)
        for label in unique_labels:
            if label == -1:
                continue  # Omitir outliers
            mask = (flat_clustering == label)
            intensity_map = np.zeros_like(flat_clustering, dtype=float)
            intensity_map[mask] = intensities[mask]
            intensity_map_2d = intensity_map.reshape(shape)
            
            # Calcular rango de valores solo para píxeles del cluster (no-cero)
            cluster_values = intensity_map[mask]
            if len(cluster_values) > 0:
                vmin = cluster_values.min()
                vmax = cluster_values.max()
            else:
                vmin, vmax = 0, 1
            
            # Crear máscara para píxeles fuera del cluster (poner NaN para que no aparezcan en colorbar)
            intensity_map_2d_masked = intensity_map_2d.copy()
            intensity_map_2d_masked[intensity_map_2d == 0] = np.nan
            
            img = hv.Image(
                xr.Dataset(
                    {f'Intensidad_Cluster_{label}': (['y', 'x'], intensity_map_2d_masked)},
                    coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
                ),
                kdims=['x', 'y']
            ).opts(
                xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
                invert_yaxis=True, aspect='equal', frame_height=300,
                cmap=cmap,
                clim=(vmin, vmax),
                bgcolor='black',
                title=f'Intensidad integrada - Cluster {label}' if channel is None else f'Intensidad canal {channel} - Cluster {label}'
            )
            show(hv.render(img, backend='bokeh'))
            
    def _plot_hdbscan_map_probabilities(self, clustering, hdbscan_results, norm='log' or 'exp'):
        """
        Visualización soft del clustering usando HDBSCAN.
        Muestra un mapa por cluster con la probabilidad de pertenencia por píxel.
        clustering: matriz 2D de labels (shape: [y, x])
        hdbscan_results: objeto HDBSCAN tras ajuste (debe tener .probabilities_)
        cmap_obj: objeto con .colors para los clusters
        """
        probs = hdbscan_results.probabilities_
        labels = hdbscan_results.labels_
        shape = clustering.shape
        probs_2d = probs.reshape(shape)
        labels_2d = labels.reshape(shape)
        
        # Para cada cluster (excepto outlier -1), mostrar mapa de probabilidad
        for idx, label in enumerate(np.unique(labels)):
            if label == -1:
                continue  # Omitir outliers
            mask = (labels_2d == label)
            prob_map = np.zeros_like(probs_2d)
            prob_map[mask] = probs_2d[mask]
            
            if norm == 'log':
                prob_map = np.log1p(prob_map)
            elif norm == 'exp':
                prob_map = np.expm1(prob_map)

            img = hv.Image(
                xr.Dataset(
                    {f'Probabilidad_Cluster_{label}': (['y', 'x'], prob_map)},
                    coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
                ),
                kdims=['x', 'y']
            ).opts(
                xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
                invert_yaxis=True, aspect='equal', frame_height=300,
                title=f'Probabilidad de pertenencia - Cluster {label}',
                cmap = 'cubehelix'
                # logz=True
            )
            show(hv.render(img, backend='bokeh'))

    def plot_cluster_dispersion_histograms(self, clustering=None):
        """
        Para cada cluster, grafica:
        - Histograma de las distancias euclídeas al centroide.
        """
        if clustering is None:
            clustering = self._hdbscan_results.labels_.reshape(self.data.shape[0], self.data.shape[1])

        energy_axis = self.e_loss
        flat_clustering = clustering.reshape(-1)
        flat_spectra = self.data.reshape(-1, energy_axis.size)
        unique_labels = np.unique(flat_clustering)
        
        print(f"Análisis de dispersión para {len(unique_labels)} clusters...\n")
        for idx, label in enumerate(unique_labels):
            cluster_mask = (flat_clustering == label)
            if np.sum(cluster_mask) == 0:
                print(f"Cluster {label} está vacío, se omite.")
                continue
            spectra_cluster = flat_spectra[cluster_mask]
            mean_spectrum = np.mean(spectra_cluster, axis=0)
            dists = np.linalg.norm(spectra_cluster - mean_spectrum, axis=1)
            print(spectra_cluster.shape, mean_spectrum.shape, dists.shape)
            print(f"Cluster {label}: {len(dists)} espectros")
            # Histograma
            plt.figure(figsize=(5, 4))
            plt.hist(dists, bins=30, color='teal', alpha=0.7)
            plt.xlabel('Distancia euclídea al centroide')
            plt.ylabel('Nº de espectros')
            plt.title(f'Cluster {label}: Histograma')
            plt.tight_layout()
            # Guardar el plot
            filename = f"cluster_{label}_histo.png"
            plt.savefig(filename, dpi=300)
            print(f"Histograma guardado en {filename}")
            plt.show()

        print("Todos los análisis de dispersión han sido completados.")

    def cut_signal(self, x1=None, x2=None):
        """Corta la señal en el rango especificado."""
        self._cut = self.m.deepcopy().isig[x1:x2]
        self.m = self._cut
        self.e_loss = self._cut.axes_manager[-1].axis
        self.data = self._cut.data
        print(f"Cutting signal from {x1} to {x2} eV done successfully.")
        return self._cut
    
    def plot_image(self):
        plt.imshow(self.data[...].sum(-1), cmap="gray")
        plt.show()

    def plot_pixel_spectrum(self, pixel):
        spect = self.data[pixel[1], pixel[0]]
        fig, ax = plt.subplots(1,1,figsize=(3.5,2.5))
        plt.plot(self.e_loss, spect, c='dimgrey')
        plt.xlabel('Energy Loss (eV)')
        plt.ylabel('Intensity (counts)')
        plt.tick_params(axis='both', direction="in", which='both', top=True, right=True)
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        plt.tight_layout()
        plt.show()

    def plot_sum_spectrum(self):
        counts = self.data.reshape(
            self.data.shape[0] * self.data.shape[1], self.data.shape[-1]
            ).sum(0)
        fig, ax = plt.subplots(1,1,figsize=(3,2))
        ax.set_xlim(-0.2, 3.8)
        ax.set_ylim(-2E7, 5E8)
        plt.plot(self.e_loss, counts, label='original', color="teal")
        ax.fill_between(self.e_loss, counts, color="teal")
        plt.tick_params(axis='both', direction="in", which='both', top=True, right=True)
        plt.xlabel("Energy Loss (eV)")
        plt.ylabel("Intensity (AU)")
        ax.xaxis.set_minor_locator(AutoMinorLocator(3))
        ax.yaxis.set_minor_locator(AutoMinorLocator(3))
        plt.tight_layout()
        plt.show()

    def compute_umap_embedding(self, 
                               min_dist_list = [1., 0.75, 0.5, 0.25],
                               n_neighbors_list=[25, 50, 100, 150], 
                               n_components=2,
                               save = True,
                               file_path = None,
                               folder_params = 'umap_params/'
                               ):
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

        self._visualize_umap_embedding(min_dist_list, n_neighbors_list, umap_data_dict=umap_data_dict)

        if save:
            import os
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
    
    def _read_umap_embedding(self,
                            min_dist_list,
                            n_neighbors_list, 
                            folder_params):
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
        self.umap_shape = (self.data.shape[0], # type: ignore
                           self.data.shape[1], # type: ignore
                           next(iter(umap_data_dict.values())).embedding_.shape[1]) 
        
        print("UMAP dict loaded successfully.")
        return umap_data_dict

    def _visualize_umap_embedding(self, 
                                  min_dist_list,
                                  n_neighbors_list,
                                  load=False,
                                  folder_params=None,
                                  umap_data_dict=None):
        """Visualize multiple UMAP embeddings using holoviews/bokeh."""
        
        if load and folder_params is not None:
            umap_data_dict = self._read_umap_embedding(min_dist_list, n_neighbors_list, folder_params)
        elif load==False and folder_params==None:
            umap_data_dict = self.umap_data_dict
            
        embeddings_plots = []

        for min_dist in min_dist_list:
            for n_neighbors in n_neighbors_list:
                emb = umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)].embedding_
                zers = np.zeros((emb.shape[0], 3))
                zers[:, : -1] = emb
                points = hv.Points(zers, vdims=['color']).opts(
                    frame_width=650, 
                    frame_height=300, 
                    toolbar=None, 
                    fill_alpha=0.1, 
                    bgcolor='black',
                    line_alpha=0, 
                    line_width=0.15, 
                    size=2.5, 
                    xaxis=None, 
                    yaxis=None,
                    show_legend=True, 
                    color='color', 
                    shared_axes=False,
                    title=('UMAP on masked data, min_dist={}, n_neighbors={}'.format(min_dist, n_neighbors))
                )
                embeddings_plots.append(points)
                
        layout = hv.Layout(embeddings_plots).cols(len(n_neighbors_list))
        show(hv.render(layout, backend='bokeh'))
        print("UMAP embeddings visualized successfully.")
    
    def _run_hdbscan_and_plot(self, embedding, spectrum_image, min_samples, min_cluster_size):
        """
        Ejecuta HDBSCAN, visualiza y retorna resultados.
        """
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
        """
        Simplified HDBSCAN clustering and visualization on UMAP embedding, following class logic.
        """
        config_dict = {'dpi': 500,
                      'min_sample_start': 1,
                      'min_sample_end': 8,
                      'min_cluster_start': 100,
                      'min_cluster_end': 900,
                      'min_cluster_step': 100}

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

    def _plot_hdbscan_map(self, clustering, cmap_obj):
        img = hv.Image(
            xr.Dataset(
                {'Labels':( ['y','x'], clustering)},
                coords = {'x':np.arange(self.data.shape[1]),
                          'y':np.arange(self.data.shape[0])}
                ),
                kdims = ['x','y']
                ).opts(
            xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
            invert_yaxis=True, aspect='equal', frame_height=300, cmap=cmap_obj.colors,
            title='HDBSCAN map')
        show(hv.render(img, backend='bokeh'))

    def _plot_umap_embedding_with_labels(self, embedding, labels, cmap_obj, min_samp, min_clust):
        zers = np.zeros((embedding.shape[0], 3))
        zers[:, :-1] = embedding
        zers[:, -1] = labels
        points = hv.Points(zers, vdims=['color']).opts(
            frame_width=650, frame_height=300, toolbar='right', fill_alpha=0.1, bgcolor='black',
            line_alpha=0, line_width=0.15, size=2.5, xaxis=None, yaxis=None, cmap=cmap_obj.colors,
            show_legend=True, color='color', shared_axes=False,
            title=f'UMAP embedding min_samples={min_samp}, min_cluster_size={min_clust}')
        show(hv.render(points, backend='bokeh'))

    def _plot_mean_spectra_per_cluster(self, clustering, cmap_obj):
        """
        Plot the mean spectrum for each cluster as colored curves.
        """
        energy_axis = self.e_loss
        mean_spectra_overlay = {}
        flat_clustering = clustering.reshape(-1)
        flat_spectra = self.data.reshape(-1, energy_axis.size) 
        print('Shapes: flat_clustering', flat_clustering.shape, 'flat_spectra', flat_spectra.shape)
        unique_labels = np.unique(flat_clustering)
        
        for idx, label in enumerate(unique_labels):
            cluster_mask = (flat_clustering == label)
            spectra_cluster = flat_spectra[cluster_mask]
            mean_spectrum = np.mean(spectra_cluster, axis=0)
            curve = hv.Curve(
                (energy_axis, mean_spectrum), 
                'Eloss', 
                f'Intensity (Label {label})'
                ).opts(color=cmap_obj.colors[idx])
            mean_spectra_overlay[f'Label_{label}'] = curve

        overlay = hv.NdOverlay(mean_spectra_overlay).opts(
            frame_height=300, 
            frame_width=650, 
            bgcolor='black', 
            legend_cols=False,
            legend_position='right', 
            show_grid=True, 
            ylabel='Intensity (counts)', 
            xlabel='Energy Loss (eV)',
            title='Centroids of HDBSCAN on the UMAP embedding',
            hooks=[self._add_wavelength_axis]
        )
        show(hv.render(overlay, backend='bokeh'))
    
    def _add_wavelength_axis(self, plot, element):
        """
        Hook para añadir un eje superior con valores de wavelength (1240/eV).
        Se usa FuncTickFormatter para calcular las etiquetas en nm a partir de eV,
        manejando divisiones por cero y valores no finitos.
        """
        from bokeh.models import LinearAxis, FuncTickFormatter

        fig = plot.state

        # Formatter JS: calcula 1240 / tick, evita division por cero y valores no finitos.
        fmt = FuncTickFormatter(code="""
            // tick es el valor en la escala del eje (eV)
            if (!isFinite(tick) || tick === 0) { return ""; }
            var nm = 1240.0 / tick;
            if (!isFinite(nm)) { return ""; }
            // Ajusta formato según magnitud (sin decimales por defecto)
            return nm.toFixed(0);
        """)

        axis = LinearAxis(axis_label='Wavelength (nm)', formatter=fmt)
        fig.add_layout(axis, 'above')
        
    def _get_nclusters_cmap(self, n_clusters, cmap='tab20b'):
        """
        Create a colormap with n_clusters colors based on a colormap with 20 colors, such as 'tab20b'.
        Returns a dict con .colors en formato hexadecimal para Bokeh/Holoviews.
        """
        import matplotlib.colors as mcolors
        original_cmap = plt.cm.get_cmap(cmap)
        hex_colors = []
        # Obtener las labels presentes en el clustering actual
        labels = getattr(self._hdbscan_results, 'labels_', None)
        if labels is not None and -1 in np.unique(labels):
            # Si hay outlier, el primer color es lightgray
            hex_colors.append('lightgray')
            n_valid = n_clusters - 1
        else:
            n_valid = n_clusters
        if n_valid > 0:
            indices = np.linspace(0, 19, n_valid, dtype=int)
            colors = [original_cmap(i) for i in indices]
            hex_colors.extend([mcolors.to_hex(c) for c in colors])
        class CmapObj:
            pass
        cmap_obj = CmapObj()
        cmap_obj.colors = hex_colors
        return cmap_obj

    def _get_cmap(self, cmap='cubehelix', n_colors=256):
        """
        Devuelve un objeto con una lista de colores hexadecimales generada con matplotlib.colors,
        compatible con Holoviews/Bokeh para mapas continuos (por ejemplo, cubehelix).
        """
        import matplotlib.colors as mcolors
        import matplotlib.pyplot as plt
        original_cmap = plt.cm.get_cmap(cmap, n_colors)
        hex_colors = [mcolors.to_hex(original_cmap(i)) for i in range(original_cmap.N)]
        class CmapObj:
            pass
        cmap_obj = CmapObj()
        cmap_obj.colors = hex_colors
        return cmap_obj

    def _get_tinted_grey_cmap(self, tint_color='blue', n_colors=256, reverse=False):
        """
        Genera un colormap recorriendo la luminosidad del color tintado.
        Mantiene el tono (hue) y saturación constantes, variando solo la luminosidad.

        Parámetros:
        - tint_color: str o tupla RGB (0-1) o hex, color para tintar la escala.
        - n_colors: int, número de colores a generar (por defecto 256).
        - reverse: bool, si True invierte el gradiente (tint_color -> negro).

        Devuelve:
        Un objeto con atributos:
        - colors: lista de strings hex ('#rrggbb') compatible con Holoviews/Bokeh
        - cmap: matplotlib.colors.Colormap (LinearSegmentedColormap)
        """
        import matplotlib.colors as mcolors
        from matplotlib.colors import LinearSegmentedColormap
        import colorsys

        # Normalizar y convertir tint_color a RGB
        try:
            rgb = mcolors.to_rgb(tint_color)
        except Exception:
            # Asumir que es una tupla ya en formato RGB
            rgb = tuple(tint_color)

        # Convertir RGB a HLS (Hue, Lightness, Saturation)
        h, l, s = colorsys.rgb_to_hls(*rgb)
        
        # Generar gradiente variando solo la luminosidad desde 0 (negro) hasta l (color original)
        colors_list = []
        luminosities = np.linspace(0, l, n_colors)
        
        if reverse:
            luminosities = luminosities[::-1]
        
        for lum in luminosities:
            # Mantener hue y saturación constantes, variar solo luminosidad
            rgb_varied = colorsys.hls_to_rgb(h, lum, s)
            colors_list.append(rgb_varied)
        
        cmap = LinearSegmentedColormap.from_list('tinted_grey', colors_list, N=n_colors)

        # Convertir a hex para compatibilidad con Holoviews/Bokeh
        hex_colors = [mcolors.to_hex(colors_list[i]) for i in range(n_colors)]

        class CmapObj:
            pass

        cmap_obj = CmapObj()
        cmap_obj.colors = hex_colors
        cmap_obj.cmap = cmap
        return cmap_obj

    def plot_clusters_overlay(self, clustering=None, labels=None, colors=None, channel=None,
                              max_labels=6, frame_height=300, frame_width=650,
                              colorbar_width=90, colorbar_spacing=0, colorbar_position='right',
                              colorbar_side='left'):
        """
        Superpone varios mapas de intensidad (uno por cluster) en un único plot con estilo
        consistente con los demás plots del core (bgcolor negro, invert_yaxis, aspect='equal').

        Parámetros:
        - clustering: matriz 2D de labels. Si None, toma self._hdbscan_results.labels_.
        - labels: lista de labels a plotear (sin incluir -1). Si None, toma los primeros `max_labels`.
        - colors: lista de colores (hex/nombre) para tintar cada cluster. Si None, usa una paleta por defecto.
        - channel: índice de canal para usar en lugar de la suma integrada. Si None usa suma total.
        - max_labels: número máximo de clu  sters a superponer.
        - frame_height/frame_width: tamaño del plot.
        - colorbar_width: ancho (px) del mini-plot invisible que contiene el colorbar.
        - colorbar_spacing: espacio (px) arriba/abajo de cada barra en la columna (admite negativos para compactar).
        - colorbar_position: posición de la barra ('right'|'left'|'top'|'bottom').
        - colorbar_side: dónde colocar la columna de barras respecto al overlay ('left'|'right').
        """
        # Obtener clustering
        if clustering is None:
            if not hasattr(self, '_hdbscan_results') or self._hdbscan_results is None:
                raise ValueError("No clustering provided and self._hdbscan_results is missing.")
            clustering = self._hdbscan_results.labels_.reshape(self.data.shape[0], self.data.shape[1])

        # Intensidad
        if channel is None:
            intensity_map = self.data.sum(axis=-1)
        else:
            intensity_map = self.data[..., channel]

        # Labels a mostrar
        unique = [lab for lab in np.unique(clustering) if lab != -1]
        if labels is None:
            labels = unique[:max_labels]
        else:
            labels = [lab for lab in labels if lab in unique][:max_labels]

        # Colores por defecto si no se pasan
        if colors is None:
            colors = ["#FFFAF9", "#FFFEFB", "#FAF4FF", "#F3F6FF", "#7AC4B8", "#F3E8F0"]
        # Asegurar que hay suficientes colores
        if len(colors) < len(labels):
            colors = (colors * ((len(labels) // len(colors)) + 1))[:len(labels)]

        layers = []
        colorbars = []  # un colorbar por cluster
        shape = clustering.shape
        
        # Hook para hacer transparente el fondo y el borde del mini-plot del colorbar
        def _transparent_bg(plot, element):
            p = plot.state
            try:
                p.background_fill_alpha = 0
                p.border_fill_alpha = 0
                p.outline_line_alpha = 0
                p.min_border = 0
                p.min_border_top = 0
                p.min_border_bottom = 0
                p.min_border_left = 0
                p.min_border_right = 0
                p.toolbar_location = None
            except Exception:
                pass
        for lab, col in zip(labels, colors):
            mask = (clustering == lab)
            if not np.any(mask):
                continue
            arr = np.where(mask, intensity_map, np.nan)

            # generar cmap tintado compatible con Holoviews/Bokeh
            try:
                cmap = self._get_tinted_grey_cmap(col).colors
            except Exception:
                cmap = col

            # clim sólo con valores del cluster
            valid = arr[np.isfinite(arr)]
            if valid.size > 0:
                clim = (np.nanmin(valid), np.nanmax(valid))
            else:
                clim = (0, 1)

            img = hv.Image(
                xr.Dataset(
                    {f'Cluster_{lab}': (['y', 'x'], arr)},
                    coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
                ),
                kdims=['x', 'y']
            ).opts(
                xaxis=None, yaxis=None, colorbar=False, toolbar='right',
                invert_yaxis=True, aspect='equal', frame_height=frame_height, frame_width=frame_width,
                cmap=cmap, clim=clim, bgcolor='black'
            ).relabel(f"cluster {lab}")

            layers.append(img)

            # Crear un colorbar específico para este cluster usando un HeatMap invisible
            cbar = hv.HeatMap([(0, 0, clim[0]), (0, 1, clim[1])]).opts(
                cmap=cmap,
                clim=clim,
                colorbar=True,
                colorbar_position=colorbar_position,
                colorbar_opts={'title': f'cluster {lab}', 'orientation': 'vertical'},
                xaxis=None,
                yaxis=None,
                show_frame=False,
                alpha=0,              # hacer el heatmap invisible y dejar solo la barra
                frame_height=frame_height,
                frame_width=0,
                toolbar='disable',
                margin=(colorbar_spacing, 0, colorbar_spacing, 0),  # usa negativo para compactar más
                padding=0,
                hooks=[_transparent_bg],
                shared_axes=False,
                axiswise=True,
            )
            colorbars.append(cbar)

        if not layers:
            raise RuntimeError("No hay capas para plotear (posibles labels vacíos).")

        overlay = hv.Overlay(layers).opts(shared_axes=True)

        # Disponer los colorbars en una columna fija usando bokeh layouts
        if colorbars:
            from bokeh.layouts import row, column
            overlay_fig = hv.render(overlay, backend='bokeh')
            cbar_figs = [hv.render(cb, backend='bokeh') for cb in colorbars]
            cbar_column = row(*cbar_figs, sizing_mode='fixed')
            if str(colorbar_side).lower() == 'right':
                layout = row(cbar_column, overlay_fig)
            else:
                layout = row(overlay_fig, cbar_column)
            show(layout)
        else:
            show(hv.render(overlay, backend='bokeh'))

    def save_centroids(self, clustering, filename="centroids.npy"):
        """
        Calcula y guarda los centroides y las posiciones de los píxeles 
        pertenecientes a cada cluster HDBSCAN.

        Parameters
        ----------
        clustering : ndarray (H, W)
            Mapa de etiquetas del clustering.
        filename : str
            Archivo donde guardar los datos (*.npy).

        Returns
        -------
        result : dict
            Diccionario {label: {"centroid": array, "positions": array}}
        """

        energy_axis = self.e_loss
        H, W = clustering.shape

        # Flatten para extracción
        flat_labels  = clustering.reshape(-1)
        flat_spectra = self.data.reshape(-1, energy_axis.size)

        # Coordenadas de todos los píxeles
        ys, xs = np.indices((H, W))
        flat_pos = np.column_stack([ys.reshape(-1), xs.reshape(-1)])

        unique_labels = np.unique(flat_labels)

        result = {}

        for label in unique_labels:
            mask = (flat_labels == label)

            # centroid
            spectra_cluster = flat_spectra[mask]
            centroid = spectra_cluster.mean(axis=0)

            # posiciones (y, x) en la imagen original
            positions = flat_pos[mask]

            result[label] = {
                "centroid": centroid,
                "positions": positions
            }

        # Guardar como diccionario numpy
        np.save(filename, result)
        print(f"Centroides y posiciones guardados en '{filename}'")

        return result

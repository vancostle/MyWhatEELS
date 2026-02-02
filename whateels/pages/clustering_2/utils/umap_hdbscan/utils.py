"""Utility functions for UMAP_HDBSCAN analysis."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


def cut_signal(data, e_loss, x1=None, x2=None):
    """
    Corta la señal en el rango especificado.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    e_loss : np.ndarray
        Energy loss axis
    x1 : float, optional
        Start energy
    x2 : float, optional
        End energy
        
    Returns:
    --------
    tuple : (data_cut, e_loss_cut)
    """
    # Find indices corresponding to x1 and x2 in e_loss
    if x1 is not None:
        idx1 = np.argmin(np.abs(e_loss - x1))
    else:
        idx1 = 0
    
    if x2 is not None:
        idx2 = np.argmin(np.abs(e_loss - x2))
    else:
        idx2 = len(e_loss)
    
    # Slice data and energy axis
    data_cut = data[..., idx1:idx2]
    e_loss_cut = e_loss[idx1:idx2]
    
    print(f"Cutting signal from {x1} to {x2} eV done successfully.")
    return data_cut, e_loss_cut


def plot_image(data):
    """
    Plot summed image from 3D spectral data.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    """
    plt.imshow(data[...].sum(-1), cmap="gray")
    plt.show()


def plot_pixel_spectrum(data, e_loss, pixel):
    """
    Plot spectrum from a single pixel.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    e_loss : np.ndarray
        Energy loss axis
    pixel : tuple
        (x, y) coordinates
    """
    spect = data[pixel[1], pixel[0]]
    fig, ax = plt.subplots(1, 1, figsize=(3.5, 2.5))
    plt.plot(e_loss, spect, c='dimgrey')
    plt.xlabel('Energy Loss (eV)')
    plt.ylabel('Intensity (counts)')
    plt.tick_params(axis='both', direction="in", which='both', top=True, right=True)
    ax.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    plt.tight_layout()
    plt.show()


def plot_sum_spectrum(data, e_loss):
    """
    Plot sum spectrum from all pixels.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    e_loss : np.ndarray
        Energy loss axis
    """
    counts = data.reshape(
        data.shape[0] * data.shape[1], data.shape[-1]
    ).sum(0)
    
    fig, ax = plt.subplots(1, 1, figsize=(3, 2))
    ax.set_xlim(-0.2, 3.8)
    ax.set_ylim(-2E7, 5E8)
    plt.plot(e_loss, counts, label='original', color="teal")
    ax.fill_between(e_loss, counts, color="teal")
    plt.tick_params(axis='both', direction="in", which='both', top=True, right=True)
    plt.xlabel("Energy Loss (eV)")
    plt.ylabel("Intensity (AU)")
    ax.xaxis.set_minor_locator(AutoMinorLocator(3))
    ax.yaxis.set_minor_locator(AutoMinorLocator(3))
    plt.tight_layout()
    plt.show()


def plot_cluster_dispersion_histograms(data, e_loss, clustering):
    """
    Para cada cluster, grafica histograma de las distancias euclídeas al centroide.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    e_loss : np.ndarray
        Energy loss axis
    clustering : np.ndarray
        2D cluster labels
    """
    energy_axis = e_loss
    flat_clustering = clustering.reshape(-1)
    flat_spectra = data.reshape(-1, energy_axis.size)
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


def save_centroids(data, e_loss, clustering, filename="centroids.npy"):
    """
    Calcula y guarda los centroides y las posiciones de los píxeles 
    pertenecientes a cada cluster HDBSCAN.

    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    e_loss : np.ndarray
        Energy loss axis
    clustering : np.ndarray
        2D cluster labels (H, W)
    filename : str
        Output filename

    Returns:
    --------
    dict : {label: {"centroid": array, "positions": array}}
    """
    energy_axis = e_loss
    H, W = clustering.shape

    # Flatten para extracción
    flat_labels = clustering.reshape(-1)
    flat_spectra = data.reshape(-1, energy_axis.size)

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
    np.save(filename, result, allow_pickle=True)
    print(f"Centroides y posiciones guardados en '{filename}'")

    return result

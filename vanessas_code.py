from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans

def kmeans_clustering(matrix, n_cluster, norma='l2'):
    '''
    Función que aplica kmeans clustering en la imagen de espectros.
    
    Parameters:
    -----------
    matrix: numpy array. (x,y,eloss)
        Imagen de espectros.
    n_cluster: int.
        Número de clusters.
    norma: string, optional. (default='l2')
        Normalización que queremos aplicar. Opciones: ‘l1’, ‘l2’, ‘max’, 'None'.
        
    Returns:
    --------
    labels: numpy array. (x,y)
        Matriz con las etiquetas de cada cluster. 
    centres: numpy array. (n_cluster,eloss)
        Matriz que contiene los centroides de cada cluster identificado (estos centroides provienen de los espectros normalizados). 
    '''
    allowed_norms = ['l1', 'l2', 'max', None]
    if norma not in allowed_norms:
        raise ValueError(f"norma debe ser uno de {allowed_norms}")
        
    matrix_norm = matrix.copy()
    matrix_norm = matrix_norm.reshape(matrix.shape[0]*matrix.shape[1], matrix.shape[-1])
    if norma is None: 
        sclust_norm = matrix_norm
    else:
        sclust_norm, _ = normalize(matrix_norm,norm=norma,axis=1,return_norm=True)
    kmeans = KMeans(n_clusters=n_cluster, tol=1e-9, max_iter=700, random_state=13)
    fitted = kmeans.fit(sclust_norm)
    centres = fitted.cluster_centers_
    labels = fitted.labels_.reshape(matrix.shape[:-1])
    return labels, centres


labels, centres = kmeans_clustering(matrix=m_tallat.data, n_cluster=6, norma='l2')


unique_values = np.unique(labels)

cmap = plt.get_cmap('viridis_r')


from matplotlib.colors import BoundaryNorm

norm = BoundaryNorm(boundaries=unique_values, ncolors=cmap.N)


%matplotlib inline
from matplotlib.colors import BoundaryNorm
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar

unique_values = np.unique(labels)
boundaries = np.append(unique_values, unique_values[-1] + 1)

cmap = plt.get_cmap('viridis_r')
norm = BoundaryNorm(boundaries=boundaries, ncolors=cmap.N)

fig, ax = plt.subplots(1,1,figsize=(4,2))
plt.imshow(labels, cmap=cmap, norm=norm)
plt.xticks([])
plt.yticks([])
scalebar = AnchoredSizeBar(ax.transData,
                           px_scale, '100 nm', 'lower right', label_top=True,
                           color='white',
                           frameon=False,
                           size_vertical=0.01)
ax.add_artist(scalebar)
plt.colorbar(ticks=unique_values, orientation='horizontal')
plt.show()

from matplotlib.ticker import AutoMinorLocator

fig, ax = plt.subplots(1,1,figsize=(3.5,2))
for i in range(0,len(centres)):
    plt.plot(m_tallat.axes_manager[-1].axis, centres[i], 
             color=listed_colormap(i / len(centres)), label=str(i))
plt.xlabel('Energy Loss (eV)')
plt.ylabel('Intensity (AU)')
plt.tick_params(axis='both', direction="in", which='both', top=True, right=True)
ax.xaxis.set_minor_locator(AutoMinorLocator(4))
ax.yaxis.set_minor_locator(AutoMinorLocator(2))
plt.legend()
plt.xlim([0.3, 3.9])
plt.ylim([0, 0.07])
plt.tight_layout()
plt.show()
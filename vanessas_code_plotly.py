import numpy as np
import plotly.graph_objects as go
from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans

def kmeans_clustering(matrix, n_cluster, norma='l2'):
    '''
    Same as original: applies kmeans clustering to a 3D spectrum image.
    '''
    allowed_norms = ['l1', 'l2', 'max', None]
    if norma not in allowed_norms:
        raise ValueError(f"norma debe ser uno de {allowed_norms}")
    matrix_norm = matrix.copy()
    matrix_norm = matrix_norm.reshape(matrix.shape[0]*matrix.shape[1], matrix.shape[-1])
    if norma is None:
        sclust_norm = matrix_norm
    else:
        sclust_norm, _ = normalize(matrix_norm, norm=norma, axis=1, return_norm=True)
    kmeans = KMeans(n_clusters=n_cluster, tol=1e-9, max_iter=700, random_state=13)
    fitted = kmeans.fit(sclust_norm)
    centres = fitted.cluster_centers_
    labels = fitted.labels_.reshape(matrix.shape[:-1])
    return labels, centres

# Example usage (replace m_tallat.data with your data):
# labels, centres = kmeans_clustering(matrix=m_tallat.data, n_cluster=6, norma='l2')

def plot_kmeans_labels_plotly(labels, title="KMeans Clustering Labels", colorscale="Viridis"):
    """
    Plot the clustering labels using Plotly for interactive visualization.
    labels: 2D numpy array (x, y)
    """
    fig = go.Figure(go.Heatmap(z=labels, colorscale=colorscale, colorbar=dict(title="Cluster")))
    fig.update_layout(title=title, xaxis_title="X", yaxis_title="Y", yaxis_autorange='reversed')
    fig.show()

# Example usage (replace m_tallat.data with your data):
# labels, centres = kmeans_clustering(matrix=m_tallat.data, n_cluster=6, norma='l2')
# plot_kmeans_labels_plotly(labels)

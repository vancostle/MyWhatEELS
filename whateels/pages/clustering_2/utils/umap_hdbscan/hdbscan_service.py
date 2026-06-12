import numpy as np
import hdbscan

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt


class HDBSCANService:
    """Encapsulates HDBSCAN-related clustering and evaluation logic."""

    def compute_hdbscan_on_umap(self, umap_embedding, min_samples, min_cluster_size):
        """Compute HDBSCAN clustering on the provided UMAP embedding."""
        hdbscan_results = hdbscan.HDBSCAN(
            min_samples=min_samples,
            min_cluster_size=min_cluster_size,
        ).fit(umap_embedding)
        return hdbscan_results

    def get_nclusters_cmap(self, hdbscan_results, n_clusters, cmap='tab20b'):
        """Create hex colormap values for cluster visualization."""
        original_cmap = plt.cm.get_cmap(cmap)
        hex_colors = []

        labels = getattr(hdbscan_results, 'labels_', None)
        if labels is not None and -1 in np.unique(labels):
            hex_colors.append('lightgray')
            n_valid = n_clusters - 1
        else:
            n_valid = n_clusters

        if n_valid > 0:
            indices = np.linspace(0, 19, n_valid, dtype=int)
            colors = [original_cmap(i) for i in indices]
            hex_colors.extend([mcolors.to_hex(c) for c in colors])

        return {"colors": hex_colors}

    def evaluate_hdbscan(
        self,
        embedding,
        min_samples_min: int = 1,
        min_samples_max: int = 8,
        min_cluster_size_min: int = 100,
        min_cluster_size_max: int = 900,
        step: int = 100,
    ) -> list[tuple[int, int, int, int, float]]:
        """Evaluate HDBSCAN over a configurable min_samples/min_cluster_size grid."""
        min_sample_start = max(1, int(min_samples_min))
        min_sample_end = max(min_sample_start, int(min_samples_max))
        min_cluster_start = max(1, int(min_cluster_size_min))
        min_cluster_end = max(min_cluster_start, int(min_cluster_size_max))
        min_cluster_step = max(1, int(step))

        data = []

        min_sample_values = list(range(min_sample_start, min_sample_end + 1))
        min_cluster_values = list(range(min_cluster_start, min_cluster_end + 1, min_cluster_step))

        for i in min_sample_values:
            for j in min_cluster_values:
                hdbscan_results = hdbscan.HDBSCAN(min_cluster_size=j, min_samples=i)
                hdbscan_results.fit(embedding)
                outliers = np.count_nonzero(hdbscan_results.labels_ == -1)
                total_points = hdbscan_results.labels_.size
                data.append((i, j, len(np.unique(hdbscan_results.labels_)), outliers, (outliers / total_points) * 100))

        return data
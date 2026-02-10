
import copy, numpy as np, umap, hdbscan
from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from xarray import DataArray
    
class UMAP_HDBSCAN:
    
    def __init__(self, electron_count_data : "DataArray"):
        
        self._electron_count_data = copy.deepcopy(electron_count_data) # Deep copy to avoid modifying original data
        self._eloss = self._electron_count_data.coords["Eloss"].values
    
    def cut_signal(self, min_eloss, max_eloss) -> bool:
        """Cuts the signal range based on min and max eloss values."""
        try:
            self._electron_count_data = self._electron_count_data.sel(Eloss=slice(min_eloss, max_eloss)) # Overwrite data with cut signal range
            self._eloss = self._electron_count_data.coords["Eloss"].values # Update eloss values accordingly
            return True
        except Exception:
            return False
        
    def compute_umap_embedding(
        self,
        min_dist : float = 0.1,
        n_neighbors : int = 15,
        n_components : int = 2,
        metric : str = 'euclidean',
        random_state : int = 1
        
    ) -> tuple[Any, dict]:
        """ Compute UMAP embedding of the image spectra image. """
        data_2d = self._get_reshaped_data()
        
        mapper = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=n_components,
            random_state=random_state,
            metric=metric
        )
        embedding = mapper.fit_transform(data_2d)
        
        umap_data_dict = dict()
        umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)] = mapper
        
        return embedding, umap_data_dict

    def _get_reshaped_data(self) -> Optional[np.ndarray]:
        """Reshape electron count data to 2D array for UMAP processing."""
        try:
            shape = self._electron_count_data.shape
            if len(shape) == 2:
                return np.array(self._electron_count_data)
            elif len(shape) == 3:
                n_y, n_x, n_eloss = shape
                return np.array(self._electron_count_data).reshape(n_y * n_x, n_eloss)
            else:
                raise ValueError("Electron count data must be 2D or 3D.")
        except Exception as e:
            print(f"Error processing electron count data: {e}")
            return None
        
        
    def compute_hdbscan_on_umap(self, umap_embedding, min_samples, min_cluster_size):
        """Compute HDBSCAN clustering on the provided UMAP embedding."""
        
        print(f"Computing HDBSCAN with min_samples={min_samples} and min_cluster_size={min_cluster_size}...")
        hdbscan_results = hdbscan.HDBSCAN(
            min_samples=min_samples,
            min_cluster_size=min_cluster_size
        ).fit(umap_embedding)
        
        return hdbscan_results        

        
    # def hdbscan_for_umap(self, umap_data_dict : dict, n_neighbors, min_dist, min_samples=None, min_cluster_size=None):
    #     """
    #         Simplified HDBSCAn clustering and visualization on UMAP embedding, following class logic.
    #     """
        
    #     config_dict = {
    #         'dpi': 500,
    #         'min_smaple_start': 1,
    #         'min_sample_end': 8,
    #         'min_cluster_start': 100,
    #         'min_cluster_end': 900,
    #         'min_cluster_step': 100
    #     }
        
    #     spectrum_image = self._electron_count_data
        
    #     if isinstance(umap_data_dict, dict):
    #         key = f'umap_data_{min_dist}_{n_neighbors}'
    #         if key not in umap_data_dict:
    #             raise ValueError(f"UMAP data for min_dist={min_dist} and n_neighbors={n_neighbors} not found in the provided dictionary.")
    #         embedding = umap_data_dict[key].embedding_
    #     elif isinstance(umap_data_dict, list):
    #         embedding = umap_data_dict[0]
    #     else:
    #         embedding = umap_data_dict
            
    #     print("----------------------- HDBSCAN clustering would be performed here with the following parameters:")
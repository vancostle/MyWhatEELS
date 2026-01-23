
import copy, numpy as np, time, umap, pickle
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
    ) -> tuple[Any, dict]:
        """ Compute UMAP embedding of the image spectra image. """
        
        RANDOM_STATE = 1

        data_2d = self._get_reshaped_data()
        
        mapper = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=n_components,
            random_state=RANDOM_STATE,
        )
        embedding = mapper.fit_transform(data_2d)
        
        umap_data_dict = dict()
        umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)] = mapper
        
        print(f"UMAP computed for min_dist={min_dist}, n_neighbors={n_neighbors} successfully.")
        
        return embedding, umap_data_dict
    
    # TODO: think if this method is necessary and if it is not, delete it
    def compute_all_umaps_embedding(
        self,
        min_dist_list : list[float] = [0.1, 0.5, 0.9],
        n_neighbors_list : list[int] = [5, 15, 50],
        n_components : int = 2,
    ):
        """ Compute UMAP embeddings for all combinations of min_dist and n_neighbors. """
        RANDOM_STATE = 1

        data_2d = self._get_reshaped_data()
        if data_2d is None:
            return
        
        embeddings = []
        umap_data_dict = dict()
        time_lapsed = 0

        for min_dist in min_dist_list:
            for n_neighbor in n_neighbors_list:
                t0 = time.time()
                mapper = umap.UMAP(
                    n_neighbors=n_neighbor,
                    min_dist=min_dist,
                    n_components=n_components,
                    random_state=RANDOM_STATE,
                )
                embedding = mapper.fit_transform(data_2d)
                embeddings.append(embedding)
                
                umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbor)] = mapper
                
                t1 = time.time()
                time_lapsed = round(t1 - t0, 2)
                print(f"UMAP computed for min_dist={min_dist}, n_neighbors={n_neighbor} in {time_lapsed} seconds.")

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
        
    def _visulize_umap_embedding(
        self,
        min_dist : float,
        n_neighbors : int,
        umap_data_dict : dict,
    ):
        """ Visualize UMAP embedding (to be implemented). """
        pass
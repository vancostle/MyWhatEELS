import numpy as np
import plotly.graph_objs as go
import os
from typing import Tuple, Optional

# Try to import xarray if available; otherwise operate in numpy-only mode
try:
    import xarray as xr
    _HAS_XARRAY = True
except Exception:
    xr = None
    _HAS_XARRAY = False

def multifit_modified(data, model, Eloss_x=None, fit_range=None, progress_every=1000):
    """
    Pixel-wise multifit using lmfit models with basic masking.

    Parameters:
      data (np.ndarray): 3D array (dimx, dimy, spectrum_length)
      model: lmfit model instance or class
      Eloss_x (array-like): 1D energy-loss axis
      fit_range (tuple or None): (xmin, xmax) to restrict fitting range (in same units as Eloss_x)
      progress_every (int): print progress every N fits (0 to disable)
      
    Returns:
      List of fit result objects (or None for skipped pixels)
    """
    import numpy as _np
    from inspect import isclass as _isclass

    data_arr = _np.asarray(data)
    if data_arr.ndim != 3:
        raise ValueError("data must be a 3D array shaped (dimx, dimy, spectrum_length).")
    dimx, dimy, spectrum_length = data_arr.shape

    # Determine energy loss axis
    if Eloss_x is None:
        try:
            Eloss_x = data.Eloss_x  # Custom attribute if set
        except AttributeError:
            raise ValueError("Please provide the energy loss axis (Eloss_x) as a separate argument or attribute.")

    x = _np.asarray(Eloss_x)
    if x.ndim != 1:
        raise ValueError("Eloss_x must be a 1D array.")
    if x.size != spectrum_length:
        raise ValueError("Eloss_x length must match the third dimension of data.")

    # Build x mask: finite and > 0 to avoid log issues; apply range if provided
    mask_x = _np.isfinite(x) & (x > 0)
    if fit_range is not None:
        xmin, xmax = fit_range
        mask_x &= (x >= float(xmin)) & (x <= float(xmax))

    # Normalize model to an instance
    model_instance = model() if _isclass(model) else model

    results = []
    progress = 0
    for i in range(dimx):
        for j in range(dimy):
            y = _np.asarray(data_arr[i, j, :])
            # Per-spectrum mask: finite and > 0 for y in addition to mask_x
            mask = mask_x & _np.isfinite(y) & (y > 0)
            if _np.count_nonzero(mask) < 3:
                results.append(None)
            else:
                x_fit = x[mask]
                y_fit = y[mask]
                pars = model_instance.guess(y_fit, x=x_fit)
                res = model_instance.fit(data=y_fit, params=pars, x=x_fit)
                
                # Evaluate the fitted model on the FULL energy axis
                # so that best_fit_full has the same length as the original spectrum
                try:
                    # Evaluate model with optimized params on full valid x range (x>0)
                    x_valid_mask = _np.isfinite(x) & (x > 0)
                    x_valid = x[x_valid_mask]
                    best_fit_full = _np.zeros(spectrum_length)
                    best_fit_full[x_valid_mask] = res.eval(params=res.params, x=x_valid)
                    # Store the full-spectrum fit in a custom attribute
                    res.best_fit_full = best_fit_full
                except Exception:
                    # Fallback: just keep original res.best_fit (subset)
                    res.best_fit_full = None
                
                results.append(res)

            progress += 1
            if progress_every and (progress % progress_every == 0):
                print(f"  Processed {progress}/{dimx*dimy} pixels")

    return results

def create_data_from_multifit(results, original_data, mode='subtracted'):
    """
    Create a 3D numpy array from multifit results.
    
    Parameters:
    - results: List of fit result objects from multifit_modified.
    - original_data: Original 3D numpy array (dimx, dimy, spectrum_length).
    - mode: 'subtracted' (default) returns original - fit (background removal)
            'fitted' returns the fit itself
            'original' returns original data unchanged
    
    Returns:
    - processed_data: 3D numpy array with processed spectra according to mode.
    """
    dimx, dimy, spectrum_length = original_data.shape
    processed_data = np.zeros((dimx, dimy, spectrum_length))
    
    index = 0
    for x_i in range(dimx):
        for y_i in range(dimy):
            res = results[index]
            if res is not None:
                try:
                    # Try to use best_fit_full (full spectrum) first
                    if hasattr(res, 'best_fit_full') and res.best_fit_full is not None:
                        fit_spectrum = res.best_fit_full
                        original_spectrum = original_data[x_i, y_i, :]
                        
                        if mode == 'subtracted':
                            processed_data[x_i, y_i, :] = original_spectrum - fit_spectrum
                        elif mode == 'fitted':
                            processed_data[x_i, y_i, :] = fit_spectrum
                        else:  # mode == 'original'
                            processed_data[x_i, y_i, :] = original_spectrum
                    else:
                        # Fallback to res.best_fit (may be subset)
                        best_fit = res.best_fit
                        if len(best_fit) == spectrum_length:
                            original_spectrum = original_data[x_i, y_i, :]
                            
                            if mode == 'subtracted':
                                processed_data[x_i, y_i, :] = original_spectrum - best_fit
                            elif mode == 'fitted':
                                processed_data[x_i, y_i, :] = best_fit
                            else:
                                processed_data[x_i, y_i, :] = original_spectrum
                        else:
                            # Size mismatch - keep original data
                            processed_data[x_i, y_i, :] = original_data[x_i, y_i, :]
                except Exception:
                    # Fallback to original data if error
                    processed_data[x_i, y_i, :] = original_data[x_i, y_i, :]
            else:
                # No fit -> keep original data
                processed_data[x_i, y_i, :] = original_data[x_i, y_i, :]
            index += 1
            
    return processed_data

def save_fitted_data(fitted_data, folder=None, filename='fitted_data'):
    """
    Guarda fitted_data como un objeto numpy en un directorio 'temp_data'.

    Parámetros:
    - fitted_data: array numpy 3D devuelto por create_data_from_multifit.
    - folder: ruta opcional donde crear 'temp_data'. Si es None, se crea junto a este archivo.
    - filename: nombre base del fichero (sin extensión). Por defecto 'fitted_data'.

    Resultado:
    - ruta del fichero creado (incluye .npy).
    """
    # Determinar carpeta base
    base_dir = folder if folder is not None else os.path.join(os.path.dirname(__file__), 'temp_data')
    # Crear carpeta si no existe
    os.makedirs(base_dir, exist_ok=True)
    # np.save añadirá .npy si no se incluye extensión
    save_path = os.path.join(base_dir, filename)
    np.save(save_path, fitted_data)
    # Devolver la ruta final (con extensión .npy)
    final_path = save_path + '.npy' if not save_path.endswith('.npy') else save_path
    return final_path

"""
Minimal helper AxisArray and MultiFit wrapper
"""

class AxisArray:
    """Minimal axis wrapper exposing a .values attribute like xarray."""
    def __init__(self, values: np.ndarray):
        self.values = np.asarray(values)

class MultiFit:
    """
    Wrapper object to run multifit, access results and save fitted_data.
    Uso:
      mf = MultiFit(data, model, Eloss_x=eloss)
      mf.run()
      fitted = mf.get_fitted_data()
      mf.save()  # guarda en temp_data/fitted_data.npy por defecto
    """
    def __init__(self, data, model, Eloss_x=None, fit_range=None, save_folder=None, filename='fitted_data_{fit_range}'):
        """
        Initialize MultiFit object.
        
        Parameters:
        - data: Either a raw numpy 3D array (dimx, dimy, Eloss) or an xarray.Dataset
                that contains a variable named 'ElectronCount' (or similar). If xarray is
                available and an xarray.Dataset is passed, MultiFit will keep a reference
                to it and can produce an xarray.Dataset with fitted data via to_dataset().
        - model: lmfit model instance or class (e.g., PowerLawModel)
        - Eloss_x: 1D energy-loss axis array
        - fit_range: (xmin, xmax) tuple to restrict fitting range
        - save_folder: Optional folder path for saving fitted data
        - filename: Base filename for saving (without extension)
        """
        self._original_dataset = None
        
        # If xarray is available and the user passed an xarray Dataset, keep it
        if _HAS_XARRAY and isinstance(data, xr.Dataset):
            self._original_dataset = data
            # Try to find ElectronCount variable
            if 'ElectronCount' in data:
                self.data = np.asarray(data['ElectronCount'].values)
            else:
                # Attempt to use the first variable with 3 dims
                found = None
                for v in data.data_vars:
                    arr = data[v]
                    if getattr(arr, 'ndim', None) == 3:
                        found = v
                        break
                if found is not None:
                    self.data = np.asarray(data[found].values)
                else:
                    raise ValueError("xarray.Dataset provided to MultiFit does not contain a 3D variable to fit")
        else:
            self.data = data
            
        self.model = model
        self.Eloss_x = Eloss_x
        self.fit_range = fit_range
        self.save_folder = save_folder
        self.filename = filename
        self.results = None
        self.fitted_data = None
        
        # Provide xarray-like coords for downstream compatibility
        try:
            eloss_values = np.asarray(Eloss_x) if Eloss_x is not None else np.array([])
        except Exception:
            eloss_values = np.array([])
        self._coords = {'Eloss': AxisArray(eloss_values)}

    def run(self, mode='subtracted'):
        """
        Execute the multifit and generate fitted_data.
        
        Parameters:
        - mode: 'subtracted' (default): returns original - fit (background removal)
                'fitted' - returns the fit itself
                'original' - returns original data unchanged
                
        Returns:
        - self (for method chaining)
        """
        self.results = multifit_modified(self.data, self.model, Eloss_x=self.Eloss_x, fit_range=self.fit_range)
        self.fitted_data = create_data_from_multifit(self.results, self.data, mode=mode)
        return self

    def get_fitted_data(self):
        return self.fitted_data

    def get_results(self):
        return self.results

    def save(self, folder=None, filename=None):
        """
        Save fitted_data using save_fitted_data.
        
        Returns:
        - Path to the saved .npy file
        """
        if self.fitted_data is None:
            raise RuntimeError("No fitted_data available. Call run() first.")
        folder_to_use = folder if folder is not None else self.save_folder
        filename_to_use = filename if filename is not None else self.filename
        return save_fitted_data(self.fitted_data, folder=folder_to_use, filename=filename_to_use)

    def summary(self):
        """Return basic summary of the multifit object."""
        n_res = len(self.results) if self.results is not None else 0
        try:
            dimx, dimy, _ = self.data.shape
        except Exception:
            dimx = dimy = None
        return {"dimx": dimx, "dimy": dimy, "n_results": n_res}

    @property
    def coords(self):
        return self._coords

    @property
    def ElectronCount(self):
        """
        Provide an xarray-like accessor for the electron count cube.
        If fitted_data is available, expose that; otherwise expose raw input data.
        
        Returns:
        - xarray.DataArray if original dataset was xarray, otherwise numpy array
        """
        cube = self.fitted_data if self.fitted_data is not None else self.data
        if cube is None:
            raise AttributeError("No data available for ElectronCount")
            
        # If we have an original xarray Dataset, return an xarray.DataArray
        if _HAS_XARRAY and self._original_dataset is not None:
            try:
                orig = self._original_dataset
                # Determine dims order for the variable in the original dataset
                var_name = 'ElectronCount' if 'ElectronCount' in orig else None
                if var_name is None:
                    # Choose the first 3D variable
                    for v in orig.data_vars:
                        if getattr(orig[v], 'ndim', None) == 3:
                            var_name = v
                            break
                if var_name is not None:
                    orig_da = orig[var_name]
                    dims = orig_da.dims
                    coords = {k: orig.coords[k] for k in orig_da.coords.keys()}
                    da = xr.DataArray(data=cube, dims=dims, coords=coords)
                else:
                    # Fallback dims
                    da = xr.DataArray(
                        data=cube, 
                        dims=("y", "x", "Eloss"), 
                        coords={"Eloss": orig.coords.get('Eloss', np.asarray(self.Eloss_x) if self.Eloss_x is not None else np.arange(cube.shape[-1]))}
                    )
                return da
            except Exception:
                # Fallback to numpy array if xarray construction fails
                return cube
        else:
            # No xarray available/original dataset not provided: return raw numpy array
            return cube
    
    def to_dataset(self):
        """
        Return an xarray.Dataset containing the fitted ElectronCount variable.
        
        Requires xarray to be available and original dataset or fitted data to exist.
        
        Returns:
        - xarray.Dataset with fitted data
        
        Raises:
        - RuntimeError if xarray is not available or no fitted data exists
        """
        if not _HAS_XARRAY:
            raise RuntimeError("xarray is not available in this environment")
        if self.fitted_data is None:
            raise RuntimeError("No fitted data available. Call run() first.")
            
        if self._original_dataset is None:
            # Create a new Dataset from coords and fitted_data
            ds = xr.Dataset()
            ds['ElectronCount'] = xr.DataArray(
                self.fitted_data, 
                dims=("y", "x", "Eloss"), 
                coords={"Eloss": self._coords['Eloss'].values}
            )
            return ds
            
        # Reuse original dataset and replace variable
        ds = self._original_dataset.copy(deep=True)
        
        # Choose the var to replace (ElectronCount preferred)
        var_name = 'ElectronCount' if 'ElectronCount' in ds else None
        if var_name is None:
            for v in ds.data_vars:
                if getattr(ds[v], 'ndim', None) == 3:
                    var_name = v
                    break
                    
        if var_name is None:
            # No suitable variable found; add ElectronCount
            ds['ElectronCount'] = xr.DataArray(
                self.fitted_data, 
                dims=("y", "x", "Eloss"), 
                coords={"Eloss": self._coords['Eloss'].values}
            )
        else:
            orig_da = ds[var_name]
            dims = orig_da.dims
            coords = {k: ds.coords[k] for k in orig_da.coords.keys()}
            ds[var_name] = xr.DataArray(self.fitted_data, dims=dims, coords=coords)
            # Ensure ElectronCount exists as well
            if 'ElectronCount' not in ds:
                ds['ElectronCount'] = ds[var_name]
        return ds

    @property
    def dataset(self):
        """Shorthand accessor to get the fitted dataset (requires xarray)."""
        return self.to_dataset()

    def result_like_input(self):
        """
        Return results in the same type as the input data.
        
        Returns:
        - xarray.Dataset if input was xarray, otherwise numpy array
        """
        if self._original_dataset is not None and _HAS_XARRAY:
            return self.to_dataset()
        # Numpy-only mode
        return self.fitted_data if self.fitted_data is not None else self.data

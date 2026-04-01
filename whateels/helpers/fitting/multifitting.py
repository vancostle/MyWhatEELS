import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import plotly.graph_objs as go
from typing import Tuple, Optional

# Try to import xarray if available; otherwise operate in numpy-only mode
try:
    import xarray as xr
    _HAS_XARRAY = True
except Exception:
    xr = None
    _HAS_XARRAY = False

def multifit_modified(data, model, Eloss_x=None, fit_range=None, progress_every=1000, progress_callback=None):
    """
    Pixel-wise multifit using lmfit models with basic masking.

    Parameters:
        data (np.ndarray): 3D array (dimx, dimy, spectrum_length)
        model: lmfit model instance or class
        Eloss_x (array-like): 1D energy-loss axis
        fit_range (tuple or None): (xmin, xmax) to restrict fitting range (in same units as Eloss_x)
        progress_every (int): print progress every N fits (0 to disable)
        progress_callback (callable): optional callback(progress, total) for progress updates
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

    # Default: serial execution (preserve original behavior)
    total = dimx * dimy
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
                if progress_callback:
                    progress_callback(progress, total)

    return results


def _fit_chunk_worker(args):
    """
    Worker function for parallel fitting over a chunk of spectra.
    Receives a tuple with (chunk_2d, x, model_class, fit_range).

    Returns a list (same length as chunk) of dict results or None entries.
    """
    import numpy as _np
    from inspect import isclass as _isclass
    chunk, x_full, model, fit_range = args
    n_chunk = int(len(chunk)) if hasattr(chunk, '__len__') else 0
    try:
        chunk_arr = _np.asarray(chunk)
        if chunk_arr.ndim != 2:
            return [None] * n_chunk

        # Build model instance locally in worker process
        model_instance = model() if _isclass(model) else model
        x = _np.asarray(x_full)

        # Build masks reused by all spectra in the chunk
        mask_x = _np.isfinite(x) & (x > 0)
        if fit_range is not None:
            xmin, xmax = fit_range
            mask_x &= (x >= float(xmin)) & (x <= float(xmax))
        x_valid_mask = _np.isfinite(x) & (x > 0)
        x_valid = x[x_valid_mask]

        out = [None] * chunk_arr.shape[0]
        for i in range(chunk_arr.shape[0]):
            y = _np.asarray(chunk_arr[i])
            mask = mask_x & _np.isfinite(y) & (y > 0)
            if _np.count_nonzero(mask) < 3:
                continue

            x_fit = x[mask]
            y_fit = y[mask]
            pars = model_instance.guess(y_fit, x=x_fit)
            res = model_instance.fit(data=y_fit, params=pars, x=x_fit)

            # Evaluate on full axis
            try:
                best_fit_full = _np.zeros_like(x)
                best_fit_full[x_valid_mask] = res.eval(params=res.params, x=x_valid)
            except Exception:
                best_fit_full = None

            out[i] = {'best_fit_full': best_fit_full, 'best_fit': getattr(res, 'best_fit', None)}

        return out
    except Exception:
        return [None] * n_chunk


def multifit_parallel(data, model, Eloss_x=None, fit_range=None, workers=None, progress_every=1000, progress_callback=None, chunk_size=None):
    """
    Parallel implementation of multifit that uses ProcessPoolExecutor.
    Returns a list of dict results (or None) in the same order as the pixels.
    Accepts optional progress_callback(progress, total) for progress updates.
    """
    import numpy as _np
    data_arr = _np.asarray(data)
    if data_arr.ndim != 3:
        raise ValueError("data must be a 3D array shaped (dimx, dimy, spectrum_length).")
    dimx, dimy, spectrum_length = data_arr.shape
    n_pixels = dimx * dimy

    x = _np.asarray(Eloss_x)
    if x.ndim != 1:
        raise ValueError("Eloss_x must be a 1D array.")
    if x.size != spectrum_length:
        raise ValueError("Eloss_x length must match the third dimension of data.")

    if n_pixels == 0:
        return []

    # Use a reasonable default for workers
    max_workers = workers if workers is not None else max(1, (os.cpu_count() or 1) - 1)
    if max_workers <= 1:
        return multifit_modified(
            data_arr,
            model,
            Eloss_x=x,
            fit_range=fit_range,
            progress_every=progress_every,
            progress_callback=progress_callback,
        )

    flat = _np.ascontiguousarray(data_arr.reshape(n_pixels, spectrum_length))

    if chunk_size is None:
        # Heuristic: many medium chunks tends to be faster than per-pixel futures.
        chunk_size = max(64, min(1024, n_pixels // max(1, max_workers * 6)))
    chunk_size = max(16, int(chunk_size))

    chunks = []
    for start in range(0, n_pixels, chunk_size):
        end = min(start + chunk_size, n_pixels)
        chunks.append((start, end))

    results = [None] * n_pixels

    with ProcessPoolExecutor(max_workers=max_workers) as exe:
        future_to_span = {}
        for start, end in chunks:
            fut = exe.submit(
                _fit_chunk_worker,
                (flat[start:end], x, model, fit_range),
            )
            future_to_span[fut] = (start, end)

        processed = 0
        total = n_pixels

        for fut in as_completed(future_to_span):
            start, end = future_to_span[fut]
            n_chunk = end - start
            try:
                chunk_res = fut.result()
            except Exception:
                chunk_res = [None] * n_chunk

            if not isinstance(chunk_res, list):
                chunk_res = [None] * n_chunk

            if len(chunk_res) < n_chunk:
                chunk_res = chunk_res + ([None] * (n_chunk - len(chunk_res)))
            elif len(chunk_res) > n_chunk:
                chunk_res = chunk_res[:n_chunk]

            results[start:end] = chunk_res
            processed += n_chunk
            if progress_every and (processed % progress_every == 0 or processed == total):
                if progress_callback:
                    progress_callback(processed, total)

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
    orig = np.asarray(original_data)
    dimx, dimy, spectrum_length = orig.shape
    flat_orig = orig.reshape(-1, spectrum_length)
    flat_out = flat_orig.copy()

    for idx, res in enumerate(results):
        if res is None:
            continue

        fit_spectrum = None
        try:
            # Fast path: full-length fit was provided.
            if hasattr(res, 'best_fit_full') and res.best_fit_full is not None:
                fit_spectrum = np.asarray(res.best_fit_full)
            elif isinstance(res, dict) and res.get('best_fit_full') is not None:
                fit_spectrum = np.asarray(res.get('best_fit_full'))

            # Fallback: subset best_fit only if full-length and compatible.
            if fit_spectrum is None:
                best_fit = None
                if hasattr(res, 'best_fit'):
                    best_fit = res.best_fit
                elif isinstance(res, dict):
                    best_fit = res.get('best_fit')
                if best_fit is not None:
                    fit_spectrum = np.asarray(best_fit)

            if fit_spectrum is None or fit_spectrum.shape[0] != spectrum_length:
                continue

            if mode == 'subtracted':
                flat_out[idx] = flat_orig[idx] - fit_spectrum
            elif mode == 'fitted':
                flat_out[idx] = fit_spectrum
            else:  # mode == 'original'
                flat_out[idx] = flat_orig[idx]
        except Exception:
            # Keep original spectrum on any failure.
            flat_out[idx] = flat_orig[idx]

    return flat_out.reshape(dimx, dimy, spectrum_length)

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

    def run(self, mode='subtracted', use_parallel=False, workers=None, progress_callback=None):
        """
        Execute the multifit and generate fitted_data.
        
    Parameters:
    - mode: 'subtracted' (default): returns original - fit (background removal)
        'fitted' - returns the fit itself
        'original' - returns original data unchanged
    - use_parallel: if True, use multiple processes to fit pixels in parallel.
        Note: lmfit model classes are constructed in worker processes, and
        only minimal result dicts are returned to the parent process to
        avoid pickling issues.
    - workers: number of worker processes to use when use_parallel=True. If None,
        uses (cpu_count - 1) or 1.

        Recommended workers:

        Usually: workers = max(1, os.cpu_count() - 1)

        Quick rules:

        - If you have many pixels and each fit is expensive → cpu_count()-1 (or cpu_count()).
        - If memory is limited (Windows may duplicate memory) or each process uses lots of RAM → use 2–4 workers.
        - If few pixels (< ~100) or fits are very fast → do not parallelize (workers=1).
                
        Returns:
        - self (for method chaining)
        """
        # By default run serial implementation for compatibility
        if use_parallel:
            # Use parallel implementation that returns lightweight dicts
            self.results = multifit_parallel(self.data, self.model, Eloss_x=self.Eloss_x, fit_range=self.fit_range, workers=workers, progress_every=1000, progress_callback=progress_callback)
        else:
            self.results = multifit_modified(self.data, self.model, Eloss_x=self.Eloss_x, fit_range=self.fit_range, progress_every=1000, progress_callback=progress_callback)
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

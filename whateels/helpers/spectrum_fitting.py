from scipy.optimize import curve_fit
import numpy as np

class SpectrumFitting:
    """
    Provides static methods for spectrum fitting and visualization.
    Includes power-law fitting and utilities to add fit traces to Plotly figures.
    Designed for use in EELS spectrum analysis workflows.
    """
    
    @staticmethod
    def powerlaw(x, A, k):
        """
        Power-law function: y = A * x^k

        Parameters:
            x (array-like): Input data (independent variable).
            A (float): Amplitude parameter.
            k (float): Exponent parameter.

        Returns:
            np.ndarray: Computed power-law values for x.
        """
        IGNORE = 'ignore'
        with np.errstate(divide=IGNORE, invalid=IGNORE):
            return A * np.power(x, k)

    @staticmethod
    def fit_powerlaw_curve(x, y, range_values=None) -> np.ndarray | None:
        """
        Fit a powerlaw curve to the data, optionally within a specified range.

        Parameters:
            x (array-like): Independent variable data.
            y (array-like): Dependent variable data.
            range_values (tuple, optional): Range of x values to use for fitting. If None, use all data.

        Returns:
            tuple: (params, y_fit)
                params: Fitted parameters (A, k) or None if fitting fails.
                y_fit: Fitted curve values for all x, or None if fitting fails.
        """
        MAXFEV = 10000
        mask = np.isfinite(x) & np.isfinite(y) & (y > 0) & (x > 0)
        if range_values is not None:
            mask &= (x >= range_values[0]) & (x <= range_values[1])
        x_f = x[mask]
        y_f = y[mask]
        if x_f.size < 3:
            return None
        try:
            params, _ = curve_fit(SpectrumFitting.powerlaw, x_f, y_f, maxfev=MAXFEV)
            y_fit = SpectrumFitting.powerlaw(x, *params)
            return y_fit
        except Exception:
            return None

    @staticmethod
    def multifit_modified(x, data, model, range_values=None, progress_every=1000, guess_kwargs=None, fit_kwargs=None):
        """
        Pixel-wise multifit using lmfit models with x/y-style inputs similar to fit_powerlaw_curve.

        Parameters:
            x (array-like): 1D energy loss axis.
            data (np.ndarray): 3D array (dimx, dimy, spectrum_length) of EELS spectra.
            model: lmfit model instance or class from lmfit.models.
            range_values (tuple, optional): (xmin, xmax) range on x for fitting.
            progress_every (int): Print progress every N fits (set None/0 to disable).
            guess_kwargs (dict, optional): Extra kwargs forwarded to model.guess.
            fit_kwargs (dict, optional): Extra kwargs forwarded to model.fit.

        Returns:
            list: Flat list of lmfit ModelResult objects (or None where fit not possible), row-major order.
        """
        # Validate x
        x = np.asarray(x)
        if x.ndim != 1:
            raise ValueError("x (Eloss axis) must be a 1D array.")

        # Validate data
        data_arr = np.asarray(data)
        if data_arr.ndim != 3:
            raise ValueError("data must be a 3D numpy array shaped (dimx, dimy, spectrum_length).")
        dimx, dimy, spectrum_length = data_arr.shape
        if x.size != spectrum_length:
            raise ValueError("x length must match the third dimension (spectrum_length) of data.")

        # Build base mask like fit_powerlaw_curve (finite x, x>0, and optional range)
        mask_x = np.isfinite(x) & (x > 0)
        if range_values is not None:
            xmin, xmax = range_values
            mask_x &= (x >= xmin) & (x <= xmax)

        # Normalize model to an instance
        try:
            from inspect import isclass
        except Exception:
            def isclass(_):  # fallback
                return False
        model_instance = model() if isclass(model) else model

        results = []
        progress = 0
        guess_kwargs = guess_kwargs or {}
        fit_kwargs = fit_kwargs or {}

        for x_i in range(dimx):
            for y_i in range(dimy):
                data_y = data_arr[x_i, y_i, :]

                # Per-spectrum mask includes finite/positive y in addition to mask_x
                mask = mask_x & np.isfinite(data_y) & (data_y > 0)

                # Need enough points to fit
                if np.count_nonzero(mask) < 3:
                    results.append(None)
                else:
                    x_fit = x[mask]
                    y_fit = data_y[mask]
                    pars = model_instance.guess(y_fit, x=x_fit, **guess_kwargs)
                    res = model_instance.fit(data=y_fit, params=pars, x=x_fit, **fit_kwargs)
                    results.append(res)

                progress += 1
                if progress_every and (progress % progress_every == 0):
                    print(progress)

        return results

    @staticmethod
    def build_spectrum_image_from_results(results, template, x, fill_value=np.nan, progress_every=1000):
        """
        Reconstruye una imagen-espectro 3D a partir de una lista plana de lmfit ModelResult.

        Parametros:
            results (list): lista plana de ModelResult (row-major) o None por píxel.
            template (ndarray or object): ndarray 3D (dimx,dimy,spec_len) o un objeto que tenga .data.
            x (array-like): eje de energía (1D) donde evaluar las reconstrucciones.
            fill_value (float): valor para píxeles sin fit válido (por defecto NaN).
            progress_every (int): imprimir progreso cada N píxeles (None/0 para desactivar).

        Retorna:
            Si template tiene .deepcopy() o es copiable y posee .data, devuelve una copia con .data reemplazada.
            En caso contrario devuelve el ndarray 3D reconstruido.
        """
        import copy

        x = np.asarray(x)
        if x.ndim != 1:
            raise ValueError("x must be a 1D array.")

        # Resolver forma desde el template
        if hasattr(template, "data"):
            orig_data = np.asarray(template.data)
        else:
            orig_data = np.asarray(template)

        if orig_data.ndim != 3:
            raise ValueError("template.data (or template) must be a 3D array (dimx, dimy, spectrum_length).")

        dimx, dimy, spectrum_length = orig_data.shape
        out_len = x.size
        out = np.full((dimx, dimy, out_len), fill_value, dtype=float)

        total = dimx * dimy
        if len(results) != total:
            raise ValueError(f"Expected results length {total}, got {len(results)}.")

        progress = 0
        for i in range(dimx):
            for j in range(dimy):
                idx = i * dimy + j
                res = results[idx]
                if res is None:
                    # deja como fill_value
                    pass
                else:
                    y_full = None
                    # Intentar evaluar el modelo ajustado en el eje completo
                    try:
                        y_full = res.model.eval(params=res.params, x=x)
                        y_full = np.asarray(y_full, dtype=float)
                    except Exception:
                        try:
                            # fallback a res.eval si está disponible
                            y_full = res.eval(x=x)
                            y_full = np.asarray(y_full, dtype=float)
                        except Exception:
                            # fallback a best_fit si coincide en longitud
                            try:
                                bf = np.asarray(getattr(res, "best_fit", None))
                                if bf is not None and bf.size == out_len:
                                    y_full = bf.astype(float)
                                else:
                                    y_full = None
                            except Exception:
                                y_full = None

                    if y_full is not None and y_full.size == out_len:
                        out[i, j, :] = y_full
                    # si no coincide, deja el fill_value

                progress += 1
                if progress_every and (progress % progress_every == 0):
                    print(progress)

        # Intentar devolver una copia del template con .data reemplazada
        if hasattr(template, "deepcopy"):
            try:
                template_copy = template.deepcopy()
                template_copy.data = out
                return template_copy
            except Exception:
                pass

        # Intento genérico de deepcopy
        try:
            template_copy = copy.deepcopy(template)
            if hasattr(template_copy, "data"):
                template_copy.data = out
                return template_copy
        except Exception:
            pass

        # Devolver ndarray si no se pudo devolver template
        return out
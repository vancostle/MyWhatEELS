from scipy.optimize import curve_fit
import numpy as np
import plotly.graph_objs as go

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
            return None, None
        try:
            params, _ = curve_fit(SpectrumFitting.powerlaw, x_f, y_f, maxfev=MAXFEV)
            y_fit = SpectrumFitting.powerlaw(x, *params)
            return y_fit
        except Exception:
            return None
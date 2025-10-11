"""whateels.helpers.fitting

Public API for the fitting helpers used by the application.
This module re-exports the main helpers implemented in multifitting.py so
 callers can do:

    from whateels.helpers.fitting import MultiFit, multifit_modified

Keep this file small: heavy implementation remains in multifitting.py.
"""

from .multifitting import (
    MultiFit,
    multifit_modified,
    create_data_from_multifit,
    save_fitted_data,
)

__all__ = [
    "MultiFit",
    "multifit_modified",
    "create_data_from_multifit",
    "save_fitted_data",
]

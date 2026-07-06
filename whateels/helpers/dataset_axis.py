"""Helpers for Eloss axis labelling on xarray datasets."""

ELOSS_CALIBRATED_ATTR = "eloss_calibrated"
ELOSS_AXIS_LABEL_ATTR = "eloss_axis_label"
ELOSS_AXIS_LABEL_EV = "Energy Loss (eV)"
ELOSS_AXIS_LABEL_CHANNEL = "Channel index"


def eloss_axis_label(dataset, default: str = ELOSS_AXIS_LABEL_EV) -> str:
    """Return the spectrum X-axis label stored on *dataset*, or *default*."""
    return dataset.attrs.get(ELOSS_AXIS_LABEL_ATTR, default)

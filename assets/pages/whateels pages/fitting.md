<!-- order: 3 -->

## Introduction
The Fitting page provides an interactive workflow for fitting spectral models to selected regions of a Spectrum Image dataset.

---

## Requirements
- A DM3 or DM4 file with at least one Spectrum Image (SIm) dataset must be loaded on the Home page.
- The page loads the dataset corresponding to the `?tab=N` URL parameter.

---

## Dataset Visualization
- The left pane (paneA) displays the integrated intensity heatmap of the selected dataset.
- Hovering over pixels shows their spectrum in the right pane (paneB).
- Drawing a lasso or box selection on the heatmap sums the spectra in that region and displays the summed spectrum.
- Double-clicking resets any active selection and returns to hover mode.
- Clicking a selected pixel while a region is active temporarily shows that pixel's spectrum, then reverts to the region spectrum after a short inactivity period.

---

## Preprocessed Data Switch
- A switch in the right sidebar enables using Home multifit-preprocessed data instead of raw data.
- This switch is only active if preprocessing was applied on the Home page and is compatible with the current dataset dimensions.

---

## Fitting Workflow
### Adding Components
1. Draw a lasso or box selection on the heatmap to define your region of interest.
2. In the right sidebar, set an energy center for the spectral component you want to fit.
3. Select a model type (e.g. Gaussian, Lorentzian).
4. Click "Add Component" to register the component. A component card appears in the sidebar showing its parameters.
5. Repeat to add multiple components.

---

### Running the Fit
- Once components are added, click the fit button to execute the NLLS fitting on the summed spectrum.
- The fitted curve is overlaid on paneB as a filled magenta area on top of the ROI spectrum.

---

### Managing Components
- Each component card in the sidebar allows editing of its parameters.
- Components can be removed individually.
- Changing energy center values updates the editable energy range automatically.

---

## Energy Map
- Click the "Energy Map" toggle button to replace paneA with a heatmap of a model-computed energy value across the image.
- The energy map uses a green-to-pink colormap and shows spatial variation of the fitted energy.
- Toggle the button again to return to the standard integrated intensity image.

---

## Multifit / Background Subtraction
- A "Multifit" button runs the background subtraction computation using the defined components across the full data cube.
- The result is stored in shared session state and becomes available on the Clustering and Advanced Clustering pages as preprocessed data.

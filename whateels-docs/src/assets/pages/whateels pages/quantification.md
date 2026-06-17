<!-- order: 6 -->

## Quantification Page
The Quantification page enables elemental quantification of EELS spectra from a selected region of interest using cross-section models.

## Requirements
- A DM3 or DM4 file with at least one Spectrum Image (SIm) dataset must be loaded on the Home page.
- The page loads the dataset corresponding to the `?tab=N` URL parameter.
- At least two elements must be added before quantification can be run.

## Dataset Visualization
- The left pane (paneA) shows the integrated intensity heatmap.
- Hovering over pixels temporarily shows their spectrum in the right pane (paneB).
- Drawing a lasso or box selection on the heatmap sums spectra in that region and displays the summed spectrum with any active quantification overlays.
- After a selection is drawn, paneB reverts to the summed ROI spectrum after a short hover inactivity period.
- Double-clicking resets the selection and returns to hover mode.

## Adding Elements
1. In the right sidebar, select an atomic number (element) using the element input.
2. Available subshells for the selected element are loaded automatically.
3. Select one or more subshells from the multiselect widget.
4. Click "Add Element" to register the element with its subshells and cross-section data.
5. Each element appears as an item in the sidebar list. Elements cannot be added twice.
6. Remove any element item if you need to replace it.

## Quantification Overlays
- Once elements are added and a region is selected, the spectrum in paneB is overlaid with:
  - A power-law background fit curve.
  - Background-subtracted signal for each element.
  - Cross-section curves scaled to the experimental signal.
- These overlays update automatically when the selection changes.

## Running Quantification
- Click "Run Quantification" to compute elemental proportions for the selected ROI.
- A pie chart (or bar chart) is rendered in paneB showing the relative proportions of each element as percentages.
- The result reflects the ratio of integrated signal to cross-section for each element in the defined energy windows.

## Toggle Quantification Overlay
- A toggle button allows showing or hiding the quantification overlay independently of the pie chart.

## Notes
- Beam energy and collection angle are read directly from the file metadata and used for cross-section calculations.
- Cross-section data follows the Hartree–Fock tables from F. Salvat (bundled with the application).

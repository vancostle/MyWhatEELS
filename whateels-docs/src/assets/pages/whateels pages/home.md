<!-- order: 1 -->

## Introduction
The Home page is the starting point of WhatEELS. Its primary function is file loading and initial dataset exploration.

---

## File Uploader
- Click the upload area to select a DM3 or DM4 file from disk or put the file path in the input field.
- Only `.dm3` and `.dm4` extensions are accepted; other formats are rejected with a notification.
- To replace the current file, drop or select a new one. The previous dataset is cleared automatically.
- On the successful upload state, you can:
    - Hover over the file name to see the full path
    - Click to copy the path to clipboard
    - Or click the remove button to clear the file.
- After a successful upload, the file's datasets are parsed and become available as tabs for exploration.

![File Upload Widget](gifs/how-to-use-file-uploader.gif)

---

## Dataset Tabs
- After a successful upload, each embedded dataset inside the DM file becomes its own tab.
- Supported dataset types are: Spectrum Image (SIm), Spectrum Line (SLi), Single Spectrum (SSp), and Image (Img).
- You can switch between tabs to inspect different datasets from the same file.
- The selected dataset is shared across pages via session state and reflected in the URL as a query parameter (e.g., `?tab=0`).

---

## Interactive Spectrum Visualization
- The main panel shows the integrated intensity heatmap of the selected dataset on the left (paneA).
- Hovering over the heatmap shows the pixel spectrum on the right (paneB) in real time.
- Clicking on a pixel freezes the spectrum display for that pixel.
- Double-clicking returns to hover mode.
- Drawing a lasso or box selection on the heatmap sums the spectra in that region.
- The spectrum axis is labeled in Energy Loss (eV).

---

## Preprocessing Controls
The right sidebar exposes several preprocessing options that persist across the session:

---

### Spike Removal
- Enable the spike removal toggle to activate despiking preprocessing.
- Adjust the spike threshold and window size using the dedicated sliders.
- Click "Apply Remove Spikes" to compute and store the despiked cube.
- The toggle button indicates whether despiking is currently applied to the display.

---

### Cut Range
- Enter minimum and maximum energy values to restrict the energy axis.
- Click "Apply Cut Range" to trim the spectrum to the defined range.
- A reset button restores the original energy axis.

---

### Multifitting / Background Subtraction
- Enable the multifitting switch to activate background subtraction preprocessing.
- Click "Apply Multifit" to compute the background-subtracted data cube using parallel processing.
- The result is stored in shared session state and becomes available to the Fitting and Clustering pages.

---

## Dataset Information
- A dataset information panel in the sidebar shows key metadata attributes (dimensions, energy axis, dataset type).
- A "View Metadata" button navigates to the Metadata Details page.

---

## Navigation
- Once a file is loaded, navigation links in the header become active for pages that require EELS data (Clustering, Fitting, Quantification).

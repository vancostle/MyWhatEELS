<!-- order: 4 -->

## Introduction
The Clustering page provides unsupervised spectral grouping of a Spectrum Image dataset using three classical clustering algorithms.

---

## Requirements
- A DM3 or DM4 file with at least one Spectrum Image (SIm) dataset must be loaded on the Home page first.
- Optionally, multifit preprocessing (background subtraction) must be applied on the Home page for the preprocessing switch to become active on this page.

---

## Viewing the Dataset
- The heatmap on the left (paneA) initially shows the integrated intensity image.
- Hovering over any pixel shows the corresponding spectrum in the right panel (paneB).
- Clicking a pixel freezes that spectrum. Double-clicking the heatmap toggles between hover mode and a view of all cluster centers.

---

## Clustering Algorithms
Three algorithms are available as separate tabs in the right sidebar:

---

### K-Means
- Select the number of clusters, number of initializations, maximum iterations, and initialization method.
- Choose an optional normalization for the spectral vectors (none, L1, L2, max).
- Click "Run K-Means" to start. Clustering runs in a background thread with a progress indicator.
- Results are immediately shown in paneA as a color-coded heatmap.

---

### Agglomerative
- Configure the number of clusters, linkage method (ward, complete, average, single), and affinity metric.
- When ward linkage is selected, affinity is locked to euclidean automatically.
- Click "Run Agglomerative" to start.

---

### Spectral
- Configure the number of clusters, number of initializations, assign-labels method, affinity metric (rbf or nearest_neighbors), number of neighbors, and gamma.
- Click "Run Spectral" to start.

---

## Cluster Heatmap Interaction
- After a clustering run, paneA shows a discrete color-coded heatmap with one color per cluster.
- Hovering a pixel shows that pixel's spectrum overlaid with its cluster center.
- Clicking a pixel freezes the spectrum view on that pixel and its cluster center.
- Double-clicking toggles between showing the hovered pixel spectrum and showing all cluster center spectra simultaneously.

---

## Color Picker
- Each algorithm tab includes a color picker widget, enabled after a clustering run.
- The picker is initialized to the color assigned to the pixel at position (0, 0).
- Clicking a pixel in the heatmap updates the picker to reflect the cluster at that location.
- Changing the color in the picker immediately repaints both paneA and paneB to reflect the new color.

---

## Preprocessed Data Switch
- A toggle in the sidebar enables using the multifit-preprocessed data cube for clustering instead of raw data.
- This option is only available if the multifit background subtraction was applied on the Home page.

---

## Saving Results
- A "Store Last Clustering Results" button downloads the last completed clustering result as a JSON file.
- The file includes algorithm type, input parameters, cluster labels, and cluster center spectra.

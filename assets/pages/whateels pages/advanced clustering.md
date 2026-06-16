<!-- order: 5 -->

## Advanced Clustering Page
The Advanced Clustering page provides a non-linear dimensionality reduction and density-based clustering workflow using UMAP and HDBSCAN.

---

## Requirements
- A DM3 or DM4 file with at least one Spectrum Image (SIm) dataset must be loaded on the Home page.
- The dataset must be selected via a valid tab URL parameter (`?tab=N`).
- Optionally, Home multifit preprocessing can be used as input instead of raw data.

---

## Data Source
- A switch at the top of the right sidebar allows switching between raw data and Home-preprocessed data as input for UMAP.
- Switching the source clears any previously computed results and requires a new UMAP run.

---

## UMAP Embedding
- Configure the following UMAP parameters in the right sidebar:
  - Normalization method (none, L1, L2, max)
  - One or more `min_dist` values
  - One or more `n_neighbors` values
  - Number of components
  - Distance metric
- Each combination of `min_dist` × `n_neighbors` generates a separate embedding.
- Click "Run UMAP" to start all combinations in parallel background threads.
- Results appear as a grid of 2D scatter plots. Each plot represents one UMAP embedding.
- The run button becomes a cancel button during computation. Canceling stops any pending combinations.
- Completed embeddings can be downloaded as a file for later reuse.

---

## Loading a Saved UMAP File
- Previously saved UMAP results can be uploaded via the left sidebar.
- This allows skipping the UMAP computation step when results are already available.

---

## HDBSCAN Clustering
- After UMAP embeddings are computed, select one from the dropdown in the HDBSCAN section.
- Configure minimum samples and minimum cluster size.
- Click "Run HDBSCAN" to perform density-based clustering on the selected UMAP embedding.
- The result is shown in the spectrum visualizer below: paneA displays the cluster label heatmap and paneB shows mean spectra per cluster.

---

## Cluster Visualization
- Hovering on the HDBSCAN cluster map shows the hovered pixel's raw spectrum overlaid with the cluster center spectrum.
- Clicking a pixel freezes the spectrum on that location.
- Double-clicking toggles back to hover mode.
- Noise points (label −1 from HDBSCAN) are shown with a distinct color in the map.

<!-- order: 1 -->

## What is WhatEELS?
WhatEELS is an interactive web application for exploring and analyzing Electron Energy Loss Spectroscopy (EELS) datasets. It is designed to help researchers move from raw spectral data to interpretable results through visual, guided workflows.

The application is built with Python, Panel, and HoloViews, and runs as a local browser app. It combines data inspection, metadata exploration, clustering, fitting, and quantification in a single environment.

---

## Download WhatEELS
You can download the latest version of WhatEELS from the releases page on the next link:

[Download WhatEELS](https://download-whateels-9k5k.onrender.com/)

---

## Why WhatEELS exists
EELS analysis often requires multiple disconnected tools and repeated context switching between scripts, plots, and files. WhatEELS brings these steps together so users can:

- load and inspect data quickly,
- validate metadata before analysis,
- run unsupervised clustering to discover spectral structure,
- perform fitting and map fit-related outputs,
- quantify selected elements in a region of interest.

---

## Who should use WhatEELS?
WhatEELS is useful for:

- Materials science and microscopy researchers working with EELS data.
- Analysts who need a visual workflow instead of script-only processing.
- Teams that want a shared, structured analysis environment for common EELS tasks.

---

## Scope and current input support
WhatEELS currently focuses on EELS workflows around DM3 and DM4 file ingestion and interactive browser-based analysis. Additional integrations can be layered through its modular page and component architecture.

---

## What can you do with it?
With WhatEELS, you can:

- Upload Digital Micrograph files using DM3 and DM4 formats.
- Explore spectrum images interactively by hovering and selecting regions.
- Inspect dataset metadata in a dedicated metadata view.
- Run clustering workflows with K-Means, Agglomerative, and Spectral clustering.
- Customize cluster colors and inspect cluster-center spectra interactively.
- Use advanced clustering workflows based on UMAP and HDBSCAN.
- Perform fitting workflows, including overlays and energy-map visualization.
- Run quantification workflows with ROI-driven spectra and quantification overlays.
- Reuse shared state across pages (for example metadata, selected data context, multifit outputs, and quantification elements).

---

## Main analysis areas
WhatEELS is organized around feature pages:

- Home: data loading and initial dataset interaction.
- Metadata Details: detailed metadata visualization and validation.
- Clustering: classical clustering methods for spectral grouping and center inspection.
- Advanced Clustering: UMAP + HDBSCAN workflow for non-linear embedding and density-based clustering.
- Fitting: fit-oriented visualization, ROI-aware plotting, and energy-map workflows.
- Quantification: ROI-based quantification with model overlays and compositional outputs.

---

## Typical user workflow
A common end-to-end workflow looks like this:

1. Load a DM3 or DM4 dataset on the Home page.
2. Review metadata to confirm dataset integrity and context.
3. Explore spectral behavior interactively (hover/click or ROI where applicable).
4. Run clustering to identify spectral populations.
5. Refine interpretation with fitting tools.
6. Run quantification on selected regions/elements.
7. Export or continue iterative analysis with updated parameters.

---

## In short
WhatEELS is a practical, interactive EELS analysis workspace that helps users go from raw spectra to interpretable clustering, fitting, and quantification results in one consistent tool.

---

## Project Contributors
The following people have participated in the WhatEELS project so far:

- Vanessa Costa Ledesma
- [Andry Alexis Reyes Cruz](https://es.linkedin.com/in/andryalexisreyescruz)


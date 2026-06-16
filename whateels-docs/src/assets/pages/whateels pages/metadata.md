<!-- order: 2 -->

## Metadata Details Page
The Metadata Details page provides a structured view of the raw metadata embedded in the uploaded DM3 or DM4 file.

## Accessing the Page
- Navigate to this page by clicking "View Metadata" from the Home page dataset info panel or via the site header link.
- The page requires a file to be loaded first. If no file has been uploaded, a placeholder is shown instead of metadata content.

## What Is Displayed
- All metadata fields parsed from the DM file are presented in a structured, interactive JSON tree view.
- The metadata includes instrument settings, acquisition parameters, calibration information, and any other tags embedded in the file by the acquisition software.
- The tree is fully expandable and collapsible, allowing you to explore nested structures.

## Use Case
- Verify acquisition parameters (e.g. beam energy, collection angle, pixel size) before running any analysis.
- Inspect calibration values used internally by other pages (e.g. beam energy is used by Quantification for cross-section calculations).
- Cross-check dataset integrity by reviewing embedded dimensional information.

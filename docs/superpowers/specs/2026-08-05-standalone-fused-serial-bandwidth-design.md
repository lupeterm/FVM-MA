# Standalone Fused Serial Bandwidth Plot Design

## Goal

Add a reusable plot to `variants/generate_figures_gpu.ipynb` for the serial (`Threads == 1`) results in `variants/standalone_fused.csv`. The figure compares the two CPU nodes with H100 on the left and H200 on the right.

The implementation must be written directly into a new executable code cell in the notebook. The cell must contain both the plotting function and its invocation so that running it displays the figure inline. No separate Python, HTML, or visualization source file is part of the implementation; the SVG is only an export produced by the notebook cell.

## Data preparation

- Load `standalone_fused.csv` with blank-line handling enabled.
- Derive `cells` from the numeric suffix of `case_long`.
- Map each cell count to `nnz` using `../results/NEON-CPU.csv`, validating that every plotted row receives an `nnz` value.
- Calculate bandwidth in GB/s using the notebook's established formula:

  `bandwidth = nnz * 8 / (time_mean_ms * 1_000_000)`

- Map strategy identifiers to the existing display names.
- Filter to `Threads == 1`. Keep every problem size currently available for each node; H100 and H200 do not need identical cell-count coverage.

## Figure design

- Produce one figure with two subplots using a Seaborn faceted line plot.
- Fix the facet order to H100 on the left and H200 on the right.
- Plot `cells` on a logarithmic x-axis and bandwidth on a shared y-axis.
- Draw the three available serial strategies with stable colors, line styles, and markers across both facets.
- Put `H100` and `H200` in framed labels in the upper-left corner of their respective subplot.
- Remove facet titles and use one shared legend above the subplots.
- Label the axes `#Cells` and `Matrix Assembly Bandwidth [GB/s]`.
- Save the figure as `bandwidth-cpu-serial-h100-h200.svg`.

## Function boundary

Implement the plot as a function inside the new notebook cell. It accepts the prepared dataframe and owns serial filtering, ordering, plotting, annotation, layout, output, and returns the Seaborn grid so callers can inspect or further adjust it. Invoke the function at the end of the same cell with the prepared `standalone_fused.csv` dataframe so the plot is rendered directly in the notebook.

## Validation and errors

- Raise a clear error if no serial rows are available.
- Raise a clear error if either H100 or H200 is missing entirely.
- Verify that the rendered figure has exactly two axes in the requested order.
- Verify that the shared legend is inside the figure and above both axes.
- Verify that all three strategies retain the same color and marker mapping in both facets.
- Verify that H100 and H200 retain all of their available serial cell counts.

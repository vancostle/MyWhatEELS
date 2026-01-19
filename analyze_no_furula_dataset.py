import xarray as xr

# Load the dataset from the NetCDF file
nc_path = "no_furula_dataset.nc"
ds = xr.open_dataset(nc_path)

# Show dataset summary
print(ds)

# Show detailed info
print("\n--- ds.info() ---")
ds.info()

# Show first few values of each variable
def print_var_samples(ds):
    for var in ds.data_vars:
        print(f"\nVariable: {var}")
        print("Shape:", ds[var].shape)
        print("Dimensions:", ds[var].dims)
        print("Coordinates:", list(ds[var].coords))
        print("First 10 values:", ds[var].values.ravel()[:10])

print_var_samples(ds)

import os, sys
import pandas as pd
import subprocess
import glob
import yaml
import platform

import configuration
import main
import json
from pathlib import Path
import multiprocessing
from functools import partial # used for partially applied function which allows to create new functions with arguments
import time
import xarray as xr

infile  = sys.argv[1]
with open(infile, 'r') as file:
    d = yaml.safe_load(file)

dsim = d['simulations']
workflow_dir        = d["workflow_dir"]
input_dir           = d["input_dir"]
output_dir          = Path(d["output_dir"])
verbosity           = dsim.get('verbosity', 0)
num_processors_forcing  = 1

dforcing = d['forcings']
forcing_dir      = dforcing.get("forcing_dir", "")
forcing_time     = dforcing["forcing_time"]
forcing_format   = dforcing.get('forcing_format', '.nc')
forcing_venv_dir = dforcing.get('forcing_venv_dir', "~/venv_forcing")

output_dir.mkdir(parents=True, exist_ok=True)

# fix missing data points (NaNs) and APCP_surface units
def forcing_data_correction(fdir):

    nc_file = glob.glob(f"{fdir}/*.nc")
    nc_file = [f for f in nc_file if not "_corrected" in f][0]

    ds = xr.open_dataset(nc_file)

    # add units to precipitation
    ds['APCP_surface'].attrs['units'] = 'mm/hr'

    for name in ds.data_vars:
    
        # Check for NaN values
        if ds[name].isnull().any():
            if verbosity >=2:
                print(f"Missing data: NaNs found in {name}.")
            ds[name] = ds[name].interpolate_na(dim='time',method='nearest') # default method = linear
        elif verbosity >=2:
            print(f"Looks good. No NaNs found in {name}.")

    path = Path(nc_file)

    new_file = Path(fdir) / (path.stem + "_corrected.nc")

    ds.to_netcdf(new_file)
    
def forcing_generate_catchment(dir):

    os.chdir(dir)
    infile = os.path.join(workflow_dir, "configs/config_aorc.yaml")

    if (os.path.exists(os.path.join(dir,"data"))):
        gpkg_file = glob.glob(dir + "data/*.gpkg")[0]
    else:
        return

    fdir = forcing_dir
    if "{*}" in forcing_dir:
        fdir = Path(forcing_dir.replace("{*}", Path(dir).name))

    config_dir = os.path.join(dir,"configs")
    forcing_config = configuration.write_forcing_input_files(forcing_basefile = infile,
                                                             gpkg_file        = gpkg_file,
                                                             forcing_time     = forcing_time,
                                                             forcing_format   = forcing_format,
                                                             forcing_dir      = fdir)

    run_cmd = f'python {workflow_dir}/extern/CIROH_DL_NextGen/forcing_prep/generate.py {forcing_config}'

    venv_bin = os.path.join(forcing_venv_dir, 'bin')

    if (not os.path.exists(venv_bin)):
        msg = f"Python venv for forcing does not exist. Provided {forcing_venv_dir}"
        sys.exit(msg)

    env = os.environ.copy()
    env['PATH'] = f"{venv_bin}:{env['PATH']}"
    result = subprocess.call(run_cmd, shell=True, env = env)


    if (forcing_format == ".nc"):
        print ("Correcting forcing data ...")
        forcing_data_correction(fdir)
    
def forcing(nproc = 1):


    if (not os.path.exists(infile)):
        sys.exit("Sample forcing yaml file does not exist, provided is " + infile)

    # create a pool of processors using multiprocessing tool
    pool = multiprocessing.Pool(processes=nproc)

    # map catchments to each processor
    results = pool.map(forcing_generate_catchment, gpkg_dirs)
    results = [result for result in results if result is not None]

    # collect results from all processes
    for result in results:
        basin_ids.extend(result[0])
        num_cats.extend(result[1])

    pool.close()
    pool.join()
    

if __name__ == "__main__":

        
    all_dirs = glob.glob(os.path.join(input_dir, '*/'), recursive = True)

    assert all_dirs, f"No directories found in the input directory {input_dir}."
    
    gpkg_dirs = [
        g for g in all_dirs 
        if os.path.exists(os.path.join(g, 'data')) and glob.glob(os.path.join(g, 'data', '*.gpkg'))
    ]


    output_dirs = [output_dir / Path(g).name for g in gpkg_dirs ]

    forcing(nproc = num_processors_forcing)

import os, sys
import pandas as pd
import subprocess
import glob
import yaml
import platform
#from generate_files import configuration
import configuration
import json
from pathlib import Path
import multiprocessing
from functools import partial # used for partially applied function which allows to create new functions with arguments
import time

infile  = sys.argv[1]
with open(infile, 'r') as file:
    d = yaml.safe_load(file)

dsim = d['simulations']
workflow_dir        = d["workflow_dir"]
output_dir          = d["output_dir"]
simulation_time     = dsim["simulation_time"]
is_netcdf_forcing   = dsim.get('is_netcdf_forcing', True)
verbosity           = dsim.get('verbosity', 0)
forcing_venv_dir    = dsim.get('forcing_venv_dir', "~/venv_forcing")
#forcing_venv_dir   = "/home/ec2-user/venv_forcing"
num_processors_forcing  = 1

def forcing_generate_catchment(dir):

    os.chdir(dir)
    infile = os.path.join(workflow_dir, "configs/config_aorc.yaml")

    if (os.path.exists(os.path.join(dir,"data"))):
        gpkg_file = glob.glob(dir + "data/*.gpkg")[0]
    else:
        return
    
    config_dir = os.path.join(dir,"configs")
    forcing_config = configuration.write_forcing_input_files(forcing_basefile = infile,
                                                             gpkg_file = gpkg_file,
                                                             time = simulation_time)

    run_cmd = f'python {workflow_dir}/extern/CIROH_DL_NextGen/forcing_prep/generate.py {forcing_config}'

    venv_bin = os.path.join(forcing_venv_dir, 'bin')

    if (not os.path.exists(venv_bin)):
        sys.exit("venv for forcing does not exist...")

    env = os.environ.copy()
    env['PATH'] = f"{venv_bin}:{env['PATH']}"
    result = subprocess.call(run_cmd, shell=True, env = env)

    
def forcing(nproc = 1):


    if (not os.path.exists(infile)):
        sys.exit("Sample forcing yaml file does not exist, provided is " + infile)

    # create a pool of processors using multiprocessing tool
    pool = multiprocessing.Pool(processes=nproc)
    

    #partial_generate_files_catchment = partial(generate_catchment_files, forcing_files=forcing_files)

    # map catchments to each processor
    #results = pool.map(partial_generate_files_catchment, gpkg_dirs)
    results = pool.map(forcing_generate_catchment, gpkg_dirs)
    results = [result for result in results if result is not None]

    # collect results from all processes
    for result in results:
        basin_ids.extend(result[0])
        num_cats.extend(result[1])

    # Write results to CSV
    #with open(basins_passed, 'w', newline='') as file:
    #    dat = zip(basin_ids, num_cats)
    #    writer = csv.writer(file)
    #    writer.writerow(['basin_id', 'n_cats'])
    #    writer.writerows(dat)

    pool.close()
    pool.join()
    


    #print (d)
if __name__ == "__main__":

    all_dirs = glob.glob(output_dir + "/*/", recursive = True)
    gpkg_dirs = [g for g in all_dirs if "failed_cats" not in g] # remove the failed_cats directory

    forcing(nproc = num_processors_forcing)

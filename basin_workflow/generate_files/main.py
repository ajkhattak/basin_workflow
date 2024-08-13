############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : October 11, 2023 
############################################################################################


import os,sys
import subprocess
import pandas as pd
import glob
import shutil
import re
import geopandas as gpd
import csv
import yaml
import multiprocessing
from functools import partial # used for partially applied function which allows to create new functions with arguments
import time
import argparse

import helper
# Note #1: from the command line just run 'python path_to/main.py'
# Note #2: make sure to adjust the following required arguments
# Note #3: several model coupling options are available, the script currently supports a few of them, for full list see
#          below the coupled_models_option


############################# Required Arguments ###################################
### Specify the following four directories (change according to your settings)
# workflow_dir    : points to the base directory of generate_files under basin_workflow
# root_dir        : geopackage(s) directory (format root_dir/GAUGE_ID see below)                 
# nc_forcing_dir  : lumped forcings directory (pre-downloaded forcing data for each catchment (.csv or .nc); only need if forcing
#                   directory is outside the structure of the root_dir described below)
# ngen_dir        : nextgen directory path

### Specify the following model options
# simulation_time            : string  | simulation start/end times; format YYYYMMDDHHMM (YYYY, MM, DD, HH, MM)
# model_option               : string  | model option (see available options below)
# surface_runoff_scheme      : string  | surface runoff scheme for CFE and LASAM OPTION=[GIUH, NASH_CASCADE]
# precip_partitioning_scheme : string  | precipitation partitioning scheme for CFE OPTION=[Schaake, Xinanjiang]
# is_netcdf_forcing          : boolean | True if forcing data is in netcdf format
# clean                      : str/lst | Options = all, existing, none (all deletes everything other than data directory, existing deletes
#                                        existing simulation configs, json, and outputs directories
# num_processors_config      : int     | Number of processors for generating config/realiation files
# num_processors_sim         : int     | Number of processors for catchment/geopackage partition for ngen parallel runs
# setup_simulation           : boolean | True to create files for simulaiton;
# rename_existing_simulation : string  | move the existing simulation set (json, configs, outputs dirs) to this directory, e.g. "sim_cfe1.0"

####################################################################################

"""
root_dir:
   - 10244950
     - data
       - Gage_10244950.gpkg
       - forcings
   - 01047000
     - data
       - Gage_01047000.gpkg
       - forcings
"""

"""
coupled_models_options = {
"C"   : "cfe",
"L"   : "lasam",
"NC"  : "nom_cfe",
"NL"  : "nom_lasam",
"NCP" : "nom_cfe_pet",
"NCSS": "nom_cfe_smp_sft",
"NLSS": "nom_lasam_smp_sft",
"NT"  : "nom_topmodel",
"BC"  : "baseline_cfe",
"BL"  : "baseline_lasam"
}
"""

###########################################################################
class colors:
    GREEN = '\033[92m'
    RED   = '\033[91m'
    END   = '\033[0m'

# Set all variables as  global variables from your yaml config file
#parent_dir = os.path.dirname(os.path.dirname(sys.argv[0]))
#with open(os.path.join(parent_dir, "input.yaml"), 'r') as file:
#    d = yaml.safe_load(file)

infile  = sys.argv[1]
with open(infile, 'r') as file:
    d = yaml.safe_load(file)

dsim = d['simulations']
workflow_dir               = d["workflow_dir"]
root_dir                   = d["output_dir"]
ngen_dir                   = dsim["ngen_dir"]
simulation_time            = dsim["simulation_time"]
model_option               = dsim['model_option']
precip_partitioning_scheme = dsim['precip_partitioning_scheme']
surface_runoff_scheme      = dsim['surface_runoff_scheme']
is_netcdf_forcing          = dsim.get('is_netcdf_forcing', True)
clean                      = dsim.get('clean', "none")
is_routing                 = dsim.get('is_routing', False)
verbosity                  = dsim.get('verbosity', 0)
num_processors_config      = dsim.get('num_processors_config', 1)
num_processors_sim         = dsim.get('num_processors_sim', 1)
setup_simulation           = dsim.get('setup_simulation', True)
rename_existing_simulation = dsim.get('rename_existing_simulation', "")
is_calibration             = dsim.get('is_calibration', False)

def process_clean_input_param():
    clean_lst = []
    if (isinstance(clean, str)):
        clean_lst = [clean]
    elif (isinstance(clean, list)):
        clean_lst.extend(clean)
    return clean_lst

clean = process_clean_input_param()

##############################################################################

def generate_catchment_files(dir, forcing_files):
    
    os.chdir(dir)

    basin_ids = []
    num_cats  = []
    
    if (verbosity >=2):
        print ("dir: ", dir)
        print ("cwd: ", os.getcwd())

    if (os.path.exists(os.path.join(dir,"data"))):
        gpkg_name = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])
        gpkg_dir = f"data/{gpkg_name}"
    else:
        return

    filled_dot = '●'

    if (setup_simulation):
        
        if verbosity >=1:
            print(filled_dot, gpkg_name, end="")

        
        if len(forcing_files) > 0:
            id = int(gpkg_name[:-5].split("_")[1])
            forcing_file = [f for f in forcing_files if str(id) in f]
            if len(forcing_file) == 1:
                forcing_dir = forcing_file[0]
            else:
                if verbosity >=2:
                    print("Forcing file .nc does not exist for this gpkg, continuing to the next gpkg")
                if verbosity >=1:
                    print (colors.RED + "  Failed " + colors.END )
                return
        elif is_netcdf_forcing:
            try:
                forcing_dir = glob.glob("data/forcing/*.nc")[0]
            except:
                if verbosity >=2:
                    print("Forcing file does not exist under data/forcing, continuing to the next gpkg")
                if verbosity >=1:
                    print (colors.RED + "  Failed " + colors.END )
                return
        else:
            forcing_dir = "data/forcing"
            if (not os.path.exists(forcing_dir)):
                if verbosity >=2:
                    print(f"Forcing file does not exist under {forcing_dir}, continuing to the next gpkg")
                if verbosity >=1:
                    print (colors.RED + "  Failed " + colors.END )
                return

        assert os.path.exists(forcing_dir)

    config_dir = os.path.join(dir,"configs")
    json_dir   = os.path.join(dir, "json")
    gpkg_dir   = os.path.join(dir, gpkg_dir)
    sim_output_dir = os.path.join(dir, "outputs")
    
    helper.create_clean_dirs(dir, config_dir, json_dir, setup_simulation = setup_simulation,
                             rename_existing_simulation = rename_existing_simulation, clean = clean)

    if (not setup_simulation):
        return

    workflow_driver = os.path.join(workflow_dir, "generate_files/driver.py")

    driver = f'python {workflow_driver} -gpkg {gpkg_dir} -ngen {ngen_dir} -f {forcing_dir} \
    -o {config_dir} -m {model_option} -p {precip_partitioning_scheme} -r {surface_runoff_scheme} -t \'{simulation_time}\' \
    -netcdf {is_netcdf_forcing} -troute {is_routing} -json {json_dir} -v {verbosity} -c {is_calibration} \
    -sout {sim_output_dir}'

    failed = subprocess.call(driver, shell=True)

    if (not failed):
        id_full = str(gpkg_name[:-5].split("_")[1])
        basin_ids.append(str(id_full))

        x = gpd.read_file(gpkg_dir, layer="divides")
        num_cats.append(len(x["divide_id"]))

    if verbosity >=1:
        result = "Passed" if not failed else "Failed" 
        print (colors.GREEN + "  %s "%result + colors.END )

    return basin_ids, num_cats

############################### MAIN LOOP #######################################

def main(forcing_files, nproc = 4):
    
    basins_passed = os.path.join(root_dir,"basins_passed.csv")
    
    if (os.path.exists(basins_passed)):
        os.remove(basins_passed)

    basin_ids = []
    num_cats  = []

    # create a pool of processors using multiprocessing tool
    pool = multiprocessing.Pool(processes=nproc)
    
    #print ("CPU:", multiprocessing.cpu_count())

    partial_generate_files_catchment = partial(generate_catchment_files, forcing_files=forcing_files)

    # map catchments to each processor
    results = pool.map(partial_generate_files_catchment, gpkg_dirs)
    results = [result for result in results if result is not None]

    # collect results from all processes
    for result in results:
        basin_ids.extend(result[0])
        num_cats.extend(result[1])

    # Write results to CSV
    with open(basins_passed, 'w', newline='') as file:
        dat = zip(basin_ids, num_cats)
        writer = csv.writer(file)
        writer.writerow(['basin_id', 'n_cats'])
        writer.writerows(dat)

    pool.close()
    pool.join()

    return len(num_cats)

if __name__ == "__main__":

    start_time = time.time()
    
    if (verbosity >=2):
        print (simulation_time)

    if (clean[0] == "all"):
        check = input("\nDo you really want to delete all except \'data\' directory? you will lose all ngen output data: ")
        if check.lower() in ["y", "yes"]:
            print ("Deleting all existing simulation data except \'data\' directory.")
        elif check.lower() in ["n", "no"]:
            sys.exit("Quiting...")
    
    ############ CHECKS ###################
    assert (os.path.exists(root_dir))
    assert (os.path.exists(workflow_dir))
    assert (os.path.exists(ngen_dir))
    ######################################

    if (not os.path.exists(os.path.join(workflow_dir, "generate_files"))):
        sys.exit("check `workflow_dir`, it should be the parent directory of `generate_files` directory")

    all_dirs = glob.glob(root_dir + "/*/", recursive = True)
    gpkg_dirs = [g for g in all_dirs if "failed_cats" not in g] # remove the failed_cats directory
 
    forcing_files = []
    if (is_netcdf_forcing):
        try:
            nc_forcing_dir  = dsim['nc_forcing_dir']
            if (not os.path.exists(nc_forcing_dir)):
                sys.exit(f"Forcing directory does not exist. Provided: {nc_forcing_dir}")

            forcing_files = glob.glob(os.path.join(nc_forcing_dir, "*.nc"), recursive = True)
            assert (len(forcing_files) > 0)
        except:
            if (verbosity >=2):
                print ("Forcing stored in the local sub directory (data/forcing)")
            
    success_ncats = main(forcing_files, nproc = num_processors_config)

    end_time = time.time()
    total_time = end_time - start_time # in seconds

    print ("================== SUMMARY ===============================")
    print("| Total time         = %s [sec], %s [min]" % (round(total_time,4), round(total_time/60.,4)))
    print("| Total no of basins = %s "% len(gpkg_dirs))
    print("| Succeeded          = %s "% success_ncats)
    print("| Failed             = %s "% (len(gpkg_dirs)-success_ncats))
    print ("==========================================================")

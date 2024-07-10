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

import helper
# Note #1: from the command line just run 'python path_to/main.py'
# Note #2: make sure to adjust the following required arguments
# Note #3: several model coupling options are available, the script currently supports a few of them, for full list see
#          below the coupled_models_option


############################# Required Arguments ###################################
### Specify the following four directories (change according to your settings)
# root_dir     : geopackage(s) directory
# forcing_dir  : lumped forcings directory (pre-downloaed forcing data for each catchment (.csv or .nc))
# ngen_dir     : nextgen directory path
# config_dir   : config directory path (all config files will be stored here)

### Specify the following model options
# simulation_time            : simulation start/end times (example is given below)
# model_option               : model option (see available options below)
# surface_runoff_scheme      : surface runoff scheme for CFE and LASAM OPTION=[GIUH, NASH_CASCADE]
# precip_partitioning_scheme : preciptation partitioning scheme for CFE OPTION=[Schaake, Xinanjiang]
# is_netcdf_forcing          : True if forcing data is in netcdf format, otherwise False
# clean_all                  : delete all old/existing config files directories
# partition_pgkg             : Set to True for partitioning the geopackage for a parallel ngen run

#NOTE: The script assumes that .gpkg files are stored under cat_id/data/gage_id.gpkg (modify this part according to your settings)
################################################ ###################################


#################################################################################
############################### MAIN LOOP #######################################
#################################################################################

def main():
    
    basins_passed = os.path.join(root_dir,"basins_passed.csv")
    
    if (os.path.exists(basins_passed)):
        os.remove(basins_passed)

    basin_ids = []
    nproc_lst = []

    
    for dir in gpkg_dirs:
        os.chdir(dir)

        if (verbosity >=1):
            print ("cwd: ", os.getcwd())
        
        gpkg_name = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])  # <---- modify this line according to local settings
        gpkg_dir  = f"data/{gpkg_name}"                                   # <---- modify this line according to local settings


        if (len(forcing_files) > 0):
            id =  int(gpkg_name[:-5].split("_")[1]) # -5 is to remove .gpkg from the string
            forcing_file = [f for f in forcing_files if str(id) in f]
            if(len(forcing_file) == 1):
                forcing_dir = forcing_file[0]
            else:
                print ("Forcing file .nc does not exist for this gpkg, continuing to the next gpkg")
                continue

        elif (is_netcdf_forcing):
            forcing_dir = glob.glob("data/forcing/*.nc")[0]
        else:
            forcing_dir = "data/forcing"

        
        assert (os.path.exists(forcing_dir))
        
        if (verbosity >=0):
            print("=========================================")
            print ("Running : ", gpkg_dir)
        
        # config_dir and json_dir are simply names of the directories (not paths) and are created under the cwdir
        config_dir = "configs" #+ model_option
        json_dir   = "json"
        
        helper.create_clean_dirs(dir, config_dir, json_dir, setup_another_simulation, rename_existing_simulation, clean_all)
        
        
    
        workflow_driver = os.path.join(workflow_dir,"driver.py")
        
        driver = f'python {workflow_driver} -gpkg {gpkg_dir} -ngen {ngen_dir} -f {forcing_dir} \
        -o {config_dir} -m {model_option} -p {precip_partitioning_scheme} -r {surface_runoff_scheme} -t \'{simulation_time}\' \
        -netcdf {is_netcdf_forcing} -troute {is_routing} -json {json_dir} -v {verbosity}'

        result = subprocess.call(driver,shell=True)


        #####################################################################
        nproc = 1
        # Parition geopackage
        if(partition_gpkg):
            if (os.path.exists(f"{ngen_dir}/cmake_build/partitionGenerator")):
            
                x = gpd.read_file(gpkg_dir, layer="divides")
                num_div = len(x["divide_id"])
                #nproc = 1
                if (num_div <= 4):
                    nproc = 1
                elif (num_div <= 8):
                    nproc = 2
                elif (num_div <= 16):
                    nproc = 4
                elif(num_div <= 32):
                    nproc = 8
                elif(num_div <= 64):
                    nproc = 12
                elif(num_div <= 96):
                    nproc = 16
                else:
                    nproc = 20
                #fpar = os.path.join("data", gpkg_name[:-5].split(".")[0] + f"-par{nproc}.json")     # -5 is to remove .gpkg from the string
                fpar = os.path.join(json_dir, gpkg_name[:-5].split(".")[0] + f"-par{nproc}.json")     # -5 is to remove .gpkg from the string
                partition=f"{ngen_dir}/cmake_build/partitionGenerator {gpkg_dir} {gpkg_dir} {fpar} {nproc} \"\" \"\" "
                if (nproc > 1):
                    result = subprocess.call(partition,shell=True)

        id_full =  str(gpkg_name[:-5].split("_")[1]) # -5 is to remove .gpkg from the string, include leading zero
        basin_ids.append(str(id_full))
        nproc_lst.append(nproc)

        with open(basins_passed, 'w', newline='') as file:
            dat = zip(basin_ids, nproc_lst)
            writer = csv.writer(file)
            writer.writerow(['basin_id', 'nproc'])
            writer.writerows(dat)
        break

if __name__ == "__main__":
    
    with open(os.path.dirname(sys.argv[0])+"/input.yaml", 'r') as file:
        d = yaml.safe_load(file)


    workflow_dir = d["workflow_dir"]
    root_dir     = d["root_dir"]
    #nc_forcing_dir  = "/Users/ahmadjan/Core/SimulationsData/projects/ngen_evaluation_camels/forcings" # provide only if all .nc files are stored in one directory
    ngen_dir     = d["ngen_dir"]

    # simulation time format YYYYMMDDHHMM (YYYY, MM, DD, HH, MM)
    simulation_time            = d["simulation_time"]
    model_option               = d['model_option']
    precip_partitioning_scheme = d['precip_partitioning_scheme']
    surface_runoff_scheme      = d['surface_runoff_scheme']
    is_netcdf_forcing          = d['is_netcdf_forcing']
    clean_all                  = d['clean_all']
    partition_gpkg             = d['partition_gpkg']
    is_routing                 = d['is_routing']
    verbosity                  = d['verbosity']    # 0 = none, 1=low, 2=high
    setup_another_simulation   = d['setup_another_simulation']
    rename_existing_simulation = d['rename_existing_simulation']

    if (verbosity >=1):
        print (simulation_time)

    ############ CHECKS ###################
    assert (os.path.exists(root_dir))
    assert (os.path.exists(workflow_dir))
    assert (os.path.exists(ngen_dir))
    ######################################

    gpkg_dirs = glob.glob(root_dir + "/*/", recursive = True)

    forcing_files = []
    if (is_netcdf_forcing):
        try:
            forcing_files = glob.glob(os.path.join(nc_forcing_dir, "*.nc"), recursive = True)
            assert (len(forcing_files) > 0)
        except:
            if (verbosity >=1):
                print ("Forcing stored in the local sub directories")
            
    main()

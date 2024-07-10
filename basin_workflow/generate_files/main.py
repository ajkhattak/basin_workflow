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
# root_dir     : geopackage(s) directory (format root_dir/GAUGE_ID see below)                 
# forcing_dir  : lumped forcings directory (pre-downloaed forcing data for each catchment (.csv or .nc); only need if forcing directory is outside the structure of the root_dir described below)
# ngen_dir     : nextgen directory path
# config_dir   : config directory path (all config files will be stored here)

### Specify the following model options
# simulation_time            : string  | simulation start/end times; format YYYYMMDDHHMM (YYYY, MM, DD, HH, MM)
# model_option               : string  | model option (see available options below)
# surface_runoff_scheme      : string  | surface runoff scheme for CFE and LASAM OPTION=[GIUH, NASH_CASCADE]
# precip_partitioning_scheme : string  | preciptation partitioning scheme for CFE OPTION=[Schaake, Xinanjiang]
# is_netcdf_forcing          : boolean | True if forcing data is in netcdf format
# clean_all                  : boolean | True to delete all old/existing directories (it won't delete the geopackage or forcing data)
# partition_pgkg             : boolean | True to partition the geopackage for a parallel ngen run
# setup_another_simulation   : boolean | for multiple simulation sets such as cfe1.0, cfe2.0, LASAM for the same basins
# rename_existing_simulation : string  | move the existing simulation set (json, configs, outputs dirs) to this directory, e.g. "sim_cfe1.0"

################################################ ###################################

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


############################### MAIN LOOP #######################################

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

        if (verbosity >=0):
            print("=========================================")
            print ("Running : ", gpkg_dir)

        if (len(forcing_files) > 0):
            id =  int(gpkg_name[:-5].split("_")[1]) # -5 is to remove .gpkg from the string
            forcing_file = [f for f in forcing_files if str(id) in f]
            if(len(forcing_file) == 1):
                forcing_dir = forcing_file[0]
            else:
                print ("Forcing file .nc does not exist for this gpkg, continuing to the next gpkg")
                continue

        elif (is_netcdf_forcing):
            try:
                forcing_dir = glob.glob("data/forcing/*.nc")[0]
            except:
                print ("Forcing file does not exist under data/forcing, continuing to the next gpkg")
                continue
        else:
            forcing_dir = "data/forcing"

        
        assert (os.path.exists(forcing_dir))
        
        
        
        # config_dir and json_dir are simply names of the directories (not paths) and are created under the cwdir
        config_dir = "configs" #+ model_option
        json_dir   = "json"
        
        helper.create_clean_dirs(dir, config_dir, json_dir, setup_another_simulation,
                                 rename_existing_simulation, clean_all, clean_except_data)
        
        
    
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

        print ("************* DONE ************** ")
        #break

if __name__ == "__main__":
    
    with open(os.path.dirname(sys.argv[0])+"/input.yaml", 'r') as file:
        d = yaml.safe_load(file)


    workflow_dir               = d["workflow_dir"]
    root_dir                   = d["root_dir"]
    ngen_dir                   = d["ngen_dir"]
    simulation_time            = d["simulation_time"]
    model_option               = d['model_option']
    precip_partitioning_scheme = d['precip_partitioning_scheme']
    surface_runoff_scheme      = d['surface_runoff_scheme']
    is_netcdf_forcing          = d.get('is_netcdf_forcing',True)
    clean_all                  = d.get('clean_all', False)
    clean_except_data          = d.get('clean_except_data',False)
    partition_gpkg             = d.get('partition_gpkg', False)
    is_routing                 = d.get('is_routing', False)
    verbosity                  = d.get('verbosity',0)    # 0 = none, 1=low, 2=high
    setup_another_simulation   = d.get('setup_another_simulation', False)
    rename_existing_simulation = d.get('rename_existing_simulation', "")
    
    if (verbosity >=1):
        print (simulation_time)

    check = input("\nDo you really want to delete all except \'data\' directory? you will lose all ngen output data: ")
    if check.lower() in ["y", "yes"]:
        print ("Deleting all existing simulation data except \'data\' directory.")
    elif check.lower() in ["n", "no"]:
        print("Quiting...")
        quit()
        
    ############ CHECKS ###################
    assert (os.path.exists(root_dir))
    assert (os.path.exists(workflow_dir))
    assert (os.path.exists(ngen_dir))
    ######################################

    gpkg_dirs = glob.glob(root_dir + "/*/", recursive = True)

    forcing_files = []
    if (is_netcdf_forcing):
        try:
            nc_forcing_dir  = d['nc_forcing_dir']
            forcing_files = glob.glob(os.path.join(nc_forcing_dir, "*.nc"), recursive = True)
            assert (len(forcing_files) > 0)
        except:
            if (verbosity >=1):
                print ("Forcing stored in the local sub directory (data/forcing)")
            
    main()

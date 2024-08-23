############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : July 5, 2024
############################################################################################
import os, sys
import pandas as pd
import subprocess
import glob
import yaml
import platform
from generate_files import configuration
import json
from pathlib import Path

os_name = platform.system()
infile  = sys.argv[1]

with open(infile, 'r') as file:
    d = yaml.safe_load(file)

dsim = d['simulations']
workflow_dir     = d["workflow_dir"]
output_dir       = d["output_dir"]
ngen_dir         = dsim["ngen_dir"]
nproc            = int(dsim.get('num_processors_sim', 1))
nproc_adaptive   = int(dsim.get('num_processors_adaptive', True))
is_calibration   = dsim.get('is_calibration', False)
simulation_time  = json.loads(dsim["simulation_time"])

#
#
def run_ngen_without_calibration():
    
    infile = os.path.join(output_dir, "basins_passed.csv")
    indata = pd.read_csv(infile, dtype=str)

    ngen_exe = os.path.join(ngen_dir, "cmake_build/ngen")

    
    for id, ncats in zip(indata["basin_id"], indata['n_cats']):

        ncats = int(ncats)
        
        dir = os.path.join(output_dir, id)
        os.chdir(dir)

        gpkg_name  = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])
        gpkg_file  = f"data/{gpkg_name}" 

        nproc_local = nproc

        file_par = ""
        if (nproc_local > 1):
            nproc_local, file_par = generate_partition_basin_file(ncats, gpkg_file)
        
        print ("Running basin %s on cores %s ********"%(id, nproc_local), flush = True)
        
        realization = glob.glob("json/realization_*.json")
        
        assert (len(realization) == 1)

        realization = realization[0]
        
        if (nproc_local == 1):
            run_cmd = f'{ngen_exe} {gpkg_file} all {gpkg_file} all {realization}'
        else:
            run_cmd = f'mpirun -np {nproc_local} {ngen_exe} {gpkg_file} all {gpkg_file} all {realization} {file_par}'

        if os_name == "Darwin":
            run_cmd = f'PYTHONEXECUTABLE=$(which python) {run_cmd}'
        
        print (f"Run command: {run_cmd} ", flush = True)
        result = subprocess.call(run_cmd,shell=True)

    
def run_ngen_with_calibration():

    infile = os.path.join(output_dir, "basins_passed.csv")
    indata = pd.read_csv(infile, dtype=str)
   
    path = Path(sys.argv[0]).resolve() # get the absolute path
    ngen_cal_basefile = os.path.join(path.parent, "configs", "input_calib.yaml")
    
    for id, ncats in zip(indata["basin_id"], indata['n_cats']):

        ncats = int(ncats)
        
        dir = os.path.join(output_dir, id)
        os.chdir(dir)

        gpkg_file = glob.glob(dir + "/data/*.gpkg")[0]
        gpkg_name  = os.path.basename(gpkg_file).split(".")[0]
        nproc_local = nproc
        
        start_time = pd.Timestamp(simulation_time['start_time']).strftime("%Y%m%d%H%M")
        
        #troute_output_file = os.path.join(dir, "outputs/troute", "troute_output_{}.csv".format(start_time))
        troute_output_file = os.path.join(dir, "outputs/troute", "flowveldepth_{}.csv".format(gpkg_name))
        conf_dir = os.path.join(dir,"configs")

        file_par = ""
        if (nproc_local > 1):
            nproc_local, file_par = generate_partition_basin_file(ncats, gpkg_file)
            file_par = os.path.join(dir, file_par)
        print ("Running basin %s on cores %s ********"%(id, nproc_local), flush = True)
        
        realization = glob.glob(dir+"/json/realization_*.json")

        assert (len(realization) == 1)

        realization = realization[0]

        configuration.write_calib_input_files(gpkg_file = gpkg_file,
                                              ngen_dir = ngen_dir,
                                              conf_dir = conf_dir,
                                              realz_file = realization,
                                              realz_file_par = file_par,
                                              ngen_cal_basefile = ngen_cal_basefile,
                                              num_proc = nproc_local,
                                              troute_output_file = troute_output_file)
        #quit()
        run_command = f"python -m ngen.cal configs/calib_config.yaml"  
        result = subprocess.call(run_command,shell=True)

#####################################################################
def generate_partition_basin_file(ncats, gpkg_file):

    nproc_local = nproc
    json_dir   = "json"

    if (ncats <= nproc_local):
        nproc_local = ncats
    elif(nproc_adaptive):
        nproc_local = min(int(ncats/nproc_local), 20)

    fpar = " "
    
    if (nproc_local > 1):
        fpar = os.path.join(json_dir, f"partition_{nproc_local}.json")
        partition=f"{ngen_dir}/cmake_build/partitionGenerator {gpkg_file} {gpkg_file} {fpar} {nproc_local} \"\" \"\" "
        result = subprocess.call(partition,shell=True)

    return nproc_local, fpar

if __name__ == "__main__":
    
    if (nproc > 1 and not os.path.exists(f"{ngen_dir}/cmake_build/partitionGenerator")):
        sys.exit("Partitioning geopackage is requested but partitionGenerator does not exit! Quitting...")


    if (not is_calibration):
        print ("Running NextGen without calibration ...")
        run_ngen_without_calibration()
    else:
        print ("Running NextGen with calibration ...")
        run_ngen_with_calibration()
        

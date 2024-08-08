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
os_name = platform.system()

infile  = sys.argv[1]
#with open(os.path.dirname(sys.argv[0])+"/input.yaml", 'r') as file:
#    d = yaml.safe_load(file)

with open(infile, 'r') as file:
    d = yaml.safe_load(file)
    
workflow_dir     = d["workflow_dir"]
root_dir         = d["root_dir"]
ngen_dir         = d["ngen_dir"]
nproc            = int(d.get('num_processors_sim', 1))
nproc_adaptive   = int(d.get('num_processors_adaptive', True))
is_calibration   = d.get('is_calibration', False)
simulation_time  = json.loads(d["simulation_time"])

def run_ngen_wihtout_calibration():
    
    infile = os.path.join(root_dir, "basins_passed.csv")
    indata = pd.read_csv(infile, dtype=str)

    ngen_exe = os.path.join(ngen_dir, "cmake_build/ngen")

    
    for id, ncats in zip(indata["basin_id"], indata['n_cats']):

        ncats = int(ncats)
        
        dir = os.path.join(root_dir, id)
        os.chdir(dir)

        gpkg_name     = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])  # <---- modify this line according to local settings
        gpkg_file      = f"data/{gpkg_name}"                                   # <---- modify this line according to local settings

        nproc_local = nproc
        
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
        #break
    
def run_ngen_with_calibration():

    infile = os.path.join(root_dir, "basins_passed.csv")
    indata = pd.read_csv(infile, dtype=str)

    #ngen_exe = os.path.join(ngen_dir, "cmake_build/ngen")

    ngen_cal_config_dir  = os.path.join(os.path.dirname(sys.argv[0]),"configs")
    ngen_cal_file = os.path.join(ngen_cal_config_dir, "input_calib.yaml")
    
    for id, ncats in zip(indata["basin_id"], indata['n_cats']):

        ncats = int(ncats)
        
        dir = os.path.join(root_dir, id)
        os.chdir(dir)

        #gpkg_name   = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])  # <---- modify this line according to local settings
        #gpkg_dir    = f"data/{gpkg_name}"                                   # <---- modify this line according to local settings

        gpkg_file = glob.glob(dir + "/data/*.gpkg")[0]
        nproc_local = nproc
        
        start_time = pd.Timestamp(simulation_time['start_time']).strftime("%Y%m%d%H%M")
        
        troute_output_file = os.path.join(dir, "outputs/troute", "troute_output_{}.csv".format(start_time))
        print ( troute_output_file)
        cal_dir = os.path.join(dir,"configs")
        
        if (nproc_local > 1):
            nproc_local, file_par = generate_partition_basin_file(ncats, gpkg_file)
        
        print ("Running basin %s on cores %s ********"%(id, nproc_local), flush = True)
        
        realization = glob.glob(dir+"/json/realization_*.json")

        print ("REALL: ", realization, dir)
        assert (len(realization) == 1)

        realization = realization[0]

        
        configuration.write_calib_input_files(gpkg_file = gpkg_file, ngen_dir = ngen_dir, cal_dir = cal_dir,
                                              real_file = realization, ngen_cal_file = ngen_cal_file,
                                              num_proc = nproc_local, troute_output_file = troute_output_file)
        """
        if (nproc_local == 1):
            run_command = f"python -m ngen.cal {workflow_dir}/configs/input_calib.yaml"  
            
            #run_cmd = f'{ngen_exe} {gpkg_dir} all {gpkg_dir} all {realization}'
        else:
            run_cmd = f'mpirun -np {nproc_local} {ngen_exe} {gpkg_dir} all {gpkg_dir} all {realization} {file_par}'

        if os_name == "Darwin":
            run_cmd = f'PYTHONEXECUTABLE=$(which python) {run_cmd}'
        
        print (f"Run command: {run_cmd} ", flush = True)
        result = subprocess.call(run_cmd,shell=True)
        #break
        
        """
        print ("current: ", os.getcwd())
        run_command = f"python -m ngen.cal configs/calib_config.yaml"  
        result = subprocess.call(run_command,shell=True)

#####################################################################
def generate_partition_basin_file(ncats, gpkg_file):

    nproc_local = nproc
    json_dir   = "json"

    if(nproc_adaptive):
        if (ncats <= nproc_local):
            nproc_local = ncats
        if (ncats < nproc_local):
            nproc_local = 1
        elif (ncats <= 150):
            nproc_new = int(ncats/nproc_local)
        else:
            nproc_local = 30
                
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
        run_ngen_without_calibration()
    else:
        run_ngen_with_calibration()
        

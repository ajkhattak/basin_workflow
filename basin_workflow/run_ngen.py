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

os_name = platform.system()

with open(os.path.dirname(sys.argv[0])+"/input.yaml", 'r') as file:
    d = yaml.safe_load(file)

    
workflow_dir     = d["workflow_dir"]
root_dir         = d["root_dir"]
ngen_dir         = d["ngen_dir"]
nproc            = int(d.get('num_processors_sim', 1))
nproc_adaptive   = int(d.get('num_processors_adaptive', True))


def main():
    
    infile = os.path.join(root_dir, "basins_passed.csv")
    indata = pd.read_csv(infile, dtype=str)

    ngen_exe = os.path.join(ngen_dir, "cmake_build/ngen")

    
    for id, ncats in zip(indata["basin_id"], indata['n_cats']):

        ncats = int(ncats)
        
        dir = os.path.join(root_dir, id)
        os.chdir(dir)

        gpkg_name     = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])  # <---- modify this line according to local settings
        gpkg_dir      = f"data/{gpkg_name}"                                   # <---- modify this line according to local settings

        nproc_local = nproc
        
        if (nproc_local > 1):
            nproc_local, file_par = generate_partition_basin_file(ncats, gpkg_name, gpkg_dir)
        
        print ("Running basin %s on cores %s ********"%(id, nproc_local), flush = True)
        
        realization = glob.glob("json/realization_*.json")
        
        assert (len(realization) == 1)

        realization = realization[0]
        
        if (nproc_local == 1):
            run_cmd = f'{ngen_exe} {gpkg_dir} all {gpkg_dir} all {realization}'
        else:
            run_cmd = f'mpirun -np {nproc_local} {ngen_exe} {gpkg_dir} all {gpkg_dir} all {realization} {file_par}'

        if os_name == "Darwin":
            run_cmd = f'PYTHONEXECUTABLE=$(which python) {run_cmd}'
        
        print (f"Run command: {run_cmd} ", flush = True)
        result = subprocess.call(run_cmd,shell=True)
        #break
    
        

#####################################################################
def generate_partition_basin_file(ncats, gpkg_name, gpkg_dir):

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
        #fpar = os.path.join(json_dir, gpkg_name[:-5].split(".")[0] + f"-par{nproc}.json")     # -5 is to remove .gpkg from the string
        fpar = os.path.join(json_dir, f"partition_{nproc_local}.json")
        partition=f"{ngen_dir}/cmake_build/partitionGenerator {gpkg_dir} {gpkg_dir} {fpar} {nproc_local} \"\" \"\" "
        result = subprocess.call(partition,shell=True)

    return nproc_local, fpar

if __name__ == "__main__":
    
    if (nproc > 1 and not os.path.exists(f"{ngen_dir}/cmake_build/partitionGenerator")):
        print ("Partitioning geopackage is requested but partitionGenerator does not exit! Quitting...")
        quit()
    #elif (partition_basin == 1):
    #    print ("Partitioning geopackage is requested but partition_num_processors = 1. Quitting...")
    #    quit()

    main()

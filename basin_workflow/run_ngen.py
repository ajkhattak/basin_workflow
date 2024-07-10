############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : July 5, 2024
############################################################################################
import os, sys
import pandas as pd
import subprocess
import glob

root_dir     = "/Users/ahmadjan/Core/SimulationsData/projects/ngen_evaluation_camels/basins516_model_attr"
workflow_dir = "/Users/ahmadjan/codes/workflows/basin_workflow/basin_workflow/"
ngen_dir     = "/Users/ahmadjan/codes/ngen/ngen"

infile = os.path.join(root_dir, "basins_passed.csv")
indata = pd.read_csv(infile, dtype=str)

ngen_exe = os.path.join(ngen_dir, "cmake_build/ngen")

for id, nproc in zip(indata["basin_id"], indata['nproc']):
    print ("Running: Basin %s on cores %s ********"%(id, nproc))

    dir = os.path.join(root_dir, id)
    os.chdir(dir)

    gpkg_name     = os.path.basename(glob.glob(dir + "/data/*.gpkg")[0])  # <---- modify this line according to local settings
    gpkg_dir      = f"data/{gpkg_name}"                                   # <---- modify this line according to local settings

    realization = glob.glob("json/*.json")
    assert (len(realization) <= 2)
    
    if (int(nproc) == 1):
        realization = glob.glob("json/*.json")[0]
        run_cmd = f'{ngen_exe} {gpkg_dir} all {gpkg_dir} all {realization}'
    else:
        continue
        file_par = glob.glob("json/*par*.json")[0]
        realization.remove(file_par)
        realization = realization[0]
        run_cmd = f'mpirun -np {nproc} {ngen_exe} {gpkg_dir} all {gpkg_dir} all {realization} {file_par}'
    
    print (f"Run: {run_cmd}")
    result = subprocess.call(run_cmd,shell=True)
    #break
    
        
#/Users/ahmadjan/codes/ngen/ngen/cmake_build/ngen data/Gage_01047000.gpkg cat-7395 data/Gage_01047000.gpkg nex-7396 json/realization_nom_cfe_pet.json

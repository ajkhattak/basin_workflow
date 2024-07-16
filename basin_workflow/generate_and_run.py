############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : July 16, 2024
############################################################################################

import os, sys
import subprocess
import yaml


workflow_dir = os.path.dirname(sys.argv[0])
generate_configs = f"python {workflow_dir}/generate_files/main.py"

print (generate_configs)
print ("Generating config files...")
result = subprocess.call(generate_configs,shell=True)

print ("**********************************")

run_command = f"python {workflow_dir}/run_ngen.py"

print (run_command)
print ("Running simulations...")
result = subprocess.call(run_command,shell=True)

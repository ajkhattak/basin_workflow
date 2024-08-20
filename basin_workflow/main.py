############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : July 16, 2024
############################################################################################

import os, sys
import subprocess
import yaml
import argparse
from pathlib import Path

path = Path(sys.argv[0]).resolve()
workflow_dir = path.parent


def runner():
    
    if (args.gpkg):
        print ("Generating geopackages...")
        generate_gpkg = f"Rscript {workflow_dir}/giuh_twi/main.R {workflow_dir}/configs/input_config.yaml"
        status = subprocess.call(generate_gpkg,shell=True)

        if (status):
            sys.exit("Failed during generating geopackge(s) step...")
        else:
            print ("DONE \u2713")

    if (args.conf):
        print ("Generating config files...")
        generate_configs = f"python {workflow_dir}/generate_files/main.py {workflow_dir}/configs/input_config.yaml"
        status = subprocess.call(generate_configs,shell=True)

        if (status):
            sys.exit("Failed during generating config files step...")
        else:
            print ("DONE \u2713")
        
    if (args.run):
        print ("Calling Runner ...")
        infile = f"{workflow_dir}/configs/input_config.yaml"
        
        with open(infile, 'r') as file:
            d = yaml.safe_load(file)

        run_command = f"python {workflow_dir}/runner.py {workflow_dir}/configs/input_config.yaml"
        status = subprocess.call(run_command,shell=True)

        if (status):
            sys.exit("Failed during ngen-cal execution...")
        else:
            print ("DONE \u2713")
    
    print ("**********************************")
    
    

if __name__ == "__main__":
    
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-gpkg", action='store_true', help="generate gpkg files")
        parser.add_argument("-conf", action='store_true', help="generate config files")
        parser.add_argument("-run",  action='store_true', help="run nextgen without caliberation")
        #parser.add_argument("-cal",  action='store_true', help="run nextgen with caliberation")
        
        args = parser.parse_args()
    except:
        parser.print_help()
        sys.exit(0)


    if (len(sys.argv) < 2):
        print ("No arguments are provide, printing help()")
        parser.print_help()
        sys.exit(0)

    runner()

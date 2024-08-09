## Instructions for computing Geomorphological Instantaneous Unit Hydrograph (GIUH) and Topographic Wetness Index (TWI)
This set of scripts offers a workflow for establishing basin-scale simulations from the ground up 
and executing them within the NextGen framework.

- R-based scripts, leveraging the [WhiteBox](https://www.whiteboxgeo.com/manual/wbw-user-manual/book/tool_help.html) tool, a geospatial data analysis software,
  are provided for the computation of GIUH and TWI.
  Detailed instruction are available [here](https://github.com/ajkhattak/SoilMoistureProfiles/tree/ajk/auto_py_script/basin_workflow/giuh_twi/main.R)
  
- Python-based scripts are provided for generating model(s) (standalone and coupled) configuration files and the
  NextGen realization file. Detailed instruction can be found [here](https://github.com/ajkhattak/SoilMoistureProfiles/tree/ajk/auto_py_script/basin_workflow/generate_files/main.py)

### Configuration files
The workflow needs three configuration files, the options and paths need to be adjusted to local settings, please see these files for further instruction.

- config file for option `-gg` (see [here](https://github.com/ajkhattak/basin_workflow/blob/master/basin_workflow/configs/input_gpkg_params.yaml)). Changes to this file needed.
- config file for option `-cf` (see [here](https://github.com/ajkhattak/basin_workflow/blob/master/basin_workflow/configs/input_config.yaml)). Changes to this file needed.
- config file for option `-rc` (see [here](https://github.com/ajkhattak/basin_workflow/blob/master/basin_workflow/configs/input_calib.yaml)). Changes to this file needed. 

### Running the workflow
- run `python /Users/ahmadjan/codes/workflows/basin_workflow/basin_workflow/main.py OPTIONS = [-gg -cf -r -rc]
-  `-gg` option downloads geopackage(s) given gage ID, computes TWI, GIUH, and Nash parameters, and append them along with other model parameters (from S3 bucket)
   as `model-attributes`
- `-cf` option generates configuration files for the selected models
- `-r` runs nextgen without calibration
- `-rc` runs nextgen with calibration using [ngen-cal](https://github.com/NOAA-OWP/ngen-cal)

### NOTE
This workflow does not download basin's forcing data. Users are required to provide the forcing data. 
General instructions on how to download forcing data are documented [here](https://github.com/ajkhattak/SoilMoistureProfiles/blob/ajk/auto_py_script/basin_workflow/FORCING.md).

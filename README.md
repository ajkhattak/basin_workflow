# BasinWorkflow

**Description**


## Dependencies

Describe any dependencies that must be installed for this software to work.

## Installation

Detailed instructions on how to install, configure, and get the project running.
This should be frequently tested to ensure reliability. Alternatively, link to
a separate [INSTALL](INSTALL.md) document.

## Configuration

If the software is configurable, describe it in detail, either here or in other documentation to which you link.

## Usage

Show users how to use the software.
Be specific.
Use appropriate formatting when showing code snippets.


### Instructions for computing Geomorphological Instantaneous Unit Hydrograph (GIUH) and Topographic Wetness Index (TWI)
This set of scripts offers a workflow for establishing basin-scale simulations from the ground up 
and executing them within the NextGen framework.

- R-based scripts, leveraging the [WhiteBox](https://www.whiteboxgeo.com/manual/wbw-user-manual/book/tool_help.html) tool, a geospatial data analysis software,
  are provided for the computation of GIUH and TWI.
  Detailed instruction are available [here](https://github.com/ajkhattak/SoilMoistureProfiles/tree/ajk/auto_py_script/basin_workflow/giuh_twi/main.R)
  
- Python-based scripts are provided for generating model(s) (standalone and coupled) configuration files and the
  NextGen realization file. Detailed instruction can be found [here](https://github.com/ajkhattak/SoilMoistureProfiles/tree/ajk/auto_py_script/basin_workflow/generate_files/main.py)


### Configuration steps
  - `git clone https://github.com/ajkhattak/basin_workflow`
  - cd basin_workflow/basin_workflow
  - `git submodule update --init`
  - `pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'`
  - `pip install extern/ngen-cal/python/ngen_config_gen`
  - `pip install hydrotools.events`
  - `pip install -e ./extern/ngen_cal_plugins`
    
#### Forcing data downloaders
  - Currently supports Nels and Jonathan tools available [here](https://github.com/ajkhattak/CIROH_DL_NextGen)
  - `mkdir ~/.venv_forcing` (preferably in your home directory and don't change the name of the env othewise it needs to be explicitly provided in the config file)
  - `python -m venv ~/.venv_forcing`
  - `source ~/.venv_forcing/bin/activate`
  - `pip install -r extern/CIROH_DL_NextGen/forcing_prep/requirements.txt`

### Setup configuration files
The workflow needs two configuration files, provided [here](https://github.com/ajkhattak/basin_workflow/blob/master/basin_workflow/configs/). Workflow setup and model options and paths need to be adjusted to local settings. Please see the configuration files for further details.

### Running the workflow
```
python /Users/ahmadjan/codes/workflows/basin_workflow/basin_workflow/main.py OPTIONS = [-gpkg -forc -conf -run]
```
Note: These options can be run individually or all together by `path_to/main.py -gpkg -conf -run`. The `-gpkg` is an expensive step, should be run once to get the desired basin geopacakge.

- Option: `-gpkg` downloads geopackage(s) given a gage ID(s), computes TWI, GIUH, and Nash parameters, and append them to the geopackage along with other model parameters (from S3 bucket) as `model-attributes`
- Option: `-conf` generates configuration files for the selected models/basins
- Option: `-run` runs NextGen simulations with and without calibration. The workflow uses [ngen-cal](https://github.com/NOAA-OWP/ngen-cal) for calibration


### NOTE
This workflow does not download basin's forcing data. The user is required to provide the forcing data. 
General instructions on how to download forcing data are documented [here](https://github.com/ajkhattak/SoilMoistureProfiles/blob/ajk/auto_py_script/basin_workflow/FORCING.md).

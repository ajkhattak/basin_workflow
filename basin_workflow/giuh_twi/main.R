# @author Ahmad Jan Khattak
# @email ahmad.jan@noaa.gov
# @date  December 22, 2023

# The script downloads geopackge(s) given USGS gauge id(s) (also can read gpkg from the disk)
# Computes TWI, GIUH, Nash cascade parameters, and extracts model attributes from source,
# source could either be hydrofabric S3 endpoint or local sync hydrofabric (preferred for speed)

# INPUT  : yaml file (see below)
# OUTPUT : a geopackage with all model parameters, which is used for generating config and realization files

######################## REQUIRED INPUT #######################################
# Key steps are hihglight as:
# STEP #1: Setup (REQUIRED) (main.R)
# STEP #2: Options: Provide gage ID or list of gage IDs or set path to work with already download geopackages (main.R)
# Workflow substeps
#   STEP #3: Download geopackage (if needed) (inside driver.R)
#   STEP #4: Add model attributes to the geopackage (inside driver.R)
#   STEP #5: Compute TWI and width function (inside driver.R)
#   STEP #6: Compute GIUH (inside driver.R)
#   STEP #7: Compute Nash cascade parameters (N and K) for surface runoff (inside driver.R)
#   STEP #8: Append GIUH, TWI, width function, and Nash cascade parameters to model_attributes layer (inside driver.R)


################################ SETUP #########################################
# STEP #1: INSTALL REQUIRED PACKAGES 
# - set workflow_dir (basin_workflow repository directory)
# - set options for installing/reinstalling hydrofabric and other packages 
# - set dem_infile (defaults to S3 .vrt file)
# - set output_dir (geopackages and DEM files will be stored here)
# - set hf_source (if sync'ed hydrofabric is available, set this path; defaults to S3 end point)

# - reinstall_hydrofabric    # Defaults to FALSE. TRUE updates/overwrites the existing hydrofabric
# - reinstall_arrow          # Defaults to FALSE. old arrow package or arrow installed without S3 support can cause issues, 
                             # typical error msg "Error: NotImplemented: Got S3 URI but Arrow compiled without S3 support"
                             # setting it to TRUE to install arrow package with S3 support 
                             # (see install_load_libs.R for more instructions)
# - dem_infile = "/vsicurl/https://lynker-spatial.s3.amazonaws.com/gridded-resources/dem.vrt"


library(yaml)
args <- commandArgs(trailingOnly = TRUE)

setup <-function() {
  
  if (length(args) == 1) {
    infile_config = args
    print (paste0("Config file provided: ", infile_config))
  } else if (length(args) > 1) {
    stop("Please provide only one argument (input.yaml).")
  } else {
    infile_config <- "/Users/ahmadjan/codes/workflows/basin_workflow/basin_workflow/configs/input_config.yaml"
  }

  if (!file.exists(infile_config)) {
    print(paste0("input config file does not exist, provided: ", infile_config))
    return(1)
  }
  
  inputs = yaml.load_file(infile_config)

  workflow_dir      <<- inputs$workflow_dir
  output_dir        <<- inputs$output_dir
  hf_source         <<- inputs$gpkg_model_params$hf_source
  reinstall_arrow   <<- inputs$gpkg_model_params$reinstall_arrow
  nproc             <<- inputs$gpkg_model_params$number_processors
  reinstall_hydrofabric <<- inputs$gpkg_model_params$reinstall_hydrofabric
  
  source(paste0(workflow_dir, "/giuh_twi/install_load_libs.R"))
  source(glue("{workflow_dir}/giuh_twi/custom_functions.R"))

  use_gage_id   <<- get_param(inputs, "gpkg_model_params$options$use_gage_id$use_gage_id", FALSE)
  gage_ids      <<- get_param(inputs, "gpkg_model_params$options$use_gage_id$gage_ids", NULL)
  
  use_gage_file <<- get_param(inputs, "gpkg_model_params$options$use_gage_file$use_gage_file", FALSE)
  gage_file     <<- get_param(inputs, "gpkg_model_params$options$use_gage_file$gage_file", NULL)
  column_name   <<- get_param(inputs, "gpkg_model_params$options$use_gage_file$column_name", "")
  
  use_gpkg      <<- get_param(inputs, "gpkg_model_params$options$use_gpkg$use_gpkg", FALSE)
  gpkg_dir      <<- get_param(inputs, "gpkg_model_params$options$use_gpkg$gpkg_dir", NULL)
  pattern       <<- get_param(inputs, "gpkg_model_params$options$use_gpkg$pattern", "Gage_")
  
  if (sum(use_gage_id, use_gage_file, use_gpkg) > 1){
    print(glue("Only one condition needs to be TRUE, user provide: \n
             use_gage_id   = {use_gage_id}, \n 
             use_gage_file = {use_gage_file}, \n 
             use_gpkg      = {use_gpkg}"))
    return(1)
  }
  
  if (!file.exists(output_dir)) {
    print(glue("Output directory does not exist, provided: {output_dir}"))
    return(1)
  }
  
  setwd(output_dir)
  wbt_wd(getwd())
  
  return(0)
}

# call setup function to read parameters from config file
result <- setup()
if (result){
  stop("Setup failed!")
}

################################ OPTIONS #######################################

start_time <- Sys.time()
if (use_gage_id == TRUE) {
  ################################ EXAMPLE 1 ###################################
  # For this example either provide a gage ID or a file to read gage IDs from
  # Modify this part according your settings
  
  stopifnot( length(gage_ids) > 0)

  cats_failed <- driver_given_gage_IDs(gage_id = gage_ids, 
                                       output_dir = output_dir, 
                                       hf_source = hf_source,
                                       nproc = nproc
                                       )
  
  
} else if (use_gage_file == TRUE) {
  
  d = read.csv(gage_file,colClasses = c("character")) 
  gage_ids <- d[[column_name]]
  print(paste0("gage_file ", gage_file))
  print (gage_ids)
  
  cats_failed <- driver_given_gage_IDs(gage_id = gage_ids, 
                                       output_dir = output_dir, 
                                       hf_source = hf_source,
                                       nproc = nproc 
                                       )
} else if (use_gpkg == TRUE) {

  gage_files = list.files(gpkg_dir, full.names = FALSE, pattern = pattern)
  
  cats_failed <- driver_given_gpkg(gage_files = gage_files, 
                                   gpkg_dir = gpkg_dir, 
                                   output_dir = output_dir,
                                   hf_source = NULL,
                                   nproc = nproc
                                   )
  
}


end_time <- Sys.time()
time_taken <- as.numeric(end_time - start_time, units = "secs")
print (paste0("Time total = ", time_taken))

print(cats_failed)

################################### DONE #######################################
############################### SET PATHS ######################################
# STEP #2. Load custom .R files
################################################################################

source(glue("{workflow_dir}/src_r/twi_width.R"))
source(glue("{workflow_dir}/src_r/helper.R"))
source(glue("{workflow_dir}/src_r/giuh.R"))
source(glue("{workflow_dir}/src_r/nash_cascade.R"))
source(glue("{workflow_dir}/src_r/driver.R"))

# List all functions - give access to these function to each worker
functions_lst = c("run_driver", "add_model_attributes", "dem_function", "twi_function", 
                  "width_function", "twi_pre_computed_function", "giuh_function", 
                  "Nash_Cascade_Runoff", "get_nash_params", "fun_crop_lower", 
                  "fun_crop_upper")
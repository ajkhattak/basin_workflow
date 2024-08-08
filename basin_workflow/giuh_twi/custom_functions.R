############################### SET PATHS ######################################
# STEP #2. Load custom .R files
################################################################################

source(glue("{workflow_dir}/giuh_twi/twi_width.R"))
source(glue("{workflow_dir}/giuh_twi/helper.R"))
source(glue("{workflow_dir}/giuh_twi/giuh.R"))
source(glue("{workflow_dir}/giuh_twi/nash_cascade.R"))
source(glue("{workflow_dir}/giuh_twi/driver.R"))

# List all functions - give access to these function to each worker
functions_lst = c("run_driver", "add_model_attributes", "dem_function", "twi_function", 
                  "width_function", "twi_pre_computed_function", "giuh_function", 
                  "Nash_Cascade_Runoff", "get_nash_params", "fun_crop_lower", 
                  "fun_crop_upper")
#----------------------- DOWNLOAD GEOPACKAGE ----------------------------------#
# STEP #3: provide USGS gauge id or your own geopackage (single or multiple)
#------------------------------------------------------------------------------#


############################ DRIVER_GIVEN_GAGE_ID ##############################
# main script that loops over all the gage IDs and computes giuh/twi etc.
driver_given_gage_IDs <- function(gage_ids, 
                                  output_dir,
                                  hf_source = NULL,
                                  failed_dir = "failed_cats",
                                  write_attr_parquet = FALSE,
                                  dem_input_file = NULL,
                                  dem_output_dir = "",
                                  nproc = 1) {
  print ("DRIVER GIVEN GAGE ID")
  # create directory to stored catchment geopackage in case of errors or missing data
  #failed_dir = "failed_cats"
  dir.create(failed_dir, recursive = TRUE, showWarnings = FALSE)
  
  if (nproc > parallel::detectCores()) {
    nproc = parallel::detectCores() - 1
  }
  
  # make a cluster of multicores
  cl <- parallel::makeCluster(nproc)
  on.exit(parallel::stopCluster(cl))  # this ensures the cluster is stopped on exit
  
  # Export all environment variables and functions here, so all worker/nodes have access to them
  clusterExport(cl, varlist = c(functions_lst, 
                                "libraries_lst", 
                                "output_dir", 
                                "failed_dir",
                                "write_attr_parquet",
                                "dem_output_dir",
                                "dem_input_file",
                                "hf_source",
                                "as_sqlite"),
                envir = environment())
  
  #evaluate an expression on in the global environment each node of the cluster; here loading packages
  clusterEvalQ(cl, {
    libraries_lst <- get("libraries_lst", environment())
    for (pkg in libraries_lst) {
      suppressPackageStartupMessages(library(pkg, character.only = TRUE))
    }
  })
  
  
  # Initialize and call pb (progress bar)
  
  cats_failed <- pblapply(X = gage_ids, FUN = process_catchment_id, cl = cl, failed_dir)
  
  #stopCluster(cl)
  
  #lapply(X = gage_ids, FUN = process_catchment_id, output_dir = output_dir, failed_dir = failed_dir)
  
  
  setwd(output_dir)
  
  return(cats_failed)
}

#-----------------------------------------------------------------------------#
# Function called by pblapply for parallel processing by each worker/node
# for each catchemnt id
# it calls run_driver for each gage id and computes giuh/twi etc.

process_catchment_id <- function(id, failed_dir) {
  print ("PROCESS CATCHMENT ID FUNCTION")
  # vector contains ID of basins that failed for some reason
  cats_failed <- numeric(0)
  
  # uncomment for debugging, it puts screen outputs to a file
  #log_file <- file("output.log", open = "wt")
  #sink(log_file, type = "output")
  
  cat_dir = glue("{output_dir}/{id}")
  dir.create(cat_dir, recursive = TRUE, showWarnings = FALSE)
  
  setwd(cat_dir)
  wbt_wd(getwd())
  
  # DEM and related files (such as projected/corrected DEMs, and specific contributing area rasters are stored here)
  dem_dir = "dem"
  dir.create(dem_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create("data", recursive = TRUE, showWarnings = FALSE)
  
  failed <- TRUE
  
  tryCatch({
    cat ("Processing catchment: ", id, "\n")
    run_driver(gage_id = id,
               dem_input_file = dem_input_file,
               dem_output_dir = dem_dir, 
               hf_source = hf_source,
               write_attr_parquet = write_attr_parquet
    )
    
    failed <- FALSE
  }, error = function(e) {
    failed <- TRUE
  })
  
  # move (or delete) dem output directory out of the main output directory
  clean_move_dem_dir(id = id, output_dir = output_dir, dem_output_dir = dem_output_dir)
  
  if (failed) {
    cat ("Cat failed:", id, "\n")
    cats_failed <- id
    cat_failed_dir = glue("{output_dir}/{failed_dir}/{id}")
    
    if (file.exists(cat_failed_dir) ) {
      unlink(cat_failed_dir, recursive = TRUE)
    }
    
    file.rename(cat_dir, cat_failed_dir)
    
  }
  else {
    cat ("Cat passed:", id, "\n")
  }
  
  #sink(type = "output")
  #close(log_file)
  
  return(cats_failed)
}

############################ DRIVER_GIVEN_GPKG #################################
# main script that loops over all the geopackages and computes giuh/twi etc.
driver_given_gpkg <- function(gage_files, 
                              gpkg_dir, 
                              output_dir,
                              hf_source = NULL,
                              failed_dir = "failed_cats",
                              dem_output_dir = "",
                              dem_input_file = NULL,
                              write_attr_parquet = FALSE,
                              nproc = 1) {
  
  print ("DRIVER GIVEN GEOPACKAGE FUNCTION")
  # create directory to stored catchment geopackage in case of errors or missing data
  #failed_dir = "failed_cats"
  
  if (dir.exists(failed_dir)) {
    unlink(failed_dir, recursive = TRUE)
  }
  dir.create(failed_dir, recursive = TRUE, showWarnings = FALSE)
  
  if (nproc > parallel::detectCores()) {
    nproc = parallel::detectCores() - 1
  }
  
  # make a cluster of multicores
  cl <- parallel::makeCluster(nproc)
  on.exit(parallel::stopCluster(cl))  # this ensures the cluster is stopped on exit

  # Export all environment variables and functions here, so all worker/nodes have access to them
  clusterExport(cl, varlist = c(functions_lst, 
                                "libraries_lst", 
                                "output_dir", 
                                "failed_dir",
                                "hf_source",
                                "gpkg_dir",
                                "as_sqlite",
				"write_attr_parquet",
                                "dem_output_dir",
				"dem_input_file"),
                envir = environment())
  
  #evaluate an expression on in the global environment each node of the cluster; here loading packages
  clusterEvalQ(cl, {
    libraries_lst <- get("libraries_lst", environment())
    for (pkg in libraries_lst) {
      suppressPackageStartupMessages(library(pkg, character.only = TRUE))
    }
  })
  
  
  # Initialize and call pb (progress bar)
  cats_failed <- pblapply(X = gage_files, FUN = process_gpkg, cl = cl, failed_dir)
  
  #cats_failed <- lapply(X = gage_files, FUN = process_gpkg, failed_dir)
  setwd(output_dir)
  
  return(cats_failed)
}

process_gpkg <- function(gfile, failed_dir) {
  
  print ("PROCESS GPKG FUNCTION")

  # vector contains ID of basins that failed for some reason
  cats_failed <- numeric(0)

  # uncomment for debugging, it puts screen outputs to a file
  #log_file <- file("output.log", open = "wt")
  #sink(log_file, type = "output")

  #id <- as.integer(sub(".*_(.*?)\\..*", "\\1", gfile))
  id <- sub(".*_(.*?)\\..*", "\\1", gfile)
  
  if (is.na(id)) {
     id <- 11111
  }
  
  # check if gage ID is missing a leading zero, does not happens most of the times, but good to check
  #if (as.integer(nchar(id)/2) %% 2 == 1) {
  #  id <- paste(0,id, sep = "")
  #  }

  cat_dir = glue("{output_dir}/{id}")
  dir.create(cat_dir, recursive = TRUE, showWarnings = FALSE)
  
  setwd(cat_dir)
  wbt_wd(getwd())
    
  # DEM and related files (such as projected/corrected DEMs, and specific contributing 
  # area rasters are stored here)
  dem_dir = "dem"
  dir.create(dem_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create("data", recursive = TRUE, showWarnings = FALSE)
  file.copy(gfile, "data")

  failed <- TRUE
  
  tryCatch({
    cat ("Processing catchment: ", id, "\n")

    #local_gpkg_file = gfile # point to original file
    gpkg_name = basename(gfile)

    local_gpkg_file = glue("{cat_dir}/data/{gpkg_name}")
    
    run_driver(is_gpkg_provided = TRUE,
               loc_gpkg_file = local_gpkg_file,
               dem_output_dir = dem_dir,
               dem_input_file = dem_input_file,
               write_attr_parquet = write_attr_parquet
               )
      
    failed <- FALSE
      
    }, error = function(e) {
      failed <- TRUE
    })
  
  # move (or delete) dem output directory out of the main output directory
  clean_move_dem_dir(id = id, output_dir = output_dir, dem_output_dir = dem_output_dir)
  
  if (failed) {
    cat ("Cat failed:", id, "\n")
    cats_failed <- append(cats_failed, id)
    target_failed_cat_dir =  glue("{output_dir}/{failed_dir}/{id}")
    if (dir.exists(target_failed_cat_dir)) {
      unlink(target_failed_cat_dir, recursive = TRUE)
    }
    file.rename(cat_dir, target_failed_cat_dir)
  }
  else {
    cat ("Cat passed:", id, "\n")
  }
  
  #sink(type = "output")
  #close(log_file)
  
  return(cats_failed)

}

############################# RUN_DRIVER ######################################
# main runner function
run_driver <- function(gage_id = NULL, 
                       is_gpkg_provided = FALSE, 
                       dem_input_file = NULL,
                       dem_output_dir,
                       hf_source = NULL,
                       loc_gpkg_file = "",
                       twi_pre_computed_option = FALSE,
                       write_attr_parquet = FALSE) {

  print ("RUN DRIVER FUNCTION")
  
  
  outfile <- " "
  if(!is_gpkg_provided) {
    start.time <- Sys.time()
    fid = glue('USGS-{gage_id}')
    outfile <- glue('data/gage_{gage_id}.gpkg')
    
    if (is.null(hf_source)) {
      hfsubsetR::get_subset(nldi_feature = list(featureSource="nwissite", featureID=fid),
                            outfile = outfile, 
                            hf_version = '2.1.1', 
                            type = 'nextgen',
                            overwrite = TRUE)
      
    } else {
      # if local synchronized hydrofabric exists
      hfsubsetR::get_subset(nldi_feature = list(featureSource="nwissite", featureID=fid),
                            outfile = outfile, 
                            hf_version = '2.1.1', 
                            type = 'nextgen',
                            source = hf_source,
                            lyrs = c("divides", "flowlines", "network", "nexus"),
                            overwrite = TRUE)
      #, 
      #"model-attributes", 'flowpath-attributes'
    }

    time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
    print (paste0("Time (geopackage) = ", time.taken))
    
  } else { 
    outfile <- loc_gpkg_file
    }

 
  ## Stop if .gpkg does not exist

  if (!file.exists(outfile)) {
    print(glue("FILE '{outfile}' DOES NOT EXIST!!"))
    stop()
    }

  div <- read_sf(outfile, 'divides')
  nexus <- read_sf(outfile, 'nexus')
  streams <- read_sf(outfile, 'flowlines')

  ########################## MODELS' ATTRIBUTES ##################################
  # STEP #4: Add models' attributes from the parquet file to the geopackage
  # this TRUE will be changed once synchronized HF bugs are fixed

  if(is.null(hf_source) | TRUE) {
    # print layers before appending model attributes
    layers_before_cfe_attr <- sf::st_layers(outfile)
    #print (layers_before_cfe_attr$name)
    start.time <- Sys.time()

    m_attr <- add_model_attributes(div_infile = outfile, 
                                   write_attr_parquet = write_attr_parquet)
    
    time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
    print (paste0("Time (model attrs) = ", time.taken))    
  } else {
    m_attr <- read_sf(outfile, 'model-attributes')
  }

  layers_after_cfe_attr <- sf::st_layers(outfile)
  #print (layers_after_cfe_attr$name)
  
  ############################### GENERATE TWI ##################################
  # STEP #5: Generate TWI and width function and write to the geopackage
  # Note: The default distribution = 'quantiles'
  
  start.time <- Sys.time()
  dem_function(div_infile = outfile, dem_input_file, dem_output_dir)

  time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
  print (paste0("Time (dem func) = ", time.taken))
  
  print("STEP: Computing TWI and Width function .................")
  start.time <- Sys.time()
  twi <- twi_function(div_infile = outfile, dem_output_dir = dem_output_dir, 
                      distribution = 'simple', nclasses = 30)
  
  width_dist <- width_function(div_infile = outfile, dem_output_dir = dem_output_dir)
  
  twi_dat_values = data.frame(ID = twi$divide_id, twi = twi$fun.twi, 
                              width_dist = width_dist$fun.downslope_fp_length)
  
  # write TWI and width function layers to the geopackage
  names(twi_dat_values)
  colnames(twi_dat_values) <- c('divide_id', 'twi', 'width_dist')
  names(twi_dat_values)

  
  ### NOTES: Pre-computed TWI
  # Note 1: model attributes layer ships with pre-computed TWI distribution with four equal quantiles
  #m_attr$twi_dist_4
  
  # Note 2: The user can also compute their own distribution from the pre-computed TWI using the dataset
  # available at s3://lynker-spatial/gridded-resources/twi.vrt
  
  if (twi_pre_computed_option) {
    twi_pre_computed <- twi_pre_computed_function(div_infile = outfile, distribution = 'simple', 
                                                  nclasses = 30)    
  }

  time.taken <- as.numeric(Sys.time() - start.time, units = "secs")
  print (paste0("Time (twi func) = ", time.taken))
  
  ############################### GENERATE GIUH ################################
  # STEP #6: Generate GIUH and write to the geopackage
  # There are many "model" options to specify the velocity.
  # Here we are using a simple approach: constant velocity as a function of upstream drainage area.
  print("STEP: Computing GIUH.................")
  start.time <- Sys.time()
  vel_channel     <- 1.0  # meter/second
  vel_overland    <- 0.1  # Fred: 0.1
  vel_gully       <- 0.2 # meter per second
  gully_threshold <- 30.0 # m (longest , closer to 10-30 m, Refs) 
  
  giuh_compute <- giuh_function(div_infile = outfile, dem_output_dir = dem_output_dir, 
                                vel_channel, vel_overland, vel_gully, gully_threshold)
  
  #giuh_compute[2,] %>% t()
  
  # write GIUH layer to the geopackage
  giuh_dat_values = data.frame(ID = giuh_compute$divide_id, giuh = giuh_compute$fun.giuh_minute)
  names(giuh_dat_values)
  colnames(giuh_dat_values) <- c('divide_id', 'giuh')
  names(giuh_dat_values)

  #giuh_dat_values$giuh[1]
  time.taken <- as.numeric(Sys.time() - start.time, units = "secs")
  print (paste0("Time (giuh ftn) = ", time.taken))
  
  #######################. COMPUTE NASH CASCADE PARAMS ###########################
  # STEP #7: Generate Nash cascade parameters for surface runoff
 
  print("STEP: Computing Nash Cascade parameters .............")
  start.time <- Sys.time()
  nash_params_surface <- get_nash_params(giuh_dat_values, calib_n_k = FALSE)
  
  time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
  print (paste0("Time (nash func) = ", time.taken))
  
  ####################### WRITE MODEL ATTRIBUTE FILE ###########################
  # STEP #8: Append GIUH, TWI, width function, and Nash cascade N and K parameters
  # to model attributes layers

  m_attr$giuh <- giuh_dat_values$giuh             # append GIUH column to the model attributes layer
  m_attr$twi  <- twi_dat_values$twi               # append TWI column to the model attributes layer
  m_attr$width_dist <- twi_dat_values$width_dist  # append width distribution column to the model attributes layer
  m_attr$N_nash_surface <- nash_params_surface$N_nash
  m_attr$K_nash_surface <- nash_params_surface$K_nash

  if (!write_attr_parquet) {
    sf::st_write(m_attr, outfile,layer = "model-attributes", append = FALSE)  
  }
  else {
    #var = strsplit(outfile, "\\.")[[1]][1]
    var = glue("{getwd()}/data")
    attr_par_dir = glue("{var}/model-attributes.parquet")
    arrow::write_parquet(m_attr,attr_par_dir)
  }

}


clean_move_dem_dir <- function(id = id,
                               output_dir = output_dir,
                               dem_output_dir = dem_output_dir) {
  
  if (dir.exists(dem_output_dir) ) {
    if (dir.exists(glue("{dem_output_dir}/{id}"))) {
      unlink(glue("{dem_output_dir}/{id}"), recursive = TRUE)
    }
    dir.create(glue("{dem_output_dir}/{id}"), recursive = TRUE, showWarnings = FALSE)
    file.rename(glue("{output_dir}/{id}/dem"), glue("{dem_output_dir}/{id}"))
  }
  else {
    unlink(glue("{output_dir}/{id}/dem"), recursive = TRUE)
  }  
}



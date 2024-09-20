# @author Ahmad Jan Khattak
# @email ahmad.jan@noaa.gov
# @date  February 05, 2024

# Get the DEM
dem_function <- function(div_infile,
                         dem_input_file = NULL,
                         dem_output_dir) {
  print ("DEM FUNCTION")
  
  tryCatch({
    elev <- rast(dem_input_file)
  }, error = function(e) {
    cat ("Error: dem_input_file does not exist: provided ", dem_input_file, "\n")
  })

  
  # Get the catchment geopackage
  div <- read_sf(div_infile, 'divides')
  
  # Buffer because we want to guarantee we don not have boundary issues when processing the DEM
  div_bf <- st_buffer(div,dist=5000)
  
  dem <- crop(elev, project(vect(div_bf), crs(elev)), snap = "out")
  cm_to_m <- 0.01
  dem <- dem * cm_to_m
  writeRaster(dem, glue("{dem_output_dir}/dem.tif"), overwrite = TRUE)
  
  gdal_utils("warp",
             source = glue("{dem_output_dir}/dem.tif"),
             destination = glue("{dem_output_dir}/dem_proj.tif"),
             options = c("-of", "GTiff", "-t_srs", "EPSG:5070", "-r", "bilinear")
  )
  
  wbt_breach_depressions(dem = glue("{dem_output_dir}/dem_proj.tif"), output = glue("{dem_output_dir}/dem_corr.tif") )
  
}


#the condition [coverage_fraction > .1] excludes/drops all cell X that has fraction less than 10% in the divide Y
fun_crop_lower <- function(values, coverage_fraction) {
  data = (values * coverage_fraction)[coverage_fraction > 0.1]
  percentile_10 <- unname(quantile(data, probs = 0.15, na.rm = TRUE)) # unname function returns the quantile value only, and not the cut points
  data[data <= percentile_10] = percentile_10
}

fun_crop_upper <- function(values, coverage_fraction) {
  data = (values * coverage_fraction)[coverage_fraction > .1]
  percentile_90 <- unname(quantile(data, probs = 0.85, na.rm = TRUE))
  data[data >= percentile_90] = percentile_90
}


# Add model attribtes to the geopackage
add_model_attributes <- function(div_infile, hf_version = 'v2.1.1', write_attr_parquet = FALSE) {
  print ("ADD MODEL ATTRIBUTES FUNCTION")
  
  base = 's3://lynker-spatial/hydrofabric/v2.1.1/nextgen/conus'

  # net has divide_id, id, and vupid that are used for filtering below
  net = as_sqlite(div_infile, "network") 

  # Courtesy of Mike Johnson
  model_attr <- arrow::open_dataset(glue('{base}_model-attributes')) |>
    dplyr::inner_join(dplyr::collect(dplyr::distinct(dplyr::select(net, divide_id, vpuid)))) |> 
    dplyr::collect() 

  flowpath_attr <- arrow::open_dataset(glue('{base}_flowpath-attributes')) |>
    dplyr::inner_join(dplyr::collect(dplyr::distinct(dplyr::select(net, id, vpuid)))) |> 
    dplyr::collect()

  #cat ("m_attr: ", nrow(model_attr))
  stopifnot(nrow(model_attr) > 0)
  stopifnot(nrow(flowpath_attr) > 0)
  
  # Write the attributes to a new table in the hydrofabric subset GPKG
  if (!write_attr_parquet) {
    sf::st_write(model_attr, div_infile, layer = "model-attributes", append = FALSE)
    sf::st_write(flowpath_attr, div_infile, layer = "flowpath-attributes", append = FALSE)    
  }
  else {
    #var = strsplit(div_infile, "\\.")[[1]][1]
    var = glue("{getwd()}/data")
    attr_par_dir = glue("{var}/flowpath-attributes.parquet")
    arrow::write_parquet(flowpath_attr,attr_par_dir)
  }

  
  return(model_attr)
  
  #### Method 2 - could be done this way too
  #net = as_sqlite(outfile, "network") |> 
  #  select('id', 'divide_id', 'vpuid') |> 
  #  collect()
  
  #model_attr <- open_dataset(glue('s3://lynker-spatial/hydrofabric/{hf_version}/nextgen/conus_model-attributes')) |>
  #  filter(vpuid %in% unique(net$vpuid), divide_id %in% unique(net$divide_id)) |> 
  #  collect() 
  
  #flowpath_attr <- open_dataset(glue('s3://lynker-spatial/hydrofabric/{hf_version}/nextgen/conus_flowpath-attributes')) |>
  #  filter(vpuid %in% unique(net$vpuid), divide_id %in% unique(net$id)) |> 
  #  collect()
}

# get parameter function check if a param is provided otherwise a default value
get_param <- function(input, param, default_value) {

  tryCatch({
    value = eval(parse(text = paste("input$", param, sep = "")))
    
    if (is.null(value)) default_value else value
    }, error = function(e) {
      default_value
    })
}

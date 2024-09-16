# The script downloads geopackages from and S3 bucket
library(aws.s3)

bucket_name <- "ngen-bm"
prefix <- "hydrofabric/"

gpkg_files <- get_bucket_df(bucket = bucket_name, prefix = prefix) |> dplyr::filter(grepl(".gpkg$", Key) ) |> 
              dplyr::filter(!grepl("[.]_", Key))
gpkg_files$Key


# local output directory to save the files
out_dir <- "/Users/ahmadjan/Core/SimulationsData/projects/ngen-bm/hydrofabric"
if (!dir.exists(out_dir)) {
  dir.create(out_dir)
}

# Download each .gpkg file
for (g in gpkg_files$Key) {
  # Define local file path
  print (g)
  
  local_path <- file.path(out_dir, basename(g))
  
  # Download the file
  save_object(object = g, bucket = bucket_name, file = local_path)
  
}

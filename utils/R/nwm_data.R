# Courtesy of Mike Johnson

#install.packages("reticulate")

library(reticulate)
#library(ncdf4)
#system('python3 -m venv venv_r')
#use_virtualenv("./venv_r")
use_virtualenv("~/venv_r", required = TRUE)

#py_install("xarray['io']")
#py_install('s3fs')

xr     = import("xarray")
fsspec = import("fsspec")
np     = import("numpy")

reticulate::py_last_error()

nwm_url    <- 's3://noaa-nwm-retrospective-3-0-pds/CONUS/zarr/chrtout.zarr'
start_time <- "2010-10-01 00:00:00"
end_time   <- "2011-10-01 00:00:00"

slice <- import_builtins()$slice

nwm_zarr <- xr$open_zarr(fsspec$get_mapper(nwm_url, anon=TRUE), consolidated=TRUE)

nwm_streamflow_xr <- nwm_zarr['streamflow']

nwm_streamflow_xr <- nwm_streamflow_xr$sel(time=slice(start_time, end_time))

# You can loop ids through starting here, or pass multiple!!!

nldi  <- dataRetrieval::findNLDI(nwis = "01052500")
comid <- np$array(as.integer(nldi$origin$comid))
comid

df <-  data.frame(
  date = seq.POSIXt(as.POSIXct(start_time, tz = "UTC"), 
                    as.POSIXct(end_time,   tz = "UTC"), by = "hour"),
  flow = nwm_streamflow_xr$sel(feature_id = comid)$data)

plot(df$date, df$flow)

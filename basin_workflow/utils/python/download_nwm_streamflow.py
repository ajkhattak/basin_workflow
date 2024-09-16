import xarray as xr
import requests
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates


from dataretrieval import nwis, utils, codes, nldi


def get_comid(fid):
    gdf = nldi.get_features(feature_source="WQP", feature_id=fid)
    comid = int(gdf['comid'][0])

    return comid


def get_stream_discharge(gage_id, start_time, end_time):

    #gage_id = "USGS-01052500"
    if not 'USGS' in gage_id:
        gage_id = 'USGS-'+gage_id

    comid = get_comid(gage_id)
    
    #awspath2 ='https://noaa-nwm-retrospective-2-1-zarr-pds.s3.amazonaws.com/ldasout.zarr'
    
    awspath3  = 'https://noaa-nwm-retrospective-3-0-pds.s3.amazonaws.com/CONUS/zarr/chrtout.zarr'
    #nwm_url  = 's3://noaa-nwm-retrospective-3-0-pds/CONUS/zarr/chrtout.zarr' # this also works
    
    ds = xr.open_zarr(awspath3,consolidated=True)

    nwm_streamflow = ds['streamflow']
    
    #nwm_streamflow has dimensions ('time', 'feature_id')
    # slice the time dimension by range of start and end times
    nwm_streamflow = nwm_streamflow.sel(time=slice(start_time, end_time))
    
    # slice feature_id dimension by comid
    flow_data = nwm_streamflow.sel(feature_id=comid)
    
    df = pd.DataFrame({
        'time': flow_data.time,
        'flow': flow_data.data
    })

    # time units [hour]
    # flow units [m3 s-1]
    return df

if __name__ == "__main__":


     try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-gid", dest="gage_id",    type=str, required=True,  help="USGS gage ID")
        parser.add_argument("-s",   dest="start_rime", type=str, required=True,  help="start time")
        parser.add_argument("-e",   dest="end_time",   type=str, required=True,  help="end time")
    except:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    get_stream_discharge(args.gage_id, args.start_time, args.end_time)
    

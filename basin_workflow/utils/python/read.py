from glob import glob
import os
import geopandas as gpd
import netCDF4
import pandas as pd

gpkg_file = 'Gage_*.gpkg'
troute_ncfile="troute_output_*.nc"

# identify outlet nexus draining to stream gage
gage = os.path.basename(gpkg_file).split('.')[0].split('_')[1]
nexdf = gpd.read_file(gpkg_file, layer="nexus").dropna()
if nexdf['hl_uri'].values[0].split('-')[1] == gage:
    nexs = nexdf['id'].tolist()

# identify catchments draining to outlet nexus
div = gpd.read_file(gpkg_file, layer="divides")
wbs = div[div['toid'].isin(nexs)]['divide_id'].tolist()
wblst = [int(wb.split('-')[1]) for wb in wbs]

# get streamflow corresponding to the selected catchments
ncvar = netCDF4.Dataset(troute_ncfile, "r")
fid_index = [list(ncvar['feature_id'][0:]).index(fid) for fid in wblst]
output = pd.DataFrame(data={'sim_flow': pd.DataFrame(ncvar['flow'][fid_index], index=fid_index).T.sum(axis=1)})

# add time range
nexfile = list(glob("nex*.csv"))[0]
nexdf = pd.read_csv(nexfile, index_col=0, parse_dates=[1], names=['ts', 'time', 'Q']).set_index('time')
dt_range = pd.date_range(nexdf.index[1], nexdf.index[-1], len(output.index)).round('min')
output.index = dt_range
output = output.resample('1H').first()
output.index.name='Time'
output.reset_index(inplace=True)

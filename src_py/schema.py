import pandas as pd
import geopandas as gpd
import numpy as np

"""
# the primary gw outlet coefficient (baseflow)

From Nels
# cgw from WRF-Hydro NWM is in "m^3/s" which is interestingly
# 0.005 everywhere
# We need to rescale this to m/hr
# Hydrofabic v2.1.1 conus areasqkm distribution is

   mean         14.129473
   std         166.396737
   min           0.000235
   25%           4.565701
   50%           7.337700
   75%          11.065949
   max       65014.294940

# Since the min and max here are well outside the idealized size (3-10 sqkm), we will use
# the inter qualitle values for calibration range, and the median for default here
cgs = self.data['cgw'].value
cgs = cgs/(7.337700*1000*1000) # now we have m/s, I think, converting sq things to flat is hard
cgs = cgs*3600 # m/hr
self.data['cgw'].value = cgs
"""

def get_schema_model_attributes(gdf_model):
    schema = gdf_model.dtypes
    
    df = {}
    for d in schema.index:
        if 'bexp_soil_layers_stag=1' in d:
            df['soil_b'] = d
        if 'dksat_soil_layers_stag=1' in d:
            df['soil_dksat'] = d
        if 'psisat_soil_layers_stag=1' in d:
            df['soil_psisat'] = d
        if 'smcmax_soil_layers_stag=1' in d:
            df['soil_smcmax'] = d
        if 'smcwlt_soil_layers_stag=1' in d:
            df['soil_smcwlt'] = d
    
        if 'ISLTYP' in d:
            df['ISLTYP'] = d
        if 'IVGTYP' in d:
            df['IVGTYP'] = d

        if 'refkdt' in d:
            df['soil_refkdt'] = d
        
        if 'Coeff' in d:
            df['gw_Coeff'] = d
        if 'Zmax' in d:
            df['gw_Zmax'] = d
        if 'Expon' in d:
            df['gw_Expon'] = d
        if 'slope' in d:
            if 'slope_mean' in d:
                df['slope_mean'] = d
            else:
                df['soil_slope'] = d
        if 'elevation' in d:
            df['elevation_mean'] = d

        if 'twi'in d:
            if 'twi_dist' in d:
                df['twi_dist'] = d
            else:
                df['twi'] = d
        if 'width_dist' in d:
            df['width_dist'] = d
        if 'giuh' in d:
            df['giuh'] = d
        if 'N_nash' in d:
            df['N_nash_surface'] = d
        if 'K_nash' in d:
            df['K_nash_surface'] = d

    return df



def get_schema_flowpath_attributes(gdf_flowpath, for_gage_id = False):
    schema = gdf_flowpath.dtypes

    df = {}

    # key, downstream, and mainstem should come from flowlines column names, and not from flowpaths-attributes
    df['mainstem'] = 'mainstem'
    df['key'] = "id"
    df['downstream'] = "toid"
    df['alt'] = "alt"    # should come from flowpaths-attributes

    for d in schema.index:

        if (for_gage_id):
            if 'id' == d or 'link' == d:
                df['key'] = d

        #if 'id' == d or 'link' == d:
        #    df['key'] = d

        #if 'to' == d:
        #    df['downstream'] = d

        if 'length_m' == d or 'Length_m' == d:
            df['dx'] = d

        if 'n' == d :
            df['n'] = d

        if 'nCC' == d:
            df['ncc'] = d

        if 'So' == d:
            df['s0'] = d

        if 'BtmWdth' == d:
            df['bw'] = d

        if 'rl_NHDWaterbodyComID' == d or 'WaterbodyID' == d:
            df['waterbody'] = d 

        if 'rl_gages' == d or 'gage' == d:
            df['gages'] = d

        if 'TopWdth' == d:
            df['tw'] = d

        if 'TopWdthCC' == d:
            df['twcc'] = d

        if 'alt' == d:
            df['alt'] = d

        if 'MusK' == d:
            df['musk'] = d

        if 'MusX' == d:
            df['musx'] = d

        if 'ChSlp' == d:
            df['cs'] = d

    return df

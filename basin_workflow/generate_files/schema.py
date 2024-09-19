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

def get_schema(gdf_soil):
    schema = gdf_soil.dtypes
    
    dict = {}
    for d in schema.index:
        if 'bexp_soil_layers_stag=1' in d:
            dict['soil_b'] = d
        if 'dksat_soil_layers_stag=1' in d:
            dict['soil_dksat'] = d
        if 'psisat_soil_layers_stag=1' in d:
            dict['soil_psisat'] = d
        if 'smcmax_soil_layers_stag=1' in d:
            dict['soil_smcmax'] = d
        if 'smcwlt_soil_layers_stag=1' in d:
            dict['soil_smcwlt'] = d
    
        if 'ISLTYP' in d:
            dict['ISLTYP'] = d
        if 'IVGTYP' in d:
            dict['IVGTYP'] = d

        if 'refkdt' in d:
            dict['soil_refkdt'] = d
        
        if 'Coeff' in d:
            dict['gw_Coeff'] = d
        if 'Zmax' in d:
            dict['gw_Zmax'] = d
        if 'Expon' in d:
            dict['gw_Expon'] = d
        if 'slope' in d:
            if 'slope_mean' in d:
                dict['slope_mean'] = d
            else:
                dict['soil_slope'] = d
        if 'elevation' in d:
            dict['elevation_mean'] = d

        if 'twi'in d:
            if 'twi_dist' in d:
                dict['twi_dist'] = d
            else:
                dict['twi'] = d
        if 'width_dist' in d:
            dict['width_dist'] = d
        if 'giuh' in d:
            dict['giuh'] = d
        if 'N_nash' in d:
            dict['N_nash_surface'] = d
        if 'K_nash' in d:
            dict['K_nash_surface'] = d

    return dict

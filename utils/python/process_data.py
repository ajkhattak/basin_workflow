import pandas as pd
import numpy as np
from pathlib import Path
import glob
import math
import sys
import time
import hydrotools
from hydrotools.metrics.metrics import *

sys.path.append('/home/ec2-user/codes/workflows/basin_workflow/utils/python/')
import download_nwm_streamflow as nwmQ

#model = 'cfe_bfi_nnse'
model = 'cfe_bfi_kge' #'lgar_bfi_nnse'

root_dir = Path(f'/home/ec2-user/core/agu_2024/simulations/{model}/')

infiles_calib = glob.glob(str(root_dir / "*" / "2024*" / "best*"))
infiles_calib = [Path(f)  for f in infiles_calib]

infiles_valid = glob.glob(str(root_dir / "*" / "2024*" / "output_sim_obs/sim_obs_validation.csv"))
infiles_valid = [Path(f)  for f in infiles_valid]


outfile = f'/home/ec2-user/core/agu_2024/evaluation/summary/{model}.csv'
outfile_nwm = f'/home/ec2-user/core/agu_2024/evaluation/summary/nwm_bfi_kge.csv'

#basins_infile = '/home/ec2-user/core/agu_2024/evaluation/data/gagesII_LRR.csv'
basins_infile = '/home/ec2-user/core/agu_2024/evaluation/data/gagesII_lowBFI.csv'

df_basins = pd.read_csv(basins_infile, dtype= {'STAID': str})
df_basins.set_index('STAID', inplace=True)




def get_best_kge():
    sim_kge = []
    basin_id = []
    lat = []
    lng = []

    for file in infiles_calib:

        df_params = pd.read_csv(file, header = None)
        df_params.columns = ['value']

        best_itr  = str(int(df_params['value'][1]))

        if (not pd.isna(df_params['value'][2]) and not math.isinf(df_params['value'][2])):
            best_kge  = 1 - df_params['value'][2]
        else:
            best_kge = -100
    
        sim_kge.append(best_kge)
    
        id = str(file.parent.parent.stem)
        basin_id.append(id)
        
        lat.append(df_basins.loc[id]['LAT_GAGE'])
        lng.append(df_basins.loc[id]['LNG_GAGE'])
    
    df_calib = {
        'STAID' : basin_id,
        'LAT_GAGE' : lat,
        'LNG_GAGE' : lng,
        'kge_calib' : sim_kge
    }

    df_calib = pd.DataFrame(data = df_calib)

    # Validation KGE
    sim_kge = []
    basin_id = []

    for file in infiles_valid:

        id = str(file.parent.parent.parent.stem)
        #print (id)

        df = pd.read_csv(file, usecols=['time', 'sim_flow', 'obs_flow'])
        df.set_index('time', inplace=True)
        if (df.empty):
            continue
        #print (df)
        #print (df["sim_flow"])
        basin_id.append(id)
        sim_kge.append(kling_gupta_efficiency(df["obs_flow"], df["sim_flow"]))
        #sim_kge.append(nash_sutcliffe_efficiency(df["obs_flow"], df["sim_flow"]))
        #print (sim_kge)
        #quit()
    df_valid = {
        'STAID' : basin_id,
        'kge_valid' : sim_kge
    }

    df_valid = pd.DataFrame(data = df_valid)

    df_sim = pd.merge(df_calib, df_valid, on='STAID', how='left')
    #df_sim = df_sim.dropna()
    #df_sim = pd.merge(df_calib, df_valid, left_index=True, right_index=True)
    """
    df_sim = {
        'STAID':basin_id,
        'kge' : sim_kge }
    """
    #print (df_sim)

    return df_sim

df_sim = get_best_kge()
df_sim.to_csv(outfile, index=True)


def get_kge_nwm():

    lat = []
    lng = []
    nwm_kge = []
    basin_id = []
    for file in infiles_calib:

        simfile = glob.glob(str(file.parent / 'output_sim_obs/sim_obs_0.csv' ))[0]

        id = str(file.parent.parent.stem)
        basin_id.append(id)
        print (id)

        try:
            observed_data = pd.read_csv(simfile, usecols=['time', 'sim_flow', 'obs_flow'])
            observed_data.set_index('time', inplace=True)
            start_time = observed_data.index[0]
            end_time = observed_data.index[-1]

            observed_data = observed_data.loc[start_time:end_time]
            observed_data.index = pd.to_datetime(observed_data.index)

            df_nwm = nwmQ.get_streamflow(gage_id=id, start_time=start_time, end_time=end_time)
        
            df_nwm.set_index('time', inplace=True)
            df_nwm.index = pd.to_datetime(df_nwm.index)
            
            df = pd.merge(df_nwm['flow'], observed_data['obs_flow'], left_index=True, right_index=True)
            
            nwm_kge.append(kling_gupta_efficiency(df["obs_flow"], df["flow"]))
            #nwm_kge.append(nash_sutcliffe_efficiency(df["obs_flow"], df["flow"]))
        except:
            nwm_kge.append(-100)

        lat.append(df_basins.loc[id]['LAT_GAGE'])
        lng.append(df_basins.loc[id]['LNG_GAGE'])
        time.sleep(10)

    print ("A: ", len(basin_id), len(lat), len(lng), len(nwm_kge))    
    df_nwm = {
        'STAID' : basin_id,
        'LAT_GAGE' : lat,
        'LNG_GAGE' : lng,
        'kge' : nwm_kge
    }

    df_nwm = pd.DataFrame(data = df_nwm)
    df_nwm.to_csv(outfile_nwm, index=True)
    
#get_kge_nwm()

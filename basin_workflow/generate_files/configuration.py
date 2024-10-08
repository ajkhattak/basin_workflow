############################################################################################
# Author  : Ahmad Jan
# Contact : ahmad.jan@noaa.gov
# Date    : September 28, 2023
############################################################################################

"""
The script generates config files for all nextgen models using a hydrofabric subset geopackage
 - inputs:  see main function for inputs (taken as arguments)
 - outputs: writes configuration files for all catchments within the basin
"""

import os, sys
import argparse
import re
import copy
import glob
import json
import subprocess
import pandas as pd
import geopandas as gpd
import numpy as np
import fiona
import yaml
import platform

try:
    from generate_files import schema
except:
    import schema
os_name = platform.system()


#############################################################################
# module reads NWM soil type file and returns a table
# this is used for two purposes: 1) Xinanjiang parameters, 2) soil quartz content used in soil freeze thaw model
# @param infile : input file contain NWM 3.0 soil data/properties
# - returns     : dataframe
#############################################################################
def get_soil_class_NWM(infile):
    header = ['index','BB','DRYSMC','F11','MAXSMC','REFSMC','SATPSI','SATDK','SATDW','WLTSMC', \
              'QTZ', 'BVIC', 'AXAJ', 'BXAJ', 'XXAJ', 'BDVIC', 'BBVIC', 'GDVIC','ISLTYP']
    
    df = pd.read_table(infile, delimiter=',', index_col=0, skiprows=3, nrows=19, names=header)

    return df



#############################################################################
# module reads hydrofabric geopackage file and retuns a dict containing parameters needed for our models
# this is intended to be modified if more models are added or more soil parameters need to be extracted
# @param infile : input file pointing to hydrofabric basin geopkacge
# - returns     : geodataframe 
#############################################################################
def read_gpkg_file(infile, coupled_models, surface_runoff_scheme, verbosity, schema_type='noaa-owp'):
    
    try:
        gdf_soil = gpd.read_file(infile, layer='model-attributes')
    except:
        try:
            gdf_soil = gpd.read_file(infile, layer='model_attributes')
        except:
            print("layer 'model-attributes or model_attributes does not exist!'")
            sys.exit(1)
    
    gdf_soil.set_index("divide_id", inplace=True)
    gdf_div = gpd.read_file(infile, layer='divides')
    gdf_div = gdf_div.to_crs("EPSG:4326") # change CRS to 4326

    #global layers, flowpath_layer   # global layers
    layers = fiona.listlayers(infile)

    flowpath_layer = [layer for layer in layers if 'flowpath' in layer][0]
    
    if (verbosity >=3):
        print ("Geopackage layers: ", layers)
        print ("\n")

    params = schema.get_schema_model_attributes(gdf_soil)

    #read_gpkg_schema()
    gdf_soil['soil_b']      = gdf_soil[params['soil_b']].fillna(16)
    gdf_soil['soil_dksat']  = gdf_soil[params['soil_dksat']].fillna(0.00000338)
    gdf_soil['soil_psisat'] = gdf_soil[params['soil_psisat']].fillna(0.355)
    gdf_soil['soil_smcmax'] = gdf_soil[params['soil_smcmax']].fillna(0.439)
    gdf_soil['soil_smcwlt'] = gdf_soil[params['soil_smcwlt']].fillna(0.066)
    gdf_soil['gw_Zmax']     = gdf_soil[params['gw_Zmax']].fillna(0.01)
    gdf_soil['gw_Coeff']    = gdf_soil[params['gw_Coeff']].fillna(1.8e-05)
    gdf_soil['gw_Expon']    = gdf_soil[params['gw_Expon']].fillna(6.0)
    gdf_soil['soil_slope']  = gdf_soil[params['soil_slope']].fillna(1.0)
    gdf_soil['ISLTYP']      = gdf_soil[params['ISLTYP']].fillna(1).astype(int)
    gdf_soil['IVGTYP']      = gdf_soil[params['IVGTYP']].fillna(1).astype(int)
    gdf_soil['gw_Zmax']     = gdf_soil['gw_Zmax']/1000. # convert mm to m
    gdf_soil['gw_Coeff']    = gdf_soil['gw_Coeff']*3600/(7.337700*1000*1000) # schema.py for more details
    gdf_soil['elevation_mean'] = gdf_soil[params['elevation_mean']].fillna(4) # if nan, put 4 MASL
    

    if (schema_type == 'dangermond'):
        gdf_soil['elevation_mean'] = gdf_soil['elevation_mean']/100.0  # cm to m conversion
        
    if('refkdt' in gdf_soil):
        gdf_soil['soil_refkdt'] = gdf_soil[params['soil_refkdt']].fillna(3.0)
    else:
        gdf_soil['soil_refkdt'] = 3.0

    # copy parameters needed
    #gdf = gpd.GeoDataFrame(pd.DataFrame(), geometry= gdf_div['geometry'], index=gdf_soil.index)
    
    gdf = gpd.GeoDataFrame(data={'geometry': gdf_div['geometry'].values},
                           index=gdf_soil.index
                           )
    
    gdf['soil_b']       = gdf_soil['soil_b'].copy()
    gdf['soil_satdk']   = gdf_soil['soil_dksat'].copy()
    gdf['soil_satpsi']  = gdf_soil['soil_psisat'].copy()
    gdf['soil_slop']    = gdf_soil['soil_slope'].copy()
    gdf['soil_smcmax']  = gdf_soil['soil_smcmax'].copy()
    gdf['soil_wltsmc']  = gdf_soil['soil_smcwlt'].copy()
    gdf['soil_refkdt']     = gdf_soil['soil_refkdt'].copy()
    gdf['max_gw_storage']  = gdf_soil['gw_Zmax'].copy()
    gdf['Cgw']             = gdf_soil['gw_Coeff'].copy()
    gdf['gw_expon']        = gdf_soil['gw_Expon'].copy()
    gdf['ISLTYP']          = gdf_soil['ISLTYP'].copy()
    gdf['IVGTYP']          = gdf_soil['IVGTYP'].copy()
    gdf['elevation_mean']  = gdf_soil['elevation_mean'].copy()

    # ensure parameter `b` is non-zero
    mask = gdf['soil_b'].gt(0.0) # greater than or equal to
    min_value = gdf['soil_b'][mask].min() # get the min value > 0.0

    mask = gdf['soil_b'].le(0.0) # find all values <= 0.0
    
    #df['soil_params.b'][mask] = min_value
    gdf.loc[mask, 'soil_b'] = min_value


    # check if elevation is negative, specially near coastal areas
    mask = gdf['elevation_mean'].le(0.0) # find all values <= 0.0
    gdf.loc[mask, 'elevation_mean'] = 1.0
    
    # TWI for topmodel
    if ("nom_topmodel" in coupled_models):
        gdf['twi'] = gdf_soil[params['twi']]
        gdf['width_dist'] = gdf_soil[params['width_dist']]

    if ("cfe" in coupled_models or "lasam" in coupled_models):
        if (surface_runoff_scheme == "GIUH" or surface_runoff_scheme == 1):
            gdf['giuh'] = gdf_soil[params['giuh']]
        elif (surface_runoff_scheme == "NASH_CASCADE" or surface_runoff_scheme == 2):
            gdf['N_nash_surface'] = gdf_soil[params['N_nash_surface']]
            gdf['K_nash_surface'] = gdf_soil[params['K_nash_surface']]

    # get catchment ids -- for Shengting
    df_cats = gpd.read_file(infile, layer='divides')
    catids = [int(re.findall('[0-9]+',s)[0]) for s in df_cats['divide_id']]
    
    return gdf, catids

#############################################################################
# write uniform forcing data files, takes a base file and replicate it over all catchments (will be removed later)
# this is only for testing purposes
# @param catids : array/list of integers contain catchment ids
# @param infile : input file of the  base forcing data     
#############################################################################
def write_forcing_files(catids, infile):
    
    inpath= os.path.dirname(infile)
    
    for catID in catids:
        cat_name = 'cat-'+str(catID)
        fname = cat_name+'.csv'
        str_sub="cp " + infile + " "+os.path.join(inpath,fname)
        out=subprocess.call(str_sub,shell=True)

#############################################################################
# The function generates configuration files for NOAH-OWP-Modular

# @param catids      : array/list of integers contain catchment ids
# @param nom_dir     : output directory (config files are written to this directory)
# @param forcing_dir : forcing data directory containing data for each catchment
# @param gpkg_file   : basin geopackage file
# @param simulation_time : dictionary contain start/end time of the simulation

#############################################################################
def write_nom_input_files(catids, nom_dir, forcing_dir, gdf_soil, simulation_time, verbosity):

    if (verbosity >=3):
        print ("NOM simulation time: ", simulation_time)
    
    start_time = pd.Timestamp(simulation_time['start_time']).strftime("%Y%m%d%H%M")
    end_time   = pd.Timestamp(simulation_time['end_time']).strftime("%Y%m%d%H%M")
    
    for catID in catids:
        cat_name = 'cat-'+str(catID)
        
        centroid_x = str(gdf_soil['geometry'][cat_name].centroid.x)
        centroid_y = str(gdf_soil['geometry'][cat_name].centroid.y)
        
        soil_type = str(gdf_soil.loc[cat_name]['ISLTYP'])
        veg_type  = str(gdf_soil.loc[cat_name]['IVGTYP'])

        timing = ["&timing                                   ! and input/output paths",
                  "  dt                 = 3600.0             ! timestep [seconds]",
                  "  startdate          = \"%s\"             ! UTC time start of simulation (YYYYMMDDhhmm)"%start_time,
                  "  enddate            = \"%s\"             ! UTC time end of simulation (YYYYMMDDhhmm)"%end_time,
                  "  forcing_filename   = \"%s.csv\"         ! file containing forcing data"%(os.path.join(forcing_dir,cat_name)),
                  "  output_filename    = \"output-%s.csv\""%cat_name,
                  "/\n"
                  ]
        
        params = ["&parameters",
                  "  parameter_dir      = \"%s\"  ! location of input parameter files"%(os.path.join(nom_dir,"parameters")),
                  "  general_table      = \"GENPARM.TBL\"                ! general param tables and misc params",
                  "  soil_table         = \"SOILPARM.TBL\"               ! soil param table",
                  "  noahowp_table      = \"MPTABLE.TBL\"                ! model param tables (includes veg)",
                  "  soil_class_name    = \"STAS\"                       ! soil class data source - STAS or STAS-RUC",
                  "  veg_class_name     = \"MODIFIED_IGBP_MODIS_NOAH\"   ! vegetation class data source - MODIFIED_IGBP_MODIS_NOAH or USGS",
                  "/\n"
                  ]
        
        location = ["&location                                         ! for point runs",
                    "  lat              = %s                           ! latitude [degrees]  (-90 to 90)"%centroid_y,
                    "  lon              = %s                           ! longitude [degrees] (-180 to 180)"%centroid_x,
                    "  terrain_slope    = 0.0                          ! terrain slope [degrees]",
                    "  azimuth          = 0.0                          ! terrain azimuth or aspect [degrees clockwise from north]",
                    "/ \n"
                    ]
        
        forcing = ["&forcing",
                   "  ZREF               = 10.0                        ! measurement height for wind speed (m)",
                   "  rain_snow_thresh   = 1.0                         ! rain-snow temperature threshold (degrees Celcius)",
                   "/ \n"
                   ]

        model_opt = ["&model_options                                   ! see OptionsType.f90 for details",
                     "  precip_phase_option               = 1",
                     "  snow_albedo_option                = 1",
                     "  dynamic_veg_option                = 4",
                     "  runoff_option                     = 3",
                     "  drainage_option                   = 8",
                     "  frozen_soil_option                = 1",
                     "  dynamic_vic_option                = 1",
                     "  radiative_transfer_option         = 3",
                     "  sfc_drag_coeff_option             = 1",
                     "  canopy_stom_resist_option         = 1",
                     "  crop_model_option                 = 0",
                     "  snowsoil_temp_time_option         = 3",
                     "  soil_temp_boundary_option         = 2",
                     "  supercooled_water_option          = 1",
                     "  stomatal_resistance_option        = 1",
                     "  evap_srfc_resistance_option       = 4",
                     "  subsurface_option                 = 2",
                     "/\n",
                     ]

        struct = ["&structure",
                  "  isltyp           = %s               ! soil texture class"%soil_type,
                  "  nsoil            = 4               ! number of soil levels",
                  "  nsnow            = 3               ! number of snow levels",
                  "  nveg             = 27              ! number of vegetation types",
                  "  vegtyp           = %s               ! vegetation type"%veg_type,
                  "  croptype         = 0               ! crop type (0 = no crops; this option is currently inactive)",
                  "  sfctyp           = 1               ! land surface type, 1:soil, 2:lake",
                  "  soilcolor       = 4               ! soil color code",
                  "/\n"
                  ]
        
        init_val = ["&initial_values",
                    "  dzsnso    =  0.0,  0.0,  0.0,  0.1,  0.3,  0.6,  1.0     ! level thickness [m]",
                    "  sice      =  0.0,  0.0,  0.0,  0.0                       ! initial soil ice profile [m3/m3]",
                    "  sh2o      =  0.3,  0.3,  0.3,  0.3                       ! initial soil liquid profile [m3/m3]",
                    "  zwt       =  -2.0                                        ! initial water table depth below surface [m]",
                    "/\n",
                    ]

        # combine all sub-blocks
        nom_params = timing + params + location + forcing + model_opt + struct + init_val

        fname_nom = 'nom_config_'+cat_name+'.input'
        nom_file = os.path.join(nom_dir, fname_nom)
        with open(nom_file, "w") as f:
            f.writelines('\n'.join(nom_params))

#############################################################################
# The function generates configuration file for CFE
# @param catids         : array/list of integers contain catchment ids
# @param runoff_schame  : surface runoff schemes - Options = Schaake or Xinanjiang
# @soil_class_NWM       : a dict containing NWM soil characteristics, used here for extracting
#                         Xinanjiang properties for a given soil type
# @gdf_soil             : geodataframe contains soil properties extracted from the hydrofabric
# @param cfe_dir        : output directory (config files are written to this directory)
# @param gpkg_file      : basin geopackage file
# @param coupled_models : option needed to modify CFE config files based on the coupling type
#############################################################################
def write_cfe_input_files(catids, precip_partitioning_scheme, surface_runoff_scheme, soil_class_NWM, gdf_soil,
                          cfe_dir, coupled_models):

    if (not precip_partitioning_scheme in ["Schaake", "Xinanjiang"]):
        sys.exit("Runoff scheme should be: Schaake or Xinanjiang")
    
    ice_content_threshold  = 0.3 # used when coupled with Soil freeze thaw model

    urban_decimal_fraction = 0.0 # used when runoff scheme is Xinanjiang

    delimiter = ","
    
    # loop over all catchments and write config files
    for catID in catids:
        cat_name = 'cat-'+str(catID) 
        fname = cat_name+'*.txt'
        
        # cfe params set
        cfe_params = ['forcing_file=BMI',
                      'surface_water_partitioning_scheme=Schaake',
                      'surface_runoff_scheme=GIUH',
                      'soil_params.depth=2.0[m]',
                      'soil_params.b='      + str(gdf_soil['soil_b'][cat_name])+'[]',
                      'soil_params.satdk='  + str(gdf_soil['soil_satdk'][cat_name])+'[m s-1]', 
                      'soil_params.satpsi=' + str(gdf_soil['soil_satpsi'][cat_name])+'[m]',
                      'soil_params.slop='   + str(gdf_soil['soil_slop'][cat_name])+"[m/m]",
                      'soil_params.smcmax=' + str(gdf_soil['soil_smcmax'][cat_name])+"[m/m]",
                      'soil_params.wltsmc=' + str(gdf_soil['soil_wltsmc'][cat_name])+"[m/m]",
                      'soil_params.expon=1.0[]',
                      'soil_params.expon_secondary=1.0[]',
                      'refkdt='         + str(gdf_soil['soil_refkdt'][cat_name]),
                      'max_gw_storage=' + str(gdf_soil['max_gw_storage'][cat_name])+'[m]',
                      'Cgw=' + str(gdf_soil['Cgw'][cat_name])+'[m h-1]',
                      'expon=' + str(gdf_soil['gw_expon'][cat_name])+'[]',
                      'gw_storage=0.05[m/m]',
                      'alpha_fc=0.33',
                      'soil_storage=' + str(gdf_soil['soil_smcmax'][cat_name])+'[m/m]', # 50% reservoir filled
                      'K_nash_subsurface=0.03[]',
                      'N_nash_subsurface=2',
                      'K_lf=0.01[]',
                      'nash_storage_subsurface=0.0,0.0',
                      'num_timesteps=1',
                      'verbosity=0'
                   ]

        
        if (gdf_soil['soil_b'][cat_name] == 1.0):
            cfe_params[4] = 1.1

        # add giuh ordinates
        if (surface_runoff_scheme == "GIUH" or surface_runoff_scheme == 1):
            giuh_cat = json.loads(gdf_soil['giuh'][cat_name])
            giuh_cat = pd.DataFrame(giuh_cat, columns=['v', 'frequency'])

            giuh_ordinates = ",".join(str(x) for x in np.array(giuh_cat["frequency"]))
            cfe_params.append(f'giuh_ordinates={giuh_ordinates}')
            
        elif (surface_runoff_scheme == "NASH_CASCADE" or surface_runoff_scheme == 2):
            cfe_params[2]='surface_runoff_scheme=NASH_CASCADE'
            cfe_params.append("N_nash_surface=" + str(int(gdf_soil['N_nash_surface'][cat_name]))+'[]')
            cfe_params.append("K_nash_surface=" + str(gdf_soil['K_nash_surface'][cat_name])+'[h-1]')
            s = [str(0.0),]*int(gdf_soil['N_nash_surface'][cat_name])
            s = delimiter.join(s)
            cfe_params.append("nash_storage_surface=" + str(s)+'[]')
        
        if(precip_partitioning_scheme == 'Xinanjiang'):
            cfe_params[1]='surface_water_partitioning_scheme=Xinanjiang'
            cfe_params.append('a_Xinanjiang_inflection_point_parameter='+str(soil_class_NWM['AXAJ'][soil_id]))
            cfe_params.append('b_Xinanjiang_shape_parameter='+str(soil_class_NWM['BXAJ'][soil_id]))
            cfe_params.append('x_Xinanjiang_shape_parameter='+str(soil_class_NWM['XXAJ'][soil_id]))
            cfe_params.append('urban_decimal_fraction='+str(urban_decimal_fraction))

        # coupled with Soil freeze thaw model
        if(coupled_models == "nom_cfe_smp_sft"):
            cfe_params.append("sft_coupled=true")
            cfe_params.append("ice_content_threshold="+str(ice_content_threshold))

        fname_cfe = 'cfe_config_' + cat_name + '.txt'
        cfe_file = os.path.join(cfe_dir, fname_cfe)
        with open(cfe_file, "w") as f:
            f.writelines('\n'.join(cfe_params))

#############################################################################
# The function generates configuration file for TopModel
# @param catids         : array/list of integers contain catchment ids
# @param runoff_schame  : surface runoff schemes - Options = Schaake or Xinanjiang
# @soil_class_NWM       : a dict containing NWM soil characteristics, used here for extracting
#                         Xinanjiang properties for a given soil type
# @gdf_soil             : geodataframe contains soil properties extracted from the hydrofabric
# @param cfe_dir        : output directory (config files are written to this directory)
# @param gpkg_file      : basin geopackage file
# @param coupled_models : option needed to modify CFE config files based on the coupling type
#############################################################################
def write_topmodel_input_files(catids, gdf_soil, topmodel_dir, coupled_models):
    
    # loop over all catchments and write config files
    for catID in catids:
        cat_name = 'cat-'+str(catID) 
        fname = cat_name+'*.txt'
        
        ##################
        topmod = ["0",
                  f'{cat_name}',
                  "./forcing/%s.csv"%cat_name,
                  f'./{topmodel_dir}/subcat_{cat_name}.dat',
                  f'./{topmodel_dir}/params_{cat_name}.dat',
                  f'./{topmodel_dir}/topmod_{cat_name}.out',
                  f'./{topmodel_dir}/hyd_{cat_name}.out'
                  ]

        fname_tm = f'topmod_{cat_name}.run' # + '_config_.run'
        tm_file = os.path.join(topmodel_dir, fname_tm)
        with open(tm_file, "w") as f:
            f.writelines('\n'.join(topmod))

        f.close()
        
        #################
        params = [f'Extracted study basin: {cat_name}',
                  "0.032  5.0  50.  3600.0  3600.0  0.05  0.0000328  0.002  0  1.0  0.02  0.1"
                  ]

        fname_tm = f'params_{cat_name}.dat'
        tm_file = os.path.join(topmodel_dir, fname_tm)
        with open(tm_file, "w") as f:
            f.writelines('\n'.join(params))

        f.close()

        ################
        twi_cat = json.loads(gdf_soil['twi'][cat_name])

        twi_cat = pd.DataFrame(twi_cat, columns=['v', 'frequency'])
        # frequency: distributed area by percentile, v: twi value
               
        twi_cat = twi_cat.sort_values(by=['v'],ascending=False)
        
        # add width function commulative distribution
        width_f = json.loads(gdf_soil['width_dist'][cat_name])
        df_width_f = pd.DataFrame(width_f, columns=['v', 'frequency'])
        v_cumm = np.cumsum(df_width_f['frequency'])
        
        nclasses_twi = len(twi_cat['frequency'].values)
        
        nclasses_width_function = len(df_width_f['frequency'].values) # width functions (distance to the outlet)
        subcat = ["1 1 1",
                  f'Extracted study basin: {cat_name}',
                  f'{nclasses_twi} 1',
                  'replace_with_twi',
                  f'{nclasses_width_function}',
                  'add_width_function',
                  '$mapfile.dat'
                  ]

        twi_str = ''
        for freq, value in zip(twi_cat['frequency'].values, twi_cat['v'].values):
            twi_str+="{0:.6f}".format(freq) + " " + "{0:.6f}".format(value)+ "\n"
        
        subcat[3] = twi_str.strip()

        # update list/location for the width function
        widthf_str = ''
        for freq, value in zip(v_cumm.values, df_width_f['v'].values):
            widthf_str+="{0:.6f}".format(freq) + " " + "{0:.6f}".format(value)+ " "

        subcat[5] = widthf_str.strip()
        
        fname_tm = f'subcat_{cat_name}.dat'
        tm_file = os.path.join(topmodel_dir, fname_tm)
        with open(tm_file, "w") as f:
            f.writelines('\n'.join(subcat))

        f.close()
        
                       
#############################################################################
# The function generates configuration file for soil freeze thaw (SFT) model
# @param catids         : array/list of integers contain catchment ids
# @param runoff_schame  : surface runoff schemes - Options = Schaake or Xinanjiang
# @param forcing_dir    : forcing data directory containing data for each catchment
#                         used here for model initialization (based on mean annual air temperature)                
# @param soil_class_NWM : a dict containing NWM soil characteristics, used here for extracting
# @param gdf_soil       : geodataframe contains soil properties extracted from the hydrofabric
#                         Quartz properties for a given soil type
# @param sft_dir        : output directory (config files are written to this directory)
#############################################################################
def write_sft_input_files(catids, precip_partitioning_scheme, surface_runoff_scheme, forcing_dir,
                          gdf_soil, soil_class_NWM, sft_dir):

    # runoff scheme
    if (not precip_partitioning_scheme in ["Schaake", "Xinanjiang"]):
        sys.exit("Runoff scheme should be: Schaake or Xinanjiang")

    # num cells -- number of cells used for soil column discretization
    #ncells = 4
    #soil_z = "0.1,0.3,1.0,2.0"

    ncells = 19
    soil_z = "0.1,0.15,0.18,0.23,0.29,0.36,0.44,0.55,0.69,0.86,1.07,1.34,1.66,2.07,2.58,3.22,4.01,5.0,6.0"
    
    delimiter = ','

    nsteps_yr = 365 * 24 # number of steps in the first year of the met. data
    
    # loop over all catchments and write config files
    for catID in catids:
        cat_name = 'cat-'+str(catID)
        forcing_file = glob.glob(os.path.join(forcing_dir, cat_name+'*.csv'))[0]
        
        # obtain annual mean surface temperature as proxy for initial soil temperature
        #df_forcing = pd.read_table(forcing_file,  delimiter=',')
        df_forcing = pd.read_csv(forcing_file,  delimiter=',', usecols=['T2D'], nrows=nsteps_yr, index_col=None)
        
        # compute mean annual air temperature for model initialization
        #MAAT = [str(round(df_forcing['T2D'][:nsteps_yr].mean(), 2)),]*ncells
        MAAT = [str(round(df_forcing['T2D'].mean(), 2)),]*ncells
        MAAT = delimiter.join(MAAT)
        
        # get soil type
        soil_id = gdf_soil['ISLTYP'][cat_name]
        
        # sft params set
        sft_params = ['verbosity=none', 'soil_moisture_bmi=1', 'end_time=1.0[d]', 'dt=1.0[h]', 
                      'soil_params.smcmax=' + str(gdf_soil['soil_params.smcmax'][cat_name]) + '[m/m]', 
                      'soil_params.b=' + str(gdf_soil['soil_params.b'][cat_name]) + '[]', 
                      'soil_params.satpsi=' + str(gdf_soil['soil_params.satpsi'][cat_name]) + '[m]', 
                      'soil_params.quartz=' + str(soil_class_NWM['QTZ'][soil_id]) +'[]',
                      'ice_fraction_scheme=' + precip_partitioning_scheme,
                      f'soil_z={soil_z}[m]',
                      f'soil_temperature={MAAT}[K]'
                      ]

        fname_sft = 'sft_config_' + cat_name + '.txt'
        sft_file = os.path.join(sft_dir, fname_sft)
        with open(sft_file, "w") as f:
            f.writelines('\n'.join(sft_params))

#############################################################################
# The function generates configuration file for soil moisture profiles (SMP) model
# @param catids         : array/list of integers contain catchment ids
# @gdf_soil             : geodataframe contains soil properties extracted from the hydrofabric
# @param smp_dir        : output directory (config files are written to this directory)
# @param coupled_models : option needed to modify SMP config files based on the coupling type
#############################################################################
def write_smp_input_files(catids, gdf_soil, smp_dir, coupled_models):

    #soil_z = "0.1,0.3,1.0,2.0"
    soil_z = "0.1,0.15,0.18,0.23,0.29,0.36,0.44,0.55,0.69,0.86,1.07,1.34,1.66,2.07,2.58,3.22,4.01,5.0,6.0"

    # loop over all catchments and write config files
    for catID in catids:
        cat_name = 'cat-'+str(catID) 

        soil_id = gdf_soil['ISLTYP'][cat_name]
                   
        smp_params = ['verbosity=none',
                      'soil_params.smcmax=' + str(gdf_soil['soil_params.smcmax'][cat_name]) + '[m/m]',
                      'soil_params.b=' + str(gdf_soil['soil_params.b'][cat_name]) + '[]',
                      'soil_params.satpsi=' + str(gdf_soil['soil_params.satpsi'][cat_name]) + '[m]',
                      f'soil_z={soil_z}[m]',
                      'soil_moisture_fraction_depth=1.0[m]'
                      ]

        if ("cfe" in coupled_models):
            smp_params += ['soil_storage_model=conceptual', 'soil_storage_depth=2.0']  
        elif ("lasam" in coupled_models):
            smp_params += ['soil_storage_model=layered', 'soil_moisture_profile_option=constant',
                           'soil_depth_layers=2.0', 'water_table_depth=10[m]']
            # note: soil_depth_layers is an array of depths and will be modified in the future for heterogeneous soils 
            # for exmaple, 'soil_depth_layers=0.4,1.75,2.0'
            # SMCMAX is also an array for hetero. soils

        fname_smp = 'smp_config_' + cat_name + '.txt'
        smp_file = os.path.join(smp_dir, fname_smp)
        with open(smp_file, "w") as f:
            f.writelines('\n'.join(smp_params))

#############################################################################
# The function generates configuration file for lumped arid/semi-arid model (LASAM)
# @param catids         : array/list of integers contain catchment ids
# @param soil_param_file : input file containing soil properties read by LASAM
#                          (characterizes soil for specified soil types)
# @gdf_soil             : geodataframe contains soil properties extracted from the hydrofabric
# @param lasam_dir        : output directory (config files are written to this directory)
# @param coupled_models : option needed to modify SMP config files based on the coupling type
#############################################################################
def write_lasam_input_files(catids, soil_param_file, gdf_soil, lasam_dir, coupled_models):

    sft_calib = "False" # update later (should be taken as an argument)

    # used when LASAM coupled with SFT
    #soil_z="10,30,100.0,200.0"
    soil_z = "10.0,15.0,18.0,23.0,29.0,36.0,44.0,55.0,69.0,86.0,107.0,134.0,166.0,207.0,258.0,322.0,401.0,500.0,600.0"
    
    # lasam parameters
    lasam_params_base = ['verbosity=none',
                         'soil_params_file=' + soil_param_file,
                         'layer_thickness=200.0[cm]',
                         'initial_psi=2000.0[cm]',
                         'timestep=300[sec]',
                         'endtime=1000[hr]',
                         'forcing_resolution=3600[sec]',
                         'ponded_depth_max=0[cm]',
                         'use_closed_form_G=false',
                         'layer_soil_type=',
                         'wilting_point_psi=15495.0[cm]',
                         'field_capacity_psi=340.9[cm]',
                         'giuh_ordinates='
                         ]

    if("sft" in coupled_models):
        lasam_params_base.append('sft_coupled=true')
        lasam_params_base.append(f'soil_z={soil_z}[cm]')

    if ( ("sft" in coupled_models) and (sft_calib in ["true", "True"]) ):
        lasam_params_base.append('calib_params=true')

    
    soil_type_loc = lasam_params_base.index("layer_soil_type=")
    giuh_loc_id   = lasam_params_base.index("giuh_ordinates=")
    
    # loop over all catchments and write config files
    for catID in catids:
        cat_name = 'cat-'+str(catID) 
        fname = cat_name+'*.txt'

        lasam_params = lasam_params_base.copy()
        lasam_params[soil_type_loc] += str(gdf_soil['ISLTYP'][cat_name])

        # add giuh ordinates
        giuh_cat = json.loads(gdf_soil['giuh'][cat_name])
        giuh_cat = pd.DataFrame(giuh_cat, columns=['v', 'frequency'])

        giuh_ordinates = ",".join(str(x) for x in np.array(giuh_cat["frequency"]))
        lasam_params[giuh_loc_id] += giuh_ordinates
        
        fname_lasam = 'lasam_config_' + cat_name + '.txt'
        lasam_file = os.path.join(lasam_dir, fname_lasam)
        with open(lasam_file, "w") as f:
            f.writelines('\n'.join(lasam_params))

#############################################################################
# The function generates configuration file for potential evapotranspiration model
# @param catids         : array/list of integers contain catchment ids
# @param gdf_soil       : geodataframe contains soil properties extracted from the model attributes
#                          (characterizes soil for specified soil types)
# @param gdf_soil        : geodataframe contains soil properties extracted from the model attributes
# @param pet_dir         : output directory (config files are written to this directory)
#############################################################################
def write_pet_input_files(catids, gdf_soil, gpkg_file, pet_dir):

    df_cats = gpd.read_file(gpkg_file, layer='divides')
    df_cats = df_cats.to_crs("EPSG:4326") # change CRS to 4326
    
    df_cats.set_index("divide_id", inplace=True)
    
    pet_method = 3

    
    # loop over all catchments and write config files
    for catID in catids:
        cat_name = 'cat-'+str(catID)
        
        centroid_x = str(df_cats['geometry'][cat_name].centroid.x)
        centroid_y = str(df_cats['geometry'][cat_name].centroid.y)

        elevation_mean = gdf_soil['elevation_mean'][cat_name]
        
        # pet parameters
        pet_params = ['verbose=0',
                      f'pet_method={pet_method}',
                      'forcing_file=BMI',
                      'run_unit_tests=0',
                      'yes_aorc=1',
                      'yes_wrf=0',
                      'wind_speed_measurement_height_m=10.0',
                      'humidity_measurement_height_m=2.0',
                      'vegetation_height_m=16.0',
                      'zero_plane_displacement_height_m=0.0003',
                      'momentum_transfer_roughness_length=0.0',
                      'heat_transfer_roughness_length_m=0.0',
                      'surface_longwave_emissivity=1.0',
                      'surface_shortwave_albedo=0.17',
                      'cloud_base_height_known=FALSE',
                      'time_step_size_s=3600',
                      'num_timesteps=720',
                      'shortwave_radiation_provided=1',
                      f'latitude_degrees={centroid_y}',
                      f'longitude_degrees={centroid_x}',
                      f'site_elevation_m={elevation_mean}'
                      ]
    

        
        fname_pet = 'pet_config_' + cat_name + '.txt'
        pet_file = os.path.join(pet_dir, fname_pet)
        with open(pet_file, "w") as f:
            f.writelines('\n'.join(pet_params))

#############################################################################
# The function generates configuration file for t-route model
# @param catids         : array/list of integers contain catchment ids
# @param troute_dir        : output directory (config files are written to this directory)
#############################################################################
def write_troute_input_files(gpkg_file, routing_file, troute_dir, simulation_time,
                             sim_output_dir, is_calib):

    gpkg_name  = os.path.basename(gpkg_file).split(".")[0]
    
    if (not os.path.exists(routing_file)):
        sys.exit("Sample routing yaml file does not exist, provided is " + routing_file)
    
    with open(routing_file, 'r') as file:
        d = yaml.safe_load(file)
    
    d['network_topology_parameters']['supernetwork_parameters']['geo_file_path'] = gpkg_file
    d['network_topology_parameters']['waterbody_parameters']['level_pool']['level_pool_waterbody_parameter_file_path'] = gpkg_file
    d['network_topology_parameters']['supernetwork_parameters']['title_string'] = gpkg_name
    
    dt = 300 # seconds
    """
    layers = fiona.listlayers(gpkg_file)

    flowpath_layer = [layer for layer in layers if 'flowpath' in layer][0]
    
    gdf_fp_attr = gpd.read_file(gpkg_file, layer=flowpath_layer)

    params = schema.get_schema_flowpath_attributes(gdf_fp_attr)
    """
    
    params = get_flowpath_attributes(gpkg_file, full_schema=True)

    columns = {
        'key' : params['key'],
        'downstream' : params['downstream'],
        'mainstem' : params['mainstem'],
        'dx' : params['dx'],
        'n' : params['n'],
        'ncc' : params['ncc'],
        's0' : params['s0'],
        'bw' : params['bw'],
        'waterbody' : params['waterbody'],
        'gages' : params['gages'],
        'tw' : params['tw'],
        'twcc' : params['twcc'],
        'musk' : params['musk'],
        'musx' : params['musx'],
        'cs' : params['cs'],
        'alt' : params['alt']
    }

    d['network_topology_parameters']['supernetwork_parameters']['columns'] = columns
    
    #start_time = pd.Timestamp(simulation_time['start_time']).strftime("%Y-%m-%d_%H:%M:%S")
    start_time = pd.Timestamp(simulation_time['start_time'])
    end_time   = pd.Timestamp(simulation_time['end_time'])    
    
    diff_time = (end_time - start_time).total_seconds()
    
    d['compute_parameters']['restart_parameters']['start_datetime'] = start_time.strftime("%Y-%m-%d_%H:%M:%S")
    

    if(is_calib in ["True", "true", "TRUE", "Yes", "yes",  "YES"]):
        d['compute_parameters']['forcing_parameters']['qlat_input_folder'] =  "./"
    else:
        d['compute_parameters']['forcing_parameters']['qlat_input_folder'] =  os.path.join(sim_output_dir,"div")
    
    d['compute_parameters']['forcing_parameters']['qlat_file_pattern_filter'] = "nex-*"
    #d['compute_parameters']['forcing_parameters']['binary_nexus_file_folder'] = "outputs/troute_parq"
    del d['compute_parameters']['forcing_parameters']['binary_nexus_file_folder']
    d['compute_parameters']['forcing_parameters']['nts']                      = int(diff_time / dt)
    d['compute_parameters']['forcing_parameters']['max_loop_size']            = 10000000

    d['compute_parameters']['cpu_pool'] = 10

    if(is_calib in ["True", "true", "TRUE", "Yes", "yes",  "YES"]):
        stream_output = {
            "csv_output" : {
                "csv_output_folder" : "./"
            },
            "stream_output" : {
                "stream_output_directory" : "./",
                'stream_output_time'      : -1, #[hr], -1 = write one file at the end of simulation
                'stream_output_type'      : '.csv', # netcdf '.nc' or '.csv' or '.pkl'
                'stream_output_internal_frequency' : 60 #[min]
            }
        }
    else:
        stream_output = {
            "stream_output" : {
                'stream_output_directory' : os.path.join(sim_output_dir, "troute"),
                'stream_output_time'      : -1, #[hr], -1 = write one file at the end of simulation
                'stream_output_type'      : '.csv', # netcdf '.nc' or '.csv' or '.pkl'
                'stream_output_internal_frequency' : 60 #[min]
            }
        }
    
    d['output_parameters'] = stream_output
    
    with open(os.path.join(troute_dir,"troute_config.yaml"), 'w') as file:
        yaml.dump(d,file, default_flow_style=False, sort_keys=False)


#############################################################################
# The function generates configuration file for t-route model
# @param catids         : array/list of integers contain catchment ids
# @ngen_dir             : ngen directory
# @param gpkg_file      : basin geopackage file
# @param real_file      : realization file
#############################################################################
def write_calib_input_files(gpkg_file, ngen_dir, conf_dir, realz_file, realz_file_par,
                            troute_output_file, ngen_cal_basefile, num_proc = 1):

    if (not os.path.exists(ngen_cal_basefile)):
        sys.exit("Sample calib yaml file does not exist, provided is " + ngen_cal_basefile)

    basin_workflow_dir = os.path.dirname(os.path.dirname(ngen_cal_basefile))

    gpkg_name  = os.path.basename(gpkg_file).split(".")[0]
    
    with open(ngen_cal_basefile, 'r') as file:
        d = yaml.safe_load(file)

    d['general']['workdir']    = os.path.dirname(os.path.dirname(gpkg_file))

    d['model']['binary']      = os.path.join(ngen_dir, "cmake_build/ngen")
    d['model']['realization'] = realz_file
    d['model']['hydrofabric'] = gpkg_file
    d['model']['routing_output'] = f'./flowveldepth_{gpkg_name}.csv' # this gpkg_name should be consistent with title_string in troute
    #"./troute_output_201010010000.csv" # in the ngen-cal created directory named {current_time}_ngen_{random stuff}_worker
    #d['model']['routing_output'] = troute_output_file # if in the outputs/troute directory


    gage_id = get_flowpath_attributes(gpkg_file, gage_id=True)

    if (len(gage_id) == 1):
        d['model']['eval_feature'] = gage_id[0]
    else:
        print ("more than one rl_gages exist in the geopackage, using max drainage area to filter...")
        div = gpd.read_file(gpkg_file, layer='divides')
        df = div[['divide_id', 'tot_drainage_areasqkm']]
        index = df['divide_id'].map(lambda x: 'wb-'+str(x.split("-")[1]))
        df.set_index(index, inplace=True)
        idmax = df['tot_drainage_areasqkm'].idxmax() # maximum drainage area catchment ID; downstream outlet
        d['model']['eval_feature'] = idmax


    # 2nd strategy: using total drainage area to locate the basin outlet gage ID
    """
    div = gpd.read_file(gpkg_file, layer='divides')
    df = div[['divide_id', 'tot_drainage_areasqkm', 'toid']]
    index = df['toid'].map(lambda x: 'wb-'+str(x.split("-")[1]))
    df.set_index(index, inplace=True)
    df.index.name = 'wb_id'  # index name
    idmax = df['tot_drainage_areasqkm'].idxmax() # maximum drainage area catchment ID; downstream outlet
    d['model']['eval_feature'] = idmax
    """

    if (num_proc > 1):
        d['model']['parallel'] = num_proc
        d['model']['partitions'] = realz_file_par

    if os_name == "Darwin":
        d['model']['binary'] = f'PYTHONEXECUTABLE=$(which python) ' + os.path.join(ngen_dir, "cmake_build/ngen")
    else:
        d['model']['binary'] = os.path.join(ngen_dir, "cmake_build/ngen")
    
    with open(os.path.join(conf_dir,"calib_config.yaml"), 'w') as file:
        yaml.dump(d,file, default_flow_style=False, sort_keys=False)


#############################################################################
# Return flowpath attributes for t-troue and ngen-cal
#############################################################################
def get_flowpath_attributes(gpkg_file, full_schema=False, gage_id=False):

    layers = fiona.listlayers(gpkg_file)

    flowpath_layer = [layer for layer in layers if 'flowpath' in layer and not 'flowpaths' in layer][0]

    gdf_fp_attr = gpd.read_file(gpkg_file, layer=flowpath_layer)

    params = schema.get_schema_flowpath_attributes(gdf_fp_attr, for_gage_id = gage_id)

    if (full_schema):
        return params
    elif (gage_id):
        # get the gage and waterbody IDs for calibration
        gage_id      = params['gages']   # gage or rl_gages
        waterbody_id = params['key']     # id or link

        gdf_fp_cols = gdf_fp_attr[[waterbody_id, gage_id]] # select the two columns of interest
        basin_gage  = gdf_fp_cols[gdf_fp_cols[gage_id].notna()]
        basin_gage_id = basin_gage[waterbody_id].tolist()

        return basin_gage_id


#############################################################################
# The function generates configuration file for forcing data downlaoder
# @param catids         : array/list of integers contain catchment ids
# @ngen_dir             : ngen directory
# @param gpkg_file      : basin geopackage file
# @param real_file      : realization file
#############################################################################
def write_forcing_input_files(forcing_basefile, gpkg_file, time):

    if (not os.path.exists(forcing_basefile)):
        sys.exit("Sample forcing yaml file does not exist, provided is " + forcing_basefile)

    
    with open(forcing_basefile, 'r') as file:
        d = yaml.safe_load(file)
    time_sim = json.loads(time)

    print ("T: ", time_sim)
    
    start_yr = pd.Timestamp(time_sim['start_time']).year #strftime("%Y")
    end_yr = pd.Timestamp(time_sim['end_time']).year #strftime("%Y")
    
    if (start_yr <= end_yr):
        end_yr = end_yr + 1

    d['gpkg']  = gpkg_file
    d["years"] = [start_yr, end_yr]
    d["out_dir"] = os.path.join(os.path.dirname(gpkg_file), "forcing")

    if (not os.path.exists(d["out_dir"])):
        os.makedirs("data/forcing")

    with open(os.path.join(d["out_dir"],"forcing_config.yaml"), 'w') as file:
        yaml.dump(d,file, default_flow_style=False, sort_keys=False)

    return os.path.join(d["out_dir"],"forcing_config.yaml")

#############################################################################
#############################################################################
def create_directory(dir_name):
    if (os.path.exists(dir_name)):
        str_sub="rm -rf "+dir_name
        out=subprocess.call(str_sub,shell=True)
    os.mkdir(dir_name)


#############################################################################
# main function controlling calls to modules writing config files
# @param gpkg_file       : hydrofabric geopackage file (.gpkg)
# @param forcing_dir     : forcing data directory containing data for each catchment
# @param output_dir      : output directory (config files are written to subdirectories under this directory)
# @param ngen_dir        : path to nextgen directory
# @param models_option   : models coupling option (pre-defined names; see main.py)
# @param runoff_schame   : surface runoff schemes - Options = Schaake or Xinanjiang (For CFE and SFT)
# @param time            : dictionary containing simulations start and end time
# @param overwrite       : boolean (if true, existing output directories are deleted or overwritten)
#############################################################################
def main():

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-gpkg", dest="gpkg_file",     type=str, required=True,  help="the gpkg file")
        parser.add_argument("-f",    dest="forcing_dir",   type=str, required=True,  help="the forcing files directory")
        parser.add_argument("-o",    dest="output_dir",    type=str, required=True,  help="the output files directory")
        parser.add_argument("-ngen", dest="ngen_dir",      type=str, required=True,  help="the ngen directory")
        parser.add_argument("-m",    dest="models_option", type=str, required=True,  help="option for models coupling")
        parser.add_argument("-p",    dest="precip_partitioning_scheme", type=str, required=False,
                            help="option for precip partitioning scheme", default="Schaake")
        parser.add_argument("-r",    dest="surface_runoff_scheme", type=str, required=False,
                            help="option for surface runoff scheme", default="GIUH")
        parser.add_argument("-t",    dest="time",          type=json.loads, required=True,
                            help="simulation start/end time") 
        parser.add_argument("-ow",   dest="overwrite",     type=str, required=False, default=True,
                            help="overwrite old/existing files")
        parser.add_argument("-troute", dest="troute",     type=str, required=False, default=False, help="option for t-toure")
        parser.add_argument("-routfile", dest="routfile", type=str, required=False, default=False, help="routing sample config file")
        parser.add_argument("-v",      dest="verbosity",  type=int, required=False, default=False, help="verbosity option (0, 1, 2)")
        parser.add_argument("-json",   dest="json_dir",   type=str, required=True,  help="realization files directory")
        parser.add_argument("-sout",   dest="sim_output_dir",  type=str, required=True,  help="ngen runs output directory")
        parser.add_argument("-c",      dest="calib",     type=str, required=False, default=False, help="option for calibration")
        parser.add_argument("-schema", dest="schema",    type=str, required=False, default=False, help="gpkg schema type")
    except:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    if (not os.path.exists(args.gpkg_file)):
        str_msg = 'The gpkg file does not exist! %s'%args.gpkg_file
        sys.exit(str_msg)

    # check if the forcing dir is under Inputs directory
    if (not os.path.exists(args.forcing_dir)):
        str_msg = 'The forcing directory does not exist! %s'%args.forcing_dir
        sys.exit(str_msg)


    try:
        gdf_soil, catids = read_gpkg_file(args.gpkg_file,
                                          args.models_option,
                                          args.surface_runoff_scheme,
                                          args.verbosity,
                                          schema_type=args.schema)
    except:
        print("Couldn't read geopackage file for model-attributes successfully..")
        sys.exit(1)        
    # doing it outside NOM as some of params from this file are also needed by CFE for Xinanjiang runoff scheme
    nom_params = os.path.join(args.ngen_dir,"extern/noah-owp-modular/noah-owp-modular/parameters")
    
    # *************** NOM  ********************
    if "nom" in args.models_option:
        if (args.verbosity >=3):
            print ("Generating config files for NOM ...")
        nom_dir = os.path.join(args.output_dir,"nom")
        create_directory(nom_dir)
        str_sub ="cp -r "+ nom_params + " %s"%nom_dir
        out=subprocess.call(str_sub,shell=True)
        nom_soil_file = os.path.join(nom_dir,"parameters/SOILPARM.TBL")

        write_nom_input_files(catids, nom_dir, args.forcing_dir,  gdf_soil, args.time, args.verbosity)
    
    # *************** CFE  ********************
    if "cfe" in args.models_option:
        if (args.verbosity >=3):
            print ("Generating config files for CFE ...")
        cfe_dir = os.path.join(args.output_dir,"cfe")
        create_directory(cfe_dir)

        # read NWM soil class
        nom_soil_file = os.path.join(nom_params,"SOILPARM.TBL")
        soil_class_NWM = get_soil_class_NWM(nom_soil_file)
        
        write_cfe_input_files(catids, args.precip_partitioning_scheme, args.surface_runoff_scheme,
                              soil_class_NWM, gdf_soil, cfe_dir, args.models_option)

    # *************** TOPMODEL  ********************
    if "topmodel" in args.models_option:
        if (args.verbosity >=3):
            print ("Generating config files for TopModel ...")
        tm_dir = os.path.join(args.output_dir,"topmodel")
        create_directory(tm_dir)
        
        write_topmodel_input_files(catids, gdf_soil, tm_dir, args.models_option)

    # *************** PET  ********************
    if "pet" in args.models_option:
        if (args.verbosity >=3):
            print ("Generating config files for PET ...")
        pet_dir = os.path.join(args.output_dir,"pet")
        create_directory(pet_dir)
        
        write_pet_input_files(catids, gdf_soil, args.gpkg_file, pet_dir)
        
    # *************** SFT ********************
    if "sft" in args.models_option:
        if (args.verbosity >=3):
            print ("Generating config files for SFT and SMP ...")
        smp_only_flag = False
        
        sft_dir = os.path.join(args.output_dir,"sft")
        create_directory(sft_dir)

        smp_dir = os.path.join(args.output_dir,"smp")
        create_directory(smp_dir)

        # read NWM soil class
        nom_soil_file = os.path.join(nom_params,"SOILPARM.TBL")
        soil_class_NWM = get_soil_class_NWM(nom_soil_file)
        
        write_sft_input_files(catids, args.precip_partitioning_scheme, args.surface_runoff_scheme,
                              args.forcing_dir, gdf_soil, soil_class_NWM, sft_dir)

        write_smp_input_files(catids, gdf_soil, smp_dir, args.models_option)
        
    elif ("smp" in args.models_option):
        if (args.verbosity >=3):
            print ("Generating config files for SMP...")

        smp_dir = os.path.join(args.output_dir,"smp")
        create_directory(smp_dir)

        write_smp_input_files(catids, gdf_soil, smp_dir, args.models_option)
    
    
    if "lasam" in args.models_option:
        if (args.verbosity >=3):
            print ("Generating config files for LASAM ...")
        lasam_params = os.path.join(args.ngen_dir,"extern/LGAR-C/data/vG_default_params.dat")

        if (not os.path.isfile(lasam_params)):
            lasam_params = os.path.join(args.ngen_dir,"extern/LASAM/data/vG_default_params.dat")

        lasam_dir = os.path.join(args.output_dir,"lasam")
        create_directory(lasam_dir)
    
        str_sub ="cp -r "+ lasam_params + " %s"%lasam_dir
        out=subprocess.call(str_sub,shell=True)

        write_lasam_input_files(catids, os.path.join(lasam_dir, "vG_default_params.dat"),
                                gdf_soil, lasam_dir, args.models_option)


    if (args.troute):
        write_troute_input_files(args.gpkg_file, args.routfile, args.output_dir, args.time,
                                 sim_output_dir = args.sim_output_dir, is_calib = args.calib)

    #if (args.calib):
    #    real_file = os.path.join(args.json_dir, "realization_%s.json"%args.models_option)
    #    write_calib_input_files(args.gpkg_file, args.ngen_dir, args.output_dir, real_file)
    
    ## create uniform forcings
    #forcing_file = os.path.join(args.forcing_dir,"cat-base.csv")
    #write_forcing_files(catids, forcing_file)
    

if __name__ == "__main__":
    main()

    

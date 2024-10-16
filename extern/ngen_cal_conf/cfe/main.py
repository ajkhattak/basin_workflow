import geopandas as gpd
import pandas as pd

from ngen.config_gen.file_writer import DefaultFileWriter
from ngen.config_gen.hook_providers import DefaultHookProvider
from ngen.config_gen.generate import generate_configs

#from ngen.config_gen.models.cfe import Cfe
#from ngen.config_gen.models.pet import Pet

from ngen_cal_user_conf.cfe import Cfe

# or pass local file paths instead
hf_file = "/Users/ahmadjan/Core/SimulationsData/projects/ngen_evaluation_camels/testX/01052500/data/gage_01052500.gpkg"

hf: gpd.GeoDataFrame = gpd.read_file(hf_file, layer="divides")
hf_lnk_data: gpd.GeoDataFrame = gpd.read_file(hf_file, layer="model-attributes")


hook_provider = DefaultHookProvider(hf=hf, hf_lnk_data=hf_lnk_data)
# files will be written to ./config
#file_writer = DefaultFileWriter("./Users/ahmadjan/Core/SimulationsData/projects/ngen_evaluation_camels/testX/01052500/configX/")
file_writer = DefaultFileWriter("./configX/")


generate_configs(
    hook_providers=hook_provider,
    hook_objects=[Cfe],
    file_writer=file_writer,
)


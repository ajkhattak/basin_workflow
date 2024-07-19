import os
import shutil

#def create_clean_dirs(root_dir, config_dir = "configs", json_dir = "json", setup_another_simulation = False,
#                      rename_existing_simulation = "", clean_all = False, clean_except_data = False):
def create_clean_dirs(root_dir, config_dir = "configs", json_dir = "json", output_dir = "outputs",
                      setup_simulation = True, rename_existing_simulation = "", clean = ["none"]):

    if (isinstance(rename_existing_simulation, str) and rename_existing_simulation != ""):
        subdirs  = os.listdir(root_dir)
        os.mkdir(rename_existing_simulation)
        for d in subdirs:
            if (d in ["configs", "json", "outputs"]):
                shutil.move(d, rename_existing_simulation)

    
    if (clean == ["all"]):
        subdirs  = os.listdir(root_dir)
        for d in subdirs:
            if (d != "data"):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
    elif (clean == ["existing"]):
        subdirs  = os.listdir(root_dir)
        for d in subdirs:
            if (d in ["configs", "json", "outputs"]):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
    elif (len(clean) >= 1 and clean != ["none"]):
        subdirs  = os.listdir(root_dir)
        for d in subdirs:
            if (d in clean):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)

    if (setup_simulation):
        subdirs  = os.listdir(root_dir)
        for d in subdirs:
            if (d in ["configs", "json", "outputs"]):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
        
        os.mkdir(config_dir)
        os.mkdir(json_dir)
        os.makedirs("outputs/div")
        os.makedirs("outputs/troute")
        os.makedirs("outputs/troute_parq")
    
    if (os.path.isdir("dem")):
        shutil.rmtree("dem")
    

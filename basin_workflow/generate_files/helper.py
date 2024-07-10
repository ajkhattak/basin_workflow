import os
import shutil

def create_clean_dirs(root_dir, config_dir = "configs", json_dir = "json", setup_another_simulation = False,
                      rename_existing_simulation ="", clean_all = False, clean_except_data = False):

    if (setup_another_simulation):
        subdirs  = os.listdir(root_dir)
        os.mkdir(rename_existing_simulation)
        for d in subdirs:
            if (d in ["configs", "json", "outputs"]):
                shutil.move(d, rename_existing_simulation)

    if (clean_except_data):
        subdirs  = os.listdir(root_dir)
        for d in subdirs:
            if (d != "data"):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
    
    elif (clean_all):
        subdirs  = os.listdir(root_dir)
        for d in subdirs:
            if (d in ["configs", "json", "outputs"]):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
           
    if (not os.path.isdir(config_dir)):
        os.mkdir(config_dir)

    if (not os.path.isdir(json_dir)):
        os.mkdir(json_dir)

    if (os.path.isdir("dem")):
        shutil.rmtree("dem")


    

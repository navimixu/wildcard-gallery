from modules import scripts
from modules import shared

import os
import shutil
import yaml
from pathlib import Path
import errno


RES_FOLDER = os.path.join(scripts.basedir(), "resources")
CARDS_FOLDER = os.path.join(scripts.basedir(), "cards")
WILDCARDS_FOLDER = getattr(shared.opts, "wcc_wildcards_directory","").split("\n")
WILDCARDS_FOLDER = [wdir for wdir in WILDCARDS_FOLDER if os.path.isdir(wdir)]
WILD_STR = getattr(shared.opts, "dp_parser_wildcard_wrap", "__")
STRAY_RES_folder = os.path.join(scripts.basedir(), "STRAY_RESOURCES")
COLL_PREV_folder = os.path.join(scripts.basedir(), "COLLECTED_PREVIEWS")

def find_ext_wildcard_paths():
    try:
        from modules.paths import extensions_dir, script_path
        EXT_PATH = Path(extensions_dir).absolute()
    except ImportError:
        FILE_DIR = Path().absolute()
        EXT_PATH = FILE_DIR.joinpath("extensions").absolute()

    found = list(EXT_PATH.glob("*/wildcards/"))

    try:
        from modules.shared import opts
    except ImportError:
        opts = None

    # Append custom wildcard paths
    custom_paths = [
        getattr(shared.cmd_opts, "wildcards_dir", None),    # Cmd arg from the wildcard extension
        getattr(opts, "wildcard_dir", None),                # Custom path from sd-dynamic-prompts
    ]
    for path in [Path(p).absolute() for p in custom_paths if p is not None]:
        if path.exists():
            found.append(path)

    return [str(x) for x in found]

def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise 

def collect_Wildcards(wildcards_dirs):
    collected_paths = []
    whitelist  = [item for item in getattr(shared.opts, "wcc_wildcards_whitelist", "").split("\n") if item]
    blacklist  = [item for item in getattr(shared.opts, "wcc_wildcards_blacklist", "").split("\n") if item]
    if not wildcards_dirs : print("___Wildcard Directories is not setup yet!___")
    for wildcards_dir in wildcards_dirs :
        for root, dirs, files in os.walk(wildcards_dir):
            for file in files:
                    if file.lower().endswith(".txt") :
                        #file_name, file_extension = os.path.splitext(os.path.basename(file))
                        wild_path_txt = os.path.relpath(os.path.join(root,file),wildcards_dir).replace(os.path.sep, "/").replace(".txt", "")
                        if((wild_path_txt in whitelist)or not whitelist) and not(wild_path_txt in blacklist):
                            collected_paths.append(wild_path_txt)
                    elif file.lower().endswith(".yaml") :
                        wild_yaml_name, ext = os.path.splitext(file)
                        wild_yaml_name = wild_yaml_name.split(os.path.pathsep)[-1]
                        if((wild_yaml_name in whitelist)or not whitelist) and not(wild_yaml_name in blacklist):
                            collected_paths += get_yaml_paths(os.path.join(root, file))
    return list(collected_paths)

def get_yaml_paths(yaml_file_path):
    def traverse(data, path=''):
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}/{key}" if path else key
                traverse(value, new_path)
        else:
            paths.add(path)

    # Loads a YAML file!!
    try:
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
        paths = set()
        traverse(data)
        return list(paths)
    except yaml.YAMLError as e:
        print(f"Error occured while trying to load the file {yaml_file_path} ")
        print(f"Exception arised : {e} ")
        return []

def get_safe_name(selected_wild_path, wild_paths_list, inclusion_level = 2):

    path_parts = selected_wild_path.split('/')

    if len(path_parts) > inclusion_level:
        parent = path_parts[-inclusion_level-1]
    else:
        parent = ""
    
    curated_format_sel = '/'.join(path_parts[-inclusion_level:])

    curated_format_list = ['/'.join(wild_path.split('/')[-inclusion_level:]) for wild_path in wild_paths_list]
    
    occurance_count  = curated_format_list.count(curated_format_sel)
    if occurance_count > 1 :
        count = curated_format_list.count(curated_format_sel) + 1
        suffix = parent if parent else count
        return f"{curated_format_sel}({suffix})" , parent
    else:
        return curated_format_sel , parent

def get_safe_name_2(selected_wild_path, wild_paths_list):

    path_parts = selected_wild_path.split('/')


    parent = path_parts[-2] if len(path_parts) > 1 else ""
    aux_fallback_parent = path_parts[-3] if len(path_parts) > 2 else ""
    

    curated_format_list = ['/'.join(wild_path.split('/')[-2:]) for wild_path in wild_paths_list]
    
    occurance_count = 0
    occurance_count  = curated_format_list.count('/'.join(path_parts[-1:]))
    occurance_count_aux  = curated_format_list.count('/'.join(path_parts[-2:]))
    
    if occurance_count_aux > 1 :
        suffix = f"{aux_fallback_parent}/{parent}" if aux_fallback_parent else f"{parent}({occurance_count_aux+1})"
        return f"{path_parts[-1]}({suffix})" , parent
    else:
        occurance_count_str = "" if occurance_count == 0 else f"({occurance_count+1})"
        suffix = parent if parent else occurance_count_str
        return f"{path_parts[-1]}({suffix})" , parent

def create_dir_and_file(parent_dir, path, extentsion =".card"):

    if os.path.dirname(path): 
        dir_path, file_name = os.path.split(path)
        full_dir_path = os.path.join(parent_dir, dir_path) 
        os.makedirs(full_dir_path, exist_ok=True) 
        file_path = os.path.join(full_dir_path, file_name + extentsion)
    else: 
        file_path = os.path.join(parent_dir, path + extentsion)

    if not os.path.exists(file_path):
        Path(file_path).touch() 

    return file_path

def clean_residue (cards_dir, wildcards_list, extentsion =".card"):
    stay_cards_list = []
    residue_folders_list = []
    for root, dirs, files in os.walk(cards_dir):
        # Remove stray cards
        for file in files:
                if file.lower().endswith(extentsion) :
                    file_path = os.path.join(root, file)
                    relative_file_path = os.path.relpath(file_path, cards_dir)
                    fromatted_path = relative_file_path.replace(os.path.sep, "/").replace(extentsion, "").upper()
                    
                    if not fromatted_path in (wildcard.upper() for wildcard in wildcards_list):
                        stay_cards_list.append(file_path)
                        silentremove(file_path)
    
        # Removes empty directories
        for dirname in dirs:
            dir_to_check = os.path.join(root, dirname)
            if not os.listdir(dir_to_check):
                os.rmdir(dir_to_check)
                residue_folders_list.append(dir_to_check) 

    if(stay_cards_list): print(f'______ {len(stay_cards_list)} Wildcard Cards Altered______')
    if(residue_folders_list): print(f'______ {len(residue_folders_list)} Residue Folders Cleared______')

def collect_previews_by_channel (channel, wildpath_selector, cards_dir = CARDS_FOLDER):
    collected_previews_list = []
    msg = "no wildcard previews were collected"
    channel_suffix = "."+channel.replace(" ","") if (not channel=="") and (not channel=="default") and channel  else ""
    os.makedirs(COLL_PREV_folder, exist_ok=True) 
    for root, dirs, files in os.walk(cards_dir):
        for file in files:
                if file.lower().endswith(f"{channel_suffix}.jpeg") or file.lower().endswith(f"{channel_suffix}.jpg")  or file.lower().endswith(f"{channel_suffix}.png")  or file.lower().endswith(f"{channel_suffix}.gif") and (not channel=="default" or (channel=="default" and file.lower().count(".")==1) ):
                    match_found = False
                    for wpath in wildpath_selector :
                        save_file_name= os.path.join(os.path.abspath(cards_dir), wpath.replace("/", os.path.sep))+"."
                        file_path  = os.path.abspath(os.path.join(root, file))
                        if (file_path.lower().startswith(save_file_name.lower())):
                            collected_previews_list.append(file_path)
                            match_found = True
                            break

                    if(match_found):    
                        try:
                            dest_file_path = os.path.join(os.path.relpath(collected_previews_list[-1], CARDS_FOLDER), COLL_PREV_folder)
                            shutil.copy2(collected_previews_list[-1], dest_file_path)
                        except OSError:
                            print(f"failed to collect [{os.path.join(root, file)}]")
                                

    if(collected_previews_list):
        msg = f'______ {len(collected_previews_list)} previews from channel[{channel}] were collected______'
        print(msg)
        print(f'copied into: [{COLL_PREV_folder}]')
    return msg

def delete_previews_by_channel (channel, wildpath_selector, cards_dir = CARDS_FOLDER):
    collected_previews_list = []
    msg = "no wildcard previews were deleted"
    channel_suffix = "."+channel.replace(" ","") if (not channel=="") and (not channel=="default") and channel  else ""
    os.makedirs(COLL_PREV_folder, exist_ok=True) 
    for root, dirs, files in os.walk(cards_dir):
        for file in files:
                if file.lower().endswith(f"{channel_suffix}.jpeg") or file.lower().endswith(f"{channel_suffix}.jpg")  or file.lower().endswith(f"{channel_suffix}.png")  or file.lower().endswith(f"{channel_suffix}.gif") and (not channel=="default" or (channel=="default" and file.lower().count(".")==1) ):
                    match_found = False
                    for wpath in wildpath_selector :
                        save_file_name= os.path.join(os.path.abspath(cards_dir), wpath.replace("/", os.path.sep))+"."
                        file_path  = os.path.abspath(os.path.join(root, file))
                        if (file_path.lower().startswith(save_file_name.lower())):
                            collected_previews_list.append(file_path)
                            match_found = True
                            break

                    if(match_found):    
                        try:
                            silentremove(collected_previews_list[-1])
                        except OSError:
                            print(f"failed to delete [{os.path.join(root, file)}]")
                                

    if(collected_previews_list):
        msg = f'______ {len(collected_previews_list)} previews from channel[{channel}] were deleted______'
        print(msg)
    return msg

def collect_stray_previews (wild_paths, cards_dir = CARDS_FOLDER):
    stay_previews_list = []
    os.makedirs(STRAY_RES_folder, exist_ok=True) 
    
    for root, dirs, files in os.walk(cards_dir):
        # Remove stray cards
        for file in files:
                if file.lower().endswith(".jpeg") or file.lower().endswith(".jpg")  or file.lower().endswith(".png")  or file.lower().endswith(".gif") :
                    exist_check = False
                    for wpath in wild_paths :
                        save_file_name= os.path.join(os.path.abspath(cards_dir), wpath.replace("/", os.path.sep))+"."
                        file_path  = os.path.abspath(os.path.join(root, file))
                        if (file_path.lower().startswith(save_file_name.lower())):
                            exist_check = True
                            break
                    if not exist_check :
                        new_dir = os.path.join(STRAY_RES_folder, os.path.relpath(os.path.join(root, file),cards_dir).replace(os.path.sep,"+"))
                        print(new_dir)
                        
                        try:
                            os.replace(os.path.join(root, file), new_dir)
                            stay_previews_list.append(new_dir)
                        except OSError:
                            print(f"failed to collect [{os.path.join(root, file)}]")
                                

    if(stay_previews_list):
        print(f'______ {len(stay_previews_list)} stray previews collected______')
        print(f'moved into: [{STRAY_RES_folder}]')



if(not WILDCARDS_FOLDER): WILDCARDS_FOLDER = find_ext_wildcard_paths()

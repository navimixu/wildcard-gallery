from modules import scripts, shared 
from modules.paths import extensions_dir


import os, shutil, yaml, json, errno, urllib.parse, time, zipfile, io, requests, re
from typing import Union, IO
from pathlib import Path
from fastapi.exceptions import HTTPException
from fastapi import Request
from starlette.responses import FileResponse
from dataclasses import dataclass, field, asdict
import mimetypes

def fetch_wilcards_dir():
    setting_dir = getattr(shared.opts, "wcc_wildcards_directory","").strip()
    found_path = os.path.join(extensions_dir,"sd-dynamic-prompts","wildcards")
    if os.path.isdir(setting_dir):
        return setting_dir
    elif getattr(shared.opts, "wildcard_dir", None):
        found_path = getattr(shared.opts, "wildcard_dir", None)
    elif getattr(shared.cmd_opts, "wildcards_dir", None):
        found_path = getattr(shared.cmd_opts, "wildcards_dir", None)
    
    if os.path.isdir(found_path):
        setattr(shared.opts,"wcc_wildcards_directory",found_path)
        return found_path
    else:
        print("No wilcards directory was found, make sure you have the sd-dynamic-prompts extension installed, if you have a custom directory make sure to set it manually in the settings")
        return None


EXT_NAME = "Wildcards Gallery"
BASE_URL = ""
RES_FOLDER = os.path.join(scripts.basedir(), "resources")
META_FOLDER = os.path.join(scripts.basedir(), "metadata")
CARDS_FOLDER = os.path.join(scripts.basedir(), "cards")
WILDCARDS_FOLDER = fetch_wilcards_dir()
ADDED_WILDCARDS_FOLDER = "wildcard_gallery"
WILD_STR = getattr(shared.opts, "dp_parser_wildcard_wrap", "__")
COLL_PREV_folder = os.path.join(scripts.basedir(), "USER_OUTPUT")
STRAY_RES_folder = os.path.join(COLL_PREV_folder, "STRAY_RESOURCES")
IMG_CHANNELS= ["default", "preview1", "preview2", "preview3","channel4"]
VALID_IMG_EXT = [".jpeg", ".jpg", ".png", ".gif"]
ICON_LIB = {
    "copy"  : os.path.join(RES_FOLDER,"icons","copy-svgrepo-com.svg"),
    "delete": os.path.join(RES_FOLDER,"icons","trash-bin-2-svgrepo-com.svg"),
    "edit"  : os.path.join(RES_FOLDER,"icons","pen-2-svgrepo-com.svg"),
    "fav"   : os.path.join(RES_FOLDER,"icons","heart-svgrepo-com.svg"),
    "unfav"  : os.path.join(RES_FOLDER,"icons","heart-broken-svgrepo-com.svg")
}


SHARED_ASSESTS = {
    "card_fallback":os.path.join(RES_FOLDER,"wcc_fallback.jpg"),
    "card_create":os.path.join(RES_FOLDER,"card-sel.gif"),
    "null_card":os.path.join(RES_FOLDER,"null-preview.jpeg"),
    "custom_yaml": f"{ADDED_WILDCARDS_FOLDER}/custom_cards"
}

@dataclass
class UserAuxMetadata: #NYI
    url: str    = field( default= "")
    os_url: str = field( default= "")
    notes: str  = field( default= "")


@dataclass
class WildcardEntry:
    name: str 
    path: str
    prompts: str  = field( default= "")
    aux_prompt: str  = field( default= "")
    thumbnails: dict[str,str] = field(default_factory=dict)
    last_update:int = field(default=int(time.time()))
    is_preloaded:bool = field( default= False)
    tags: list[str] = field(default_factory=list)
    file_origin: str = field( default= "")
    is_locked:bool = field( default= True)


    def check_lock_status (self): #wip until dynamic cutom files are added
        
        return not os.path.normpath(self.file_origin).endswith(os.path.normpath(SHARED_ASSESTS["custom_yaml"]+".yaml"))

    def get_preview_channels (self):
        preview_channels = []
        for chn,img in self.thumbnails.items():
            if  img != SHARED_ASSESTS["card_fallback"]  and img :
                preview_channels.append(chn)
                
        return preview_channels
    
    def preload_previews(self, channels:list[str]= IMG_CHANNELS, parent_dir:str= CARDS_FOLDER):
        self.is_preloaded = True
        for channel in channels :
            self.thumbnails[channel]= SHARED_ASSESTS["card_fallback"]
            suffix = "" if  channel == "default" else f".{channel}" 
            possible_file  = os.path.join(parent_dir, self.path + suffix)
            for ext in VALID_IMG_EXT:
                img_path = os.path.normpath(possible_file + ext)
                if os.path.exists(img_path):
                    self.thumbnails[channel]=img_path
                    break
                    
    def update_thumbnails(self, update_dict:dict[str,str]={}):
        self.thumbnails.update(update_dict)
        self.last_update = int(time.time())
    
    def nullify_channel_img(self, channels:list[str]= IMG_CHANNELS, parent_dir:str= CARDS_FOLDER):  
        affected_image = []
        fl_nm, fl_ext= os.path.splitext(SHARED_ASSESTS["null_card"])
        self.last_update = int(time.time())
        for channel in channels :
            suffix = "" if  channel == "default" else f".{channel}" 
            resulted_file  = os.path.normpath(os.path.join(parent_dir, self.path + suffix + fl_ext))
            try:
                shutil.copyfile(SHARED_ASSESTS["null_card"],resulted_file)
                affected_image.append(resulted_file)
            except OSError:
                print(f"failed to nullify [{resulted_file}]")
 
        return affected_image

    def delete_channel_img(self, channels:list[str]= IMG_CHANNELS, parent_dir:str= CARDS_FOLDER):
        removed_image = []
        self.last_update = int(time.time())
        for channel in channels :
            suffix = "" if  channel == "default" else f".{channel}" 
            possible_file  = os.path.join(parent_dir, self.path + suffix)
            for ext in VALID_IMG_EXT:
                img_path = os.path.normpath(possible_file + ext)
                if os.path.exists(img_path):
                    try:
                        silentremove(img_path)
                        self.thumbnails[channel]= SHARED_ASSESTS["card_fallback"]
                        removed_image.append(img_path)
                    except OSError:
                        print(f"failed to delete [{img_path}]")
                    break
        return removed_image
    
    def collect_channel_img(self, channels:list[str]= IMG_CHANNELS, parent_dir:str= CARDS_FOLDER, dest_dir:str= COLL_PREV_folder):
        collected_images = []
        os.makedirs(dest_dir, exist_ok=True) 
        for channel in channels :
            suffix = "" if  channel == "default" else f".{channel}" 
            possible_file  = os.path.join(parent_dir, self.path + suffix)
            for ext in VALID_IMG_EXT:
                img_path = os.path.normpath(possible_file + ext)
                if os.path.exists(img_path):
                    try:
                        dest_file_path = os.path.join(dest_dir, os.path.relpath(img_path, parent_dir))
                        copy_with_directories(src= img_path, dst= dest_file_path)
                        collected_images.append(img_path)
                    except OSError:
                        print(f"failed to copy [{img_path}]")
                    break
        return collected_images


    def html_tag_stack(self , config_dict:dict[str,'TagConfig']={}, hide_masked = False, masked_groups=[]):
        config_block = r'style="color: ##tx_col##;background: ##bg_col##;"'
        tag_html_block =r'<div class="wcc_gal_tag" ##stl## >###</div>'
        tags_stack_block =r'<div class="wcc_tag_stack">###</div>'
        tags_stack = ""
        for tag in self.tags:
            config = config_dict.get(tag)
            if config and ((config.masked and hide_masked) or (config.config_name in masked_groups)):
                continue
            tag_cfg = config_block.replace("##tx_col##",config.tx_color).replace("##bg_col##",config.bg_color) if config else ""
            tags_stack+=tag_html_block.replace("##stl##",tag_cfg).replace("###",tag)
        
        
        return tags_stack_block.replace("###",tags_stack)

    def to_galley_item(self, is_selected=False, img_channel="", config_dict:dict[str,'TagConfig']={}, stack_count:int=1, stack_name ="", hidden_tag_groups=[]):
        select_symb = r'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"> <path d="M9 16.2l-4.2-4.2 1.4-1.4L9 13.4l7.8-7.8 1.4 1.4L9 16.2z"></path> </svg>'
        stack_tag = f'<div class="wcc_stack_tag">{stack_count} Cards</div>'
        main_html_block = r'<div class="wcc_gal_item " ##img## >##stk## <div class="shine"></div>###</div>' 
        generated_block = f'<div class="wcc_gal_label">{stack_name}</div>' if stack_count >1 else f'<div class="wcc_gal_label">{self.name}</div>' 

        img_file = self.thumbnails.get(img_channel,"") 
        image_block = f'style="background-image: url({link_img(img_file, self.last_update)});"' if img_file else 'style="background-image: url(./resources/card-no-preview.jpg);"'

        if stack_count >1:
            main_html_block= main_html_block.replace("wcc_gal_item", "wcc_gal_item wcc_item_stack ") 
            main_html_block= main_html_block.replace("##stk##", stack_tag) 
            
        else:
            main_html_block= main_html_block.replace("##stk##", "")
        main_html_block= main_html_block.replace("wcc_gal_item", "wcc_gal_item wcc_item_selected ") if is_selected else main_html_block 
        main_html_block= main_html_block.replace("###", select_symb+"###")

        if "All" not in hidden_tag_groups:
            generated_block= self.html_tag_stack(config_dict, hide_masked= "Masked Tags" in hidden_tag_groups, masked_groups= hidden_tag_groups) + generated_block
        
        return main_html_block.replace("###",generated_block).replace("##img##",image_block)
    
 
    
@dataclass
class TagConfig:
    config_name: str
    bg_color: str   = field(default="#2b527b8a")
    tx_color: str   = field(default="white")
    masked: bool        = field(default=False)
    members: list[str]  = field(default_factory=list)
    added_prompt: str   = field(default="")
    
    @staticmethod
    def load_from_json(filename: str ="tags_config.json") -> list['TagConfig']:
        """
        Loads TagConfig instances from a JSON file.
        
        :param json_file_path: Path to the JSON file.
        :return: A list of TagConfig instances loaded from the file.
        """
        file_path = os.path.join(META_FOLDER,filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
 
            if not isinstance(data, list):
                raise ValueError("JSON content must be an array of tag configurations.")
 
            tag_configs = [TagConfig(**item) for item in data]

            return tag_configs
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except PermissionError:
            print(f"Permission denied: {file_path}")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in {file_path}: {e}")
        except ValueError as e:
            print(f"Value error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        
        return []

def get_base_url(request: Request):
    return {"base_url": str(request.base_url)}


def load_base_url():
    global BASE_URL
    if not BASE_URL:
        try:
            r = requests.get("http://127.0.0.1:7860/wcc_cards/base_url")
            BASE_URL = r.json().get("base_url", "")
        except Exception:
            BASE_URL = ""
    
    return BASE_URL

def fetch_img(filename: str = ""):
    if not os.path.isfile(filename):
        raise HTTPException(status_code=404, detail="File not found")
    else:
        try:
            fileDir = os.path.dirname(filename)
            content_type, _ = mimetypes.guess_type(filename)
            common      = os.path.commonpath([CARDS_FOLDER, fileDir])
            common_res  = os.path.commonpath([RES_FOLDER, fileDir])
        except ValueError:
            raise HTTPException(status_code=403, detail="File out of addon directory")
        
        if common !=CARDS_FOLDER and common_res!=RES_FOLDER:
            raise HTTPException(status_code=403, detail="File out of addon directory")
        elif not content_type:
            raise HTTPException(status_code=415, detail="Unsupported media type")
                                    
    return FileResponse(filename, headers={"Accept-Ranges": "bytes"}, media_type=content_type)

def link_img(filename, ver=1, absolute =False):
    quoted_filename = urllib.parse.quote(filename.replace('\\', '/'))
    root_url = load_base_url() if absolute else "./" 
    return f"{root_url}wcc_cards/img?filename={quoted_filename}&v={ver}"

def copy_with_directories(src, dst):
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    except Exception as e:
        print(f"failed to copy [{src}]")

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

def collect_Wildcards(wildcards_dirs= [WILDCARDS_FOLDER], collect_prompts:bool = False, collect_sub_cards:bool = False) -> dict[str,WildcardEntry]:
    collected_wildcards = {}
    whitelist  = [item for item in getattr(shared.opts, "wcc_wildcards_whitelist", "").split("\n") if item] + [SHARED_ASSESTS["custom_yaml"].split("/")[1]]
    blacklist  = [item for item in getattr(shared.opts, "wcc_wildcards_blacklist", "").split("\n") if item]
    if not wildcards_dirs : print("___Wildcard Directories is not setup yet!___")
    for wildcards_dir in wildcards_dirs :
        if os.path.isdir(wildcards_dir):
            for root, dirs, files in os.walk(wildcards_dir):
                for file in files:
                        if file.lower().endswith(".txt") :  
                            wild_path_txt = os.path.relpath(os.path.join(root,file),wildcards_dir).replace(os.path.sep, "/").replace(".txt", "")
                            if((wild_path_txt in whitelist)or not whitelist) and not(wild_path_txt in blacklist):
                                if collect_prompts and collect_sub_cards:
                                    sub_txt_items =  get_txt_lines(os.path.join(root,file))
                                    if len(sub_txt_items)==1:
                                        collected_wildcards[wild_path_txt] = scanned_data_as_wildcard(node_path= wild_path_txt, prompt=sub_txt_items[0], file_origin_path= os.path.join(root,file)) 
                                
                                    else:
                                        for i, item_data in enumerate(sub_txt_items):
                                            indexed_wild_path = f"{wild_path_txt}[{i}]"
                                            sub_txt_items[indexed_wild_path] = item_data
                                else :
                                    card_prompt = get_txt_content(os.path.join(root,file))  if collect_prompts else ""
                                    collected_wildcards[wild_path_txt] = scanned_data_as_wildcard(node_path= wild_path_txt, prompt=card_prompt, file_origin_path= os.path.join(root,file))  
                                    
                                        
                        elif file.lower().endswith(".yaml") :
                            wild_yaml_name, ext = os.path.splitext(file)
                            wild_yaml_name = wild_yaml_name.split(os.path.pathsep)[-1]
                            if((wild_yaml_name in whitelist)or not whitelist) and not(wild_yaml_name in blacklist):
                                new_scanned_cards = get_yaml_nodes(yaml_file_path= os.path.join(root, file) , deep_scan=collect_sub_cards)
                                for card_path, card_prompt in new_scanned_cards.items():
                                    collected_wildcards[card_path]= scanned_data_as_wildcard(node_path= card_path, prompt=card_prompt, file_origin_path= os.path.join(root, file))

    
    return collected_wildcards

def scanned_data_as_wildcard(node_path:str, prompt:str="", file_origin_path:str=""):
    card_name = node_path.split("/")[-1]
    prompt_str = "||".join(str(p) for p in prompt if p is not None) if isinstance(prompt,list) else f"{prompt}"
    wildcard_obj =  WildcardEntry(name= card_name, 
                         path= node_path, 
                         prompts= prompt_str, 
                         file_origin= file_origin_path)
    wildcard_obj.is_locked = wildcard_obj.check_lock_status()

    return wildcard_obj


def get_yaml_paths(yaml_file_path, separator="/")->list[str]:
    """
    Extracts all unique paths to leaf nodes from a YAML file.

    :param yaml_file_path: Path to the YAML file.
    :param separator: Separator to use for joining keys (default: "/").
    :return: List of unique paths to all leaf nodes in the YAML structure.
    """
    def traverse(data, path=''):
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}{separator}{key}" if path else key
                traverse(value, new_path)
        else:
            paths.add(path)

    try:
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
        paths = set()
        traverse(data)
        return sorted(paths)
    except FileNotFoundError:
        print(f"File not found: {yaml_file_path}")
    except PermissionError:
        print(f"Permission denied: {yaml_file_path}")
    except ValueError as ve:
        print(f"Value error: {ve}")
    except yaml.YAMLError as ye:
        print(f"YAML parsing error in file {yaml_file_path}: {ye}")
    return []

def get_yaml_nodes( yaml_file_path:Union[str, IO], separator:str ="/", deep_scan:bool = False)->dict[str,str]:
    """
    Extracts all unique paths to leaf nodes from a YAML file, along with their corresponding data.

    :param yaml_file_path: Path to the YAML file.
    :param separator: Separator to use for joining keys (default: "/").
    :return: Dictionary with paths as keys and leaf node data as values.
    """
    def traverse(data, path=''):
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}{separator}{key}" if path else key
                traverse(value, new_path)
        elif isinstance(data, list) and len(data)>1 and deep_scan :
            for index, item in enumerate(data):
                new_path = f"{path}{separator}[{index}]"
                traverse(item, new_path)
        else:
            result[path] = data

    try:
        if isinstance(yaml_file_path,str):
            with open(yaml_file_path, 'r') as file:
                data = yaml.safe_load(file)
        else:
            data = yaml.safe_load(yaml_file_path)

        if not isinstance(data, (dict, list)):
            raise ValueError("YAML file must contain a dictionary or list as the root structure.")

        result = {}
        traverse(data)
        return result
    except FileNotFoundError:
        print(f"File not found: {yaml_file_path}")
    except PermissionError:
        print(f"Permission denied: {yaml_file_path}")
    except ValueError as ve:
        print(f"Value error: {ve}")
    except yaml.YAMLError as ye:
        print(f"YAML parsing error in file {yaml_file_path}: {ye}")
    return {}

def get_txt_content(file_path:str)-> str:
    """
    Extracts the content of a text file.

    :param file_path: Path to the text file.
    :return: A string containing the content of the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except PermissionError:
        print(f"Permission denied: {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
    return ""

def get_txt_lines(file_path:str)->list[str]:
    """
    Extracts the content of a text file and returns each line as an item in a list.

    :param file_path: Path to the text file.
    :return: A list of strings, each representing a line in the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read all lines and return as a list of strings
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except PermissionError:
        print(f"Permission denied: {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
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

def create_dir_and_file(parent_dir, path, extentsion =".card")-> str:

    if os.path.dirname(path): 
        dir_path, file_name = os.path.split(path)
        full_dir_path = os.path.join(parent_dir, dir_path) 
        os.makedirs(full_dir_path, exist_ok=True) 
        file_path = os.path.join(full_dir_path, file_name + extentsion)
    else: 
        file_path = os.path.join(parent_dir, path + extentsion)

    if not os.path.exists(file_path):
        path_entry = Path(file_path)
        path_entry.parent.mkdir(parents=True, exist_ok=True)
        path_entry.touch() 

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

    if(stay_cards_list): print(f'______ {len(stay_cards_list)} Wildcards Altered______')
    if(residue_folders_list): print(f'______ {len(residue_folders_list)} Eedundant Folders Cleared______')

def collect_previews_by_channel (channel, wildpath_selector, cards_dir = CARDS_FOLDER):
    collected_previews_list = []
    msg = "no wildcard previews were collected"
    channel_suffix = "."+channel.replace(" ","") if (not channel=="") and (not channel=="default") and channel  else ""
    os.makedirs(COLL_PREV_folder, exist_ok=True) 
    for root, dirs, files in os.walk(cards_dir):
        for file in files:              
                if (file.lower().endswith(f"{channel_suffix}.jpeg") or file.lower().endswith(f"{channel_suffix}.jpg")  or file.lower().endswith(f"{channel_suffix}.png") or file.lower().endswith(f"{channel_suffix}.gif")) and ( channel!="default" or (channel=="default" and file.lower().count(".")==1)):
                    match_found = False
                    for wpath in wildpath_selector :
                        save_file_name= os.path.join(os.path.abspath(cards_dir), wpath.replace("/", os.path.sep))+"."
                        file_path  = os.path.abspath(os.path.join(root, file))
                        if (file_path.lower().startswith(save_file_name.lower())):
                            collected_previews_list.append(file_path)
                            match_found = True
                            break

                    if(match_found):
                        dest_file_path = os.path.join(COLL_PREV_folder, os.path.relpath(collected_previews_list[-1], CARDS_FOLDER))
                        copy_with_directories(src= collected_previews_list[-1], dst= dest_file_path)
                                

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
                if (file.lower().endswith(f"{channel_suffix}.jpeg") or file.lower().endswith(f"{channel_suffix}.jpg")  or file.lower().endswith(f"{channel_suffix}.png") or file.lower().endswith(f"{channel_suffix}.gif")) and ( channel!="default" or (channel=="default" and file.lower().count(".")==1)):
                    match_found = False
                    for wpath in wildpath_selector :
                        save_file_name= os.path.join(os.path.abspath(cards_dir), wpath.replace("/", os.path.sep))+"."
                        file_path  = os.path.abspath(os.path.join(root, file))
                        if (file_path.lower().startswith(save_file_name.lower())):
                            collected_previews_list.append(file_path)
                            match_found = True
                            break

                    if(match_found):
                        print(file.lower().endswith(f"{channel_suffix}.jpeg") or file.lower().endswith(f"{channel_suffix}.jpg")  or file.lower().endswith(f"{channel_suffix}.png")) 
                        print(file.lower().endswith(f"{channel_suffix}.gif") and ( channel!="default" or (channel=="default" and file.lower().count(".")==1)))
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
    
    if wild_paths:
        for root, dirs, files in os.walk(cards_dir):
            # Remove collect imgs
            for file in files:
                    exist_check = False
                    if any(file.lower().endswith(ext) for ext in VALID_IMG_EXT ) :
                        
                        for wpath in wild_paths :
                            save_file_name= os.path.join(os.path.abspath(cards_dir), wpath.replace("/", os.path.sep))+"."
                            file_path  = os.path.abspath(os.path.join(root, file))
                            if (file_path.lower().startswith(save_file_name.lower())):
                                exist_check = True 
                                break
                        
                        if exist_check == False:
                            print(f"[{EXT_NAME}] collecting [{os.path.join(root, file)}]") 
                            new_dir = os.path.join(STRAY_RES_folder, os.path.relpath(os.path.join(root, file),cards_dir).replace(os.path.sep,"+"))
                            
                            try:
                                os.replace(os.path.join(root, file), new_dir)
                                stay_previews_list.append(new_dir)
                            except OSError:
                                print(f"[{EXT_NAME}] failed to collect [{os.path.join(root, file)}]")
    else:
      print(f'______ No wildcards were loaded in______')                      

    if(stay_previews_list):
        print(f'______ {len(stay_previews_list)} stray previews collected in [{STRAY_RES_folder}]______')


def save_tag_config (tag_config_list :list[TagConfig], parent_dir=META_FOLDER, target_file="tags_config.json")->bool:
    file_path = os.path.join(parent_dir,target_file)
    if not os.path.exists(file_path):
        fl_nm, fl_ext= os.path.splitext(target_file)
        file_path = create_dir_and_file(parent_dir, fl_nm, extentsion=".json" )
    
    try:
        with open(file_path, "w") as file:
            json.dump([asdict(cfg) for cfg in tag_config_list], file, indent=4 )
            print(f"updated tag config data")
            return True
    except Exception as e:
        print(f"unable to update tag config data on {file_path}")   
        print(f"Error: {e}")      
    return False

def save_tags (tags_dict:dict[str:list[str]], parent_dir=META_FOLDER, target_file="tags_data.json")->bool:
    file_path = os.path.join(parent_dir,target_file)
    if not os.path.exists(file_path):
        fl_nm, fl_ext= os.path.splitext(target_file)
        file_path = create_dir_and_file(parent_dir, fl_nm, extentsion=".json" )
    
    try:
        with open(file_path, "w") as file:
            json.dump(tags_dict, file, indent=4 )
            print(f"updated tags data")
            return True
    except Exception:
        print(f"unable to update tags data on {file_path}")           
    return False

def load_tags (target_file="tags_data.json")->dict[str:list[str]]:
    result = {}
    file_path = os.path.join(META_FOLDER,target_file)
    if not os.path.exists(file_path):
        with open(file_path, "w") as file:
            json.dump(result, file)
        print(f"tags file created {file_path}")   
    else:
        try:
            with open(file_path, "r") as file:
                result = json.load(file)
        except Exception:
            print(f"unable to read tags data from {file_path}")    
    return result

def merge_tag_dicts(old: dict[str, list[str]], new: dict[str, list[str]]) -> dict[str, list[str]]:
    merged = old.copy()
    for key, new_values in new.items():
        if key in merged:
            merged[key] = list(set(merged[key]) | set(new_values))
        else:
            merged[key] = new_values
    return merged

def unpack_wildcard_pack(pack_path) -> str: 
    zip_cards_sub_path ="cards/" #non-dynamic logic bit
    zip_tags_file ="metadata/tags_data.json" #non-dynamic logic bit
    imported_yaml_name = ""
    
    tags_db_file = os.path.join(META_FOLDER, "tags_data.json")
    traget_dir = os.path.join(WILDCARDS_FOLDER,ADDED_WILDCARDS_FOLDER,"imported")
    
    with zipfile.ZipFile(pack_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            if member.startswith(zip_cards_sub_path) and not member.endswith('/'):
                source = zip_ref.open(member)
                target_path = os.path.join(CARDS_FOLDER, os.path.relpath(member, 'cards/'))
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, 'wb') as f:
                    shutil.copyfileobj(source, f)

            elif member.endswith('.yaml'):
                source = zip_ref.open(member)
                imported_yaml_name, _= os.path.splitext(member)
                target_file = os.path.join(traget_dir,member)
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                with open(target_file, 'wb') as f:
                    shutil.copyfileobj(source, f)

            elif member == zip_tags_file:
                with zip_ref.open(member) as source:
                    new_data = json.load(source)

                if os.path.exists(tags_db_file):
                    with open(tags_db_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                else:
                    existing_data = {}

                merged_data = merge_tag_dicts(existing_data, new_data)

                with open(tags_db_file, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, indent=2)
    
    if imported_yaml_name:
        whitelist  = [item for item in getattr(shared.opts, "wcc_wildcards_whitelist", "").split("\n") if item]
        if imported_yaml_name not in whitelist:
            whitelist.append(imported_yaml_name)
            new_opt = "\n".join(whitelist)
            setattr(shared.opts,"wcc_wildcards_whitelist",new_opt)
            shared.opts.save(shared.config_filename)
            print("Whitelist Settings Updated")


def process_selector(wild_path_selector, wild_paths)-> list[str]:
    selected_wildcards= []
    if wild_path_selector and wild_paths:
        wild_path_selector = wild_path_selector.replace("*","").replace(WILD_STR,"").strip()
        selected_wildcards = [item for item in wild_paths if item.lower().startswith(wild_path_selector.lower())]
    return selected_wildcards

def update_wildcard_yaml(wild_path: str="", prompt: str="", parent_dir=WILDCARDS_FOLDER, file_name: str = SHARED_ASSESTS["custom_yaml"])-> WildcardEntry | None : 
    wild_path = wild_path.strip()
    prompt    = prompt.strip(" , ")

    if  not os.path.isdir(parent_dir) or not ( wild_path or prompt ) or wild_path.endswith('/') :
        print("Wildcard creation canceld due to invalid paramaters")
        return None
    prompt+=", "
    path_parts = wild_path.split('/')
    nested_dict = prompt_to_nested_dict(path_parts, prompt)
    file_path = os.path.normpath(os.path.join(parent_dir,file_name+".yaml"))

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            existing_data = yaml.safe_load(file) or {}
    else:
        file_path = create_dir_and_file(parent_dir, file_name, extentsion=".yaml" )
        existing_data = {}

    # Merge the new nested dictionary into the existing data
    merged_data = merge_dicts(existing_data, nested_dict)

    # Write the updated data back to the YAML file
    with open(file_path, "w") as file:
        yaml.dump(merged_data, file, default_flow_style=False, sort_keys=False, indent=2 )
    return WildcardEntry(name= path_parts[-1], path= wild_path, prompts= prompt)

def prompt_to_nested_dict(path_parts: list, prompt: str):
    """Recursively creates a nested dictionary from path parts."""
    if len(path_parts) == 1:
        return {path_parts[0]: [prompt]}
    return {path_parts[0]: prompt_to_nested_dict(path_parts[1:], prompt)}

def merge_dicts(dict1: dict, dict2: dict):
    """Recursively merges two dictionaries."""
    for key, value in dict2.items():
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(value, dict):
                # Merge nested dictionaries
                merge_dicts(dict1[key], value)
            elif isinstance(dict1[key], list) and isinstance(value, list):
                # Add new items to the existing list, avoiding duplicates
                dict1[key].extend(x for x in value if x not in dict1[key])
            else:
                # If the types are different, prefer the value from dict2
                dict1[key] = value
        else:
            dict1[key] = value
    return dict1

def zip_folder(folder_path: str, zip_name : str, extension =".zip", post_delete = False):
    folder = Path(folder_path)
    with zipfile.ZipFile(zip_name + extension, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in folder.rglob('*'): 
            zipf.write(file, file.relative_to(folder)) 

    if post_delete:
        shutil.rmtree(folder_path)
    

def export_cards_pack(selected_cards: list[WildcardEntry], save_name:str = "", save_dir:str = COLL_PREV_folder, img_channels:list[str]= IMG_CHANNELS, exclude_Masked_Tags = False, config_dict = {}):
    save_name = save_name if save_name else f"wildpack_{int(time.time())}"
    save_dir = os.path.join(save_dir, save_name)
    exp_tags_path = os.path.join(save_dir, "metadata")
    exp_img_path = os.path.join(save_dir, "cards")
    exp_tag_dict = {}
    export_status = bool(selected_cards)
    
    for entry in selected_cards:
        for tag in entry.tags:
            if not (exclude_Masked_Tags and config_dict and config_dict.get(tag) and config_dict.get(tag).masked): 
                exp_tag_dict[tag] = exp_tag_dict.get(tag,[]) + [entry.path]
        entry.collect_channel_img(dest_dir=exp_img_path, channels= img_channels)
        export_status= export_status and update_wildcard_yaml(file_name= save_name, parent_dir= save_dir,  prompt= entry.prompts, wild_path=entry.path)
    
    
    export_status= export_status and save_tags(parent_dir=exp_tags_path, tags_dict= exp_tag_dict)
    if export_status:
        zip_folder(save_dir, save_dir, post_delete= True)
        print(f"Exported {len(selected_cards)} cards and {len(exp_tag_dict)} tags to [{save_dir}.zip]")
    return export_status


def wildpack_info_scan(wildpack_file_path):
    cards_sub_path ="cards/"
    tags_sub_file ="metadata/tags_data.json" 
    yaml_nodes = []
    thumbnails_imgs = []
    got_tags = False
    if (os.path.exists(wildpack_file_path)):
        with zipfile.ZipFile(wildpack_file_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.startswith(cards_sub_path):
                    for ext in VALID_IMG_EXT:
                        if member.endswith(ext):
                            thumbnails_imgs.append(member)
                            break
                elif member == tags_sub_file:
                    got_tags = True
                elif member.endswith('.yaml'):
                    with zip_ref.open(member) as targe_file:
                        decoded_io = io.TextIOWrapper(targe_file, encoding='utf-8')
                        yaml_nodes = get_yaml_nodes(yaml_file_path= decoded_io, deep_scan=True)
        
    return yaml_nodes, thumbnails_imgs, got_tags
        
def html_simple_list(items:list):
    list_wraper = "<ul>"  
    for item in items:
        list_wraper +=f"<li> {item} </li>"
    return list_wraper+ "</ul>" 

def strip_trailing_number(s):
    return re.sub(r'\d+$', '', s)

from modules.ui_extra_networks import ExtraNetworksPage, quote_js, register_page
from modules import shared, script_callbacks
import modules.scripts as scripts 

from scripts.misc_utils import (
    collect_Wildcards,clean_residue,
    create_dir_and_file,fetch_img, get_safe_name_2, get_base_url,
    WILDCARDS_FOLDER, CARDS_FOLDER, RES_FOLDER, WILD_STR,IMG_CHANNELS,EXT_NAME,
    WildcardEntry, load_tags, link_img, strip_trailing_number
    
)
from scripts.wg_filter_tab import on_ui_tabs, init_filter_module
from scripts.preview_processing import   txt2img_prompting_process, txt2img_preview_process, normal_process
import shutil
import os
import gradio as gr
from fastapi import FastAPI 


wildcards_dict:dict[str,WildcardEntry]  = {}
filter_interr_fn = None

extra_network_name = "Wildcards" 
log_suffix = "[LOG] "
error_suffix = "[ERR] "
FILTER_EXTRACT_OPTS =["all filter results","selected cards only"]
PROMPTER_OPTS       =["combine cards","each card"]
SCRIPT_MODES_OPTS   =["disabled", "batch prompting", "preview generation", "sequance generation"]




class WildcardsCards(ExtraNetworksPage):

    def __init__(self):
        super().__init__(extra_network_name)
        self.allow_negative_prompt = True
        self.cards: list[str] = None
        self.refresh()

    def refresh(self, shallow_refresh = True): 
        global wildcards_dict
        global filter_interr_fn
        if not shallow_refresh:
            wildcards_dict, tags_dict = build_gallery_dict()
            filter_interr_fn = init_filter_module(wildcards_dict, tags_dict) 
            clean_residue(CARDS_FOLDER, list(wildcards_dict.keys()))

        self.cards = wildcards_dict
 


    def create_item(self, wild_path:str, index:int=1, tags:list[str] =[], raw_prompt:str="", thumbnail:str = "", mtime=1, enable_filter:bool=True):
        filePath = os.path.abspath(create_dir_and_file(CARDS_FOLDER, wild_path))
        path, ext = os.path.splitext(filePath)
        prompt = f"{WILD_STR}{wild_path}{WILD_STR}"


        #suffix = getattr(shared.opts, "wcc_preview_channel", "default").replace("default","preview").strip()

        #"preview"       : self.find_preview(path+"."+suffix) if self.find_preview(path+"."+suffix) else self.find_preview(path),
        #"local_preview" : f"{path}.{suffix}.{shared.opts.samples_format}",


        name , category = get_safe_name_2(wild_path, self.cards)

        metadata = {
            "activation text": prompt,
            "notes":f"prompts: {raw_prompt}"
        }
        return {
            "name": name,
            "filename": filePath,
            "shorthash": f"{hash(filePath)}",
            "preview"       : link_img(thumbnail, mtime),
            "local_preview" : thumbnail,
            "description": self.find_description(path),
            "search_terms": [self.search_terms_from_path(filePath)],
            "prompt": quote_js(prompt),
            "user_metadata": metadata,
            "sort_keys": {
                "default": f"{category.lower()}-{name.lower()}",
                "date_created": index,
                "date_modified": f"{category.lower()}-{index}",
                "name": name.lower(),
            },
        }

    def list_items(self): 
        channel = getattr(shared.opts, "wcc_preview_channel", "default").strip()
        for index, (wpath, wentry) in enumerate(self.cards.items()):
            if not wentry.is_preloaded:
                wentry.preload_previews()
            preview_file = wentry.thumbnails.get(channel, "")
            yield self.create_item(wpath, index, tags= wentry.tags, raw_prompt= wentry.prompts , thumbnail = preview_file, mtime=wentry.last_update)
 

    def allowed_directories_for_previews(self): #might not be be needed anymore
        return [CARDS_FOLDER]

#-------------------------|Settings_page Block_Start|--------------------------
def on_ui_settings():
    section = "WildcardsGallery", "Wildcards Gallery"
    shared.opts.add_option(
        key="wcc_wildcards_directory",
        info=shared.OptionInfo(
            WILDCARDS_FOLDER,
            "Wildcard Directory",
            gr.Textbox,
            lambda: {"interactive": True, "show_label" : True},
            section=section,
        ),
    )

    shared.opts.add_option(
        key="wcc_wildcards_whitelist",
        info=shared.OptionInfo(
            "\n".join(getattr(shared.opts, "wcc_wildcards_whitelist","").split("\n")),
            "Whitelisted Wildcards",
            gr.Code,
            lambda: {"interactive": True, "show_label" : True},
            section=section,
        ),
    )

    shared.opts.add_option(
        key="wcc_wildcards_blacklist",
        info=shared.OptionInfo(
            "\n".join(getattr(shared.opts, "wcc_wildcards_blacklist","").split("\n")),
            "Blacklistd Wildcards",
            gr.Code,
            lambda: {"interactive": True, "show_label" : True},
            section=section,
        ),
    )

    shared.opts.add_option(
        key="wcc_preview_channel", 
        info=shared.OptionInfo(
            getattr(shared.opts, "wcc_preview_channel", "default"),
            "Main preview channel", 
            gr.Dropdown,
            lambda: {"choices": IMG_CHANNELS}, 
            section=section)
        )
    
    shared.opts.add_option(
        key="wcc_downscale_preview",
        info=shared.OptionInfo(
            getattr(shared.opts, "wcc_downscale_preview", False), 
            "Downscale preview images",
            gr.Checkbox,
            lambda: {"interactive": True, "show_label" : True},
            section=section,
        ),
    )
    


#-------------------------|Settings_page Block_End|----------------------------


#-------------------------|Utility_Script Block_Start|--------------------------

def btn_count_wildcards (filter_extact_mode):
    msg = f"{log_suffix}: No wildcards selected"
    sel_only  = filter_extact_mode == FILTER_EXTRACT_OPTS[1]
    selected_wildcards_list = filter_interr_fn(sel_only)
    if(selected_wildcards_list):
        msg = f"{log_suffix}: { len(selected_wildcards_list) } wildcards selected"
    
    return (gr.update(value= msg))

def toggle_search_replace_box (insertion_type):
    return (gr.update(visible= insertion_type == "SREACH & REPLACE" , value="@GG"))

def toggle_wildpath_box (toggle_status):
    return (gr.update(visible= toggle_status))

def selection_sequance(use_wild_path, selected_wildcard, selected_wild_path):
    selected_wildcard_final_list = []
    if((selected_wild_path and not selected_wild_path=="") or (not use_wild_path and selected_wildcard)):
        wild_paths = list(wildcards_dict.keys())
        selected_wild_path = selected_wild_path.replace("*","").replace(WILD_STR,"").strip()

        selected_wildcard_final_list = [item for item in wild_paths if (item.lower().startswith(selected_wild_path.lower()) and use_wild_path) or (item in selected_wildcard if selected_wildcard else False)   ]
    return selected_wildcard_final_list

def change_scrip_mode(mode):
    print(f">> Set generation script mode to: {mode}")
    if mode not in SCRIPT_MODES_OPTS or mode == SCRIPT_MODES_OPTS[0] :
        return(
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False)
              )
    if mode == SCRIPT_MODES_OPTS[1]:
        return(
            gr.update(visible= True),
            gr.update(visible= True),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= True),
            gr.update(visible= True),
            gr.update()  )
    if mode == SCRIPT_MODES_OPTS[2]:
        return(
            gr.update(visible= True),
            gr.update(visible= False),
            gr.update(visible= True),
            gr.update(visible= True),
            gr.update(visible= True),
            gr.update(visible= True),
            gr.update()  )
    if mode == SCRIPT_MODES_OPTS[3]:
        return(
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= True),
            gr.update(visible= True),
            gr.update()  ) 
       
def act_lunch_gen (filter_extact_mode):
    sel_only  = filter_extact_mode == FILTER_EXTRACT_OPTS[1]
    selected_wildcards_list = filter_interr_fn(sel_only)
    gr.Info(f"Processing Tumbnails for {len(selected_wildcards_list)} Cards")

class Script(scripts.Script):
    is_txt2img = False

    # Function to set title
    def title(self):
        return "Wildcards preview utils"

    def ui(self, is_img2img):
        with gr.Column():
            with gr.Row():
                script_mode     = gr.Radio (label ="Script Mode", choices= SCRIPT_MODES_OPTS, value=SCRIPT_MODES_OPTS[0], elem_classes=["wcc_flat_radio","wcc_radio_header"])
            with gr.Row(): 
                filter_extact_mode  = gr.Radio (visible=False, label ="Included Wildcards", choices= FILTER_EXTRACT_OPTS, value=FILTER_EXTRACT_OPTS[1], elem_classes=["wcc_flat_radio","wcc_radio_header"]) 
                prompting_mode      = gr.Radio (visible=False, label ="Prompt usage mode",  choices= PROMPTER_OPTS, value=PROMPTER_OPTS[1], elem_classes=["wcc_flat_radio","wcc_radio_header"])
                
            
            preview_suffix = gr.Dropdown (
                        visible=False, 
                        choices = IMG_CHANNELS,
                        label="preview channel",
                        value= getattr(shared.opts, "wcc_preview_channel", "default"), 
                        interactive = True , 
                        info="generate the preview for the selected channel", 
                        multiselect=True )
            with gr.Row():
                insertion_type =  gr.Dropdown (
                                choices = ["AFTER", "BEFORE", "SREACH & REPLACE"],
                                label="wildcard insertion method",
                                value= "AFTER", 
                                interactive = True , 
                                visible= False, 
                                info="how and where to insert the wildcard within the prompt" )
                replace_str_opt = gr.Textbox(label="S/R text" , interactive = True , info="searches and replace the provided text by the wildcard in the prompt", visible= False, value="@GG" )

            with gr.Column():
                
                with gr.Row():
                    task_override   = gr.Checkbox(visible=False, label ="override exisiting previews"  ,value = False) 
                
                with gr.Row():
                    btn_run_gen     = gr.Button (visible=False, value="Generate", variant="primary", elem_classes="wcc_compos_btn_left")
                    act_count   = gr.Button(value = "count selected cards",  elem_classes="wcc_compos_btn_mid" )
                    act_msg     = gr.Markdown(value = log_suffix+": _",  elem_id="wld_gal_notif_area" )
 


        gen_click_js = '''
                    ()=>{
                        currentTab = gradioApp().querySelector('#tabs > .tabitem[id^=tab_]:not([style*="display: none"])');
                        gen_btn = currentTab.querySelector('button[id$=_generate]');
                        if (gen_btn) {gen_btn.click()}
                        else{ print("cant connect to gen button")}
                    }
                '''

        script_mode.change      (change_scrip_mode, inputs=script_mode, outputs= [filter_extact_mode, prompting_mode, task_override, preview_suffix, insertion_type, btn_run_gen, replace_str_opt])
        insertion_type.change   (toggle_search_replace_box, inputs=insertion_type, outputs= replace_str_opt )
        act_count.click         (btn_count_wildcards,   inputs= [filter_extact_mode], outputs=act_msg)  
        btn_run_gen.click       (act_lunch_gen,   inputs= [filter_extact_mode]).then(None, _js=gen_click_js)
         
        
        
        return [filter_extact_mode, task_override ,replace_str_opt, preview_suffix, insertion_type, script_mode, prompting_mode]
    
    # Function to show the script
    def show(self, is_img2img):
        return not is_img2img

    # Function to run the script
    def run(self, p,filter_extact_mode , task_override,  replace_str_opt, preview_suffix, insertion_type, script_mode, prompting_mode):
        global wildcards_dict

        selected_wild_paths = filter_interr_fn(filter_extact_mode == FILTER_EXTRACT_OPTS[1] or SCRIPT_MODES_OPTS[3]) if callable(filter_interr_fn) else []
        preview_suffix      = preview_suffix if preview_suffix else [IMG_CHANNELS[0]]
        
        if script_mode==SCRIPT_MODES_OPTS[0]:
            processed_req = normal_process(p)
        
        elif script_mode==SCRIPT_MODES_OPTS[1] and (selected_wild_paths):
            processed_req = txt2img_prompting_process(p,selected_wild_paths ,replace_str_opt ,  insertion_type, prompting_mode) 

        
        elif script_mode==SCRIPT_MODES_OPTS[2] and (selected_wild_paths):
            processed_req, update_stack = txt2img_preview_process(p,selected_wild_paths ,replace_str_opt , task_override ,preview_suffix, insertion_type, view_mode= False)
            for wpath, channel_dict in update_stack.items():
                entry = wildcards_dict.get(wpath)
                if entry:
                    entry.update_thumbnails(channel_dict)

        
        elif script_mode==SCRIPT_MODES_OPTS[3] and (selected_wild_paths):
            new_selected_wild_paths = []
            for wildpath in selected_wild_paths:
                counter = 1
                potential_sequence = f"{strip_trailing_number(wildpath)}{counter}"
                while potential_sequence in  wildcards_dict :
                    new_selected_wild_paths.append(potential_sequence)
                    print(f"**  {potential_sequence}")
                    counter +=1
                    potential_sequence = f"{strip_trailing_number(wildpath)}{counter}"
            
            processed_req, update_stack = txt2img_preview_process(p,new_selected_wild_paths ,replace_str_opt , task_override ,preview_suffix, insertion_type, view_mode= True)

        
        else:
            gr.Error("Lacking selection or parameters", duration = 3, visible= True)
            print("___Preview generation halted___")
            processed_req = txt2img_prompting_process (p,selected_wild_paths)
        
        return processed_req

def on_app_started(_, app:FastAPI):
    app.add_api_route("/wcc_cards/img", fetch_img, methods=["GET"])
    app.add_api_route("/wcc_cards/base_url", get_base_url, methods=["GET"])



def build_gallery_dict(perload_thumbnails:bool = False)->tuple[dict[str,WildcardEntry], dict[str,list[str]]]:

    if not os.path.exists(CARDS_FOLDER):
        print(f'\n[{EXT_NAME}] "cards" folder not found. Reinitializing...\n')
        os.makedirs(CARDS_FOLDER, exist_ok=True) 

    wildcards_dict = collect_Wildcards( collect_prompts =True)
    tags_dict = load_tags()
    

    for wild_path, wildcard in wildcards_dict.items():
        if wild_path:
            tags = []
            for tag, paths in tags_dict.items():
                if wild_path in paths:
                    tags.append(tag)
            wildcard.tags = tags
            wildcard.is_preloaded = perload_thumbnails
            if perload_thumbnails: wildcard.preload_previews()
    
    print(f"___Gallery dictionary built with [{len(wildcards_dict)} wildcards]___")
    return wildcards_dict, tags_dict


def pre_ui_init():
    global wildcards_dict
    global filter_interr_fn
    print(f"___{EXT_NAME} Initializing. . . ")
    wildcards_dict, tags_dict = build_gallery_dict()
    wcc_extra_net_page  = WildcardsCards()
    filter_interr_fn =  init_filter_module(wildcards_dict, tags_dict, rebuild_fn= wcc_extra_net_page.refresh)
    register_page(wcc_extra_net_page)
    print(f"___{EXT_NAME} Initialized___")
    



 


#-------------------------|Utility_Script Block_End|----------------------------

script_callbacks.on_app_started(on_app_started)
script_callbacks.on_before_ui(pre_ui_init)
script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_ui_tabs(on_ui_tabs)
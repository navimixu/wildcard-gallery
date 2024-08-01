from modules.ui_extra_networks import ExtraNetworksPage, quote_js, register_page
from modules import shared, script_callbacks
import modules.scripts as scripts 

from scripts.misc_utils import (
    collect_Wildcards,
    create_dir_and_file,
    clean_residue,
    get_safe_name_2,
    collect_stray_previews, collect_previews_by_channel, delete_previews_by_channel, 
    WILDCARDS_FOLDER,
    CARDS_FOLDER,
    RES_FOLDER,
    WILD_STR,
)
from scripts.preview_processing import (
    txt2img_process, set_preview_as_null
)
import shutil
import os
import gradio as gr

addon_name = "Wildcards Gallery"
extra_network_name = "Wildcards"
preview_channels = ["default", "preview", "preview 1", "preview 2", "preview 3"]
log_suffix = "[LOG] "
error_suffix = "[ERR] "

def setting_action_clean_residue():
    wild_paths = collect_Wildcards(WILDCARDS_FOLDER)
    clean_residue(CARDS_FOLDER, wild_paths)
    print("[task complete]---clean_residue---")

def setting_action_collect_stray_prv():
    wild_paths = collect_Wildcards(WILDCARDS_FOLDER)
    collect_stray_previews(wild_paths)
    print("[task complete]---collect stray previews---")

class WildcardsCards(ExtraNetworksPage):

    def __init__(self):
        super().__init__(extra_network_name)
        self.allow_negative_prompt = True
        self.cards: list[str] = None

        if not os.path.exists(CARDS_FOLDER):
            print(f'\n[{addon_name}] "cards" folder not found. Initializing...\n')
            shutil.copytree(RES_FOLDER, CARDS_FOLDER)

        self.refresh()

    def refresh(self):
        self.cards = []
        wild_paths = collect_Wildcards(WILDCARDS_FOLDER)
        self.cards = wild_paths
        clean_residue(CARDS_FOLDER, wild_paths)


    def create_item(self, wild_path: str, index=1, enable_filter=True):
        filePath = os.path.abspath(create_dir_and_file(CARDS_FOLDER, wild_path))
        path, ext = os.path.splitext(filePath)
        prompt = f"__{wild_path}__"
        suffix = getattr(shared.opts, "wcc_preview_channel", "default").replace("default","preview").replace(" ","")

        #if "/" in wild_path:
        #    category, name = wild_path.rsplit("/", 1)
        #else:
        #    category, name = '', wild_path

        name , category = get_safe_name_2(wild_path, self.cards)

        return {
            "name": name,
            "filename": filePath,
            "shorthash": f"{hash(filePath)}",
            "preview": self.find_preview(path+"."+suffix) if self.find_preview(path+"."+suffix) else self.find_preview(path),
            "description": self.find_description(path),
            "search_terms": [self.search_terms_from_path(filePath)],
            "prompt": quote_js(prompt),
            "local_preview": f"{path}.{suffix}.{shared.opts.samples_format}",
            "sort_keys": {
                "default": f"{category.lower()}-{name.lower()}",
                "date_created": index,
                "date_modified": f"{category.lower()}-{index}",
                "name": name.lower(),
            },
        }

    def list_items(self):
        i = 0

        for FILE in self.cards:
            i += 1
            yield self.create_item(FILE, i)

    def allowed_directories_for_previews(self):
        return [CARDS_FOLDER]

#-------------------------|Settings_page Block_Start|--------------------------
def on_ui_settings():
    section = "WildcardsGallery", "Wildcards Gallery"
    shared.opts.add_option(
        key="wcc_wildcards_directory",
        info=shared.OptionInfo(
            "\n".join(WILDCARDS_FOLDER),
            "Wildcard Directories",
            gr.Code,
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
        key="wcc_downscale_preview",
        info=shared.OptionInfo(
            getattr(shared.opts, "wcc_downscale_preview", False), 
            "Downscale preview images",
            gr.Checkbox,
            lambda: {"interactive": True, "show_label" : True},
            section=section,
        ),
    )
    
    shared.opts.add_option(
        key="wcc_preview_channel", 
        info=shared.OptionInfo(
            getattr(shared.opts, "wcc_preview_channel", "default"),
            "Switch preview images", 
            gr.Dropdown,
            lambda: {"choices": preview_channels}, 
            section=section)
        )
    
    shared.opts.add_option(
        key="wcc_action_clean_residue", 
        info=shared.OptionInfo(
            "Clean residue cards and folders", 
            "testing actions2", 
            gr.HTML,
            {}, 
            refresh=setting_action_clean_residue, 
            section=section)
        )

    shared.opts.add_option(
        key="wcc_action_collect_stary", 
        info=shared.OptionInfo(
            "Collect stray preview files", 
            "testing actions", 
            gr.HTML,
            {}, 
            refresh=setting_action_collect_stray_prv, 
            section=section)
        )
#-------------------------|Settings_page Block_End|----------------------------


#-------------------------|Utility_Script Block_Start|--------------------------

def btn_count_wildcards (use_wild_path, selected_wildcard, selected_wild_path):
    msg = error_suffix+"No wildcards selected"
    selected_wildcards_list  = selection_sequance (use_wild_path, selected_wildcard, selected_wild_path)
    if(selected_wildcards_list):
        msg = f"Prameters are selecting { len(selected_wildcards_list) } wildcards"
    
    return (gr.update(value= log_suffix + msg))

def btn_collect_previews (preview_suffix, use_wild_path, selected_wildcard, selected_wild_path):
    msg = error_suffix+"No wildcards selected"
    selected_wildcards_list  = selection_sequance (use_wild_path, selected_wildcard, selected_wild_path)
    
    if(selected_wildcards_list):
        msg=""
        for channel_item in preview_suffix:
            msg = msg + collect_previews_by_channel(channel=channel_item,  wildpath_selector= selected_wildcards_list) +"\n"
    
    return (gr.update(value= log_suffix+msg))

def btn_delete_previews (preview_suffix, use_wild_path, selected_wildcard, selected_wild_path):
    msg = error_suffix+"No wildcards selected"
    selected_wildcards_list  = selection_sequance (use_wild_path, selected_wildcard, selected_wild_path)
    
    if(selected_wildcards_list):
        msg=""
        for channel_item in preview_suffix:
            msg =  log_suffix + delete_previews_by_channel(channel=channel_item,  wildpath_selector= selected_wildcards_list)+"\n"+ msg 
    return (gr.update(value= msg))

def toggle_search_replace_box (insertion_type):
    return (gr.update(visible= insertion_type == "SREACH & REPLACE"))

def toggle_wildpath_box (toggle_status):
    return (gr.update(visible= toggle_status))

def selection_sequance(use_wild_path, selected_wildcard, selected_wild_path):
    selected_wildcard_final_list = []
    if((selected_wild_path and not selected_wild_path=="") or (not use_wild_path and selected_wildcard)):
        wild_paths = collect_Wildcards(WILDCARDS_FOLDER)
        selected_wild_path = selected_wild_path.replace("*","").replace(WILD_STR,"").strip()

        selected_wildcard_final_list = [item for item in wild_paths if (item.lower().startswith(selected_wild_path.lower()) and use_wild_path) or (item in selected_wildcard if selected_wildcard else False)   ]
    return selected_wildcard_final_list

class Script(scripts.Script):
    is_txt2img = False

    # Function to set title
    def title(self):
        return "Wildcards preview utils"

    def ui(self, is_img2img):
        with gr.Column():
            use_wild_path       = gr.Checkbox (label ="use wildcard branch selector",value = False)
            selected_wild_path  = gr.Textbox (label   ="wildcard parent branch" , interactive = True , info="specify the wildcard or a wildcard root to process" , visible= False)
            with gr.Row():
                selected_wildcard = gr.Dropdown(label ="wildcards" , interactive = True , choices= collect_Wildcards(WILDCARDS_FOLDER), multiselect=True)
            
            with gr.Row():
                insertion_type =  gr.Dropdown (
                                choices = ["AFTER", "BEFORE", "SREACH & REPLACE"],
                                label="wildcard insertion method",
                                value= "AFTER", 
                                interactive = True , 
                                info="how and where to insert the wildcard within the prompt" )
                replace_str_opt = gr.Textbox(label="S/R text" , interactive = True , info="searches and replace the provided text by the wildcard in the prompt", visible= False )

            with gr.Accordion(open=False, label="Extra options"):
                with gr.Column():
                    preview_suffix = gr.Dropdown (
                                choices = preview_channels,
                                label="preview channel",
                                value= getattr(shared.opts, "wcc_preview_channel", "default"), 
                                interactive = True , 
                                info="generate the preview for the selected channel", 
                                multiselect=True )
                    task_override       = gr.Checkbox(label ="override exisiting previews"  ,value = False)
                    task_nullify        = gr.Checkbox (label ="return as null previwes"     ,value = False)

            with gr.Accordion(open=False, label="Actions"):
                    with gr.Column():
                        act_msg     = gr.Markdown(value = log_suffix+" ",  elem_id="wld_gal_notif_area" )
                        with gr.Row():
                            act_count   = gr.Button(value = "count selected cards")
                            act_collect = gr.Button(value = "collect previews")
                        act_delete = gr.Button(value = "delete previews in channel", elem_classes= "wld_gal_ngbutton")

        use_wild_path.change(fn=toggle_wildpath_box , inputs=use_wild_path, outputs= selected_wild_path)
        insertion_type.change(fn= toggle_search_replace_box, inputs=insertion_type, outputs= replace_str_opt )
        act_collect.click(btn_collect_previews, inputs= [preview_suffix, use_wild_path, selected_wildcard, selected_wild_path], outputs=act_msg)
        act_count.click(btn_count_wildcards,   inputs= [use_wild_path, selected_wildcard, selected_wild_path], outputs=act_msg)
        act_delete.click(btn_delete_previews, inputs= [preview_suffix, use_wild_path, selected_wildcard, selected_wild_path], outputs=act_msg)
        
        
        return [selected_wild_path , task_override ,replace_str_opt, preview_suffix, selected_wildcard, use_wild_path, task_nullify, insertion_type]
    
    
    
    # Function to show the script
    def show(self, is_img2img):
        return not is_img2img

    # Function to run the script
    def run(self, p,selected_wild_path , task_override,  replace_str_opt, preview_suffix, selected_wildcard, use_wild_path, task_nullify, insertion_type):
        # Make a process_images Object
        selected_wild_paths = selection_sequance (use_wild_path, selected_wildcard, selected_wild_path)
        if not preview_suffix : preview_suffix = ["default"]
        if(selected_wild_paths):
            if(task_nullify):
                for channel_item in preview_suffix:
                    set_preview_as_null(selected_wild_paths, task_override ,channel_item)
                return txt2img_process(p,[] ,replace_str_opt , task_override ,preview_suffix, insertion_type)
            else:
                return txt2img_process(p,selected_wild_paths ,replace_str_opt , task_override ,preview_suffix, insertion_type)
        else:
            print("___Skipping Wildcard preview generation [wildcard not found or invalid parameters]___")
            return txt2img_process(p,[] ,replace_str_opt , task_override ,preview_suffix, insertion_type)

#-------------------------|Utility_Script Block_End|----------------------------


script_callbacks.on_before_ui(lambda: register_page(WildcardsCards()))
script_callbacks.on_ui_settings(on_ui_settings)
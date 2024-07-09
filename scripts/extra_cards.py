from modules.ui_extra_networks import ExtraNetworksPage, quote_js, register_page
from modules import shared, script_callbacks
import modules.scripts as scripts

from scripts.misc_utils import (
    collect_Wildcards,
    create_dir_and_file,
    clean_residue,
    get_safe_name_2,
    collect_stray_previews,
    WILDCARDS_FOLDER,
    CARDS_FOLDER,
    RES_FOLDER,
    WILD_STR,
)
from scripts.preview_processing import (
    txt2img_process
)
import shutil
import os
import gradio as gr

addon_name = "Wildcards Gallery"
extra_network_name = "Wildcards"
preview_channels = ["default", "preview", "preview 1", "preview 2", "preview 3"]

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
class Script(scripts.Script):
    is_txt2img = False

    # Function to set title
    def title(self):
        return "Wildcards preview utils"

    def ui(self, is_img2img):
        with gr.Column():
            selected_wild_path = gr.Textbox(label="wildcard" , interactive = True , info="specify the wildcard or wildcard branch to process" )
            extra_Info          = gr.Markdown( value = "the entred wildcard will include its children if it has any" )
            task_override = gr.Checkbox(label="override exisiting previews",value = False,info ="override exisiting previews")
            with gr.Accordion(open=False, label="Extra options"):
                with gr.Column():
                    replace_str_opt = gr.Textbox(label="insert by replacing" , interactive = True , info="insert by replacing a text passage" )
                    preview_suffix = gr.Dropdown (
                            choices = preview_channels,
                            label="preview channel",
                            value= getattr(shared.opts, "wcc_preview_channel", "default"), 
                            interactive = True , 
                            info="adds the preview to the chosen preview_channel" )


        
        return [selected_wild_path ,extra_Info ,task_override ,replace_str_opt, preview_suffix]

    # Function to show the script
    def show(self, is_img2img):
        return not is_img2img

    # Function to run the script
    def run(self, p,selected_wild_path ,extra_Info, task_override,  replace_str_opt, preview_suffix):
        # Make a process_images Object
        if(selected_wild_path and not selected_wild_path==""):
            wild_paths = collect_Wildcards(WILDCARDS_FOLDER)
            selected_wild_paths = [item for item in wild_paths if item.lower().startswith(selected_wild_path.lower())]
            if(selected_wild_paths):
                return txt2img_process(p,selected_wild_paths ,replace_str_opt , task_override ,preview_suffix)
            else:
                print("___Skipping Wildcard preview generation [wildcard empty or not found]___")
        else:
            print("___Skipping Wildcard preview generation [lack of perameters]___")
#-------------------------|Utility_Script Block_End|----------------------------


script_callbacks.on_before_ui(lambda: register_page(WildcardsCards()))
script_callbacks.on_ui_settings(on_ui_settings)
import gradio as gr
import math 
from scripts.misc_utils import  (   load_tags, save_tags, save_tag_config, process_selector,WildcardEntry, TagConfig,update_wildcard_yaml,create_dir_and_file, unpack_wildcard_pack,
                                    collect_stray_previews, export_cards_pack, wildpack_info_scan, html_simple_list,
                                    link_img, IMG_CHANNELS,  WILD_STR, CARDS_FOLDER, EXT_NAME, ICON_LIB)


 

TAB_NAME = "Wildcards Filter"
EXT_HANDEL = "wcc"
ITEMS_CAP = 25
rebuild_callback = None
wildcards_dict:dict[str,WildcardEntry]  = {}
tags_dict:dict[str,list[str]]           = {}
tag_config_dict:dict[str,TagConfig]     = {}
tag_config_groups:dict[str,TagConfig]     = {}
filter_modes = ["wildcard","selector text","tags", "prompt search"]
filter_logic = ["AND","OR"]

selection_modes = ["Selected Only", "All filtered Results"]
import_modes = ["Standalone File", "Merge"]


filtered_stacks:dict[str,list[WildcardEntry]]  = {}
filtered_pile:list[WildcardEntry]       = []
selected_entries:list[WildcardEntry]    = []
selected_stack_paths:list[str]          = []
last_edit:WildcardEntry = None

multi_selection_mode = True 
card_edit_mode = False 
hidden_tag_groups = []

current_img_channel = IMG_CHANNELS[0]
current_stack_level = 0
current_page:int = 1


def interrogate_filter(only_selected=True):
    return  [entry.path for entry in selected_entries] if only_selected else [entry.path for entry in filtered_pile]

def build_tag_config_dict(tag_config_list:list[TagConfig]):
    for config in tag_config_list:
        tag_config_groups[config.config_name] = config
        for tag in config.members:
            tag_data = tags_dict.get(tag)
            if tag_data:
                tag_config_dict[tag] = config
                for wild_path in tag_data:
                    wdata = wildcards_dict.get(wild_path)
                    if wdata: wdata.aux_prompt=config.added_prompt

def init_filter_module(built_wildcards_dict:dict[str,WildcardEntry], built_tags_dict:dict[str,list[str]], rebuild_fn=None):
    global wildcards_dict
    global tags_dict
    global tag_config_dict
    global tag_config_groups
    global rebuild_callback
    rebuild_callback = rebuild_fn if callable(rebuild_fn) else rebuild_callback
    
    wildcards_dict = built_wildcards_dict
    tags_dict   = built_tags_dict

    tag_config_list = TagConfig.load_from_json()
    build_tag_config_dict(tag_config_list)

    return interrogate_filter
    



#---------------------------------|Renderers|---------------------------------
def details_pannel_html (selected_card:WildcardEntry):
    main_html_block = r'<div >###</div>'
    detail_block = f'<div class="wcc_card_detail" ><label class="wcc_detail_header" >##hr##:</label> <label class="wcc_detail_text">##tx##</label></div>'
    generated_html = detail_block.replace("##hr##","Card Path").replace("##tx##",selected_card.path)
    generated_html += detail_block.replace("##hr##","Prompt").replace("##tx##",f"{selected_card.prompts}")
    generated_html += detail_block.replace("##hr##","File").replace("##tx##",f"{selected_card.file_origin}")
    generated_html += detail_block.replace("##hr##","Protected").replace("##tx##",f"{selected_card.is_locked}")
    
    generated_html += detail_block.replace("##hr##","Channels").replace("##tx##",  html_simple_list(selected_card.get_preview_channels())  )
    generated_html  =  selected_card.html_tag_stack(tag_config_dict) + generated_html
    return main_html_block.replace("###",generated_html) 

def toast_notif(msg="", is_err=False):
    added_class = "wcc_notif_err" if is_err else ""
    return f'<div id="wcc_notif_msg" class="{added_class}" > {msg} </div>'

def creation_pannel_html (is_done=False, is_error=False):

    main_html_block = r'<div id="wcc_stack_preview"><div id="wcc_stack_label"> Wildcard Creation </div> <div class="wcc_cards_stack">###</div></div>'
    icon_svg = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
    <path d="M16.19 2H7.81C4.17 2 2 4.17 2 7.81V16.18C2 19.83 4.17 22 7.81 22H16.18C19.82 22 21.99 19.83 21.99 16.19V7.81C22 4.17 19.83 2 16.19 2ZM10.95 17.51C10.66 17.8 10.11 18.08 9.71 18.14L7.25 18.49C7.16 18.5 7.07 18.51 6.98 18.51C6.57 18.51 6.19 18.37 5.92 18.1C5.59 17.77 5.45 17.29 5.53 16.76L5.88 14.3C5.94 13.89 6.21 13.35 6.51 13.06L10.97 8.6C11.05 8.81 11.13 9.02 11.24 9.26C11.34 9.47 11.45 9.69 11.57 9.89C11.67 10.06 11.78 10.22 11.87 10.34C11.98 10.51 12.11 10.67 12.19 10.76C12.24 10.83 12.28 10.88 12.3 10.9C12.55 11.2 12.84 11.48 13.09 11.69C13.16 11.76 13.2 11.8 13.22 11.81C13.37 11.93 13.52 12.05 13.65 12.14C13.81 12.26 13.97 12.37 14.14 12.46C14.34 12.58 14.56 12.69 14.78 12.8C15.01 12.9 15.22 12.99 15.43 13.06L10.95 17.51ZM17.37 11.09L16.45 12.02C16.39 12.08 16.31 12.11 16.23 12.11C16.2 12.11 16.16 12.11 16.14 12.1C14.11 11.52 12.49 9.9 11.91 7.87C11.88 7.76 11.91 7.64 11.99 7.57L12.92 6.64C14.44 5.12 15.89 5.15 17.38 6.64C18.14 7.4 18.51 8.13 18.51 8.89C18.5 9.61 18.13 10.33 17.37 11.09Z"/></svg>'''
    card_html_block = r'<div class="wcc_liv_card wcc_new_card ##cls##"  >###</div>'
    img_block = r'<img src=##url## >'
    

    img = None  #img = card.thumbnails.get(current_img_channel,"")
    card_img = img_block.replace("##url##",link_img(img)) if img else ""

    generated_html =card_html_block.replace("###",icon_svg+" ###").replace("###",card_img).replace("##cls##","")

    if is_done:
        generated_html+= card_html_block.replace("##cls##","wcc_card_edit_done").replace("###","")
    elif is_error: 
        generated_html+= card_html_block.replace("##cls##","wcc_card_edit_err" ).replace("###","")
    

    return main_html_block.replace("###",generated_html)

def update_stack_view(selected_cards:list[WildcardEntry]=[], invert:bool = False): 
    play_dir = "reverse" if invert else "normal"

    main_html_block = r'<div id="wcc_stack_preview"><div id="wcc_stack_label"> #label# </div> <div class="wcc_cards_stack">###</div></div>'
    card_html_block = f'<div class="wcc_liv_card" style="animation-direction: {play_dir}" id="wcc_liv_card#ndx#">###</div>'
    img_block = f'<img src=##url## style="animation-direction: {play_dir}" >'
    generated_html  = r''
    if invert and selected_cards:
        top_stack = selected_cards[-5:][::-1]
        top_stack+=[top_stack[0]]
    else:
        top_stack = selected_cards[-5:][::-1]
    for index, card in enumerate(top_stack):
        card_img =""
        if card and index <3  :
            img = card.thumbnails.get(current_img_channel)
            card_img = img_block.replace("##url##",link_img(img, card.last_update)) if img else ""
        generated_html =card_html_block.replace("#ndx#",f"{index}").replace("###",card_img) + generated_html
    
    title = selected_cards[0].name if len(selected_cards) ==1 else f"[{len(selected_cards)} Wildcards Selected]"

    return main_html_block.replace("###",generated_html).replace("#label#",title) 

def formulate_text_selector():
    result = " "
    if current_stack_level >0 and selected_stack_paths:
        for stack_path in selected_stack_paths:
            result+=f" {WILD_STR}{stack_path}/*{WILD_STR}"
    else:
        for entry in selected_entries:
            if entry.aux_prompt: result+=f"{entry.aux_prompt}, "
            result+=f" {WILD_STR}{entry.path}{WILD_STR}"
        
    return result 

def update_gallery_view(new_sel_index=None, update_stacks=False):
    global selected_entries
    global filtered_pile
    global filtered_stacks
    global last_edit 
    global selected_stack_paths
    global current_stack_level


    samples_list = []
    if new_sel_index and not multi_selection_mode:
        selected_stack_paths = []
        selected_entries = []
 
    if filtered_pile and current_stack_level>0:
        if update_stacks:
            filtered_stacks={}
            for entry in filtered_pile:
                parent_key = entry.path.split('/')
                parent_key = "/".join(parent_key[:current_stack_level])
                if parent_key:
                    filtered_stacks[parent_key] = filtered_stacks.get(parent_key,[]) + [entry]
        
        page_items = list(filtered_stacks.keys())[max(current_page*ITEMS_CAP-1 - ITEMS_CAP, 0): (current_page*ITEMS_CAP)-1] 
        for i, entry_path in enumerate(page_items) :
            entry_list= filtered_stacks.get(entry_path)
            entry_lead= entry_list[0]
            selected = False
 
            if i==new_sel_index and not multi_selection_mode:
                selected_entries     = [] if entry_path in selected_stack_paths else entry_list.copy()
                selected_stack_paths = [] if entry_path in selected_stack_paths else [entry_path]
                selected = bool(selected_stack_paths)
 
            elif i==new_sel_index :
                if entry_path in selected_stack_paths:
                    selected_stack_paths.remove(entry_path)
                    for sib_entry in entry_list:
                        if sib_entry in selected_entries:
                            selected_entries.remove(sib_entry)
                else:
                    selected = True
                    selected_stack_paths.append(entry_path)
                    for sib_entry in entry_list[::-1]: # makes sure that the leading card is on top of the preview stack 
                        if sib_entry not in  selected_entries:
                            selected_entries.append(sib_entry)     
            else:
                selected = entry_path in selected_stack_paths
            stk_name= f"{entry_path.split('/')[-1]}/*"
            samples_list.append([entry_lead.to_galley_item(is_selected= selected, 
                                                      img_channel= current_img_channel, 
                                                      config_dict= tag_config_dict, 
                                                      stack_count= len(entry_list),
                                                      stack_name= stk_name,
                                                      hidden_tag_groups= hidden_tag_groups
                                                      )]) 
    
    elif filtered_pile:
        page_items = filtered_pile[max(current_page*ITEMS_CAP-1 - ITEMS_CAP, 0): (current_page*ITEMS_CAP)-1]
        for i, entry in enumerate(page_items) :
            selected = False

            if i==new_sel_index and not multi_selection_mode:
                selected_entries     = [] if entry in selected_entries else [entry]
                selected = bool(selected_entries)
            
            elif i==new_sel_index:
                if entry in selected_entries:
                    selected_entries.remove(entry)
                else:
                    selected_entries.append(entry)
                    selected = True
            else:
                selected = entry in selected_entries
            
            samples_list.append([entry.to_galley_item(is_selected= selected, 
                                                      img_channel= current_img_channel, 
                                                      config_dict= tag_config_dict,
                                                      hidden_tag_groups= hidden_tag_groups
                                                      )])
    last_edit = selected_entries[-1] if selected_entries else last_edit
    
    if new_sel_index and current_stack_level>0 and not multi_selection_mode:
        current_stack_level = 0
        filtered_stacks =   {}
        filtered_pile= selected_entries.copy()
        return update_gallery_view()
    
    return  samples_list 

def update_card_mode(html_view:str = "", is_creation:bool = True, is_selection:bool =False, is_edit:bool =False): 
    #[disp_card_stack, btn_copy_txt, tx_edit_quick_path, btn_use_last, tx_edit_wpath, tx_edit_prompt, sel_tag_add,tx_sel_tag_add, btn_create_card, btn_tag_add, btn_tag_rmv, acc_aux_details]
    btn_label = f"Re-Use [{last_edit.name}]" if last_edit else "No Recent Card Info"
    
    
    return ( 
             gr.update( value = html_view ) ,
             gr.update( visible= is_selection or is_edit, icon= link_img( ICON_LIB["copy"],absolute=True)  ), 
             gr.update( visible= is_creation, choices=list(wildcards_dict.keys())),
             gr.update( visible= is_creation and last_edit, value=btn_label),
             gr.update( visible= is_creation),
             gr.update( visible= is_creation),
             gr.update( visible= is_creation or is_edit, choices=list(tags_dict.keys()), value=[]),
             gr.update( visible= is_creation or is_edit, value = ""),
             gr.update( visible= is_creation),
             gr.update( visible= is_edit),
             gr.update( visible= is_edit),
             gr.update( visible= is_selection and len(selected_entries)<2), 

             gr.update( visible= is_selection or is_edit,   icon= link_img( ICON_LIB["edit"],absolute=True)  ), 
             gr.update( visible= is_selection or is_edit,   icon= link_img( ICON_LIB["fav"],absolute=True)  ), 
             gr.update( visible= is_selection or is_edit,   icon= link_img( ICON_LIB["delete"],absolute=True)  ), 
             )

def gr_update_pages(page=0, max_pages=0):
    is_active = page > 0 and max_pages > 0
    next_exist = page+1 <= max_pages
    prev_exist = page-1 > 0
    return ( 
            gr.update(  visible= max_pages> 1 and is_active),
            gr.update(  visible= is_active, label=f"Page ({page}/{max_pages})", value= page),
            gr.update( visible= is_active, interactive= prev_exist),
            gr.update( visible= is_active, interactive= next_exist),
            )
#-------------------------|Gradio Events lvl|-----------------------------


def act_filter_mod_change(sel_filter_prop):
    choices_list = []
    if wildcards_dict and sel_filter_prop==filter_modes[0]:
        choices_list = list(wildcards_dict.keys())
    elif tags_dict and sel_filter_prop==filter_modes[2]:
        choices_list = list(tags_dict.keys())
    return (
        gr.update(visible= sel_filter_prop in [filter_modes[2], filter_modes[3]],value= filter_logic[0]),
        gr.update(visible= sel_filter_prop == filter_modes[0]),
        gr.update(visible= sel_filter_prop in [filter_modes[1], filter_modes[3]], value=""),
        gr.update(visible= sel_filter_prop in [filter_modes[1], filter_modes[3]], value=""),
        gr.update(visible= sel_filter_prop in [filter_modes[0], filter_modes[2]], choices= choices_list, value=[]),
        gr.update(visible= sel_filter_prop==filter_modes[2], choices= choices_list, value=[]),
        gr.update(visible= sel_filter_prop in filter_modes)
    )

def act_run_filter (sel_filter_prop, sel_filter_logic, opt_extend_sel, tx_pos_input, tx_neg_input, sel_pos_input, sel_neg_input):
    global filtered_pile
    global filtered_stacks
    global selected_entries
    global selected_stack_paths
    global current_page

    filtered_pile = []
    filtered_stacks = {}
    selected_entries  = []
    selected_stack_paths = []
    current_page = 1

    samples_list = []
    filtered_list:list[str]= []
 

    if sel_filter_prop == filter_modes[0] and not opt_extend_sel:
        filtered_list = sel_pos_input
    
    elif sel_filter_prop == filter_modes[0]and opt_extend_sel:
        pos_list = set()
        for selector in sel_pos_input:
            parent = "/".join(selector.split("/")[:-1])
            parent = parent+"/" if parent else selector
            pos_list.update(set(process_selector(parent, wild_paths= list(wildcards_dict.keys()))))
        filtered_list = list(pos_list)
    
    elif sel_filter_prop == filter_modes[1] :
        pos_list = set()
        neg_list = set()

        if tx_pos_input:
            for selector in tx_pos_input.split(","):
                selector.strip()
                pos_list.update(set(process_selector(selector, wild_paths= list(wildcards_dict.keys()))))
        if tx_neg_input:
            for selector in tx_neg_input.split(","):
                selector.strip()
                neg_list.update(set(process_selector(selector, wild_paths= list(wildcards_dict.keys()))))

        filtered_list = list(pos_list.difference(neg_list))
    
    elif sel_filter_prop == filter_modes[2]: 
        pos_list = set()
        neg_list = set()
        if sel_pos_input:
            for index, tag in enumerate(sel_pos_input):
                if sel_filter_logic == filter_logic[1]:
                    pos_list.update(set(tags_dict.get(tag,[])))
                elif sel_filter_logic == filter_logic[0]:
                    pos_list = set(tags_dict.get(tag,[])) if index==0 else pos_list.intersection(set(tags_dict.get(tag,[])))
        else:
            pos_list = set(path for sublist in tags_dict.values() for path in sublist)
 
        for tag in sel_neg_input:
            neg_list.update(set(tags_dict.get(tag,[])))
        
        filtered_list = list(pos_list.difference(neg_list))

    elif sel_filter_prop == filter_modes[3]:
            pos_terms_list = [term.strip() for term in tx_pos_input.strip().split(",") if term.strip()]
            neg_terms_list = [term.strip() for term in tx_neg_input.strip().split(",") if term.strip()]
 
            if pos_terms_list or neg_terms_list:
                for wpath, wentry in wildcards_dict.items():
                    if sel_filter_logic == filter_logic[0] :
                        pos_check = all(term in f"{wentry.prompts}" for term in pos_terms_list) if pos_terms_list else True
                    elif sel_filter_logic == filter_logic[1]:
                        pos_check = any(term in f"{wentry.prompts}" for term in pos_terms_list) if pos_terms_list else True
 
                    neg_check = any(term in f"{wentry.prompts}" for term in neg_terms_list) if neg_terms_list else False
                    if pos_check and not neg_check:
                        filtered_list.append(wpath)
    
    if filtered_list:
        for wpath in filtered_list:
            entry = wildcards_dict.get(wpath)
            if entry: 
                if not entry.is_preloaded:
                    entry.preload_previews()
                filtered_pile.append(entry)



    samples_list = update_gallery_view( update_stacks= True)
    page_count =  max(math.ceil(len(filtered_pile)/ITEMS_CAP), 1) if current_stack_level<=0 else max(math.ceil(len(filtered_stacks)/ITEMS_CAP), 1)
    filter_stat_tx = f"🎴 Filter Results: ({len(filtered_pile)}) Wildcards"
    filter_stat_tx+= f"  /  ({len(filtered_stacks)}) Packs at stacking lvl [{current_stack_level}]" if current_stack_level >0 else ""


    return (    gr.update( visible= bool(samples_list), samples= samples_list),

                gr.update( visible= page_count>1),
                gr.update( visible= page_count>1, value = 1, label=f"Page (1/{page_count})"),
                gr.update( visible= page_count>1, interactive= current_page-1 > 0),
                gr.update( visible= page_count>1, interactive= current_page+1 <= page_count),
                gr.update( value =filter_stat_tx ),

                gr.update( visible = True), # enables the creation mode btn
                *update_card_mode( is_creation=False,  is_edit=False ) #9 updates 
              )

def act_select_entry(index):
    global selected_entries
    global card_edit_mode
    card_edit_mode = False

    index = index[0] if isinstance(index,list) else index #in case of gradio 3

    old_count = len(selected_entries)
    samples_list =  update_gallery_view( new_sel_index= index)

    aux_details = details_pannel_html(selected_entries[0]) if (selected_entries and (len(selected_entries)<2)) else ""

    html_view = update_stack_view(selected_entries, invert= old_count>len(selected_entries)) if selected_entries else ""

    return ( 
             gr.update( visible= bool(samples_list), samples= samples_list),
             gr.update( value= current_stack_level),

             gr.update( visible= True),
             *update_card_mode(html_view, is_creation= False , is_selection= bool(selected_entries),  is_edit=False), #9 updates

             gr.update( value = aux_details, visible= (selected_entries and (len(selected_entries)<2) ))
            )

def act_paginate(page_str):
    global current_page
    try:
        page = int(page_str)
    except ValueError:
        print(f"The page ({page_str}) is not valid")
        page = None
        
    
    page_count =  max(math.ceil(len(filtered_pile)/ITEMS_CAP), 1) if current_stack_level<=0 else max(math.ceil(len(filtered_stacks)/ITEMS_CAP), 1)
    if page and (page <= page_count):
        current_page = page
    else:
        print(f"The page ({page}) is not valid")

    samples_list =  update_gallery_view() 
    
    return ( gr.update( visible= bool(samples_list), samples= samples_list),  *gr_update_pages(current_page,page_count)  )


def act_paginate_next():
    global current_page
    page_count =  max(math.ceil(len(filtered_pile)/ITEMS_CAP), 1) if current_stack_level<=0 else max(math.ceil(len(filtered_stacks)/ITEMS_CAP), 1)
    if current_page and current_page+1 <= page_count:
        current_page+= 1
    else:
        print(f"The page ({current_page+1}) is not valid")
    
    samples_list =  update_gallery_view() 
    return ( gr.update( visible= bool(samples_list), samples= samples_list), *gr_update_pages(current_page,page_count),  )
 

def act_paginate_prev():
    global current_page
    page_count =  max(math.ceil(len(filtered_pile)/ITEMS_CAP), 1) if current_stack_level<=0 else max(math.ceil(len(filtered_stacks)/ITEMS_CAP), 1)
    if current_page and current_page-1 > 0:
        current_page-= 1
    else:
        print(f"The page ({current_page-1}) is not valid")
    
    samples_list =  update_gallery_view() 
    
    return (  gr.update( visible= bool(samples_list), samples= samples_list), *gr_update_pages(current_page,page_count) )

def act_select_all():
    global selected_entries
    global selected_stack_paths
    
    selected_entries    = filtered_pile.copy()
    selected_stack_paths = list(filtered_stacks.keys()) if filtered_stacks else []
    
    samples_list =  update_gallery_view()
    html_view = update_stack_view(selected_entries ) if selected_entries else ""
    return (
            gr.update( visible= bool(samples_list), samples= samples_list),

            gr.update( visible= True),
            *update_card_mode(html_view, is_creation= False, is_selection= bool(selected_entries), is_edit=False) #9 updates
            )

def act_deselect_all():
    global selected_entries
    global selected_stack_paths
    
    selected_entries     = []
    selected_stack_paths = []
    
    samples_list =  update_gallery_view()
    html_view = ""
    return (
            gr.update( visible= bool(samples_list), samples= samples_list),

            gr.update( visible= True ),
            *update_card_mode(html_view, is_creation= False, is_selection= False , is_edit=False) #9 updates
            )

def act_change_sel_mode():
    global multi_selection_mode
    multi_selection_mode = not multi_selection_mode
    mode_text = "Stack" if multi_selection_mode else "Single"
    return ( gr.update( value = f"Select Mode [{mode_text}]") )


def act_hide_tags(selected_tag_groups):
    global hidden_tag_groups
    hidden_tag_groups = selected_tag_groups
    samples_list =  update_gallery_view( )
    
    return  (gr.update( visible= bool(samples_list), samples= samples_list))

 

def act_change_stack_level(lvl):
    global current_stack_level
    global selected_stack_paths
    global current_page 

    current_page = 1
    selected_stack_paths = []
    current_stack_level = int(lvl)
    samples_list =  update_gallery_view( update_stacks= True)
    page_count =   max(math.ceil(len(filtered_pile)/ITEMS_CAP), 1) if current_stack_level<=0 else max(math.ceil(len(filtered_stacks)/ITEMS_CAP), 1)
    
    filter_stat_tx = f"🎴 Filter Results: ({len(filtered_pile)}) Wildcards"
    filter_stat_tx+= f"  /  ({len(filtered_stacks)}) Packs at stacking lvl [{current_stack_level}]" if current_stack_level >0 else ""
    
    return (
        gr.update( visible= bool(samples_list), samples= samples_list),
        gr.update( value =filter_stat_tx),
        *gr_update_pages(current_page,page_count)
          )

def act_change_channel(channel):
    global current_img_channel
    current_img_channel = channel if channel in IMG_CHANNELS else ""
    samples_list =  update_gallery_view()
    return (gr.update( visible= bool(samples_list), samples= samples_list) )

def act_toggle_edit_mode():
    global card_edit_mode
    card_edit_mode = (not card_edit_mode) and bool(selected_entries)
    html_view = update_stack_view(selected_entries ) if selected_entries else ""
    return  update_card_mode( html_view= html_view, is_creation= False , is_selection= not card_edit_mode, is_edit= card_edit_mode)

def act_add_fav ():
     return add_tag(["fav"],"")


def add_tag(sel_tag_add:list[str], tx_sel_tag_add:str):
    global wildcards_dict
    global tags_dict
    
    flat_selected_entries = [entry.path for entry in selected_entries]
    new_tags = [tag.strip() for tag in tx_sel_tag_add.split(",") if tag.strip()]
    sel_tag_add.extend(new_tags)
    for tag in sel_tag_add:
        tags_dict[tag] = list(set(tags_dict.get(tag,[]) + flat_selected_entries))
    

    if save_tags(tags_dict):
        for path in flat_selected_entries:
            entry = wildcards_dict.get(path)
            if entry:
                entry.tags = list(set(entry.tags+sel_tag_add))    

    samples_list =  update_gallery_view()
    return (
        gr.update(value=[], choices=list(tags_dict.keys())),
        gr.update(value=""),
        gr.update( visible= bool(samples_list), samples= samples_list)
    )

def remove_tag(sel_tag_add:list[str], tx_sel_tag_add:str):
    global wildcards_dict
    global tags_dict
    new_tags = [tag.lstrip().rstrip() for tag in tx_sel_tag_add.split(",")]
    sel_tag_add.extend(new_tags)
    
    for entry in selected_entries:
        for tag in sel_tag_add:
            traget_tag_list = tags_dict.get(tag)
            if traget_tag_list:
                traget_tag_list.remove(entry.path)

    if save_tags(tags_dict):
        for entry in selected_entries:
            entry.tags = list(set(entry.tags).difference(set(sel_tag_add)))
  

    samples_list =  update_gallery_view()
    return (
        gr.update(value=[], choices=list(tags_dict.keys())),
        gr.update(value=""),
        gr.update( visible= bool(samples_list), samples= samples_list)
    )


def enable_creation_mode():
    global selected_entries
    global selected_stack_paths
    global last_edit
        
    selected_entries     = []
    selected_stack_paths = []
    samples_list =  update_gallery_view()

    return (
        gr.update( visible= False),
        gr.update( visible= bool(samples_list), samples= samples_list),
        *update_card_mode(creation_pannel_html(),  is_creation= True) #9 updates
        )
    

def act_copy_path(wpath:str):
    wentry = wildcards_dict.get(wpath)
    processed_path = wpath.split("/")
    if len(processed_path)>1:
        processed_path.pop()
        processed_path = '/'.join(processed_path)+'/'
    else:
        processed_path =""
 
    return (
        gr.update(value=""),
        gr.update(value=processed_path),
        gr.update(value= wentry.tags if wentry else [])
    )

def act_reuse_last(): 
    processed_path =""
    if last_edit:
        print(f"[{EXT_NAME}] loading info from last edited wildcard")
        processed_path = last_edit.path.split("/")
        if len(processed_path)>1:
            processed_path.pop()
            processed_path = '/'.join(processed_path)+'/'
 
    return (
        gr.update(value=""),
        gr.update(value=processed_path),
        gr.update(value= last_edit.tags if last_edit else [])
    )


def act_create_wildcard (tx_edit_wpath, tx_edit_prompt, sel_tag_add, tx_sel_tag_add):
    global wildcards_dict
    global tags_dict
    global selected_entries
    global selected_stack_paths
    global filtered_pile
    global filtered_stacks
    global current_page
    global current_stack_level
    global last_edit
    
    new_card =None
    if not tx_edit_wpath    : gr.Warning("wildcard path is missing")
    elif tx_edit_wpath.endswith('/')    : gr.Warning("wildcard path must end with name")
    elif not tx_edit_prompt : gr.Warning("wildcard prompt is missing")
    else                    : new_card = update_wildcard_yaml(tx_edit_wpath, tx_edit_prompt)

    if new_card :
        create_dir_and_file(CARDS_FOLDER, new_card.path)
        wildcards_dict[new_card.path] = new_card
        
        filtered_pile       = [new_card]
        filtered_stacks     = {}
        last_edit           = new_card
        selected_entries    = []
        selected_stack_paths = []
        current_page        = 1
        current_stack_level = 0
        
        new_tags = [tag.strip() for tag in tx_sel_tag_add.split(",") if tag.strip()]
        sel_tag_add.extend(new_tags)
        for tag in sel_tag_add:
                tags_dict[tag] = tags_dict.get(tag,[])+[new_card.path]
        if save_tags(tags_dict):
            wildcards_dict[new_card.path].tags = sel_tag_add.copy()
        
    
    samples_list =  update_gallery_view()
    html_view = creation_pannel_html(is_done= bool(new_card), is_error= not bool(new_card))
    return (
            gr.update( value = html_view),
            gr.update( visible= bool(samples_list), samples= samples_list),
            gr.update( value = "🎴 Created Wildcard Entry"),
            gr.update(value= "" if new_card else tx_edit_wpath),
            gr.update(value= "" if new_card else tx_edit_prompt),
            gr.update(value= [] if new_card else sel_tag_add , choices=list(tags_dict.keys())),
            gr.update(value= "" if new_card else tx_sel_tag_add),
            gr.update(choices=list(wildcards_dict.keys())),
            )

 
def act_copy_txt(text):
    print(f"Wildcard selector copied to clipboard")
    return(
        gr.update(show_label=False, label=text, value=toast_notif('Copied to Clipboard!')),
        gr.update( value=formulate_text_selector())
        )
     
#-------------------------|Misc events|--------------------------
def act_nullify_imgs():
    imgs_pile = []
    for entry in selected_entries:
        imgs_pile+= entry.nullify_channel_img(channels=[current_img_channel])
    
    print(f"[{EXT_NAME}] nullified {len(imgs_pile)} previews from channel {current_img_channel}")

    samples_list =  update_gallery_view()
    html_view = update_stack_view(selected_entries) if selected_entries else ""
    return (
        gr.update( value = html_view),
        gr.update( visible= bool(samples_list), samples= samples_list))


def act_misc_rmv_imgs():
    imgs_pile = []
    global selected_entries #REV
    for entry in selected_entries:
        imgs_pile+= entry.delete_channel_img(channels=[current_img_channel])
    
    print(f"[{EXT_NAME}] deleted {len(imgs_pile)} previews from channel {current_img_channel}")

    samples_list =  update_gallery_view()
    html_view = update_stack_view(selected_entries) if selected_entries else ""
    return (
        gr.update( value = html_view),
        gr.update( visible= bool(samples_list), samples= samples_list))

def reset_filter_view():
    global filtered_pile
    global filtered_stacks
    global last_edit
    global selected_entries
    global selected_stack_paths
    global current_page
    global current_stack_level

    filtered_pile       = []
    filtered_stacks     = {}
    last_edit           = None
    selected_entries    = []
    selected_stack_paths = []
    current_page        = 1
    current_stack_level = 0
    
    samples_list =  update_gallery_view()

    return samples_list

def act_misc_rebuild():
    updated_samples_list = reset_filter_view()
    
    if callable(rebuild_callback):
        rebuild_callback(shallow_refresh = False)
        gr.Info("Dictionary have been rebuilt")
    else:
        gr.Error("Dictionary rebuilding failed")
    
    
    return( 
            gr.update( visible= bool(updated_samples_list), samples= updated_samples_list),

            gr.update(visible=True),
            gr.update(value = f"\nDictionay have been rebuilt with a total of [{len(wildcards_dict)}] Entries"),
            gr.update(value = current_stack_level),
            *gr_update_pages(),
            *update_card_mode("",  is_creation= False)
            )

def act_misc_coll_stry():
    wpath_list = [ entry.path for entry in wildcards_dict.values()] 
    collect_stray_previews(wild_paths= wpath_list)

def act_reform_tags():
    global tags_dict

    registered_wpaths = list(wildcards_dict.keys())
    for tag, wpath_list in tags_dict.items():
        muta_list = wpath_list.copy()
        redundant_entries = []
        for wpath in wpath_list:
            if wpath not in registered_wpaths:
                muta_list.remove(wpath)
                redundant_entries.append(wpath)
        
        if redundant_entries:
            tags_dict[tag] = muta_list
            print(f"[{EXT_NAME}] cleaned ({len(redundant_entries)}) redundant entries from [{tag}]")

    
    save_tags(tags_dict)


def act_misc_collect_imgs():
    imgs_pile = []
    for entry in selected_entries:
        imgs_pile+= entry.collect_channel_img()
    print(f"[{EXT_NAME}] collected {len(imgs_pile)} previews from channel {[current_img_channel]}")


def act_upload_wildpack (selected_file_path):
    print(f"Loaded {selected_file_path.name}")
    scanned_cards, scanned_imgs, got_tags  = wildpack_info_scan(selected_file_path.name)
    if scanned_cards:
        html_content = f"Wildcard Pack contains: <br> - {len(scanned_cards)} Cards 🎴 <br> - {len(scanned_imgs)} Thumbnails 🖼 "
        html_content += "<br> - Has tags metadata 🏷 <br>" if got_tags else ""
        isValid = True 
    else:
        html_content = "⚠ Invalid Pack File"
        isValid = False 


    return ( 
        gr.update( visible= isValid),
        gr.update( visible= True, value= html_content)
        )

def act_clear_wildpack (selected_file_path):
    return ( 
        gr.update( visible= False),
        gr.update( visible= False)
        )

def act_import_wildpack ( selected_file_path ):
    print(f"importing {selected_file_path.name}")
    try:
        unpack_wildcard_pack(selected_file_path.name)
        gr.Info("Wildcards imported successfully")
        if callable(rebuild_callback):
            rebuild_callback(shallow_refresh = False)
            gr.Info("Dictionary have been rebuilt")
        else:
            gr.Error("Dictionary rebuilding failed")
    
    except:
        gr.Error("Wildcards import failed")

    updated_samples_list = reset_filter_view()
    
    
    return ( 
        gr.update( value= None),
        gr.update( visible= False),
        gr.update( visible= False), 

        gr.update( visible= bool(updated_samples_list), samples= updated_samples_list),

        gr.update(visible=True),
        gr.update(value = f"\nDictionay have been rebuilt with a total of [{len(wildcards_dict)}] Entries"),
        gr.update(value = current_stack_level),
        *gr_update_pages(),
        *update_card_mode("",  is_creation= False)

        )

def act_export( selection_mode , opt_skip_masked, opt_clear_maskedTags, tx_wildpack_name):
    traget_wildcards = selected_entries if selection_mode == selection_modes[0] else filtered_pile
    
    if opt_skip_masked:
        post_filteded_cards = []
        for card in traget_wildcards:
            for tag in card.tags:
                tag_config = tag_config_dict.get(tag)
                if not tag_config.masked:
                    post_filteded_cards.append(card)
                    break
        traget_wildcards = post_filteded_cards

    if traget_wildcards:
        opr_status = export_cards_pack(selected_cards= traget_wildcards, save_name=tx_wildpack_name, img_channels= [current_img_channel], exclude_Masked_Tags = opt_clear_maskedTags, config_dict= tag_config_dict)
        if opr_status:
            gr.Info(f"Packaging successful")
        else:
            gr.Warning(f"Packaging failed")
    else:
        gr.Warning(f"No selected wildcards")

def act_list_tagroup (selected_tag_group):
    is_create_new =  (selected_tag_group == "__CREATE NEW__")
    loaded_tag_group = TagConfig("") if is_create_new else tag_config_groups.get(selected_tag_group)
    if bool(loaded_tag_group):
        return (
            gr.update( visible= True, value= loaded_tag_group.config_name),
            gr.update( visible= True, value= loaded_tag_group.members),
            gr.update( visible= True, value= loaded_tag_group.masked), 
            gr.update( visible= True, value= loaded_tag_group.tx_color),
            gr.update( visible= True)  )
    else:
        return (
            gr.update( visible= False),
            gr.update( visible= False),
            gr.update( visible= False), 
            gr.update( visible= False),
            gr.update( visible= False)
            )


def act_save_tagroup(tx_taggroup_name, sel_member_tags, opt_mask_group, picker_sec_color):
    global tag_config_groups 
    group_name = "unnamed" if tx_taggroup_name == "" else tx_taggroup_name
    new_group_obj = TagConfig(  config_name= group_name,
                                members= sel_member_tags, 
                                masked= opt_mask_group,
                                bg_color= picker_sec_color+"69",
                                tx_color= picker_sec_color)
    tag_config_groups[group_name] = new_group_obj
    if save_tag_config( list(tag_config_groups.values())):
        build_tag_config_dict(list(tag_config_groups.values()))
        return(
            gr.update(choices= ["All","Masked Tags"]+list(tag_config_groups.keys())),
            gr.update(choices= ["__CREATE NEW__"]+list(tag_config_groups.keys()), value = None),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False),
            gr.update(visible= False)
        )
    else:
        return (None, None, None, None, None, None, None)


    
    
#-------------------------|Gradio Interface lvl|--------------------------
def on_ui_tabs():
    with gr.Blocks() as filter_tab: 
        disp_notif = gr.HTML(toast_notif())
        with gr.Accordion("Filter Options", open=True, elem_id="wcc_fil_accord"):
            with gr.Column(elem_id=f"wcc_fil_opt_div"):
                with gr.Row():
                    sel_filter_prop  = gr.Radio(choices= ["none"]+filter_modes, value = "none", show_label=False, elem_classes="wcc_flat_radio")
                with gr.Row(elem_id=f"wcc_fil_input_div"):
                    sel_filter_logic    = gr.Radio(choices=filter_logic, visible=False, label= "inclusion logic", elem_classes="wcc_fil_aux_opt")
                    opt_extend_sel      = gr.Checkbox(visible=False, label="extend selection to parent", value = False, elem_classes="wcc_fil_aux_opt")
                    tx_pos_input    = gr.Textbox(label="included", visible=False, elem_classes=["wcc_pos_input"])
                    tx_neg_input    = gr.Textbox(label="excluded", visible=False, elem_classes=["wcc_neg_input"])
                    sel_pos_input   = gr.Dropdown( visible=False, multiselect= True, label= "included", elem_classes=["wcc_pos_input"])
                    sel_neg_input   = gr.Dropdown( visible=False, multiselect= True, label= "excluded", elem_classes=["wcc_neg_input"])
                    btn_run_filter  = gr.Button("Run Filter", visible= False, elem_id="wcc_filer_run_btn", variant='primary')
                
                
        with gr.Accordion("Viewer Options", open=False, elem_id= "wcc_prev_opt"):
            with gr.Row():
                with gr.Row(elem_id="wcc_viewer_opts"):
                    opt_stacks_lvl  = gr.Slider(value = 0,label="Cards stacking lvl", step=1, maximum=15) 
                    opt_tags_groups  = gr.Dropdown( visible=True, multiselect= True, label= "Hide Tags", choices= ["All","Masked Tags"]+list(tag_config_groups.keys()))
                opt_img_mod      = gr.Radio(choices= IMG_CHANNELS+["none"], label="Preview channels", value=IMG_CHANNELS[0], elem_classes="wcc_flat_radio")
        with gr.Row():
            with gr.Column(elem_id="wcc_sel_view") :
                disp_card_stack     = gr.HTML("")
                with gr.Row(elem_id="wcc_filt_send_sec"):
                    btn_copy_txt    =  gr.Button("", visible=False, elem_classes=["wcc_status_btn", "wcc_iconed_btn"])
                    btn_edit_card   =  gr.Button("", visible=False, elem_classes=["wcc_status_btn", "wcc_iconed_btn"])
                    btn_fav_card    =  gr.Button("", visible=False, elem_classes=["wcc_status_btn", "wcc_iconed_btn"])
                    btn_delete_card =  gr.Button("", visible=False,  elem_classes=["wcc_status_btn", "wcc_iconed_btn"])

                
                with gr.Accordion("Details", open=True, visible= False) as acc_aux_details:
                    disp_aux_details = gr.HTML(elem_id="wcc_sel_aux_dt")
                with gr.Row(elem_classes="wcc_div_sep"):
                    tx_edit_quick_path  = gr.Dropdown(visible=False,  label= "quick reference")
                    btn_use_last        = gr.Button("No Recent Card Info", visible=False)
                    
                    
                tx_edit_wpath       = gr.Textbox(visible=False,  placeholder="example 'root/parent/sub-parent/card_name'", label= "wildcard path")
                tx_edit_prompt      = gr.Textbox(visible=False ,  label= "prompt")
                sel_tag_add         = gr.Dropdown(visible=False , choices=list(tags_dict.keys()) , multiselect=True, label= "tag selection")
                tx_sel_tag_add      = gr.Textbox(visible=False , placeholder="accepts comma separated values", label= "manual tagging")
                with gr.Row():
                    btn_create_card = gr.Button("Create Wildcard", visible=False, variant='primary')
                    btn_tag_add     = gr.Button("Add tags", visible=False, elem_classes=["wcc_btn_flex"], variant='primary')
                    btn_tag_rmv     = gr.Button("remove tags", visible=False, elem_classes=["wcc_btn_flex"])
                
                
            
            with gr.Column(elem_id=f"wcc_fil_gal_div"):
                with gr.Row():
                    disp_results = gr.HTML("No Filter operation mid execution.", elem_classes="info_log_block")
                    with gr.Row(elem_id="wcc_filter_acts"):
                            sel_none_fil_btn = gr.Button("None", elem_classes="wcc_status_btn")
                            sel_all_fil_btn  = gr.Button("ALL", elem_classes="wcc_status_btn")
                            sel_mode_btn  = gr.Button("Select Mode [Multi]", elem_classes="wcc_status_btn")
                            btn_create_mode     = gr.Button("➕ Create New Card", visible=True, elem_classes="wcc_status_btn")
                            
                wcards_selector = gr.Textbox(visible= False, interactive=False)
                coll_flt_res = gr.Dataset(visible= False,  label="wildcards", elem_id="wcc_fil_cards_gal", components=[gr.HTML(elem_classes=["wcc_fil_card"])], samples= [[i] for i in range(0, ITEMS_CAP)], samples_per_page=ITEMS_CAP+1 , type="index")
                with gr.Row( elem_id= "wcc_pag_div") :
                    btn_pg_prev = gr.Button("\u25C0", visible= False)
                    tx_pg_jump = gr.Textbox(label="page", visible= False)
                    btn_pg_jump = gr.Button("Go", visible= False)
                    btn_pg_next = gr.Button("\u25B6", visible= False)
            
        with gr.Accordion("Import Wildcards Pack", open=False):
            with gr.Row():
                file_browse_wp = gr.File(file_count="single", type='file', file_types=[".zip"], label="Wildcard pack", show_label=True) 
            with gr.Row():
                html_pack_info = gr.HTML(visible=False)
            #with gr.Row():
                #rdo_import_modes = gr.Radio(choices= import_modes , value=import_modes[0])
            btn_import_wp     = gr.Button(visible= False, value="Import", variant="primary")
        
        
        with gr.Accordion("Export as Wildcards Pack", open=False):
            with gr.Row():
                tx_wildpack_name    = gr.Textbox(label="Wildcards pack name")
            with gr.Row():
                rdo_selection_modes = gr.Radio(choices= selection_modes , value=selection_modes[0], label= "Included Wildcards")
            with gr.Row():
                opt_skip_masked         = gr.Checkbox(label="Exclude Wildcards With Masked Tags")
                opt_clear_maskedTags    = gr.Checkbox(label="Do Not Export Masked Tags")
            btn_export      = gr.Button("Export", variant="primary")
        

        with gr.Accordion("Tag Groups", open=False):
            with gr.Column():
                sel_mgr_tag_groups  = gr.Dropdown( visible=True, multiselect= False, label= "Tag groups", choices= ["__CREATE NEW__"]+list(tag_config_groups.keys()))
                tx_taggroup_name    = gr.Textbox(visible=False, label="Tag Group Name")
                sel_member_tags     = gr.Dropdown(visible=False, choices=list(tags_dict.keys()), multiselect=True, label= "Member tags")
                opt_mask_group      = gr.Checkbox(visible=False, label="Masked tag group", value= False)
                picker_sec_color    = gr.ColorPicker(visible=False,show_label= True, label= "Group Color", elem_classes="wcc_color_picker")
                btn_save_tag_group  = gr.Button(visible=False,  value= "Save Tag Group", variant="primary")
        
        with gr.Accordion("Misc Actions", open=False):
            gr.HTML(value="Dictionary actions:")
            with gr.Row():
                btn_misc_rebuild        = gr.Button("Rebuild Wildcards Dictionary", elem_classes="wld_gal_imbutton")
                btn_misc_coll_stry      = gr.Button("Collect Redundant Thumbnail Files")
                btn_misc_reform_tags    = gr.Button("Rebuild Tags Index [NYI]", visible= False)
            gr.HTML(value="Selected cards channel actions:")
            with gr.Row():
                btn_misc_coll_imgs      = gr.Button("Collect Thumbnails")
                btn_misc_nullify        = gr.Button("Nullify Thumbnails")
                btn_misc_rmv_imgs       = gr.Button("Remove Thumbnails", elem_classes= "wld_gal_ngbutton")
        
        
        js_clipborad= ''' 
            (text) => {
                var notifContainer = document.getElementById("wcc_notif_msg");
                navigator.clipboard.writeText(text).then(() => {
                    console.log("Copied to clipboard: " + text);
                }).catch(err => {
                    console.log("Failed to copy: " + err);
                });
                if (notifContainer) notifContainer.classList.add("wcc_anim"); 
                setTimeout(() => {  if (notifContainer)  notifContainer.classList.remove("wcc_anim");    }, 2100);
                }
        '''

        js_toast_trigger= ''' 
            () => {
                var notifContainer = document.getElementById("wcc_notif_msg");
                if (notifContainer) notifContainer.classList.add("wcc_anim"); 
                setTimeout(() => {  if (notifContainer)  notifContainer.classList.remove("wcc_anim");    }, 2100);
                }
        '''


        js_kill_notif= ''' 
            () => {setTimeout(() => {
                            var notifContainer = document.getElementById("wcc_notif_msg");
                            if (notifContainer)  {
                                notifContainer.classList.remove("wcc_anim");
                                }
                            else {
                                console.log("DOM not found");
                            }
                    }, 2100);
            }
        '''
        js_reload = ''' 
            () => {
                var btn_refresh_internal = gradioApp().getElementById("txt2img_wildcards_extra_refresh");
                btn_refresh_internal.dispatchEvent(new Event("click"));
            }
        '''
        

     
        gr_stack_page_selector  = [btn_pg_jump, tx_pg_jump, btn_pg_prev, btn_pg_next]
        gr_stack_filter_pannel  = [sel_filter_logic, opt_extend_sel, tx_pos_input, tx_neg_input, sel_pos_input, sel_neg_input, btn_run_filter]
        gr_stack_card_editor    = [disp_card_stack, btn_copy_txt, tx_edit_quick_path, btn_use_last, tx_edit_wpath, tx_edit_prompt, sel_tag_add,tx_sel_tag_add, btn_create_card, btn_tag_add, btn_tag_rmv, acc_aux_details, btn_edit_card, btn_fav_card, btn_delete_card]

        sel_filter_prop.change  (act_filter_mod_change , inputs= [sel_filter_prop], outputs= gr_stack_filter_pannel )
        btn_run_filter.click    (act_run_filter        , inputs= [sel_filter_prop, sel_filter_logic, opt_extend_sel, tx_pos_input, tx_neg_input, sel_pos_input, sel_neg_input], outputs= [coll_flt_res, *gr_stack_page_selector, disp_results, btn_create_mode, *gr_stack_card_editor])
        coll_flt_res.select     (act_select_entry       , inputs= [coll_flt_res], outputs= [coll_flt_res, opt_stacks_lvl, btn_create_mode, *gr_stack_card_editor, disp_aux_details])
        
        btn_pg_jump.click       (act_paginate       ,  inputs=  [tx_pg_jump], outputs= [coll_flt_res, *gr_stack_page_selector])
        btn_pg_next.click       (act_paginate_next  ,  outputs= [coll_flt_res, *gr_stack_page_selector])
        btn_pg_prev.click       (act_paginate_prev  ,  outputs= [coll_flt_res, *gr_stack_page_selector])
        
        opt_stacks_lvl.release  (act_change_stack_level ,  inputs=  [opt_stacks_lvl], outputs= [coll_flt_res, disp_results, *gr_stack_page_selector])
        opt_tags_groups.select    (act_hide_tags        ,  inputs=  [opt_tags_groups], outputs= [coll_flt_res] )
        
        opt_img_mod.change      (act_change_channel     ,  inputs=  [opt_img_mod], outputs= [coll_flt_res])
        sel_all_fil_btn.click   (act_select_all         ,  outputs= [coll_flt_res, btn_create_mode, *gr_stack_card_editor])
        sel_none_fil_btn.click  (act_deselect_all       ,  outputs= [coll_flt_res, btn_create_mode, *gr_stack_card_editor])
        sel_mode_btn.click      (act_change_sel_mode    ,  outputs= [sel_mode_btn])

        btn_copy_txt.click        (act_copy_txt, inputs=[wcards_selector], outputs=[disp_notif, wcards_selector]).then(fn= None, inputs=[wcards_selector], _js=js_clipborad)
        btn_create_mode.click     (enable_creation_mode ,  inputs=  [], outputs= [btn_create_mode, coll_flt_res, *gr_stack_card_editor])
        tx_edit_quick_path.select (act_copy_path        ,  inputs=  [tx_edit_quick_path], outputs= [tx_edit_quick_path, tx_edit_wpath, sel_tag_add])
        btn_use_last.click        (act_reuse_last,  outputs= [tx_edit_quick_path, tx_edit_wpath, sel_tag_add])
        btn_create_card.click     (act_create_wildcard  ,  
                                   inputs=  [tx_edit_wpath, tx_edit_prompt, sel_tag_add, tx_sel_tag_add], 
                                   outputs= [disp_card_stack, coll_flt_res, disp_results, tx_edit_wpath, tx_edit_prompt, sel_tag_add, tx_sel_tag_add, tx_edit_quick_path]
                                   )

        
        btn_edit_card.click     (act_toggle_edit_mode , outputs= [*gr_stack_card_editor])
        btn_fav_card.click      (act_add_fav    ,  outputs= [sel_tag_add, tx_sel_tag_add, coll_flt_res])
        

        btn_tag_add.click       (add_tag    , inputs= [sel_tag_add, tx_sel_tag_add], outputs= [sel_tag_add, tx_sel_tag_add, coll_flt_res])
        btn_tag_rmv.click       (remove_tag , inputs= [sel_tag_add, tx_sel_tag_add], outputs= [sel_tag_add, tx_sel_tag_add, coll_flt_res])


        btn_misc_rebuild.click      (act_misc_rebuild , outputs= [coll_flt_res, btn_create_mode, disp_results, opt_stacks_lvl,  *gr_stack_page_selector, *gr_stack_card_editor])
        btn_misc_coll_stry.click    (act_misc_coll_stry)
        btn_misc_reform_tags.click  (act_reform_tags)
        btn_misc_coll_imgs.click    (act_misc_collect_imgs)
        btn_misc_nullify.click      (act_nullify_imgs,  outputs= [disp_card_stack, coll_flt_res])
        btn_misc_rmv_imgs.click     (act_misc_rmv_imgs, outputs= [disp_card_stack, coll_flt_res])

 
        btn_export.click        (act_export, inputs= [rdo_selection_modes, opt_skip_masked, opt_clear_maskedTags, tx_wildpack_name] )
        file_browse_wp.upload   (act_upload_wildpack, inputs= [file_browse_wp] , outputs=[btn_import_wp, html_pack_info])
        file_browse_wp.clear    (act_clear_wildpack,  inputs= [file_browse_wp] , outputs=[btn_import_wp, html_pack_info])
        btn_import_wp.click     (act_import_wildpack, inputs= [file_browse_wp] , outputs= [file_browse_wp, btn_import_wp, html_pack_info,       coll_flt_res, btn_create_mode, disp_results, opt_stacks_lvl,  *gr_stack_page_selector, *gr_stack_card_editor])

        sel_mgr_tag_groups.select   (act_list_tagroup, inputs= [sel_mgr_tag_groups],  outputs=[tx_taggroup_name, sel_member_tags, opt_mask_group, picker_sec_color, btn_save_tag_group])
        btn_save_tag_group.click    (act_save_tagroup, inputs=[tx_taggroup_name, sel_member_tags, opt_mask_group, picker_sec_color], outputs=[opt_tags_groups, sel_mgr_tag_groups, tx_taggroup_name, sel_member_tags, opt_mask_group,  picker_sec_color, btn_save_tag_group] )
    
    return ((filter_tab, TAB_NAME, f"wildcards_filter_tab"),)
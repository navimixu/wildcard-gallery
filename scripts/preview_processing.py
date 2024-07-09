from modules.processing import process_images, Processed, fix_seed
from modules.shared import state, opts
from modules import images
import os
from PIL import Image, ImageOps
from scripts.misc_utils import (
    CARDS_FOLDER,
    WILD_STR,
)

def resize_as_thumbnail (img, tragetSize=512):
    thumbnail_size = tragetSize, tragetSize
    
    if img.width > img.height :
        width = tragetSize
        height = round((img.height/img.width)*tragetSize)
    else:
        width = tragetSize
        height = round((img.height/img.width)*tragetSize)
    
    #return img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
    return images.resize_image(0, img, width, height)
    

def txt2img_process(p,selected_wild_paths, replace_str_opt = "", task_override=False, preview_suffix =""): 
  
    images_list = []
    all_prompts = []
    infotexts = []
    suffix = "."+preview_suffix.replace(" ","") if (not preview_suffix=="") and (not preview_suffix=="default") and preview_suffix  else ""
    base_prompt = p.prompt
    fix_seed(p)
    filtered_job_list = []

    print(f"\n Selected ({len(selected_wild_paths)}) wildcards for preview generation :")
    for wpath in selected_wild_paths : 
        save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+suffix
        if os.path.exists(save_file_name+".jpeg") or os.path.exists(save_file_name+".jpg") or os.path.exists(save_file_name+".png")  or os.path.exists(save_file_name+".gif"):
            if task_override:
                filtered_job_list.append(wpath)
                print(f">> {wpath}  (EXIST=OVERRIDE)")
            else:
                print(f">> {wpath}  (EXIST=SKIP)")
        else:
            filtered_job_list.append(wpath)
            print(f">> {wpath}")
    
    print(f"\n Generating ({len(filtered_job_list)}/{len(selected_wild_paths)}) wildcard previews ...")

    state.job_count = len(filtered_job_list)
    for wpath in filtered_job_list:
        if state.interrupted: break

        if(replace_str_opt=="" or base_prompt.count(replace_str_opt)==0):
            p.prompt = f"{base_prompt} {WILD_STR}{wpath}{WILD_STR}"
        else:
            p.prompt = base_prompt.replace(replace_str_opt, f"{WILD_STR}{wpath}{WILD_STR}", 1)  
        
        all_prompts.append(p.prompt)
        
        proc = process_images(p)
        infotexts.append(proc.info)
        
        if(len(proc.images)>1):
            images_list.append(proc.images[0])
        else:
            images_list += proc.images
        
        if state.interrupted: break  
        # save_dir = os.path.dirname(os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep)))
        # save_name = wpath.split("/")[-1]
        # images.save_image(
        #         image= proc.images[0], 
        #         path= save_dir, 
        #         basename= save_name, 
        #         seed = p.seed, 
        #         prompt = p.prompt, 
        #         extension= opts.samples_format, 
        #         info="", 
        #         p=p, 
        #         suffix= suffix)
        
        save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+suffix+".jpeg"
        print(f"Saving preview image at: {save_file_name}")
        #proc.images[0].save(save_file_name)
        if(getattr(opts, "wcc_downscale_preview", False)):
            final_image = resize_as_thumbnail(proc.images[0])
        else:
            final_image = proc.images[0]
        
        images.save_image_with_geninfo(image = final_image, geninfo = proc.info, filename = save_file_name)
        

    return Processed(p, images_list, p.seed, "", all_prompts=all_prompts, infotexts=infotexts)


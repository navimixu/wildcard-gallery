from modules.processing import process_images, Processed, fix_seed
from modules.shared import state, opts
from modules import images
import os
import shutil 
from PIL import Image, ImageOps
from scripts.misc_utils import (
    CARDS_FOLDER, RES_FOLDER, WILD_STR, VALID_IMG_EXT,EXT_NAME
)

prefered_format = ".jpeg"

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

def normal_process(p): 
    proc = process_images(p)
    return Processed(p, proc.images, p.seed, "", all_prompts=proc.all_prompts, infotexts=proc.infotexts)





def txt2img_preview_process(p,selected_wild_paths, replace_str_opt = "", task_override=False, preview_suffix =["default"], insertion_type = "AFTER", view_mode=False, lock_seed=False): 
  
    images_list = []
    all_prompts = []
    infotexts = []
    

    base_prompt = p.prompt
    fix_seed(p)
    filtered_job_list = []
    filtered_job_map = {}
    new_img_tracker = {}
    job_count = 0 
    
    if(selected_wild_paths):
        print(f"\n[{EXT_NAME}] Selected ({len(selected_wild_paths)}) wildcards for image generation :")
        for channel_item in preview_suffix:
            suffix = "."+channel_item.replace(" ","") if (not channel_item=="") and (not channel_item=="default") and channel_item  else ""
            filtered_job_map[channel_item] = []
            for wpath in selected_wild_paths : 
                save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+suffix
                if  any(os.path.exists(save_file_name+ext) for ext in VALID_IMG_EXT ) and not view_mode:
                    if task_override:
                        filtered_job_map[channel_item].append(wpath)
                        print(f"  >> {wpath}  (EXIST=OVERRIDE)")
                    else:
                        print(f"  >> {wpath}  (EXIST=SKIP)")
                else:
                    filtered_job_map[channel_item].append(wpath)
                    print(f"  >> {wpath}")
            
            if view_mode:
                print(f"\n[{EXT_NAME}] Using ({len(filtered_job_map[channel_item])}/{len(selected_wild_paths)}) wildcards for image generation ...\n ")
            else:
                print(f"\n[{EXT_NAME}] Generating ({len(filtered_job_map[channel_item])}/{len(selected_wild_paths)}) wildcard previews for channel [{channel_item}] ...\n ")
            job_count+= len(filtered_job_map[channel_item])

        state.job_count = job_count
        job_itr_counter = 0
        for job_channel, filtered_job_list in filtered_job_map.items():
            if not lock_seed:
                p.seed = p.seed+job_itr_counter
            
            job_itr_counter = job_itr_counter + 1
            suffix = "."+job_channel.replace(" ","") if (not job_channel=="") and (not job_channel=="default") and job_channel  else ""
            for i, wpath in enumerate(filtered_job_list):
                save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+ suffix + prefered_format
                
                
                if state.interrupted: break
 
                if(insertion_type == "SREACH & REPLACE"):
                    if(replace_str_opt!="" and base_prompt.count(replace_str_opt)>0):
                        p.prompt = base_prompt.replace(replace_str_opt, f"{WILD_STR}{wpath}{WILD_STR}", 1)  
                elif(insertion_type =="BEFORE"):
                    p.prompt = f"{WILD_STR}{wpath}{WILD_STR} {base_prompt}"
                else:
                    p.prompt = f"{base_prompt} {WILD_STR}{wpath}{WILD_STR}"
                    
                all_prompts.append(p.prompt)
                proc = process_images(p)
                infotexts.append(proc.info)
                
                if(len(proc.images)>1):
                    images_list.append(proc.images[0])
                else:
                    images_list += proc.images
            
                if state.interrupted: break  
    


                if(getattr(opts, "wcc_downscale_preview", False)):
                    final_image = resize_as_thumbnail(proc.images[0])
                else:
                    final_image = proc.images[0]
                
                if not view_mode:
                    images.save_image_with_geninfo(image = final_image, geninfo = proc.info, filename = save_file_name)
                
                new_img_tracker[wpath]= new_img_tracker.get(wpath,{})
                new_img_tracker[wpath][job_channel]=  save_file_name
                if not view_mode:
                    wname = wpath.split('/')[-1]
                    print(f"Operation progress: ({i+1}/{len(filtered_job_list)}) @channel[{job_channel}] Saving preview thumbnail for [{wname}] ")
            

    return Processed(p, images_list, p.seed, "", all_prompts=all_prompts, infotexts=infotexts), new_img_tracker

def txt2img_prompting_process(p,selected_wild_paths, replace_str_opt = "", insertion_type = "AFTER", combine_cards=False, lock_seed=True): 
  
    images_list = []
    all_prompts = []
    infotexts = []
    
    base_prompt = p.prompt
    fix_seed(p)
    filtered_job_list = []
    job_count = 0 
    
    if(selected_wild_paths):
        print(f"\n[{EXT_NAME}] Selected ({len(selected_wild_paths)}) wildcards for prompting:")
        for wpath in selected_wild_paths : 
            filtered_job_list.append(f"{WILD_STR}{wpath}{WILD_STR}")
            print(f"  >> {wpath}")
            

        if combine_cards:
            print(f"\n[{EXT_NAME}] Combining ({len(filtered_job_list)}) wildcards for image generation ...\n ")
            filtered_job_list[0] = ", ".join(filtered_job_list)
            job_count= 1
        else:
            print(f"\n[{EXT_NAME}] Using ({len(filtered_job_list)}) wildcards for image generation ...\n ")
            job_count+= len(filtered_job_list )

        state.job_count = job_count
        job_itr_counter = 0
   
            
        for i, wildcard_p in enumerate(filtered_job_list):
            if not lock_seed:
                p.seed = p.seed+job_itr_counter
            job_itr_counter = job_itr_counter + 1
            
            if state.interrupted: break

            if(insertion_type == "SREACH & REPLACE"):
                if(replace_str_opt!="" and base_prompt.count(replace_str_opt)>0):
                    p.prompt = base_prompt.replace(replace_str_opt, wildcard_p, 1)  
            elif(insertion_type =="BEFORE"):
                p.prompt = f"{wildcard_p} {base_prompt}"
            else:
                p.prompt = f"{base_prompt} {wildcard_p}"
                
            all_prompts.append(p.prompt)
            proc = process_images(p)
            infotexts.append(proc.info)
            
            if(len(proc.images)>1):
                images_list.append(proc.images[0])
            else:
                images_list += proc.images
        
            if state.interrupted: break  

            if not combine_cards:
                print(f"Operation progress: ({i+1}/{len(filtered_job_list)}) cards ")
            

    return Processed(p, images_list, p.seed, "", all_prompts=all_prompts, infotexts=infotexts) 


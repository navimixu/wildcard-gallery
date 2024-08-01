from modules.processing import process_images, Processed, fix_seed
from modules.shared import state, opts
from modules import images
import os
import shutil 
from PIL import Image, ImageOps
from scripts.misc_utils import (
    CARDS_FOLDER,
    RES_FOLDER,
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

def set_preview_as_null(selected_wild_paths, task_override=False, channel_suffix ="default"):
    suffix = "."+channel_suffix.replace(" ","") if (not channel_suffix=="") and (not channel_suffix=="default") and channel_suffix  else ""
    filtered_job_list = []

    print(f"\n Selected ({len(selected_wild_paths)}) wildcards for preview nullification :")
    for wpath in selected_wild_paths : 
        save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+suffix
        if os.path.exists(save_file_name+".jpeg") or os.path.exists(save_file_name+".jpg") or os.path.exists(save_file_name+".png")  or os.path.exists(save_file_name+".gif"):
            if task_override:
                filtered_job_list.append(wpath)
                print(f">> {wpath}  (EXIST=OVERRIDE)")
                shutil.copyfile(os.path.join(RES_FOLDER,"null-preview.jpeg"), os.path.join(save_file_name+".jpeg"))
            else:
                print(f">> {wpath}  (EXIST=SKIP)")
        else:
            filtered_job_list.append(wpath)
            shutil.copyfile(os.path.join(RES_FOLDER,"null-preview.jpeg"), os.path.join(save_file_name+".jpeg"))
            print(f">> {wpath}")
    
    print(f"\n({len(filtered_job_list)}/{len(selected_wild_paths)}) wildcard previews nullified")
    

   

def txt2img_process(p,selected_wild_paths, replace_str_opt = "", task_override=False, preview_suffix =["default"], insertion_type = "AFTER"): 
  
    images_list = []
    all_prompts = []
    infotexts = []
    prefered_format = ".jpeg"

    base_prompt = p.prompt
    fix_seed(p)
    filtered_job_list = []
    filtered_job_map = {}
    job_count = 0 
    if(selected_wild_paths):
        print(f"\n Selected ({len(selected_wild_paths)}) wildcards for preview generation :\n \n ")
        for channel_item in preview_suffix:
            suffix = "."+channel_item.replace(" ","") if (not channel_item=="") and (not channel_item=="default") and channel_item  else ""
            filtered_job_map[channel_item] = []
            for wpath in selected_wild_paths : 
                save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+suffix
                if os.path.exists(save_file_name+".jpeg") or os.path.exists(save_file_name+".jpg") or os.path.exists(save_file_name+".png")  or os.path.exists(save_file_name+".gif"):
                    if task_override:
                        filtered_job_map[channel_item].append(wpath)
                        print(f">> {wpath}  (EXIST=OVERRIDE)")
                    else:
                        print(f">> {wpath}  (EXIST=SKIP)")
                else:
                    filtered_job_map[channel_item].append(wpath)
                    print(f">> {wpath}")
            
            print(f" Generating ({len(filtered_job_map[channel_item])}/{len(filtered_job_map[channel_item])}) wildcard previews in channel [{channel_item}] ...\n ")
            job_count+= len(filtered_job_map[channel_item])

        state.job_count = job_count

        for job_channel, filtered_job_list in filtered_job_map.items():
            suffix = "."+job_channel.replace(" ","") if (not job_channel=="") and (not job_channel=="default") and job_channel  else ""
            p.seed = p.seed+1
            for wpath in filtered_job_list:
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
 
                
                save_file_name= os.path.join(CARDS_FOLDER, wpath.replace("/", os.path.sep))+ suffix + prefered_format
                print(f"Saving preview image at: {save_file_name}")
 
                if(getattr(opts, "wcc_downscale_preview", False)):
                    final_image = resize_as_thumbnail(proc.images[0])
                else:
                    final_image = proc.images[0]
                
                images.save_image_with_geninfo(image = final_image, geninfo = proc.info, filename = save_file_name)
            

    return Processed(p, images_list, p.seed, "", all_prompts=all_prompts, infotexts=infotexts)


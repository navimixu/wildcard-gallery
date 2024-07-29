
  

# Wildcard Gallery


## What is this

This Automatic1111 extension primary adds a new extra networks gallery for wildcards along with preview thumbnails and other features for an enhanced wildcards management and use experience.

  

## Features

- wildcards gallery

- automatic batch thumbnail generation

- thumbnail size optimization

- the ability to have multiple preview thumbnails for each item (up to 4 preview channels)

## requirements

this extension extends on the wildcard functionality so it goes without saying that you already have in your WebUi ecosystem if not then you'll need to install the **[sd-dynamic-prompts](https://github.com/adieyal/sd-dynamic-prompts)** extension.

## Usage

### Gallery

- After installation the extension should automatically index all wildcard items (not inner lists) found in your wildcard directory whether in `.txt` or `.yaml` format then creates gallery entries for each indexed item.

<img  src="screenshots/screen (4).png"/>

(this process happens on every start or galley refresh to pick up on newly added or altered wildcards)

- The gallery entries are physically present in `extensions\sd-webui-wildcard-gallery\cards` as acts the same as any extra network entry.

that means that if you add an image named the same a specific entry it would be assigned as its DEFAULT preview thumbnail (may require a gallery refresh to show up)

<img  src="screenshots/screen (6).png"/>

<img  src="screenshots/screen (2).png"/>

<img  src="screenshots/screen (1).png"/>

- Additionally you can also add image with the predefined suffixes [.preview, .preview1, .preview2, .preview3] to add additional thumbnails to its respective channel, then you can later on switch between preview channels in the settings tab `Settings/Wildcards Gallery/Switch preview images`

after hitting **Apply settings** and **Refresh Galley** all wildcards previews would change to that of the selected channel (if its exists else it will fall back to the DEFAULT preview)

<img  src="screenshots/screen (7).png"/>

### Preview generation

- You batch generate preview images for wildcards beaches by selecting the `Wildcards preview utils` in the Script dropdown menu in either the txt2img tab
- you simply have to choose the cards from the dropdown menu (you can also type while in the dropdown menu to filter items )
<img  src="screenshots/screen (5).png"/>

- the in the following screenshot only 1 preview for the "knight" wildcard will be generated.

- you can also use the parent wildcard path to easly select multiple cards at once for the preview generation
<img  src="screenshots/screen (8).png"/>

- the in the following screenshot all the wildcards nested under "fantesy_jobs" will have thier previews generated
- simply check the `use wildcard branch selector` box and enter the parent wildcard activation path in the `wildcard parent branch` text area
[ *if you are unsure about the wildcard activation path you can click on the wildcard in the galley that will insert the activation path into the prompt area for you to view * ]

- now after hitting **Generate** the script will:

- automatically iterate over the sub-wildcards found under parent wildcard

- adds them to end of the prompt

- auto assign the generated result to their respective gallery entries

  

For Example:

for the following wildcard hierarchy

<img  src="screenshots/screen (3).png"/>

inputting `navi_atlas/urban_areas/mid_developed` as a parameter would generate one image for the "mid_developed" wildcard

while `navi_atlas/urban_areas/` as a parameter would generate images for all wildcards within "urban_areas"

- additionally you can choose to include the resulted previews in preview channels other then the DEFAULT one by expanding on the **Extra options** section and changing the **preview channel** prior generating

## Settings

- to limit indexation to specific wildcard branches you can add the parent activation path wildcard to the **Whitelist**

- to exclude wildcards from indexation you can add their activation path to the **Whitelist**

- you can toggle the **Downscale preview images** to resize and compress generated previews to take far less size on the disk

- you can switch between previews by selecting their respective channel in **Switch preview images**

- the **Clean residue cards and folders** action clean up empty folders left by pruned or deleted wildcard branches

- the **Collect stray cards** collected thumbnails left behind by deleted or renamed wildcards and places them in `extensions\sd-webui-wildcard-gallery\STRAY_RESOURCES`

## Installation

### Manually

`git clone` this repo to the `extensions` folder in your Web UI installation.

## Compatibility

- tested on [Automatic1111 Webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) v1.9

- tested on [Automatic1111 Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) f0.0.17v1.8.0rc

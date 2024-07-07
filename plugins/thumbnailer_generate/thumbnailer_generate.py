#!/usr/bin/env python3
#coding: utf-8

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Thumbnailer - Generate
"""


import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

import pygsheets
import configparser
import sys
import json
import re
import random
import math
import os

sys.stderr = open('C:/log/thumbnailer-output.txt','a')
sys.stdout=sys.stderr # So that they both go to the same file

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

######### BUILD THUMBNAIL #########
def buildThumbnail(instance, structure):
    game = instance['game']
    # Image & Group
    image = Gimp.list_images()[0]
    generated = image.get_layer_by_name('_Generated')
    # Create Video Layer Group
    videoThumbGroup = image.get_layer_by_name("empty_layer_group").copy()
    videoThumbGroup.set_name(instance['videoid'])
    videoThumbGroup.set_visible(True)
    image.insert_layer(videoThumbGroup, generated, 0)
    # Create Border Segment
    borderGroup = image.get_layer_by_name("empty_layer_group").copy()
    borderGroup.set_name('border')
    borderGroup.set_visible(True)
    image.insert_layer(borderGroup, videoThumbGroup, 0)
    # Add Border & Mask
    borderColorLayer = image.get_layer_by_name(f"border[{game}]").copy()
    borderColorLayer.set_visible(True)
    image.insert_layer(borderColorLayer, borderGroup, 0)
    borderMask = image.get_layer_by_name("border_layer_mask").copy()
    borderMask.set_visible(True)
    image.insert_layer(borderMask, borderGroup, 0)
    borderMask.set_mode(58)
    # Add Episode Text
    epNumber = instance['ep_number']
    subText = instance['ep_sub_text']
    subText = re.sub('<br>', '\n', subText)
    # subText = "Nights\n1 - 3"
    epLayer = image.get_layer_by_name('empty_layer').copy()
    epLayer.set_visible(True)
    epSubLayer = image.get_layer_by_name('empty_layer').copy()
    epSubLayer.set_visible(True)
    epTextGroup = image.get_layer_by_name("empty_layer_group").copy()
    epTextGroup.set_visible(True)
    epTextGroup.set_name('ep text')
    image.insert_layer(epTextGroup, videoThumbGroup, 0)
    image.insert_layer(epLayer, epTextGroup, 0)
    image.insert_layer(epSubLayer, epTextGroup, 0)
    epLayer.set_visible(True)
    epLayer.set_name('ep_text')
    epSubLayer.set_visible(True)
    epSubLayer.set_name('ep_sub_text')
    white = Gegl.Color()
    white.set_rgba(1.0, 1.0, 1.0, 1.0)    
    Gimp.context_set_foreground(white)
    epTextLayer = Gimp.text_font(image,
                                epLayer,
                                20,
                                591,
                                epNumber, 0,
                                True,
                                120,
                                Gimp.fonts_get_by_name("Bangers Regular")[0])  
    Gimp.floating_sel_anchor(epTextLayer)
    image.select_color(0, epLayer, white)
    epBounds = image.get_selection().bounds(image)
    epTextSubLayer = Gimp.text_font(image,
                                    epSubLayer,
                                    epBounds.x2 + 10,
                                    epBounds.y1 - 10 if subText.count('\n') == 1 else epBounds.y1 + 18,
                                    subText, 0,
                                    True,
                                    57 if subText.count('\n') == 1 else 75,
                                    Gimp.fonts_get_by_name("Bangers Regular")[0])
    epTextSubLayer.set_line_spacing(-15)
    Gimp.floating_sel_anchor(epTextSubLayer)
    image.select_color(0, epSubLayer, white)
    epSubBounds = image.get_selection().bounds(image)
    # Drop Shadow For Text
    if epBounds.non_empty:
        createDropShadow(epLayer, 3,3, 4, 0, "000000")
    if epSubBounds.non_empty:
        createDropShadow(epSubLayer, 3,3, 4, 0, "000000")
    # Add Border Behind Text
    image.get_selection().none(image)
    top = min(epBounds.y1 if epBounds.non_empty else 0, epSubBounds.y1 if epSubBounds.non_empty else 720) - 15
    width = (epBounds.x2 if epBounds.non_empty else 0) + (epSubBounds.x2 + 15 if epSubBounds.non_empty else 0) - (epSubBounds.x1 if epSubBounds.non_empty else 0) + 15 + 10 + 25
    image.select_round_rectangle(0, -25, top, width, 200, 25, 25)
    image.get_selection().feather(image, 8)
    borderMask.edit_clear()
    image.get_selection().none(image)
    # Add Highlight & Logo
    borderHighlightMask = image.get_layer_by_name("border_highlight_mask").copy()
    borderHighlightMask.set_visible(True)
    image.insert_layer(borderHighlightMask, borderGroup, 0)
    potamusLogo = image.get_layer_by_name("potamus_logo").copy()
    potamusLogo.set_visible(True)
    image.insert_layer(potamusLogo, borderGroup, 0)
    # Iterate Over Features
    featuresGroupTop = image.get_layer_by_name("empty_layer_group").copy()
    featuresGroupTop.set_name('features-top')
    featuresGroupTop.set_visible(True)
    image.insert_layer(featuresGroupTop, videoThumbGroup, 0)
    featuresGroupMiddle = image.get_layer_by_name("empty_layer_group").copy()
    featuresGroupMiddle.set_name('features-middle')
    featuresGroupMiddle.set_visible(True)
    image.insert_layer(featuresGroupMiddle, videoThumbGroup, 3)
    featuresGroupBottom = image.get_layer_by_name("empty_layer_group").copy()
    featuresGroupBottom.set_name('features-bottom')
    featuresGroupBottom.set_visible(True)
    image.insert_layer(featuresGroupBottom, videoThumbGroup, 5)
    for feature in reversed(structure[game]['features']):
        featureGroup = image.get_layer_by_name("empty_layer_group").copy()
        featureGroup.set_visible(True)
        print(f"\tProcessing feature: {feature['type']}[{game}]")
        featureOptions = image.get_layer_by_name(f"{feature['type']}[{game}]")
        # Get Selector Type
        if feature['selector'] == "ordered":
            if instance['features'][feature['type']]:
                featureInstance = instance['features'][feature['type']].pop() if feature['type'] in instance['features'] else "any"
        elif feature['selector'].startswith("single"):
            if feature['type'] in instance['features'] and len(instance['features'][feature['type']]) != 1:
                print("WARNING: Single feature provided multiple options...")
            choice = "any"
            if "-" in feature['selector']:
                choice = feature['selector'].split('-')[1]
            featureInstance = instance['features'][feature['type']][0] if feature['type'] in instance['features'] else choice
        elif feature['selector'].startswith("specific"):
            selectedElement = int(feature['selector'].split("-")[1])
            if feature['type'] in instance['features'] and len(instance['features'][feature['type']]) > selectedElement:
                featureInstance = instance['features'][feature['type']][selectedElement]
            else:
                continue
        elif feature['selector'] == "random":
            random.shuffle(instance['features'][feature['type']])
            if instance['features'][feature['type']]:
                featureInstance = instance['features'][feature['type']].pop() if feature['type'] in instance['features'] else "any"
            else:
                continue
        else:
            print("WARNING: Selector Not Recognized....")
        
        # Choose Feature
        chosenLayer = None
        if featureInstance == "any":
            chosenLayer = random.choice(featureOptions.list_children())
            newFeatureLayer = chosenLayer.copy()
        elif featureInstance.startswith("any-include:"):
            includedFeature = [f for f in featureOptions.list_children() if re.match(featureInstance.split(':')[1],  f.get_name()) or featureInstance.split(':')[1] in f.get_name()]
            if not includedFeature:
                print(f"WARNING: any selector returned not results [{featureInstance.split(':')[1]}]... defaulting to any")
                includedFeature = featureOptions.list_children()
            chosenLayer = random.choice(includedFeature)
            newFeatureLayer = chosenLayer.copy()
        elif featureInstance.startswith("any-exclude:"):   
            excludedFeature = [f for f in featureOptions.list_children() if not re.match(featureInstance.split(':')[1],  f.get_name()) or featureInstance.split(':')[1] not in f.get_name()]
            if not includedFeature:
                print(f"WARNING: any selector returned not results [{featureInstance.split(':')[1]}]... defaulting to any")
                excludedFeature = featureOptions.list_children()
            chosenLayer = random.choice(excludedFeature)
            newFeatureLayer = chosenLayer.copy()
        else:
            requestedLayerName = f"{featureInstance}[{game}-{feature['type']}]"
            if not image.get_layer_by_name(requestedLayerName):
                multipleOptionsRegex = re.compile(f"{featureInstance} [0-9]+[\[]{game}-{feature['type']}[\]]")
                missingOptions = [l for l in image.get_layer_by_name(f"{feature['type']}[{game}]").list_children() if multipleOptionsRegex.match(l.get_name())]
                if missingOptions:
                    chosenLayer = random.choice(missingOptions)
                    newFeatureLayer = chosenLayer.copy()
                    layerEnderStr = f"[{game}-{feature['type']}]"
                    print(f"\t\t\tChose '{chosenLayer.get_name().replace(layerEnderStr, '')}' from options: [{', '.join([l.get_name().replace(layerEnderStr, '') for l in missingOptions])}]")
                else:
                    print(f"WARNING: Layer '{requestedLayerName}' doesn't exist... skipping.")
                    continue
            else:
                chosenLayer = image.get_layer_by_name(f"{featureInstance}[{game}-{feature['type']}]")
                newFeatureLayer = chosenLayer.copy()
        featureGroup.set_name(feature['type']+"-"+featureInstance)
        newFeatureLayer.set_visible(True)
        newFeatureLayer.set_name(f"{game}-{feature['type']}-{feature['id']}")
        if feature['z_index'] == 'top':
            image.insert_layer(featureGroup, featuresGroupTop, 0)
        elif feature['z_index'] == 'middle':
            image.insert_layer(featureGroup, featuresGroupMiddle, 0)
        elif feature['z_index'] == 'bottom':
            image.insert_layer(featureGroup, featuresGroupBottom, 0)
        i = 1
        while True:
            chosenLayerSegment = re.sub(r'^([^[]*)([^]]*])$', rf'\1({str(i)})\2', chosenLayer.get_name())
            if image.get_layer_by_name(chosenLayerSegment):
                print(f"\t\tFound Segment: {chosenLayerSegment}")
                segmentLayer = image.get_layer_by_name(chosenLayerSegment).copy()
                image.insert_layer(segmentLayer, featureGroup, len(featureGroup.list_children()))
                if 'scale_algo' in feature:
                    if feature['scale_algo'] == 'pixel':
                        # INTERPOLATION-NONE (0)
                        Gimp.context_set_interpolation(0)
                    elif feature['scale_algo'] == 'smooth':
                        # INTERPOLATION-NOHALO (3)
                        Gimp.context_set_interpolation(3)
                else:
                    # scale image => INTERPOLATION-NOHALO (3)
                    Gimp.context_set_interpolation(3)
                segmentLayer.transform_2d(0,0, # Source
                                         feature['scale'],feature['scale'], # Scale
                                         feature['rotate']*math.pi/180,   # Angle
                                         0,0) # Dest
                segmentLayer.set_offsets(feature['x_offset'], feature['y_offset'])
                i += 1
            else:
                break
        
        image.insert_layer(newFeatureLayer, featureGroup, 0)
        if 'scale_algo' in feature:
            if feature['scale_algo'] == 'pixel':
                # INTERPOLATION-NONE (0)
                Gimp.context_set_interpolation(0)
            elif feature['scale_algo'] == 'smooth':
                # INTERPOLATION-NOHALO (3)
                Gimp.context_set_interpolation(3)
        else:
            # scale image => INTERPOLATION-NOHALO (3)
            Gimp.context_set_interpolation(3)
        newFeatureLayer.transform_2d(0,0, # Source
                                     feature['scale'],feature['scale'], # Scale
                                     feature['rotate']*math.pi/180,   # Angle
                                     0,0) # Dest
        newFeatureLayer.set_offsets(feature['x_offset'], feature['y_offset'])
        for effect in feature['effects']:
            if effect['effect_name'] == 'flip':
                (offsetX, offsetY, width, height) = (newFeatureLayer.get_offsets().offset_x,
                                                     newFeatureLayer.get_offsets().offset_y,
                                                     newFeatureLayer.get_width(),
                                                     newFeatureLayer.get_height())
                if effect["axis"] == "horizontal":
                    transformResult = newFeatureLayer.transform_flip(offsetX+width/2, 0, offsetX+width/2, 720)    
                elif effect["axis"] == "vertical":
                    transformResult = newFeatureLayer.transform_flip(0, offsetY+height/2, 1280, offsetY+height/2)
            if effect['effect_name'] == 'shadow':
                createDropShadow(newFeatureLayer, effect['x-offset'], effect['y-offset'], effect['blur'], effect['shrink'], "000000" if not effect['color'] else effect['color'])
        featureGroup.set_expanded(False)
    setVisibleAll(videoThumbGroup)
    epLayer.set_expanded(False)
    borderGroup.set_expanded(False)
    videoThumbGroup.set_expanded(False)

# Create Drop Shadow For Layer
def createDropShadow(layer, offset_x, offset_y, blurRadius, shrink, color):
    image = Gimp.list_images()[0]
    # Get Parent & Position
    parent = layer.get_parent()
    childPosition = 0
    for i, child in enumerate(parent.list_children()):
        if child.get_name() == layer.get_name():
            childPosition = i
            break
    # Copy & Resize Layer
    tempLayer = layer.copy()
    tempLayer.set_visible(True)
    image.insert_layer(tempLayer, parent, childPosition+1)
    tempLayer.resize_to_image_size()
    # Get Selection
    Gimp.context_set_sample_transparent(True)
    transparent = Gegl.Color()
    transparent.set_rgba(0.0, 0.0, 0.0, 0.0)
    image.get_selection().none(image)
    image.select_color(0, tempLayer, transparent)
    image.get_selection().invert(image)
    image.get_selection().shrink(image, shrink)
    # image.get_selection().feather(image, blurRadius)
    # Remove Temp Layer
    image.remove_layer(tempLayer)
    # Create Shadow Layer
    dropShadowLayer = image.get_layer_by_name('empty_layer').copy()
    dropShadowLayer.set_name("shadow of "+layer.get_name())
    dropShadowLayer.set_visible(True)
    # Fill Selection
    shadowColor = parseHex(color)
    Gimp.context_set_foreground(shadowColor)
    image.insert_layer(dropShadowLayer, parent, childPosition+1)
    dropShadowLayer.edit_fill(Gimp.FillType.FOREGROUND)
    image.get_selection().none(image)
    # Blur Shadow
    procedure = Gimp.get_pdb().lookup_procedure('plug-in-gauss')
    config = procedure.create_config()
    config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
    config.set_property('image', image)
    config.set_property('drawable', dropShadowLayer)
    config.set_property('horizontal', blurRadius)
    config.set_property('vertical', blurRadius)
    config.set_property('method', 0)
    result = procedure.run(config)
    transformResult = dropShadowLayer.transform_2d(0,0,1,1,0,offset_x,offset_y)
    cropToContent(image, dropShadowLayer)

# Crop to Content                      
def cropToContent(imageIn, layerIn):
    imageIn.set_selected_layers([layerIn])
    visible = layerIn.get_visible()
    layerIn.set_visible(True)
    # layerIn.resize_to_image_size()
    procedure = Gimp.get_pdb().lookup_procedure('plug-in-autocrop-layer')
    config = procedure.create_config()
    config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
    config.set_property('image', imageIn)
    config.set_property('drawable', layerIn)
    result = procedure.run(config)
    layerIn.set_visible(visible)
    return result.index(0)

def setVisibleAll(layerGroup):
    for layer in layerGroup.list_children():
        if layer.is_group():
            setVisibleAll(layer)
            layer.set_visible(True)
        else:
            layer.set_visible(True)

def parseHex(hex):
    color = Gegl.Color()
    
    rgb = tuple(int(hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    color.set_rgba((float(rgb[0])/255.0)**2.25132, (float(rgb[1])/255.0)**2.25132, (float(rgb[2])/255.0)**2.25132, 1.0)
    
    return color

# Utility Functions
def getDataFromSheet(thumbsWorksheet):
    print('\tPulling thumbs from sheet...')

    headers = thumbsWorksheet.get_values(start='A3', end='Q3', returnas='matrix')[0]
    thumbRows = thumbsWorksheet.get_values(start='A5', end='Q50', returnas='matrix')

    thumbsToBuild = []
    for row in thumbRows:
        if row[0] != '' and row[0] != 'Filename':
            thumbsToBuild.append({ x.lower(): y for (x,y) in zip(headers, row) if y != ''})

    return thumbsToBuild

def run(procedure, run_mode, image, n_layers, layers, args, CONFIG):
    print("----- GENERATE THUMBNAILS -----")
    Gimp.context_push()
    image.undo_group_start()

    # Body of the Run Method
    print('\tLoading Structure JSON...')
    structure = json.load(open(os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['structure'])))
    print('\tConnecting to gSheets...')
    gc = pygsheets.authorize(service_file=CONFIG['AUTHENTICATION']['serviceToken'])
    sheet = gc.open_by_key(CONFIG['GENERAL']['spreadsheetId'])

    mainWorksheet = sheet.worksheet_by_title(CONFIG['SHEETS']['main'])
    thumbsWorksheet = sheet.worksheet_by_title(CONFIG['SHEETS']['thumbnails'])

    thumbsToBuild = [x for x in getDataFromSheet(thumbsWorksheet) if 'json' in x and x['json']]
    
    for thumb in thumbsToBuild:
        buildThumbnail(json.loads(thumb['json']), structure)
    # End Body of the Run Method

    Gimp.displays_flush()
    image.undo_group_end()
    Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class ThumbnailerGenerate(Gimp.PlugIn):
    def __init__(self):
        print('ThumbnailerGenerate: Parsing config file...')
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('thumbnailer.ini')
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "plug-in-thumbnailer-generate-python" ]
    
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_create_procedure(self, name):
        procedure = None
        if name == "plug-in-thumbnailer-generate-python":
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                run, self.CONFIG)

            procedure.set_image_types("*")
            procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
            procedure.set_documentation (
                N_("Template + Google Sheet => Thumbnail"),
                N_("Use metadata from Google Sheets to compose Thumbnails from layers in the Template."),
                name)
            procedure.set_menu_label(N_("Generate Thumbnails"))
            procedure.set_attribution("Alden Roberts",
                                      "(c) GPL V3.0 or later",
                                      "2024")
            procedure.add_menu_path("<Image>/Filters/Thumbnailer/")

        return procedure

Gimp.main(ThumbnailerGenerate.__gtype__, sys.argv)
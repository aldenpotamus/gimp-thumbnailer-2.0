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
Thumbnailer - Clean Up
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

import configparser
import sys
from datetime import datetime

sys.stderr = open('C:/log/thumbnailer-output-'+str(datetime.now())[:10].replace(r" ", ".").replace(":", ".")+'.txt', 'a')
sys.stdout=sys.stderr # So that they both go to the same file

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

######### CLEAN LAYER NAMES #########
import re
def cleanLayerNames(image):
    gameAssetsGroup = image.get_layer_by_name('Game Assets')
    for gameLayer in gameAssetsGroup.list_children():
        if gameLayer:
            gameLayer.set_name(gameLayer.get_name().lower())
            gameName = gameLayer.get_name()
            for featTypeLayer in gameLayer.list_children():
                featTypeLayer.set_name(featTypeLayer.get_name().lower())
                if featTypeLayer:
                    typeName = re.sub("\[[^]]+\]", "", featTypeLayer.get_name()).lower()
                    featTypeUnique = f'[{gameName.lower()}]'
                    if featTypeUnique.lower() not in featTypeLayer.get_name().lower():
                        # Clean Filename Stuff
                        typeName = re.sub(" #[0-9]+$", "", re.sub(".png", "", re.sub("_", " ", typeName))).lower()
                        featTypeLayer.set_name(typeName+featTypeUnique)
                    for featureLayer in featTypeLayer.list_children():
                        featName = re.sub("\[[^]]+\]", "", featureLayer.get_name()).lower()
                        featureUnique = f"[{gameName.lower()}-{typeName.lower()}]"
                        if featureUnique not in featName:
                            # Clean Filename Stuff
                            featName = re.sub(" #[0-9]+$", "", re.sub(".png", "", re.sub("_", " ", featName))).lower()
                            featureLayer.set_name(featName+featureUnique)

######### LAYER SIZE TO PARENT #########
# Recursive Get Child Leaf Nodes
def getChildLeafNodes(layerGroup, result):
    for layer in layerGroup.list_children():
        if layer.is_group():
            getChildLeafNodes(layer, result)
        else:
            result.append(layer)

# Crop layer to the Size of its Contents
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

# Correct Expansion and Visibility Issues With Assets
def fixVisAndExpand(layerGroup):
    for layer in layerGroup.list_children():
        if layer.is_group():
            fixVisAndExpand(layer)
            layer.set_expanded(False)
            layer.set_visible(True)
        else:
            layer.set_visible(False)

def layerSizeToParent(image):
    gameAssetsGroup = image.get_layer_by_name('Game Assets')
    for gameLayer in gameAssetsGroup.list_children():
        for featTypeLayer in gameLayer.list_children():
            if featTypeLayer:
                (xMin, yMin) = (100000, 100000)
                (xMax, yMax) = (-100000, -100000)
                featureLayers = []
                getChildLeafNodes(featTypeLayer, featureLayers)
                
                normalized = all([l.get_offsets().offset_x == featureLayers[0].get_offsets().offset_x and
                                  l.get_offsets().offset_y == featureLayers[0].get_offsets().offset_y and
                                  l.get_width() == featureLayers[0].get_width() and
                                  l.get_height() == featureLayers[0].get_height() for 
                                  l in featureLayers])
                
                if normalized:
                    print(f"\tSkipping... no normalization needed on layer group [{featTypeLayer.get_name()}]")
                    continue
                
                for featureLayer in featureLayers:
                    if featureLayer:
                        cropToContent(image, featureLayer)
                        xMin = min(xMin, featureLayer.get_offsets().offset_x)
                        yMin = min(yMin, featureLayer.get_offsets().offset_y)
                        xMax = max(xMax, featureLayer.get_offsets().offset_x + featureLayer.get_width())
                        yMax = max(yMax, featureLayer.get_offsets().offset_y + featureLayer.get_height())
                
                print(f'\tTotal is min=({xMin},{yMin}) max=({xMax},{yMax})')
                for featureLayer in featureLayers:
                    if featureLayer:
                        x = featureLayer.get_offsets().offset_x
                        y = featureLayer.get_offsets().offset_y
                        if x != xMin or y != yMin or featureLayer.get_width() != xMax - xMin or featureLayer.get_height() != yMax-yMin:
                            print(f"\t\tResize on Layer: {featureLayer.get_name()} to dim=({xMax-xMin},{yMax-yMin}) and offset=({x-xMin},{y-yMin})")
                            featureLayer.resize(xMax-xMin, yMax-yMin, x-xMin, y-yMin)
    fixVisAndExpand(gameAssetsGroup)

def run(procedure, run_mode, image, n_layers, layers, args, CONFIG):
    print("----- CLEAN UP -----")
    Gimp.context_push()
    image.undo_group_start()

    # Body of the Run Method
    print("\tCleaning up layer names...")
    cleanLayerNames(image)
    
    print("\tHomogenizing layer sizes...")
    layerSizeToParent(image)

    Gimp.displays_flush()
    image.undo_group_end()
    Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class ThumbnailerCleanup(Gimp.PlugIn):
    def __init__(self):
        print('ThumbnailerCleanup: Parsing config file...')
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('thumbnailer.ini')
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "plug-in-thumbnailer-clear-up-python" ]
    
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_create_procedure(self, name):
        procedure = None
        if name == "plug-in-thumbnailer-clear-up-python":
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                run, self.CONFIG)

            procedure.set_image_types("*")
            procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
            procedure.set_documentation (
                N_("Cleans Up Template File"),
                N_("Cleanup Layer Names & Layer Sizes to be Consistent"),
                name)
            procedure.set_menu_label(N_("Clean-up Template"))
            procedure.set_attribution("Alden Roberts",
                                      "(c) GPL V3.0 or later",
                                      "2024")
            procedure.add_menu_path("<Image>/Filters/Thumbnailer/Support/")

        return procedure

Gimp.main(ThumbnailerCleanup.__gtype__, sys.argv)

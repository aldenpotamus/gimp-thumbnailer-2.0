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

import configparser
from datetime import datetime
import json
import os
import re
import shutil
import sys
import math

sys.stderr = open('C:/log/thumbnailer-output.txt','a')
sys.stdout=sys.stderr # So that they both go to the same file

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

# Get Layer Offset For Layers
def getLayerStructure(image, layers):
    game = None
    ids = set()
    result = []
    for l in layers:
        if l.is_text_layer():
            type = "text"
            font = l.get_font().get_name()
            fontSize = l.get_font_size()[0]
        else:
            layerLocator = re.sub(r'[^\[]*\[([^\]]*)\].*', r'\1', l.get_name())
            gameInner, type = layerLocator.split('-')
            if game and game != gameInner:
                print("\tError: composed structure contains items from multiple games.")
                return None
            game = gameInner

        scale = 1
        if image.get_layer_by_name(f'{type}[{game}]'):
            baselineLayer = image.get_layer_by_name(f'{type}[{game}]').list_children()[0]
            scale = l.get_width() / baselineLayer.get_width()

            a = ogWidth = baselineLayer.get_width()
            b = ogHeight = baselineLayer.get_height()
            c = afterWidth = l.get_width()
            r1 = r2 = None
            try:
                r1 = math.degrees(math.acos((float(a**2 * c) + math.sqrt(a**4 * b**2 + a**2 * b**4 - a**2 * b**2 * c**2))/float(a**2 + b**2) / float(a)))
            except ValueError:
                r1 = None
            try:
                r2 = math.degrees(math.acos((float(a**2 * c) - math.sqrt(a**4 * b**2 + a**2 * b**4 - a**2 * b**2 * c**2))/float(a**2 + b**2) / float(a)))
            except:
                r2 = None

        i = 0
        while f'{type}{i}' in ids:
            i += 1
        ids.add(f'{type}{i}')
        result.append({
                        "id": f'{type}{i}',
                        "type": type,
                        "selector": "TBD:ordered,single,random,specific-N,single-NAME",
                        "scale": f'{scale},1',
                        "rotate": f'{r1 if r1 else 0.0:.2f},{r2 if r2 else 0.0:.2f},-{r1 if r1 else 0.0:.2f},-{r2 if r2 else 0.0:.2f},0',
                        "x_offset": l.get_offsets().offset_x,
                        "y_offset": l.get_offsets().offset_y,
                        "z_index": "TBD:bottom,middle,top",
                        "effects": []
                      } | ({
                        "font": font,
                        "font_size": fontSize
                      } if type == "text" else {}))

    return result

# Recursive Get Child Leaf Nodes
def getChildLeafNodes(layerGroup, result):
    for layer in layerGroup.list_children():
        if layer.is_group():
            getChildLeafNodes(layer, result)
        else:
            result.append(layer)

def divineStucture(image, layer):
    features = []
    getChildLeafNodes(layer, features)
    return (layer.get_name(), getLayerStructure(image, features))
    

def run(procedure, run_mode, image, n_layers, layers, args, CONFIG):
    print("----- EXTRACT STRUCTURE -----")
    Gimp.context_push()
    image.undo_group_start()

    # Body of the Run Method
    if n_layers == 1:
        key, structureAddition = divineStucture(image, layers[0])

        print('\tBacking Up Current Structure...')
        shutil.copyfile(os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['structure']),
                        os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['structure']+".bak."+str(datetime.now())[:19].replace(r" ", ".").replace(":", ".")))
        with open(os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['structure'])) as structureFile:
            structure = json.load(structureFile)

        if key in structure:
            print(f'\tOverwriting current structure for {key} game.  If this is incorrect, check .bak')
        structure[key] = structureAddition
        
        with open(os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['structure']), 'w') as structureFile:
            json.dump(structure, structureFile, indent=2)
    else:
        print("\tToo many layers selected... skipping extraction.")

    # End Body of the Run Method

    Gimp.displays_flush()
    image.undo_group_end()
    Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class ThumbnailerStructureExport(Gimp.PlugIn):
    def __init__(self):
        print('ThumbnailerStructureExport: Parsing config file...')
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('thumbnailer.ini')
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "plug-in-thumbnailer-extract-structure-python" ]
    
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_create_procedure(self, name):
        procedure = None
        if name == "plug-in-thumbnailer-extract-structure-python":
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                run, self.CONFIG)

            procedure.set_image_types("*")
            procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
            procedure.set_documentation (
                N_("Generate a Structure JSON File From Template"),
                N_("Uses a set of layers composed by the user to generate a structure JSON payload."),
                name)
            procedure.set_menu_label(N_("Extract Structure"))
            procedure.set_attribution("Alden Roberts",
                                      "(c) GPL V3.0 or later",
                                      "2024")
            procedure.add_menu_path("<Image>/Filters/Thumbnailer/")

        return procedure

Gimp.main(ThumbnailerStructureExport.__gtype__, sys.argv)
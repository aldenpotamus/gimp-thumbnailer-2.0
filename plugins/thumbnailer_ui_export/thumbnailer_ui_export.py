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
import os
import sys
import shutil

from datetime import datetime

sys.stderr = open('C:/log/thumbnailer-output-'+str(datetime.now())[:10].replace(r" ", ".").replace(":", ".")+'.txt', 'a')
sys.stdout=sys.stderr # So that they both go to the same file

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

import re
import json
def extractInstanceData(image, instanceData):
    gameAssetsGroup = image.get_layer_by_name('Game Assets')
    allFeatures = instanceData['all']
    del instanceData['all']
    for game in gameAssetsGroup.list_children():
        gameName = game.get_name()
        tmpFeatures = allFeatures.copy()
        tmpFeatures.update(instanceData[gameName]['features'])
        instanceData[gameName]['features'] = tmpFeatures
        for featureGroup in [g for g in game.list_children() if g.is_group()]:
            featureGroupName = re.sub(r'\[[^]]*\]', "", featureGroup.get_name())
            if featureGroupName not in instanceData[gameName]['features']:
                continue
            if 'options' not in instanceData[gameName]['features'][featureGroupName]:
                instanceData[gameName]['features'][featureGroupName]['options'] = set()
                for feature in featureGroup.list_children():
                    featureName = re.sub(r'\[[^]]*\]', "", feature.get_name())
                    featureName = re.sub(r'(?:[\(][0-9]*[\)])', '', featureName)
                    featureName = re.sub(r' [0-9]+', "", featureName)
                    instanceData[gameName]['features'][featureGroupName]['options'].add(featureName)
            instanceData[gameName]['features'][featureGroupName]['options'] = sorted(instanceData[gameName]['features'][featureGroupName]['options'])
            if 'options_additional' in instanceData[gameName]['features'][featureGroupName]:
                for addOp in reversed(instanceData[gameName]['features'][featureGroupName]['options_additional']):
                    instanceData[gameName]['features'][featureGroupName]['options'].insert(0, addOp)
                del instanceData[gameName]['features'][featureGroupName]['options_additional']
    return instanceData

def run(procedure, run_mode, image, n_layers, layers, args, CONFIG):
    print("----- EXPORT UI JSON -----")
    Gimp.context_push()
    image.undo_group_start()

    # Body of the Run Method
    print("\tLoading json files...")
    base_all = json.load(open(os.path.join(CONFIG['PROJ']['dir'], 'json', CONFIG['JSON']['base_all'])))
    base_game = json.load(open(os.path.join(CONFIG['PROJ']['dir'], 'json', CONFIG['JSON']['base_game'])))
    baseJSON = base_all | base_game

    print("\tPulling instance data from XFC and merging...")
    mergedDict = extractInstanceData(image, baseJSON)
    
    print("\tBacking up current merged.json file...")
    shutil.copyfile(os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['merged']),
                    os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['merged']+".bak."+str(datetime.now())[:19].replace(r" ", ".").replace(":", ".")))
    
    print("\tWriting merged data to file...")
    with open(os.path.join(CONFIG['JSON']['gen_dir'], CONFIG['JSON']['merged']), 'w') as f:
        json.dump(mergedDict, f, indent=2)
    # End Body of the Run Method

    Gimp.displays_flush()
    image.undo_group_end()
    Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class ThumbnailerUIExport(Gimp.PlugIn):
    def __init__(self):
        print('ThumbnailerUIExport: Parsing config file...')
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('thumbnailer.ini')
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "plug-in-thumbnailer-export-ui-json-python" ]
    
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_create_procedure(self, name):
        procedure = None
        if name == "plug-in-thumbnailer-export-ui-json-python":
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                run, self.CONFIG)

            procedure.set_image_types("*")
            procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
            procedure.set_documentation (
                N_("Exports JSON File That Drives The Web UI"),
                N_("Exports layer data (name & location) into a JSON file that drives the web UI."),
                name)
            procedure.set_menu_label(N_("Export UI JSON"))
            procedure.set_attribution("Alden Roberts",
                                      "(c) GPL V3.0 or later",
                                      "2024")
            procedure.add_menu_path("<Image>/Filters/Thumbnailer/Support/")

        return procedure

Gimp.main(ThumbnailerUIExport.__gtype__, sys.argv)
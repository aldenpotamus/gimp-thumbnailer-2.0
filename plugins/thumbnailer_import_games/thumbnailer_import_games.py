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
Thumbnailer - Import Games
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
import pygsheets

from datetime import datetime

sys.stderr = open('C:/log/thumbnailer-output-'+str(datetime.now())[:10].replace(r" ", ".").replace(":", ".")+'.txt', 'a')
sys.stdout=sys.stderr # So that they both go to the same file

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

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
    print("----- IMPORT GAMES -----")
    
    print('\tConnecting to gSheets...')
    gc = pygsheets.authorize(service_file=CONFIG['AUTHENTICATION']['serviceToken'])
    sheet = gc.open_by_key(CONFIG['GENERAL']['spreadsheetId'])
    # mainWorksheet = sheet.worksheet_by_title(CONFIG['SHEETS']['main'])
    thumbsWorksheet = sheet.worksheet_by_title(CONFIG['SHEETS']['thumbnails'])
    thumbsToProcess = getDataFromSheet(thumbsWorksheet)

    games = {}
    for thumb in thumbsToProcess:
        if 'local_game' in thumb:
            games[thumb['local_game']] = True
        if 'game' in thumb:
            games[thumb['game']] = True

    gamesToMerge = [x.lower().replace(' ', '_')+'.xcf' for x in games.keys()]

    print(f'\tGames to merge in {gamesToMerge}')

    # Body of the Run Method
    print('\tCreating Image...')
    image = Gimp.Image.new(1280, 720, 0)
    Gimp.Display.new(image)
    
    Gimp.context_push()
    image.undo_group_start()

    print('\tCreating Needed Layer Groups...')
    gameAssets = Gimp.Layer.group_new(image)
    gameAssets.set_name('Game Assets')
    image.insert_layer(gameAssets, None, 0)

    generalLayerGroup = Gimp.Layer.group_new(image)
    generalLayerGroup.set_name('_General')
    image.insert_layer(generalLayerGroup, None, 0)

    generatedLayerGroup = Gimp.Layer.group_new(image)
    generatedLayerGroup.set_name('_Generated')
    image.insert_layer(generatedLayerGroup, None, 0)

    print('\tImporting Univeral Thumbnail Elements...')
    file = Gio.File.new_for_path(os.path.join(CONFIG['PROJ']['dir'], 'img', 'general.xcf'))
    layersToAdd = Gimp.file_load_layers(1, image, file)
    for layer in layersToAdd:
        image.insert_layer(layer, generalLayerGroup, 0)  
        generalLayerGroup.set_expanded(False) 
        layer.set_expanded(False)

    for gameXCF in gamesToMerge:
        file = Gio.File.new_for_path(os.path.join(CONFIG['PROJ']['dir'], 'img', gameXCF))
        layersToAdd = Gimp.file_load_layers(1, image, file)

        for layer in layersToAdd:
            image.insert_layer(layer, gameAssets, 0)
            # layer.set_name(layer.get_name().replace('_', ' ').replace('.xcf', ''))
            layer.set_expanded(False)
    
            gameLayer = layer.list_children()[0]
            image.reorder_item(gameLayer, gameAssets, 0)
            Gimp.Image.remove_layer(image, layer)
            Gimp.Layer.delete(layer)

            gameLayer.set_name(gameXCF.lower().replace('_', ' ').replace('.xcf', ''))
            gameLayer.set_expanded(False)

    Gimp.displays_flush()
    # End Body of the Run Method

    image.undo_group_end()
    Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class ThumbnailerImportGames(Gimp.PlugIn):
    def __init__(self):
        print('ThumbnailerImportGames: Parsing config file...')
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('thumbnailer.ini')
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "plug-in-thumbnailer-import-games-python" ]
    
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_create_procedure(self, name):
        procedure = None
        if name == "plug-in-thumbnailer-import-games-python":
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                run, self.CONFIG)

            procedure.set_image_types("*")
            procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)

            procedure.set_documentation (
                N_("Imports Games Data into Thumbnail File"),
                N_("Each game is stored as a seperate file, this merged those files for processing."),
                name)
            procedure.set_menu_label(N_("1. Import Games"))
            procedure.set_attribution("Alden Roberts",
                                      "(c) GPL V3.0 or later",
                                      "2024")
            procedure.add_menu_path("<Image>/Filters/Thumbnailer/")

        return procedure

Gimp.main(ThumbnailerImportGames.__gtype__, sys.argv)
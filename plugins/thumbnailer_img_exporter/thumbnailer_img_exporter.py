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
Thumbnailer - Image Exporter
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

import os
import configparser
import sys
import pygsheets

from datetime import datetime

sys.stderr = open('C:/log/thumbnailer-output-'+str(datetime.now())[:10].replace(r" ", ".").replace(":", ".")+'.txt', 'a')
sys.stdout=sys.stderr # So that they both go to the same file

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

def exportImage(image, thumbToExport, CONFIG):
    print(f"\t\tExporting image {thumbToExport['videoid']}...")
    new_image = image.duplicate()
    for l in new_image.get_layer_by_name('_Generated').list_children():
        l.set_visible(l.get_name() == thumbToExport['videoid'])
    layer = new_image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)

    outputPath = os.path.join(CONFIG['GENERAL']['outputDir'], thumbToExport['filename']+'.png')   
    file = Gio.File.new_for_path(outputPath)
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, new_image, [layer], file)
    new_image.delete()

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
    print("----- EXPORT IMAGES -----")

    # Body of the Run Method
    print('\tConnecting to gSheets...')
    gc = pygsheets.authorize(service_file=CONFIG['AUTHENTICATION']['serviceToken'])
    sheet = gc.open_by_key(CONFIG['GENERAL']['spreadsheetId'])
    thumbsWorksheet = sheet.worksheet_by_title(CONFIG['SHEETS']['thumbnails'])

    print('\tPulling thumbs to export...')
    thumbsToExport = [x for x in getDataFromSheet(thumbsWorksheet) if 'json' in x and x['json']]
    
    print('\tExporting thumbs...')
    for thumb in thumbsToExport:
        exportImage(image, thumb, CONFIG)

    Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class ThumbnailerImgExporter(Gimp.PlugIn):
    def __init__(self):
        print('ThumbnailerImgExporter: Parsing config file...')
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('thumbnailer.ini')
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "plug-in-thumbnailer-img-exporter-python" ]
    
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_create_procedure(self, name):
        procedure = None
        if name == "plug-in-thumbnailer-img-exporter-python":
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                run, self.CONFIG)

            procedure.set_image_types("*")
            procedure.set_sensitivity_mask (Gimp.ProcedureSensitivityMask.DRAWABLE |
                                            Gimp.ProcedureSensitivityMask.DRAWABLES)
            
            procedure.set_documentation (
                N_("Cleans Up Template File"),
                N_("Cleanup Layer Names & Layer Sizes to be Consistent"),
                name)
            procedure.set_menu_label(N_("3. Export Thumbnails"))
            procedure.set_attribution("Alden Roberts",
                                      "(c) GPL V3.0 or later",
                                      "2024")
            procedure.add_menu_path("<Image>/Filters/Thumbnailer/")

        return procedure

Gimp.main(ThumbnailerImgExporter.__gtype__, sys.argv)

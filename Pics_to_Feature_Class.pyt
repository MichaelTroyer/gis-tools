# -*- coding: utf-8 -*-
"""
Created on Fri Sep 14 09:27:37 2018

@author: mtroyer
"""

import os
import csv
import PIL.Image
import PIL.ExifTags

import arcpy


### Helper functions

def convert_to_degress(value):
    """
    Convert exif GPS coordinate tuples to decimal degress
    """
    d = float(value[0][0]) / float(value[0][1])
    m = float(value[1][0]) / float(value[1][1])
    s = float(value[2][0]) / float(value[2][1])
    return d + (m / 60.0) + (s / 3600.0)


def getCoords(filepath):
    """
    Get lat/long gps coordinates from a photo.
    """
    img = PIL.Image.open(filepath)

    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in img._getexif().items()
        if k in PIL.ExifTags.TAGS
        }
    
    gpsinfo = {}
    for key in exif['GPSInfo'].keys():
        decode = PIL.ExifTags.GPSTAGS.get(key,key)
        gpsinfo[decode] = exif['GPSInfo'][key]

    latitude = gpsinfo['GPSLatitude']
    latitude_ref = gpsinfo['GPSLatitudeRef']
    lat_value = convert_to_degress(latitude)
    if latitude_ref == u'S':
        lat_value = -lat_value
                
    longitude = gpsinfo['GPSLongitude']
    longitude_ref = gpsinfo['GPSLongitudeRef']
    lon_value = convert_to_degress(longitude)
    if longitude_ref == 'W':
        lon_value = -lon_value

    return {'latitude': lat_value, 'longitude': lon_value}


def picsToCoordCSV(folder):
    pic_formats = ('.png', '.jpeg', '.jpg')
    
    pics = [f for f in os.listdir(folder) if os.path.splitext(f)[1] in pic_formats]
        
    coords = {}
    for pic in pics:
        try:
            coords[pic] = getCoords(os.path.join(folder, pic))
        except:
            arcpy.AddMessage('No GPS Data: [{}]'.format(pic))

    out_csv = os.path.join(folder, 'coords.csv')
    with open(out_csv, 'wb') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['name', 'path', 'latitude', 'longitude'])
        for name, c in coords.items():
            row = (name, os.path.join(folder, name), c['latitude'], c['longitude'])
            csvwriter.writerow(row)

    return out_csv


class Toolbox(object):
    def __init__(self):
        self.label = "Toolbox"
        self.alias = ""
        self.tools = [Pics_to_Feature_Class]


class Pics_to_Feature_Class(object):
    def __init__(self):
        self.label = "Pics_to_Feature_Class"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        # pic_folder_path, gdb_name, fc_name

        pic_folder_path = arcpy.Parameter(
            displayName="Pictures Folder",
            name="in_pictures",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
 
        gdb_name = arcpy.Parameter(
            displayName="Geodatabase Name",
            name="out_location",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Output")
 
        fc_name = arcpy.Parameter(
            displayName="Feature Class Name",
            name="featureclass_name",
            datatype="String",
            parameterType="Required",
            direction="Input")

        return [pic_folder_path, gdb_name, fc_name]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        try:

            folder_path, gdb_name, fc_name = [p.valueAsText for p in parameters]

            out_csv = picsToCoordCSV(folder_path)

            # Create gdb
            if not gdb_name.endswith('.gdb'):
                gdb_name += '.gdb'
            d, n = os.path.split(gdb_name)
            arcpy.CreateFileGDB_management(d, n, "10.0")

            # Create fc from xy pairs
            fc = os.path.join(gdb_name, fc_name)
            arcpy.MakeXYEventLayer_management(
                table=out_csv,
                in_x_field="longitude",
                in_y_field="latitude",
                out_layer="coords_Layer",
                )
            arcpy.CopyFeatures_management("coords_Layer", fc)

            # Add globals and enable attachments
            arcpy.AddGlobalIDs_management(fc)
            arcpy.EnableAttachments_management(fc)

            # Add Attachments
            arcpy.AddAttachments_management(fc, 'name', out_csv, 'name', 'path')

            return # Profit
        except:
            arcpy.AddError(str(traceback.format_exc()))


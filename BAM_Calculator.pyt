# -*- coding: utf-8 -*-

"""
Calculate BAM Figures for BLM CO

Calculates for each admin unit in param1:

Unit_Acres
Unit_Site_Count
Unit_Survey_Count
Unit_Survey_Acres
Unit_Class_III_Acres

BLM_Acres
BLM_Site_Count
BLM_Survey_Count
BLM_Survey_Acres
BLM_Class_III_Acres

Unit_Sites_per_Unit_Acre
BLM_Sites_per_BLM_Acre
Unit_Sites_per_Unit_ClassIII_Acre
BLM_Sites_per_BLM_ClassIII_Acre
Unit_ClassIII_Survey_Coverage
BLM_ClassIII_Survey_Coverage
                  

Michael D. Troyer

mtroyer@blm.gov
719-269-8587
"""


from __future__ import division

import os
import re
import csv
import sys
import arcpy
import datetime
import traceback

from collections import defaultdict

arcpy.env.addOutputsToMap = False
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "BAM_Calculator"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "BAM_Calculator"
        self.description = ""
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        #Input Target Shapefile
        param0=arcpy.Parameter(
            displayName="Input BLM CO Cultural Admin Boundaries",
            name="In_Admin",
            datatype="Feature Class",
            parameterType="Required",
            direction="Input")

        param1=arcpy.Parameter(
            displayName="Input BLM CO Surface Management",
            name="In_Lands",
            datatype="Layer",
            parameterType="Required",
            direction="Input")
        
        param2=arcpy.Parameter(
            displayName="Input BLM CO Sites Feature Class",
            name="In_Sites",
            datatype="Layer",
            parameterType="Required",
            direction="Input")
        
        param3=arcpy.Parameter(
            displayName="Input BLM CO Surveys Feature Class",
            name="In_Survs",
            datatype="Layer",
            parameterType="Required",
            direction="Input")

        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        if not params[0].altered:
            params[0].value = r'T:\CO\GIS\gistools\tools\Cultural\BAM_Calculator\BAM_Data.gdb\Boundaries\BLM_CO_Cultural_Admin_Boundaries'
        if not params[1].altered:
            params[1].value = r'T:\ReferenceState\CO\CorporateData\lands\Land Ownership (No Outline).lyr'
        if not params[2].altered:
            params[2].value = r'T:\ReferenceState\CO\CorporateData\data_sharing\Sites.lyr'
        if not params[3].altered:
            params[3].value = r'T:\ReferenceState\CO\CorporateData\data_sharing\Survey.lyr'
        return

    def updateMessages(self, params):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, params, messages):
        """The source code of the tool."""

        date_time_stamp = re.sub('[^0-9]', '', str(datetime.datetime.now())[:10])
        database_path = r'T:\CO\GIS\gistools\tools\Cultural\BAM_Calculator\BAM_Data.gdb'
        output_csv = r'T:\CO\GIS\gistools\tools\Cultural\BAM_Calculator\BAM_Figures_{}.csv'.format(date_time_stamp)
        
        admin = arcpy.MakeFeatureLayer_management(params[0].value, "in_memory\\admin")
        lands = params[1].value
        sites = params[2].value
        survs = params[3].value

        # For iteration
        admin_units = set([row[0] for row in arcpy.da.SearchCursor(admin, "Admin_ID")])
        # For key: full name translations
        admin_dict = {row[1]: row[0] for row in arcpy.da.SearchCursor(admin, ["label", "Admin_ID"])}

        # Main data structure
        results = []

        for unit in admin_units:
            arcpy.AddMessage('[+] Procesing Unit: {}'.format(unit))
            
            # get the unit lands,  area calculations, and site count
            where = "Admin_ID = '{}'".format(unit)
            arcpy.SelectLayerByAttribute_management(admin, 'NEW_SELECTION', where)
            unit_lands = arcpy.Clip_analysis(lands, admin, os.path.join(database_path, 'tmp_Lands', unit + '_lands'))
            unit_lands = arcpy.MakeFeatureLayer_management(unit_lands, "in_memory\\unit_lands")
            # Unit acres
            unt_acrs = sum([row[0] for row in arcpy.da.SearchCursor(unit_lands, 'Shape_Area')]) / 4046.86
            # Get unit site count
            arcpy.SelectLayerByLocation_management(sites, "INTERSECT", unit_lands, selection_type="NEW_SELECTION")
            unt_site_cnt = int(arcpy.GetCount_management(sites).getOutput(0))
            
            # Get BLM lands,  area calculations, and site count
            arcpy.SelectLayerByAttribute_management(unit_lands, 'NEW_SELECTION', "adm_manage = 'BLM'")
            blm_lands = arcpy.CopyFeatures_management(unit_lands, os.path.join(database_path, 'tmp_Lands', unit + '_lands_blm'))
            blm_lands = arcpy.MakeFeatureLayer_management(blm_lands, "in_memory\\blm_lands")
            # BLM acres
            blm_acrs = sum([row[0] for row in arcpy.da.SearchCursor(blm_lands, 'Shape_Area')]) / 4046.86
            # Get blm site count
            arcpy.SelectLayerByLocation_management(sites, "INTERSECT", blm_lands, selection_type="NEW_SELECTION")
            blm_site_cnt = int(arcpy.GetCount_management(sites).getOutput(0))

            # Get unit survey acreage and count
            unit_survs = arcpy.Clip_analysis(survs, admin, os.path.join(database_path, 'tmp_Surveys', unit + '_surveys'))
            unt_surv_acrs = sum([row[0] for row in arcpy.da.SearchCursor(unit_survs, 'Shape_Area')]) / 4046.86
            unt_surv_cnt = int(arcpy.GetCount_management(unit_survs).getOutput(0))
            
            # Get BLM survey acreage and count
            blm_survs = arcpy.Clip_analysis(survs, blm_lands, os.path.join(database_path, 'tmp_Surveys', unit + '_surveys_blm'))
            blm_surv_acrs = sum([row[0] for row in arcpy.da.SearchCursor(blm_survs, 'Shape_Area')]) / 4046.86
            blm_surv_cnt = int(arcpy.GetCount_management(blm_survs).getOutput(0))

            class_iii_methods = set((u'Historic Survey - CIII', u'Archaeology Survey - CIII', u'CLASS III'))
            # All individual survey method encodings
            '''u'RECONNAISSANCE SURVEY',
               u'Historic Survey - CIII',
               u'Archaeology Survey - CIII',
               u'RESURVEY',
               u'CLASS III',
               u'Paleontological Survey',
               u'Archaeology Survey - CII',
               u'CLASS II',
               u'Survey - Level Unspecified',
               u'Historic Survey - CII',
               u'Class II-Pred Model'
            '''
            
            # Only sum Class III acres
            # SHPO data is a weird string of methods. Split on delimiter and compare to Class III keywords set
            # [class_iii_methods]. If a set intersection between string of methods and keywords returns anything
            # other than en empty set, we've matched a keyword - add to sum. Checks for falseness of empty set.
            unt_int_acrs = sum([row[0] for row in arcpy.da.SearchCursor(unit_survs, ['Shape_Area', 'method'])
                               if (set(row[1].split('>')) & class_iii_methods)]) / 4046.86
            blm_int_acrs = sum([row[0] for row in arcpy.da.SearchCursor(blm_survs, ['Shape_Area', 'method'])
                               if (set(row[1].split('>')) & class_iii_methods)]) / 4046.86
            
            # Prep collected data for handoff
            payload = [admin_dict[unit],
                       # The unit data
                       round(unt_acrs, 0),
                       unt_site_cnt,
                       unt_surv_cnt,
                       round(unt_surv_acrs, 0),
                       round(unt_int_acrs, 0),
                       # BLM data
                       round(blm_acrs, 0),
                       blm_site_cnt,
                       blm_surv_cnt,
                       round(blm_surv_acrs, 0),
                       round(blm_int_acrs, 0),
                       # Density calculations
                       unt_site_cnt / unt_acrs,
                       blm_site_cnt / blm_acrs,
                       unt_site_cnt / unt_int_acrs,
                       blm_site_cnt / blm_int_acrs,
                       unt_int_acrs / unt_acrs * 100,
                       blm_int_acrs / blm_acrs * 100]
    
            results.append(payload)

            # Update console
            arcpy.AddMessage("----Unit_Acres: {}".format(payload[1]))
            arcpy.AddMessage("----Unit_Site_Count: {}".format(payload[2]))
            arcpy.AddMessage("----Unit_Survey_Count: {}".format(payload[3]))
            arcpy.AddMessage("----Unit_Survey_Acres: {}".format(payload[4]))
            arcpy.AddMessage("----Unit_Class_III_Acres: {}".format(payload[5]))      
            arcpy.AddMessage("----BLM_Acres: {}".format(payload[6]))
            arcpy.AddMessage("----BLM_Site_Count: {}".format(payload[7]))
            arcpy.AddMessage("----BLM_Survey_Count: {}".format(payload[8]))
            arcpy.AddMessage("----BLM_Survey_Acres: {}".format(payload[9]))
            arcpy.AddMessage("----BLM_Class_III_Acres: {}".format(payload[10]))
            arcpy.AddMessage(" ") 

        # Column headings
        header = ("Admin_Unit",

                  "Unit_Acres",
                  "Unit_Site_Count",
                  "Unit_Survey_Count",
                  "Unit_Survey_Acres",
                  "Unit_Class_III_Acres",

                  "BLM_Acres",
                  "BLM_Site_Count",
                  "BLM_Survey_Count",
                  "BLM_Survey_Acres",
                  "BLM_Class_III_Acres",

                  "Unit_Sites_per_Unit_Acre",
                  "BLM_Sites_per_BLM_Acre",

                  "Unit_Sites_per_Unit_ClassIII_Acre",
                  "BLM_Sites_per_BLM_ClassIII_Acre",
                  
                  "Unit_ClassIII_Survey_Coverage",
                  "BLM_ClassIII_Survey_Coverage")

        # Write to csv
        with open(output_csv, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(header)
            for result in results:
                csvwriter.writerow(result)
                                                                    
        return results

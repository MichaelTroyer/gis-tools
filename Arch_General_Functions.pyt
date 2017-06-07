# -*- coding: utf-8 -*-

import arcpy
import copy
import datetime
import os
import traceback

import pandas as pd

from arcpy import mapping
from arcpy import env

from collections import defaultdict

env.addOutputsToMap = False
arcpy.env.overwriteOutput = True


##---Functions-------------------------------------------------------------------------------------


def blast_my_cache():
    """Delete in memory tables and feature classes
       reset to original worksapce when done"""

    # get the original workspace location
    orig_workspace = arcpy.env.workspace
    
    # Set the workspace to in_memory
    arcpy.env.workspace = "in_memory"
    # Delete all in memory feature classes
    fcs = arcpy.ListFeatureClasses()
    if len(fcs) > 0:
        for fc in fcs:
            arcpy.Delete_management(fc)
    # Delete all in memory tables
    tbls = arcpy.ListTables()
    if len(tbls) > 0:
        for tbl in tbls:
            arcpy.Delete_management(tbl)

    # Reset the workspace
    arcpy.env.workspace = orig_workspace

def buildWhereClauseFromList(table, field, valueList):
    """Takes a list of values and constructs a SQL WHERE
    clause to select those values within a given field and table."""

    # Add DBMS-specific field delimiters
    fieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(table).path, field)

    # Determine field type
    fieldType = arcpy.ListFields(table, field)[0].type

    # Add single-quotes for string field values
    if str(fieldType) == 'String':
        valueList = ["'%s'" % value for value in valueList]

    # Format WHERE clause in the form of an IN statement
    whereClause = "%s IN(%s)" % (fieldDelimited, ', '.join(map(str, valueList)))
    return whereClause
    
    
class Toolbox(object):   
    def __init__(self):
        self.label = "Arch_General_Functions_v2"
        self.alias = "Arch_General_Functions"
        
        # List of tool classes associated with this toolbox
        self.tools = [Arch_General_Functions]


class Arch_General_Functions(object):
    def __init__(self):
        self.label = "Arch_General_Functions"
        self.description = ""
        self.canRunInBackground = True
        
    def getParameterInfo(self):
        
        #Input Target Shapefile
        param0=arcpy.Parameter(
            displayName="Incoming Shapefile",
            name="Input_Shape",
            datatype="Feature Class",
            parameterType="Required",
            direction="Input")
        
        param1=arcpy.Parameter(
            displayName="Selection based on case value",
            name="Select_Boolean",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input",
            enabled = "False")
        
        param2=arcpy.Parameter(
            displayName="Select Feature Case Field",
            name="Select_Field",
            datatype="String",
            parameterType="Optional",
            direction="Input",
            enabled = "False")
        
        param3=arcpy.Parameter(
            displayName="Select Feature Case Value",
            name="Select_Value",
            datatype="String",
            parameterType="Optional",
            direction="Input",
            enabled = "False")
        
        #Output Location and Name
        param4=arcpy.Parameter(
            displayName="Output Workspace and File Naming Convention",
            name="Out_Name",
            datatype="File",
            parameterType="Required",
            direction="Output")
        
###
# Map Options
###

        #Create Map Document
        param5 = arcpy.Parameter(
            displayName="Create a Map Document",
            name="Create_Map",
            datatype="Boolean",
            parameterType="Optional",
            category = "Map Options",
            direction="Input")
        
        #Select Template
        param6 = arcpy.Parameter(
            displayName="Select Map Template",
            name="Map_Template",
            datatype="string",
            parameterType="Optional",
            category = "Map Options",            
            direction="Input")
        
        #Cultural Resources Report Number
        param7=arcpy.Parameter(
            displayName="Culural Resource Report Number",
            name="Input_CRNum",
            datatype="String",
            parameterType="required", 
            direction="Input")
        
        #Cultural Resources Report Name
        param8=arcpy.Parameter(
            displayName="Cultural Resources Report Name",
            name="Input_CRName",
            datatype="String",
            parameterType="Optional",
            category = "Map Options", 
            direction="Input")
        
        #Author
        param9=arcpy.Parameter(
            displayName="Author",
            name="Input_Author",
            datatype="String",
            parameterType="Optional",
            category = "Map Options",
            direction="Input")
        
###
# SHPO data prep
###

        #Populate SHPO Layers
        param10 = arcpy.Parameter(
            displayName="Populate SHPO Layers",
            name="SHPO_Option",
            datatype="boolean",
            parameterType="Optional",
            category = "SHPO Options",
            direction="Input")
        
        #Select SHPO Layers
        param11 = arcpy.Parameter(
            displayName="Select SHPO Layer to Populate",
            name="SHPO_Layers",
            datatype="string",
            parameterType="Optional",
            enabled = "False",
            category = "SHPO Options",
            direction="Input")
        
        #Input Site/Survey ID
        param12 = arcpy.Parameter(
            displayName="Input SHPO Site or Survey ID",
            name="Input_ID",
            datatype="string",
            parameterType="Optional",
            enabled = "False",
            category = "SHPO Options",
            direction="Input")
        
###
# Data options
###

        #Output table of spatial information in PLSS
        param13 = arcpy.Parameter(
            displayName="Write PLSS Spatial Location Data to Table",
            name="Output_PLSS",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Clip Elevation
        param14 = arcpy.Parameter(
            displayName="Clip Degital Elevation Model (DEM)",
            name="Output_DEM",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Calculate Slope
        param15 = arcpy.Parameter(
            displayName="Calculate Slope",
            name="Output_Slope",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Clip and Dissolve Geology
        param16 = arcpy.Parameter(
            displayName="Clip Geology",
            name="table_Output",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Clip and Dissolve Soils
        param17 = arcpy.Parameter(
            displayName="Clip Soils",
            name="Output_Soils",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Clip and Dissolve Vegetation
        param18 = arcpy.Parameter(
            displayName="Clip Vegetation",
            name="Output_Veg",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Clip and Dissolve Sites
        param19 = arcpy.Parameter(
            displayName="Clip Sites",
            name="Output_Sites",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        #Clip and Dissolve Surveys
        param20 = arcpy.Parameter(
            displayName="Clip Surveys",
            name="Output_Surveys",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")

        #Create Lit Search Tables
        param21 = arcpy.Parameter(
            displayName="Copy Lit Search Tables",
            name="Lit_Tables",
            datatype="Boolean",
            parameterType="Optional",
            category = "Data Options",
            direction="Input")
        
        params = [param0, param1, param2, param3, param4, param5, param6,
                  param7, param8, param9, param10, param11, param12, param13,
                  param14, param15, param16, param17, param18, param19, param20,
                  param21]
        
        return params


    def isLicensed(self):
        return True


    def updateParameters(self, params):
        #Param0 - Shape In and handle subselections
        params[0].filter.list = ["Polygon"]
        
        if params[0].value:
            params[1].enabled = "True"
        else:
            params[1].enabled = "False"
            
        if params[1].value == 1:
            params[1].enabled = "True"
        else:
            params[2].value = ""
            params[2].enabled = "False"
        
        if params[1].value == 1:
            desc = arcpy.Describe(params[0].value)
            fields = desc.fields
            featurefieldList = [field.name for field in fields
                                if field.type in ["String", "Integer", "SmallInteger"]]
                                
            params[2].enabled = "True"
            params[2].filter.type = "ValueList"
            params[2].filter.list = featurefieldList
            
        if params[2].value:
            params[3].enabled = "True"
        else:
            params[3].value = ""
            params[3].enabled = "False"
            
        if params[2].value:
            field_select = params[2].value
            arcpy.Frequency_analysis(params[0].value, "in_memory\\field_freq", field_select)
            
            
            for field in fields:
                if field.name == field_select:
                    type = field.type
                    if type in ("Integer", "SmallInteger"):
                        where = '"{}" IS NOT NULL'.format(field_select)
                    elif type == "String":
                        where = '"{}" <> \'\' and "{}" IS NOT NULL'.format(
                            field_select, field_select)

            featurevalueList = [row[0] for row in arcpy.da.SearchCursor(
                "in_memory\\field_freq", [field_select], where)]        
                    
            featurevalueList.sort()
            
            params[3].enabled = "True"
            params[3].filter.type = "ValueList"
            params[3].filter.list = featurevalueList

        #param5 - Create Map Document
        if not params[5].value == 1:
            params[6].enabled = "False"
            params[8].enabled = "False"
            params[9].enabled = "False"
        else:
            params[6].enabled = "True"
            params[8].enabled = "True"
            params[9].enabled = "True"
            
        templateList = []
        
        #Hard Code MAP TEMPLATES
        path = r'T:\CO\GIS\giswork\rgfo\development\cultural\Templates(NO_EDIT)\MapTemplates'
        
        #Hard Code MAP TEMPLATES
        dirList = os.listdir(path)
        
        for fname in dirList:
            if "mxd" in fname:
                templateList.append(fname)
                
        params[6].filter.type = "ValueList"
        params[6].filter.list = templateList
        
        #param6 - map Template
        if not params[6].altered:
            params[6].value = "MappingTemplate_24k_Landscape.mxd"
            
        #param7 - CR Report Number
        if not params[7].altered:
            params[7].value = "CR-RG-17-xxx (x)"
            
        #param8 - CR Report Name
        if not params[8].altered:
            params[8].value = ""

        #param9 - Author
        if not params[9].altered:
            params[9].value = ""

        #param10 - SHPO Layers and values
        if not params[10].value == 1:
            params[11].enabled = "False"
            params[12].enabled = "False"
        else:
            params[11].enabled = "True"
            params[12].enabled = "True"
            
        #param11 - Select Layer
        populateList = ["Site", "Survey"]
        params[11].filter.type = "ValueList"
        params[11].filter.list = populateList
        if not params[11].altered:
            params[11].value = "Survey"
            
        #param14 - DEM, Slope, Aspect
        if not params[14].value == 1:
            params[15].enabled = "False"
            params[15].value = 0
        else:
            params[15].enabled = "True"
        return


    def updateMessages(self, params):    
        #param10 - Populate SHPO Layers
        if params[10].value == 1 and params[11].value == "Survey":
            surveyString = str(params[12].ValueAsText)
            surveyCount = surveyString.count(".")
            if not surveyCount == 2:
                params[12].setErrorMessage(
                    "Survey ID must be in format xx.LM.xxXXX (e.g. MC.LM.NR999)")
                
        if params[10].value == 1 and params[11].value == "Site":
            siteString = str(params[12].ValueAsText)
            siteCount = siteString.count(".")
            if not siteCount >= 1:
                params[12].setErrorMessage(
                    "Site ID must be in format 5xx.XXXX (e.g. 5FN.9999)")                             
        return


    def execute(self, params, messages):
        blast_my_cache()

        #Hard Codes
        Sites               = r'T:\CO\GIS\gistools\tools\Cultural\BLM_Cultural_Resources'\
                              r'\BLM_Cultural_Resources.gdb\RGFO_Sites'
        Surveys             = r'T:\CO\GIS\gistools\tools\Cultural\BLM_Cultural_Resources'\
                              r'\BLM_Cultural_Resources.gdb\RGFO_Surveys'
        DEM                 = r'T:\ReferenceState\CO\CorporateData\topography\dem'\
                              r'\Elevation 10 Meter Zunits Feet.lyr'
        mxd                 = arcpy.mapping.MapDocument(
                              r'T:\CO\GIS\giswork\rgfo\development'\
                              r'\cultural\Templates(NO_EDIT)\MapTemplates\{}'\
                              r''.format(params[6].valueAsText))
        sections            = r'T:\ReferenceState\CO\CorporateData\cadastral\Sections.lyr'
        GCDB                = r'T:\ReferenceState\CO\CorporateData\cadastral\Survey Grid.lyr'
        counties            = r'T:\ReferenceState\CO\CorporateData\admin_boundaries'\
                              r'\County Boundaries.lyr'
        quad                = r'T:\ReferenceState\CO\CorporateData\cadastral'\
                              r'\24k USGS Quad Index.lyr'
        shpoSurveyTarget    = r'T:\CO\GIS\giswork\rgfo\development\cultural\Templates(NO_EDIT)'\
                              r'\SHPOTemplates\survey_ply_tmp.shp'
        shpoSiteTarget      = r'T:\CO\GIS\giswork\rgfo\development\cultural\Templates(NO_EDIT)'\
                              r'\SHPOTemplates\site_ply_tmp.shp'
        PLSStable           = r'T:\CO\GIS\giswork\rgfo\development\cultural\Templates(NO_EDIT)'\
                              r'\Other_Templates\SpatialOutputTemplate.dbf'
        Geology             = r'T:\CO\GIS\gisuser\rgfo\mtroyer\z_Misc\z_Data\Data.gdb\Geology'
        Soils               = r'T:\CO\GIS\gisuser\rgfo\mtroyer\z_Misc\z_Data\Data.gdb\Soils'
        Vegetation          = r'T:\ReferenceState\CO\CorporateData\vegetation'\
                              r'\Colorado GAP ReGAP 2004.lyr'
        
        #Hold Param0 and check for multi-part and select case values where appropriate
##        polyRaw = '{}\{}_Polygon.shp'.format(
##                    os.path.dirname(params[4].valueAsText),
##                    os.path.basename(params[4].valueAsText))
             
        # If case selct
        if params[1].value == 1:
            desc = arcpy.Describe(params[0].value)
            fields = desc.fields
            
            for field in fields:
                if field.name == params[2].valueAsText:
                    ftype = field.type
                    field = params[2].value
                    field_select = '"'+params[2].valueAsText+'"'
                    title = params[3].valueAsText
                    if ftype in ("Integer", "SmallInteger"):
                        where = field_select + ' = ' + title
                    elif ftype == "String":
                        where = field_select + ' = ' + "'" + title + "'"
                    break
                
            arcpy.MakeFeatureLayer_management(params[0].value, "in_memory\\selected", where)
            
        else:  # take everything
            arcpy.MakeFeatureLayer_management(params[0].value, "in_memory\\selected")
            
            
        polyParts = int(arcpy.GetCount_management("in_memory\\selected").getOutput(0))
        
        if polyParts >1:
            arcpy.Dissolve_management("in_memory\\selected", 'in_memory\\Poly')    
        
        else:
            arcpy.MakeFeatureLayer_management("in_memory\\selected", 'in_memory\\Poly')
            
##        arcpy.CopyFeatures_management('in_memory\\Poly', polyRaw)
##        poly = polyRaw
        poly = 'in_memory\\Poly'
        #Create POLY_ACRES if it doesn't already exist
        desc = arcpy.Describe(params[0].value)
        fields = desc.fields
        fieldNames = []

        for field in fields:
            fieldNames.append(field.name)
            
        if not "POLY_ACRES" in fieldNames:                     
            arcpy.AddField_management(poly, "POLY_ACRES", 'DOUBLE', 12, 8)
            
        #Calculate field - POLY_ACRES
        arcpy.CalculateField_management(poly, "POLY_ACRES", "!shape.area@ACRES!", "PYTHON_9.3", "")

        #Identify Workspace and hold param4 - naming convention
        baseName = \
            os.path.dirname(params[4].valueAsText) + "\\" + os.path.basename(params[4].valueAsText)
            
        envPath = baseName + "_Env_Data"
        
        if params[14].value == 1 \
        or params[16].value == 1 \
        or params[17].value == 1 \
        or params[18].value == 1:
            if not os.path.exists(envPath): 
                os.mkdir(envPath)
            
        try:
            # Peel back input polygon 10 meters to prevent extranneous boundary overlap - i.e. PLSS
            # If poly(s) is too small and gets erased, keep original(s)
            arcpy.MakeFeatureLayer_management(poly, "in_memory\\polycopy")
            arcpy.PolygonToLine_management("in_memory\\polycopy", "in_memory\\polylines")
            arcpy.Buffer_analysis("in_memory\\polylines", "in_memory\\polybuffer", 10)
            
            arcpy.Erase_analysis("in_memory\\polycopy",
                                 "in_memory\\polybuffer",
                                 "in_memory\\PLSSpoly")
            
            inResult =int(arcpy.GetCount_management("in_memory\\polycopy").getOutput(0))
            outResult=int(arcpy.GetCount_management("in_memory\\PLSSpoly").getOutput(0))
            
            if not inResult == outResult:
                arcpy.Delete_management("in_memory\\PLSSpoly")
                arcpy.MakeFeatureLayer_management(poly, "in_memory\\PLSSpoly")
                
            arcpy.Delete_management("in_memory\\polycopy")
            arcpy.Delete_management("in_memory\\polylines")
            arcpy.Delete_management("in_memory\\polybuffer")
            
            #Clip elevation
            if params[14].value == 1:
                param14Name = envPath+"\\elevation"
                arcpy.Clip_management(DEM, "", param14Name, poly, "", "ClippingGeometry")
                
            #Map Processes 
            if params[5].value == 1:
                arcpy.AddMessage("Creating Map Document")
                
                df1 = arcpy.mapping.ListDataFrames(mxd)[0]
                df2 = arcpy.mapping.ListDataFrames(mxd)[1]

                now = datetime.datetime.now()
                
                #Intersect survey poly, GCDB Survey Grid, counties, and quad
                arcpy.Intersect_analysis(
                    ["in_memory\\PLSSpoly", GCDB, counties, quad], "in_memory\\survey", "NO_FID")
                
                arcpy.Frequency_analysis("in_memory\\survey", "in_memory\\County", "COUNTY")
                
                countyList = [str(row[0]).title() + " County"
                              for row in arcpy.da.SearchCursor("in_memory\\County", ["COUNTY"])]
                            
                arcpy.Frequency_analysis("in_memory\\survey", "in_memory\\Quad", "QUAD_NAME")
                
                quadList =   [str(row[0]).title() + " 7.5'" 
                              for row in arcpy.da.SearchCursor("in_memory\\Quad", ["QUAD_NAME"])]
                                            
                #Select sections that intersect a feature class
                arcpy.MakeFeatureLayer_management(sections, "in_memory\\sections_join")
                arcpy.SelectLayerByLocation_management(
                    "in_memory\\sections_join", "INTERSECT", "in_memory\\PLSSpoly")                
                
                #Get unique PLSSID's
                arcpy.Frequency_analysis(
                    "in_memory\\sections_join", "in_memory\\PLSSID_freq", ["PLSSID"])              
                
                PLSSIDlist = \
                    [row[0] for row in arcpy.da.SearchCursor("in_memory\\PLSSID_freq", ["PLSSID"])]
        
                meridianlist_orig=[PLSSID[2:4]for PLSSID in PLSSIDlist] 
              
                #Message the console
                infolist=[]
                meridianlist_unique = list(set(meridianlist_orig))
                
                for meridian in meridianlist_unique:
                    if meridian == "06":
                        meridian_name = "6th Principal Meridian"
                    elif meridian == "31":
                        meridian_name = "Ute Principal Meridian"
                    elif meridian == "23":
                        meridian_name = "New Mexico Principal Meridian"
                        
                    infolist.append(meridian_name)
                    
                    for PLSSID in PLSSIDlist:
                        if PLSSID[2:4] == meridian:
                            twnsp = str(int(PLSSID[5:7]))
                            twnspdir = PLSSID[8]
                            plss_range = str(int(PLSSID[9:12]))
                            rangedir = PLSSID[13]                         
                            plss_where = 'PLSSID = {}'.format(PLSSID)

                            trDesc = "T. {} {}., R. {} {}.".format(
                                twnsp, twnspdir, plss_range, rangedir)
                         
                            infolist.append(trDesc)
                            
                legalDesc = '\n'.join(infolist)
                arcpy.AddMessage(legalDesc)

                #Pull and populate elevation in feet
                arcpy.FeatureToPoint_management(poly, "in_memory\\centroid", "CENTROID")
                arcpy.sa.ExtractValuesToPoints(
                    "in_memory\\centroid", DEM, "in_memory\\centValue", "NONE", "VALUE_ONLY")
                
                ElePoint = str([row[0] for row
                                in arcpy.da.SearchCursor("in_memory\\centValue", "RASTERVALU")])
                
                Elevation = ElePoint.split(".")
                
                Elev1 = Elevation[0]
                ElevPrint = Elev1[1:]

                #Update report elements with dict - k: element_ID, v: text                
                map_elements = {"ProjectID" : params[7].valueAsText,
                                "Title"     : params[8].valueAsText,
                                "Author"    : params[9].valueAsText,
                                "Date"      : str(now.month)+"\\"+str(now.day)+"\\"+str(now.year),
                                "Location"  : legalDesc,
                                "County"    : "\n".join(countyList),
                                "Quad"      : "\n".join(quadList),
                                "Elevation" : ElevPrint+" feet"}
                                                                
                for item in arcpy.mapping.ListLayoutElements(mxd):
                    # Not all will be in dict..
                    try:
                        ePX = item.elementPositionX
                        item.text = map_elements[item.name]
                        item.elementPositionX = ePX
                    except: pass
                    
                #Identify and select intersected counties
                arcpy.MakeFeatureLayer_management(counties, "in_memory\\NewCounty")       
                arcpy.SelectLayerByLocation_management(
                    "in_memory\\NewCounty", "INTERSECT", "in_memory\\PLSSpoly") 
                    
                arcpy.MakeFeatureLayer_management("in_memory\\NewCounty", "Inset_Cty")
                
                countyLayer = baseName+"_InsetCounty.lyr"
                arcpy.SaveToLayerFile_management("Inset_Cty", countyLayer)
                addLayer = arcpy.mapping.Layer(countyLayer)
                arcpy.mapping.AddLayer(df2, addLayer, "TOP")
                arcpy.Delete_management(countyLayer)
                
                #Add Layers
                polyLyr = arcpy.mapping.Layer(params[0].valueAsText)
                arcpy.mapping.AddLayer(df1, polyLyr, "TOP")
                
                #Set visible layers
                for item in arcpy.mapping.ListLayers(mxd, "", df1):
                    if item.supports("VISIBLE") == "True":
                        item.visible = "False"

                arcpy.RefreshActiveView
                arcpy.RefreshTOC           
                
                #Save as new mxd
                saveName = ((params[4].valueAsText)+".mxd")
                mxd.saveACopy(saveName)
                
                #set scale and pan to extent
                mxd = arcpy.mapping.MapDocument(saveName)
                df1 = arcpy.mapping.ListDataFrames(mxd)[0]
                surDesc = arcpy.Describe(poly)
                newExtent = surDesc.extent
                df1.extent = newExtent
                df1.scale = 24000
                mxd.save()
                
            #SHPO Processes
            if params[10].value == 1:
                shpoName = str(params[12].ValueAsText)
                
                #Survey
                if params[11].ValueAsText == "Survey":
                    arcpy.AddMessage("Populating SHPO Survey Layer")
                    shpoName2 = shpoName.replace(".", "_")
                    output = os.path.dirname(params[4].valueAsText)+"\\"+shpoName2+"_SHPO.shp"
                    
                    #Clear template for appending
                    arcpy.DeleteRows_management(shpoSurveyTarget)
                    
                    #Append feature
                    arcpy.Append_management(poly, shpoSurveyTarget, "NO_TEST")
                    arcpy.MakeFeatureLayer_management(shpoSurveyTarget, 'in_memory\\outPoly')
                    
                    #Calculate geometry (area, perimeter, acres)
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "AREA", "!shape.area@SQUAREMETERS!", "PYTHON_9.3")
                    
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "PERIMETER", "!shape.length@METERS!", "PYTHON_9.3")
                    
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")
                    
                    #Calculate location (x, y)
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "X","!SHAPE.CENTROID.X!", "PYTHON_9.3")
                    
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "Y","!SHAPE.CENTROID.Y!", "PYTHON_9.3")
                    
                    #Add other info (DOC_, CONF, ZONE, AGENCY_, SOURCE, DATE)
                    fields = ('DOC_', 'CONF','ZONE', 'AGENCY_', 'DATE')   
                    
                    with arcpy.da.UpdateCursor("in_memory\\outpoly", fields) as cursor:
                        for row in cursor:
                            row[0] = params[12].valueAsText 
                            row[1] = "HC"
                            row[2] = "13"
                            row[3] = params[7].valueAsText
                            row[4] = datetime.datetime.now()
                            
                            cursor.updateRow(row)   
                            
                    #output shape and save
                    arcpy.CopyFeatures_management("in_memory\\outpoly", output)
                    
                    #Clear template for future use
                    arcpy.DeleteRows_management(shpoSurveyTarget)
                    
                #Site
                if params[11].ValueAsText == "Site":
                    arcpy.AddMessage("Populating SHPO Site Layer")
                    shpoName2 = shpoName.replace(".", "_")
                    output = os.path.dirname(params[4].valueAsText)+"\\"+shpoName2+"_SHPO.shp"
                    
                    #Clear template for appending
                    arcpy.DeleteRows_management(shpoSiteTarget)
                    
                    #Append feature
                    arcpy.Append_management(poly, shpoSiteTarget, "NO_TEST")
                    arcpy.MakeFeatureLayer_management(shpoSiteTarget, 'in_memory\\outPoly')
                    
                    #Calculate geometry (area, perimeter, acres)
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "AREA", "!shape.area@SQUAREMETERS!", "PYTHON_9.3")
                    
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "PERIMETER", "!shape.length@METERS!", "PYTHON_9.3")
                    
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")
                    
                    #Calculate location (x, y)
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "X","!SHAPE.CENTROID.X!", "PYTHON_9.3")
                    
                    arcpy.CalculateField_management(
                        'in_memory\\outPoly', "Y","!SHAPE.CENTROID.Y!", "PYTHON_9.3")
                    
                    #Add other info (SITE_, BND_CMPLT, DATE, LINEAR, ZONE, CONF)  
                    fields = ('SITE_','BND_CMPLT','DATE', 'LINEAR', 'ZONE', 'CONF')
                    
                    with arcpy.da.UpdateCursor("in_memory\\outpoly", fields)as cursor:
                        for row in cursor:
                            row[0] = params[12].valueAsText
                            row[1] = "Y"
                            row[2] = datetime.datetime.now()
                            row[3] = '0'
                            row[4] = "13"
                            row[5] = "HC"
                            
                            cursor.updateRow(row)    
                            
                    #output shape and save
                    arcpy.CopyFeatures_management("in_memory\\outpoly", output)
                    
                    #Clear template for future use
                    arcpy.DeleteRows_management(shpoSiteTarget)
                    
            #Output PLSS
            if params[13].value == 1:
                arcpy.AddMessage("Writing PLSS Location Data")
                
                #Intersect survey poly, GCDB Survey Grid, counties, and quad
                
                arcpy.Intersect_analysis(
                    ["in_memory\\PLSSpoly", GCDB, counties, quad], "in_memory\\survey", "NO_FID")
                
##                freqFields = ["PLSSID","FRSTDIVNO","QQSEC"]
##                arcpy.Frequency_analysis("in_memory\\survey", "in_memory\\Loc", freqFields)
##                arcpy.CopyRows_management(PLSStable, "in_memory\\outTable")
##                fieldNames = ["PM", "TWN", "RNG", "SEC", "QQ1", "QQ2"]
##                inCur = arcpy.da.InsertCursor("in_memory\\outTable", fieldNames)
##                with arcpy.da.SearchCursor("in_memory\\Loc", freqFields) as cursor:
##                    for row in cursor:
##                        #inRow[0] = PM
##                        inRow0 = str(row[0])[2:4]
##                        #inRow[1] = Twn 
##                        inRow1 = str(row[0])[5:7]+str(row[0])[8]
##                        #inRow[2] = Rng
##                        inRow2 = str(row[0])[10:12]+str(row[0])[13]
##                        #inRow[3] = Sec
##                        inRow3 = str(row[1])
##                        #inRow[4] = Quar1
##                        inRow4 = str(row[2])[0:2]
##                        #inRow[5] = Quar2
##                        inRow5 = str(row[2])[2:4]
##
##                        inCur.insertRow([inRow0, inRow1, inRow2, inRow3, inRow4, inRow5]) 
#####
                freqFields = ["PLSSID","FRSTDIVNO","QQSEC"]
                arcpy.Frequency_analysis("in_memory\\survey", "in_memory\\Loc", freqFields)
                
                fieldNames = ["PM", "TWN", "RNG", "SEC", "QQ1", "QQ2"]
                
                plss = defaultdict(list)
                
                with arcpy.da.SearchCursor("in_memory\\Loc", freqFields) as cursor:
                    for row in cursor:
                        pm  = str(row[0])[2:4]
                        twn = str(row[0])[5:7]+str(row[0])[8]
                        rng = str(row[0])[10:12]+str(row[0])[13]
                        sec = str(row[1])
                        qq1 = str(row[2])[0:2]
                        qq2 = str(row[2])[2:4]
                        
                        plss[pm +'-'+ twn +'-'+ rng +'-'+ sec].append([qq1, qq2])
                            
                        print_list = []

                        for section in plss.keys():
                            splits = section.split('-')
                            
                            if len(plss[section]) == 16:
                                splits.extend(['ENTIRE', 'SECTION'])
                                print_list.append(splits)
                                continue
                                
                            quarters = defaultdict(list)
                            
                            for quarter in plss[section]:
                                quarters[quarter[1]].append(quarter)
                                
                            for quarter, q_list in quarters.items():
                                if len(q_list) == 4:
                                    splits_ = copy.copy(splits)
                                    splits_.extend(['ENTIRE', quarter])
                                    print_list.append(splits_)
                                else: 
                                    for q in q_list:
                                        splits_ = copy.copy(splits)
                                        splits_.extend(q)
                                        print_list.append(splits_)

                out_csv = baseName +'_PLSS.csv'
                arcpy.AddMessage(out_csv)                        

                df = pd.DataFrame(print_list, columns=fieldNames)

                # sort into proper (non-lexigraphic) order
                df.PM  = df.PM.astype(int)
                df.SEC = df.SEC.astype(int)
                df['TWN_v'] = df.TWN.str[:-1]
                df['TWN_d']= df.TWN.str[-1]
                df['RNG_v'] = df.RNG.str[:-1]
                df['RNG_d']= df.RNG.str[-1]

                for col in df.columns:
                    try:
                        df[col] = df[col].astype(int)
                    except: pass

                df.sort(['PM', 'TWN_v', 'TWN_d', 'RNG_v', 'RNG_d', 'SEC', 'QQ2', 'QQ1'], inplace=True)
                df.drop(['TWN_v', 'TWN_d', 'RNG_v', 'RNG_d'], axis=1, inplace=True)
                df.to_csv(out_csv, index=False)
#####
##
##                arcpy.TableToTable_conversion("in_memory\\outTable",
##                      os.path.dirname(params[4].valueAsText),
##                      os.path.basename(params[4].valueAsText+"_Legal_Location.csv"))
                
            #Output DEM
            if params[14].value == 1:
                arcpy.AddMessage("Clipping Digital Elevation Model")
                
            #Output Slope
            if params[15].value == 1:
                arcpy.AddMessage("Calculating Slope")
                param15Name = envPath+"\\slope"
                outSlope = arcpy.sa.Slope(param14Name, "DEGREE", 0.3043)
                outSlope.save(param15Name)
                
            #Output Geology
            if params[16].value == 1:
                arcpy.AddMessage("Clipping Geology")
                param17Name = envPath+"\\Geology.shp"
                arcpy.Clip_analysis(Geology, poly, param17Name)
                
            #Output Soils
            if params[17].value == 1:
                arcpy.AddMessage("Clipping Soils")
                param18Name = envPath+"\\Soils.shp"
                arcpy.Clip_analysis(Soils, poly, param18Name)   
                
            #Output Vegetation
            if params[18].value == 1:
                arcpy.AddMessage("Clipping Vegetation")
                param19Name = envPath+"\\Vegetation.shp"
                arcpy.Clip_analysis(Vegetation, poly, param19Name)
                
            #Output Sites
            if params[19].value == 1:
                arcpy.AddMessage("Clipping Sites")
                param20Name = baseName+"_Sites.shp"
                arcpy.MakeFeatureLayer_management(Sites, "in_memory\\siteLayer")
                
                arcpy.SelectLayerByLocation_management(
                    "in_memory\\siteLayer", "INTERSECT", poly, "", "NEW_SELECTION")
                
                siteResult=int(arcpy.GetCount_management("in_memory\\siteLayer").getOutput(0)) 
                
                if siteResult == 0:
                    arcpy.AddMessage(
                        "####"+'\n'+'\n'+"There are no sites within this polygon"+'\n'+'\n'+"####")          
                else:
                    arcpy.CopyFeatures_management("in_memory\\siteLayer", param20Name) 
                    
            #Output Surveys
            if params[20].value == 1:
                arcpy.AddMessage("Clipping Surveys")
                param21Name = baseName+"_Surveys.shp"
                arcpy.MakeFeatureLayer_management(Surveys, "in_memory\\surveyLayer")
                
                arcpy.SelectLayerByLocation_management(
                    "in_memory\\surveyLayer", "INTERSECT", poly, "", "NEW_SELECTION")
                
                surveyResult=int(arcpy.GetCount_management("in_memory\\surveyLayer").getOutput(0))           
                
                if surveyResult == 0:
                    arcpy.AddMessage(
                      "####"+'\n'+'\n'+"There are no surveys within this polygon"+'\n'+'\n'+"####")
                else:
                    arcpy.Clip_analysis("in_memory\\surveyLayer", poly, param21Name)
                    arcpy.AddField_management(param21Name, "ACRES", "DOUBLE", 15, 2)
                    arcpy.CalculateField_management(
                        param21Name, "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")

            #Lit
            if params[21].value == 1:
                # sites
                arcpy.SelectLayerByLocation_management(
                    "in_memory\\siteLayer", 'WITHIN_A_DISTANCE', poly, '1 Mile', 'NEW_SELECTION')
                
                if int(arcpy.GetCount_management("in_memory\\siteLayer").getOutput(0)) <> 0:
                    arcpy.TableToTable_conversion("in_memory\\siteLayer",
                        os.path.dirname(params[4].valueAsText),
                        os.path.basename(params[4].valueAsText+"_Sites_lit.csv"))
                
                # surveys
                arcpy.SelectLayerByLocation_management(
                    "in_memory\\surveyLayer", 'WITHIN_A_DISTANCE', poly, '1 Mile', 'NEW_SELECTION')
                
                if int(arcpy.GetCount_management("in_memory\\surveyLayer").getOutput(0)) <> 0:
                    arcpy.TableToTable_conversion("in_memory\\surveyLayer",
                        os.path.dirname(params[4].valueAsText),
                        os.path.basename(params[4].valueAsText+"_Surveys_lit.csv"))
        except:
            arcpy.AddMessage(str(traceback.format_exc()))
        
        finally:
            blast_my_cache()
            
        return                      

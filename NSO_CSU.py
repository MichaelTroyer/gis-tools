#!/usr/bin/env python
# -*- coding: utf-8 -*-


#######################################################################################################################
##
## FRONT MATTER
##
#######################################################################################################################

"""
Author:
Michael D. Troyer

Date:
10/25/2016 

Purpose:
Accept an analysis area and an arbitrary number of input feature classes.
Union the feature classes by input category (as parameter) and union all categories with analysis area.
Clip the output union by analysis area.
For each category, add field, select overlap, and populate table with self id.
Represents polygons flagged by some spatial intersection.
Calculate summary statistics and summary field in table.
Write inputs and outputs, results, and summary.
Copy inputs and write outputs to new gdb.
Something like that..
Log everything...

Comments:
def deleteInMemory by Ben Zank
"""


#######################################################################################################################
##
## IMPORTS
##
#######################################################################################################################

from __future__ import division # Integer division is lame - use // instead

import datetime, logging, os, re, sys, traceback
import arcpy
from arcpy import env
import copy, csv, math
#import numpy as np
#import pandas as pd
#import scipy as sp
#import matplotlib as mpl
#import matplotlib.pyplot as plt
from collections import Counter, defaultdict

#pylab

env.addOutputsToMap = False
env.overwriteOutput = True


#######################################################################################################################
##
## GOLBAL VARIABLES
##
#######################################################################################################################

start_time = datetime.datetime.now()

# Set starting home directory
#home_dir = os.path.join(os.path.dirname(__file__), os.path.basename(__file__)
home_dir = r'T:\CO\GIS\gisuser\rgfo\mtroyer\z_GIS_Exchange'

# Set starting workspace environment
env_workspace = r'T:\CO\GIS\gisuser\rgfo\mtroyer\z_GIS_Exchange\scratch.gdb'
arcpy.env.workspace = env_workspace


#######################################################################################################################
##
## GLOBAL FUNCTIONS
##
#######################################################################################################################

def deleteInMemory():
    # Set the workspace to in_memory
    env.workspace = "in_memory"
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


#######################################################################################################################
##
## EXECUTION
##
#######################################################################################################################
  
class Toolbox(object):
    def __init__(self):
        self.label = "NSO_CSU_Analysis"
        self.alias = "NSO_CSU_Analysis"

        # List of tool classes associated with this toolbox
        self.tools = [NSO_CSU_Analysis]


class NSO_CSU_Analysis(object):
    def __init__(self):
        self.label = "NSO_CSU_Analysis"
        self.description = ""
        self.canRunInBackground = True # Will likely fail if set to false - memory error in 32 bit env

    def getParameterInfo(self):
        """Define parameter definitions"""

#######################################################################################################################
##
## PARAMETERS
##
#######################################################################################################################
        
        # Input Analysis Area
        param00=arcpy.Parameter(
            displayName="Input Project Analysis Area",
            name="Analysis_Area",
            datatype="Feature Class",
            parameterType="Required",
            direction="Input")

        # Output Location
        param01=arcpy.Parameter(
            displayName="Output File Geodatabase Location",
            name="Out_Location",
            datatype="File",
            parameterType="Required",
            direction="Output")
        
############
##
## CATEGORY RESOURCES
##
############
        
        param02=arcpy.Parameter(
            displayName="Air Quality and Climate",
            name="Air_Quality_and_Climate",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param03=arcpy.Parameter(
            displayName="Geology",
            name="Geology",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param04=arcpy.Parameter(
            displayName="Soil Resources",
            name="Soil_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param05=arcpy.Parameter(
            displayName="Water Resources",
            name="Water_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param06=arcpy.Parameter(
            displayName="Terrestrial Wildlife",
            name="Terrestrial_Wildlife",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param07=arcpy.Parameter(
            displayName="Aquatic Wildlife",
            name="Aquatic_Wildlife",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param08=arcpy.Parameter(
            displayName="Vegetation",
            name="Vegetation",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param09=arcpy.Parameter(
            displayName="Wetlands and Riparian Resources",
            name="Wetlands_and_Riparian_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param10=arcpy.Parameter(
            displayName="Special Status Species",
            name="Special_Status_Species",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)
        
        param11=arcpy.Parameter(
            displayName="Wildland Fire and Fuel Management",
            name="Wildland_Fire_and_Fuel_Management",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param12=arcpy.Parameter(
            displayName="Cultural Resources",
            name="Cultural_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param13=arcpy.Parameter(
            displayName="Tribal Concerns",
            name="Tribal_Concerns",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param14=arcpy.Parameter(
            displayName="Paleontological Resources",
            name="Paleontological_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param15=arcpy.Parameter(
            displayName="Visual Resources",
            name="Visual_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)

        param16=arcpy.Parameter(
            displayName="Lands with Wilderness Characteristics",
            name="Lands_with_Wilderness_Characteristics",
            datatype="Feature Class",
            parameterType="Optional",
            category = "1 - Resources",
            direction="Input",
            multiValue=True)
        
############
##
## CATEGORY RESOURCE USES
##
############
        
        param17=arcpy.Parameter(
            displayName="Recreation",
            name="Recreation",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

        param18=arcpy.Parameter(
            displayName="Livestock Grazing",
            name="Livestock_Grazing",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)
        
        param19=arcpy.Parameter(
            displayName="Forestry",
            name="Forestry",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

        param20=arcpy.Parameter(
            displayName="Minerals",
            name="Minerals",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

        param21=arcpy.Parameter(
            displayName="Renewable Energy",
            name="Renewable_Energy",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

        param22=arcpy.Parameter(
            displayName="Travel and Transportation Management",
            name="Travel_and_Transportation_Management",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

        param23=arcpy.Parameter(
            displayName="Lands and Realty",
            name="Lands_and_Realty",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

        param24=arcpy.Parameter(
            displayName="South Park Master Leasing Plan",
            name="South_Park_Master_Leasing_Plan",
            datatype="Feature Class",
            parameterType="Optional",
            category = "2 - Resource Uses",
            direction="Input",
            multiValue=True)

############
##
## CATEGORY SPECIAL DESIGNATIONS
##
############
        
        param25=arcpy.Parameter(
            displayName="Areas of Critical Environmental Concern",
            name="Areas_of_Critical_Environmental_Concern",
            datatype="Feature Class",
            parameterType="Optional",
            category = "3 - Special Designations",
            direction="Input",
            multiValue=True)

        param26=arcpy.Parameter(
            displayName="Backcountry Conservation Areas",
            name="Backcountry_Conservation_Areas",
            datatype="Feature Class",
            parameterType="Optional",
            category = "3 - Special Designations",
            direction="Input",
            multiValue=True)

        param27=arcpy.Parameter(
            displayName="National and State Scenic Byways",
            name="National_and_State_Scenic_Byways",
            datatype="Feature Class",
            parameterType="Optional",
            category = "3 - Special Designations",
            direction="Input",
            multiValue=True)

        param28=arcpy.Parameter(
            displayName="Wild and Scenic Rivers",
            name="Wild_and_Scenic_Rivers",
            datatype="Feature Class",
            parameterType="Optional",
            category = "3 - Special Designations",
            direction="Input",
            multiValue=True)
        
        param29=arcpy.Parameter(
            displayName="Wilderness Areas and Wilderness Study Areas",
            name="Wilderness_Areas_and_Wilderness_Study_Areas",
            datatype="Feature Class",
            parameterType="Optional",
            category = "3 - Special Designations",
            direction="Input",
            multiValue=True)

############
##
## CATEGORY SOCIAL AND ECONOMIC CONDITIONS
##
############ 

        param30=arcpy.Parameter(
            displayName="Abandoned Mine Land, Hazardous Materials, and Public Safety",
            name="Abandoned_Mine_Land_Hazardous_Materials_and_Public_Safety",
            datatype="Feature Class",
            parameterType="Optional",
            category = "4 - Social and Economic Conditions",
            direction="Input",
            multiValue=True)

        param31=arcpy.Parameter(
            displayName="Social and Economic Values",
            name="Social_and_Economic_Values",
            datatype="Feature Class",
            parameterType="Optional",
            category = "4 - Social and Economic Conditions",
            direction="Input",
            multiValue=True)

############
##
## ANALYSIS TYPE SELECTION
##
############ 
        
        param32=arcpy.Parameter(
            displayName="NSO, CSU, ROW_EX, ROW_AV, CFML, CLOT",
            name="NSO_CSU_ROW_EX_ROW_AV_CFML_CLOT",
            datatype="String",
            parameterType="Required",
            direction="Input")
                
        parameters = [param00, param01, param02, param03, param04, param05, param06, param07, param08, param09, param10,
                      param11, param12, param13, param14, param15, param16, param17, param18, param19, param20, param21,
                      param22, param23, param24, param25, param26, param27, param28, param29, param30, param31, param32]
                          
        return parameters


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        parameters[0].filter.list = ['Polygon']
        for i in range(2,32):
            parameters[i].filter.list = ['Polygon']
        

        parameters[32].filter.type = "ValueList"
        parameters[32].filter.list = ['NSO', 'CSU', 'ROW_EX', 'ROW_AV', 'CFML', 'CLOT'] #missing one
        if not parameters[32].altered:
            parameters[32].value = "NSO"
        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return


    def execute(self, parameters, messages):
        """The source code of the tool."""

        try:
            
            # Clear memory JIC
            deleteInMemory()

#######################################################################################################################
##
## INITIALIZE LOGGING
##
#######################################################################################################################

            database_name = os.path.join(os.path.dirname(parameters[1].valueAsText),
                                         os.path.basename(parameters[1].valueAsText))
            date_time = (str(datetime.datetime.now())).split('.')[0]
            date_time_stamp = re.sub('[^0-9]', '_', date_time)
            filename = os.path.basename(__file__)
            output_process_log = database_name+'_LogFile.txt' # will write to existing or create if new

            logging.basicConfig(filename = output_process_log, level=logging.DEBUG, format = '%(message)s')

            # Create the log file header
            logging.debug('LOG FILE:')
            logging.debug('_'*120+'\n\n')
            logging.debug('Start date: '+date_time+'\n')
            logging.debug('Filename: '+filename+'\n')
            logging.debug('Working directory:\n '+os.getcwd()+'\n')
            logging.debug('Running python from:\n '+sys.executable+'\n')
            logging.debug('System Info:\nPython version: '+sys.version+'\n\n')
            logging.debug("Execution:")
            logging.debug('_'*120+'\n')

            # Print the output logfile path to the console
            arcpy.AddMessage(os.path.join(os.path.dirname(output_process_log), os.path.basename(output_process_log)))

            # Uncomment for production code
            #logging.disable(logging.CRITICAL)

            # Use for logging variables
            #logging.debug(    'DEBUG:     x = {} and is {}'.format(str(x), str(type(x))))
            #logging.info(     'INFO:      x = {} and is {}'.format(str(x), str(type(x))))
            #logging.warning(  'WARNING:   x = {} and is {}'.format(str(x), str(type(x))))
            #logging.error(    'ERROR:     x = {} and is {}'.format(str(x), str(type(x))))
            #logging.critical( 'CRITICAL:  x = {} and is {}'.format(str(x), str(type(x))))

            # Use assert sanity checks
            #assert [condition], 'assertionError str'

            def auto_log(str, *vars): # a function to log vars and messages to terminal and logfile simultaneously - this thing is sweet!
                arcpy.AddMessage(str)
                logging.debug(str)
                for var in vars:
                    logging.debug(var)
                return
                
#######################################################################################################################
##
## MAIN PROGRAM
##
#######################################################################################################################
            
            # Declare operational parameters
            arcpy.AddMessage("Running environment: Python - {}".format(sys.version))
            
            # Make a geodatabase
            database_name = os.path.basename(parameters[1].valueAsText)+"_"+date_time_stamp+".gdb"
            database_path = os.path.dirname(parameters[1].valueAsText)
            arcpy.CreateFileGDB_management (database_path, database_name, "10.0")
            output_path = database_path+"\\"+database_name
            auto_log('Creating geodatabase', output_path)

            # Secure a copy of the input analysis area
            arcpy.MakeFeatureLayer_management(parameters[0].value, "in_memory\\_")
            
            # Dissolve everything to prevent overlapping input polygons
            auto_log('Dissolving input polygon')
            arcpy.Dissolve_management("in_memory\\_", "in_memory\\__")
            analysis_area = output_path+"\\Analysis_Area"
            arcpy.CopyFeatures_management("in_memory\\__", analysis_area)

            # Set the workspace to the output database
            arcpy.env.workspace = output_path
            
            # Identify spatial reference of analysis area
            spatial_ref = arcpy.Describe(analysis_area).spatialReference
                                      
            # The main data structure - key = parameter ID, values = ['input parameter paths', 'category', 'Code']
            input_params = {'02air_quality_and_climate':
                                [parameters[2].valueAsText, 'Resources', 'AIR_QUAL'],
                            '03geology':
                                [parameters[3].valueAsText, 'Resources', 'GEO'],
                            '04soil_resources':
                                [parameters[4].valueAsText, 'Resources', 'SOIL'],
                            '05water_resources':
                                [parameters[5].valueAsText, 'Resources', 'H2O'],
                            '06terrestrial_wildlife':
                                [parameters[6].valueAsText, 'Resources', 'TERR_W'],
                            '07aquatic_wildlife':
                                [parameters[7].valueAsText, 'Resources', 'AQUAT_W'],
                            '08vegetation':
                                [parameters[8].valueAsText, 'Resources', 'VEG'],
                            '09wetlands_and_riparian_resources':
                                [parameters[9].valueAsText, 'Resources', 'WETLANDS'],
                            '10special_status_species':
                                [parameters[10].valueAsText, 'Resources', 'SS_SPECIES'],
                            '11wildland_fire_and_fuel_management':
                                [parameters[11].valueAsText, 'Resources', 'FIRE_FUELS'],
                            '12cultural_resources':
                                [parameters[12].valueAsText, 'Resources', 'CULTURAL'],
                            '13tribal_concerns':
                                [parameters[13].valueAsText, 'Resources', 'TRIBAL'],
                            '14paleontological_resources':
                                [parameters[14].valueAsText, 'Resources', 'PALEO'],
                            '15visual_resources':
                                [parameters[15].valueAsText, 'Resources', 'VISUAL'],
                            '16lands_with_wilderness_characteristics':
                                [parameters[16].valueAsText, 'Resources', 'LWC'],
                            '17recreation':
                                [parameters[17].valueAsText, 'Resource_Uses', 'REC'],
                            '18livestock_grazing':
                                [parameters[18].valueAsText, 'Resource_Uses', 'GRAZING'],
                            '19forestry':
                                [parameters[19].valueAsText, 'Resource_Uses', 'FORESTRY'],
                            '20minerals':
                                [parameters[20].valueAsText, 'Resource_Uses', 'MINERALS'],
                            '21renewable_energy':
                                [parameters[21].valueAsText, 'Resource_Uses', 'RENEWABLE'],
                            '22travel_and_transportation_management':
                                [parameters[22].valueAsText, 'Resource_Uses', 'TRAVEL'],
                            '23lands_and_realty':
                                [parameters[23].valueAsText, 'Resource_Uses', 'LANDS'],
                            '24south_park_master_leasing_plan':
                                [parameters[24].valueAsText, 'Resource_Uses', 'SPMLP'],
                            '25areas_of_critical_environmental_concern':
                                [parameters[25].valueAsText, 'Special_Designations', 'ACEC'],
                            '26backcountry_conservation_areas':
                                [parameters[26].valueAsText, 'Special_Designations', 'BCA'],
                            '27national_and_state_scenic_byways':
                                [parameters[27].valueAsText, 'Special_Designations', 'BYWAYS'],
                            '28wild_and_scenic_rivers':
                                [parameters[28].valueAsText, 'Special_Designations', 'WSR'],
                            '29wilderness_areas_and_WSAs':
                                [parameters[29].valueAsText, 'Special_Designations', 'WSA'],
                            '30aml_hazmat_and_public_safety':
                                [parameters[30].valueAsText, 'Social_Economic_Conditions', 'AML_HAZMAT'],
                            '31social_and_economic_values':
                                [parameters[31].valueAsText, 'Social_Economic_Conditions', 'SOC_ECON']}

            # Create a sorted list of input parameters with actual values
            sorted_inputs = sorted([item for item in input_params.items() if not item[1][0] == None])
            auto_log('Getting valid parameters', sorted_inputs)
            
            # Verify that there were some inputs
            if len(sorted_inputs) == 0:
                auto_log('No Inputs')
                arcpy.AddError("There are no valid inputs - system exit")
                sys.exit()
                            
            # Get a list of the categories represented in the input data
            input_categories = set([item[1][1] for item in sorted_inputs])
            auto_log('Getting categories', input_categories)

            # Create list of feature datasets to create from input categories
            feature_datasets = []
            feature_datasets.extend(["Input_"+category for category in input_categories])
            feature_datasets.extend(["Results_"+category for category in input_categories])
            auto_log('Creating gdb datasets', feature_datasets)
                                   
            # Create feature datasets: 'Input_*' for copy of input data, 'Results_*' for outputs
            for fds in feature_datasets:
                arcpy.CreateFeatureDataset_management(output_path, fds, spatial_ref)
                                 
            # Function to copy the unioned layers and dissolve to input data - deletes attribute data!
            def union_inputs(name, dest, fc_list):
                union_output = output_path+"\\Input_"+dest+"\\"+name
                arcpy.Union_analysis(fc_list, "in_memory\\dissolve")
                arcpy.Dissolve_management("in_memory\\dissolve", union_output)
                # Uncomment below and comment 2  llines above to choose to not dissolve / delete attribute data
                # Note: overlapping polygon errors are possible in acreage counts!
                #arcpy.Union_analysis(fc_list, union_output)
                return 
                   
            # Iterate across sorted items and create union output
            auto_log('Creating and dissolving criteria unions      ---this will probably be slow---     ')
            for id, data in sorted_inputs:
                union_output = union_inputs(id[2:], data[1], data[0])
                
### At this point, we have created the gdb and feature datasets, sorted the inputs, and created the unioned criteria layers
                
            # Write all input paths to text report doc
            # Open text file for writing path details
            auto_log('Writing text file')
            outText = database_path+"\\"+os.path.basename(parameters[1].valueAsText)+"_"+date_time_stamp+"_Report.txt"
            textFile = open(outText, "w")
            textFile.write("Surface Use Analysis "+str(datetime.datetime.now())+"\n")
            textFile.write("_______________________________________________"+"\n\n\n\n")
            textFile.write("Analysis Area:\n")
            textFile.write('\t'+parameters[0].valueAsText+'\n\n')
            textFile.write("Output Location:\n")
            textFile.write('\t'+parameters[1].valueAsText+'\n\n\n')
            for category in input_categories:
                textFile.write(category.upper()+":\n\n")
                for ID, data_list in sorted_inputs:
                    paths = data_list[0].split(";")
                    if data_list[1] == category:
                        textFile.write('\t'+ID[2:].upper().replace("_", " ")+" - "+data_list[2]+'\n')
                        for path_name in paths:
                            textFile.write("\t\t")
                            textFile.write(path_name+"\n")
                        textFile.write("\n")
                textFile.write("\n\n")
            textFile.close()

            # Get the NSO or CSU selection
            nso_csu = parameters[32].valueAsText
                         
            # Create a master list of all category fcs that were created for later intersection
            all_fcs_list = []
            
            # Iterate across input categories, list feature classes in each category
            auto_log('Clipping feature classes')
            for category in input_categories:
                fc_input_list = arcpy.ListFeatureClasses(feature_dataset="Input_"+category)
                all_fcs_list.extend(fc_input_list)
                
                # For each fc in each category, clip the analysis area, dissolve the fc and out put as [NSO/CSU]_ + feature name
                for fc in fc_input_list:
                    output_fc_name = nso_csu+"_"+os.path.basename(fc)
                    output_fc_path = output_path+"\\Results_"+category+"\\"+output_fc_name
                    arcpy.Clip_analysis(analysis_area, fc, "in_memory\\clip")
                    # Dissolve the clips
                    arcpy.Dissolve_management("in_memory\\clip", output_fc_path)
                    
            fc_id_map = defaultdict(str)
            for key, value in sorted_inputs:
                fc_id_map[key[2:]] = value[2]
                       
            # Collapse geometry union [will be slow with full input]
            auto_log('Unioning criteria inputs   ---this will probably be slow---   ')
            output_aggregate_feature = output_path+"\\Aggregate_Results"
            all_fcs_list_copy = copy.deepcopy(all_fcs_list)
            
            # Add input analysis area to list of union and union it all
            all_fcs_list_copy.append(u'Analysis_Area')
            arcpy.Union_analysis(all_fcs_list_copy, "in_memory\\agg_union")
            
            # Clip the union and output it
            arcpy.Clip_analysis("in_memory\\agg_union", analysis_area, "in_memory\\clip_")

            # Make sure everything is in single-part format for later analysis - JIC
            arcpy.MultipartToSinglepart_management("in_memory\\clip_", output_aggregate_feature)

            # Erase all the other fields - sometimes its easier to ask for forgiveness than permission [ietafftp]
            erase_fields_lst = [field.name for field in arcpy.ListFields(output_aggregate_feature)]
            auto_log('Creating matrix    ---this will probably be slow---   ', erase_fields_lst)
            # Union creates very messy tables - clean them
            for field in erase_fields_lst:
                try:
                    arcpy.DeleteField_management(output_aggregate_feature, field)
                except:
                    logging.debug("Delete field failed: "+str(field)) # Should minimally fail on OID, Shape, Shape_area, and Shape_length
                
            # Delete identical features within output_aggregate_feature to prevent double counting acres
            auto_log('Checking for identical features')
            try:
                arcpy.DeleteIdentical_management(output_aggregate_feature, ["SHAPE"])
            except:
                logging.debug("Delete identical failed") # This will usually fail - it's ok
                
            # Calculate acreage
            auto_log('Calculating acres')
            # Add ACRES field to analysis area - check if exists
            # If ACRES/Acres/acres exists in table, flag for calculation instead
            field_list = [field.name for field in arcpy.ListFields(output_aggregate_feature) if field.name.upper() == "ACRES"]            
            if field_list:
                acre_field = field_list[0] # select the suitable 'acres' variant
            else:
                arcpy.AddField_management(output_aggregate_feature, "ACRES", "DOUBLE", 15, 2)
                acre_field = "ACRES"
            arcpy.CalculateField_management(output_aggregate_feature, acre_field, "!shape.area@ACRES!", "PYTHON_9.3")

            # Create a defaultdict to store acreages - default dictionaries are awesome
            acreage_counts = defaultdict(int)
            
            # Iterate across all_fcs_list and add field, select by location and calculate field with ID, remove null
            arcpy.MakeFeatureLayer_management(output_aggregate_feature, "in_memory\\mem_agg_layer")

            # Create a list to store all added field ids    
            fc_field_list = []
                        
            auto_log('Populating matrix')                             
            for fc in all_fcs_list:
                fc_ID = fc_id_map[str(fc)]
                
                # Copy the created fields for later use in fields summary
                fc_field_list.append(fc_ID)
                
                # Add field, select, and calculate
                arcpy.AddField_management("in_memory\\mem_agg_layer", fc_ID, "Text", field_length=20)
                arcpy.SelectLayerByLocation_management("in_memory\\mem_agg_layer", "WITHIN", fc, selection_type="NEW_SELECTION")
                arcpy.CalculateField_management("in_memory\\mem_agg_layer", fc_ID, '"'+fc_ID+'"', "PYTHON_9.3")

                # Get the acres
                fc_acres = sum([row[0] for row in arcpy.da.SearchCursor("in_memory\\mem_agg_layer", acre_field)])
                
                # Add key=fc_id and value=acreage to sweet default dictionary
                acreage_counts[fc_ID] = round(fc_acres, 2)

                # Switch the selection
##                arcpy.SelectLayerByAttribute_management("in_memory\\mem_agg_layer", "CLEAR_SELECTION")                
##                arcpy.SelectLayerByAttribute_management("in_memory\\mem_agg_layer", "NEW_SELECTION", '"'+fc_ID+'" IS NULL')
                arcpy.SelectLayerByAttribute_management("in_memory\\mem_agg_layer", "SWITCH_SELECTION")
                
                # Clean the table for readability - replace "Null" with ""
                arcpy.CalculateField_management("in_memory\\mem_agg_layer", fc_ID, '"'+""+'"', "PYTHON_9.3")
                arcpy.SelectLayerByAttribute_management("in_memory\\mem_agg_layer", "CLEAR_SELECTION")
                
            # Write the markup feature to disc
            auto_log('Creating markup output')   
            output_aggregate_feature_markup = output_path+"\\Aggregate_Results_Markup"
            arcpy.CopyFeatures_management("in_memory\\mem_agg_layer", output_aggregate_feature_markup)

            # Create a summary field and get list of other fields
            auto_log('Calculating summary field') 
            arcpy.AddField_management(output_aggregate_feature_markup, "Summary", "Text", field_length=255)
            fc_field_list.append('Summary')
            num_of_fields = len(fc_field_list)
            with arcpy.da.UpdateCursor(output_aggregate_feature_markup, fc_field_list) as cur:
                for row in cur:
                    # There's gotta be a better way to do this... this sucks
                    row[num_of_fields-1] = re.sub('\s+', ' ', (reduce(lambda x,y: x+" "+y, [row[i] for i in range(num_of_fields-1)]))).strip()
                    cur.updateRow(row)

            # Get the total analysis acreage
            arcpy.MakeFeatureLayer_management(output_aggregate_feature_markup, "in_memory\\_markup")
            total_analysis_acres = sum([row[0] for row in arcpy.da.SearchCursor("in_memory\\_markup", acre_field)])
            
            # Get the total marked-up acreage
            arcpy.SelectLayerByAttribute_management("in_memory\\_markup", "NEW_SELECTION", """ "Summary" <> '' """)
            total_markup_acres = sum([row[0] for row in arcpy.da.SearchCursor("in_memory\\_markup", acre_field)])
                
            # Delete the lingering unmarked output - comment out if you want to keep original with original fields
            arcpy.Delete_management(output_aggregate_feature)
            
            # Write outputs acreages to csv
            auto_log('Writing acreages to csv')
            outCSV = database_path+"\\"+os.path.basename(parameters[1].valueAsText)+"_"+date_time_stamp+"_Acreage_Report.csv"
            with open(outCSV, 'wb') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(["Total Analysis Acres", str(round(total_analysis_acres, 2))])
                csvwriter.writerow(["", ""])
                csvwriter.writerow(["", ""])
                csvwriter.writerow(['Criteria', nso_csu+"_Acres", "Percent"])
                for fc_id, acres in sorted(acreage_counts.items()):
                    csvwriter.writerow([fc_id, acres, ((acres/total_analysis_acres)*100)])
                csvwriter.writerow(["", ""])
                csvwriter.writerow(["", ""])
                csvwriter.writerow(["Total "+nso_csu+" Acres", round(total_markup_acres, 2), ((total_markup_acres/total_analysis_acres)*100)])

            auto_log('Done..')


#######################################################################################################################
##
## EXCEPTIONS
##
#######################################################################################################################
                    
        except:
            logging.debug('\n\n')
            logging.debug('Exceptions:\n')
            logging.debug('_'*120+'\n\n')
            logging.debug('\n'+str(traceback.format_exc()))

            def print_full_stack():
                exc = sys.exc_info()[0]
                stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
                if not exc is None:  # i.e. if an exception is present
                    del stack[-1]       # remove call of full_stack, the printed exception
                                        # will contain the caught exception caller instead
                trc = 'Traceback (most recent call last):\n'
                stackstr = trc + ''.join(traceback.format_list(stack))
                if not exc is None:
                     stackstr += '  ' + traceback.format_exc().lstrip(trc)
                print "print_full_stack: "+stackstr

            def print_extended_traceback():
                """write traceback plus all stacked frame locals - innermost last"""
                tb = sys.exc_info()[2]
                while tb.tb_next:
                    tb = tb.tb_next    #fast forward to end of stack
                stack = []
                f = tb.tb_frame
                while f:
                    stack.append(f)    #append tb.tb_frame in reverse order
                    f = f.f_back
                stack.reverse()    #reverse to forward order
                logging.debug('local variables by frame - innermost last')
                for frame in stack:
                    logging.debug('frame {} in {} at line {}'.format(frame.f_code.co_name,
                                                                     frame.f_code.co_filename,
                                                                     frame.f_lineno))
                    # Give up ALL that data!
                    for key, value in frame.f_locals.items():
                        logging.debug('\t\t%20s = '% key)
                        try:
                            logging.debug(value)
                        except:
                            logging.debug('Error writing value')

            # Comment out for production
            
            print_extended_traceback()
            
            arcpy.AddMessage('\n'+str(traceback.format_exc()))
            arcpy.AddMessage('\nTraceback written to:\n{}'.format(output_process_log))
 

#######################################################################################################################
##
## CLEAN-UP
##
#######################################################################################################################

        finally:
            end_time = datetime.datetime.now()
            auto_log("End Time: "+str(end_time))
            auto_log("Time Elapsed: %s" %(str(end_time - start_time)))
            logging.debug('\n'*10)
            logging.shutdown()
            deleteInMemory()


#######################################################################################################################
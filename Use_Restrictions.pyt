# -*- coding: utf-8 -*-


###################################################################################################
##
## FRONT MATTER
##
###################################################################################################

"""
Author:                  _         _
Michael D. Troyer..       \_(''/)_/

Date:
10/25/2016

Updated:
12/20/16
    - add layer symbology, optional logging, and Alternative A clip
1/17/17
    - added CLOSE_MIN_ENT and CLOSE_COAL
1/20/17
    - removed CLOSE_MIN_ENT, changed MIN_WD to CLOSE_MinWD,
      CLOSE_GEX to CLOSE_GEOEX, CLOSE_MMD to CLOSE_MMDisp,
      add CLOSE_SML
      restructured inputs and reported outputs to have no categories
    
Purpose:
The tool accepts an analysis area (RMP boundary), use-restriction type, an alternative, and an 
arbitrary number of input feature classes which represent the relevant RMP analysis criteria for 
the given analysis type an alternative. The tool unions the feature classes into groups 
representing (arbitrarily) between 1 and 30 individual resources. These resource unions are then
unioned with the analysis area yielding all possible combinations of spatial overlap 
between the input criteria and analysis area. For each resource, the tool adds a field to the 
aggregate union, selects areas of overlap with that resource (itself a union of individual 
criteria), and attributes the newly-created field with a resource ID as a means to codify the 
spatial intersection of resource concerns and the RMP analysis area. The result is effectively a
markup matrix. The tool then calculates the relevant acreages represented by each resource and 
writes the summary data to an output .csv file, and copies the output feature classes 
and copies of its inputs to a user-defined, date/time-stamped database. Depending on the 
alternative selection, the tool may also subdivide the analysis by previous plan extent 
(Alternative A) or by ecoregion(Alternative D). The end product is intended to be a stand-alone, 
fully-transparent, end-to-end analysis complete with input data, output data, operational metadata,
and a results summary. The tool uses a simple, custom logging class to simultaneously send status
reports to the console, report operational metadata (inputs, outputs, user, etc..) to a report text
file, and log extended details to an optional logfile with variable introspection.

Comments:
def deleteInMemory by Ben Zank

To Do:
Replace +'\\'+ path joins with os.path.join()
Remove depricated categories content

"""


###################################################################################################
##
## IMPORTS
##
###################################################################################################


from __future__ import division # Integer division is lame - use // instead
from collections import defaultdict
import arcpy
import copy
import csv
import datetime
import getpass
import os
import re
import sys
import traceback


###################################################################################################
##
## GLOBALS
##
###################################################################################################

##---Classes---------------------------------------------------------------------------------------

class pyt_log(object):
    """A custom logging class that can simultaneously write to the console - AddMessage,
       write to an optional logfile, and/or a production report..."""
       
    def __init__(self, report_path, log_path, log_active=True):
        self.report_path = report_path
        self.log_path = log_path
        self.log_active = log_active
    
    def _write_arg(self, arg, path, starting_level=0):
        """Accepts a [path] txt from open(path) and unpacks the data [arg]"""
        level = starting_level
        txtfile = open(path, 'a')
        if level == 0:
            txtfile.write("_"*80)
        if type(arg) == dict:
            txtfile.write("\n"+(level*"\t")+(str(arg))+"\n")
            txtfile.write((level*"\t")+str(type(arg))+"\n")
            for key, value in arg.items():
                txtfile.write((level*"\t\t")+(str(key))+": "+(str(value))+"\n")
                if hasattr(value, '__iter__'):
                    txtfile.write((level*"\t")+"Values:"+"\n")
                    txtfile.close()
                    for val in value:
                        self._write_arg(val, path, starting_level=level+1)
                txtfile.close()
        else:
            txtfile.write("\n"+(level*"\t")+(str(arg))+"\n")
            txtfile.write((level*"\t")+str(type(arg))+"\n")
            if hasattr(arg, '__iter__'): #does not include strings
                txtfile.write((level*"\t")+"Iterables:"+"\n")
                txtfile.close()
                for a in arg:
                    self._write_arg(a, path, starting_level=level+1)

    def _writer(self, msg, path, *args):
        """A writer to write the msg, and unpacked variable"""
        if os.path.exists(path):
            write_type = 'a'
        else:
            write_type = 'w'
        with open(path, write_type) as txtfile:
            txtfile.write("\n"+msg+"\n")
            txtfile.close()
            if args:
                for arg in args:
                    self._write_arg(arg, path)

    def console(self, msg):
        """Print to console only"""
        arcpy.AddMessage(msg)

    def report(self, msg):
        """Write to report only"""
        self._writer(msg, path=self.report_path)

    def logfile(self, msg, *args):
        """Write to logfile only"""
        if self.log_active:
            path = self.log_path
            self._writer(msg, path, *args)
            
    def log_report(self, msg, *args):
        """Write to logfile and report only"""
        self.report(msg)
        self.logfile(msg, *args)
        
    def log_all(self, msg, *args):
        """Write to all"""
        self.console(msg)
        self.report(msg)
        self.logfile(msg, *args)

##---Functions-------------------------------------------------------------------------------------

def deleteInMemory():
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

def get_acres(fc):
    """Check for an acres field in fc - create if doesn't exist or flag for calculation.
       Recalculate acres and return name of acre field"""

    # Add ACRES field to analysis area - check if exists
    field_list = [field.name for field in arcpy.ListFields(fc) if field.name.upper() == "ACRES"]

    # If ACRES/Acres/acres exists in table, flag for calculation instead
    if field_list:
        acre_field = field_list[0] # select the 'acres' variant
    else:
        arcpy.AddField_management(fc, "ACRES", "DOUBLE", 15, 2)
        acre_field = "ACRES"

    arcpy.CalculateField_management(fc, acre_field, "!shape.area@ACRES!", "PYTHON_9.3")
    return acre_field

##---Variables-------------------------------------------------------------------------------------

start_time = datetime.datetime.now()

user = getpass.getuser()

##---Settings--------------------------------------------------------------------------------------

arcpy.env.addOutputsToMap = False

arcpy.env.overwriteOutput = True


###################################################################################################
##
## EXECUTION
##
###################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "Use_Restrictions_v3"
        self.alias = "use_restrictions"

        # List of tool classes associated with this toolbox
        self.tools = [Use_Restrictions_v3]


class Use_Restrictions_v3(object):
    def __init__(self):
        self.label = "Use_Restrictions_v3"
        self.description = ""
        self.canRunInBackground = True 

    def getParameterInfo(self):
        """Define parameter definitions"""


###################################################################################################
##
## PARAMETERS
##
###################################################################################################

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
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

############
##
## RESOURCES
##
############

        param02=arcpy.Parameter(
            displayName="Abandoned Mine Land, Hazardous Materials, and Public Safety",
            name="Abandoned_Mine_Land_Hazardous_Materials_and_Public_Safety",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
        
        param03=arcpy.Parameter(
            displayName="Air Quality and Climate",
            name="Air_Quality_and_Climate",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param04=arcpy.Parameter(
            displayName="Aquatic Wildlife",
            name="Aquatic_Wildlife",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param05=arcpy.Parameter(
            displayName="Areas of Critical Environmental Concern",
            name="Areas_of_Critical_Environmental_Concern",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param06=arcpy.Parameter(
            displayName="Backcountry Conservation Areas",
            name="Backcountry_Conservation_Areas",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
        
        param07=arcpy.Parameter(
            displayName="Cultural Resources",
            name="Cultural_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param08=arcpy.Parameter(
            displayName="Fire and Fuel Management",
            name="Fire_and_Fuel_Management",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param09=arcpy.Parameter(
            displayName="Forestry",
            name="Forestry",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
                
        param10=arcpy.Parameter(
            displayName="Geology",
            name="Geology",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param11=arcpy.Parameter(
            displayName="Grazing",
            name="Grazing",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param12=arcpy.Parameter(
            displayName="Lands and Realty",
            name="Lands_and_Realty",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
        
        param13=arcpy.Parameter(
            displayName="Lands with Wilderness Characteristics",
            name="Lands_with_Wilderness_Characteristics",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param14=arcpy.Parameter(
            displayName="Minerals",
            name="Minerals",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param15=arcpy.Parameter(
            displayName="National and State Scenic Byways",
            name="National_and_State_Scenic_Byways",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
        
        param16=arcpy.Parameter(
            displayName="Paleontological Resources",
            name="Paleontological_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param17=arcpy.Parameter(
            displayName="Recreation",
            name="Recreation",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param18=arcpy.Parameter(
            displayName="Renewable Energy",
            name="Renewable_Energy",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param19=arcpy.Parameter(
            displayName="Social and Economic Values",
            name="Social_and_Economic_Values",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
        
        param20=arcpy.Parameter(
            displayName="Soil Resources",
            name="Soil_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param21=arcpy.Parameter(
            displayName="South Park Master Leasing Plan",
            name="South_Park_Master_Leasing_Plan",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param22=arcpy.Parameter(
            displayName="Special Status Species",
            name="Special_Status_Species",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param23=arcpy.Parameter(
            displayName="Terrestrial Wildlife",
            name="Terrestrial_Wildlife",
            datatype="Feature Class",
            parameterType="Optional",
             category = "Resources",
            direction="Input",
            multiValue=True)

        param24=arcpy.Parameter(
            displayName="Travel and Transportation Management",
            name="Travel_and_Transportation_Management",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)
        
        param25=arcpy.Parameter(
            displayName="Tribal Concerns",
            name="Tribal_Concerns",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param26=arcpy.Parameter(
            displayName="Vegetation",
            name="Vegetation",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param27=arcpy.Parameter(
            displayName="Visual Resources",
            name="Visual_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param28=arcpy.Parameter(
            displayName="Water Resources",
            name="Water_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param29=arcpy.Parameter(
            displayName="Wetlands and Riparian Resources",
            name="Wetlands_and_Riparian_Resources",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param30=arcpy.Parameter(
            displayName="Wild and Scenic Rivers",
            name="Wild_and_Scenic_Rivers",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

        param31=arcpy.Parameter(
            displayName="Wilderness Areas and Wilderness Study Areas",
            name="Wilderness_Areas_and_Wilderness_Study_Areas",
            datatype="Feature Class",
            parameterType="Optional",
            category = "Resources",
            direction="Input",
            multiValue=True)

############
##
## ANALYSIS TYPE SELECTIONS
##
############

        param32=arcpy.Parameter(
            displayName="Use Restriction Type",
            name="Use_Restriction_Type",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param33=arcpy.Parameter(
            displayName="Analysis Area Type",
            name="Analysis_Area_Type",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param34=arcpy.Parameter(
            displayName="Alternative",
            name="Alternative",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param35=arcpy.Parameter(
            displayName="Enable Logging",
            name="Enable_Logging",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")

        parameters = [param00, param01, param02, param03, param04, param05, param06, param07,
                      param08, param09, param10, param11, param12, param13, param14, param15,
                      param16, param17, param18, param19, param20, param21, param22, param23,
                      param24, param25, param26, param27, param28, param29, param30, param31,
                      param32, param33, param34, param35]

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

        for i in range(32,35):
            parameters[i].filter.type = "Valuelist"
            
        parameters[32].filter.list = ['NSO', 'CSU', 'TL', 'ROW_AV', 'ROW_EX', 'CLOSE_SML',
                                      'CLOSE_FML',  'CLOSE_COAL', 'CLOSE_MMDisp',
                                      'CLOSE_GEOEX',  'CLOSE_MinWD', 'CLOSE_REN_U', 'CLOSE_REN_NU', 'OTHER']
        
        parameters[33].filter.list = ['Surface [SUR]', 'Mineral Estate [MIN]']
        
        parameters[34].filter.list = ['Alternative A [ALT_A] - will clip by plan area',
                                      'Alternative B [ALT_B]',
                                      'Alternative C [ALT_C]',
                                      'Alternative D [ALT_D] - will clip by ecoregion']

        if not parameters[35].altered:
            parameters[35].value = True
            
        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return


###################################################################################################
##
## EXECUTION
##
###################################################################################################

    def execute(self, parameters, messages):
        """The source code of the tool."""

        try:

            # Clear memory JIC
            deleteInMemory()
            
            # Get the analysis ID
            analysis_id = (parameters[34].valueAsText.split("[")[1][:5])+"_"+\
                          (parameters[33].valueAsText.split("[")[1][:3])+"_"+\
                          (parameters[32].valueAsText)

            # Get the alternative selection
            alternative = parameters[34].valueAsText.split("[")[1][:5]
            
            # Make a directory
            parent_folder_path = os.path.join(os.path.dirname(parameters[1].valueAsText),
                                              os.path.basename(parameters[1].valueAsText))
            child_folder_path = parent_folder_path+"\\"+analysis_id

            # JIC
            if not os.path.exists(parent_folder_path):
                    os.mkdir(parent_folder_path)

            if not os.path.exists(child_folder_path):
                    os.mkdir(child_folder_path)

            date_time_stamp = re.sub('[^0-9]', '', str(datetime.datetime.now())[5:16])
            #filename = os.path.basename(__file__)
            analysis_id_time_stamp = analysis_id+"_"+date_time_stamp

            # Create the logger
            report_path = child_folder_path+"\\"+analysis_id_time_stamp+"_Report.txt"
            logfile_path = child_folder_path+"\\"+analysis_id_time_stamp+"_Logfile.txt"
            logger = pyt_log(report_path, logfile_path)

            if parameters[35] == False:
                logger.log_active = False
            
            # Start logging
            logger.log_all("Use Restrictions Analysis "+str(datetime.datetime.now()))
            logger.log_report("_"*120+"\n")
            logger.log_all("Running environment: Python - {}\n".format(sys.version))
            logger.log_all("User: "+user+"\n")
            logger.log_all("Analysis Type: "+analysis_id+"\n")
            logger.log_all("Analysis Area:\n")
            logger.log_all('\t'+parameters[0].valueAsText+'\n')
            logger.log_all("Output Location:\n")
            logger.log_all('\t'+parameters[1].valueAsText+'\n')


###################################################################################################
##
## MAIN PROGRAM
##
###################################################################################################

            # Make a geodatabase
            database_name = analysis_id_time_stamp+'.gdb'
            database_path = child_folder_path
            arcpy.CreateFileGDB_management(database_path, database_name, "10.0")
            output_path = database_path+"\\"+database_name
            logger.log_all('Created geodatabase at: \n')
            logger.log_all('\t'+output_path+"\n")

            # Secure a copy of the input analysis area
            arcpy.MakeFeatureLayer_management(parameters[0].value, "in_memory\\_")

            # Dissolve everything to prevent overlapping input polygons
            logger.console('1.) Dissolving input polygon')
            arcpy.Dissolve_management("in_memory\\_", "in_memory\\__")
            analysis_area = output_path+"\\"+analysis_id+"_Analysis_Area"
            arcpy.CopyFeatures_management("in_memory\\__", analysis_area)

            # Set the workspace to the output database
            arcpy.env.workspace = output_path
            logger.logfile("Env workspace:", output_path)

            # Identify spatial reference of analysis area
            spatial_ref = arcpy.Describe(analysis_area).spatialReference
            logger.logfile("Spatial reference:", str(spatial_ref))

            # The main data structure
            # Dictionary:
            # key = parameter ID
            # values = ['input parameter path(s)', 'category', 'ID'] - 'category' not used in v0.3
            input_params = {'03air_quality_climate':
                                [parameters[3].valueAsText,  'Resources', 'AIR_QUAL'],
                            '04aquatic_wildlife':
                                [parameters[4].valueAsText,  'Resources', 'AQUAT_WL'],
                            '07cultural_resources':
                                [parameters[7].valueAsText,  'Resources', 'CULTURAL'],
                            '08fire_fuel':
                                [parameters[8].valueAsText,  'Resources', 'FIRE_FUELS'],
                            '10geology':
                                [parameters[10].valueAsText, 'Resources', 'GEO'],
                            '13wilderness_characteristics':
                                [parameters[13].valueAsText, 'Resources', 'LWC'],
                            '16paleo_resources':
                                [parameters[16].valueAsText, 'Resources', 'PALEO'],
                            '20soil_resources':
                                [parameters[20].valueAsText, 'Resources', 'SOIL'],
                            '22special_status_species':
                                [parameters[22].valueAsText, 'Resources', 'SS_SPECIES'],
                            '23terrestrial_wildlife':
                                [parameters[23].valueAsText, 'Resources', 'TERR_WL'],
                            '25tribal_concerns':
                                [parameters[25].valueAsText, 'Resources', 'TRIBAL'],
                            '26vegetation':
                                [parameters[26].valueAsText, 'Resources', 'VEG'],
                            '27visual_resources':
                                [parameters[27].valueAsText, 'Resources', 'VISUAL'],
                            '28water_resources':
                                [parameters[28].valueAsText, 'Resources', 'WATER'],
                            '29wetlands_riparian':
                                [parameters[29].valueAsText, 'Resources', 'WETLANDS'],
                            '09forestry':
                                [parameters[9].valueAsText,  'Resource_Uses', 'FORESTRY'],
                            '11livestock_grazing':
                                [parameters[11].valueAsText, 'Resource_Uses', 'GRAZING'],
                            '12lands_realty':
                                [parameters[12].valueAsText, 'Resource_Uses', 'LANDS'],
                            '14minerals':
                                [parameters[14].valueAsText, 'Resource_Uses', 'MINERALS'],
                            '17recreation':
                                [parameters[17].valueAsText, 'Resource_Uses', 'REC'],
                            '18renewable_energy':
                                [parameters[18].valueAsText, 'Resource_Uses', 'RENEWABLE'],
                            '21south_park_MLP':
                                [parameters[21].valueAsText, 'Resource_Uses', 'SPMLP'],
                            '24travel_transportation':
                                [parameters[24].valueAsText, 'Resource_Uses', 'TRAVEL'],
                            '05ACECs':
                                [parameters[5].valueAsText,  'Special_Designations', 'ACEC'],
                            '06BCAs':
                                [parameters[6].valueAsText,  'Special_Designations', 'BCA'],
                            '15scenic_byways':
                                [parameters[15].valueAsText, 'Special_Designations', 'BYWAYS'],
                            '31wilderness_areas_WSAs':
                                [parameters[31].valueAsText, 'Special_Designations', 'WSA'],
                            '30wild_scenic_rivers':
                                [parameters[30].valueAsText, 'Special_Designations', 'WSR'],
                            '02aml_hazmat':
                                [parameters[2].valueAsText,  'Social_Economics', 'AML_HAZMAT'],
                            '19social_economic_values':
                                [parameters[19].valueAsText, 'Social_Economics', 'SOC_ECON']}

            # Create a sorted list of input parameters with actual values
            sorted_inputs = sorted([item for item 
                                    in input_params.items()
                                    if not item[1][0] == None])
            
            logger.logfile('Valid inputs:', sorted_inputs)

            # Verify that there were some inputs
            if len(sorted_inputs) == 0:
                logger.log_all('No Inputs')
                logger.log_all("There are no valid inputs - system exit")
                sys.exit()

            # ----- depricated in V0.3
            # Get a list of the categories represented in the input data
#            input_categories = set([item[1][1] for item in sorted_inputs])
#            logger.logfile('Input categories:', input_categories)

            # Create feature datasets: 'Inputs' for copy of input data, 'Results' for outputs
            arcpy.CreateFeatureDataset_management(output_path, "Inputs", spatial_ref)
            arcpy.CreateFeatureDataset_management(output_path, "Results", spatial_ref)

            logger.console('2.) Dissolving criteria unions')

# TODO: It is potentially faster to union with all fields and clean all the tables
#       than to iteratively select and create new fields.. think about it.. the table
#       way is nasty - potentially hundreds of arbitrary fields.. the iterative
#       selection method is slow.. think about it some more.

            # Function to union the layers and dissolve
            # Deletes attribute data!
            def union_inputs(input): #(name, fc_list)
                name, fc_list = input[0], input[1]
                union_output = output_path+"\\Inputs\\"+name  
                arcpy.Union_analysis(fc_list, "in_memory\\dissolve", join_attributes="ONLY_FID")
                # Dissolve
                arcpy.Dissolve_management("in_memory\\dissolve", union_output)
                arcpy.Delete_management("in_memory\\dissolve")
                
                return
                
            # Prep the tasks - makes it easier to read
            tasks = [(id[2:], data[0]) for id, data in sorted_inputs]
            logger.logfile('tasks', tasks)

            # Union
            for task in tasks:
                union_inputs(task)
                             
            logger.report("RESOURCES:"+'\n')
            
            # Write inputs to report
            for ID, data_list in sorted_inputs:
                paths = data_list[0].split(";")
                logger.report("\t"+ID[2:].upper().replace("_", " ")+
                              ' - '+data_list[2]+'\n')
                for path_name in paths:
                    logger.report("\t\t"+path_name)
                logger.report("\n")

            # Create a master list of all category fcs that were created for later intersection
            all_fcs_list = []
            for fc in arcpy.ListFeatureClasses(feature_dataset="Inputs"):
                all_fcs_list.append(fc)  
            logger.logfile('all_fcs_list', all_fcs_list)

            # For each fc in all_fcs_list,
            # dissolve the fc and output as analysis_id + feature name
            for fc in all_fcs_list:
                logger.logfile("FC", fc)
                output_fc_name = "Restriction_"+os.path.basename(fc)
                logger.logfile('output_fc_name', output_fc_name)
                output_fc_path = output_path+"\\Results\\"+output_fc_name
                logger.logfile('output_fc_path', output_fc_path)
                arcpy.Clip_analysis(analysis_area, fc, "in_memory\\clip")
                # Dissolve the clips
                arcpy.Dissolve_management("in_memory\\clip", output_fc_path)

            # map the criteria to their categories
            fc_id_map = defaultdict(str)
            for key, value in sorted_inputs:
                fc_id_map[key[2:]] = value[2]  # Drop the sort num prefixes

            # Collapse geometry union [will be slow with full input]
            logger.console('3.) Unioning all criteria inputs')
            output_aggregate_feature = output_path+"\\Aggregate_Results"

            # Add input analysis area to list of union and union it all
            all_fcs_list_copy = copy.deepcopy(all_fcs_list)
            all_fcs_list_copy.append(analysis_area)
            logger.logfile("all_fcs_list_copy", all_fcs_list_copy)
            arcpy.Union_analysis(all_fcs_list_copy, "in_memory\\agg_union", join_attributes="ONLY_FID")

            # Clip the union and output it
            arcpy.Clip_analysis("in_memory\\agg_union", analysis_area, "in_memory\\clip_")

            # Make sure everything is in single-part format for later analysis - JIC
            arcpy.MultipartToSinglepart_management("in_memory\\clip_", output_aggregate_feature)

            # Create the matrix
            logger.console('4.) Creating matrix')

            # Erase all the other fields - ETFP
            erase_fields_lst = [field.name for field in arcpy.ListFields(output_aggregate_feature)]
            for field in erase_fields_lst:
                try:
                    arcpy.DeleteField_management(output_aggregate_feature, field)
                except:
                    # Should minimally fail on OID, Shape, Shape_area, and Shape_length
                    logger.logfile("Delete field failed:", field) 

            # Delete identical features within output_aggregate_feature to prevent double counting
            # Can ues shape ratio field in case of VERY small differences in an 'identical' polygon
            try:
                # Try to match the geometry
                arcpy.DeleteIdentical_management(output_aggregate_feature, "SHAPE")
                logger.logfile("Delete identical succeeded")
            except:
                # This will usually fail - it's ok
                logger.logfile("Delete Identical failed")
                
            # Calculate acres for output_aggregate_field and get acre field name
            acre_field = get_acres(output_aggregate_feature)

            # Create a defaultdict to store acreages - default dictionaries are awesome!
            acreage_counts = defaultdict(int)

            # Iterate across all_fcs_list and add field,
            # select by location and calculate field with ID, remove null
            arcpy.MakeFeatureLayer_management(output_aggregate_feature, "in_memory\\mem_agg_layer")

            # Create a list to store all added field ids
            fc_field_list = []

            logger.console('5.) Populating matrix')
            for fc in all_fcs_list:
                fc_ID = fc_id_map[str(fc)]

                # Copy the created fields for later use in fields summary
                fc_field_list.append(fc_ID)

                # Add field, select, and calculate
                arcpy.AddField_management("in_memory\\mem_agg_layer", 
                                          fc_ID, "Text", field_length=20)
                
                arcpy.SelectLayerByLocation_management("in_memory\\mem_agg_layer", "WITHIN", 
                                                       fc, selection_type="NEW_SELECTION")
                
                arcpy.CalculateField_management("in_memory\\mem_agg_layer",
                                                fc_ID, '"'+fc_ID+'"', "PYTHON_9.3")

                # Get the acres
                fc_acres = sum([row[0] for row in 
                                arcpy.da.SearchCursor("in_memory\\mem_agg_layer", acre_field)])

                # Add key=fc_id and value=acreage to sweet default dictionary
                acreage_counts[fc_ID] = round(fc_acres, 2)

                # Switch the selection
                arcpy.SelectLayerByAttribute_management("in_memory\\mem_agg_layer",
                                                        "SWITCH_SELECTION")

                # Clean the table for readability - replace "Null" with ""
                arcpy.CalculateField_management("in_memory\\mem_agg_layer",
                                                fc_ID, '"'+""+'"', "PYTHON_9.3")
                
                arcpy.SelectLayerByAttribute_management("in_memory\\mem_agg_layer",
                                                        "CLEAR_SELECTION")

            # Write the markup feature to disc
            output_aggregate_feature_markup = output_path+"\\"+analysis_id+"_Restrictions_Markup"
#            output_aggregate_layer_markup = child_folder_path+"\\"+analysis_id_time_stamp+"_Markup.lyr"
            arcpy.CopyFeatures_management("in_memory\\mem_agg_layer",
                                          output_aggregate_feature_markup)
            
            # Create a summary field and get list of other fields
            arcpy.AddField_management(output_aggregate_feature_markup,
                                      "Summary", "Text", field_length=255)
            
            fc_field_list.append('Summary')
            num_fields = len(fc_field_list)
            with arcpy.da.UpdateCursor(output_aggregate_feature_markup, fc_field_list) as cur:
                for row in cur:
# TODO:             # There's gotta be a better way to do this... (!)
                    row[num_fields-1] = re.sub('\s+', ' ', (reduce(lambda x,y: x+" "+y,
                                                 [row[i] for i in range(num_fields-1)]))).strip()
                    
                    cur.updateRow(row)
            
            # Get the total analysis acreage
            arcpy.MakeFeatureLayer_management(output_aggregate_feature_markup, 
                                              "in_memory\\_markup")
            
            total_analysis_acres = sum([row[0] for row in 
                                        arcpy.da.SearchCursor("in_memory\\_markup", acre_field)])
            
            logger.logfile("Total analysis acres", total_analysis_acres)

            # Get the total marked-up acreage
            logger.console('6.) Creating markup output')
            arcpy.SelectLayerByAttribute_management("in_memory\\_markup",
                                                    "NEW_SELECTION", """ "Summary" <> '' """)
            
            # Create a markup only fc - piggyback above selection
            output_aggregate_markup_only = output_path+"\\"+analysis_id+"_Restrictions_Markup_Only"
            arcpy.MakeFeatureLayer_management("in_memory\\_markup", "in_memory\\_markup_only")
            arcpy.CopyFeatures_management("in_memory\\_markup_only", output_aggregate_markup_only)
                        
            total_markup_acres = sum([row[0] for row in 
                                      arcpy.da.SearchCursor("in_memory\\_markup", acre_field)])
            
            logger.logfile("Total markup acres", total_markup_acres)

            # Delete the lingering unmarked output 
            # Comment out to keep original with original fields
            arcpy.Delete_management(output_aggregate_feature)

            # Partition output datasets - Alternatives A and D
            logger.logfile("alternative", alternative)

            # Final clip by management plans or ecoregions

            if alternative == "ALT_A": # --- ALTERNATIVE A ----------------------------------------
                
                # Partition the data sets by management plan areas and write outputs to csv
                logger.console('      Partitioning outputs by previous management plans')
                
                management_plans = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP'\
                                   r'\Draft_RMP_EIS\1_Analysis\ECRMP_Outputs\boundaries'\
                                   r'\boundaries.gdb\ECRMP_NE_RG_PlanBoundaries_AltA_20161213'
                    
                # Create a default dict to hold the values
                management_plan_markup_acres = defaultdict(int)

                # Get a list of plans
                plan_field = "PlanID"  
                plan_list = [str(row[0]) for row in 
                                  arcpy.da.SearchCursor(management_plans, plan_field)]

                logger.logfile("Management_plan_list", plan_list)
                    
                # These will be created by split
                plan_out_names = [output_path+"\\"+plan for plan in plan_list]
                
                # Rename to these:
                plan_rename = [output_path+"\\"+analysis_id+"__"+plan for plan in plan_list]
                logger.logfile("Management_plan_out_names", plan_out_names)
                
                arcpy.Split_analysis(output_aggregate_feature_markup, management_plans,
                                     plan_field, output_path)
               
                # Rename the plan split outputs
                for old_name, new_name in zip(plan_out_names, plan_rename):
                    arcpy.Rename_management(old_name, new_name) 
                
                for plan_fc in plan_rename:
                    # Get the acres
                    acre_field = get_acres(plan_fc)
                    arcpy.MakeFeatureLayer_management(plan_fc, "in_memory\\plan")
                    arcpy.SelectLayerByAttribute_management("in_memory\\plan", 
                                                            "NEW_SELECTION", 
                                                            """ "Summary" <> '' """)
                    
                    plan_acres = sum([row[0] for row in 
                                           arcpy.da.SearchCursor("in_memory\\plan",
                                                                 acre_field)])

                    # Add key=fc_id and value=acreage to sweet default dictionary
                    management_plan_markup_acres[os.path.basename(plan_fc)] = round(plan_acres, 2)
       
            if alternative == "ALT_D": # --- ALTERNATIVE D ----------------------------------------
                
                # Partition the data sets by ecoregion and write outputs to csv
                logger.console('      Partitioning outputs by ecoregions')
                
                ecoregions = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP'\
                             r'\Draft_RMP_EIS\1_Analysis\ECRMP_Outputs\boundaries'\
                             r'\boundaries.gdb\ECRMP_HumanEcoregions_AltD_20161213'
                

                # Create a default dict to hold the values
                ecoregion_markup_acres = defaultdict(int)

                # Get a list of ecoregions
                ecoregion_field = "CommLandID"
                ecoregion_list = [str(row[0]) for row in 
                                  arcpy.da.SearchCursor(ecoregions, ecoregion_field)]

                logger.logfile("Ecoregion_list", ecoregion_list)

                # these will be created by split
                ecoregion_out_names = [output_path+"\\"+er for er in ecoregion_list]
                
                # Rename to these:
                ecoregion_rename = [output_path+"\\"+analysis_id+"__"+er for er in ecoregion_list]
                logger.logfile("Ecoregion_out_names", ecoregion_out_names)
                
                arcpy.Split_analysis(output_aggregate_feature_markup, ecoregions,
                                     ecoregion_field, output_path)
               
                # Rename the ecoregion split outputs
                for old_name, new_name in zip(ecoregion_out_names, ecoregion_rename):
                    arcpy.Rename_management(old_name, new_name) 
                
                for ecoregion_fc in ecoregion_rename:
                    # Get the acres
                    acre_field = get_acres(ecoregion_fc)
                    arcpy.MakeFeatureLayer_management(ecoregion_fc, "in_memory\\ecoregion")
                    arcpy.SelectLayerByAttribute_management("in_memory\\ecoregion", 
                                                            "NEW_SELECTION", 
                                                            """ "Summary" <> '' """)
                    
                    ecoregion_acres = sum([row[0] for row in 
                                           arcpy.da.SearchCursor("in_memory\\ecoregion",
                                                                 acre_field)])

                    # Add key=fc_id and value=acreage to sweet default dictionary
                    ecoregion_markup_acres[os.path.basename(ecoregion_fc)] = round(ecoregion_acres, 2)

            # Write outputs acreages to csv
            logger.console('7.) Writing data')
                    
            outCSV = child_folder_path+"\\"+analysis_id_time_stamp+'_Acreage.csv'
            
            with open(outCSV, 'wb') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(["Total Analysis Acres", str(round(total_analysis_acres, 2))])
                csvwriter.writerow(["", ""])
                csvwriter.writerow(["", ""])
                # Write the criteria data
                csvwriter.writerow(['Resource', analysis_id+"_Raw_Acres",
                                    analysis_id+"_Rounded_Acres", "Raw_Percent"])
                
                for fc_id, acres in sorted(acreage_counts.items()):
                    csvwriter.writerow([fc_id, acres, round(acres, -2),
                                        ((acres/total_analysis_acres)*100)])
                    
                csvwriter.writerow(["", ""])
                csvwriter.writerow(["*Individual resource acreages will not add up to total due to overlap"])
                csvwriter.writerow(["", ""])
                # Write the total data
                csvwriter.writerow(["Total "+analysis_id+" Acres",
                                    round(total_markup_acres, 2),
                                    round(total_markup_acres, -2),
                                    (total_markup_acres/total_analysis_acres)*100])

                if alternative == "ALT_D":
                    # Write the ecoregion data
                    csvwriter.writerow(["", ""])
                    csvwriter.writerow(["", ""])
                    csvwriter.writerow(['Ecoregion', "Raw_Acres", "Rounded_Acres"])
                    for ecoregion, acres in sorted(ecoregion_markup_acres.items()):
                        csvwriter.writerow([ecoregion, acres, round(acres, -2)])
                    csvwriter.writerow(["", ""])
                    csvwriter.writerow(["", ""])

                if alternative == "ALT_A":
                    # Write the management plan data
                    csvwriter.writerow(["", ""])
                    csvwriter.writerow(["", ""])
                    csvwriter.writerow(['Management Plan', "Raw_Acres", "Rounded_Acres"])
                    for plan, acres in sorted(management_plan_markup_acres.items()):
                        csvwriter.writerow([plan, acres, round(acres, -2)])
                    csvwriter.writerow(["", ""])
                    csvwriter.writerow(["", ""])


            logger.log_all('\nSuccessful completion..\n')


###################################################################################################
##
## EXCEPTIONS
##
###################################################################################################

        except:
            try:
                logger.log_all('\n\nTOOL - USE RESTRICTIONS DID NOT SUCCESSFULLY COMPLETE')
                logger.console('See logfile for details')
                logger.log_all('Exceptions:\n')
                logger.log_report('_'*120+'\n')
                logger.log_all(str(traceback.format_exc()))
                ### Maybe add the frame locals inspector exception handler 
            except:
                pass

###################################################################################################
##
## CLEAN-UP
##
###################################################################################################

        finally:
            end_time = datetime.datetime.now()
            try:
                logger.log_all("End Time: "+str(end_time))
                logger.log_all("Time Elapsed: %s" %(str(end_time - start_time)))
            except:
                pass
            deleteInMemory()


###################################################################################################
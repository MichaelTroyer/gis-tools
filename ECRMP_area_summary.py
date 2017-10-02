"""
Land surface and mineral estate ownership analysis

Michael D. Troyer

def deleteInMemory and getErrors by Ben Zank

10/18/2016
"""

import arcpy, sys, os, traceback, datetime, csv
from arcpy import env
env.addOutputsToMap = False
env.overwriteOutput = True

def deleteInMemory():
    #Set the workspace to in_memory
    env.workspace = "in_memory"
    #Delete all in memory feature classes
    fcs = arcpy.ListFeatureClasses()
    if len(fcs) > 0:
        for fc in fcs:
            arcpy.Delete_management(fc)
    #Delete all in memory tables 
    tbls = arcpy.ListTables()
    if len(tbls) > 0:
        for tbl in tbls:
            arcpy.Delete_management(tbl)

def getErrors():
    # Get the traceback object
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # Concatenate information together concerning the error into a message string
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
    # Return python error messages for use in script tool or Python Window
    arcpy.AddError(pymsg)
    arcpy.AddError(msgs)
    return pymsg, msgs

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
        self.label = "Land_Surface_and_Mineral_Estate_Ownership_Analysis"
        self.alias = "Land Surface and Mineral Estate Ownership Analysis"

        # List of tool classes associated with this toolbox
        self.tools = [Land_Surface_and_Mineral_Estate_Analysis]


class Land_Surface_and_Mineral_Estate_Analysis(object):
    def __init__(self):
        self.label = "Land_Surface_and_Mineral_Estate_Ownership_Analysis"
        self.description = "Land_Surface_and_Mineral_Estate_Ownership_Analysis"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Analysis Area
        param0=arcpy.Parameter(
            displayName="Input ECRMP Analysis Area",
            name="Analysis_Area",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygons"]

        # Output Location 
        param1=arcpy.Parameter(
            displayName="Output File Geodatabase Location",
            name="Out_Location",
            datatype="File",
            parameterType="Required",
            direction="Output")

        # Input Land Ownership
        param2=arcpy.Parameter(
            displayName="Input Land Ownership",
            name="Land_Ownership",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        param2.filter.list = ["Polygons"]

        # Input Mineral Estate
        param3=arcpy.Parameter(
            displayName="Input Mineral Estate",
            name="Federal_Mineral_Estate",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        param3.filter.list = ["Polygons"]
       
        parameters = [param0, param1, param2, param3]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        if not parameters[0].altered:
            parameters[0].value = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP\Draft_RMP_EIS\1_Analysis\ECRMP_Outputs\boundaries\boundaries.gdb\ECRMP_PlanBoundary_20161006'

        if not parameters[2].altered:
            parameters[2].value = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP\Draft_RMP_EIS\0_SourceData\lands\lands.gdb\lands_20161014\CO_BLM_LST_SMA_GCDB_dissolve'

        if not parameters[3].altered:
            parameters[3].value = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP\Draft_RMP_EIS\0_SourceData\lands\lands.gdb\lands_20161014\CO_mno_GCDB_dissolve'
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        land_ownership_fields = [f.name for f in arcpy.ListFields(parameters[2].valueAsText)]
        mineral_estate_fields = [f.name for f in arcpy.ListFields(parameters[3].valueAsText)]
        if not "adm_code" in land_ownership_fields:
            parameters[2].setErrorMessage("incorrect data source - input requires field 'adm_code'")
        if not "SubSurRights" in mineral_estate_fields:
            parameters[2].setErrorMessage("incorrect data source - input requires field 'SubSurRights'")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        try:
            # Secure a copy of the input ECRMP boundary
            arcpy.MakeFeatureLayer_management(parameters[0].value, "in_memory\\_")
            arcpy.CopyFeatures_management("in_memory\\_", "in_memory\\ECRMP_boundary")
                                          
            # Make a geodatabase
            time_stamp = str(datetime.date.today())
            database_name = os.path.basename(parameters[1].valueAsText)+"_"+time_stamp+".gdb"
            database_path = os.path.dirname(parameters[1].valueAsText)
            arcpy.CreateFileGDB_management (database_path, database_name, "10.0")
            output_path = database_path+"\\"+database_name

            # Identify spatial reference of ECRMP area
            spatial_ref = arcpy.Describe("in_memory\\ECRMP_boundary").spatialReference
                                          
            # Create two feature datasets: 'Input_Data' for copy of input data, 'Results' for outputs
            arcpy.CreateFeatureDataset_management(output_path, "Input_Data", spatial_ref)
            arcpy.CreateFeatureDataset_management(output_path, "Results", spatial_ref)

            # Identify the analysis layers inputs, IDs, and outputs
            input_params = {'ECRMP_Boundary': parameters[0].ValueAsText,
                            'Surface_Ownership': parameters[2].ValueAsText,
                            'Mineral_Estate': parameters[3].ValueAsText}
            
            # Make a copy of the input data - Input_Data
            for ID, path in sorted(input_params.items()):
                if ID == 'ECRMP_Boundary':
                    # If its the boundary, just copy it
                    boundary_path = output_path+"\\Input_Data\\"+ID 
                    arcpy.CopyFeatures_management(path, boundary_path)
                else:
                    # Clip everything else by the boundary
                    clip_path = output_path+"\\Input_Data\\"+ID 
                    arcpy.Clip_analysis(path, parameters[0].ValueAsText, clip_path)

            # Set the workspace to the output database and get list of feature classes in Input_Data dataset
            arcpy.env.workspace = output_path
            Input_Data_list = arcpy.ListFeatureClasses(feature_dataset="Input_Data")
            
            # Create ACRES field for all inputs - check if exists first
            for fc in Input_Data_list:
                field_list = [field.name.upper() for field in arcpy.ListFields(fc)]
                if not "ACRES" in field_list:
                    arcpy.AddField_management(fc, "ACRES", "DOUBLE", 15, 2)
                # Calculate acres
                arcpy.CalculateField_management(fc, "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")

            boundary_acres = sum([row[0] for row in arcpy.da.SearchCursor(boundary_path, 'ACRES')])
            
            # Open text file for writing path details
            outText = database_path+"\\"+os.path.basename(parameters[1].valueAsText)+"_"+time_stamp+"_Report.txt"
            textFile = open(outText, "w")
            textFile.write("Land Surface and Mineral Estate Ownership Analysis "+str(datetime.datetime.now())+"\n")
            textFile.write("_____________________________________________________________________________"+"\n\n\n")
            for ID, path in sorted(input_params.items()):
                textFile.write(ID+": "+path+"\n\n\n")
            textFile.write("ECRMP AREA ACRES: "+str(round(boundary_acres, 1)))
            textFile.write("\n\n\n\n")
            textFile.close()

            ### These sort and calculate calls should be a function
            # Sort and calculate acres for surface onwership
            surface_owners = {'BLM':0, 'BOR':0, 'DOD':0, 'LOCAL':0, 'NPS':0, 'OTHER':0, 'PRI':0, 'STA':0, 'USFS%':0, 'USFW':0}
            owner_layer = arcpy.MakeFeatureLayer_management(output_path+"\\Input_Data\\Surface_Ownership", "in_memory\\surface_ownership")
            for owner, acres in sorted(surface_owners.items()):
                where = "adm_code LIKE '%s'" %owner
                arcpy.SelectLayerByAttribute_management(owner_layer, "NEW_SELECTION", where)
                # Calculate the acres
                surface_owners[owner] = sum([row[0] for row in arcpy.da.SearchCursor(owner_layer, 'ACRES')])
                # Copy BLM surface to Results
                if owner == 'BLM':
                    blm_surface = output_path+"\\Results\\BLM_Surface"
                    arcpy.CopyFeatures_management(owner_layer, blm_surface)
                # Clear to prevent weirdness
                arcpy.SelectLayerByAttribute_management(owner_layer, "CLEAR_SELECTION")
            # Write the data to file
            textFile = open(outText, "a")
            textFile.write("Surface Ownership")
            textFile.write("\n\n")
            for owner, acres in sorted(surface_owners.items()):
                textFile.write(str(owner).replace('%', "")+": "+str(round(acres, 1))+" acres"+"\n")
            surface_owners_sum = sum(surface_owners.values())
            textFile.write("\n")
            textFile.write("Surface Ownership Sum: %s" %str(round(surface_owners_sum, 1)))
            textFile.write("\n\n\n")
            textFile.close()
            
            # Sort and calculate acres for mineral estate
            mineral_estate = {'All Minerals':0, 'Coal Only':0, 'Oil and Gas Only':0, 'Oil, Gas and Coal Only':0, 'Other':0}
            estate_layer = arcpy.MakeFeatureLayer_management(output_path+"\\Input_Data\\Mineral_Estate", "in_memory\\mineral_estate")
            for estate, acres in sorted(mineral_estate.items()):
                where = "SubSurRights LIKE '%s'" %estate
                arcpy.SelectLayerByAttribute_management(estate_layer, "NEW_SELECTION", where)
                # Calculate the acres
                mineral_estate[estate] = sum([row[0] for row in arcpy.da.SearchCursor(estate_layer, 'ACRES')])
                # Clear to prevent weirdness
                arcpy.SelectLayerByAttribute_management(estate_layer, "CLEAR_SELECTION")
            # Write the data to file
            textFile = open(outText, "a")
            textFile.write("Mineral Estate")
            textFile.write("\n\n")
            for estate, acres in sorted(mineral_estate.items()):
                textFile.write(str(estate)+": "+str(round(acres, 1))+" acres"+"\n")
            mineral_estate_sum = sum(mineral_estate.values())
            textFile.write("\n")
            textFile.write("Mineral Estate Sum: %s" %str(round(mineral_estate_sum, 1)))
            textFile.write("\n\n\n")
            textFile.close()
            
            # Create output Federal Mineral Estate
            federal_mineral_estate_where = buildWhereClauseFromList(output_path+"\\Input_Data\\Mineral_Estate", "SubSurRights",
                                                                    mineral_estate.keys())
            federal_mineral_estate_layer = arcpy.MakeFeatureLayer_management(output_path+"\\Input_Data\\Mineral_Estate",
                                                                             "in_memory\\federal_mineral_estate",
                                                                             federal_mineral_estate_where)
            output_federal_mineral_estate = output_path+"\\Results\\Federal_Mineral_Estate"
            arcpy.CopyFeatures_management(federal_mineral_estate_layer, output_federal_mineral_estate)

            # Clear selections to prevent weirdness        
            arcpy.SelectLayerByAttribute_management(owner_layer, "CLEAR_SELECTION")
            arcpy.SelectLayerByAttribute_management(estate_layer, "CLEAR_SELECTION")
            
            # Create split estate layer
            non_federal_surface_where = buildWhereClauseFromList(owner_layer, 'adm_code', ['STA', 'LOCAL', 'PRI'])
            arcpy.SelectLayerByAttribute_management(owner_layer, "NEW_SELECTION", non_federal_surface_where)
            output_split_estate = output_path+"\\Results\\Split_Estate_Minerals"
            arcpy.Clip_analysis(output_federal_mineral_estate, owner_layer, output_split_estate)
            arcpy.CalculateField_management(output_split_estate, "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")
            
            # Sort and calculate acres for split estate
            split_estate = {'All Minerals':0, 'Coal Only':0, 'Oil and Gas Only':0, 'Oil, Gas and Coal Only':0, 'Other':0}
            split_estate_layer = arcpy.MakeFeatureLayer_management(output_split_estate, "in_memory\\split_estate")
            for estate, acres in sorted(split_estate.items()):
                where = "SubSurRights LIKE '%s'" %estate
                arcpy.SelectLayerByAttribute_management(split_estate_layer, "NEW_SELECTION", where)
                # Calculate the acres
                split_estate[estate] = sum([row[0] for row in arcpy.da.SearchCursor(split_estate_layer, 'ACRES')])
                # Clear to prevent weirdness
                arcpy.SelectLayerByAttribute_management(split_estate_layer, "CLEAR_SELECTION")
            # Write the data to file
            textFile = open(outText, "a")
            textFile.write("Split Estate")
            textFile.write("\n\n")
            for estate, acres in sorted(split_estate.items()):
                textFile.write(str(estate)+": "+str(round(acres, 1))+" acres"+"\n")
            split_estate_sum = sum(split_estate.values())    
            textFile.write("\n")
            textFile.write("Split Estate Sum: %s" %str(round(split_estate_sum, 1)))
            textFile.write("\n\n\n")
            textFile.close()

            # Clear selections to prevent weirdness
            arcpy.SelectLayerByAttribute_management(owner_layer, "CLEAR_SELECTION")
            arcpy.SelectLayerByAttribute_management(estate_layer, "CLEAR_SELECTION")
            
            # Create federal mineral estate decision area
            federal_mineral_decision_where = buildWhereClauseFromList(owner_layer, 'adm_code', ['BLM', 'STA', 'LOCAL', 'PRI', 'OTHER'])
            arcpy.SelectLayerByAttribute_management(owner_layer, "NEW_SELECTION", federal_mineral_decision_where)
            output_federal_mineral_decision = output_path+"\\Results\\Mineral_Estate_Decision_Area"
            arcpy.Clip_analysis(output_federal_mineral_estate, owner_layer, output_federal_mineral_decision)
            arcpy.CalculateField_management(output_federal_mineral_decision, "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")
                    
            # Sort and calculate acres for federal mineral estate decision area
            decision_estate = {'All Minerals':0, 'Coal Only':0, 'Oil and Gas Only':0, 'Oil, Gas and Coal Only':0, 'Other':0}
            estate_decision_layer = arcpy.MakeFeatureLayer_management(output_federal_mineral_decision, "in_memory\\estate_decision")
            for estate, acres in sorted(decision_estate.items()):
                where = "SubSurRights LIKE '%s'" %estate
                arcpy.SelectLayerByAttribute_management(estate_decision_layer, "NEW_SELECTION", where)
                # Calculate the acres
                decision_estate[estate] = sum([row[0] for row in arcpy.da.SearchCursor(estate_decision_layer, 'ACRES')])
                # Clear to prevent weirdness
                arcpy.SelectLayerByAttribute_management(estate_decision_layer, "CLEAR_SELECTION")
            # Write the data to file
            textFile = open(outText, "a")
            textFile.write("Federal Mineral Estate Decision Area")
            textFile.write("\n\n")
            for estate, acres in sorted(decision_estate.items()):
                textFile.write(str(estate)+": "+str(round(acres, 1))+" acres"+"\n")
            decision_estate_sum = sum(decision_estate.values())
            textFile.write("\n")
            textFile.write("Federal Mineral Estate Decision Area Sum: %s" %str(round(decision_estate_sum, 1)))
            textFile.write("\n\n\n")
            textFile.close()

            # Collect the data dictionaries 
            data_dictionaries = {'1surface_owners': [surface_owners, surface_owners_sum],
                                 '2mineral_estate': [mineral_estate, mineral_estate_sum],
                                 '3split_estate': [split_estate, split_estate_sum],
                                 '4decision_estate': [decision_estate, decision_estate_sum]}

            # Iterate over the data dictionary and write data to csv files
            outCSV = database_path+"\\"+os.path.basename(parameters[1].valueAsText)+"_"+time_stamp+"_Acreage_Report.csv"
            with open(outCSV, 'wb') as csvfile:
                csvwriter = csv.writer(csvfile)
                for data_name, data_list in sorted(data_dictionaries.items()):
                    csvwriter.writerow(['Dataset Name', 'Feature ID', "Acres", "Percent"])
                    for id, value in sorted(data_list[0].items()):
                        name = data_name[1:]
                        percent = (value/data_list[1])*100
                        csvwriter.writerow([name, str(id).replace('%', ""), value, percent])
                    csvwriter.writerow(["", "", "", ""])
                    csvwriter.writerow(["", "", "", ""])
                
        except arcpy.ExecuteError: 
            # Get the tool error messages 
            msgs = arcpy.GetMessages(2) 
            # Return the tool error messages 
            arcpy.AddError(msgs)
            
        except:
            getErrors()
       
        finally:
            #Clean everything out
            deleteInMemory()

        return

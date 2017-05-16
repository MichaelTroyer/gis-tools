"""
Retention Criteria Analysis:

Used to identify which retention/disposal criteria are
applicable for an input surface ownership polygon. Writes
results to attribute table.

Michael D. Troyer

def deleteInMemory and getErrors by Ben Zank

09/29/2016
"""

import arcpy, sys, os, traceback, datetime
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


class Toolbox(object):
    def __init__(self):
        self.label = "Retention_Criteria_Analysis"
        self.alias = "Retention_Criteria_Analysis"

        # List of tool classes associated with this toolbox
        self.tools = [Retention_Criteria_Analysis]


class Retention_Criteria_Analysis(object):
    def __init__(self):
        self.label = "Retention_Criteria_Analysis"
        self.description = """Used to identify which retention/disposal criteria are
                            applicable for an input surface ownership polygon. Writes
                            results to attribute table"""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Analysis Area
        param0=arcpy.Parameter(
            displayName="Input Project Analysis Area",
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

        # Retention Criteria
        param2=arcpy.Parameter(
            displayName="Retention Criteria Feature Classes",
            name="Retention_Criteria",
            datatype="Value Table",
            parameterType="Optional",
            direction="Input")
        param2.columns = [['Feature Layer', 'Retention Feature Classes'], ['String', 'Retention ID']]

        # Disposal Criteria
        param3=arcpy.Parameter(
            displayName="Disposal Criteria Feature Classes",
            name="Disposal_Criteria",
            datatype="Value Table",
            parameterType="Optional",
            direction="Input")
        param3.columns = [['Feature Layer', 'Disposal Feature Classes'], ['String', 'Disposal ID']]  

        parameters = [param0, param1, param2, param3]
                  
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        # Get the path and IDs lists make sure no duplicate paths or IDs or spaces in IDs
        if parameters[2].value:
            retention_paths = [path.dataSource for path, _ in parameters[2].value]            
            retention_IDs = [ID.upper() for _, ID in parameters[2].value]

            if "" in retention_IDs:
                parameters[2].setErrorMessage("ID required")
                
            if len(set(retention_paths)) != len(retention_paths):
                parameters[2].setErrorMessage("Duplicate layer input detected: the same layer cannnot be used more than once.")

            if len(set(retention_IDs)) != len(retention_IDs):
                parameters[2].setErrorMessage("Duplicate ID detected: the same retention ID cannnot be used more than once.")

            for ID in retention_IDs:
                if " " in ID:
                    parameters[2].setErrorMessage("Spaces are not allowed in Retention IDs")
                    
        if parameters[3].value:    
            disposal_paths = [path.dataSource for path, _ in parameters[3].value]
            disposal_IDs = [ID.upper() for _, ID in parameters[3].value]

            if "" in disposal_IDs:
                parameters[3].setErrorMessage("ID required")
                
            if len(set(disposal_paths)) != len(disposal_paths):
                parameters[3].setErrorMessage("Duplicate layer input detected: the same layer cannnot be used more than once.")

            if len(set(disposal_IDs)) != len(disposal_IDs):
                parameters[3].setErrorMessage("Duplicate ID detected: the same disposal ID cannnot be used more than once.")
                
            for ID in disposal_IDs:
                if " " in ID:
                    parameters[3].setErrorMessage("Spaces are not allowed in Disposal IDs")
                    
        # Make sure no duplicate values between r/d path parameters
        if parameters[2].value and parameters[3].value:
            if len([path for path in retention_paths if path in disposal_paths]) != 0:
                parameters[2].setErrorMessage("Duplicate layer input detected: the same layer cannnot be used more than once.")
                parameters[3].setErrorMessage("Duplicate layer input detected: the same layer cannnot be used more than once.")          
                            
            # Make sure no duplicate values within or between r/d ID parameters
            if len([ID for ID in retention_IDs if ID.upper() in disposal_IDs]) != 0:
                parameters[2].setErrorMessage("Duplicate ID detected: the same ID cannnot be used more than once.")
                parameters[3].setErrorMessage("Duplicate ID detected: the same ID cannnot be used more than once.")         

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        try:
            # Secure an in_memory copy of the input analysis area
            arcpy.MakeFeatureLayer_management(parameters[0].value, "in_memory\\input_analysis")
            #Make a copy of the input to prevent walking on original
            arcpy.CopyFeatures_management("in_memory\\input_analysis", "in_memory\\_")
            #Make a feature layer for Geoprocessing
            arcpy.MakeFeatureLayer_management("in_memory\\_", "in_memory\\gp_target")
            # Make sure no duplicate spatial features
            arcpy.DeleteIdentical_management("in_memory\\gp_target", ["SHAPE"])
                           
            # Make a geodatabase
            time_stamp = str(datetime.date.today())
            database_name = os.path.basename(parameters[1].valueAsText)+"_"+time_stamp+".gdb"
            database_path = os.path.dirname(parameters[1].valueAsText)
            arcpy.CreateFileGDB_management (database_path, database_name, "10.0")
            output_path = database_path+"\\"+database_name

            # Identify spatial reference of analysis area
            spatial_ref = arcpy.Describe("in_memory\\gp_target").spatialReference
                                          
            # Create two feature datasets: Retention' and 'Disposal for outputs
            if parameters[2].value:
                arcpy.CreateFeatureDataset_management(output_path, "Retention", spatial_ref)
            if parameters[3].value:
                arcpy.CreateFeatureDataset_management(output_path, "Disposal", spatial_ref)

            # Make an on-disc, unaltered copy of the input analysis area
            analysis_area = output_path+"\\"+"Analysis_Area"
            arcpy.CopyFeatures_management("in_memory\\input_analysis", analysis_area)

            # Create ACRES field - check if exists first
            field_list = [field.name for field in arcpy.ListFields("in_memory\\gp_target")]
            if not "ACRES" in field_list:
                arcpy.AddField_management("in_memory\\gp_target", "ACRES", "DOUBLE", 15, 2)
         
            # Calculate starting acres
            arcpy.CalculateField_management("in_memory\\gp_target", "ACRES", "!shape.area@ACRES!", "PYTHON_9.3")
            starting_acres = sum([row[0] for row in arcpy.da.SearchCursor("in_memory\\gp_target",["ACRES"])])
                            
            # Add retention and disposal ID fields
            if parameters[2].value:
                arcpy.AddField_management("in_memory\\gp_target", "Retention", "Text", field_length=255)
            if parameters[3].value:
                arcpy.AddField_management("in_memory\\gp_target", "Disposal", "Text", field_length=255)
            
            # Two ways to handle tracking retention and disposal intersection - matrix of fields, or list in single field
            
            arcpy.MakeFeatureLayer_management("in_memory\\gp_target", "in_memory\\gp_target_layer")

            # Create a table to track added fields - for clean up
            added_fields = []
            if parameters[2].value:
                added_fields.append("Retention")
            if parameters[3].value:
                added_fields.append("Disposal")

            # The creation loops
            if parameters[2].value:
                for path, ID in parameters[2].value:
                    # Copy all the input retention criteria
                    output_retention = output_path+"\\Retention\\"+"Retention_"+ID
                    arcpy.MakeFeatureLayer_management(path, "in_memory\\"+ID)
                    arcpy.CopyFeatures_management("in_memory\\"+ID, output_retention)
                    # Select by location and calculate ID fields with 'Retain' and retention field with list of IDs
                    arcpy.AddField_management("in_memory\\gp_target_layer", ID, "Text", field_length=7)
                    added_fields.append(ID)
                    arcpy.SelectLayerByLocation_management("in_memory\\gp_target_layer", 'INTERSECT', output_retention)
                    expression = "Retain"
                    arcpy.CalculateField_management("in_memory\\gp_target_layer", ID, '"'+expression+'"', "PYTHON_9.3")
                    # Iterate and calculate aggregate disposal field
                    with arcpy.da.UpdateCursor("in_memory\\gp_target_layer", ["Retention", ID]) as cursor:
                        for row in cursor:
                            if row[1] == "Retain":
                                if row[0]:
                                    row[0] = row[0]+", "+ID
                                else:
                                    row[0] = ID
                                cursor.updateRow(row)

            if parameters[3].value:
                for path, ID in parameters[3].value:
                    # Copy all the input disposal criteria
                    output_disposal = output_path+"\\Disposal\\"+"Disposal_"+ID
                    arcpy.MakeFeatureLayer_management(path, "in_memory\\"+ID)
                    arcpy.CopyFeatures_management("in_memory\\"+ID, output_disposal)
                    # Select by location and calculate ID fields with 'Dispose' and disposal field with list of IDs
                    arcpy.AddField_management("in_memory\\gp_target_layer", ID, "Text", field_length=7)
                    added_fields.append(ID)
                    arcpy.SelectLayerByLocation_management("in_memory\\gp_target_layer", 'INTERSECT', output_disposal)
                    expression = "Dispose"
                    arcpy.CalculateField_management("in_memory\\gp_target_layer", ID, '"'+expression+'"', "PYTHON_9.3")
                    # Iterate and calculate aggregate disposal field
                    with arcpy.da.UpdateCursor("in_memory\\gp_target_layer", ["Disposal", ID]) as cursor:
                        for row in cursor:
                            if row[1] == "Dispose":
                                if row[0]:
                                    row[0] = row[0]+", "+ID
                                else:
                                    row[0] = ID
                                cursor.updateRow(row)

            # Clear any lingering selections
            arcpy.SelectLayerByAttribute_management("in_memory\\gp_target_layer", "CLEAR_SELECTION")
            
            # Create two dictionaries for collecting acres and get those acres
            if parameters[2].value:
                retention_layers_acres = {}
                for _, ID in parameters[2].value:
                    layer_acres = sum([row[0] for row in arcpy.da.SearchCursor("in_memory\\gp_target_layer", ["Acres", ID]) if row[1] == "Retain"])
                    retention_layers_acres[ID] = layer_acres
            if parameters[3].value:
                disposal_layers_acres = {}
                for _, ID in parameters[3].value:
                    layer_acres = sum([row[0] for row in arcpy.da.SearchCursor("in_memory\\gp_target_layer", ["Acres", ID]) if row[1] == "Dispose"])
                    disposal_layers_acres[ID] = layer_acres
            
            # Open text file for writing report
            outText = database_path+"\\"+os.path.basename(parameters[1].valueAsText)+"_"+time_stamp+"_Retention_Report.txt"
            textFile = open(outText, "w")
            textFile.write("Retention and Disposal Analysis "+str(datetime.datetime.now())+"\n")
            textFile.write("___________________________________________________________________________________________"+"\n\n\n")
            textFile.write("Retention Criteria:"+"\n\n")
            if parameters[2].value:
                for path, ID in parameters[2].value:
                    textFile.write(ID+": "+path.dataSource+"\n")
                    textFile.write(ID+" identified %d acres for retention" %retention_layers_acres[ID])
                    textFile.write("\n\n")
            else:
                textFile.write("No retention criteria specified")
                textFile.write("\n\n")
                
            if parameters[3].value:    
                textFile.write("\n\n\nDisposal Criteria:"+"\n\n")
                for path, ID in parameters[3].value:
                    textFile.write(ID+": "+path.dataSource+"\n")
                    textFile.write(ID+" identified %d acres for disposal" %disposal_layers_acres[ID])
                    textFile.write("\n\n")
            else:
                textFile.write("No disposal criteria specified")
                textFile.write("\n\n")

            textFile.close()

            # Create management fields
            arcpy.AddField_management("in_memory\\gp_target_layer", "Results", "Text", field_length=10)
            arcpy.AddField_management("in_memory\\gp_target_layer", "Reviewed", "Text", field_length=10)
            arcpy.AddField_management("in_memory\\gp_target_layer", "Resolution", "Text", field_length=50)
            arcpy.AddField_management("in_memory\\gp_target_layer", "Rationale", "Text", field_length=255)
            added_fields.extend(["Results", "Reviewed", "Resolution", "Rationale"])

            # Calculate results field:
            if parameters[2].value and parameters[3].value:
                with arcpy.da.UpdateCursor("in_memory\\gp_target_layer", ['Retention','Disposal','Results']) as cursor:
                    for row in cursor:
                        if row[0] is not None and row[1] is not None: 
                            row[2] = "Conflict"
                        elif row[0] is not None:
                            row[2] = "Retain"
                        elif row[1] is not None:
                            row[2] = "Dispose"
                        else:
                            pass
                        cursor.updateRow(row)
                    
            elif parameters[2].value:
                with arcpy.da.UpdateCursor("in_memory\\gp_target_layer", ['Retention', 'Results']) as cursor:
                    for row in cursor:
                        if row[0] is not None: 
                            row[1] = "Retain"
                        else:
                            pass
                        cursor.updateRow(row)
                    
            elif parameters[3].value:
                with arcpy.da.UpdateCursor("in_memory\\gp_target_layer", ['Disposal','Results']) as cursor:
                    for row in cursor:
                        if row[0] is not None: 
                            row[1] = "Dispose"
                        else:
                            pass
                        cursor.updateRow(row)
                        
            # Clean the table for readability - replace "Null" with " "
            for field in added_fields:
                arcpy.SelectLayerByAttribute_management("in_memory\\gp_target_layer", "NEW_SELECTION", '"'+field+'" IS NULL')
                arcpy.CalculateField_management("in_memory\\gp_target_layer", field, '"'+""+'"', "PYTHON_9.3")

            # Clear last selection and copy analysis area as results dataset
            arcpy.SelectLayerByAttribute_management("in_memory\\gp_target_layer", "CLEAR_SELECTION")
            results_fc = output_path+"\\Results"
            arcpy.CopyFeatures_management("in_memory\\gp_target_layer", results_fc)
        
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

"""
Name:             SHPO_General_Tools.pyt
Author:           Michael D. Troyer
                    with contributions by Benjamin Zank
Date:             August 11, 2016
Version:          2.0 (Beta)
ArcGIS Version:   10.3 (requires Advanced License)

As-is, No Warranty, etc.

Direct comments to:

	Michael Troyer
	mtroyer@blm.gov / 719-269-8587

Upon failure:

    Screenshot the error message
    and the tool input UI [relaunch from results window]

    and send to Michael Troyer at mtroyer@blm.gov

-------------------------------------------------------------------------------
PURPOSE AND USAGE:

The SHPO General Tools script creates output data regarding an input polygon
in order to streamline the collection and input of project data into the SHPO
data system.

Specifically, the SHPO General Tools python toolbox accepts an input polygon and
generates three output data files.

INPUTS:

- A polygon representing a site or survey boundary. The polygon can be multipart
or single part, but must represent a single project. If the input polygon
represents more than one unique project (the project id field returns more
than one unique ID, the tool will exit and direct the user to use a subselection
of the data. The subselection can be performed in ArcMap, using the various
select tools, or within the tool itself. Within the tool dialog, the
user has the ability to select specific features from within the input polygon
according to a FIELD and VALUE query. In this case, the user clicks Selection
Based on Case Value and then selects the appropriate field from the Select
Feature Case Field drop-down. The tool will identify a subset of the feature
layer based on the values contained within the selected field.

OUTPUTS:

1.) A .csv file of the input polygon vertex coordinates in X/Y format. 
The tool will recognize mulitpart features and assign a generic, 
sequential ID to the individual parts so that they can be individually 
recognized and managed within the output .csv file.

2.) A .csv of the PLSS legal location of the input polygon. The .csv contains
the following fields: feature ID, PM, TWN, RNG, SEC, QQ1, and QQ2.

3.) A .txt file with the feature ID, polygon acreage, counties, quads, elevation
at the project centroid, the polygon centroid coordinates in X/Y format (if a
single polygon, the tool will not generate a centroid location for a multipart
or multiple feature since that centroid will likely fall outside the polygon
boundary), and the PLSS location.

The tool will also update the geometry data of the input polygon
(area, perimeter, acres, and X and Y coordinates).
-------------------------------------------------------------------------------
"""

import arcpy, os, sys, traceback, csv
from arcpy import env
env.addOutputsToMap = False
env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.label = "SHPO_General_Tools"
        self.alias = "SHPO_General_Tools"

        # List of tool classes associated with this toolbox
        self.tools = [SHPO_General_Tools]


class SHPO_General_Tools(object):
    def __init__(self):
        self.label = "SHPO_General_Tools"
        self.description = ""
        self.canRunInBackground = False
        
    def getParameterInfo(self):
        # Input Target Shapefile
        param0=arcpy.Parameter(
            displayName="Input Shapefile or Feature Class",
            name="Input_Shape",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygons"]

        # Allow sub-selections
        param1=arcpy.Parameter(
            displayName="Selection Based on Case Value",
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
        
        # Output Location and Name
        param4=arcpy.Parameter(
            displayName="Output Workspace and File Naming Convention",
            name="Out_Name",
            datatype="File",
            parameterType="Required",
            direction="Output")

        # Quad Index
        param5=arcpy.Parameter(
            displayName="Input Quadrangle Index Layer",
            name="Input_Quad",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        
        # County Layer
        param6=arcpy.Parameter(
            displayName="Input County Index Layer",
            name="Input_County",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        
        # DEM
        param7=arcpy.Parameter(
            displayName="Input DEM Raster",
            name="Input_DEM",
            datatype="Raster Layer",
            parameterType="Required",
            direction="Input")
        
        # PLSS
        param8=arcpy.Parameter(
            displayName="Input PLSS Survey Grid Layer",
            name="Input_PLSS",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8]
        return params

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        # Params 0-3 - Input shape and handle sub-selections
        if params[0].value:
            params[1].enabled = "True"
        else:
            params[1].enabled = "False"
            
        if params[1].value == 1:
            fieldtypeList = ["String", "Integer"]
            desc = arcpy.Describe(params[0].value)
            fields = desc.fields
            featurefieldList = [field.name for field in fields if field.type in fieldtypeList]
            params[2].enabled = "True"
            params[2].filter.type = "ValueList"
            params[2].filter.list = featurefieldList
        else:
            params[2].value = ""
            params[2].enabled = "False"
        
        if params[2].value:
            field_select = params[2].value
            arcpy.Frequency_analysis(params[0].value, "in_memory\\field_freq", field_select)
            featurevalueList = []
            for field in fields:
                if field.name == field_select:
                    type = field.type
                    if type == "Integer":
                        where = '"'+field_select+'" IS NOT NULL'
                    elif type == "String":
                        where = '"'+field_select+'" IS NOT NULL AND NOT "'+field_select+'" = '+"'' AND NOT "+'"'+field_select+'" = '+"' '"
            with arcpy.da.SearchCursor("in_memory\\field_freq", [field_select], where)as cursor:
                for row in cursor:
                    featurevalueList.append(row[0])
            featurevalueList.sort()
            params[3].enabled = "True"
            params[3].filter.type = "ValueList"
            params[3].filter.list = featurevalueList
        else:
            params[3].value = ""
            params[3].enabled = "False"

        # Param 5 - Quad default value
        if not params[5].altered:
            params[5].value = " H:\Zone 13 Basemaps - 83\qdindex.shp" 

        # Param 6 - County default value
        if not params[6].altered:
            params[6].value = "H:\Zone 13 Basemaps - 83\Counties.shp" 

        # Param 7 - DEM default value
        # SHPO inDEM = r'H:\Zone 13 Basemaps - 83\
        if not params[7].altered:
            params[7].value = "" 

        # Param 8 - PLSS default value
        if not params[8].altered:
            params[8].value = "H:\ToolboxesArc10\PLSSIntersected.gdb\CO_PLSSIntersected" 
        return

    def updateMessages(self, params):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        if arcpy.CheckProduct("ArcInfo") == "Available":
            return True
        else:
            msg = "ArcGIS for Desktop Advanced License is not available. Install Advanced Licnese and try again."
            sys.exit(msg)

    def execute(self, params, messages):
        # Define workspace locations - can also use os.path.join()
        arcpy.env.workspace = os.path.dirname(params[4].valueAsText)+"\\"+os.path.basename(params[4].valueAsText)
        dirName = os.path.dirname(params[4].valueAsText)
        baseName = os.path.dirname(params[4].valueAsText)+"\\"+os.path.basename(params[4].valueAsText)

        # Define base data sources
        inDEM = params[7].valueAsText
        inQuad = params[5].valueAsText
        inCounty = params[6].valueAsText
        inPLSS = params[8].valueAsText

        # Define Functions:
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

        def selectAndPart(inPoly):
            """Check for subselection and manage singlepart/multipart/multiple parts"""
            # Check for subselection
            if params[1].value == 1:
                desc = arcpy.Describe(inPoly)
                fields = desc.fields
                for field in fields:
                    if field.name == params[2].valueAsText:
                        type = field.type
                        selField = '"'+params[2].valueAsText+'"'
                        selValue = params[3].valueAsText
                        if type == "Integer":
                            where = selField+' = '+selValue
                        elif type == "String":
                            where = selField+' = '+"'"+selValue+"'"      
                arcpy.MakeFeatureLayer_management(inPoly, "in_memory\\selected", where)
            else:
                arcpy.MakeFeatureLayer_management(inPoly, "in_memory\\selected")
            
            # Identify project ID field and get a list of individual project IDs
            desc = arcpy.Describe("in_memory\\selected")
            fieldnames = []
            for field in desc.fields:
                fieldnames.append(field.name)
                
            # for site
            if "SITE_" in fieldnames:
                projID = "SITE_"
            # for survey
            elif "DOC_" in fieldnames:
                projID = "DOC_"
            # if neither parse for shape or fc    
            elif "FID" in fieldnames:
                projID = "FID"
            elif "OBJECTID" in fieldnames:
                projID = "OBJECTID"
           
            # If more than one unique project ID, return with message to use subselection
            projectIDS = []
            with arcpy.da.SearchCursor("in_memory\\selected", projID) as cur:
                for row in cur:
                    projectIDS.append(str(row[0]))       
            uniqueIDS = set(projectIDS)
                
            if not len(uniqueIDS) == 1:
                arcpy.AddMessage("------------------------------------------------------------")
                arcpy.AddMessage("\n The input feature represents more than one unique project.")
                arcpy.AddMessage("\n Please use the field and value subselection function to identify a single project.")
                arcpy.AddMessage("\n The SHPO General Tools script will now exit.\n")
                arcpy.AddMessage("------------------------------------------------------------")
                sys.exit()
                                
            # Check for multiple features of the same project - dissolve on projID
            else:
                if len(projectIDS) > 1:
                    arcpy.Dissolve_management("in_memory\\selected", "in_memory\\singleFeature", [projID])
                else:
                    arcpy.MakeFeatureLayer_management("in_memory\\selected", "in_memory\\singleFeature")
            
            # Check for multipart - create single part and multipart versions
            desc = arcpy.Describe("in_memory\\singleFeature")
            shape_field = desc.ShapeFieldName
            rows = arcpy.SearchCursor("in_memory\\singleFeature")
            for row in rows:
                poly = row.getValue(shape_field)
                if poly.isMultipart:
                    arcpy.MultipartToSinglepart_management("in_memory\\singleFeature", "in_memory\\multiFeatures")
                else:
                    #if singlepart, just create a copy named multipart
                    arcpy.MakeFeatureLayer_management("in_memory\\singleFeature", "in_memory\\multiFeatures") 

            singleFeature = "in_memory\\singleFeature"
            multiFeature = "in_memory\\multiFeatures"
            return singleFeature, multiFeature

        def outTable(inPoly):
            """Creates a table of input ID, quads, counties, and PLSS data"""
            
            # Execute CreateTable
            arcpy.CreateTable_management("in_memory", "output")

            # Add fields to table
            desc = arcpy.Describe(inPoly)
            fieldnames = []
            for field in desc.fields:
                fieldnames.append(field.name)
            # for site
            if "SITE_" in fieldnames:
                projID = "SITE_"
            # for survey
            elif "DOC_" in fieldnames:
                projID = "DOC_"
            # if neither parse for shape or fc    
            elif "FID" in fieldnames:
                projID = "FID"
            elif "OBJECTID" in fieldnames:
                projID = "OBJECTID"

            # Add the fields to the table
            arcpy.AddField_management("in_memory\\output", projID, "TEXT", "", "", 50)
            arcpy.AddField_management("in_memory\\output", "PM", "TEXT","","",6)
            arcpy.AddField_management("in_memory\\output", "TWN", "TEXT","","",6)
            arcpy.AddField_management("in_memory\\output", "RNG", "TEXT","","",6)
            arcpy.AddField_management("in_memory\\output", "SEC", "TEXT","","",4)
            arcpy.AddField_management("in_memory\\output", "QQ1", "TEXT","","",4)
            arcpy.AddField_management("in_memory\\output", "QQ2", "TEXT","","",4)
            
            # Create insert cursor
            inCur = arcpy.da.InsertCursor("in_memory\\output", [projID, "PM", "TWN", "RNG", "SEC", "QQ1", "QQ2"])

            # Peel back input polygon 10 meters to prevent extranneous boundary overlap - particulurly PLSS
            # If poly(s) is too small and gets erased, keep original(s)
            arcpy.MakeFeatureLayer_management(inPoly, "in_memory\\polycopy")
            arcpy.PolygonToLine_management("in_memory\\polycopy", "in_memory\\polylines")
            arcpy.Buffer_analysis("in_memory\\polylines", "in_memory\\polybuffer", 10)
            arcpy.Erase_analysis("in_memory\\polycopy", "in_memory\\polybuffer", "in_memory\\PLSSpoly")
            inResult=int(arcpy.GetCount_management("in_memory\\polycopy").getOutput(0))
            outResult=int(arcpy.GetCount_management("in_memory\\PLSSpoly").getOutput(0))
            if not inResult == outResult:
                arcpy.Delete_management("in_memory\\PLSSpoly")
                arcpy.MakeFeatureLayer_management(inPoly, "in_memory\\PLSSpoly")
            arcpy.Delete_management("in_memory\\polycopy")
            arcpy.Delete_management("in_memory\\polylines")
            arcpy.Delete_management("in_memory\\polybuffer")

            # Intersect locations
            arcpy.Intersect_analysis(["in_memory\\PLSSpoly", inPLSS], "in_memory\\locations", "NO_FID")

            # Secure site/survey id
            inRow0 = str([row[0] for row in arcpy.da.SearchCursor(inPoly, projID)])

            # Sort PLSS            
            freqFields = ["PLSSID","FRSTDIVNO","QQSEC"]
            arcpy.Frequency_analysis("in_memory\\locations", "in_memory\\PLSS", freqFields)
            with arcpy.da.SearchCursor("in_memory\\PLSS", freqFields) as cursor:
                for row in cursor:
                    #inRow[1] = PM
                    inRow1 = str(row[0])[2:4]
                    #inRow[2] = Twn 
                    inRow2 = str(row[0])[5:7]+str(row[0])[8]
                    #inRow[3] = Rng
                    inRow3 = str(row[0])[10:12]+str(row[0])[13]
                    #inRow[4] = Sec
                    inRow4 = str(row[1])
                    #inRow[5] = Quar1
                    inRow5 = str(row[2])[0:2]
                    #inRow[6] = Quar2
                    inRow6 = str(row[2])[2:4]
                    inCur.insertRow([inRow0, inRow1, inRow2, inRow3, inRow4, inRow5, inRow6])

            # Write to .csv - use an intermediate to clean up extraneous fields - OID           
            tempTable = baseName+"_temp.csv"
            outTable = baseName+"_PLSS_Data.csv"
            arcpy.CopyRows_management("in_memory\\output", tempTable)
            arcpy.Delete_management("in_memory\\output")

            # Clean up csv - remove OID field
            with open(tempTable,"rb") as source:
                rdr = csv.reader(source)
                with open(outTable,"wb") as result:
                    wtr = csv.writer(result)
                    for r in rdr:
                        wtr.writerow((r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
            # Clean up
            os.remove(tempTable)
            os.remove(baseName+"_temp.txt.xml")
            os.remove(dirName+"\\"+"schema.ini")
            return        

        def outText(inPoly):
            """Creates a text file of input ID, acreage, county(s),
            quad(s), centroid (if single polygon), and PLSS data"""
            
            # Get project ID 
            desc = arcpy.Describe(inPoly)
            fieldnames = []
            for field in desc.fields:
                fieldnames.append(field.name)
            # for site
            if "SITE_" in fieldnames:
                projID = "SITE_"
            # for survey
            elif "DOC_" in fieldnames:
                projID = "DOC_"
            # if neither parse for shape or fc    
            elif "FID" in fieldnames:
                projID = "FID"
            elif "OBJECTID" in fieldnames:
                projID = "OBJECTID"
                
            # Peel back input polygon boundary 10 meters to prevent
            # extranneous PLSS boundary overlap for PLSS caclculation
            arcpy.MakeFeatureLayer_management(inPoly, "in_memory\\polycopy")
            arcpy.PolygonToLine_management("in_memory\\polycopy", "in_memory\\polylines")
            arcpy.Buffer_analysis("in_memory\\polylines", "in_memory\\polybuffer", 10)
            arcpy.Erase_analysis("in_memory\\polycopy", "in_memory\\polybuffer", "in_memory\\PLSSpoly")
            arcpy.Delete_management("in_memory\\polycopy")
            arcpy.Delete_management("in_memory\\polylines")
            arcpy.Delete_management("in_memory\\polybuffer")

            # Intersect locations
            arcpy.Intersect_analysis(["in_memory\\PLSSpoly", inPLSS, inCounty, inQuad], "in_memory\\locations", "NO_FID")
                
            # Secure site/survey id
            projectValue = ([row[0] for row in arcpy.da.SearchCursor(inPoly, projID)])
            projectID = "Feature ID: "+str(projectValue[0])
            
            # Sort counties
            arcpy.Frequency_analysis("in_memory\\locations", "in_memory\\County", "NAME")
            ###arcpy.Frequency_analysis("in_memory\\locations", "in_memory\\County", "COUNTY") # this is for BLM testing
            countyList = []
            ###with arcpy.da.SearchCursor("in_memory\\County", ["COUNTY"]) as cursor:  # this is for BLM testing
            with arcpy.da.SearchCursor("in_memory\\County", ["NAME"]) as cursor:
                for row in cursor:
                        countyList.append(str(row[0]).title()+" County")
            arcpy.Delete_management("in_memory\\County")
            countyText = "Counties: "+", ".join(countyList)
                        
            # Sort Quads
            arcpy.Frequency_analysis("in_memory\\locations", "in_memory\\Quad", "QUAD_NAME")
            quadList = []
            with arcpy.da.SearchCursor("in_memory\\Quad", ["QUAD_NAME"]) as cursor:
                for row in cursor:
                        quadList.append(str(row[0]).title()+" 7.5'")
            arcpy.Delete_management("in_memory\\Quad")
            quadText = "Quads: "+", ".join(quadList)

            # Extract Elevation at centroid and get centroid location
            # If single polygon, create variable to signal print centroid location - default False
            arcpy.FeatureToPoint_management(inPoly, "in_memory\\centroid", "CENTROID")
            printCentroid = 0
            desc = arcpy.Describe(inPoly)
            shape_field = desc.ShapeFieldName
            rows = arcpy.SearchCursor(inPoly)
            for row in rows:
                poly = row.getValue(shape_field)
                if not poly.isMultipart:
                    printCentroid = 1
                    with arcpy.da.SearchCursor("in_memory\\centroid",["SHAPE@"]) as cursor:
                        for row in cursor:
                            centroidX = row[0].centroid.X
                            centroidY = row[0].centroid.Y
                            centroidPrint = "Polygon centroid: "+str(int(round(centroidX)))+" mE   "+str(int(round(centroidY)))+" mN"
            arcpy.sa.ExtractValuesToPoints("in_memory\\centroid", inDEM, "in_memory\\centValue", "NONE", "VALUE_ONLY")
            elePrint = int(round([row[0] for row in arcpy.da.SearchCursor("in_memory\\centValue", "RASTERVALU")][0]))       
            elevText = "Elevation at project centroid: "+str(elePrint)
            
            # Sort PLSS            
            freqFields = ["PLSSID","FRSTDIVNO","QQSEC"]
            arcpy.Frequency_analysis("in_memory\\locations", "in_memory\\PLSS", freqFields)
            PLSSlist = []
            with arcpy.da.SearchCursor("in_memory\\PLSS", freqFields) as cursor:
                for row in cursor:
                    PMtext = str(row[0])[2:4]
                    TWNtext = str(row[0])[5:7]+str(row[0])[8]
                    RNGtext = str(row[0])[10:12]+str(row[0])[13]
                    SECtext = str(row[1])
                    QQ1text = str(row[2])[0:2]
                    QQ2text = str(row[2])[2:4]
                    PLSSinput = PMtext+" "+TWNtext+" "+RNGtext+" "+SECtext+" "+QQ1text+" "+QQ2text
                    PLSSlist.append(PLSSinput)
                PLSStext = ", ".join(PLSSlist)

            # Calculate acreage and format for print w/ 2 decimal places
            with arcpy.da.UpdateCursor(inPoly,["SHAPE@"]) as cur:
                for row in cur:
                    acreage = row[0].area*0.000247105
                    acreagePrint = "Polygon acreage: %.2f" % acreage
                    
            # Write to text file                    
            outText = baseName+"_Location_Data.txt"
            textFile = open(outText, "w")
            textFile.write(projectID)
            textFile.write("\n")
            textFile.write(acreagePrint)
            textFile.write("\n")
            textFile.write(countyText)
            textFile.write("\n")
            textFile.write(quadText)
            textFile.write("\n")
            textFile.write(elevText)
            textFile.write("\n")
            if printCentroid:
                textFile.write(centroidPrint)
            textFile.write("\n")
            textFile.write("\n")
            textFile.write("PLSS Location")
            textFile.write("\n")
            for plss in PLSSlist:
                textFile.write(plss)
                textFile.write("\n")
            textFile.close()
            return

        def updateInput(inPoly):          
            """Update the input polygon attributes"""
            
            # Check if fields exist - if not, add them
            fields = ["SHAPE@", "AREA", "PERIMETER","ACRES", "X", "Y"]
            fieldList = arcpy.ListFields(inPoly)
            if not "AREA" in fieldList:
                arcpy.AddField_management(inPoly, "AREA", "DOUBLE",15,3)
            if not "PERIMETER" in fieldList:
                arcpy.AddField_management(inPoly, "PERIMETER", "DOUBLE",15,3)
            if not "ACRES" in fieldList:
                arcpy.AddField_management(inPoly, "ACRES", "DOUBLE",15,3)
            if not "X" in fieldList:
                arcpy.AddField_management(inPoly, "X", "LONG",6)
            if not "Y" in fieldList:
                arcpy.AddField_management(inPoly, "Y", "LONG",7)

            # Update the fields        
            with arcpy.da.UpdateCursor(inPoly,fields) as cur:
                for row in cur:
                    row[1] = row[0].area
                    row[2] = row[0].length
                    row[3] = row[0].area*0.000247105
                    row[4] = row[0].centroid.X
                    row[5] = row[0].centroid.Y 
                    cur.updateRow(row)
            return

        def getCoords(inPoly):          
            """Get vertice coordiantes and write to csv, assign arbitrary ID to multiple parts"""
            
            # Create the tables - use an intermediary to clean up fieds
            tempTable = baseName+"_temp.csv"
            outTable = baseName+"_Coordinates.csv"

            # Execute Feature Vertices to Points - THIS REQUIRES AN ADVANCED LICENSE
            arcpy.FeatureVerticesToPoints_management(inPoly, "in_memory\\vertPoints", "ALL")

            # Add Fields XCOORD, YCOORD
            arcpy.AddField_management("in_memory\\vertPoints", "XCOORD", "LONG",6)
            arcpy.AddField_management("in_memory\\vertPoints", "YCOORD", "LONG",7)
            with arcpy.da.UpdateCursor("in_memory\\vertPoints",["SHAPE@", "XCOORD", "YCOORD"]) as cursor:
                for row in cursor:
                    row[1] = row[0].centroid.X
                    row[2] = row[0].centroid.Y
                    cursor.updateRow(row)
            arcpy.DeleteIdentical_management("in_memory\\vertPoints", ["XCOORD", "YCOORD"])
            arcpy.ExportXYv_stats("in_memory\\vertPoints", ["ORIG_FID","XCOORD","YCOORD"], "COMMA", tempTable, "ADD_FIELD_NAMES")

            # Clean up csv - remove OID field
            with open(tempTable,"rb") as source:
                rdr = csv.reader(source)
                with open(outTable,"wb") as result:
                    wtr = csv.writer(result)
                    for r in rdr:
                        if r[2] == "ORIG_FID":
                            r[2] = "ID"
                        wtr.writerow((r[2], r[3], r[4]))

            # Clean up
            os.remove(tempTable)
            os.remove(baseName+"_temp.txt.xml")
            return
        try:
            """With all functions defined, unpack selectAndPart return tuple for use
            in other functions. Execute outTable, outText, updateInput, and getCoords.
            Return exceptions."""
            single, multi = selectAndPart(params[0].value)
            outTable(single)
            outText(single)
            updateInput(params[0].value)
            getCoords(multi)

            
        except SystemExit:
            arcpy.AddMessage("System Exit")
        except arcpy.ExecuteError: 
            # Get the tool error messages 
            msgs = arcpy.GetMessages(2) 
            # Return tool error messages for use with a script tool 
            arcpy.AddError(msgs)
        except:
            getErrors()
            
        finally:
            #Clean everything out
            deleteInMemory()
import os
import re
import arcpy


class Toolbox(object):
    def __init__(self):
        self.label = "Output_Attachments"
        self.alias = "OutputAttachments"
        self.tools = [OutputAttachments]


class OutputAttachments(object):
    def __init__(self):
        self.label = "Output_Attachments"
        self.description = "Output fGDB feature class attachments"
        self.canRunInBackground = True

    def getParameterInfo(self):
        # inFeas, inRows, idFlds, outDir
                
        inFeas=arcpy.Parameter(
            displayName="Input Feature Class",
            name="InFeas",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            )

        inRows=arcpy.Parameter(
            displayName="Input Attachments Table",
            name="InRows",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            )
        
        idFlds=arcpy.Parameter(
            displayName="Feature Class Attachment ID Fields",
            name="idFlds",
            datatype="String",
            parameterType="Required",
            direction="Input",
            multiValue=True,
            )

        outDir=arcpy.Parameter(
            displayName="Output Workspace",
            name="OutDir",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
            )

        return [inFeas, inRows, idFlds, outDir]

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        inFC, inTbl, inFields, outDir = params
        if inFC:
            fields = [f.name for f in arcpy.Describe(inFC).fields]
            inFields.filter.type = "ValueList"
            inFields.filter.list = fields
            if not inTbl.value:
                inTbl.value = inFC.valueAsText + '__ATTACH'
            if not outDir.value:
                outDir.value = os.path.dirname(os.path.dirname(inFC.valueAsText))
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        inFC, inTbl, idFlds, outDir = params

        # Make feature layer or table view
        if hasattr(arcpy.Describe(inFC.value), 'shapeType'):  # is a feature class
            arcpy.MakeFeatureLayer_management(inFC.value, 'in_memory\\lyr')
        else:
            arcpy.MakeTableView_management(inFC.value, 'in_memory\\lyr')

        fcName = os.path.basename(inFC.valueAsText)
        tblName = os.path.basename(inTbl.valueAsText)
        
        dtFlds = ['ATT_NAME', 'DATA']

        idFlds = ['{}.{}'.format(fcName, fld) for fld in idFlds.values]
        dtFlds = ['{}.{}'.format(tblName, fld) for fld in dtFlds]

        # Add join
        arcpy.AddJoin_management('in_memory\\lyr', "GlobalID", inTbl.value, "REL_GLOBALID")

        with arcpy.da.SearchCursor('in_memory\\lyr', idFlds + dtFlds) as cur:
            for row in cur:
                try:
                    name = '_'.join([re.sub('[^0-9a-zA-Z-_.]+', '', str(r)) for r in row[:-1]])
                    data = row[-1]
                    if data:
                        with open(os.path.join(outDir.valueAsText, name), 'wb') as f:
                            f.write(data)
                except:
                    arcpy.AddMessage('[-] Error writing: {}'.format(repr(row)))
                    

        return

import arcpy
import os, re, csv
                

class Toolbox(object):
    def __init__(self):
        """Define the toolbox."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Find_Site_Files]


class Find_Site_Files(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Find Site Files"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input directory
        param0=arcpy.Parameter(
            displayName="Input Site File Directory",
            name="In_Dir",
            datatype="Folder",
            parameterType="Required",
            direction="Input")
        
        #Output Location and Name
        param1=arcpy.Parameter(
            displayName="Output .csv Location and File Name",
            name="Out_Name",
            datatype="File",
            parameterType="Required",
            direction="Output")
        
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, params):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, params, messages):
        """The source code of the tool."""
        
        # Matching 5XXDDDD and 5XXDDDD.D
        regex = re.compile('(5\w{2}\.?[\d]+[\.\d+]*)')     
        
        def regex_match(regex, string):
            fname, ext = os.path.splitext(string)
            if ext.lower() in ['.pdf', '.doc', '.docx']:
                result = regex.match(fname)
                return result if result else None
            
        def find_site_forms(root_path, output_csv):
            paths = []
            for directory, dirnames, filenames in os.walk(root_path):
                for filename in filenames:
                    try:
                        result = regex_match(regex, filename)
                        if result:
                            name = result.group(1).upper()
                            if name[3] == '.':
                                name = name[:3] + name[4:]
                            if len(name.split('.')[0]) < 7:
                                name = name[:3] + '0' + name[3:]
                            paths.append([name, os.path.join(directory, filename)])
                    except Exception as e:
                        print e
            with open(output_csv, 'wb') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(['FEA_ID', 'ATT_PATH'])
                for path in paths:
                    csvwriter.writerow(path)
            return paths
    
        root = params[0].valueAsText
        ocsv = params[1].valueAsText
        if not ocsv.endswith('.csv'):
            ocsv += '.csv'
        find_site_forms(root, ocsv)
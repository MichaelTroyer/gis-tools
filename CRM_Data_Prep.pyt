import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tool"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # param0 - input polygon

        # param1 - output location


        ### options
        # param2 - optionally generalize polygon

        # param3 - optionally split input by zone


        params = None
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # Verify that input is a polygon

        # Defaults
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # output path is real? create directory

        # makeFeatureLayer - 'in_memory\\fc'
        ### required ops

        # Check geometry / repair geometry
        
        # Check for correct projection
        # Capture the projection as a variable - Proj
        # extents = {'NAD12': (N, E, W, S), 'NAD13': (N, E, W, S)}
        # extents[Proj]

        # Verify location (extent)

        # hard coded Colorado's extent
        # NAD 12 extent
        # NAD 13 extent

        # Add metadata?


        ### optional ops

        # optionally generalize polygon

        # optionally split input by zone

        # optionally copy features


        return

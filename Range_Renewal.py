#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#
# FRONT MATTER ----------------------------------------------------------------
#
###############################################################################

"""
Author:
    Michael D. Troyer

Date:
    12/8/2016

Purpose:
    Track Range Renewals

Comments:

"""

###############################################################################
#
# IMPORTS ---------------------------------------------------------------------
#
###############################################################################

from __future__ import division  # Integer division is lame - use // instead
import arcpy
import collections
import csv
import datetime
import getpass
import os
import re
import sys
import textwrap
import traceback

###############################################################################
#
# GLOBALS ---------------------------------------------------------------------
#
###############################################################################

###############################################################################
# Classes
###############################################################################

class py_log(object):
    """A custom logging class that simultaneously writes to the console,
       an optional logfile, and/or a production report. The methods provide
       three means of observing the tool behavior 1.) console progress updates
       during execution, 2.) tool metadata regarding date/user/inputs/outputs..
       and 3.) an optional logfile where the tool will print messages and
       unpack variables for further inspection"""

    def __init__(self, report_path, log_path, log_active=True, rep_active=True):
        self.report_path = report_path
        self.log_path = log_path
        self.log_active = log_active
        self.rep_active = rep_active

    def _write_arg(self, arg, path, starting_level=0):
        """Accepts a [path] txt from open(path)
           and unpacks that data like a baller!"""
        level = starting_level
        txtfile = open(path, 'a')
        if level == 0:
            txtfile.write(header)
        if type(arg) == dict:
            txtfile.write("\n"+(level*"\t")+(str(arg))+"\n")
            txtfile.write((level*"\t")+str(type(arg))+"\n")
            for k, v in arg.items():
                txtfile = open(path, 'a')
                txtfile.write('\n'+(level*"\t\t")+(str(k))+": "+(str(v))+"\n")
                if hasattr(v, '__iter__'):
                    txtfile.write((level*"\t\t")+"Values:"+"\n")
                    txtfile.close()
                    for val in v:
                        self._write_arg(val, path, starting_level=level+2)
        else:
            txtfile.write("\n"+(level*"\t")+(str(arg))+"\n")
            txtfile.write((level*"\t")+str(type(arg))+"\n")
            if hasattr(arg, '__iter__'):  # Does not include strings
                txtfile.write((level*"\t")+"Iterables:"+"\n")
                txtfile.close()
                for a in arg:
                    self._write_arg(a, path, starting_level=level+1)
        txtfile.close()

    def _writer(self, msg, path, *args):
        """A writer to write the msg, and unpacked variable"""
        with open(path, 'a') as txtfile:
            txtfile.write(msg+"\n")
            txtfile.close()
            if args:
                for arg in args:
                    self._write_arg(arg, path)

    def console(self, msg):
        """Print to console only - progress reports"""
        print(msg)  # Optionally - arcpy.AddMessage()

    def report(self, msg):
        """Write to report only - tool process metadata for the user"""
        if self.rep_active:
            path_rep = self.report_path
            self._writer(msg, path_rep)

    def logfile(self, msg, *args):
        """Write to logfile only - use for reporting debugging data
           With an optional shut-off"""
        if self.log_active:
            path_log = self.log_path
            self._writer(msg, path_log, *args)

    def logging(self, log_level, msg, *args):
        assert log_level in [1,2,3], "Incorrect log level"
        if log_level == 1: # Updates - Console, report, and logfile:
            self.console(msg)
            self.report(msg)
            self.logfile(msg, *args)
        if log_level == 2:  # Operational metadata - report and logfile
            self.report(msg)
            self.logfile(msg, *args)
        if log_level == 3:  # Debugging - logfile only
            self.logfile(msg, *args)

###############################################################################
# Functions
###############################################################################

def print_exception_full_stack(lg, print_locals=True):
    """Print full stack in a more orderly way
       Optionally print the exception frame local variables"""
    exc = sys.exc_info()  # 3-tuple (type, value, traceback)
    if exc is None:
        return None

    tb_type, tb_value, tb_obj = exc[0], exc[1], exc[2]
    exc_type = str(tb_type).split(".")[1].replace("'>", '')
    lg.logging(1, '\n\n'+header+'\n'+header)
    lg.logging(1,'\nEXCEPTION:\n{}\n{}\n'.format(exc_type, tb_value))
    lg.logging(1, header+'\n'+header+'\n\n')
    lg.logging(1, 'Traceback (most recent call last):')

    # 4-tuple (filename, line no, func name, text)
    tb = traceback.extract_tb(exc[2])
    for tb_ in tb:
        lg.logging(1, "{}\n"
                   "Filename: {}\n"
                   "Line Number: {}\n"
                   "Function Name: {}\n"
                   "Text: {}\n"
                   "Exception: {}"
                   "".format(header, tb_[0], tb_[1], tb_[2],
                             textwrap.fill(tb_[3]), exc[1]))
    if print_locals:
        stack = []
        while tb_obj.tb_next:
            tb_obj = tb_obj.tb_next  # Make sure at end of stack
        f = tb_obj.tb_frame          # Get the frame object(s)

        while f:                     # Append and rewind, reverse order
            stack.append(f)
            f = f.f_back
        stack.reverse()

        lg.logging(3, '\n\nFrames and locals (innermost last):\n'+header)
        for frame in stack:
            if str(frame.f_code.co_filename).endswith(filename):
                lg.logging(3, "{}\n"
                           "FRAME {} IN:\n"
                           "{}\n"
                           "LINE: {}\n"
                           "".format(header,
                                     textwrap.fill(frame.f_code.co_name),
                                     textwrap.fill(frame.f_code.co_filename),
                                     frame.f_lineno))

                if not frame.f_locals.items():
                    lg.logging(3, "No locals\n")

                else:
                    lg.logging(3, "{} LOCALS:\n".format(frame.f_code.co_name))
                    for key, value in sorted(frame.f_locals.items()):
                        # Exclude private and the i/o and header parameters
                        if not str(key).startswith("_"):
                            if not str(key) in ['In', 'Out', 'header']:
                                lg.logging(3, (str(key)+":").strip())

                                try:
                                    lg.logging(3, str(value).strip()+'\n')
                                except:
                                    lg.logging(3, 'Error writing value')
    return

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
    """Check for an acres field in fc - create if doesn't exist and calculate.
       Recalculate acres and return name of acre field"""

    # Add ACRES field to analysis area - check if exists
    field_list = [field.name for field in arcpy.ListFields(fc)
                  if field.name.upper() == "ACRES"]

    # If ACRES/Acres/acres exists in table, flag for calculation instead
    if field_list:
        acre_field = field_list[0] # select the 'acres' variant
    else:
        arcpy.AddField_management(fc, "ACRES", "DOUBLE", 15, 2)
        acre_field = "ACRES"

    arcpy.CalculateField_management(fc,
                                    acre_field,
                                    "!shape.area@ACRES!",
                                    "PYTHON_9.3")
    acres = sum(row[0] for row in arcpy.da.SearchCursor(fc, acre_field))
    return acre_field, acres

def selectRelatedRecords(sourceLayer, pk, targetLayer, fk):
    """A python implementation of the 'related tables' button in table view"""
    sourceIDs = set([row[0] for row in
                     arcpy.da.SearchCursor(sourceLayer, pk)])
    whereClause = buildWhereClauseFromList(targetLayer, fk, sourceIDs)
    arcpy.SelectLayerByAttribute_management(targetLayer,
                                            "NEW_SELECTION",
                                             whereClause)

###############################################################################
# Variables and settings
###############################################################################

filename = os.path.basename(__file__)

start_time = datetime.datetime.now()

user = getpass.getuser()

working_dir = r'T:\CO\GIS\gisuser\rgfo\mtroyer\a_Projects\_Range'

arcpy.env.addOutputsToMap = False

arcpy.env.overwriteOutput = True

header = ('='*100)

###############################################################################
#
# EXECUTION -------------------------------------------------------------------
#
###############################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "Range_Renewal"
        self.alias = "Range_Renewal"

        # List of tool classes associated with this toolbox
        self.tools = [Range_Renewal, Update_Polygons, Update_Tribal]

class Range_Renewal(object):
    def __init__(self):
        self.label = "Range_Renewal"
        self.description = "Range_Renewal"
        self.canRunInBackground = True

    def getParameterInfo(self):

        #Cultural resources report number
        param0=arcpy.Parameter(
            displayName="Range Renewal Report Number",
            name="Range_Renewal_Report_Number",
            datatype="String",
            parameterType="required",
            direction="Input")

        #NEPA report Number
        param1=arcpy.Parameter(
            displayName="NEPA Report Number",
            name="NEPA_Report_Number",
            datatype="String",
            parameterType="required",
            direction="Input")

        #Allotment selection
        param2=arcpy.Parameter(
            displayName="Range Allotment ID",
            name="Range_Allotment_ID",
            datatype="String",
            parameterType="required",
            direction="Input")

        #Output workspace
        param3=arcpy.Parameter(
            displayName="Output Workspace",
            name="Output_Workspace",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        params = [param0, param1, param2, param3]

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):

        params[0].value = "CR-RG-17-xxx R"

        #Populate list of range allotment IDs
        arcpy.Frequency_analysis('Range_Allotment_Polygons',
                                 'in_memory\\freq',
                                 'ALLOT_NO')
        valueList = []

        with arcpy.da.SearchCursor('in_memory\\freq',
                                   'ALLOT_NO',
                                   '"ALLOT_NO" IS NOT NULL') as cursor:
            for row in cursor:
                valueList.append(row[0])
        valueList.sort()
        params[2].filter.type = "ValueList"
        params[2].filter.list = valueList

        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):

        # Writing params[x]... everywhere is annoying
        rept_id = params[0]
        nepa_id = params[1]
        allt_id = params[2]
        out_loc = params[3]

        try:
            now = datetime.datetime.now()
            date_split = str(datetime.datetime.now()).split('.')[0]
            date_time_stamp = re.sub('[^0-9]', '', date_split)

            output_id = re.sub('[^0-9a-bA-B]', '', rept_id)

            # Create the logger
            text_path = os.path.join(working_dir, 'Range_Logs')
            log_file = os.path.join(text_path, "log.txt")
            rep_file = os.path.join(text_path, "report.txt")
            lg = py_log(rep_file, log_file)
            lg.rep_active = False # Uncomment to disable report

            # Start logging
            lg.logging(1, "\nExecuting: "+filename+' \nDate: '+date_split)
            lg.logging(2, header)
            lg.logging(2, "Running env: Python - {}".format(sys.version))
            lg.logging(1, "User: "+user)

# MAIN PROGRAM ----------------------------------------------------------------

            # Get a copy of the input polygon
            allot_where = '"ALLOT_NO" = '+str(allt_id)
            allot_poly = arcpy.MakeFeatureLayer_management(
                                    'Range_Allotment_Polygons',
                                    'in_memory\\selected',
                                    allot_where)

            arcpy.CopyFeatures_management(allot_poly,
                                          output_id+'_'+allt_id+'.shp')

            # Define some necessary source data
            GCDB = r'T:\ReferenceState\CO\CorporateData\cadastral'\
                   r'\Survey Grid.lyr'

            counties = r'T:\ReferenceState\CO\CorporateData\admin_boundaries'\
                       r'County Boundaries.lyr'

            quads = r'T:\ReferenceState\CO\CorporateData\cadastral'\
                    r'\24k USGS Quad Index.lyr'

            land_ownership = r'T:\ReferenceState\CO\CorporateData\lands'\
                             r'\Land Ownership (No Outline).lyr'

            # Clip the BLM lands out of allotment
            blm_where = buildWhereClauseFromList(land_ownership,
                                                 'adm_manage',
                                                 ['BLM'])

            arcpy.SelectLayerByAttribute_management(land_ownership,
                                                    'NEW_SELECTION',
                                                     blm_where)

            arcpy.Clip_analysis(land_ownership, allot_poly, 'in_memory\\clip')

            # Get the raw allotment acres and BLM only acres
            allot_acres = collections.defaultdict(int)
            allot_acres['Original'] += get_acres(allot_poly)[1]
            allot_acres['BLM'] += get_acres('in_memory\\clip')[1]

            county_ids = []
            quad_ids = []

            #Intersect allotment, counties, and quads
            arcpy.Intersect_analysis([allot_poly, counties, quads],
                                     "in_memory\\intersect",
                                     "NO_FID")

            arcpy.Frequency_analysis("in_memory\\intersect",
                                     "in_memory\\County",
                                     "COUNTY")

            arcpy.Frequency_analysis("in_memory\\intersect",
                                     "in_memory\\Quad",
                                     "QUAD_NAME")

            with arcpy.da.SearchCursor("in_memory\\County",
                                       ["COUNTY"]) as cursor:
                for row in cursor:
                    county_ids.append(str(row[0]))

            with arcpy.da.SearchCursor("in_memory\\Quad",
                                       ["QUAD_NAME"]) as cursor:
                for row in cursor:
                    quad_ids.append(str(row[0]))

            county_str = ', '.join(county_ids[:-1]
                                   )+' and '+county_ids[-1]+' counties'

            quad_str = ', '.join(quad_ids[:-1]
                                 )+' and '+quad_ids[-1]+' 7.5'+"'"+' quads'

            #Intersect survey poly, GCDB Survey Grid, counties, and quad
            arcpy.Intersect_analysis([allot_poly, GCDB],
                                     "in_memory\\gcdb",
                                     "NO_FID")

            gcdb_fields = ["FRSTDIVID","QQSEC"]

            arcpy.Frequency_analysis("in_memory\\gcdb",
                                     "in_memory\\gcdb_freq",
                                     gcdb_fields)


            field_names = ["PM", "Twn", "Rng", "Section", "QQ1", "QQ2"]
            csv_rows = []

            with arcpy.da.SearchCursor("in_memory\\gcdb_freq",
                                       gcdb_fields) as cursor:
                for row in cursor:
                    #inRow[0] = PM
                    r0 = str(row[0])[2:4]
                    #inRow[1] = Twn
                    r1 = str(row[0])[5:7]+str(row[0])[8]
                    #inRow[2] = Rng
                    r2 = str(row[0])[10:12]+str(row[0])[13]
                    #inRow[3] = Sec
                    r3 = str(row[0])[-3:-1]
                    #inRow[4] = QQ1
                    r4 = str(row[1])[0:2]
                    #inRow[5] = QQ2
                    r5 = str(row[1])[2:4]

                    csv_rows.append([r0, r1, r2, r3, r4, r5])

#TODO  - find a way to sort and compress entries in table

            outCSV = output_id+'_'+allt_id+'.csv'
            with open(outCSV, 'wb') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(field_names)
                for row in csv_rows:
                    csvwriter.writerow(row)

            legal_desc_tr =  list(set(' '.join(['PM '+row[0],
                                                'Twn '+row[1],
                                                'Rng '+row[2]]
                                                 for row in csv_rows)))

            # Clip sites and surveys, generate lists of PKs
            # And calculate survey coverage
            sites = r'T:\CO\GIS\gistools\tools\Cultural'\
                    r'\BLM_Cultural_Resources\Sites.lyr'

            surveys = r'T:\CO\GIS\gistools\tools\Cultural'\
                      r'\BLM_Cultural_Resources\Surveys.lyr'

            out_path = os.path.join(working_dir, '_exchange')
            out_sites_name = output_id+'_'+allt_id+'sites.shp'
            out_surveys_name = output_id+'_'+allt_id+'surveys.shp'
            out_sites = os.path.join(out_path, out_sites_name)
            out_surveys = os.path.join(out_path, out_surveys_name)

            arcpy.Clip_analysis(sites, allot_poly, out_sites)
            arcpy.Clip_analysis(surveys, allot_poly, out_surveys)

            # Get list of surveys and sum coverage acres
            surveys_dict = {'Surveys' :  [],
                          'Coverage' : 0}

            for row in arcpy.da.SearchCursor(out_surveys, 'SHPO_ID'):
                surveys_dict['Surveys'].append(row[0])
            surveys_dict['Coverage'] = get_acres(out_surveys)[1]

            # Get list of sites total and eligible sites specifically
            sites_dict = {'Sites'    : [],
                          'Eligible' : []}

            for row in arcpy.da.SearchCursor(out_sites, 'SITE_ID'):
                sites_dict['Sites'].append(row[0])

            eligible = ['ELIGIBLE', 'CONTRIBUTING', 'SUPPORTING',
                        'WITHIN ELIGIBLE DISTRICT', 'LISTED NATIONAL',
                        'NATIONAL LANDMARK', 'LISTED STATE', 'LOCAL LANDMARK',
                        'NOMINATED STATE', 'DELISTED']

            sites_where = buildWhereClauseFromList(out_sites,
                                                   'ELIGIBLE',
                                                    eligible)

            arcpy.SelectLayerByAttribute_management(out_sites,
                                                    'NEW_SELECTION',
                                                     sites_where)

            for row in arcpy.da.SearchCursor(out_sites, 'SITE_ID'):
                sites_dict['Eligible'].append(row[0])

            # Make a map
            mxd_name = output_id+'_'+allt_id+'.mxd'
            mxd_loc = os.path.join(working_dir, '_exchange')
            mxd = os.path.join(mxd_loc, mxd_name)

            temp_mxd = os.path.join(working_dir,
                                    '_templates\Range_Renewal_Temp.mxd')

            df = arcpy.mapping.ListDataFrames(temp_mxd)[0]

            # Update report elements
            data_dict = {'ProjectID': rept_id,
                         'Title'    : "Range Renewal Allotment ID: "+allt_id,
                         'Author'   : "Michael D. Troyer",
                         'Date'     : str(now.month)+"\\"+str(now.year),
                         'Location' : '\n'.join(legal_desc_tr),
                         'County'   : county_str,
                         'Quad'     : quad_str}

            for item in arcpy.mapping.ListLayoutElements(temp_mxd):
                if item.name in data_dict:
                    ePX = item.elementPositionX  # get the item position
                    item.text = data_dict[item]
                    item.elementPositionX = ePX  # reset the item position

            # Add Layer to map
            allot_lyr = arcpy.mapping.Layer(allot_poly)
            arcpy.mapping.AddLayer(df, allot_lyr, "TOP")

            # Set visible layers
            for item in arcpy.mapping.ListLayers(temp_mxd, data_frame=df):
                if item.supports("VISIBLE") == "True":
                    item.visible = "False"
            arcpy.RefreshActiveView
            arcpy.RefreshTOC

            # Set scale and pan to extent
            desc = arcpy.Describe(allot_poly)
            new_extent = desc.extent
            df.extent = new_extent
            df.scale = 24000

            # Save as new mxd
            mxd.saveACopy(mxd_name)

#TODO - update range renewal table with calculated percent inventoried

# EXCEPTIONS ------------------------------------------------------------------

        except:
            print_exception_full_stack(lg, print_locals=True)

            # Don't create exceptions in the except block!
            try:
                lg.logging(1, '\n\n{} did not complete'.format(filename))
                lg.console('See logfile for details')

            except:
                pass

# CLEAN-UP --------------------------------------------------------------------


        finally:
            end_time = datetime.datetime.now()
            elapsed_time = str(end_time - start_time)

            try:
                lg.logging(1, "End Time: "+str(end_time))
                lg.logging(1, "Time Elapsed: {}".format(elapsed_time))

            except:
                pass


###############################################################################
#
# DB Maintenance Tools---------------------------------------------------------
#
###############################################################################

class Update_Polygons(object):
    def __init__(self):
        self.label = "Update_Polygons"
        self.description = "Update_Polygons"
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        return


class Update_Tribal(object):
    def __init__(self):
        self.label = "Update_Tribal"
        self.description = "Update_Tribal"
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        return

###############################################################################
# if this .py has been called by interpreter directly and not by another module
# __name__ == "__main__":  #will be True, else name of importing module
#if __name__ == "__main__":

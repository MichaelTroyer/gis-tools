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


Purpose:


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

working_dir = r''

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
        self.label = "Temp"
        self.alias = "Temp"

        # List of tool classes associated with this toolbox
        self.tools = [Temp]

class Temp(object):
    def __init__(self):
        self.label = "Temp"
        self.description = "Temp"
        self.canRunInBackground = True

    def getParameterInfo(self):

        #Cultural resources report number
        param0=arcpy.Parameter(
            displayName='',
            name= '',
            datatype= '',
            parameterType= 'required',
            direction='Input')

        params = [param0]

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):


        try:
            now = datetime.datetime.now()
            date_split = str(datetime.datetime.now()).split('.')[0]
            date_time_stamp = re.sub('[^0-9]', '', date_split)

            # Create the logger
            text_path = os.path.join(working_dir, 'Logs')
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
# if this .py has been called by interpreter directly and not by another module
# __name__ == "__main__":  #will be True, else name of importing module
#if __name__ == "__main__":

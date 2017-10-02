# -*- coding: utf-8 -*-

"""
Created on Fri Feb 10 10:34:45 2017

@author: mtroyer
"""

import os
import csv
import sys
import arcpy
import traceback

    
def job_queue(toolbox_path, tool_name, tool_alias, csv_path, start=0, stop=None):
    """Read a csv for a list of job parameters between start and stop (non-inclusinve),
       convert to dict, and hand off to a python toolbox."""

    # Make sure everything makes sense
    assert os.path.exists(toolbox_path), "Toolbox not found"
    assert os.path.exists(csv_path), "CSV file not found"
    assert type(start) == int, "Invalid start row (must be int)"
    if stop:
        assert type(stop) == int, "Invalid stop row (must be int)"
        assert stop > start, "Invalid start-stop sequence"
    
    # Import the toolbox and get the alias
    toolbox = arcpy.ImportToolbox(toolbox_path, tool_alias)
    
    # Open and read csv within 'start' and 'stop' - get header and zip rows 
    # (tuple) with header  and convert to dict as {header: value}
    # get a list of dicts representing the parameter inputs, i.e. jobs
    with open(csv_path, 'r') as f:
        csv_reader = csv.reader(f)
        header = csv_reader.next()
        params = [dict(zip(header, row)) for row in csv_reader][start:stop]
    assert params, "No Records Returned"

    tool_exec = eval('toolbox'+"."+tool_name)
    errors = []
    for param in params:
        try:
            exc = tool_exec(**param)
        except:
            err_info = sys.exc_info()[1]
            error_param = 'FAILURE: ' + \
                          param['Alternative'] + ' ' +\
                          param['Analysis_Area_Type'] + ' ' + \
                          param['Use_Restriction_Type']
            errors.append([error_param, err_info])            
            
    return errors


def main(start=0, stop=None):
    
    tpath = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP\Draft_RMP_EIS'\
            r'\1_Analysis\ECRMP_Working\_Development\Use_Restrictions.pyt'
    cpath = r'T:\CO\GIS\giswork\rgfo\projects\management_plans\ECRMP\Draft_RMP_EIS'\
            r'\1_Analysis\ECRMP_Working\_Development\Use_Restrictions_Params.csv'
   
    jobs = job_queue(
               toolbox_path=tpath,
               tool_name='UseRestrictions',
               tool_alias='useRestrictionTools',
               csv_path=cpath,
               start=start,
               stop=stop)
    
    return jobs if jobs else "Completed Successfully"

    

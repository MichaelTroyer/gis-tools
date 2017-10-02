# -*- coding: utf-8 -*-
"""
Created on Mon Dec 26 09:56:38 2016

@author: mtroyer
"""

# test_multiprocessing.pyt
import os, sys
import multiprocessing
import arcpy

# Any functions you want to run as a child process MUST be in
# an importable module. A *.pyt is not importable by python
# Otherwise you'll get 
#     PicklingError: Can't pickle <type 'function'>: attribute lookup __builtin__.function failed
# Also make sure the code that _does_ the multiprocessing is in an importable module
# Otherwise you'll get 
#     AssertionError: main_name not in sys.modules, main_name
from test_multiprocessing_functions import execute

class Toolbox(object):
    def __init__(self):
        '''Define toolbox properties (the toolbox name is the .pyt filename).'''
        self.label = 'Test Multiprocessing'
        self.alias = 'multiprocessing'

        # List of tool classes associated with this toolbox
        self.tools = [TestTool]

class TestTool(object):
    def __init__(self):

        self.label = 'Test Multiprocessing'
        self.description = 'Test Multiprocessing Tool'
        self.canRunInBackground = True
        self.showCommandWindow = False

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def getParameterInfo(self):
        '''parameter definitions for GUI'''

        return [arcpy.Parameter(displayName='Input Rasters',
                                name='in_rasters',
                                datatype='DERasterDataset',
                                parameterType='Required',
                                direction='Input',
                                multiValue=True)]


    def execute(self, parameters, messages):
        # Make sure the code that _does_ the multiprocessing is in an importable module, not a .pyt
        # Otherwise you'll get 
        #     AssertionError: main_name not in sys.modules, main_name
        rasters = parameters[0].valueAsText.split(';')
        for raster in rasters:
            messages.addMessage(raster)

        execute(*rasters)
        
#test_multiprocessing_functions.py
#  - Always run in foreground - unchecked
#  - Run Python script in process - checked

import os, sys, tempfile
import multiprocessing
import arcpy
from arcpy.sa import *

def execute(*rasters):

    for raster in rasters:
        arcpy.AddMessage(raster)

    #Set multiprocessing exe in case we're running as an embedded process, i.e ArcGIS
    #get_install_path() uses a registry query to figure out 64bit python exe if available
    multiprocessing.set_executable(os.path.join(get_install_path(), 'pythonw.exe'))

    #Create a pool of workers, keep one cpu free for surfing the net.
    #Let each worker process only handle 10 tasks before being restarted (in case of nasty memory leaks)
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1, maxtasksperchild=10)

    # Simplest multiprocessing is to map an iterable (i.e. a list of things to process) to a function
    # But this doesn't allow you to handle exceptions in a single process
    ##output_rasters = pool.map(worker_function, rasters)

    # Use apply_async instead so we can handle exceptions gracefully
    jobs={}
    for raster in rasters:
        jobs[raster]=pool.apply_async(worker_function, [raster]) # args are passed as a list
    for raster,result in jobs.iteritems():
        try:
            result = result.get()
            arcpy.AddMessage(result)
        except Exception as e:
            arcpy.AddWarning('{}\n{}'.format(raster, repr(e)))

    pool.close()
    pool.join()


def get_install_path():
    ''' Return 64bit python install path from registry (if installed and registered),
        otherwise fall back to current 32bit process install path.
    '''
    if sys.maxsize > 2**32: return sys.exec_prefix #We're running in a 64bit process

    #We're 32 bit so see if there's a 64bit install
    path = r'SOFTWARE\Python\PythonCore\2.7'

    from _winreg import OpenKey, QueryValue
    from _winreg import HKEY_LOCAL_MACHINE, KEY_READ, KEY_WOW64_64KEY

    try:
        with OpenKey(HKEY_LOCAL_MACHINE, path, 0, KEY_READ | KEY_WOW64_64KEY) as key:
            return QueryValue(key, "InstallPath").strip(os.sep) #We have a 64bit install, so return that.
    except: return sys.exec_prefix #No 64bit, so return 32bit path

def worker_function(in_raster):
    ''' Make sure you pass a filepath to raster, NOT an arcpy.sa.Raster object'''

    ## Example "real" work" (untested)
    ## Make a unique scratch workspace
    #scratch =  tempfile.mkdtemp()
    #out_raster = os.path.join(scratch, os.path.basename(in_raster))
    #arcpy.env.workspace = scratch
    #arcpy.env.scratchWorkspace=scratch
    #ras = Raster(in_raster)
    #result = Con(IsNull(ras), FocalStatistics(ras), ras)
    #result.save(out_raster)
    #del ras, result
    #return out_raster # leave calling script to clean up tempdir.
                       # could also pass out_raster in as a arg,
                       # but you'd have to ensure no other child processes
                       # are writing the that dir when the current
                       # child process is...

    # Do some "fake" work
    import time, random
    time.sleep(random.randint(0,20)/10.0) #sleep for a bit to simulate work
    return in_raster[::-1] #Return a reversed version of what was passed in


if __name__=='__main__':
    # import current script to avoid:
    #     PicklingError: Can't pickle <type 'function'>: attribute lookup __builtin__.function failed
    import test_multiprocessing_functions

    rasters = arcpy.GetParameterAsText(0).split(';')
    for raster in rasters:
        arcpy.AddMessage(raster)

    test_multiprocessing_functions.execute(*rasters)

       
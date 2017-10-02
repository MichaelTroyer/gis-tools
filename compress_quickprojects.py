import os
import arcpy

path = r'T:\CO\GIS\gisuser\rgfo\mtroyer\a-Projects\crrg17071p_Salida_HLI'

qps = [os.path.join(path, d) for d in os.listdir(path) if d.startswith('QuickProject')]

pts = []
lns = []
ply = []

for qp in qps:
    arcpy.env.workspace = qp
    pts.extend([os.path.join(qp, f) for f in arcpy.ListFeatureClasses() if f.startswith('Points')])
    lns.extend([os.path.join(qp, f) for f in arcpy.ListFeatureClasses() if f.startswith('Lines')])
    ply.extend([os.path.join(qp, f) for f in arcpy.ListFeatureClasses() if f.startswith('Polygons')])

arcpy.Merge_management(pts, os.path.join(path, 'QuickProject_Points'))
arcpy.Merge_management(lns, os.path.join(path, 'QuickProject_Lines'))
arcpy.Merge_management(ply, os.path.join(path, 'QuickProject_Polygons'))
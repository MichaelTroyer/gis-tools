# -*- coding: utf-8 -*-
"""
Created on Fri Apr 28 09:40:16 2017

@author: mtroyer

Used to get the maximum X,Y extent of a feature and the long-axis 
measurements of the minimum boundng rectangle

Hacked from Bounding Containers by Dan Patterson http://www.arcgis.com/home/
item.html?id=564e2949763943e3b9fb4240bab0ca2f
"""
 
from __future__ import division
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import pandas as pd
import math


# Constants
degToRad = math.pi/180.0
radToDeg = 180.0/math.pi


# Functions
def p1p2Dist(pnt1, pnt2):
    """
    Returns the distance between two different points
    """
    dY = pnt2[1] - pnt1[1]
    dX = pnt2[0] - pnt1[0]
    dist = math.hypot(dX,dY)
    return dist
  
  
def p1p2Angle(pnt1, pnt2):
    """
    Returns the angle between two different points relative to the x axis
    """
    dY = pnt2[1] - pnt1[1]
    dX = pnt2[0] - pnt1[0]
    theAngle = math.atan2(dY,dX)*radToDeg
    return theAngle

  
def p1p2Azimuth(pnt1, pnt2):
    """
    Returns the azimuth in the range 0 to 360, relative to north.
    """
    dY = pnt2[1] - pnt1[1]
    dX = pnt2[0] - pnt1[0]
    z = 90 - math.atan2(dY,dX)*radToDeg
    theAngle = (z + 360.0) % 360.0
    return theAngle
  

def extentPnts(pnts):
    """Returns the min, max X, Y of input points"""
    xList = []; yList = []
    for pnt in pnts:
        xList.append(pnt[0]); yList.append(pnt[1])
    L = min(xList); R = max(xList); B = min(yList); T = max(yList)
    LL = [L,B]; UL = [L,T]; UR = [R,T]; LR = [R,B]
    return [LL, UL, UR, LR]


def extentCenter(pnts):
    """Returns the average and median X, Y coordinates of a series
       of input points"""
    xList = []; yList = []
    for pnt in pnts:
        xList.append(pnt[0]); yList.append(pnt[1])
    L = min(xList); R = max(xList); B = min(yList); T = max(yList)
    Xcent = (R - L)/2.0 + L; Ycent = (T - B)/2.0 + B
    return [Xcent, Ycent]


def polyAngles(pnts):
    """
    Requires:  a list of points forming a polygon
    Returns:   a list containing from pnt, to pnt, anAngle, aDistance
    """
    pnts2 = pnts[:]
    if pnts2[0] != pnts2[-1]:
        N = len(pnts2)
        # Add the first point to the list
        pnts2.append(pnts2[0])
    else:
        N = len(pnts2) - 1
    angleList = []  
    for i in range(1, len(pnts2)):
        pnt1 = pnts2[i-1];  pnt2 = pnts2[i]
        if pnt1 != pnt2:
            theAngle = p1p2Angle(pnt1, pnt2)
            theDist = p1p2Dist(pnt1, pnt2)
        if i < N:
            angleList.append([i-1, i, theAngle, theDist])
        else:
            angleList.append([i-1, 0, theAngle, theDist])
    return angleList

  
def transRotatePnts(pnts, pntCent, angle):
    """
    Requires a list of points, an extent point and an angle in degrees.
    Translates and rotates points about the origin using the negative angle
    formed between the points.
    """
   
    X0 = pntCent[0]; Y0 = pntCent[1]
    # Check for a duplicate closure point
    if pnts[0] != pnts[-1]:
        N = len(pnts)
    else:
        N = len(pnts)-1
    #translate and rotate shapes and determine area
    angle = angle*(-1.0) #reverse the rotation
    cosXY = math.cos(degToRad * angle) 
    sinXY = math.sin(degToRad * angle)
    rotPnts = []
    for j in range(0, N):
        X1 = pnts[j][0] - X0; Y1 = pnts[j][1] - Y0
        X = (X1 * cosXY) - (Y1 *sinXY)
        Y = (X1 * sinXY) + (Y1 *cosXY)
        pnt = [X, Y]
        rotPnts.append(pnt)
    #Return the rotated points and the centre
    return rotPnts
  
  
def minRect(pnts):
    """
    Determines the minimum area rectangle for a shape represented
    by a list of points
    """
    areaDict = {}
    angleList = polyAngles(pnts)  #determine the angles
    pntCent = extentCenter(pnts)  #determine center of the extent
    xCent = pntCent[0]; yCent = pntCent[1]
    for angle in angleList:
        rotPnts = transRotatePnts(pnts, pntCent, angle[2])  #slice the angle
        Xs = []; Ys = []
        for pnt in rotPnts:
            Xs.append(pnt[0]); Ys.append(pnt[1])
        #Determine the area of the rotated hull
        Xmin = min(Xs); Xmax = max(Xs); Ymin = min(Ys); Ymax = max(Ys)
        area = (max(Xs) - min(Xs))*(max(Ys) - min(Ys))
        areaDict.update({area:[pntCent, Xmin, Xmax, Ymin, Ymax,angle[2]]})
    #Get the minimum rectangle centred about the origin
    #Rotate the rectangle back
    minArea = min(areaDict.keys())
    a = areaDict.get(minArea)
    Xmin = a[1];  Xmax = a[2]
    Ymin = a[3];  Ymax = a[4]
    angle = a[5] * (-1.0)
    rectPnts = [[Xmin,Ymin], [Xmin,Ymax], [Xmax,Ymax], [Xmax,Ymin]]
    originPnt = [0.0,0.0]
    rotPnts = transRotatePnts(rectPnts, originPnt, angle)
    outList = []
    xyPnts = []
    for pnt in rotPnts:
        XY = [pnt[0] + xCent, pnt[1] + yCent]
        xyPnts.append(XY)
    dx = Xmax - Xmin       
    dy = Ymax - Ymin
    outList = [xyPnts, angle, dx, dy]
    #return the points
    return outList

  
###---------------------------------------------------------------------------

        
def main():
    pnts = [(1, 2), (2, 1), (2, 3), (6, 2), (7, 4), (3, 7), (9, 9)] 
    labels = [i for i in range(len(pnts))]

    # Get extent, centroid, and minimum bounding rectangle
    extent = extentPnts(pnts)
    center = extentCenter(pnts)
    min_boundary = minRect(pnts)
    
    # Plot it
    pts_xs, pts_ys = zip(*pnts)
    ext_xs, ext_ys = zip(*extent)
    plt.scatter(pts_xs, pts_ys, marker='o', color='b', label='points')
    plt.scatter(ext_xs, ext_ys, marker='x', color='r', label='extent')
    plt.scatter(center[0], center[1], marker='x', color='k', label='center')
    plt.axes().set_aspect('equal')
    
    # Label the points
    for label, x, y in zip(labels, pts_xs, pts_ys):
        plt.annotate(label, xy=(x, y), xytext=(0, 10),
            textcoords='offset points', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', fc='grey', alpha=0.25))
        
    # Plot the minimum bounding rectangle
    verts = min_boundary[0] + [min_boundary[0][0]]
    codes = [Path.MOVETO, 
             Path.LINETO,
             Path.LINETO,
             Path.LINETO,
             Path.CLOSEPOLY,]
    
    path = Path(verts, codes)
    patch = patches.PathPatch(path, facecolor='None', lw=1)
    ax = plt.gca()
    ax.add_patch(patch)

    # Get better x and y ranges
    max_x = max(v[0] for v in min_boundary[0])
    min_x = min(v[0] for v in min_boundary[0])
    max_y = max(v[1] for v in min_boundary[0])
    min_y = min(v[1] for v in min_boundary[0])
    plt.axis([min_x, max_x, min_y, max_y])
    plt.show()
    
    print
    print 'Source Points:'
    pnt_df = pd.DataFrame(pnts, columns=['X', 'Y'])
    print pnt_df
    print
    print 'Maximum Extent Points:'
    ext_df = pd.DataFrame(extent, columns=['x', 'y'])
    print ext_df
    print
    print 'Centroid: {}'.format(center)
    print
    print 'Point Relationships:'
    columns = ['src', 'dst', 'angle', 'distance']
    ang_df = pd.DataFrame(polyAngles(pnts), columns=columns)
    print ang_df
    print
    print 'Minimum Bounding Rectangle Points:'
    mbr_df = pd.DataFrame(min_boundary[0], columns=['x', 'y'])
    print mbr_df
    print
    print 'Minimum Bounding Rectangle Angle: \n{:.5} degrees'\
        .format(min_boundary[1])
    print
    print 'Axis 1 Extent:\n{:.5}'.format(min_boundary[2])
    print
    print 'Axis 2 Extent:\n{:.5}'.format(min_boundary[3])
    print
    print 'Minimum Bounding Rectangle Area:\n{}'\
        .format(min_boundary[2] * min_boundary[3])
  
    return min_boundary, ext_df, ang_df
    
if __name__ == '__main__':
    results = main()
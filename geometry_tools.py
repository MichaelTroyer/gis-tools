# -*- coding: utf-8 -*-
"""
Created on Fri Apr 28 09:40:16 2017

@author: mtroyer
"""

'''
Sourced from Bounding Containers by Dan Patterson
http://www.arcgis.com/home/
item.html?id=564e2949763943e3b9fb4240bab0ca2f
'''
#---------------------------------------------------------------------
#required modules
from __future__ import division
import math
#
#constants
degToRad = math.pi/180.0
radToDeg = 180.0/math.pi
#
#---------------------------------------------------------------
def circleMake(aPnt,aRadius):
  '''create a circle from a point [X,Y] and radius
     returns a list of points representing the circle as an Ngon
  '''
  X0, Y0 = aPnt[0], aPnt[1]
  X1, Y1 = X0 + aRadius, Y0
  circPnts = [[X1, Y1]]
  for i in range(1,360):
    X = X0 + math.cos(degToRad * i) * aRadius
    Y = Y1 + math.sin(degToRad * i) * aRadius
    circPnt = [X,Y]
    circPnts.append(circPnt)
  del circPnt
  return circPnts
#-------------------------------------------------------------
def dxdyHypot (p1,p2):
  import math
  x = p2[0] - p1[0]
  y = p2[1] - p1[1]
  dist = math.hypot(x,y)
  return dist
#-------------------------------------------------------------
def dXdY (p1,p2):
  xyDiff = [p1[0] - p2[0], p1[1] - p2[1]]
  return xyDiff
#-------------------------------------------------------------
def extentPnts(pnts):
  '''Returns the min, max X, Y of input points'''
  xList = []; yList = []
  for pnt in pnts:
    xList.append(pnt[0]); yList.append(pnt[1])
  L = min(xList); R = max(xList); B = min(yList); T = max(yList)
  LL = [L,B]; UL = [L,T]; UR = [R,T]; LR = [R,B]
  return [LL, UL, UR, LR]
#-------------------------------------------------------------
def extentCenter(pnts):
  '''Returns the average and median X, Y coordinates of a series
     of input points'''
  xList = []; yList = []
  for pnt in pnts:
    xList.append(pnt[0]); yList.append(pnt[1])
  L = min(xList); R = max(xList); B = min(yList); T = max(yList)
  Xcent = (R - L)/2.0; Ycent = (T - B)/2.0
  return [Xcent, Ycent]
#-------------------------------------------------------------
def minRect(pnts):
  '''
  Determines the minimum area rectangle for a shape represented
  by a list of points
  
  calls:  polyAngles, transRotatePnts
  Note:  polyAngles returns a list in the form
         [pnt, to pnt, anAngle, aDistance]
  '''
  areaDict = {}
  pnts = list(pnts)             #ensure that you have a list of points
  angleList = polyAngles(pnts)  #determine the angles
  pntCent = extentCenter(pnts)  #determine centre of the extent
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
  #print "xmin,xmax, ymin, ymax, angle",Xmin,Xmax,Ymin,Ymax,a[5], angle
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
#---------------------------------------------------------------
def p1p2Angle(pnt1, pnt2):
  '''
  Requires two distinctly different points, returns the angle
  relative to the x axis.
  Returns -9999.99 if pnt1 == pnt2
  usage theAngle = GeomHelp.p1p2Azimuth(pnt1, pnt2)
  '''
  dY = pnt2[1] - pnt1[1]
  dX = pnt2[0] - pnt1[0]
  if dY == 0 and dX == 0:
    return -9999.99
  theAngle = math.atan2(dY,dX)*radToDeg
  return theAngle
#---------------------------------------------------------------  
def p1p2Azimuth(pnt1, pnt2):
  '''
  Requires two distinctly different points, returns the azimuth
  in the range 0 to 360, relative to north.
  Returns -9999.99 if pnt1 = pnt2
  usage theAngle=GeomHelp.p1p2Azimuth(pnt1,pnt2)
  '''
  dY = pnt2[1] - pnt1[1]
  dX = pnt2[0] - pnt1[0]
  if dY == 0 and dX == 0:
    return -9999.99
  z = 90 - math.atan2(dY,dX)*radToDeg
  theAngle = (z + 360.0) % 360.0
  return theAngle
#---------------------------------------------------------------
def p1p2p3Angle(pnt1, pnt2, pnt3):
  '''
  Determines the angle formed by 3 points
  usage theAngle=GeomHelp.p1p2p3Angle(pnt1, pnt2, pnt3)
  '''
  Angle1 = p1p2Azimuth(pnt1,pnt2)
  Angle2 = p1p2Azimuth(pnt2,pnt3)
  theAngle = 180.0 - (Angle2 - Angle1)
  if (theAngle < 0.0):
    theAngle = 360.0 + theAngle
  elif (theAngle > 360.0):
    theAngle = theAngle - 360.0
  return theAngle
#---------------------------------------------------------------
def p1p2Dist(pnt1, pnt2):
  '''
  Returns the distance between two distinctly different points
  usage  theDist =GeomHelp.p1p2Dist(pnt1, pnt2)
  '''
  dY = pnt2[1] - pnt1[1]
  dX = pnt2[0] - pnt1[0]
  dist = math.hypot(dX,dY)
  return dist
#-------------------------------------------------------------
def pntAvgXY(pnts):
  '''
  Returns the average X, Y coordinates of a series
  of input points
  '''
  N = float(len(pnts))  #ensure floating point division later on
  Xsum = 0.0; Ysum = 0.0
  for pnt in pnts:
    X = pnt[0]; Y = pnt[1]
    Xsum = Xsum + X
    Ysum = Ysum + Y
  Xcent = (Xsum/N)
  Ycent = (Ysum/N)
  return [Xcent, Ycent]
#-------------------------------------------------------------
def pntCenter (p1,p2):
  '''
  requires 2 points [10,10],[20,20]
  returns the centre point
  '''
  centPnt = [(p1[0] + p2[0])/2.0, (p1[1] + p2[1])/2.0]
  return centPnt
#-------------------------------------------------------------
def polyAngles(pnts):
  '''
  Requires:  a list of points forming a polygon
  Returns:   a list containing from pnt, to pnt, anAngle, aDistance
  '''
  pnts2 = pnts[:]
  if pnts2[0] != pnts2[-1]:
    N = len(pnts2)
    pnts2.append(pnts2[0])        #add the first point to the list
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
  #print "points after polyangle", str(pnts), str(pnts2)
  return angleList
#-------------------------------------------------------------  
def transRotatePnts(pnts,pntCent,angle):
  '''
  Requires a list of points, an extent point and an angle in degrees
    [ [0,0],[1,1], [0,1] ] points
    [5,5]                  extent center
    45                     rotation angle
  translates and rotates points about the origin using
    the negative angle formed between the points
  calls p1p2Angle, extentCenter
  '''
  #
  X0 = pntCent[0]; Y0 = pntCent[1]
  #print "transform2D center ", str(X0), str(Y0)
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
  

def main():
    pass
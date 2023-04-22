"""Script by Mitch Heynick 22 September 2013
Attempts to find similar  objects within tolerance but with different orientation
Currently Works only on closed Breps and Meshes
Will find objects that have same volume and surface area as reference object, plus
if BRep, same number and total length of edges
if Mesh, same number of faces and vertices
Will be slow with large numbers of objects
Added: additional distance of all edge curves' start point to volume centroid check

2021-11-02: Bug fixed by diff-arch (line 84) caused by None types which have no area attribute 
"""

import Rhino, time
import rhinoscriptsyntax as rs
import scriptcontext as sc

def CurveDistanceList(pt,crvs):
    return [(crv.PointAtStart-pt).Length for crv in crvs]
    
def CheckTwoDistanceLists(lst1,lst2,tol):
    if len(lst1)!=len(lst2): return False
    lst1.sort() ; lst2.sort()
    for i in range(len(lst1)):
        if abs(lst1[i]-lst2[i])>tol: return False
    return True

def FindSimilarVolumesPlus():
    #can tighten or loosen tolerance
    tol=sc.doc.ModelAbsoluteTolerance
    errATol=0 ; errVTol=0
    refObjID=rs.GetObject("Select reference volume",8+16+32,True,True)
    if not refObjID: return
    
    if rs.IsBrep(refObjID):
        isBrep=True
        refObj=rs.coercebrep(refObjID)
        #get number of edges and total edge length
        refEdges=refObj.Edges
        refEdgeCount=refEdges.Count
        refELen=0
        for edge in refObj.Edges:
            refELen+=edge.GetLength()        
    else:
        isBrep=False
        refObj=rs.coercemesh(refObjID)
        refFaceCount=refObj.Faces.Count
        refVertCount=refObj.Vertices.Count
    
    vProp=Rhino.Geometry.VolumeMassProperties.Compute(refObj)
    refVol=vProp.Volume
    aProp=Rhino.Geometry.AreaMassProperties.Compute(refObj)
    refArea=aProp.Area
    dList=CurveDistanceList(vProp.Centroid,refEdges)
    
    if not isBrep:
        errATol=refArea*tol ; errVTol=refVol*tol
    
    rs.Prompt("Collecting objects to check...")
    if isBrep:
        objIDsToChk=rs.ObjectsByType(8+16+1073741824,state=1)        
    else:
        objIDsToChk=rs.ObjectsByType(32,state=1)
    if objIDsToChk==None or len(objIDsToChk)<2: return
    
    #remove original object from list
    objIDsToChk.remove(refObjID)
    if isBrep:
        objsToChk=[rs.coercebrep(objID) for objID in objIDsToChk]
    else:
        objsToChk=[rs.coercemesh(obj) for obj in objIDsToChk]
    if len(objsToChk)!=len(objIDsToChk): 
        print "Error in converting objects" ; return
        
    start=time.time()
    msg="Checking {} objects...".format(len(objsToChk))
    rs.Prompt(msg)
    rs.StatusBarProgressMeterShow("Checking objects ",0,len(objsToChk),False,True)
    matchIndex=[]
    for i,obj in enumerate(objsToChk):
        if (isBrep and obj.IsSolid) or (not isBrep and obj.IsClosed):
            chkVProp=Rhino.Geometry.VolumeMassProperties.Compute(obj)
            if not chkVProp:
                continue
            if abs(chkVProp.Volume-refVol)<tol+errVTol:
                #volumes match
                chkAProp=Rhino.Geometry.AreaMassProperties.Compute(obj)
                if abs(chkAProp.Area-refArea)<tol+errATol:
                    #areas match
                    if isBrep:
                        #get edge list
                        edges=obj.Edges
                        eLen=0
                        eStPts=[]
                        for edge in obj.Edges:
                            eStPts.append(edge.PointAtStart)
                            eLen+=edge.GetLength()
                        if edges.Count==refEdgeCount and abs(eLen-refELen)<tol:
                            #number and total length of edges match
                            chkDList=CurveDistanceList(chkVProp.Centroid,edges)
                            if CheckTwoDistanceLists(dList,chkDList,tol):
                            #set of distances from start points match
                                matchIndex.append(i)
                    else:
                        if obj.Faces.Count==refFaceCount:
                            if obj.Vertices.Count==refVertCount:
                                #face and vertex count match
                                matchIndex.append(i)
        rs.StatusBarProgressMeterUpdate(i,True)
    if len(matchIndex)>0:
        matches=[objIDsToChk[index] for index in matchIndex]
        rs.EnableRedraw(False)
        rs.SelectObjects(matches)
        elapsed=time.time()-start
        msg="Found {} matching objects".format(len(matchIndex))
        msg+=" | Elapsed time: {} seconds".format(round(elapsed,2))
    else:
        msg="No matching objects found"
    print msg
    rs.StatusBarProgressMeterHide()
FindSimilarVolumesPlus()
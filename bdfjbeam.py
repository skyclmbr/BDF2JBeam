#  =======   NASTRAN .bdf to JBEAM and Calculix models ===========================
#  bdfjbeam (arg)  where (Arg) is the filename.  Must have .bdf file in same folder
#  bdf file will only read CTETRA elements and CTRIA3 elements
#  For the whole workflow, I output CompGeom from OpenVSP, read it into Gmsh as a tri
#  surface mesh.  Then create a 1st order 3d tet mesh from the tri surface mesh.  THen
#  export this as a bdf, using "include all elements" to capture the surface trias too.
#  This gives a bdf with nodes, tet elements and triangles on the surface
#  This is a script which will import a NASTRAN/MYSTRAN .bdf 
#  Must be ran in the directory where your mesh files are located
#  It will extract any tetra mesh or tria mesh and create a .jbeam file and a .dat file
#      .jbeam  - this file will have nodes from the tetra mesh, beams from the tetra mesh 
#                edges, and collision triangles from the tria elements.  No masses added
#      .inp    - this will create a calculix .dat file that mimics the jbeam model, SPRINGA
#                elements along all the tetra edges, nodes where the jbeam nodes are.  No masses
#
#      todo:  -  decide if we create a spring output FEA for NASTRAN/MYSTRAN.  CBUSH seems too 
#             complex, and ELAS element formulations require a lot of directional information 
#             to align the spring along the axis between the two points?
#             -  Add mass distributions onto nodes in jbeam file
#
#     -Bryan Sandoz

#Setup the libraries
import sys
import pyNastran
import itertools
print (pyNastran.__file__)
print (pyNastran.__version__)
pkg_path = pyNastran.__path__[0]
from pyNastran.bdf.bdf import BDF, read_bdf
from pyNastran.utils import object_attributes, object_methods
print("pkg_path = %s" % pkg_path)

#Import the bdf file - only takes the first argument as filename
bdf_filename = sys.argv[1]
bdf = read_bdf(bdf_filename, xref=False)

#Print some statistics so you know what you loaded up
print(bdf.get_bdf_stats())
print("card_count = %s\n" % bdf.card_count)
print("reject_count = %s" % bdf.reject_count)

#Write text file for jbeam output
jbeamname = ("%s.jbeam" % sys.argv[1])
calculixname = ("%s.dat" % sys.argv[1])

#Write jbeam file
f = open(jbeamname, 'w')
c = open(calculixname, 'w')

#Write nodes
c.write('*NODE, NSET=ALL\n')
for nid in bdf.nodes:
    xval = "{:.4f}".format(bdf.nodes[nid].xyz[0])   #4-decimal places
    yval = "{:.4f}".format(bdf.nodes[nid].xyz[1])
    zval = "{:.4f}".format(bdf.nodes[nid].xyz[2])
    nodeline = (nid, xval, yval, zval)
    f.write('["n%s", %s, %s, %s],\n' % nodeline)     #Write node lines in jbeam file
    c.write('%s, %s, %s, %s\n' % nodeline)          #Write node lines in calculix file
f.write('\n \n \n')
c.write('\n \n \n')

#Collect beams into on long beam list to be written after the fact
#(Calculix gets two spring element sets, internal and external)
beam_list = ["",]
cxext_list = ["",]
for eid in bdf.elements:
    node_list = bdf.elements[eid].node_ids
    el_type = bdf.elements[eid].type
    if el_type == "CTETRA":      #We will only create beams along edges of tetra elements
        edge_nodepairs = list(itertools.combinations(node_list, 2))   #Create all pairs of nodes as a list
        beam_list.extend(edge_nodepairs) #add all the pairs to the master beam list
    if el_type == "CTRIA3":
        edge_nodepairs = list(itertools.combinations(node_list, 2))  # Create all pairs of nodes as a list
        cxext_list.extend(edge_nodepairs)

#Clean up and create sets, one set of all jbeams,
# one set of internal calculix springs and one set of exterior calculix springs
beam_list.pop(0)   #Remove initiating item
cxext_list.pop(0)
beam_set = set(beam_list)
cxext_set = set(cxext_list)
cxint_set = beam_set - cxext_set

#Write beams
for bid in beam_set:
    f.write('["n%s","n%s"],\n' % bid)
f.write("\n \n \n")

#Write calculix springs
beamid = 1
c.write('*ELEMENT, ELSET=ESprExt, TYPE=SPRINGA\n')
for cid in cxext_set:
    bcalc = tuple([beamid]) + cid
    print(bcalc)
    c.write('%s, %s, %s\n' % bcalc)
    beamid += 1
c.write('\n \n \n*ELEMENT, ELSET=ESprInt, TYPE=SPRINGA\n')

for cid in cxint_set:
    bcalc = tuple([beamid]) + cid
    c.write('%s, %s, %s\n' % bcalc)
    beamid += 1
c.write("\n \n \n*SPRING, ELSET=ESprExt\n 100.0\n\n")
c.write("\n \n \n*SPRING, ELSET=ESprInt\n 100.0")

#Write collision triangles
for eid in bdf.elements:
    node_list = bdf.elements[eid].node_ids
    node_type = bdf.elements[eid].type
    if node_type == "CTRIA3":
        f.write('["n%s","n%s","n%s"],\n' % tuple(node_list))

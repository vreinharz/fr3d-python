# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 12:44:30 2014 @author: Poorna
Name: RNA-protein detection
"""

"""Detect and plot RNA base- amino acid interactions."""
from fr3d.cif.reader import Cif
from fr3d.definitions import RNAconnections
from fr3d.definitions import RNAbaseheavyatoms
from fr3d.definitions import Ribophos_connect
from fr3d.definitions import aa_connections
from fr3d.definitions import aa_backconnect
from fr3d.definitions import aa_fg
from fr3d.definitions import tilt_cutoff
from fr3d.definitions import planar_atoms
from fr3d.definitions import HB_donors
from fr3d.definitions import HB_acceptors
import numpy as np
import csv
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
# note that fr3d.localpath does not synchronize with Git, so you can change it locally to point to your own directory structure
from fr3d.localpath import outputText
from fr3d.localpath import outputBaseAAFG
from fr3d.localpath import inputPath
#from fr3d.classifiers.base_aafg import distance_metrics
from datetime import datetime
from math import floor

def get_structure(filename):
    with open(filename, 'rb') as raw:
        structure = Cif(raw).structure()
        """All RNA bases are placed in the standard orientation. All Hydrogen
 atoms are inferred. Rotation matrix is calculated for each base."""
        structure.infer_hydrogens()
        return structure


def atom_dist_basepart(base_residue, aa_residue, base_atoms, c):
    """Calculates atom to atom distance of part "aa_part" of neighboring amino acids
    of type "aa" from each atom of base. Only returns a pair of aa/nt if two
    or more atoms are within the cutoff distance"""
    min_distance = 4
    n = 0
    for base_atom in base_residue.atoms(name=base_atoms):
        for aa_atom in aa_residue.atoms(name=aa_fg[aa_residue.sequence]):
            # aa_atom = atom.coordinates()
            distance = np.subtract(base_atom.coordinates(), aa_atom.coordinates())
            distance = np.linalg.norm(distance)
            #print base_residue.unit_id(), aa_residue.unit_id(), distance
            if distance <= min_distance:
                n = n+1
                #print aa_atom.name
    if n>=c:
        #print aa_residue.unit_id()
        return True

def enough_HBs(base_residue, aa_residue, base_atoms):
    """Calculates number of Hydrogen bonds between amino acid part and base_part
    and determines if they are enough to form a pseudopair"""
    min_distance = 4
    base_key = base_residue.sequence
    aa_key = aa_residue.sequence
    n = 0
    base_HB_atoms = base_atoms + ["O2'"]
    base_donors = HB_donors[base_key]
    base_acceptors = HB_acceptors[base_key]
    aa_donors = HB_donors[aa_key]
    aa_acceptors = HB_acceptors[aa_key]

    for base_atom in base_residue.atoms(name=base_HB_atoms):
        for aa_atom in aa_residue.atoms(name=aa_fg[aa_key]):
            distance = np.subtract(base_atom.coordinates(), aa_atom.coordinates())
            distance = np.linalg.norm(distance)
            if distance <= min_distance:
                #print "HB", base_residue.unit_id(), aa_residue.unit_id(), base_atom.name, aa_atom.name, distance
                if base_atom.name in base_donors and aa_atom.name in aa_acceptors:
                    n = n+1
                elif base_atom.name in base_acceptors and aa_atom.name in aa_donors:
                    n = n+1
    print base_residue.unit_id(), aa_residue.unit_id(), n
    if n>=2:
        return True

def find_neighbors(bases, amino_acids, aa_part, dist_cent_cutoff):
    """Finds all amino acids of type "aa" for which center of "aa_part" is within
    specified distance of center of bases of type "base" and returns superposed bases"""
    #count_total = 0
    count_pair = 0
    list_aa_coord = []
    list_base_coord = []
    aaList_len = None
    new_aaList_len = None
    list_base_aa = []

    start = datetime.now()

    # build a set of cubes and record which bases are in which cube
    # also record which other cubes are neighbors of each cube
    baseCubeList = {}
    baseCubeNeighbors = {}
    for base in bases:
        center = base.centers["base"]
        x = floor(center[0]/dist_cent_cutoff)
        y = floor(center[1]/dist_cent_cutoff)
        z = floor(center[2]/dist_cent_cutoff)
        key = "%d,%d,%d" % (x,y,z)
        if key in baseCubeList:
            baseCubeList[key].append(base)
        else:
            baseCubeList[key] = [base]
            baseCubeNeighbors[key] = []
            for a in [-1,0,1]:
                for b in [-1,0,1]:
                    for c in [-1,0,1]:
                        k = "%d,%d,%d" % (x+a,y+b,z+c)
                        baseCubeNeighbors[key].append(k)

    # build a set of cubes and record which amino acids are in which cube
    aaCubeList = {}
    for aa in amino_acids:
        center = aa.centers[aa_part]
        x = floor(center[0]/dist_cent_cutoff)
        y = floor(center[1]/dist_cent_cutoff)
        z = floor(center[2]/dist_cent_cutoff)
        key = "%d,%d,%d" % (x,y,z)
        if key in aaCubeList:
            aaCubeList[key].append(aa)
        else:
            aaCubeList[key] = [aa]
    print "Time to set up Cubes", datetime.now() - start

    # loop through base cubes, loop through neighboring cubes,
    # then loop through bases and amino acids in the two cubes,
    # screening distances between them, then annotating interactions
    start = datetime.now()
    for key in baseCubeList:
        for aakey in baseCubeNeighbors[key]:
            if aakey in aaCubeList:
                for base_residue in baseCubeList[key]:
                    base_seq = base_residue.sequence
                    base_atoms = RNAbaseheavyatoms[base_seq]

                    base_center = base_residue.centers["base"]
                    if not base_center.any():
                        continue
                    for aa_residue in aaCubeList[aakey]:
                        aa_center = aa_residue.centers[aa_part]
                        if not aa_center.any():
                            continue

                        if aa_residue.sequence in set (['LYS','SER', 'THR', 'TYR']):
                            c= 1
                        else:
                            c = 2

                        if abs(base_center[0]-aa_center[0]) < dist_cent_cutoff and \
                        abs(base_center[1]-aa_center[1]) < dist_cent_cutoff and \
                        np.linalg.norm(np.subtract(base_center,aa_center)) < dist_cent_cutoff and \
                        atom_dist_basepart(base_residue, aa_residue, base_atoms, c):

                            count_pair = count_pair + 1

                            rotation_matrix = base_residue.rotation_matrix
                            #print "rotation matrix", base_residue, rotation_matrix

                            base_coordinates = {}
                            standard_base = base_residue.translate_rotate_component(base_residue)
                            for base_atom in standard_base.atoms():
                                base_coordinates[base_atom.name]= base_atom.coordinates()

                            aa_coordinates = {}
                            standard_aa = base_residue.translate_rotate_component(aa_residue)
                            for aa_atom in standard_aa.atoms():
                                aa_coordinates[aa_atom.name] = aa_atom.coordinates()

                            interaction = type_of_interaction(base_residue, aa_residue, aa_coordinates)

                            base_aa = None
                            if interaction == "pseudopair" and enough_HBs(base_residue, aa_residue, base_atoms):
                                edge = detect_edge(base_residue, base_coordinates,aa_residue, aa_coordinates)
                                base_aa = annotate(base_residue, aa_residue, interaction, edge)

                            elif interaction == "SHB":
                                edge = detect_edge(base_residue, base_coordinates,aa_residue, aa_coordinates)
                                base_aa = annotate(base_residue, aa_residue, interaction, edge)

                            elif interaction == "perpendicular edge":
                                edge = detect_edge(base_residue, base_coordinates,aa_residue, aa_coordinates)
                                base_aa = annotate(base_residue, aa_residue, interaction, edge)

                            elif interaction == "stacked" or interaction == "cation-pi" \
                            or interaction == "perpendicular stacking":
                                edge = detect_face(aa_residue, aa_coordinates)
                                base_aa = annotate(base_residue, aa_residue, interaction, edge)


                            if base_aa is not None:
                                list_base_aa.append(base_aa)

                                for base_atom in base_residue.atoms():
                                    list_base_coord.append(base_coordinates)
                                for aa_atom in aa_residue.atoms():
                                    list_aa_coord.append(aa_coordinates)

    print "Time to iterate through pairs", datetime.now() - start

    return list_base_aa, list_aa_coord, list_base_coord
    #return list_aa_coord, list_base_coord, count, list_base_aa

def annotate(base_residue, aa_residue, interaction, edge):
    base_aa = (base_residue, aa_residue, interaction, edge)
    return base_aa

def type_of_interaction(base_residue, aa_residue, aa_coordinates):
    squared_xy_dist_list = []
    aa_z =[]

    """Defines different sets of amino acids"""
    stacked_planar_aa = set (["TRP", "TYR", "PHE", "HIS", "ARG", "ASN", "GLN", "GLU", "ASP"])
    stacked_aliphatic = set(["LEU", "ILE", "PRO", "THR", "MET", "CYS", "VAL", "ALA", "SER"])
    pseudopair_aa = set (["ASP", "GLU", "ASN", "GLN", "HIS", "ARG", "TYR", "TRP", "PHE", "LYS"])
    shb_aa = set (["SER", "THR", "LYS"])

    for aa_atom in aa_residue.atoms(name=aa_fg[aa_residue.sequence]):
        key = aa_atom.name
        aa_x= aa_coordinates[key][0]
        aa_y= aa_coordinates[key][1]

        squared_xy_dist = (aa_x**2) + (aa_y**2)
        squared_xy_dist_list.append(squared_xy_dist)

        aa_z.append(aa_coordinates[key][2])

    mean_z = np.mean(aa_z)

    #print base_residue.unit_id(), aa_residue.unit_id(), min(squared_xy_dist_list), mean_z
    if min(squared_xy_dist_list) <= 5:
        #print base_residue.unit_id(), aa_residue.unit_id(), min(squared_xy_dist_list), mean_z
        if aa_residue.sequence in stacked_planar_aa:
            #print "stacking?", base_residue.unit_id(), aa_residue.unit_id(), min(squared_xy_dist_list), mean_z
            return stacking_angle(base_residue, aa_residue, min(squared_xy_dist_list))

        elif aa_residue.sequence in stacked_aliphatic:
            return stacking_tilt(aa_residue, aa_coordinates)

    elif -1.8 <= mean_z < 1.8 and aa_residue.sequence in pseudopair_aa:
            angle= calculate_angle(base_residue, aa_residue)
            angle = abs(angle)
            #print "pseudopair?", base_residue.unit_id(), aa_residue.unit_id(), angle
            if 0 <= angle <= 0.75 or 2.5 <= angle <= 3.14:
                return "pseudopair"
            elif 0.95 <= angle <=1.64:
                return "perpendicular edge"

    elif -1.8 <= mean_z < 1.8 and aa_residue.sequence in shb_aa:
        base_seq = base_residue.sequence
        base_atoms = RNAbaseheavyatoms[base_seq]
        if atom_dist_basepart(base_residue, aa_residue, base_atoms, 1):
            return "SHB"

def calculate_angle (base_residue, aa_residue):
    vec1 = vector_calculation(base_residue)
    vec2 = vector_calculation(aa_residue)

    angle = angle_between_planes(vec1, vec2)
    return angle

def stacking_angle (base_residue, aa_residue, min_dist):
    vec1 = vector_calculation(base_residue)
    vec2 = vector_calculation(aa_residue)
    perpendicular_aa = set (["HIS", "ARG", "LYS", "ASN", "GLN"])
    perpendicular_stack_aa = set(["PHE", "TYR"])
    angle = angle_between_planes(vec1, vec2)
    #print "stacked?"
    #print base_residue.unit_id(), aa_residue.unit_id(), min_dist, angle
    angle = abs(angle)
    if angle <=0.68 or 2.45 <= angle <= 3.15:
        return "stacked"
    elif 1.2<= angle <=1.64:
        if aa_residue.sequence in perpendicular_stack_aa:
            return "perpendicular stacking"
        elif aa_residue.sequence in perpendicular_aa:
            return "cation-pi"

def stacking_tilt(aa_residue, aa_coordinates):
    baa_dist_list = []

    for aa_atom in aa_residue.atoms(name=aa_fg[aa_residue.sequence]):
        key = aa_atom.name
        aa_z = aa_coordinates[key][2]
        baa_dist_list.append(aa_z)
    max_baa = max(baa_dist_list)
    min_baa = min(baa_dist_list)
    diff = max_baa - min_baa
    #print aa_residue.unit_id(), diff
    if diff <= tilt_cutoff[aa_residue.sequence]:
        return "stacked"

def vector_calculation(residue):
    key = residue.sequence
    P1 = residue.centers[planar_atoms[key][0]]
    P2 = residue.centers[planar_atoms[key][1]]
    P3 = residue.centers[planar_atoms[key][2]]
    #print P1, P2, P3
    vector = np.cross((P2 - P1),(P3-P1))
    return vector

def angle_between_planes (vec1, vec2):
    cosang = np.dot(vec1, vec2)
    sinang = np.linalg.norm(np.cross(vec1, vec2))
    angle = np.arctan2(sinang, cosang)
    return angle

def detect_edge(base_residue, base_coordinates,aa_residue, aa_coordinates):
    aa_x = []
    aa_y = []
    base_x = []
    base_y = []
    for aa_atom in aa_residue.atoms(name=aa_fg[aa_residue.sequence]):
        key = aa_atom.name
        aa_x.append(aa_coordinates[key][0])
        aa_y.append(aa_coordinates[key][1])

    aa_center_x = np.mean(aa_x)
    aa_center_y = np.mean(aa_y)

    for base_atom in base_residue.atoms(name=RNAbaseheavyatoms[base_residue.sequence]):
        key = base_atom.name
        base_x.append(base_coordinates[key][0])
        base_y.append(base_coordinates[key][1])

    base_center_x = np.mean(base_x)
    base_center_y = np.mean(base_y)

    y = aa_center_y - base_center_y
    x = aa_center_x - base_center_x
    angle_aa = np.arctan2(y,x) #values -pi to pi
    #print base_residue.unit_id(), aa_residue.unit_id(),angle_aa
    purine = set(["A", "G"])
    pyrimidine = set(["C", "U"])
    angle_deg = (180*angle_aa)/3.14159 #values -180 to 180
    print "Edge angle in rad and deg", angle_aa, angle_deg

    if base_residue.sequence in purine:
        if -15 <= angle_deg <= 90:
            return "fgWC"
        elif 90 < angle_deg or angle_deg < -160:
            return "fgH"
        else:
            return "fgS"

    elif base_residue.sequence in pyrimidine:
        if -45 <= angle_deg <= 90:
            return "fgWC"
        elif 90 < angle_deg or angle_deg < -150:
            return "fgH"
        else:
            return "fgS"

def detect_face(aa_residue, aa_coordinates):
    aa_z =[]

    for aa_atom in aa_residue.atoms(name=aa_fg[aa_residue.sequence]):
        key = aa_atom.name
        aa_z.append(aa_coordinates[key][2])

    mean_z = np.mean(aa_z)
    if mean_z <= 0:
        return "fgs5"
    else:
        return "fgs3"

def text_output(result_list):
    with open(outputText % PDB, 'wb') as target:
        for result in result_list:
            target.write(str(result))
            target.write("\r\n")
            target.close

def csv_output(result_list):
    with open(outputBaseAAFG % PDB, 'wb') as csvfile:
        fieldnames = ['RNA ID', 'AA ID', 'RNA Chain ID', 'RNA residue','RNA residue number','Protein Chain ID', 'AA residue','AA residue number', 'Interaction', 'Edge']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for base_residue, aa_residue, interaction, edge in result_list:
            base = base_residue.unit_id()
            aa = aa_residue.unit_id()
            #print base, aa, interaction
            base_component = str(base).split("|")
            aa_component = str(aa).split("|")
            writer.writerow({'RNA ID': base, 'AA ID': aa, 'RNA Chain ID': base_component[2], 'RNA residue':base_component[3],'RNA residue number': base_component[4],'Protein Chain ID':aa_component[2],'AA residue': aa_component[3],'AA residue number': aa_component[4], 'Interaction': interaction, 'Edge': edge})

        """for base_residue, aa_residue,interaction in result_list:
                    base_component = str(base_residue).split("|")
                    aa_component = str(aa_residue).split("|")
                    writer.writerow({'RNA Chain ID': base_component[2], 'RNA residue':base_component[3],'RNA residue number': base_component[4],'Protein Chain ID':ChainNames[PDB][aa_component[2]],'AA residue': aa_component[3],'AA residue number': aa_component[4], 'Interaction': interaction})"""



def draw_base(base_seq, ax):
    """Connects atoms to draw neighboring bases and amino acids for 3D plots"""
     #creates lists of rotated base coordinates
    for basecoord_list in list_base_coord:
        new_base_x = []
        new_base_y = []
        new_base_z = []

        back_base_x = []
        back_base_y = []
        back_base_z = []


        try:
            for atomname in RNAconnections[base_seq]:
                coord_base = []
                coord_base= basecoord_list[atomname]
                new_base_x.append(coord_base[0])
                new_base_y.append(coord_base[1])
                new_base_z.append(coord_base[2])
            base_lines= ax.plot(new_base_x, new_base_y, new_base_z, label= 'Base')
            #ax.scatter(basecenter[0], basecenter[1], basecenter[2], zdir='y', color='b', marker='o')
            #ax.scatter(x = 0, y= 0, z= 0, color='b', marker='o')
            plt.setp(base_lines, 'color', 'b', 'linewidth', 1.0)

            for atomname in Ribophos_connect[base_seq]:
                back_base=[]
                back_base= basecoord_list[atomname]
                back_base_x.append(back_base[0])
                back_base_y.append(back_base[1])
                back_base_z.append(back_base[2])
            base_lines= ax.plot(back_base_x, back_base_y, back_base_z, label= 'Base')
            plt.setp(base_lines, 'color', 'g', 'linewidth', 1.0)
            #ax.text(9, 1, 1, base_residue)
        except:
            print "Missing residues"
            continue

def draw_aa(aa, ax):
    #Connects atoms to draw neighboring bases and amino acids for 3D plots
    for aacoord_list in list_aa_coord:
        new_aa_x=[]
        new_aa_y=[]
        new_aa_z=[]

        back_aa_x=[]
        back_aa_y=[]
        back_aa_z=[]

        try:
            for atomname in aa_connections[aa]:
                coord_aa=[]
                coord_aa= aacoord_list[atomname]
                new_aa_x.append(coord_aa[0])
                new_aa_y.append(coord_aa[1])
                new_aa_z.append(coord_aa[2])
            aa_lines= ax.plot(new_aa_x, new_aa_y, new_aa_z, label= 'Amino acid')
            plt.setp(aa_lines, 'color', 'r', 'linewidth', 1.0)

            for atomname in aa_backconnect[aa]:
                back_aa=[]
                back_aa= aacoord_list[atomname]
                back_aa_x.append(back_aa[0])
                back_aa_y.append(back_aa[1])
                back_aa_z.append(back_aa[2])
            aa_lines= ax.plot(back_aa_x, back_aa_y, back_aa_z, label= 'Amino acid')
            plt.setp(aa_lines, 'color', 'y', 'linewidth', 1.0)
        except:
            print "Missing residues"
            continue

def draw_aa_cent(aa, aa_part, ax):
    #Connects atoms to draw neighboring bases and amino acids for 3D plots
    for aacoord_list in list_aa_coord:
        new_aa_x=[]
        new_aa_y=[]
        new_aa_z=[]

        aa_center_x = 0
        aa_center_y = 0
        aa_center_z = 0
        n = 0

        if aa_part == 'aa_fg':
            connections = aa_connections
        elif aa_part == 'aa_backbone':
            connections = aa_backconnect
        try:
            for atomname in connections[aa]:
                coord_aa=[]
                coord_aa= aacoord_list[atomname]
                new_aa_x.append(coord_aa[0])
                new_aa_y.append(coord_aa[1])
                new_aa_z.append(coord_aa[2])

                aa_center_x = aa_center_x + coord_aa[0]
                aa_center_y = aa_center_y + coord_aa[1]
                aa_center_z = aa_center_z + coord_aa[2]
                n = n + 1
            ax.scatter(aa_center_x/n, aa_center_y/n, aa_center_z/n, c= 'r', marker = 'o')
        except:
            print "Missing residues"
            continue

"""Inputs a list of PDBs of interest to generate super-imposed plots"""
PDB_List = ['3QRQ']
PDB_List = ['5AJ3']
PDB_List = ['4V9F','5J7L']
PDB_List = ['4V9F']
PDB_List = ['5J7L']
PDB_List = ['6hiv']


base_seq_list = ['A','U','C','G']
#base_seq_list = ['A']
aa_list = ['ALA','VAL','ILE','LEU','ARG','LYS','HIS','ASP','GLU','ASN','GLN','THR','SER','TYR','TRP','PHE','PRO','CYS','MET']
#aa_list = ['HIS']

#fig = plt.figure()
#ax = fig.add_subplot(111, projection='3d')

"""Inputs base, amino acid, aa_part of interest and cut-off distance for subsequent functions"""
if __name__=="__main__":
    for PDB in PDB_List:
        start = datetime.now()
        structure = get_structure(inputPath % PDB)
        result_nt_aa = []

        aa_part = 'aa_fg'
        base_part = 'base'

        bases = structure.residues(sequence= base_seq_list)
        amino_acids = structure.residues(sequence=aa_list)
        print "Time to load structure", datetime.now() - start

        start = datetime.now()
        list_base_aa, list_aa_coord, list_base_coord = find_neighbors(bases, amino_acids, aa_part, 10)
        print "Time to annotate interactions", datetime.now() - start

        """ 3D plots of base-aa interactions
        for base, aa, interaction in list_base_aa:
            base_seq = base.sequence
            aa= aa.sequence

            draw_base(base_seq, ax)
            draw_aa(aa, ax)
            #draw_aa_cent(aa, aa_part, ax)

            ax.set_xlabel('X Axis')
            ax.set_ylabel('Y Axis')
            ax.set_zlabel('Z Axis')
            ax.set_xlim3d(10, -15)
            ax.set_ylim3d(10, -15)
            ax.set_zlim3d(10, -15)
            plt.title('%s with ' % base_seq +'%s' % aa + ' %s' % aa_part)
            plt.show()
                      """
        #making the list of resultant RNA-aa pairs
        result_nt_aa.extend(list_base_aa)

        #writing out output files
        #text_output(result_nt_aa)

        csv_output(result_nt_aa)

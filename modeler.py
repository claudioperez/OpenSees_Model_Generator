"""
TODO - Add module docstring
"""

#   __                 UC Berkeley
#   \ \/\   /\/\/\     John Vouvakis Manousakis
#    \ \ \ / /    \    Dimitrios Konstantinidis
# /\_/ /\ V / /\/\ \
# \___/  \_/\/    \/   April 2021
#
# https://github.com/ioannis-vm/OpenSeesPy_Building_Modeler/blob/main/modeler.py

from __future__ import annotations
from dataclasses import dataclass, field
from functools import total_ordering
from typing import List
import numpy as np
import matplotlib.pyplot as plt
import openseespy.opensees as ops
import openseespy.postprocessing.ops_vis as opsv

EPSILON = 1.00E-8
ALPHA = 10000.00

# pylint: disable=unsubscriptable-object


def previous_element(lst: list, obj):
    """
    Returns the previous object in a list
    given a target object, assuming it is in the list.
    If it is not, it returns None.
    If the target is the first object, it returns None.
    """
    try:
        idx = lst.index(obj)
    except ValueError:
        return None
    if idx == 0:
        return None
    return lst[idx - 1]


@dataclass
@total_ordering
class GridLine:
    tag: str
    pi_x: float
    pi_y: float
    pj_x: float
    pj_y: float
    start: np.ndarray = field(init=False, repr=False)
    end:   np.ndarray = field(init=False, repr=False)
    length: float = field(init=False, repr=False)
    direction: float = field(init=False, repr=False)

    def __post_init__(self):
        self.start = np.array([self.pi_x, self.pi_y])
        self.end = np.array([self.pj_x, self.pj_y])
        self.length = np.linalg.norm(self.end - self.start)
        self.direction = (self.end - self.start) / self.length

    def __eq__(self, other):
        return self.tag == other.tag

    def __le__(self, other):
        return self.tag <= other.tag

    def intersect(self, grd: GridLine):
        """
        Obtain the intersection with
        another gridline (if it exists)

        Parameters:
            grd (GridLine): a gridline to intersect
        Returns:
            list[float]: Intersection point

        Derivation:
        If the intersection point p exists, we will have
        p = ra.origin + ra.dir * u
        p = rb.origin + rb.dir * v
        We determine u and v (if possible) and check
        if the intersection point lies on both lines.
        If it does, the lines intersect.
        """
        ra_dir = self.direction
        rb_dir = grd.direction
        mat = np.array(
            [
                [ra_dir[0], -rb_dir[0]],
                [ra_dir[1], -rb_dir[1]]
            ]
        )
        if np.abs(np.linalg.det(mat)) <= EPSILON:
            # The lines are parallel
            return None
        # Get the origins
        ra_ori = self.start
        rb_ori = grd.start
        # System left-hand-side
        bvec = np.array(
            [
                [rb_ori[0] - ra_ori[0]],
                [rb_ori[1] - ra_ori[1]],
            ]
        )
        # Solve to get u and v in a vector
        uvvec = np.linalg.solve(mat, bvec)
        # Terminate if the intersection point
        # does not lie on both lines
        if uvvec[0] < 0 - EPSILON:
            return None
        if uvvec[1] < 0 - EPSILON:
            return None
        if uvvec[0] > self.length + EPSILON:
            return None
        if uvvec[1] > grd.length + EPSILON:
            return None
        # Otherwise the point is valid
        pt = ra_ori + ra_dir * uvvec[0]
        return [pt[0], pt[1]]


@dataclass
class GridSystem:
    """
    This class is a collector for the gridlines, and provides
    methods that perform operations using gridlines.
    """

    grids: list[GridLine] = field(default_factory=list)

    def add(self, grdl: "GridLine"):
        """
        Add a gridline in the grid system,
        if it is not already in
        """
        if grdl not in self.grids:
            self.grids.append(grdl)
        else:
            raise ValueError('Gridline already exists: '
                             + repr(grdl))
        self.grids.sort()

    def remove(self, grdl: "GridLine"):
        """
        Remove a gridline from the grid system
        """
        self.grids.remove(grdl)

    def intersection_points(self):
        """
        Returns a list of all the points
        defined by gridline intersections
        """
        pts = []  # intersection points: [ [x1, y1], ... ]
        for i, grd1 in enumerate(self.grids):
            for j in range(i+1, len(self.grids)):
                grd2 = self.grids[j]
                pt = grd1.intersect(grd2)
                if pt:
                    pts.append(pt)
        return pts

    def intersect(self, grd: GridLine):
        """
        Returns a list of all the points
        defined by the intersection of a given
        gridline with all the other gridlines
        in the gridsystem
        """
        pts = []  # intersection points: [ [x1, y1], ... ]
        for i, other_grd in enumerate(self.grids):
            if other_grd == grd:
                continue
            pt = grd.intersect(other_grd)
            if pt:
                pts.append(pt)
        return pts

    def __repr__(self):
        out = "The building has " + \
            str(len(self.grids)) + " gridlines\n"
        for grd in self.grids:
            out += repr(grd) + "\n"
        return out


@dataclass
class Element:
    """
    This is a generic parent element class from which
    more specific elements will be inherited, like nodes,
    columns, beams etc.
    """

    uniq_id: int = field(init=False)

    def __post_init__(self):
        self.iniq_id = 0


@dataclass
@total_ordering
class Group:
    """
    This class will be used to group together
    elements of any kind, for organization purposes
    """

    name: str
    elements: list[Element] = field(init=False)

    def __post_init__(self):
        self.elements = []

    def __eq__(self, other):
        return self.name == other.name

    def __le__(self, other):
        return self.name <= other.name

    def add(self, element: "Element"):
        """
        Add an element in the group,
        if it is not already in
        """
        if element not in self.elements:
            self.elements.append(element)

    def remove(self, element: Element):
        """
        Remove something from the group
        """
        self.elements.remove(element)


@dataclass
class Groups:
    """
    Stores the element groups of a building.
    No two element groups can have the same name.
    Elements can belong in multiple element groups
    """

    group_list: list[Group] = field(default_factory=list)
    active:     list[Group] = field(default_factory=list)

    def add(self, grp: Group):
        """
        Adds a new element group

        Parameters:
            grp (Group): the element group to add
        """
        # Verify element group name is unique
        if grp in self.group_list:
            raise ValueError('Group name already exists: ' + repr(grp))
        # Append the new element group in the list
        self.group_list.append(grp)
        # Sort the element groups in ascending order (name-wise)
        self.group_list.sort()

    def set_active(self, names: List[str]):
        """
        Assigns the active groups (one or more).
        Adding any element to the building will also
        add that element to the active groups.
        The active groups can also be set to an empty list.
        In that case, new elements will not be added to groups.

        """
        self.active = []
        found = False
        for name in names:
            for grp in self.group_list:
                if grp.name == name:
                    self.active.append(grp)
                    found = True
            if found is False:
                raise ValueError("Group " + name + " does not exist")

    def __repr__(self):
        out = "The building has " + \
            str(len(self.group_list)) + " groups\n"
        for grp in self.group_list:
            out += repr(grp) + "\n"
        return out


@dataclass
@total_ordering
class Node(Element):
    """
    Node object.
    It represents a point.
    Used for element connectivity.
    """

    x_coord: float
    y_coord: float
    z_coord: float
    restraint_type: str = field(default="free")

    def __eq__(self, other):
        """
        Equality is only checked in terms of (x, y)
        """
        dist = (self.x_coord - other.x_coord)**2 +\
            (self.y_coord - other.y_coord)**2
        return dist < EPSILON**2

    def __le__(self, other):
        d_self = self.y_coord * ALPHA + self.x_coord
        d_other = other.y_coord * ALPHA + other.x_coord
        return d_self <= d_other


@dataclass
class Nodes:
    """
    This class is a collector for the nodes, and provides
    methods that perform operations using nodes.
    """

    node_list: list[Node] = field(default_factory=list)

    def add(self, node: Node):
        """
        Add a node in the nodes collection,
        if it does not exist already
        """
        if node not in self.node_list:
            self.node_list.append(node)
        else:
            raise ValueError('Node already exists: '
                             + repr(node))
        self.node_list.sort()

    def remove(self, node: Node):
        """
        Remove a node from the node system
        """
        self.node_list.remove(node)

    def __repr__(self):
        out = "The level has " + \
            str(len(self.node_list)) + " nodes\n"
        for node in self.node_list:
            out += repr(node) + "\n"
        return out


@dataclass
class LinearElement:
    """
    Linear finite element class.
    """

    node_i: Node
    node_j: Node
    ang: float

    def local_y_axis_vector(self):
        x_vec = np.array([
            self.node_j.x_coord - self.node_i.x_coord,
            self.node_j.y_coord - self.node_i.y_coord,
            self.node_j.z_coord - self.node_i.z_coord
        ])
        x_vec = x_vec / np.linalg.norm(x_vec)
        diff = np.abs(
            np.linalg.norm(
                x_vec - np.array([0.00, 0.00, 1.00])
            )
        )
        if diff < EPSILON:
            # vertical case
            y_vec = np.array([np.cos(self.ang), np.sin(self.ang), 0.0])
        else:
            # not vertical case
            up_direction = np.array([0.0, 0.0, 1.0])
            # orthogonalize with respect to x_vec
            z_vec = up_direction - np.dot(up_direction, x_vec)
            # ..and normalize
            z_vec = z_vec / np.linalg.norm(z_vec)
            # determine y vector from the cross-product
            y_vec = np.cross(x_vec, z_vec)
        return y_vec


@ dataclass
@ total_ordering
class Column(LinearElement):
    """
    TODO
    """

    def __eq__(self, other):
        return (self.node_i == other.node_i and
                self.node_j == other.node_j)

    def __le__(self, other):
        return self.node_i <= other.node_i


@ dataclass
class Columns:
    """
    This class is a collector for columns, and provides
    methods that perform operations using columns.
    """

    column_list: list[Column] = field(default_factory=list)

    def add(self, column: Column):
        """
        Add a column in the columns collection,
        if it does not exist already
        """
        if column not in self.column_list:
            self.column_list.append(column)
        else:
            raise ValueError('Column already exists: '
                             + repr(column))
        self.column_list.sort()

    def remove(self, column: Column):
        """
        Remove a column from the column system
        """
        self.column_list.remove(column)

    def __repr__(self):
        out = "The level has " + \
            str(len(self.column_list)) + " columns\n"
        for column in self.column_list:
            out += repr(column) + "\n"
        return out


@ dataclass
@ total_ordering
class Beam(LinearElement):
    """
    TODO
    """

    def __eq__(self, other):
        return (self.node_i == other.node_i and
                self.node_j == other.node_j)

    def __le__(self, other):
        return self.node_i <= other.node_i


@ dataclass
class Beams:
    """
    This class is a collector for beams, and provides
    methods that perform operations using beams.
    """

    beam_list: list[Beam] = field(default_factory=list)

    def add(self, beam: Beam):
        """
        Add a beam in the beams collection,
        if it does not exist already
        """
        if beam not in self.beam_list:
            self.beam_list.append(beam)
        else:
            raise ValueError('Beam already exists: '
                             + repr(beam))
        self.beam_list.sort()

    def remove(self, beam: Beam):
        """
        Remove a beam from the beam system
        """
        self.beam_list.remove(beam)

    def __repr__(self):
        out = "The level has " + \
            str(len(self.beam_list)) + " beams\n"
        for beam in self.beam_list:
            out += repr(beam) + "\n"
        return out


@ dataclass
@ total_ordering
class Level:
    """
    Individual building floor level.
    All nodes, elements and applied loads must belong to a level.
    """

    name: str
    elevation: float
    restraint: str = field(default="free")
    previous_lvl: 'Level' = field(default=None)
    nodes: Nodes = field(default_factory=Nodes)
    columns: Columns = field(default_factory=Columns)
    beams: Beams = field(default_factory=Beams)

    def __post_init__(self):
        if self.restraint not in ["free", "fixed", "pinned"]:
            raise ValueError('Invalid restraint type: ' + self.restraint)

    def __eq__(self, other):
        return self.name == other.name

    def __le__(self, other):
        return self.elevation <= other.elevation

    def add_node(self, x_coord: float, y_coord: float):
        """
        Adds a node on that level at a given point
        """
        self.nodes.add(Node(x_coord, y_coord,
                            self.elevation, self.restraint))

    def look_for_node(self, x_coord: float, y_coord: float):
        """
        Returns the node that occupies a given point
        at the current level, if it exists
        """
        candidate_node = Node(x_coord, y_coord,
                              self.elevation, self.restraint)
        for other_node in self.nodes.node_list:
            if other_node == candidate_node:
                return other_node
        return None

    def add_column(self, node_i, node_j, ang):
        """
        Adds a column on that level with given nodes
        """
        self.columns.add(Column(node_i, node_j, ang))

    def add_beam(self, node_i, node_j, ang):
        """
        Adds a beam on that level with given nodes
        """
        self.beams.add(Beam(node_i, node_j, ang))


@ dataclass
class Levels:
    """
    Stores the floor levels of a building.
    No two floor levels can have the same height (no multi-tower support)
    """

    level_list: list[Level] = field(default_factory=list)
    active: list[Level] = field(default_factory=list)

    def add(self, lvl: Level):
        """
        Adds a new level. The levels must be added in ascending
        order for now. TODO -> any order

        Parameters:
            lvl (Level): the level to add
        """
        # Verify level name is unique
        if lvl in self.level_list:
            raise ValueError('Level name already exists: ' + repr(lvl))
        # Verify level elevation is unique
        if lvl.elevation in [lev.elevation
                             for lev in self.level_list]:
            raise ValueError('Level elevation already exists: ' + repr(lvl))
        # TODO - Don't accept levels out of order (for now)
        if self.level_list:
            if lvl.elevation < self.level_list[-1].elevation:
                raise ValueError(
                    'Levels should be defined from the bottom up for now..')
        # Append the new level in the level list
        self.level_list.append(lvl)
        previous_lvl = previous_element(self.level_list, lvl)
        if previous_lvl:
            lvl.previous_lvl = previous_lvl

        # If there's no active level, make
        # the newly added level active
        if not self.active:
            # (this means "if list is empty")
            self.active.append(lvl)
            self.active.sort()

    def get(self, name: str):
        """"
        Finds a level given the level name
        """
        for lvl in self.level_list:
            if lvl.name == name:
                return lvl
        raise ValueError("Level " + name + " does not exist")

    def set_active(self, names: List[str]):
        """
        Sets the active levels (one or more).
        There needs to be at least one active level at all times.
        Any element addition or modification call will
        happen on the active levels.

        """
        self.active = []
        if not names:
            # (that means if the list of names is empty)
            # this will be used to indicate "all"
            self.active = [lvl for lvl in self.level_list]
        for name in names:
            retrieved_level = self.get(name)
            if retrieved_level not in self.active:
                self.active.append(
                    retrieved_level
                )

    def __repr__(self):
        out = "The building has " + \
            str(len(self.level_list)) + " levels\n"
        for lvl in self.level_list:
            out += repr(lvl) + "\n"
        return out


@ dataclass
class Building:
    """
    This class manages building objects
    """

    ndm: int = field(default=3)
    ndf: int = field(default=6)
    gridsystem: GridSystem = field(default_factory=GridSystem)
    levels: Levels = field(default_factory=Levels)
    groups: Groups = field(default_factory=Groups)

    #############################################
    # Add methods - add objects to the building #
    #############################################

    def add_node(self,
                 x: float,
                 y: float):
        """
        Adds a node at a particular point in all active levels
        """
        for level in self.levels.active:
            level.add_node(x, y)

    def add_level(self,
                  name: str,
                  elevation: float,
                  restraint: str = "free"
                  ):
        """
        adds a level to the buildin
        """
        self.levels.add(Level(name, elevation, restraint))

    def add_gridline(self,
                     tag: str,
                     pi_x: float,
                     pi_y: float,
                     pj_x: float,
                     pj_y: float
                     ):
        """
        Adds a new gridline to the building
        """
        self.gridsystem.add(GridLine(tag, pi_x, pi_y, pj_x, pj_y))

    def add_group(self, name: str):
        """
        Adds a new group to the building
        """
        self.groups.add(Group(name))

    def add_column_at_point(self,
                            x: float,
                            y: float,
                            ang: float):
        """
        TODO - add docstring
        """
        for level in self.levels.active:
            if level.previous_lvl:  # if previous level exists
                # check to see if top node exists
                top_node = level.look_for_node(x, y)
                # create it if it does not exist
                if not top_node:
                    top_node = Node(x, y, level.elevation, level.restraint)
                    level.nodes.add(top_node)
                # check to see if bottom node exists
                bot_node = level.previous_lvl.look_for_node(
                    x, y)
                # create it if it does not exist
                if not bot_node:
                    bot_node = Node(
                        x, y, level.previous_lvl.elevation,
                        level.previous_lvl.restraint)
                    level.previous_lvl.nodes.add(bot_node)
                # add the column connecting the two nodes
                level.columns.add(Column(top_node, bot_node, ang))

    def add_beam_at_points(self,
                           pi_x: float,
                           pi_y: float,
                           pj_x: float,
                           pj_y: float,
                           ang: float):
        """
        TODO - add docstring
        """
        for level in self.levels.active:
            # check to see if start node exists
            start_node = level.look_for_node(pi_x, pi_y)
            # create it if it does not exist
            if not start_node:
                start_node = Node(pi_x, pi_y, level.elevation, level.restraint)
                level.nodes.add(start_node)
            # check to see if end node exists
            end_node = level.look_for_node(pj_x, pj_y)
            # create it if it does not exist
            if not end_node:
                end_node = Node(pj_x, pj_y, level.elevation, level.restraint)
                level.nodes.add(end_node)
            # add the beam connecting the two nodes
            level.beams.add(Beam(start_node, end_node, ang))

    def add_columns_from_grids(self):
        isect_pts = self.gridsystem.intersection_points()
        for pt in isect_pts:
            self.add_column_at_point(pt[0], pt[1], 0.00)

    def add_beams_from_grids(self):
        for grid in self.gridsystem.grids:
            isect_pts = self.gridsystem.intersect(grid)
            for i in range(len(isect_pts)-1):
                self.add_beam_at_points(
                    *isect_pts[i],
                    *isect_pts[i+1],
                    0.00
                )

    #############################################
    # Set active methods - alter active objects #
    #############################################

    def set_active_levels(self, names: List[str]):
        """
        Sets the active levels of the building.
        An empty `names` list is interpreted as
        activating all levels.
        """
        self.levels.set_active(names)

    def set_active_groups(self, names: List[str]):
        """
        Sets the active groups of the building.
        """
        self.groups.set_active(names)

    ###############################
    # Structural analysis methods #
    ###############################

    def number_components(self):
        """
        Assigns unique ID numbers to all components of the building.
        These numbers will be used in OpenSees.
        """

        def assign_numbers(list_of_list_of_things, i):
            for sub_list in list_of_list_of_things:
                for thing in sub_list:
                    thing.uniq_id = i
                    i += 1
            return i

        i = 1
        i = assign_numbers([lvl.nodes.node_list
                            for lvl in self.levels.level_list], i)
        i = assign_numbers([lvl.columns.column_list
                            for lvl in self.levels.level_list], i)
        i = assign_numbers([lvl.beams.beam_list
                            for lvl in self.levels.level_list], i)

    def lock(self):
        """
        Lock the building. No further editing beyond this point.
        """
        self.number_components()


# The following functions use the Building
# class to interact with OpenSeesPy


def to_OpenSeesPy(building: Building):
    """
    Defines the model in OpenSeesPy on the spot
    """
    # TODO
    A, Iz, Iy, J = 0.04, 0.0010667, 0.0002667, 0.01172
    E = 25.0e6
    G = 9615384.6

    ops.wipe()
    ops.model('basic', '-ndm', building.ndm,
              '-ndf', building.ndf)
    # define the nodes
    for lvl in building.levels.level_list:
        for node in lvl.nodes.node_list:
            ops.node(
                node.uniq_id,
                node.x_coord,
                node.y_coord,
                lvl.elevation
            )
            # check restraints
            if node.restraint_type == "fixed":
                ops.fix(node.uniq_id, 1, 1, 1, 1, 1, 1)
            elif node.restraint_type == "pinned":
                ops.fix(node.uniq_id, 1, 1, 1, 0, 0, 0)
            # apply mass
            # TODO
            ops.mass(node.uniq_id, 1., 1., 1., 0.001, 0.001, 0.001)

        # define the columns
        for col in lvl.columns.column_list:
            ops.geomTransf(
                'Linear',
                col.uniq_id,
                *col.local_y_axis_vector()
            )
            ops.element(
                'elasticBeamColumn',
                col.uniq_id,
                col.node_i.uniq_id,
                col.node_j.uniq_id,
                A, E, G, J, Iy, Iz, col.uniq_id)

        # define the beams
        for beam in lvl.beams.beam_list:
            ops.geomTransf(
                'Linear',
                beam.uniq_id + 150,
                *beam.local_y_axis_vector()
            )
            # TODO -> map coordinate transforms and use the same
            ops.element(
                'elasticBeamColumn',
                beam.uniq_id,
                beam.node_i.uniq_id,
                beam.node_j.uniq_id,
                A, E, G, J, Iy, Iz, beam.uniq_id + 150)

    opsv.plot_model()
    plt.show()


def from_OpenSeesPy(building: 'Building'):
    """
    Read back the OpenSees results and update the
    values contained in the Building Object
    """
    pass


def generate_OpenSeesPy_file(building: 'Building'):
    """
    Generates the input model.py file to be used
    with OpenSeesPy (as if it was manually written)
    """
    #  But I don't think I'll be able to read back
    #  the results this way.
    pass


def generate_OpenSees_file(building: 'Building'):
    """
    Generates the input model.tcl file to be used
    with OpenSees (as if it was manually written)
    """
    pass
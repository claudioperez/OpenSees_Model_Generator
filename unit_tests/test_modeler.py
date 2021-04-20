
#   __                 UC Berkeley
#   \ \/\   /\/\/\     John Vouvakis Manousakis
#    \ \ \ / /    \    Dimitrios Konstantinidis
# /\_/ /\ V / /\/\ \
# \___/  \_/\/    \/   April 2021
#
# https://github.com/ioannis-vm/OpenSeesPy_Building_Modeler/blob/main/modeler.py

import unittest
from modeler import Building, Level, GridLine, Group, LinearElement, Node

# https://docs.python.org/3/library/unittest.html


class TestLevelOperations(unittest.TestCase):

    def setUp(self):
        self.b = Building()

    def test_add_levels_in_order(self):
        self.b.add_level("base", 0.00, "fixed")
        self.b.add_level("1", 3.00)
        self.b.add_level("2", 6.00)
        self.b.add_level("3", 9.00)

    def tearDown(self):
        del(self.b)


class TestGridLineOperations(unittest.TestCase):

    def setUp(self):
        self.b = Building()

    def test_add_some_gridlines(self):
        self.b.add_gridline("1", 0., 0., 8., 0.)
        self.b.add_gridline("2", 0., 4., 8., 4.)
        self.b.add_gridline("3", 0., 8., 8., 8.)
        self.b.add_gridline("A", 0., 0., 0., 8.)
        self.b.add_gridline("B", 4., 0., 4., 8.)
        self.b.add_gridline("C", 8., 0., 8., 8.)

    def tearDown(self):
        del(self.b)


class TestGroupOperations(unittest.TestCase):

    def setUp(self):
        self.b = Building()

    def test_add_some_groups(self):
        self.b.add_group('EastFrame')
        self.b.add_group('WestFrame')

    def tearDown(self):
        del(self.b)


class TestNodeOperations(unittest.TestCase):

    def setUp(self):
        self.b = Building()
        self.b.add_level("base", 0.00, "fixed")
        self.b.add_level("1", 3.00)

    def test_add_nodes(self):
        self.b.add_node(0.00, 0.00)
        self.b.add_node(1.00, 0.00)

    def tearDown(self):
        del(self.b)


class TestLinearElement1(unittest.TestCase):

    def setUp(self):
        self.n1 = Node(0.00, 0.00, 0.00)
        self.n2 = Node(5.00, 0.00, 0.00)
        self.elm = LinearElement(self.n1, self.n2, 0.00)

    def test_y_axis(self):
        axis = self.elm.local_y_axis_vector()
        # self.assertEqual(axis, np.array([0., -1., 0.])


class TestLinearElement2(unittest.TestCase):

    def setUp(self):
        self.n1 = Node(0.00, 0.00, 3.00)
        self.n2 = Node(0.00, 0.00, 0.00)
        self.elm = LinearElement(self.n1, self.n2, 0.00)

    def test_y_axis(self):
        axis = self.elm.local_y_axis_vector()
        # assertEqual(axis, np.array([1., 0., 0.])


class TestColumnOperations(unittest.TestCase):

    def setUp(self):
        self.b = Building()
        self.b.add_level("base", 0.00, "fixed")
        self.b.add_level("1", 3.00)
        self.b.levels.set_active(['1'])

    def test_add_columns(self):
        self.b.add_column_at_point(0.00, 1.00, 0.00)
        self.b.add_column_at_point(1.00, 1.00, 0.00)
        self.b.add_column_at_point(1.00, 0.00, 0.00)
        self.b.add_columns_from_grids()

    def tearDown(self):
        del(self.b)


class TestBeamOperations(unittest.TestCase):

    def setUp(self):
        self.b = Building()
        self.b.add_level("base", 0.00, "fixed")
        self.b.add_level("1", 3.00)
        self.b.set_active_levels(['1'])

    def test_add_a_single_beam(self):
        self.b.add_beam_at_points(0.50, 0.50, 1.50, 1.50, 0.00)

    def tearDown(self):
        del(self.b)


if (__name__ == '__main__'):
    unittest.main()
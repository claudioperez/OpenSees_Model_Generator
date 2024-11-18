# ---
# jupyter:
#   jupytext:
#     cell_markers: '"""'
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
"""
# Defining a Model

This section demonstrates the model definition process.

## Model Definition Overview

The overall procedure for defining the elements of a model can be
broken down into the following steps:

- Set active levels

- Define components

- Execute pre-processing methods

The model can be visualized at any step in the process to confirm its validity.

**To see all the available arguments of each of the following methods,
please read the API reference or their docstrings**.

Alternatively, use the `help()` function inside a python shell.
e.g. `help(mdl.add_level)`

You can also use `pydoc <osmg.name_of_module>` in a terminal window.
"""

# %%
# imports
import numpy as np

from osmg import defaults, model
from osmg.gen.component_gen import BeamColumnGenerator
from osmg.gen.section_gen import SectionGenerator
from osmg.graphics.preprocessing_3d import show
from osmg.ops.element import ElasticBeamColumn
from osmg.ops.section import ElasticSection

# %%
# Instantiate a model
mdl = model.Model('example_model')


# %%
help(mdl.add_level)


# %%
# Define levels
for i in range(3):
    mdl.add_level(i, 144.00 * (i))


# %%
defaults.load_default_steel(mdl)
steel_phys_mat = mdl.physical_materials.retrieve_by_attr('name', 'default steel')


# %%
# define line element sections
secg = SectionGenerator(mdl)
secg.load_aisc_from_database(
    'W', ['W24X94'], 'default steel', 'default steel', ElasticSection
)


# %%
# set active levels
mdl.levels.set_active([1, 2])


# %%
p1 = np.array((0.00, 0.00))
p2 = np.array((360.0, 0.00))
p3 = np.array((360.0, 360.0))
p4 = np.array((0.00, 360.00))


# %%
mcg = BeamColumnGenerator(mdl)
sec = mdl.elastic_sections.retrieve_by_attr('name', 'W24X94')
for pt in [p1, p2, p3, p4]:
    mcg.add_vertical_active(
        x_coord=pt[0],
        y_coord=pt[1],
        offset_i=np.zeros(3),
        offset_j=np.zeros(3),
        transf_type='Corotational',
        n_sub=4,
        section=sec,
        element_type=ElasticBeamColumn,
        placement='centroid',
        angle=0.00,
    )


# %%
for pair in ((p1, p2), (p2, p3), (p3, p4), (p4, p1)):
    mcg.add_horizontal_active(
        xi_coord=pair[0][0],
        yi_coord=pair[0][1],
        xj_coord=pair[1][0],
        yj_coord=pair[1][1],
        offset_i=np.zeros(3),
        offset_j=np.zeros(3),
        snap_i='centroid',
        snap_j='centroid',
        transf_type='Linear',
        n_sub=4,
        section=sec,
        element_type=ElasticBeamColumn,
        placement='top_center',
        angle=0.00,
    )


# %%
show(mdl)


# %%
# fixing the base
for node in mdl.levels[0].nodes.values():
    node.restraint = [True, True, True, False, False, False]


# %%
show(mdl)


# %% [markdown]
"""
## Preprocessing
"""

# %% [markdown]
"""
Now that all the intended elements have been defined, we can apply
pre-processing methods to the model.

Some common methods are the following:

* `rigid_diaphragms` assigns rigid diaphragm constraints to all
  specified levels. Only primary nodes are affected (not internal
  nodes of component assemblies).

* `self_weight`, `self_mass` assign self-weight loads and lumped
  self-mass to all the elements / nodes.

Loads, mass, and diaphragm constraints are load_case-specific.
"""


# %%
# imports
from osmg.load_case import LoadCase
from osmg.preprocessing.self_weight_mass import self_mass, self_weight

# %%
testcase = LoadCase('test', mdl)


# %%
self_weight(mdl, testcase)
self_mass(mdl, testcase)


# %%
testcase.rigid_diaphragms([1, 2])


# %%
# visualize the model
show(mdl, testcase, extrude=True)

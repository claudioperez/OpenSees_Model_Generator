from tributary_area_load_distr.mesher import Vertex, Edge, define_halfedges
import pandas as pd
# # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# define the vertices
vertices = [
    Vertex((0., 1.)),
    Vertex((0., 0.)),
    Vertex((1., 0.)),
]


# define the edges
edges = [
    Edge(vertices[0], vertices[1]),
    Edge(vertices[1], vertices[2]),
]


# # # # # # # # # # #

define_halfedges(edges)

halfedges = []
for edge in edges:
    if edge.h_i not in halfedges:
        halfedges.append(edge.h_i)
    if edge.h_j not in halfedges:
        halfedges.append(edge.h_j)

results = {
    'halfedge': [],
    'vertex': [],
    'edge': [],
    'next': [],
}

for h in halfedges:
    results['halfedge'].append(h)
    results['vertex'].append(h.vertex)
    results['edge'].append(h.edge)
    results['next'].append(h.nxt)


df = pd.DataFrame(results)
print(df)


def is_in_some_loop(halfedge, loops):
    for loop in loops:
        if halfedge in loop:
            return True
    return False


loops = []
for halfedge in halfedges:
    if loops:
        if is_in_some_loop(halfedge, loops):
            continue
    loop = [halfedge]
    nxt = halfedge.nxt
    while(nxt != halfedge):
        loop.append(nxt)
        nxt = nxt.nxt
    loops.append(loop)

print('Formed the following loops:')
for loop in loops:
    print(loop)
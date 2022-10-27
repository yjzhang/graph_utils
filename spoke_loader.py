# Import spoke matrix from a neo4j csv dump.

import csv
import gzip
import json
import os

from scipy import sparse, io


# TODO: multiple edges between two nodes?
def import_csv(csv_filename, edges_to_include=None, remove_unused_nodes=False):
    """
    Args:
        csv_filename: name of csv file
        edges_to_include: set of edge types
        remove_unused_nodes: True if nodes with no in- or out-edges are to be removed.

    Returns:
        nodes: list of (_id, _name, _labels_id) where _labels_id corresponds to a key in node_types
        edges: dict of (node1, node2): _type_id where node1 and node2 index into nodes, and _type_id corresponds to a key in edge_types
        node_types: dict of int: str (_labels)
        edge_types: dict of int: str (_type)
    """
    nodes = []
    n_nodes = 0
    # mapping of _id to index in nodes
    node_index = {}
    # node_types is a map of string (
    node_types = {}
    edges = {}
    # edge_types is a map of string (_type) to node
    edge_types = {}
    # sets of nodes that have in-edges or out-edges (to use when deciding whether to remove nodes)
    node_has_edge = set()
    csv.field_size_limit(99999999)
    if csv_filename.endswith('.gz'):
        # handle gzip
        f = gzip.open(csv_filename, 'rt')
    else:
        f = open(csv_filename)
    dr = csv.DictReader(f, dialect='unix')
    for i, row in enumerate(dr):
        if i % 10000 == 0:
            print(i, 'nodes: ', len(node_index), 'edges: ', len(edges))
        # if this is a node
        if row['_id']:
            print(row['license'])
            if row['name']:
                row_name = row['name']
                print(row_name)
            else:
                row_name = row['pref_name']
            if row['_labels'] in node_types:
                nodes.append((int(row['_id']), row_name, node_types[row['_labels']]))
            else:
                nodes.append((int(row['_id']), row_name, len(node_types) + 1))
                node_types[row['_labels']] = len(node_types) + 1
            node_index[int(row['_id'])] = n_nodes 
            n_nodes += 1
        # if this row is an edge
        else:
            edge_type = row['_type']
            if edges_to_include is None or edge_type in edges_to_include:
                node1 = int(row['_start'])
                node2 = int(row['_end'])
                node_has_edge.add(node1)
                node_has_edge.add(node2)
                if edge_type in edge_types:
                    edges[(node1, node2)] = edge_types[edge_type]
                else:
                    edges[(node1, node2)] = len(edge_types) + 1
                    edge_types[row['_type']] = len(edge_types) + 1
    if remove_unused_nodes:
        # remove all nodes that don't have edges
        to_remove = set(node_index.keys()).difference(node_has_edge)
        nodes = [n for n in nodes if n[0] not in to_remove]
        # rebuild node_index
        node_index = {n[0]: i for i, n in enumerate(nodes)}
    # convert edge indices
    new_edges = {}
    for k, e in edges.items():
        node1, node2 = k
        node1 = node_index[node1]
        node2 = node_index[node2]
        new_edges[(node1, node2)] = e
    edges = new_edges
    node_types = {v: k for k, v in node_types.items()}
    edge_types = {v: k for k, v in edge_types.items()}
    return nodes, edges, node_types, edge_types

# TODO: multiple edges between two nodes?
def import_jsonl(filename, edges_to_include=None, remove_unused_nodes=True):
    """
    Imports a jsonl file.
    Args:
        filename: name of jsonl file
        edges_to_include: set of edge types
        remove_unused_nodes: True if nodes with no in- or out-edges are to be removed.

    Returns:
        nodes: list of (_id, _name, _labels_id) where _labels_id corresponds to a key in node_types
        edges: dict of (node1, node2): _type_id where node1 and node2 index into nodes, and _type_id corresponds to a key in edge_types
        node_types: dict of int: str (_labels)
        edge_types: dict of int: str (_type)
    """
    nodes = []
    n_nodes = 0
    # mapping of _id to index in nodes
    node_index = {}
    # node_types is a map of string (
    node_types = {}
    edges = {}
    # edge_types is a map of string (_type) to node
    edge_types = {}
    # sets of nodes that have in-edges or out-edges (to use when deciding whether to remove nodes)
    node_has_edge = set()
    if filename.endswith('.gz'):
        # handle gzip
        f = gzip.open(filename, 'rt')
    else:
        f = open(filename)
    line = f.readline()
    i = 0
    while line:
        row = json.loads(line)
        if i % 10000 == 0:
            print(i, 'nodes: ', len(node_index), 'edges: ', len(edges))
        # if this is a node
        if row['type'] == 'node':
            if 'name' in row['properties'] and row['properties']['name'] != '':
                row_name = row['properties']['name']
            elif 'pref_name' in row['properties'] and row['properties']['pref_name'] != '':
                row_name = row['properties']['pref_name']
            elif 'identifier' in row['properties'] and row['properties']['identifier'] != '':
                row_name = row['properties']['identifier']
            elif 'id' in row['properties'] and row['properties']['id']:
                row_name = row['properties']['id']
            else:
                row_name = ''
            row_label = row['labels'][0]
            if row_label in node_types:
                nodes.append((int(row['id']), row_name, node_types[row_label]))
            else:
                nodes.append((int(row['id']), row_name, len(node_types) + 1))
                node_types[row_label] = len(node_types) + 1
            node_index[int(row['id'])] = n_nodes 
            n_nodes += 1
        # if this row is an edge
        else:
            edge_type = row['label']
            if edges_to_include is None or edge_type in edges_to_include:
                node1 = int(row['start']['id'])
                node2 = int(row['end']['id'])
                node_has_edge.add(node1)
                node_has_edge.add(node2)
                if edge_type in edge_types:
                    edges[(node1, node2)] = edge_types[edge_type]
                else:
                    edges[(node1, node2)] = len(edge_types) + 1
                    edge_types[edge_type] = len(edge_types) + 1
        line = f.readline()
        i += 1
    if remove_unused_nodes:
        # remove all nodes that don't have edges
        to_remove = set(node_index.keys()).difference(node_has_edge)
        nodes = [n for n in nodes if n[0] not in to_remove]
        # rebuild node_index
        node_index = {n[0]: i for i, n in enumerate(nodes)}
    # convert edge indices
    new_edges = {}
    for k, e in edges.items():
        node1, node2 = k
        node1 = node_index[node1]
        node2 = node_index[node2]
        new_edges[(node1, node2)] = e
    edges = new_edges
    node_types = {v: k for k, v in node_types.items()}
    edge_types = {v: k for k, v in edge_types.items()}
    return nodes, edges, node_types, edge_types




def import_nodes_edges(node_file, edges_file):
    """
    Imports nodes and edges separately.
    """
    # TODO: make this work


def to_sparse(nodes, edges):
    """
    Returns a DOK matrix from the edges...
    """
    n_nodes = len(nodes)
    edge_matrix = sparse.dok_array((n_nodes, n_nodes), dtype=int)
    for k, v in sorted(edges.items()):
        n1, n2 = k
        edge_matrix[n1, n2] = v
    return edge_matrix


def load_spoke(filename='spoke.csv', edges_to_include=None, remove_unused_nodes=False, mtx_filename='spoke.mtx'):
    if filename.endswith('.csv') or filename.endswith('.csv.gz'):
        nodes, edges, node_types, edge_types = import_csv(filename, edges_to_include, remove_unused_nodes)
    elif filename.endswith('.json') or filename.endswith('.json.gz') or filename.endswith('.jsonl') or filename.endswith('.jsonl.gz'):
        nodes, edges, node_types, edge_types = import_jsonl(filename, edges_to_include, remove_unused_nodes)
    if not os.path.exists(mtx_filename):
        edge_matrix = to_sparse(nodes, edges)
        io.mmwrite(mtx_filename, edge_matrix)
    else:
        edge_matrix = io.mmread(mtx_filename)
    return nodes, edges, node_types, edge_types, edge_matrix

def symmetrize_matrix(matrix):
    """
    Symmetrizes an adjacency matrix.

    Warning: this completely destroys any meaning applied to node values. Nonzero = edge exists, zero = edge doesn't exist.
    """
    lower_triangle = sparse.tril(matrix)
    upper_triangle = sparse.triu(matrix)
    return lower_triangle + lower_triangle.T + upper_triangle + upper_triangle.T

if __name__ == '__main__':
    #nodes, edges, node_types, edge_types, edge_matrix = load_spoke('spoke_2021.csv', remove_unused_nodes=True, mtx_filename='spoke_2021.mtx.gz')
    nodes, edges, node_types, edge_types = import_jsonl('spoke_2021.jsonl.gz', remove_unused_nodes=True)
    # TODO: compute some graph statistics?
    from collections import Counter
    node_type_counts = Counter()
    for n in nodes:
        node_type_counts[n[2]] += 1
    node_type_counts = {node_types[k]: c for k, c in node_type_counts.items()}
    edge_type_counts = Counter()
    for k, e in edges.items():
        edge_type_counts[e] += 1
    edge_type_counts = {edge_types[k]: c for k, c in edge_type_counts.items()}
    with open('spoke_2021_node_types.json', 'w') as f:
        json.dump(node_type_counts, f, indent=2)
    with open('spoke_2021_edge_types.json', 'w') as f:
        json.dump(edge_type_counts, f, indent=2)



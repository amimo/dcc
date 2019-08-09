from __future__ import division

from builtins import range
#
# Copyright (c) 2012 Geoffroy Gueguen <geoffroy.gueguen@gmail.com>
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from builtins import str
from collections import defaultdict

from dex2c.basic_blocks import (IrBasicBlock, LandingPad)
from dex2c.instruction import *

logger = logging.getLogger('dex2c.graph')


class Graph(object):
    def __init__(self):
        self.entry = None
        self.exit = None
        self.nodes = list()
        self.landing_pads = list()
        self.rpo = []
        self.edges = defaultdict(list)
        self.catch_edges = defaultdict(list)
        self.reverse_edges = defaultdict(list)
        self.reverse_catch_edges = defaultdict(list)
        self.loc_to_ins = None
        self.loc_to_node = None
        self.offset_to_node = {}
        self.node_to_landing_pad = {}

    def sucs(self, node):
        return self.edges.get(node, [])[:]

    def all_sucs(self, node):
        return self.edges.get(node, []) + self.catch_edges.get(node, [])

    def all_catches(self, node):
        return self.catch_edges.get(node, [])[:]

    def preds(self, node):
        return [n for n in self.reverse_edges.get(node, []) if not n.in_catch]

    def all_preds(self, node):
        return (self.reverse_edges.get(node, []) + self.reverse_catch_edges.get(
            node, []))

    def add_node(self, node):
        self.nodes.append(node)

    def add_landing_pad(self, pad):
        self.landing_pads.append(pad)

    def add_edge(self, e1, e2):
        lsucs = self.edges[e1]
        if e2 not in lsucs:
            lsucs.append(e2)
        lpreds = self.reverse_edges[e2]
        if e1 not in lpreds:
            lpreds.append(e1)

    def remove_edge(self, e1, e2):
        lsucs = self.edges[e1]
        if e2 in lsucs:
            lsucs.remove(e2)

        lpreds = self.reverse_edges[e2]
        if e1 in lpreds:
            lpreds.remove(e1)

    def add_catch_edge(self, e1, e2):
        lsucs = self.catch_edges[e1]
        if e2 not in lsucs:
            lsucs.append(e2)
        lpreds = self.reverse_catch_edges[e2]
        if e1 not in lpreds:
            lpreds.append(e1)

    def remove_node(self, node):
        preds = self.reverse_edges.get(node, [])
        for pred in preds:
            self.edges[pred].remove(node)

        succs = self.edges.get(node, [])
        for suc in succs:
            self.reverse_edges[suc].remove(node)

        exc_preds = self.reverse_catch_edges.pop(node, [])
        for pred in exc_preds:
            self.catch_edges[pred].remove(node)

        exc_succs = self.catch_edges.pop(node, [])
        for suc in exc_succs:
            self.reverse_catch_edges[suc].remove(node)

        self.nodes.remove(node)
        if node in self.rpo:
            self.rpo.remove(node)
        del node

    def number_ins(self):
        self.loc_to_ins = {}
        self.loc_to_node = {}
        num = 0
        for node in self.rpo:
            start_node = num
            num = node.number_ins(num)
            end_node = num - 1
            self.loc_to_ins.update(node.get_loc_with_ins())
            self.loc_to_node[start_node, end_node] = node

    def get_ins_from_loc(self, loc):
        return self.loc_to_ins.get(loc)

    def get_node_from_loc(self, loc):
        for (start, end), node in self.loc_to_node.items():
            if start <= loc <= end:
                return node

    def remove_ins(self, loc):
        ins = self.get_ins_from_loc(loc)
        self.get_node_from_loc(loc).remove_ins(loc, ins)
        self.loc_to_ins.pop(loc)

    def compute_rpo(self):
        """
        Number the nodes in reverse post order.
        An RPO traversal visit as many predecessors of a node as possible
        before visiting the node itself.
        """
        nb = len(self.nodes) + 1
        for node in self.post_order():
            node.num = nb - node.po
        self.rpo = sorted(self.nodes, key=lambda n: n.num)

    def compute_block_order(self):
        list = sorted(self.nodes, key=lambda n: n.start)
        for num, node in enumerate(list):
            node.num = num
        return list

    def post_order(self):
        """
        Return the nodes of the graph in post-order i.e we visit all the
        children of a node before visiting the node itself.
        """

        def _visit(n, cnt):
            visited.add(n)
            for suc in self.all_sucs(n):
                if suc not in visited:
                    for cnt, s in _visit(suc, cnt):
                        yield cnt, s
            n.po = cnt
            yield cnt + 1, n

        visited = set()
        for _, node in _visit(self.entry, 1):
            yield node

    def draw(self, name, dname, draw_branches=True):
        from pydot import Dot, Edge,Node
        g = Dot()
        g.set_node_defaults(color='lightgray',
                            style='filled',
                            shape='box',
                            fontname='Courier',
                            fontsize='10')
        if len(self.nodes) == 1:
            g.add_node(Node(str(self.nodes[0])))
        else:
            for node in sorted(self.nodes, key=lambda x: x.num):
                for suc in self.sucs(node):
                    g.add_edge(Edge(str(node), str(suc), color='blue'))
                for except_node in self.catch_edges.get(node, []):
                    g.add_edge(Edge(str(node),
                                    str(except_node),
                                    color='black',
                                    style='dashed'))

        g.write_png('%s/%s.png' % (dname, name))

    def immediate_dominators(self):
        return dom_lt(self)

    def __len__(self):
        return len(self.nodes)

    def __repr__(self):
        return str(self.nodes)

    def __iter__(self):
        for node in self.nodes:
            yield node


def dom_lt(graph):
    """Dominator algorithm from Lengaeur-Tarjan"""

    def _dfs(v, n):
        semi[v] = n = n + 1
        vertex[n] = label[v] = v
        ancestor[v] = 0
        for w in graph.all_sucs(v):
            if not semi[w]:
                parent[w] = v
                n = _dfs(w, n)
            pred[w].add(v)
        return n

    def _compress(v):
        u = ancestor[v]
        if ancestor[u]:
            _compress(u)
            if semi[label[u]] < semi[label[v]]:
                label[v] = label[u]
            ancestor[v] = ancestor[u]

    def _eval(v):
        if ancestor[v]:
            _compress(v)
            return label[v]
        return v

    def _link(v, w):
        ancestor[w] = v

    parent, ancestor, vertex = {}, {}, {}
    label, dom = {}, {}
    pred, bucket = defaultdict(set), defaultdict(set)

    # Step 1:
    semi = {v: 0 for v in graph.nodes}
    n = _dfs(graph.entry, 0)
    for i in range(n, 1, -1):
        w = vertex[i]
        # Step 2:
        for v in pred[w]:
            u = _eval(v)
            y = semi[w] = min(semi[w], semi[u])
        bucket[vertex[y]].add(w)
        pw = parent[w]
        _link(pw, w)
        # Step 3:
        bpw = bucket[pw]
        while bpw:
            v = bpw.pop()
            u = _eval(v)
            dom[v] = u if semi[u] < semi[v] else pw
    # Step 4:
    for i in range(2, n + 1):
        w = vertex[i]
        dw = dom[w]
        if dw != vertex[semi[w]]:
            dom[w] = dom[dw]
    dom[graph.entry] = None
    return dom


def bfs(start):
    to_visit = [start]
    visited = set([start])
    while to_visit:
        node = to_visit.pop(0)
        yield node
        if node.exception_analysis:
            for _, _, exception in node.exception_analysis.exceptions:
                if exception not in visited:
                    to_visit.append(exception)
                    visited.add(exception)
        for _, _, child in node.childs:
            if child not in visited:
                to_visit.append(child)
                visited.add(child)


def construct(start_block):
    bfs_blocks = bfs(start_block)

    graph = Graph()

    block_to_node = {}
    node_to_landing_pad = {}

    # 每个异常exception_analysis 对应一个分发异常的landingping_pad, 不同的block可以有相同的异常处理
    exception_to_landing_pad = {}

    for block in bfs_blocks:
        node = block_to_node.get(block)
        if node is None:
            node = IrBasicBlock(block)
            block_to_node[block] = node
        graph.add_node(node)

        if block.exception_analysis:
            if block.exception_analysis in exception_to_landing_pad:
                landing_pad = exception_to_landing_pad[block.exception_analysis]
            else:
                # 初始化 LandingPad
                landing_pad = LandingPad(node)
                graph.add_landing_pad(landing_pad)
                exception_to_landing_pad[block.exception_analysis] = landing_pad
                for _type, _, exception_target in block.exception_analysis.exceptions:
                    catch_node = block_to_node.get(exception_target)
                    if catch_node is None:
                        catch_node = IrBasicBlock(exception_target)
                        block_to_node[exception_target] = catch_node

                    catch_node.set_catch_type(_type)
                    catch_node.in_catch = True

                    landing_pad.add_catch_handle(_type, catch_node)

            # 将catch 节点加入到node后继
            for _type, _, exception_target in block.exception_analysis.exceptions:
                catch_node = block_to_node.get(exception_target)
                assert catch_node is not None
                node.add_catch_successor(catch_node)
                graph.add_catch_edge(node, catch_node)
            # 更新节点对应的LandingPad
            node_to_landing_pad[node] = landing_pad

        for _, _, child_block in block.childs:
            child_node = block_to_node.get(child_block)
            if child_node is None:
                child_node = IrBasicBlock(child_block)
                block_to_node[child_block] = child_node
            graph.add_edge(node, child_node)

    graph.entry = block_to_node[start_block]

    graph.compute_rpo()

    offset_to_node = {}
    for node in graph.rpo:
        if node.start >= 0:
            offset_to_node[node.start] = node

    graph.node_to_landing_pad = node_to_landing_pad
    graph.offset_to_node = offset_to_node
    for node in graph.rpo:
        preds = [pred for pred in graph.all_preds(node) if pred.num < node.num]
        if preds and all(pred.in_catch for pred in preds):
            node.in_catch = True

    return graph



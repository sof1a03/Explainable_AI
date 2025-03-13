from anytree import AnyNode, RenderTree
from anytree.exporter import DotExporter
import matplotlib.pyplot as plt
from PIL import Image
import json
from itertools import product

with open("coffee.json", "r") as file:
    json_tree = json.load(file)


def build_tree(tree, parent=None):
    data = {
        key: (
            [int(v) if isinstance(v, (int, float)) else v for v in value] if isinstance(value, list)
            else int(value) if isinstance(value, (int, float))
            else value
        )
        for key, value in tree.items()
        if key != "children"
    }

    node = AnyNode(parent=parent, **data)

    # process children
    for child in tree.get("children", []):
        build_tree(child, parent=node)

    return node


def visualize_tree_textually(tree):
    for indentation, fill, node in RenderTree(tree):
        print(f"{indentation}{node.name}")


def get_tree(tree):
    tree_output = RenderTree(tree)
    print(tree_output)

    return tree_output


def visualize_tree_graphically(tree):
    DotExporter(tree).to_picture("tree.png")  # export anytree to image file

    # visualize image
    img = Image.open("tree.png")
    plt.figure(figsize=(5, 5))
    plt.imshow(img)
    plt.axis("off")
    plt.show()


def execution_traces(goal_tree_json, starting_node_name):
    """
    determines all possible behaviors (execution traces) that an agent could exhibit, based on its goal tree
    :param goal_tree_json: json file representing a goal tree
    :param starting_node_name: the name of the root node/ starting node for the traversal
    :return: list of lists representing execution traces starting from the root, with nodes being represented by their name
    """

    # convert json input to proper format
    goal_tree = goal_tree_json

    # get starting node in tree
    start_node = goal_tree
    for node in goal_tree.descendants:
        if start_node.name == starting_node_name:
            break
        else:
            start_node = node

    # recursively traverse tree to generate traces
    def _get_traces(node):
        # leave nodes are action nodes
        if node.type == "ACT":
            return [[node.name]]

        elif node.type == "OR":
            traces = []
            for child in node.children:
                for trace in _get_traces(child):
                    traces.append([node.name] + trace)

            return traces

        # list all in first visit order
        elif node.type == "AND" or node.type == "SEQ":
            parallel_traces = [_get_traces(child) for child in node.children]
            all_trace_list = [list(comb) for comb in product(*parallel_traces)]

            children_ordered = sorted(node.children, key=lambda x: x.sequence)
            children_ranked = {child.name: i for i, child in enumerate(children_ordered)}
            sorted_traces = [sorted(t, key=lambda lst: children_ranked.get(lst[0], float('inf'))) for t in
                             all_trace_list]

            current_traces = [[node.name] + sum(i, []) for i in sorted_traces]

            return current_traces

    return _get_traces(start_node)


"""
# Exercise 0
coffee_tree = build_tree(json_tree)
output = get_tree(coffee_tree)

visualize_tree_textually(coffee_tree)
visualize_tree_graphically(coffee_tree)


# Exercise 1
traces = execution_traces(build_tree(json_tree), "getCoffee")
print(traces)
"""
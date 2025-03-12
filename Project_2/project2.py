from anytree.importer import JsonImporter
from anytree import AnyNode, RenderTree
from anytree.exporter import DotExporter
import matplotlib.pyplot as plt
from PIL import Image
import json
from itertools import product

def build_tree(tree_dict, convert_to_int=False):
    if convert_to_int:
        return build_integer_tree(tree_dict)
    else:
        return tree_dict


def build_integer_tree(tree, parent=None):
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
        build_integer_tree(child, parent=node)

    return node


def import_data_from_json(json_name):
    importer = JsonImporter()
    return importer.import_(json_name)


def load_json(data_path, from_file=True):
    if from_file:
        with open(data_path, 'r') as file:
            return json.load(file)
    else:
        return json.loads(data_path)


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
    goal_tree = build_tree(load_json(goal_tree_json, from_file=True), convert_to_int=True)

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
                    #print(node.name , " " , trace)

            #for t in traces:
            #print(node.name, " NO ", traces)
            return traces

        # list all in first visit order
        elif node.type == "AND" or node.type == "SEQ":
            parallel_traces = [_get_traces(child) for child in node.children]
            all_trace_list = [list(comb) for comb in product(*parallel_traces)]
            current_traces = [[node.name] + sum(i, []) for i in all_trace_list]

            return current_traces

    return _get_traces(start_node)


# Exercise 0
"""
coffee_tree = build_tree(load_json('coffee.json'), convert_to_int=True)
output = get_tree(coffee_tree)

visualize_tree_textually(coffee_tree)
visualize_tree_graphically(coffee_tree)
"""

# Exercise 1
traces = execution_traces("coffee.json", "getCoffee")
print(traces)

# Exercise 2




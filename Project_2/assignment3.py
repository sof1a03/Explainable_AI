from anytree import AnyNode
import json
from itertools import product
from anytree import PreOrderIter

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


def get_normed_tree(tree, norm):
    if len(norm) == 0:
        return tree

    def check_violation(node, norm):
        if node.type == 'ACT':
            action_name = node.name
            if norm['type'] == 'P':  # Prohibition: Action should not be executed
                node.violation = action_name in norm['actions']
            elif norm['type'] == 'O':  # Obligation: Only permitted actions should be executed
                node.violation = action_name not in norm['actions']
            else:
                node.violation = False  # Default: No violation

        elif node.type in ['OR', 'AND', 'SEQ']:
            for child in node.children:
                check_violation(child, norm)

            if node.type == 'OR':
                node.violation = all(child.violation for child in node.children)
            elif node.type == 'AND' or node.type == 'SEQ':
                node.violation = any(child.violation for child in node.children)

    check_violation(tree, norm)
    return tree


def get_all_valid_traces(json_tree, pre, post):
    '''
    Filters the valid traces based on the pre and post conditions
    '''
    traces_with_pre_post = []
    node_traces = execution_traces(json_tree, "getCoffee")

    for trace in node_traces:
        # Filter traces that violate norms
        if not all([not node.violation for node in PreOrderIter(json_tree) if
                    hasattr(node, "violation") and node.name in trace]):
            continue
        # checking trace validity
        current_beliefs = set(pre)  # initial beliefs, set just to avoid reps
        valid = True
        for action in trace:
            node = next((n for n in PreOrderIter(json_tree) if n.name == action), None)            
            if node and hasattr(node, "pre"):
                if not all(p in current_beliefs for p in node.pre): #check precondition met
                    valid = False
                    break  # trace is invalid
            # Update beliefs after performing the action
            if node and hasattr(node, "post"):
                current_beliefs.update(node.post)
         #if preconditions are met and the post conditions are in the current valid traces, then we keep them
        if valid and all(g in current_beliefs for g in post):
            traces_with_pre_post.append(trace)

    return traces_with_pre_post


def decision_making(json_tree, norm, goal, beliefs, preferences):
    """
    :param json_tree: son object: A goal tree
    :param norm: dict: norm for violations in the tree
    :param goal: list: set of beliefs (strings) of the agent that must be true at the end of the execution of the trace
    :param beliefs: list: set of strings representing the initial beliefs of the agents
    :param preferences: list: pair describing the preference of the end-user
    :return: list of strings: represents the execution trace chosen by the agent
    """
    goal_tree = build_tree(json_tree)
    norm_tree = get_normed_tree(goal_tree, norm)
    all_traces = get_all_valid_traces(norm_tree, beliefs, goal)

    if len(all_traces) == 0:
        return all_traces

    # total cost of a trace is the sum of all costs of actions in the trace
    nodes_by_name = {node.name: node for node in PreOrderIter(norm_tree)}
    all_trace_costs = []
    for trace in all_traces:
        trace_costs = (
            [nodes_by_name.get(t, None).costs for t in trace if hasattr(nodes_by_name.get(t, None), "costs")])
        all_trace_costs.append([sum(col) for col in zip(*trace_costs)])

    print(all_trace_costs)
    preferred_trace = all_trace_costs[0]
    for t in all_trace_costs[1:]:
        for i in preferences[1]:
            if t[i] < preferred_trace[i]:
                preferred_trace = t
                break
            elif t[i] > preferred_trace[i]:
                break

    return all_traces[all_trace_costs.index(preferred_trace)]


# Exercise 3
"""
norm = {'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
goal = ['haveCoffee']
beliefs = ['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
preferences = [['quality', 'price', 'time'], [2, 0, 1]]
sol = ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
output = decision_making(json_tree, norm, goal, beliefs, preferences)
print(output)
print(output == sol)
"""

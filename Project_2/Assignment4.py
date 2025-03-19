from anytree import AnyNode, PreOrderIter
from itertools import product
import json
import numpy as np

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
                if not all(p in current_beliefs for p in node.pre):  # check precondition met
                    valid = False
                    break  # trace is invalid
            # Update beliefs after performing the action
            if node and hasattr(node, "post"):
                current_beliefs.update(node.post)
        # if preconditions are met and the post conditions are in the current valid traces, then we keep them
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

    preferred_trace = all_trace_costs[0]
    for t in all_trace_costs[1:]:
        for i in preferences[1]:
            if t[i] < preferred_trace[i]:
                preferred_trace = t
                break
            elif t[i] > preferred_trace[i]:
                break

    return all_traces[all_trace_costs.index(preferred_trace)]


def explain_or_node(or_node, selected_trace, beliefs, preferences, norm):
    explanation = []
    selected_trace = np.array(selected_trace)
    chosen_child = selected_trace[np.where(selected_trace == "getCoffee")[0] + 1]

    # chosen_child = [c for c in PreOrderIter(or_node) if c.name == chosen_child_name]
    # TODO remove
    for c in or_node.children:
        subtree_actions = [n.name for n in PreOrderIter(c)]
        if any(act in selected_trace for act in subtree_actions):
            chosen_child = c
            break
    if not chosen_child:
        return explanation

    chosen_pre = getattr(chosen_child, 'pre', [])
    explanation.append(["C", chosen_child.name, list(chosen_pre) if chosen_pre else []])

    for sibling in or_node.children:
        if sibling == chosen_child:
            continue

        child_costs = [chosen_child.costs] if hasattr(chosen_child, "costs") else []
        child_costs += [c.costs for c in chosen_child.children if hasattr(c, "costs")]
        child_costs = list(map(sum, zip(*child_costs)))
        sibling_costs = [sibling.costs] if hasattr(sibling, "costs") else []
        sibling_costs += [c.costs for c in sibling.children if hasattr(c, "costs")]
        sibling_costs = list(map(sum, zip(*sibling_costs)))


        if sibling.violation:  # Norm violation
            explanation.append(["N", sibling.name, f"{norm['type']}({', '.join(norm['actions'])})"])
        elif sibling.pre not in np.array(beliefs):
            explanation.append(["F", sibling.name, sibling.pre])
        elif next((child_costs[i] < sibling_costs[i] for i in preferences if child_costs[i] != sibling_costs[i]), None):
            explanation.append(["V", chosen_child.name, child_costs, ">", sibling.name, sibling_costs])

    return explanation


def explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain):
    selected_trace = decision_making(json_tree, norm, goal, beliefs,
                                     preferences)  # retrieve action !!! TODO make sure that it also handles multiples
    if action_to_explain not in selected_trace:  # If action not in the trace, return an empty list
        return selected_trace, []

    # convert into proper format
    root = build_tree(json_tree)
    root = get_normed_tree(root, norm)

    or_factors = []
    for node in PreOrderIter(root):  # traverse tree in pre-order
        if node.type == 'OR':
            descendants = [n.name for n in PreOrderIter(node)]
            if any(a in selected_trace for a in descendants):
                or_factors.extend(
                    explain_or_node(node, selected_trace, beliefs, preferences[1], norm))
    lookup = {n.name: n for n in PreOrderIter(root)}

    p_factors = []  # pre-conditions of the action

    for step in selected_trace:
        node = lookup.get(step)
        if node and node.type == 'ACT' and hasattr(node, 'pre') and node.pre:
            p_factors.append(["P", node.name, list(node.pre)])

        if step == action_to_explain:
            break
    d_factors = []
    target_node = lookup[action_to_explain]
    p = target_node.parent
    while p:
        if p.type in ['OR', 'AND', 'SEQ']:
            d_factors.append(["D", p.name])
        p = p.parent

    u_factor = ["U", preferences]
    explanation = or_factors + p_factors + d_factors + [u_factor]
    return selected_trace, explanation


"""
norm = {'type': 'P', 'actions': ['gotoAnnOffice']}
goal = ['haveCoffee']
beliefs = ['staffCardAvailable', 'ownCard']
preferences = [['quality', 'price', 'time'], [2, 0, 1]]
action_to_explain = "getOwnCard"
"""

norm = {"type": "P", "actions": ["payShop"]}
beliefs = ["staffCardAvailable", "ownCard", "colleagueAvailable", "haveMoney", "AnnInOffice"]
goal = ["haveCoffee"]
preferences = [["quality", "price", "time"], [1, 2, 0]]
action_to_explain = "getCoffeeKitchen"

selected_trace, output = explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain)
for i in output:
    print(i)

out = [['C', 'getKitchenCoffee', ['staffCardAvailable']],
       ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
       ['F', 'getShopCoffee', ['haveMoney']],
       ['C', 'getOwnCard', ['ownCard']],
       ['F', 'getOthersCard', ['colleagueAvailable']],
       ['P', 'getOwnCard', ['ownCard']],
       #['L', 'getOwnCard', '->', 'getCoffeeKitchen'],
       ['D', 'getStaffCard'],
       ['D', 'getKitchenCoffee'],
       ['D', 'getCoffee'],
       ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]

print(out == output)

from anytree import AnyNode, PreOrderIter
from itertools import product
import numpy as np

from anytree import AnyNode, RenderTree, PreOrderIter
import json
from itertools import product
from collections import Counter

## STEP 1: building the tree correctly for the output to be correct
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

        # Normalize the type attribute to uppercase if it exists.
    if "type" in data and isinstance(data["type"], str):
        data["type"] = data["type"].upper()

    node = AnyNode(parent=parent, **data)

    # process children
    for child in tree.get("children", []):
        build_tree(child, parent=node)

    return node

# ------------------------------------- 

#STEP 2: Identify correct Traces (assigment 1) 

def execution_traces(goal_tree_json, starting_node_name):
    
    goal_tree = goal_tree_json
    start_node = goal_tree
    for node in goal_tree.descendants:
        if node.name == starting_node_name:
            start_node = node
            break

    def _get_traces(node):
        if node.type == "ACT":
            return [[node.name]]
        elif node.type == "OR":
            return [[node.name] + trace for child in node.children for trace in _get_traces(child)]
        elif node.type in ["AND", "SEQ"]:
            parallel_traces = [_get_traces(child) for child in node.children]
            all_trace_list = [list(comb) for comb in product(*parallel_traces)]

            children_ordered = sorted(node.children, key=lambda x: getattr(x, 'sequence', 0))
            child_order_map = {child.name: i for i, child in enumerate(children_ordered)}

            sorted_traces = [
                sorted(trace, key=lambda sublist: next(
                    (child_order_map.get(name, float('inf')) for name in sublist if name in child_order_map),
                    float('inf')
                ))
                for trace in all_trace_list
            ]

            return [[node.name] + sum(t, []) for t in sorted_traces]

    return _get_traces(start_node)

# === Norm violation annotation ===
def get_normed_tree(tree, norm):
    """
    Annotates the tree with a boolean 'violation' attribute.
    - For prohibition norms ('P'), every ACT node is checked.
    - For obligation norms ('O'), every ACT node is checked:
         an ACT node is in violation if its name is NOT in norm['actions'].
    The violation status of non-ACT nodes is computed from their children.
    """
    def mark_no_violation(node):
        node.violation = False
        for child in getattr(node, 'children', []):
            mark_no_violation(child)
            
    if not norm or len(norm) == 0:
        mark_no_violation(tree)
        return tree

    def check_violation(node, norm):
        if node.type == "ACT":
            if norm["type"] == "O":
                node.violation = (node.name not in norm["actions"])
            elif norm["type"] == "P":
                node.violation = (node.name in norm["actions"])
            else:
                node.violation = False
        else:
            node.violation = False
        if node.type in ['OR', 'AND', 'SEQ']:
            for child in node.children:
                check_violation(child, norm)
            if node.type == "OR":
                node.violation = all(child.violation for child in node.children)
            elif node.type in ['AND', 'SEQ']:
                node.violation = any(child.violation for child in node.children)
    check_violation(tree, norm)
    return tree
    
def get_all_valid_traces(json_tree, pre, post):
    traces_with_pre_post = []
    node_traces = execution_traces(json_tree, "getCoffee")

    for trace in node_traces:
        if not all([not node.violation for node in PreOrderIter(json_tree) if hasattr(node, "violation") and node.name in trace]):
            continue

        current_beliefs = set(pre)
        if all(g in current_beliefs for g in post):
            traces_with_pre_post.append(trace)
            continue

        valid = True
        for action in trace:
            node = next((n for n in PreOrderIter(json_tree) if n.name == action), None)
            if node and hasattr(node, "pre") and not all(p in current_beliefs for p in node.pre):
                valid = False
                break
            if node and hasattr(node, "post"):
                current_beliefs.update(node.post)

        if valid and all(g in current_beliefs for g in post):
            traces_with_pre_post.append(trace)

    return traces_with_pre_post

# === Main decision-making function ===
def decision_making(json_tree, norm, goal, beliefs, preferences):
    """
    Selects the optimal valid execution trace according to norms, beliefs, goals, and preferences.
    """
    default_pref = [['quality', 'price', 'time'], [0, 1, 2]]
    if (not isinstance(preferences, list) or
        len(preferences) != 2 or
        not isinstance(preferences[1], list) or
        not all(isinstance(i, int) for i in preferences[1])):
        print("Invalid or missing 'preferences'. Using default preference [quality, price, time].")
        preferences = default_pref

    valid_cost_indices = [0, 1, 2]
    for idx in preferences[1]:
        if idx not in valid_cost_indices:
            print(f"Invalid cost preference index {idx}. Using default preference instead.")
            preferences = default_pref
            break

    # Build tree if necessary.
    if not hasattr(json_tree, "descendants"):
        goal_tree = build_tree(json_tree)
    else:
        goal_tree = json_tree

    norm_tree = get_normed_tree(goal_tree, norm)
    all_traces = get_all_valid_traces(norm_tree, beliefs, goal)
    if len(all_traces) == 0:
        return []

    # Gather nodes for cost lookup.
    nodes_by_name = {node.name: node for node in PreOrderIter(norm_tree)}
    all_trace_costs = []

    for trace in all_traces:
        trace_costs = []
        for t in trace:
            node = nodes_by_name.get(t, None)
            # Only include costs if the node is an ACT node; else, cost is [0.0, 0.0, 0.0].
            if node and getattr(node, "type", None) == "ACT" and hasattr(node, "costs"):
                costs = [float(c) for c in node.costs]
            else:
                costs = [0.0, 0.0, 0.0]
            trace_costs.append(costs)
        total_cost = [sum(col) for col in zip(*trace_costs)]
        all_trace_costs.append(total_cost)

    # Use lexicographic tuple comparison based on the user preference order.
    pref_order = preferences[1]
    cost_tuples = [tuple(cost[i] for i in pref_order) for cost in all_trace_costs]
    selected_index = cost_tuples.index(min(cost_tuples))
    return all_traces[selected_index]

def explain_or_node(or_node, selected_trace, beliefs, preferences, norm):
    explanation = []
    selected_trace = np.array(selected_trace)
    chosen_child = selected_trace[np.where(selected_trace == "getCoffee")[0] + 1]

    # chosen_child = [c for c in PreOrderIter(or_node) if c.name == chosen_child_name]

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
        elif getattr(sibling, 'pre', []) and not set(getattr(sibling, 'pre', [])).issubset(set(beliefs)):
            explanation.append(["F", sibling.name, getattr(sibling, 'pre', [])])
        # elif sibling.pre not in np.array(beliefs):
        #     explanation.append(["F", sibling.name, sibling.pre])
        # elif next((child_costs[i] < sibling_costs[i] for i in preferences if child_costs[i] != sibling_costs[i]), None):
        #     explanation.append(["V", chosen_child.name, child_costs, ">", sibling.name, sibling_costs])
        elif child_costs and sibling_costs and next((child_costs[i] < sibling_costs[i] 
            for i in preferences if i < len(child_costs) and i < len(sibling_costs) and child_costs[i] != sibling_costs[i]), None):
            explanation.append(["V", chosen_child.name, child_costs, ">", sibling.name, sibling_costs])

    return explanation
    
    

def get_l_factors(node, lookup, prev_node, l_factors):
    l_factors.append(["L", prev_node.name, '->', node.name])

    if not hasattr(node, "link"):
        return

    for l in node.link:
        get_l_factors(lookup[l], lookup, node, l_factors)


def explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain):
    selected_trace = decision_making(json_tree, norm, goal, beliefs,
                                     preferences)  # retrieve action 
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
    # lookup = {n.name: n for n in PreOrderIter(root)}
    lookup = {}
    for node in PreOrderIter(root):
        if node.name not in lookup:
            lookup[node.name] = node

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

    l_factors = []
    linked_nodes = target_node.link if hasattr(target_node, "link") else []
    for n in linked_nodes:
        get_l_factors(lookup[n], lookup, target_node, l_factors)

    u_factor = ["U", preferences]
    explanation = or_factors + p_factors + l_factors + d_factors 
    if explanation:
        explanation += [u_factor]
    return selected_trace, explanation


from anytree import PreOrderIter
import numpy as np
import json

# Helper function for debugging explain_action
def run_debug_explain(tree, norm, goal, beliefs, preferences, action_to_explain, expected_trace, expected_explanation, description):
    selected_trace, explanation = explain_action(tree, norm, goal, beliefs, preferences, action_to_explain)
    print("DEBUG:", description)
    print("Selected trace:", selected_trace)
    print("Explanation:", explanation)
    print("Expected trace:", expected_trace)
    print("Expected explanation:", expected_explanation)
    print("Trace pass:", selected_trace == expected_trace)
    print("Explanation pass:", explanation == expected_explanation)
    print("--------------------------")

with open("coffee1.json", "r") as file:
    coffee_tree = json.load(file)

'''Example 1'''
norm1 = {'type': 'P', 'actions': ['gotoKitchen']}
goal1 = ['haveCoffee']
beliefs1 = ['haveMoney']
preferences1 = [['quality', 'price', 'time'], [1, 2, 0]]
action_to_explain1 = "gotoShop"
true_result1 = [['C', 'getShopCoffee', ['haveMoney']],
                ['N', 'getKitchenCoffee', 'P(gotoKitchen)'],
                ['F', 'getAnnOfficeCoffee', ['AnnInOffice']],
                ['L', 'gotoShop', '->', 'getCoffeeShop'],
                ['D', 'getShopCoffee'],
                ['D', 'getCoffee'],
                ['U', [['quality', 'price', 'time'], [1, 2, 0]]]]
run_debug_explain(coffee_tree, norm1, goal1, beliefs1, preferences1, action_to_explain1, 
                  ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop'], true_result1,
                  "Example 1: Norm prohibits gotoKitchen so Shop branch is selected; explain 'gotoShop'.")

'''Example 2'''
norm2 = {'type': 'P', 'actions': ['gotoAnnOffice']}
goal2 = ['haveCoffee']
beliefs2 = ['staffCardAvailable', 'ownCard']
preferences2 = [['quality', 'price', 'time'], [2, 0, 1]]
action_to_explain2 = "getOwnCard"
true_result2 = [['C', 'getKitchenCoffee', ['staffCardAvailable']],
                ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
                ['F', 'getShopCoffee', ['haveMoney']],
                ['C', 'getOwnCard', ['ownCard']],
                ['F', 'getOthersCard', ['colleagueAvailable']],
                ['P', 'getOwnCard', ['ownCard']],
                ['L', 'getOwnCard', '->', 'getCoffeeKitchen'],
                ['D', 'getStaffCard'],
                ['D', 'getKitchenCoffee'],
                ['D', 'getCoffee'],
                ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]
run_debug_explain(coffee_tree, norm2, goal2, beliefs2, preferences2, action_to_explain2, 
                  ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'], true_result2,
                  "Example 2: Norm prohibits gotoAnnOffice so Kitchen branch is selected; explain 'getOwnCard'.")

'''Example 3'''
norm3 = {'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
goal3 = ['haveCoffee']
beliefs3 = ['haveMoney']
preferences3 = [['quality', 'price', 'time'], [2, 0, 1]]
action_to_explain3 = "gotoShop"
true_result3 = [['C', 'getShopCoffee', ['haveMoney']],
                ['N', 'getKitchenCoffee', 'O(gotoShop, payShop, getCoffeeShop)'],
                ['N', 'getAnnOfficeCoffee', 'O(gotoShop, payShop, getCoffeeShop)'],
                ['L', 'gotoShop', '->', 'getCoffeeShop'],
                ['D', 'getShopCoffee'],
                ['D', 'getCoffee'],
                ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]
run_debug_explain(coffee_tree, norm3, goal3, beliefs3, preferences3, action_to_explain3, 
                  ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop'], true_result3,
                  "Example 3: Obligation norm forces Shop branch; explain 'gotoShop'.")

'''Example 4'''
norm4 = {'type': 'P', 'actions': ['gotoKitchen']}
goal4 = ['haveCoffee']
beliefs4 = ['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
preferences4 = [['quality', 'price', 'time'], [2, 0, 1]]
action_to_explain4 = "gotoAnnOffice"
true_result4 = [['C', 'getAnnOfficeCoffee', ['AnnInOffice']],
                ['N', 'getKitchenCoffee', 'P(gotoKitchen)'],
                ['V', 'getAnnOfficeCoffee', [2, 0, 6], '>', 'getShopCoffee', [0, 3, 9]],
                ['P', 'gotoAnnOffice', ['AnnInOffice']],
                ['L', 'gotoAnnOffice', '->', 'getCoffeeAnnOffice'],
                ['D', 'getAnnOfficeCoffee'],
                ['D', 'getCoffee'],
                ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]
run_debug_explain(coffee_tree, norm4, goal4, beliefs4, preferences4, action_to_explain4, 
                  ['getCoffee', 'getAnnOfficeCoffee', 'gotoAnnOffice', 'getPod', 'getCoffeeAnnOffice'], true_result4,
                  "Example 4: Norm prohibits gotoKitchen so Ann Office branch wins by cost; explain 'gotoAnnOffice'.")

# --- Additional 5 Debugging Tests ---

'''Example 5'''
# With all beliefs provided, using default preference [0,1,2] selects the Shop branch.
# But action_to_explain is "getCoffeeKitchen" which is not in the Shop trace.
norm5 = {}
goal5 = ['haveCoffee']
beliefs5 = ['staffCardAvailable', 'ownCard', 'AnnInOffice', 'haveMoney', 'colleagueAvailable']
preferences5 = [['quality', 'price', 'time'], [0, 1, 2]]
action_to_explain5 = "getCoffeeKitchen"
expected_trace5 = ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
expected_explanation5 = []  # Because the action to explain is not in the selected trace.
run_debug_explain(coffee_tree, norm5, goal5, beliefs5, preferences5, action_to_explain5, 
                  expected_trace5, expected_explanation5,
                  "Example 5: Full beliefs, default preferences select Shop branch; 'getCoffeeKitchen' not in trace.")

'''Example 6'''
# Norm prohibits "gotoAnnOffice". Beliefs allow only 'AnnInOffice' and 'haveMoney'.
# Therefore, Ann Office branch is disqualified and Shop branch is selected.
norm6 = {'type': 'P', 'actions': ['gotoAnnOffice']}
goal6 = ['haveCoffee']
beliefs6 = ['AnnInOffice', 'haveMoney']
preferences6 = [['quality', 'price', 'time'], [2, 0, 1]]
action_to_explain6 = "gotoAnnOffice"
expected_trace6 = ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
expected_explanation6 = []  # Because "gotoAnnOffice" is not in the selected trace.
run_debug_explain(coffee_tree, norm6, goal6, beliefs6, preferences6, action_to_explain6, 
                  expected_trace6, expected_explanation6,
                  "Example 6: Norm prohibits 'gotoAnnOffice'; Shop branch selected; explain 'gotoAnnOffice' yields empty explanation.")

'''Example 7'''
# Obligation norm requires only "getKitchenCoffee" to be executed.
# Beliefs: ['staffCardAvailable', 'ownCard', 'haveMoney'] force only Kitchen branch.
# Action to explain: "getOwnCard" (which is in the Kitchen branch).
norm7 = {'type': 'O', 'actions': ['getKitchenCoffee']}
goal7 = ['haveCoffee']
beliefs7 = ['staffCardAvailable', 'ownCard', 'haveMoney']
preferences7 = [['quality', 'price', 'time'], [1, 2, 0]]
action_to_explain7 = "getOwnCard"
expected_trace7 = []
expected_explanation7 = []
run_debug_explain(coffee_tree, norm7, goal7, beliefs7, preferences7, action_to_explain7, 
                  expected_trace7, expected_explanation7,
                  "Example 7: Obligation norm forces Kitchen branch; explain 'getOwnCard'.")

'''Example 8'''
# With full beliefs and preferences [1,0,2] (i.e. price > quality > time), Ann Office branch wins.
# Action to explain is "gotoAnnOffice".
norm8 = {}
goal8 = ['haveCoffee']
beliefs8 = ['staffCardAvailable', 'ownCard', 'AnnInOffice', 'haveMoney', 'colleagueAvailable']
preferences8 = [['quality', 'price', 'time'], [1, 0, 2]]
action_to_explain8 = "gotoAnnOffice"
expected_trace8 = ['getCoffee', 'getAnnOfficeCoffee', 'gotoAnnOffice', 'getPod', 'getCoffeeAnnOffice']
expected_explanation8 = [
  ['C', 'getAnnOfficeCoffee', ['AnnInOffice']],
  ['V', 'getAnnOfficeCoffee', [2.0, 0.0, 6.0], '>', 'getKitchenCoffee', [5.0, 0.0, 3.0]],
  ['V', 'getAnnOfficeCoffee', [2.0, 0.0, 6.0], '>', 'getShopCoffee', [0.0, 3.0, 9.0]],
  ['P', 'gotoAnnOffice', ['AnnInOffice']],
  ['L', 'gotoAnnOffice', '->', 'getCoffeeAnnOffice'],
  ['D', 'getAnnOfficeCoffee'],
  ['D', 'getCoffee'],
  ['U', [['quality', 'price', 'time'], [1, 0, 2]]]
]

# (Note: Sibling factors without violations may appear with empty strings.)
run_debug_explain(coffee_tree, norm8, goal8, beliefs8, preferences8, action_to_explain8, 
                  expected_trace8, expected_explanation8,
                  "Example 8: Preferences [1,0,2] select Ann Office branch; explain 'gotoAnnOffice'.")

'''Example 9'''
# Beliefs for Kitchen branch: ['staffCardAvailable', 'ownCard'].
# In getStaffCard OR node, getOwnCard is chosen; thus, getOthersCard is not in trace.
# Action to explain: "getOthersCard" – not present.
norm9 = {}
goal9 = ['haveCoffee']
beliefs9 = ['staffCardAvailable', 'ownCard']
preferences9 = [['quality', 'price', 'time'], [0, 1, 2]]
action_to_explain9 = "getOthersCard"
expected_trace9 = ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen']
expected_explanation9 = []  # Because the action to explain is not in the selected trace.
run_debug_explain(coffee_tree, norm9, goal9, beliefs9, preferences9, action_to_explain9, 
                  expected_trace9, expected_explanation9,
                  "Example 9: 'getOthersCard' is not selected (getOwnCard chosen); explanation should be empty.")


from anytree import PreOrderIter
import numpy as np

# --- Helper function for debugging explain_action ---
def run_debug_explain(tree, norm, goal, beliefs, preferences, action_to_explain, expected_trace, expected_explanation, description):
    selected_trace, explanation = explain_action(tree, norm, goal, beliefs, preferences, action_to_explain)
    print("DEBUG:", description)
    print("Selected trace:", selected_trace)
    print("Explanation:", explanation)
    print("Expected trace:", expected_trace)
    print("Expected explanation:", expected_explanation)
    print("Trace pass:", selected_trace == expected_trace)
    print("Explanation pass:", explanation == expected_explanation)
    print("--------------------------")


# --- The coffee tree (with slink attributes as given) ---
coffee_tree = {
  "name": "getCoffee",
  "type": "OR",
  "children": [
    {"name": "getKitchenCoffee",
      "type": "SEQ",
      "pre": ["staffCardAvailable"],
      "children": [
          {"name": "getStaffCard",
            "sequence": 1,
            "type": "OR",
            "children": [
                {"name":  "getOwnCard",
                  "type": "ACT",
                  "pre": ["ownCard"],
                  "post": ["haveCard"],
                  "link": ["getCoffeeKitchen"],
                  "costs": [0.0, 0.0, 0.0]
                },
                {"name": "getOthersCard",
                  "type": "ACT",
                  "pre": ["colleagueAvailable"],
                  "post": ["haveCard"],
                  "link": ["getCoffeeKitchen"],
                  "costs": [0.0, 0.0, 2.0]
                }
            ]
          },
          {"name": "gotoKitchen",
            "type": "ACT",
            "sequence": 2,
            "post": ["atKitchen"],
            "link": ["getCoffeeKitchen"],
            "costs": [0.0, 0.0, 2.0]
          },
          {"name": "getCoffeeKitchen",
            "type": "ACT",
            "sequence": 3,
            "pre": ["haveCard", "atKitchen"],
            "post": ["haveCoffee"],
            "slink": ["getOwnCard", "getOthersCard", "gotoKitchen"],
            "costs": [5.0, 0.0, 1.0]
          }
      ]
    },
    {"name": "getAnnOfficeCoffee",
      "type": "SEQ",
      "pre": ["AnnInOffice"],
      "children": [
        {"name": "gotoAnnOffice",
          "type": "ACT",
          "sequence": 1,
          "pre": ["AnnInOffice"],
          "post": ["atAnnOffice"],
          "link": ["getCoffeeAnnOffice"],
          "costs": [0.0, 0.0, 2.0]
        },
        {"name": "getPod",
          "type": "ACT",
          "sequence": 2,
          "post": ["havePod"],
          "link": ["getCoffeeAnnOffice"],
          "costs": [0.0, 0.0, 1.0]
        },
        {"name": "getCoffeeAnnOffice",
          "type": "ACT",
          "sequence": 3,
          "pre": ["havePod", "atAnnOffice"],
          "post": ["haveCoffee"],
          "slink": ["gotoAnnOffice", "getPod"],
          "costs": [2.0, 0.0, 3.0]
          }
      ]
    },
    {"name": "getShopCoffee",
      "type": "SEQ",
      "pre": ["haveMoney"],
      "children": [
        {"name": "gotoShop",
          "type": "ACT",
          "sequence": 1,
          "post": ["atShop"],
          "link": ["getCoffeeShop"],
          "costs": [0.0, 0.0, 5.0]
        },
        {"name": "payShop",
          "type": "ACT",
          "sequence": 2,
          "pre": ["haveMoney"],
          "post": ["paidShop"],
          "link": ["getCoffeeShop"],
          "costs": [0.0, 3.0, 1.0]
        },
        {"name": "getCoffeeShop",
          "type": "ACT",
          "sequence": 3,
          "pre": ["atShop", "paidShop"],
          "post": ["haveCoffee"],
          "slink": ["gotoShop", "payShop"],
          "costs": [0.0, 0.0, 3.0]
        }
      ]
    }
  ]
}

# --- Now the debugging tests ---

# Example 1:
# norm={'type': 'P', 'actions': ['payShop']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain="getCoffeeKitchen"
# Expected trace: ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'] 
# Expected explanation:
# [['C', 'getKitchenCoffee', ['staffCardAvailable']],
#  ['F', 'getAnnOfficeCoffee', ['AnnInOffice']],
#  ['N', 'getShopCoffee', 'P(payShop)'],
#  ['C', 'getOwnCard', ['ownCard']],
#  ['F', 'getOthersCard', ['colleagueAvailable']],
#  ['P', 'getOwnCard', ['ownCard']],
#  ['P', 'getCoffeeKitchen', ['haveCard', 'atKitchen']],
#  ['D', 'getKitchenCoffee'],
#  ['D', 'getCoffee'],
#  ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['payShop']},
                  ['haveCoffee'],
                  ['staffCardAvailable', 'ownCard'],
                  [['quality', 'price', 'time'], [2, 0, 1]],
                  "getCoffeeKitchen",
                  ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'],
                  [['C', 'getKitchenCoffee', ['staffCardAvailable']],
                   ['F', 'getAnnOfficeCoffee', ['AnnInOffice']],
                   ['N', 'getShopCoffee', 'P(payShop)'],
                   ['C', 'getOwnCard', ['ownCard']],
                   ['F', 'getOthersCard', ['colleagueAvailable']],
                   ['P', 'getOwnCard', ['ownCard']],
                   ['P', 'getCoffeeKitchen', ['haveCard', 'atKitchen']],
                   ['D', 'getKitchenCoffee'],
                   ['D', 'getCoffee'],
                   ['U', [['quality', 'price', 'time'], [2, 0, 1]]]],
                  "Example 1")

# Example 2:
# norm={'type': 'P', 'actions': ['gotoAnnOffice']}
# goal=['haveCoffee']
# beliefs=['haveMoney']
# preferences=[['quality', 'price', 'time'], [1, 2, 0]]
# action_to_explain="payShop"
# Expected trace: ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
# Expected explanation:
# [['C', 'getShopCoffee', ['haveMoney']],
#  ['F', 'getKitchenCoffee', ['staffCardAvailable']],
#  ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
#  ['P', 'payShop', ['haveMoney']],
#  ['L', 'payShop', '->', 'getCoffeeShop'],
#  ['D', 'getShopCoffee'],
#  ['D', 'getCoffee'],
#  ['U', [['quality', 'price', 'time'], [1, 2, 0]]]]
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['gotoAnnOffice']},
                  ['haveCoffee'],
                  ['haveMoney'],
                  [['quality', 'price', 'time'], [1, 2, 0]],
                  "payShop",
                  ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop'],
                  [['C', 'getShopCoffee', ['haveMoney']],
                   ['F', 'getKitchenCoffee', ['staffCardAvailable']],
                   ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
                   ['P', 'payShop', ['haveMoney']],
                   ['L', 'payShop', '->', 'getCoffeeShop'],
                   ['D', 'getShopCoffee'],
                   ['D', 'getCoffee'],
                   ['U', [['quality', 'price', 'time'], [1, 2, 0]]]],
                  "Example 2")

# Example 3:
# norm={'type': 'P', 'actions': ['gotoAnnOffice']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain="getOwnCard"
# Expected trace: ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen']
# Expected explanation:
# [['C', 'getKitchenCoffee', ['staffCardAvailable']],
#  ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
#  ['F', 'getShopCoffee', ['haveMoney']],
#  ['C', 'getOwnCard', ['ownCard']],
#  ['F', 'getOthersCard', ['colleagueAvailable']],
#  ['P', 'getOwnCard', ['ownCard']],
#  ['L', 'getOwnCard', '->', 'getCoffeeKitchen'],
#  ['D', 'getStaffCard'],
#  ['D', 'getKitchenCoffee'],
#  ['D', 'getCoffee'],
#  ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['gotoAnnOffice']},
                  ['haveCoffee'],
                  ['staffCardAvailable', 'ownCard'],
                  [['quality', 'price', 'time'], [2, 0, 1]],
                  "getOwnCard",
                  ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'],
                  [['C', 'getKitchenCoffee', ['staffCardAvailable']],
                   ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
                   ['F', 'getShopCoffee', ['haveMoney']],
                   ['C', 'getOwnCard', ['ownCard']],
                   ['F', 'getOthersCard', ['colleagueAvailable']],
                   ['P', 'getOwnCard', ['ownCard']],
                   ['L', 'getOwnCard', '->', 'getCoffeeKitchen'],
                   ['D', 'getStaffCard'],
                   ['D', 'getKitchenCoffee'],
                   ['D', 'getCoffee'],
                   ['U', [['quality', 'price', 'time'], [2, 0, 1]]]],
                  "Example 3")

# Example 4:
# norm={'type': 'P', 'actions': ['payShop']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
# preferences=[['quality', 'price', 'time'], [1, 2, 0]]
# action_to_explain="getCoffeeAnnOffice"
# Expected trace: ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen']
# Expected explanation: [] (since the selected branch is Kitchen, not AnnOffice)
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['payShop']},
                  ['haveCoffee'],
                  ['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice'],
                  [['quality', 'price', 'time'], [1, 2, 0]],
                  "getCoffeeAnnOffice",
                  ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'],
                  [],
                  "Example 4")

# Example 5:
# norm={'type': 'P', 'actions': ['gotoKitchen']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard']
# preferences=[['quality', 'price', 'time'], [1, 2, 0]]
# action_to_explain="gotoKitchen"
# Expected trace: [] and expected explanation: [] (since no branch is valid)
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['gotoKitchen']},
                  ['haveCoffee'],
                  ['staffCardAvailable', 'ownCard'],
                  [['quality', 'price', 'time'], [1, 2, 0]],
                  "gotoKitchen",
                  [],
                  [],
                  "Example 5")

# Example 6:
# norm={'type': 'P', 'actions': ['gotoAnnOffice']}
# goal=['haveCoffee']
# beliefs=['haveMoney']
# preferences=[['quality', 'price', 'time'], [1, 2, 0]]
# action_to_explain="getCoffeeShop"
# Expected trace: ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
# Expected explanation:
# [['C', 'getShopCoffee', ['haveMoney']],
#  ['F', 'getKitchenCoffee', ['staffCardAvailable']],
#  ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
#  ['P', 'payShop', ['haveMoney']],
#  ['P', 'getCoffeeShop', ['atShop', 'paidShop']],
#  ['D', 'getShopCoffee'],
#  ['D', 'getCoffee'],
#  ['U', [['quality', 'price', 'time'], [1, 2, 0]]]]
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['gotoAnnOffice']},
                  ['haveCoffee'],
                  ['haveMoney'],
                  [['quality', 'price', 'time'], [1, 2, 0]],
                  "getCoffeeShop",
                  ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop'],
                  [['C', 'getShopCoffee', ['haveMoney']],
                   ['F', 'getKitchenCoffee', ['staffCardAvailable']],
                   ['N', 'getAnnOfficeCoffee', 'P(gotoAnnOffice)'],
                   ['P', 'payShop', ['haveMoney']],
                   ['P', 'getCoffeeShop', ['atShop', 'paidShop']],
                   ['D', 'getShopCoffee'],
                   ['D', 'getCoffee'],
                   ['U', [['quality', 'price', 'time'], [1, 2, 0]]]],
                  "Example 6")

# Example 7:
# norm={'type': 'P', 'actions': ['payShop']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
# preferences=[['quality', 'price', 'time'], [1, 2, 0]]
# action_to_explain="getOwnCard"
# Expected trace: ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen']
# Expected explanation:
# [['C', 'getKitchenCoffee', ['staffCardAvailable']],
#  ['V', 'getKitchenCoffee', [5, 0, 3], '>', 'getAnnOfficeCoffee', [2, 0, 6]],
#  ['N', 'getShopCoffee', 'P(payShop)'],
#  ['C', 'getOwnCard', ['ownCard']],
#  ['V', 'getOwnCard', [0, 0, 0], '>', 'getOthersCard', [0, 0, 2]],
#  ['P', 'getOwnCard', ['ownCard']],
#  ['L', 'getOwnCard', '->', 'getCoffeeKitchen'],
#  ['D', 'getStaffCard'],
#  ['D', 'getKitchenCoffee'],
#  ['D', 'getCoffee'],
#  ['U', [['quality', 'price', 'time'], [1, 2, 0]]]]
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['payShop']},
                  ['haveCoffee'],
                  ['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice'],
                  [['quality', 'price', 'time'], [1, 2, 0]],
                  "getOwnCard",
                  ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'],
                  [['C', 'getKitchenCoffee', ['staffCardAvailable']],
                   ['V', 'getKitchenCoffee', [5, 0, 3], '>', 'getAnnOfficeCoffee', [2, 0, 6]],
                   ['N', 'getShopCoffee', 'P(payShop)'],
                   ['C', 'getOwnCard', ['ownCard']],
                   ['V', 'getOwnCard', [0, 0, 0], '>', 'getOthersCard', [0, 0, 2]],
                   ['P', 'getOwnCard', ['ownCard']],
                   ['L', 'getOwnCard', '->', 'getCoffeeKitchen'],
                   ['D', 'getStaffCard'],
                   ['D', 'getKitchenCoffee'],
                   ['D', 'getCoffee'],
                   ['U', [['quality', 'price', 'time'], [1, 2, 0]]]],
                  "Example 7")

# Example 8:
# norm={'type': 'P', 'actions': ['payShop']}
# goal=['haveCoffee']
# beliefs=['haveMoney']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain="gotoAnnOffice"
# Expected trace: []
# Expected explanation: []
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['payShop']},
                  ['haveCoffee'],
                  ['haveMoney'],
                  [['quality', 'price', 'time'], [2, 0, 1]],
                  "gotoAnnOffice",
                  [],
                  [],
                  "Example 8")

# Example 9:
# norm={'type': 'P', 'actions': ['gotoKitchen']}
# goal=['haveCoffee']
# beliefs=['haveMoney']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain="payShop"
# Expected trace: ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
# Expected explanation:
# [['C', 'getShopCoffee', ['haveMoney']],
#  ['N', 'getKitchenCoffee', 'P(gotoKitchen)'],
#  ['F', 'getAnnOfficeCoffee', ['AnnInOffice']],
#  ['P', 'payShop', ['haveMoney']],
#  ['L', 'payShop', '->', 'getCoffeeShop'],
#  ['D', 'getShopCoffee'],
#  ['D', 'getCoffee'],
#  ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]
run_debug_explain(coffee_tree,
                  {'type': 'P', 'actions': ['gotoKitchen']},
                  ['haveCoffee'],
                  ['haveMoney'],
                  [['quality', 'price', 'time'], [2, 0, 1]],
                  "payShop",
                  ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop'],
                  [['C', 'getShopCoffee', ['haveMoney']],
                   ['N', 'getKitchenCoffee', 'P(gotoKitchen)'],
                   ['F', 'getAnnOfficeCoffee', ['AnnInOffice']],
                   ['P', 'payShop', ['haveMoney']],
                   ['L', 'payShop', '->', 'getCoffeeShop'],
                   ['D', 'getShopCoffee'],
                   ['D', 'getCoffee'],
                   ['U', [['quality', 'price', 'time'], [2, 0, 1]]]],
                  "Example 9")

# Example 10:
# norm={'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain="getOthersCard"
# Expected trace: []
# Expected explanation: []
run_debug_explain(coffee_tree,
                  {'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']},
                  ['haveCoffee'],
                  ['staffCardAvailable', 'ownCard'],
                  [['quality', 'price', 'time'], [2, 0, 1]],
                  "getOthersCard",
                  [],
                  [],
                  "Example 10")

# Tree A: Single ACT node missing 'pre'
treeA = {
    "name": "doSomething",
    "type": "ACT",
    "post": ["done"],
    "costs": [1.0, 2.0, 3.0]
}
# No norm is applied and the goal is "done". Beliefs are empty.
normA = {}
goalA = ["done"]
beliefsA = []
preferencesA = [['quality', 'price', 'time'], [0, 1, 2]]
action_to_explainA = "doSomething"

# Expected trace is just ["doSomething"]
# Expected explanation: since there is no pre attribute, no P factor is produced.
expected_traceA = ["doSomething"]
expected_explanationA = []  # (or possibly no P factor, if your design omits it for missing pre)

run_debug_explain(treeA, normA, goalA, beliefsA, preferencesA, action_to_explainA,
                  expected_traceA, expected_explanationA, "Weird Case Example A: Missing pre attribute")

# Tree B: OR node with duplicate action names.
treeB = {
    "name": "root",
    "type": "OR",
    "children": [
        {
            "name": "duplicate",
            "type": "ACT",
            "pre": ["a"],
            "post": ["done"],
            "costs": [1.0, 1.0, 1.0]
        },
        {
            "name": "duplicate",
            "type": "ACT",
            "pre": ["b"],
            "post": ["done"],
            "costs": [2.0, 2.0, 2.0]
        }
    ]
}
# Goal "done" is reached if one branch works.
normB = {}
goalB = ["done"]
# Provide beliefs that satisfy the first branch only.
beliefsB = ["a"]
preferencesB = [['quality', 'price', 'time'], [0, 1, 2]]
action_to_explainB = "duplicate"

# Expected trace: Since the first branch is valid, trace should be: ["root", "duplicate"]
expected_traceB = ["root", "duplicate"]
# Explanation: should include a C factor for the selected duplicate branch,
# and possibly an F factor for the other branch if its precondition ("b") is not met.
expected_explanationB = [
    ['C', 'duplicate', ['a']],
    ['F', 'duplicate', ['b']],
    ['P', 'duplicate', ['a']],
    ['D', 'root'],
    ['U', [['quality', 'price', 'time'], [0, 1, 2]]]
]

run_debug_explain(treeB, normB, goalB, beliefsB, preferencesB, action_to_explainB,
                  expected_traceB, expected_explanationB, "Weird Case Example B: Duplicate node names")
# Tree C: Composite node with an empty children list.
treeC = {
    "name": "root",
    "type": "OR",
    "children": [
        {
            "name": "emptyBranch",
            "type": "SEQ",
            "children": []  # No children provided.
        },
        {
            "name": "validAction",
            "type": "ACT",
            "pre": ["x"],
            "post": ["done"],
            "costs": [0.0, 0.0, 0.0]
        }
    ]
}
normC = {}
goalC = ["done"]
beliefsC = ["x"]
preferencesC = [['quality', 'price', 'time'], [0, 1, 2]]
action_to_explainC = "validAction"

# Expected trace: The only valid branch is the validAction branch.
expected_traceC = ["root", "validAction"]
# Expected explanation: Since validAction is an ACT node with precondition satisfied,
# a P factor should be produced, plus the D and U factors.
expected_explanationC = [
    ['C', 'validAction', ['x']],
    ['P', 'validAction', ['x']],
    ['D', 'root'],
    ['U', [['quality', 'price', 'time'], [0, 1, 2]]]
]

run_debug_explain(treeC, normC, goalC, beliefsC, preferencesC, action_to_explainC,
                  expected_traceC, expected_explanationC, "Weird Case Example C: Empty children in composite node")

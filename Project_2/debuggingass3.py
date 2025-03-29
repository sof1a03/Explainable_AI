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
    def mark_no_violation(node):
        node.violation = False
        for child in getattr(node, 'children', []):
            mark_no_violation(child)

    if len(norm) == 0:
        mark_no_violation(tree)
        return tree

    def check_violation(node, norm):
        node.violation = False
        node_type = getattr(node, "type", None)

        if node_type == 'ACT':
            action_name = node.name
            if norm['type'] == 'P':
                node.violation = action_name in norm['actions']
            elif norm['type'] == 'O':
                node.violation = action_name not in norm['actions']

        elif node_type in ['OR', 'AND', 'SEQ']:
            for child in node.children:
                check_violation(child, norm)
            node.violation = all(child.violation for child in node.children) if node_type == 'OR' else any(child.violation for child in node.children)

        else:
            for child in getattr(node, 'children', []):
                check_violation(child, norm)

    check_violation(tree, norm)
    return tree

# === Trace filtering ===
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



print("\n=================== DEBUGGING TEST SUITE ===================")

with open("coffee.json") as f:
    json_tree = json.load(f)

test_counter = 1

# Helper function for debugging tests
def run_debug(tree, norm, goal, beliefs, preferences, expected, description):
    print("DEBUG: ", description)
    result = decision_making(tree, norm, goal, beliefs, preferences)
    print("Result:   ", result)
    print("Expected: ", expected)
    print("Pass:     ", result == expected)
    print("--------------------------")

# Example 1: Simple ACT node tree.
# Tree: a single action node that requires "x" to be true, and produces "y".
tree1 = {
    "name": "getCoffee",
    "type": "ACT",
    "pre": ["x"],
    "post": ["y"],
    "costs": [1.0, 2.0, 3.0]
}
run_debug(
    tree=tree1,
    norm={},
    goal=["y"],
    beliefs=["x"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=["getCoffee"],
    description="Example 1: Single ACT node tree."
)

# Example 2: Simple OR tree with two alternatives.
# Only the first branch is valid because its precondition ("a") is satisfied.
tree2 = {
    "name": "getCoffee",
    "type": "OR",
    "children": [
        {
            "name": "getCoffeeA",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [1.0, 1.0, 1.0]
        },
        {
            "name": "getCoffeeB",
            "type": "ACT",
            "pre": ["b"],
            "post": ["y"],
            "costs": [0.5, 2.0, 2.0]
        }
    ]
}
run_debug(
    tree=tree2,
    norm={},
    goal=["y"],
    beliefs=["a"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=["getCoffee", "getCoffeeA"],
    description="Example 2: OR tree with two alternatives; only branch A is valid."
)

# Example 3: Simple SEQ tree with two steps.
# Step1 produces a postcondition that enables step2.
tree3 = {
    "name": "getCoffee",
    "type": "SEQ",
    "children": [
        {
            "name": "step1",
            "type": "ACT",
            "pre": ["p"],
            "post": ["q"],
            "costs": [2.0, 0.0, 1.0]
        },
        {
            "name": "step2",
            "type": "ACT",
            "pre": ["q"],
            "post": ["y"],
            "costs": [1.0, 0.0, 2.0]
        }
    ]
}
run_debug(
    tree=tree3,
    norm={},
    goal=["y"],
    beliefs=["p"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=["getCoffee", "step1", "step2"],
    description="Example 3: SEQ tree with sequential dependency."
)

# Example 4: Norm violation.
# A SEQ tree where the second step is prohibited by a norm.
tree4 = {
    "name": "getCoffee",
    "type": "SEQ",
    "children": [
        {
            "name": "step1",
            "type": "ACT",
            "pre": ["p"],
            "post": ["q"],
            "costs": [1.0, 0.0, 1.0]
        },
        {
            "name": "step2",
            "type": "ACT",
            "pre": ["q"],
            "post": ["y"],
            "costs": [2.0, 1.0, 3.0]
        }
    ]
}
norm4 = {"type": "P", "actions": ["step2"]}
run_debug(
    tree=tree4,
    norm=norm4,
    goal=["y"],
    beliefs=["p"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=[],  # Expect no valid trace because step2 is prohibited.
    description="Example 4: SEQ tree with norm violation (step2 prohibited)."
)

# Example 5: Cost selection in an OR tree with two valid branches.
# Both branches' preconditions are met; the best branch is selected based on cost.
tree5 = {
    "name": "getCoffee",
    "type": "OR",
    "children": [
        {
            "name": "branchA",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [3.0, 2.0, 1.0]  # quality=3, price=2, time=1
        },
        {
            "name": "branchB",
            "type": "ACT",
            "pre": ["b"],
            "post": ["y"],
            "costs": [1.0, 5.0, 5.0]  # quality=1, price=5, time=5
        }
    ]
}
# Both branches are valid when both 'a' and 'b' are in beliefs.
# With preference order [2, 0, 1] (time, then quality, then price):
# branchA gives (time, quality, price) = (1, 3, 2)
# branchB gives (time, quality, price) = (5, 1, 5)
# Lexicographically, (1,3,2) < (5,1,5), so branchA is selected.
run_debug(
    tree=tree5,
    norm={},
    goal=["y"],
    beliefs=["a", "b"],
    preferences=[["quality", "price", "time"], [2, 0, 1]],
    expected=["getCoffee", "branchA"],
    description="Example 5: OR tree cost selection with two valid branches and preference on time."
)

# Helper function for debugging tests (if not already defined)
def run_debug(tree, norm, goal, beliefs, preferences, expected, description):
    print("DEBUG: ", description)
    result = decision_making(tree, norm, goal, beliefs, preferences)
    print("Result:   ", result)
    print("Expected: ", expected)
    print("Pass:     ", result == expected)
    print("--------------------------")

### Example 6: Missing 'pre' Attribute on One Branch
# In this tree, one branch (branchA) explicitly requires "a", while branchB has no pre condition.
# In the absence of "a" in beliefs, branchA should be ruled out and branchB should be selected.
tree6 = {
    "name": "getCoffee",
    "type": "OR",
    "children": [
        {
            "name": "branchA",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [2.0, 2.0, 2.0]
        },
        {
            "name": "branchB",
            "type": "ACT",
            # Missing pre attribute → should be treated as always satisfied.
            "post": ["y"],
            "costs": [1.0, 2.0, 3.0]
        }
    ]
}
# Beliefs do NOT include "a" so branchA is not valid.
run_debug(
    tree=tree6,
    norm={},
    goal=["y"],
    beliefs=[],  
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=["getCoffee", "branchB"],
    description="Example 6: Testing missing 'pre' attribute (branchB should be chosen if its pre is missing)."
)

### Example 7: Missing 'post' Attribute Causing Sequence Failure
# In this SEQ tree, step1 lacks a 'post' attribute so its effects are not propagated.
# Thus, step2’s pre condition ("q") is never satisfied even if step1 is executed.
tree7 = {
    "name": "getCoffee",
    "type": "SEQ",
    "children": [
        {
            "name": "step1",
            "type": "ACT",
            "pre": ["p"],
            # Missing 'post' attribute.
            "costs": [1.0, 0.0, 1.0]
        },
        {
            "name": "step2",
            "type": "ACT",
            "pre": ["q"],
            "post": ["y"],
            "costs": [1.0, 0.0, 2.0]
        }
    ]
}
# Beliefs: Only "p" is provided so step1 can run but step2 will fail.
run_debug(
    tree=tree7,
    norm={},
    goal=["y"],
    beliefs=["p"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=[],  # No valid trace because "q" is never achieved.
    description="Example 7: Testing missing 'post' attribute (expected no valid trace)."
)

### Example 8: Obligation Norm Filtering Out Lower-Cost Branch
# Here, two branches in an OR node are both valid (both have pre "a"), but branchB has lower cost.
# However, a norm of type "O" (obligation) permits only branchA.
tree8 = {
    "name": "getCoffee",
    "type": "OR",
    "children": [
        {
            "name": "branchA",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [5.0, 5.0, 5.0]
        },
        {
            "name": "branchB",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [1.0, 1.0, 1.0]
        }
    ]
}
norm8 = {"type": "O", "actions": ["branchA"]}  # Only branchA is allowed.
# Beliefs include "a", so without the norm branchB would win, but the obligation forces branchA.
run_debug(
    tree=tree8,
    norm=norm8,
    goal=["y"],
    beliefs=["a"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=["getCoffee", "branchA"],
    description="Example 8: Testing obligation norm (only branchA allowed despite higher cost)."
)

### Example 9: Cost List of Incorrect Length
# In this tree, branchA’s cost list is missing one element.
# This test should expose how the cost aggregation handles (or fails on) incomplete cost lists.
tree9 = {
    "name": "getCoffee",
    "type": "OR",
    "children": [
        {
            "name": "branchA",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [1.0, 1.0, 5.0]  # Incorrect length: should be 3 values.
        },
        {
            "name": "branchB",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [2.0, 2.0, 2.0]
        }
    ]
}
# Beliefs include "a". The behavior here is undefined: the code may error or compute an incomplete sum.
# For debugging, we expect an error or a wrong trace.
run_debug(
    tree=tree9,
    norm={},
    goal=["y"],
    beliefs=["a"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    expected=[],  # We expect this test to fail or produce an incorrect trace.
    description="Example 9: Testing a branch with an incomplete cost list (should highlight a cost-format error)."
)

### Example 10: Duplicate Node Names Causing Ambiguity in Cost Lookup
# In this OR tree, both branches have the same name "duplicate".
# When building the nodes_by_name dictionary, only one entry is retained,
# which can lead to ambiguous or unintended cost selection.
tree10 = {
    "name": "getCoffee",
    "type": "OR",
    "children": [
        {
            "name": "duplicate",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [1.0, 2.0, 3.0]
        },
        {
            "name": "duplicate",
            "type": "ACT",
            "pre": ["a"],
            "post": ["y"],
            "costs": [3.0, 2.0, 1.0]
        }
    ]
}
# Beliefs include "a". A warning about duplicate node names should be printed.
# Since the dictionary retains one value, the result may be ambiguous.
# For debugging, we expect a warning and one of the branches selected.
run_debug(
    tree=tree10,
    norm={},
    goal=["y"],
    beliefs=["a"],
    preferences=[["quality", "price", "time"], [0, 1, 2]],
    # We cannot precisely control which duplicate is retained, but we expect the trace to be:
    expected=["getCoffee", "duplicate"],
    description="Example 10: Testing duplicate node names (should warn and select one branch, though ambiguity remains)."
)

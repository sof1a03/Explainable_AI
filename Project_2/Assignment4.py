from anytree import AnyNode, PreOrderIter
from itertools import product

def build_tree(tree, parent=None):
    data = {
        key: (
            [int(v) if isinstance(v, (int, float)) else v for v in value]
            if isinstance(value, list) else value
        )
        for key, value in tree.items() if key != "children"
    }
    node = AnyNode(parent=parent, **data)
    for child in tree.get("children", []):
        build_tree(child, parent=node)
    return node

def check_violation(node, norm):
    if node.type == 'ACT':
        if norm['type'] == 'O':
            node.violation = node.name not in norm['actions']
        elif norm['type'] == 'P':
            node.violation = node.name in norm['actions']
        else:
            node.violation = False
    elif node.type in ['OR', 'AND', 'SEQ']:
        for c in node.children:
            check_violation(c, norm)
        if node.type == 'OR':
            node.violation = all(child.violation for child in node.children)
        else:
            node.violation = any(child.violation for child in node.children)

def annotate_tree_with_norm(root, norm):
    check_violation(root, norm)
    return root

def expand_traces(node):
    if node.type == 'ACT':
        return [[node.name]]
    elif node.type == 'OR':
        out = []
        for c in node.children:
            for sub in expand_traces(c):
                out.append([node.name] + sub)
        return out
    elif node.type in ['AND', 'SEQ']:
        parts = [expand_traces(ch) for ch in node.children]
        combos = product(*parts)
        ordered = sorted(node.children, key=lambda x: getattr(x, 'sequence', 0))
        res = []
        for combo in combos:
            merged = []
            mapping = {}
            for ch, piece in zip(node.children, combo):
                mapping[ch] = piece
            for ch in ordered:
                merged += mapping[ch]
            res.append([node.name] + merged)
        return res

def execution_traces(root):
    return expand_traces(root)

def violates_norm(trace, root):
    lookup = {n.name: n for n in PreOrderIter(root)}
    for act in trace:
        if act in lookup and getattr(lookup[act], 'violation', False):
            return True
    return False

def check_preconditions_and_goal(trace, root, beliefs, goal):
    lookup = {n.name: n for n in PreOrderIter(root)}
    current = set(beliefs)
    for step in trace:
        node = lookup.get(step)
        if not node:
            return False
        for p in getattr(node, 'pre', []):
            if p not in current:
                return False
        for p in getattr(node, 'post', []):
            current.add(p)
    return all(g in current for g in goal)

def get_all_valid_traces(root, beliefs, goal):
    all_t = execution_traces(root)
    valid = []
    for t in all_t:
        if not violates_norm(t, root) and check_preconditions_and_goal(t, root, beliefs, goal):
            valid.append(t)
    return valid

def decision_making(json_tree, norm, goal, beliefs, preferences):
    root = build_tree(json_tree)
    annotate_tree_with_norm(root, norm)
    valid = get_all_valid_traces(root, beliefs, goal)
    if not valid:
        return []
    lookup = {n.name: n for n in PreOrderIter(root)}
    def cost_vector(trace):
        length = 0
        for step in trace:
            node = lookup.get(step)
            if node and hasattr(node, 'costs'):
                length = max(length, len(node.costs))
        out = [0] * length
        for step in trace:
            node = lookup.get(step)
            if node and hasattr(node, 'costs'):
                for i, c in enumerate(node.costs):
                    out[i] += c
        return out
    order = preferences[1]
    def compare(a, b):
        for idx in order:
            if a[idx] < b[idx]:
                return -1
            elif a[idx] > b[idx]:
                return 1
        return 0
    costlist = [cost_vector(t) for t in valid]
    best = 0
    for i in range(1, len(valid)):
        if compare(costlist[i], costlist[best]) < 0:
            best = i
    return valid[best]

def find_first_violating_action(node):
    for d in PreOrderIter(node):
        if d.type == 'ACT' and getattr(d, 'violation', False):
            return d.name
    return None

def unsatisfied_pre(node, beliefs):
    pre = node.__dict__.get('pre', [])
    return [p for p in pre if p not in beliefs]

def option_string(chosen_child):
    chosen_traces = expand_traces(chosen_child)
    if chosen_traces and len(chosen_traces[0]) > 1:
        return "O(" + ", ".join(chosen_traces[0][1:]) + ")"
    else:
        return "O()"

def explain_or_node(or_node, selected_trace, beliefs):
    explanation = []
    chosen_child = None
    for c in or_node.children:
        subtree_actions = [n.name for n in PreOrderIter(c)]
        if any(act in selected_trace for act in subtree_actions):
            chosen_child = c
            break
    if not chosen_child:
        return explanation
    chosen_pre = getattr(chosen_child, 'pre', [])
    explanation.append(["C", chosen_child.name, list(chosen_pre) if chosen_pre else []])
    opt_str = option_string(chosen_child)
    for sibling in or_node.children:
        if sibling == chosen_child:
            continue
        explanation.append(["N", sibling.name, opt_str])
    return explanation

def or_descendants_to_explain(node, selected_trace, beliefs):
    lines = []
    if node.type == 'OR':
        lines += explain_or_node(node, selected_trace, beliefs)
    if node.type in ['OR', 'AND', 'SEQ']:
        for c in node.children:
            lines += or_descendants_to_explain(c, selected_trace, beliefs)
    return lines

def explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain):
    selected_trace = decision_making(json_tree, norm, goal, beliefs, preferences)
    if action_to_explain not in selected_trace:
        return selected_trace, []
    root = build_tree(json_tree)
    annotate_tree_with_norm(root, norm)
    or_factors = []
    for node in PreOrderIter(root):
        if node.type == 'OR':
            descendants = [n.name for n in PreOrderIter(node)]
            if any(a in selected_trace for a in descendants):
                or_factors.extend(explain_or_node(node, selected_trace, beliefs))
    lookup = {n.name: n for n in PreOrderIter(root)}
    p_factors = []
    partial = []
    for step in selected_trace:
        partial.append(step)
        if step == action_to_explain:
            break
    for step in partial:
        node = lookup.get(step)
        if node and node.type == 'ACT' and hasattr(node, 'pre') and node.pre:
            p_factors.append(["P", node.name, list(node.pre)])
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
selected_trace, output = explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain)
## SO FAR THE BEST PERFORMING MODEL BUT STILL ISNT CONSITENT ENOUGH
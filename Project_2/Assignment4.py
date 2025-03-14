from anytree import AnyNode, PreOrderIter
from itertools import product

def build_tree(tree, parent=None):
    data = {
        key: (
            [int(v) if isinstance(v, (int, float)) else v for v in value]
            if isinstance(value, list)
            else int(value) if isinstance(value, (int, float))
            else value
        )
        for key, value in tree.items()
        if key != "children"
    }
    node = AnyNode(parent=parent, **data)
    for child in tree.get("children", []):
        build_tree(child, parent=node)
    return node

def check_violation(node, norm):
    if node.type == 'ACT':
        if norm['type'] == 'O':
            # Norm type O => Must be in norm['actions'] or it's a violation
            node.violation = node.name not in norm['actions']
        elif norm['type'] == 'P':
            # Norm type P => Must NOT be in norm['actions']
            node.violation = node.name in norm['actions']
        else:
            node.violation = False
    elif node.type in ['OR','AND','SEQ']:
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
    elif node.type in ['AND','SEQ']:
        blocks = [expand_traces(ch) for ch in node.children]
        combos = product(*blocks)
        order = sorted(node.children, key=lambda x: getattr(x,'sequence',0))
        res = []
        for combo in combos:
            merged = []
            mapping = {}
            for ch, piece in zip(node.children, combo):
                mapping[ch] = piece
            for ch in order:
                merged += mapping[ch]
            res.append([node.name] + merged)
        return res

def execution_traces(root):
    return expand_traces(root)

def violates_norm(trace, root):
    lookup = {n.name:n for n in PreOrderIter(root)}
    for act in trace:
        if act in lookup and getattr(lookup[act], 'violation', False):
            return True
    return False

def check_preconditions_and_goal(trace, root, beliefs, goal):
    lookup = {n.name:n for n in PreOrderIter(root)}
    current = set(beliefs)
    for step in trace:
        node = lookup.get(step)
        if not node:
            return False
        if hasattr(node, 'pre'):
            for p in node.pre:
                if p not in current:
                    return False
        if hasattr(node, 'post'):
            for p in node.post:
                current.add(p)
    return all(g in current for g in goal)

def get_all_valid_traces(root, beliefs, goal):
    all_t = execution_traces(root)
    valid = []
    for t in all_t:
        if not violates_norm(t, root):
            if check_preconditions_and_goal(t, root, beliefs, goal):
                valid.append(t)
    return valid

def decision_making(json_tree, norm, goal, beliefs, preferences):
    root = build_tree(json_tree)
    annotate_tree_with_norm(root, norm)
    valid = get_all_valid_traces(root, beliefs, goal)
    if not valid:
        return []
    lookup = {n.name:n for n in PreOrderIter(root)}

    def cost_vector(trace):
        length = 0
        for step in trace:
            node = lookup.get(step)
            if node and hasattr(node, 'costs'):
                length = max(length, len(node.costs))
        out = [0]*length
        for step in trace:
            node = lookup.get(step)
            if node and hasattr(node, 'costs'):
                for i,c in enumerate(node.costs):
                    out[i]+=c
        return out

    order = preferences[1]
    def compare(a, b):
        for idx in order:
            if a[idx]<b[idx]:
                return -1
            elif a[idx]>b[idx]:
                return 1
        return 0

    costs = [cost_vector(t) for t in valid]
    best_idx = 0
    for i in range(1,len(valid)):
        if compare(costs[i], costs[best_idx])<0:
            best_idx=i
    return valid[best_idx]

def find_first_violating_action(node):
    for d in PreOrderIter(node):
        if d.type=='ACT' and getattr(d,'violation',False):
            return d.name
    return None

def is_subtree_feasible(node, beliefs):
    p = getattr(node, 'pre', [])
    if not p:
        return True
    for cond in p:
        if cond not in beliefs:
            return False
    return True

def explain_or_node(node, selected_trace, beliefs, root, preferences):
    lines = []
    chosen_child = None
    for c in node.children:
        desc = [d.name for d in PreOrderIter(c)]
        if any(x in selected_trace for x in desc):
            chosen_child = c
            break
    child_pre = getattr(chosen_child, 'pre', []) if chosen_child else []
    lines.append(["C", chosen_child.name, list(child_pre)])
    for s in node.children:
        if s == chosen_child:
            continue
        viol_act = find_first_violating_action(s)
        if viol_act:  
            lines.append(["N", s.name, f"P({viol_act})"])
        else:
            if is_subtree_feasible(s, beliefs):
                p = getattr(s,'pre',[])
                if not p: 
                    p = []
                lines.append(["F", s.name, list(p)])
            else:
                p = getattr(s,'pre',[])
                if not p:
                    p = []
                lines.append(["V", s.name, list(p)])
    lines += or_descendants_to_explain(chosen_child, selected_trace, beliefs, root, preferences)
    return lines

def or_descendants_to_explain(node, selected_trace, beliefs, root, preferences):
    lines = []
    if node is None:
        return lines
    if node.type=='OR':
        lines += explain_or_node(node, selected_trace, beliefs, root, preferences)
    elif node.type in ['AND','SEQ']:
        for c in node.children:
            lines += or_descendants_to_explain(c, selected_trace, beliefs, root, preferences)
    return lines

def explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain):
    selected_trace = decision_making(json_tree, norm, goal, beliefs, preferences)
    if action_to_explain not in selected_trace:
        return selected_trace, []
    root = build_tree(json_tree)
    annotate_tree_with_norm(root, norm)

    explanation = or_descendants_to_explain(root, selected_trace, beliefs, root, preferences)

    lookup = {n.name:n for n in PreOrderIter(root)}
    partial = []
    for step in selected_trace:
        partial.append(step)
        if step==action_to_explain:
            break
    for act in partial:
        node = lookup.get(act)
        if node and node.type=='ACT' and hasattr(node,'pre') and node.pre:
            explanation.append(["P", node.name, list(node.pre)])

    an = lookup[action_to_explain]
    par = an.parent
    while par:
        if par.type in ['OR','AND','SEQ']:
            explanation.append(["D", par.name])
        par = par.parent

    explanation.append(["U", preferences])
    return selected_trace, explanation



selected_trace, output = explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain)

from anytree import AnyNode, RenderTree
import json

with open("coffee.json", "r") as file:
    json_tree = json.load(file)

norm = {'type': 'P', 'actions': ['gotoAnnOffice']}

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
    

def goaltree_violation(tree, norm):
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

root_node = build_tree(json_tree)
norm={'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
annotated_tree = goaltree_violation(root_node, norm)
output=RenderTree(annotated_tree)
print(output)

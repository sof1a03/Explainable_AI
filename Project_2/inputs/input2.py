"""
Input 2 - Explaining an action - Only possible action

This file contains the input variables for the generation of the second natural language explanation.
"""

name_json_tree_file = "coffee.json"
norm = {}
beliefs = ["staffCardAvailable", "ownCard"]
goal = ["haveCoffee"]
preferences = [["quality", "price", "time"], [0, 1, 2]]
action_to_explain = "getCoffeeKitchen"
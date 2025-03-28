"""
Input 5 - Explaining an action - Reasons include all aspects

This file contains the input variables for the generation of the fifth natural language explanation.
"""

name_json_tree_file = "coffee.json"
norm = {"type": "P", "actions": ["payShop"]}
beliefs = ["staffCardAvailable", "ownCard", "colleagueAvailable", "haveMoney"]
goal = ["haveCoffee"]
preferences = [["quality", "price", "time"], [1, 2, 0]]
action_to_explain = "gotoKitchen"
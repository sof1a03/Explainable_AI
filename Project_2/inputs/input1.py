"""
Input 1 - Explaining an action - Action never executed

This file contains the input variables for the generation of the first natural language explanation
"""

name_json_tree_file = "coffee.json"
norm = {"type": "P", "actions": ["payShop"]}
beliefs = ["staffCardAvailable", "ownCard", "colleagueAvailable", "haveMoney", "AnnInOffice"]
goal = ["haveCoffee"]
preferences = [["quality", "price", "time"], [1, 2, 0]]
action_to_explain = "payShop"
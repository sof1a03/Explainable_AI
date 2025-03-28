"""
Input 4 - Explaining an action - Reasons include also norms

This file contains the input variables for the generation of the fourth natural language explanation.
"""

name_json_tree_file = "coffee.json"
norm = {"type": "P", "actions": ["gotoAnnOffice"]}
beliefs = ["staffCardAvailable", "ownCard", "colleagueAvailable", "haveMoney", "AnnInOffice"]
goal = ["haveCoffee"]
preferences = [["quality", "price", "time"], [0, 1, 2]]
action_to_explain = "payShop"
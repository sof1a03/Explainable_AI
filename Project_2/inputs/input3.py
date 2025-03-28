"""
Input 3 - Explaining an action - Reasons include user preferences

This file contains the input variables for the generation of the third natural language explanation.
"""

name_json_tree_file = "coffee.json"
norm = {}
beliefs = ["haveMoney", "AnnInOffice"]
goal = ["haveCoffee"]
preferences = [["quality", "price", "time"], [0, 1, 2]]
action_to_explain = "getCoffeeShop"
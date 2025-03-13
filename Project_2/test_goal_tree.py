import unittest
from project2 import execution_traces, build_tree
from assignment3 import decision_making
import json


class MyTestCase(unittest.TestCase):
    with open("coffee.json", "r") as file:
        json_tree = json.load(file)

    def test_trace_getCoffeeKitchen(self):
        trace_algorithm = execution_traces(build_tree(self.json_tree), "getCoffeeKitchen")
        sample_trace = [["getCoffeeKitchen"]]
        self.assertEqual(trace_algorithm, sample_trace)

    def test_trace_getCoffee(self):
        trace_algorithm = execution_traces(build_tree(self.json_tree), "getCoffee")
        sample_trace = [
            ["getCoffee", "getKitchenCoffee", "getStaffCard", "getOwnCard", "gotoKitchen", "getCoffeeKitchen"],
            ["getCoffee", "getKitchenCoffee", "getStaffCard", "getOthersCard", "gotoKitchen", "getCoffeeKitchen"],
            ["getCoffee", "getAnnOfficeCoffee", "gotoAnnOffice", "getPod", "getCoffeeAnnOffice"],
            ["getCoffee", "getShopCoffee", "gotoShop", "payShop", "getCoffeeShop"]]

        self.assertEqual(trace_algorithm, sample_trace)

    def test_decision_1(self):
        norm = {'type': 'P', 'actions': ['gotoKitchen']}
        goal = ['haveCoffee']
        beliefs = ['haveMoney']
        preferences = [['quality', 'price', 'time'], [2, 0, 1]]

        sol = ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']
        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)
        print(output)
        self.assertEqual(sol, output)

    def test_decision_2(self):
        norm = {'type': 'P', 'actions': ['payShop']}
        goal = ['haveCoffee']
        beliefs = ['staffCardAvailable', 'ownCard']
        preferences = [['quality', 'price', 'time'], [1, 2, 0]]
        sol = ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen']

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)

        self.assertEqual(sol, output)

    def test_decision_3(self):
        norm = {'type': 'P', 'actions': ['payShop']}
        goal = ['haveCoffee']
        beliefs = ['haveMoney']
        preferences = [['quality', 'price', 'time'], [2, 0, 1]]
        sol = []

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)

        self.assertEqual(sol, output)

    def test_decision_4empty(self):
        norm = {}
        goal = ['haveCoffee']
        beliefs = ['staffCardAvailable', 'ownCard']
        preferences = [['quality', 'price', 'time'], [1, 2, 0]]

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)

    def test_decision_5(self):
        norm = {'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
        goal = ['haveCoffee']
        beliefs = ['staffCardAvailable', 'ownCard']
        preferences = [['quality', 'price', 'time'], [2, 0, 1]]
        sol = []

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)
        self.assertEqual(sol, output)

    def test_decision_6(self):
        norm = {'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
        goal = ['haveCoffee']
        beliefs = ['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
        preferences = [['quality', 'price', 'time'], [2, 0, 1]]
        sol = ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)
        self.assertEqual(sol, output)

    def test_decision_7(self):
        norm = {'type': 'P', 'actions': ['payShop']}
        goal = ['haveCoffee']
        beliefs = ['haveMoney']
        preferences = [['quality', 'price', 'time'], [1, 2, 0]]
        sol = []

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)

        self.assertEqual(sol, output)

    def test_decision_9(self):
        norm = {}
        goal = ['haveCoffee']
        beliefs = ['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
        preferences = [['quality', 'price', 'time'], [1, 2, 0]]
        sol = ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen']

        output = decision_making(self.json_tree, norm, goal, beliefs, preferences)

        self.assertEqual(sol, output)



if __name__ == '__main__':
    unittest.main()

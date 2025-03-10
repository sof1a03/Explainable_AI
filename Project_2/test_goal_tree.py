import unittest
from project2 import execution_traces, import_data_from_json


class MyTestCase(unittest.TestCase):
    coffee_tree = "coffee.json"

    def test_trace_getCoffeeKitchen(self):
        trace_algorithm = execution_traces(self.coffee_tree, "getCoffeeKitchen")
        sample_trace = [["getCoffeeKitchen"]]
        self.assertEqual(trace_algorithm, sample_trace)

    def test_trace_getCoffee(self):
        trace_algorithm = execution_traces(self.coffee_tree, "getCoffee")
        sample_trace = [["getCoffee", "getKitchenCoffee", "getStaffCard", "getOwnCard", "gotoKitchen", "getCoffeeKitchen"],
                        ["getCoffee", "getKitchenCoffee", "getStaffCard", "getOthersCard", "gotoKitchen", "getCoffeeKitchen"],
                        ["getCoffee", "getAnnOfficeCoffee", "gotoAnnOffice", "getPod", "getCoffeeAnnOffice"],
                        ["getCoffee", "getShopCoffee", "gotoShop", "payShop", "getCoffeeShop"]]

        self.assertEqual(trace_algorithm, sample_trace)


if __name__ == '__main__':
    unittest.main()

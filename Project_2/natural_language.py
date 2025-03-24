from ass4 import *

variable_to_english = {
    "haveCard": "it has a staff card",
    "ownCard": "it has their own card",
    "colleagueAvailable": "a colleague is available",
    "staffCardAvailable": "a staff card is available",
    "atKitchen": "it is at the kitchen",
    "atShop": "it is at the shop",
    "paidShop": "it has paid at the shop",
    "haveMoney": "it has money",
    "haveCoffee": "it ends up having coffee",
    "AnnInOffice": "Ann is in the office",
    "atAnnOffice": "it is at Ann's office",
    "havePod": "it has a coffee pod"
}
action_to_english = {
    "getAnnOfficeCoffee": "get a coffee from Ann's office",
    "gotoAnnOffice": "go to Ann's office",
    "getPod": "pick up a coffee pod",
    "getCoffeeAnnOffice": "make coffee in Ann's office",
    "getKitchenCoffee": "get a coffee from the kitchen",
    "getStaffCard": "get a staff card",
    "getOwnCard": "go get their own card",
    "getOthersCard": "borrow a card from a colleague",
    "gotoKitchen": "go to the kitchen",
    "getCoffeeKitchen": "make coffee in the kitchen",
    "getShopCoffee": "pick up the coffee from the shop",
    "gotoShop": "go to the shop",
    "payShop": "pay at the shop",
    "getCoffeeShop": "pick up the coffee at the shop",
    "getCoffee": "get a coffee"
}

def readable_condition(conds):
    return ", ".join(variable_to_english.get(c, c) for c in conds)


def readable_action(name):
    return action_to_english.get(name, name.replace("_", " "))


def generate_natural_language(explanation_factors):
    sentences = {
        "C": [],
        "N": [],
        "F": [],
        "P": [],
        "L": [],
        "D": [],
        "V": [],
        "U": []
    }

    used_conditions = set()
    used_plans = set()
    used_choices = set()
    ordered_prefs = None
    main_goal = None
    chosen_option = None
    precondition_in_C = []
    final_summary = []

    norm_violations = []
    norm_type = None
    norm_raw = None
    precondition_factors = []

    for factor in explanation_factors[::-1]:
        typ = factor[0]

        if typ == "D":
            if factor[1] == "getCoffee":
                main_goal = "get a coffee"
            elif not chosen_option:
                chosen_option = readable_action(factor[1])

        elif typ == "C":
            chosen_option = readable_action(factor[1])
            precondition_in_C = readable_condition(factor[2])

        elif typ == "U":
            pref_names, pref_order = factor[1]
            ordered_prefs = [pref_names[i] for i in pref_order]

        elif typ == "V":
            chosen = readable_action(factor[1])
            alt = readable_action(factor[4])
            reason = "because it had a lower overall cost"
            if ordered_prefs:
                reason += f", especially with {ordered_prefs[0]} as the top priority"
            reason += "."
            sentences["V"].append(f"The agent preferred to {chosen} over {alt} {reason}")

        elif typ == "N":
            norm_violations.append(readable_action(factor[1]))
            norm_raw = factor[2]
            norm_type = factor[2][0]  # 'P' or 'O'

        elif typ == "F":
            conds = readable_condition(factor[2])
            action = readable_action(factor[1])
            sentences["F"].append(f"The agent could not {action} because {conds} were not satisfied.")

        elif typ == "P":
            conds = readable_condition(factor[2])
            line = f"Before being able to {readable_action(factor[1])}, it was necessary to check that {conds}."
            if line not in precondition_factors:
                precondition_factors.append(line)

        elif typ == "L":
            sentences["L"].append(f"To have the coffee then the agent needed to {readable_action(factor[1])} and {readable_action(factor[3])}.")

    # Opening sentence
    if main_goal and chosen_option:
        opening = f"The agent wants to {main_goal} and it decided to {chosen_option}."
        final_summary.append(opening)

    # Condition for C
    if precondition_in_C:
        final_summary.append(f"This decision was made because {precondition_in_C}.")

    # All other P factors (grouped after the initial decision)
    final_summary.extend(precondition_factors)

    # Preferences
    if ordered_prefs:
        main = ordered_prefs[0]
        rest = " and then ".join(ordered_prefs[1:])
        final_summary.append(f"The agent prioritizes {main} above all, followed by {rest}.")

    # Norm violations — now considers both P and O
    if norm_violations:
        joined = " or ".join(norm_violations)
        if norm_type == "P":
            final_summary.append(f"Moreover, choosing to {joined} would have violated a prohibition, so it was excluded.")
        elif norm_type == "O":
            try:
                # extract readable version of the last action in the obligation
                obligation_parts = norm_raw[norm_raw.find('(')+1 : norm_raw.find(')')].split(',')
                final_action = obligation_parts[-1].strip()
                readable_final_action = readable_action(final_action)
                final_summary.append(f"Moreover, choosing to {joined} was not allowed because it does not fulfill the obligation to {readable_final_action}.")
            except:
                final_summary.append(f"Moreover, choosing to {joined} was not allowed because it does not fulfill an obligation.")

    # Add other explanation types
    for key in ["V", "F", "L"]:
        final_summary.extend(sentences[key])

    return " ".join(final_summary)




#example 1
# norm={'type': 'P', 'actions': ['gotoKitchen']}
# goal=['haveCoffee']
# beliefs=['staffCardAvailable', 'ownCard', 'colleagueAvailable', 'haveMoney', 'AnnInOffice']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain=	"gotoAnnOffice"
# true_result = [['C', 'getAnnOfficeCoffee', ['AnnInOffice']], ['N', 'getKitchenCoffee', 'P(gotoKitchen)'], ['V', 'getAnnOfficeCoffee', [2, 0, 6], '>', 'getShopCoffee', [0, 3, 9]], ['P', 'gotoAnnOffice', ['AnnInOffice']], ['L', 'gotoAnnOffice', '->', 'getCoffeeAnnOffice'], ['D', 'getAnnOfficeCoffee'], ['D', 'getCoffee'], ['U', [['quality', 'price', 'time'], [2, 0, 1]]]]

#example 2

# norm={'type': 'P', 'actions': ['gotoKitchen']}
# goal=['haveCoffee']
# beliefs=['haveMoney']
# preferences=[['quality', 'price', 'time'], [1, 2, 0]]
# action_to_explain="gotoShop"

#example 3

# norm={'type': 'O', 'actions': ['gotoShop', 'payShop', 'getCoffeeShop']}
# goal=['haveCoffee']
# beliefs=['haveMoney']
# preferences=[['quality', 'price', 'time'], [2, 0, 1]]
# action_to_explain="gotoShop"

#example 4

norm =	{'type': 'P', 'actions': ['gotoAnnOffice']}
goal =	['haveCoffee']
beliefs=	['staffCardAvailable', 'ownCard']
preferences	=[['quality', 'price', 'time'], [2, 0, 1]]
action_to_explain	= "getOwnCard"

selected_trace, output = explain_action(json_tree, norm, goal, beliefs, preferences, action_to_explain)
print(output)
print(generate_natural_language(output))

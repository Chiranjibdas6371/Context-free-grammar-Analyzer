from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

grammar = {}
first = {}
follow = {}

# ---------------- FIRST ---------------- #

def find_first(symbol):

    if symbol not in grammar:
        return {symbol}

    result = set()

    for production in grammar[symbol]:

        if production == "ε":
            result.add("ε")

        else:

            for char in production:

                temp = find_first(char)

                result.update(temp - {"ε"})

                if "ε" not in temp:
                    break

            else:
                result.add("ε")

    return result


# ---------------- FOLLOW ---------------- #

def find_follow(start):

    global follow

    follow = {}

    for nt in grammar:
        follow[nt] = set()

    follow[start].add("$")

    changed = True

    while changed:

        changed = False

        for head in grammar:

            for prod in grammar[head]:

                for i, symbol in enumerate(prod):

                    if symbol in grammar:

                        next_symbols = prod[i + 1:]

                        if next_symbols:

                            first_next = set()

                            for s in next_symbols:

                                f = find_first(s)

                                first_next.update(f - {"ε"})

                                if "ε" not in f:
                                    break

                            else:
                                first_next.add("ε")

                            before = len(follow[symbol])

                            follow[symbol].update(first_next - {"ε"})

                            if "ε" in first_next:
                                follow[symbol].update(follow[head])

                            if len(follow[symbol]) != before:
                                changed = True

                        else:

                            before = len(follow[symbol])

                            follow[symbol].update(follow[head])

                            if len(follow[symbol]) != before:
                                changed = True


# ---------------- LEFT RECURSION ---------------- #

def detect_left_recursion():

    recursive = []

    for head in grammar:

        for prod in grammar[head]:

            if prod and prod[0] == head:
                recursive.append(head)

    return recursive


# ---------------- LEFT FACTORING ---------------- #

def detect_left_factoring():

    factoring = []

    for head in grammar:

        prefixes = {}

        for prod in grammar[head]:

            if not prod:
                continue

            prefix = prod[0]

            if prefix in prefixes:
                factoring.append(head)
            else:
                prefixes[prefix] = True

    return factoring


# ---------------- PARSE TABLE ---------------- #

def create_parse_table():

    table = {}

    for nt in grammar:
        table[nt] = {}

    for head in grammar:

        for prod in grammar[head]:

            first_set = set()

            if prod == "ε":
                first_set.add("ε")

            else:

                for char in prod:

                    f = find_first(char)

                    first_set.update(f - {"ε"})

                    if "ε" not in f:
                        break

                else:
                    first_set.add("ε")

            for terminal in first_set:

                if terminal != "ε":
                    table[head][terminal] = prod

            if "ε" in first_set:

                for f in follow.get(head, []):
                    table[head][f] = prod

    return table


# ---------------- STRING VALIDATION ---------------- #

def validate_string_steps(input_string, table, start):

    stack = ["$", start]
    input_string += "$"

    pointer = 0

    steps = []

    while stack:

        stack_display = " ".join(stack[::-1])
        input_display = input_string[pointer:]

        top = stack.pop()
        current = input_string[pointer]

        if top == current:

            steps.append({
                "stack": stack_display,
                "input": input_display,
                "action": "match " + current
            })

            pointer += 1

        elif top in grammar:

            if current in table[top]:

                production = table[top][current]

                steps.append({
                    "stack": stack_display,
                    "input": input_display,
                    "action": f"{top} → {production}"
                })

                if production != "ε":

                    for symbol in reversed(production):
                        stack.append(symbol)

            else:
                return {"result": "Rejected", "steps": steps}

        else:
            return {"result": "Rejected", "steps": steps}

        if pointer == len(input_string):
            break

    return {"result": "Accepted", "steps": steps}


# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("index.html")


# -------- ANALYZE GRAMMAR -------- #

@app.route("/analyze", methods=["POST"])
def analyze():

    global grammar, first, follow

    data = request.json
    rules = data["grammar"].split("\n")

    grammar = {}
    first = {}
    follow = {}

    if not rules or rules == [""]:
        return jsonify({"error": "Grammar cannot be empty"})

    for rule in rules:

        if "->" not in rule:
            return jsonify({"error": "Invalid rule: " + rule})

        left, right = rule.split("->")

        left = left.strip()

        productions = [p.strip() for p in right.split("|")]

        grammar[left] = [p for p in productions if p]

    # FIRST sets
    for nt in grammar:
        first[nt] = find_first(nt)

    start = list(grammar.keys())[0]

    # FOLLOW sets
    find_follow(start)

    # Parse table
    table = create_parse_table()

    result = {
        "FIRST": {k: list(v) for k, v in first.items()},
        "FOLLOW": {k: list(v) for k, v in follow.items()},
        "LEFT_RECURSION": detect_left_recursion(),
        "LEFT_FACTORING": detect_left_factoring(),
        "PARSE_TABLE": table
    }

    return jsonify(result)


# -------- VALIDATE STRING -------- #

@app.route("/validate", methods=["POST"])
def validate():

    global grammar, follow

    if not grammar:
        return jsonify({"error": "Please analyze grammar first"})

    data = request.json
    string = data["string"]

    start = list(grammar.keys())[0]

    # Ensure FOLLOW exists
    if not follow:
        find_follow(start)

    table = create_parse_table()

    result = validate_string_steps(string, table, start)

    return jsonify(result)


# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    app.run()
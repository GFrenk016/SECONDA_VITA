"""Esegue una breve sequenza di azioni per dimostrare il motore senza input interattivo."""
from game.bootstrap import load_world_and_state
from engine.core import actions

registry, state = load_world_and_state()

sequence = [
    ("look", lambda: actions.look(state, registry)),
    ("where", lambda: actions.where(state, registry)),
]

# Trova un oggetto ispezionabile (se presente)
look_first = actions.look(state, registry)
obj_name = None
for line in look_first["lines"]:
    if line.startswith("- "):
        name_part = line[2:].split(":")[0].strip().rstrip(" *")
        obj_name = name_part
        break
if obj_name:
    sequence.extend([
        (f"inspect {obj_name}", lambda n=obj_name: actions.inspect(state, registry, n)),
        (f"examine {obj_name}", lambda n=obj_name: actions.examine(state, registry, n)),
        (f"search {obj_name}", lambda n=obj_name: actions.search(state, registry, n)),
    ])

sequence.extend([
    ("wait 5", lambda: actions.wait(state, registry, 5)),
    ("look (dopo wait)", lambda: actions.look(state, registry)),
    ("wait until notte", lambda: actions.wait_until(state, registry, "notte")),
    ("look (notte)", lambda: actions.look(state, registry)),
])

for label, func in sequence:
    print("====", label, "====")
    try:
        res = func()
    except Exception as e:
        print("[ERRORE]", e)
        continue
    for l in res["lines"]:
        print(l)
    print()

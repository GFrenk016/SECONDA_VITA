from engine.state import Location

def build_world():
    # Esempio di 3 location collegate
    return {
        "start": Location(
            key="start",
            name="A Small Clearing",
            desc=(
            "The grass is wet with dawn. A narrow path bends north between old pines."
            ),
            exits={"north": "woods"},
            ),
        "woods": Location(
            key="woods",
            name="Whispering Woods",
            desc=(
            "Branches lace above you. Somewhere, water drips. Paths lead east and south."
            ),
            exits={"east": "cabin", "south": "start"},
            ),
        "cabin": Location(
            key="cabin",
            name="Abandoned Cabin",
            desc=(
            "Dust hangs in slanted light. A table, a cold stove, and a locked chest."
            ),
            exits={"west": "woods"},
        ),
    }

from engine.state import Location

def build_world():
    # Due luoghi: foresta, casa abbandonata
    # Due oggetti totali: coltello (foresta), foto (casa)
    return {
        "foresta": Location(
            key="foresta",
            name="Foresta",
            desc=(
                "L’alba filtra tra gli aghi dei pini. L’aria sa di resina e terra bagnata. "
                "Un sentiero incerto conduce a nord, dove la luce si fa più pallida."
            ),
            exits={"north": "casa"},
            items={"coltello": 1}
        ),
        "casa": Location(
            key="casa",
            name="Casa Abbandonata",
            desc=(
                "Tavole che scricchiolano, luce obliqua dalle finestre rotte. "
                "Una fotografia impolverata riposa su un tavolo storto."
            ),
            exits={"south": "foresta"},
            items={"foto": 1}
        ),
    }

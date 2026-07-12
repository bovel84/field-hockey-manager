from src.season import generate_cup_bracket, simulate_cup
from src.models import Team, Player, Position

teams = []
for i in range(6):
    t = Team(name=f"Team{i}")
    for j in range(11):
        t.players.append(Player(name=f"P{i}_{j}", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70))
    teams.append(t)

bracket = generate_cup_bracket(teams)
winner = simulate_cup(bracket, seed=42)
print("First sim winner:", winner.name)
print("Budget after 1st:", winner.budget)
print("Prestige after 1st:", winner.prestige)
winner2 = simulate_cup(bracket, seed=99)
print("Second sim winner:", winner2.name)
print("Budget after 2nd:", winner2.budget)
print("Prestige after 2nd:", winner2.prestige)
assert winner.budget == winner2.budget, "BUDGET DOUBLED!"
assert winner.prestige == winner2.prestige, "PRESTIGE DOUBLED!"
print("m10 PASS")
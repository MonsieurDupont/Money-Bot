@app_commands.command(name="blackjack", description="Jouer au blackjack!")
async def blackjack(interaction: Interaction):
    game = Blackjack()
    # Implementation de la logic d'interation
    pass

@app_commands.command(name="poker", description="Jouer au poker!")
async def poker(interaction: Interaction):
    game = Poker()
    # Implementation de la logic d'interation
    pass

@app_commands.command(name="roulette", description="Jouer à la roulette!")
async def roulette(interaction: Interaction):
    game = Roulette()
    # Implementation de la logic d'interation
    pass
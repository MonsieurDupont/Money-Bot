import discord
import os
import mysql.connector
import random
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

# Database connection
db = mysql.connector.connect(
    host=os.getenv("host"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    database=os.getenv("database")
)
cursor = db.cursor()

# Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# --- Database setup ---
cursor.execute("CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, cash BIGINT DEFAULT 0, bank BIGINT DEFAULT 0, transactions TEXT DEFAULT '[]');")
db.commit()

# --- Commands ---
@bot.tree.command(name="register", description="Register a new user")
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    cursor.execute("INSERT IGNORE INTO users (id) VALUES (%s)", (user_id,))
    cursor.execute("UPDATE users SET cash = 100, bank = 100 WHERE id = %s", (user_id,))
    db.commit()
    await interaction.response.send_message(f"<@{user_id}>, vous êtes inscrit ! Vous avez 100 AploucheCoins en cash et 100 en banque.")

@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    cursor.execute("SELECT cash, bank FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    if result:
        cash, bank = result
        total = cash + bank
        await interaction.response.send_message(f"<@{user_id}>, votre solde est : Cash: {cash}, Banque: {bank}, Total: {total} AploucheCoins.")
    else:
        await interaction.response.send_message(f"<@{user_id}>, vous devez vous inscrire avec `/register`.")

@bot.tree.command(name="withdraw", description="Withdraw money from your bank")
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    cursor.execute("SELECT bank FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    if result:
        bank = result[0]
        if bank >= amount:
            cursor.execute("UPDATE users SET cash = cash + %s, bank = bank - %s WHERE id = %s", (amount, amount, user_id))
            db.commit()
            await interaction.response.send_message(f"<@{user_id}>, vous avez retiré {amount} AploucheCoins de votre banque.")
            add_transaction(user_id, -amount, "Sent")
        else:
            await interaction.response.send_message(f"<@{user_id}>, vous n'avez pas assez d'argent en banque.")
    else:
        await interaction.response.send_message(f"<@{user_id}>, vous devez vous inscrire avec `/register`.")

@bot.tree.command(name="deposit", description="Deposit money into your bank")
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    cursor.execute("SELECT cash FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    if result:
        cash = result[0]
        if cash >= amount:
            cursor.execute("UPDATE users SET cash = cash - %s, bank = bank + %s WHERE id = %s", (amount, amount, user_id))
            db.commit()
            await interaction.response.send_message(f"<@{user_id}>, vous avez déposé {amount} AploucheCoins dans votre banque.")
            add_transaction(user_id, amount, "Received")
        else:
            await interaction.response.send_message(f"<@{user_id}>, vous n'avez pas assez d'argent en cash.")
    else:
        await interaction.response.send_message(f"<@{user_id}>, vous devez vous inscrire avec `/register`.")

@bot.tree.command(name="leaderboard", description="View the leaderboard")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT id, cash, bank FROM users ORDER BY cash + bank DESC")
    leaderboard = cursor.fetchall()
    message = "Classement des richesses:\n"
    for i, (user_id, cash, bank) in enumerate(leaderboard):
        message += f"{i+1}. <@{user_id}>: {cash + bank} AploucheCoins\n"
    await interaction.response.send_message(message)

@bot.tree.command(name="stats", description="View your transaction history")
async def stats(interaction: discord.Interaction):
    user_id = interaction.user.id
    cursor.execute("SELECT transactions FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    if result:
        transactions = eval(result[0])
        message = "Historique des transactions:\n"
        for transaction in transactions:
            message += f"{transaction}\n"
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message(f"<@{user_id}>, vous devez vous inscrire avec `/register`.")

@bot.tree.command(name="transaction", description="Send money to another user")
async def transaction(interaction: discord.Interaction, user: discord.User, amount: int):
    sender_id = interaction.user.id
    receiver_id = user.id
    cursor.execute("SELECT cash FROM users WHERE id = %s", (sender_id,))
    result = cursor.fetchone()
    if result:
        cash = result[0]
        if cash >= amount:
            cursor.execute("UPDATE users SET cash = cash - %s WHERE id = %s", (amount, sender_id))
            cursor.execute("UPDATE users SET cash = cash + %s WHERE id = %s", (amount, receiver_id))
            db.commit()
            await interaction.response.send_message(f"<@{sender_id}>, vous avez envoyé {amount} AploucheCoins à <@{receiver_id}>.")
            add_transaction(sender_id, -amount, "Sent")
            add_transaction(receiver_id, amount, "Received")
        else:
            await interaction.response.send_message(f"<@{sender_id}>, vous n'avez pas assez d'argent.")
    else:
        await interaction.response.send_message(f"<@{sender_id}>, vous devez vous inscrire avec `/register`.")

@bot.tree.command(name="rob", description="Rob another user")
async def rob(ctx, user: discord.User):
    robber_id = interaction.user.id
    victim_id = user.id
    cursor.execute("SELECT cash FROM users WHERE id = %s", (robber_id,))
    robber_cash = cursor.fetchone()[0]
    cursor.execute("SELECT cash FROM users WHERE id = %s", (victim_id,))
    victim_cash = cursor.fetchone()[0]
    
    # Calculate probability of success
    if victim_cash <= robber_cash:
        probability = 0.1
    else:
        probability = victim_cash / (victim_cash + robber_cash)
    
    if random.random() < probability:
        amount = int(victim_cash * random.uniform(0.1, 0.3))
        cursor.execute("UPDATE users SET cash = cash - %s WHERE id = %s", (amount, victim_id))
        cursor.execute("UPDATE users SET cash = cash + %s WHERE id = %s", (amount, robber_id))
        db.commit()
        await interaction.response.send_message(f"<@{robber_id}> a volé {amount} AploucheCoins à <@{victim_id}> !")
        add_transaction(robber_id, amount, "Robbery")
        add_transaction(victim_id, -amount, "Robbery")
    else:
        loss = int(robber_cash * (1 - probability))
        cursor.execute("UPDATE users SET cash = cash - %s WHERE id = %s", (loss, robber_id))
        db.commit()
        await interaction.response.send_message(f"<@{robber_id}> a échoué à voler <@{victim_id}> et a perdu {loss} AploucheCoins !")
        add_transaction(robber_id, -loss, "Failed Robbery")

@bot.tree.command(name="rob", description="Rob another user")
async def rob(interaction: discord.Interaction, user: discord.User):
    robber_id = interaction.user.id
    victim_id = user.id
    cursor.execute("SELECT cash FROM users WHERE id = %s", (robber_id,))
    robber_cash = cursor.fetchone()[0]
    cursor.execute("SELECT cash FROM users WHERE id = %s", (victim_id,))
    victim_cash = cursor.fetchone()[0]
    
    # Calculate probability of success
    if victim_cash <= robber_cash:
        probability = 0.1
    else:
        probability = victim_cash / (victim_cash + robber_cash)
    
    if random.random() < probability:
        amount = int(victim_cash * random.uniform(0.1, 0.3))
        cursor.execute("UPDATE users SET cash = cash - %s WHERE id = %s", (amount, victim_id))
        cursor.execute("UPDATE users SET cash = cash + %s WHERE id = %s", (amount, robber_id))
        db.commit()
        await interaction.response.send_message(f"<@{robber_id}> a volé {amount} AploucheCoins à <@{victim_id}> !")
        add_transaction(robber_id, amount, "Robbery")
        add_transaction(victim_id, -amount, "Robbery")
    else:
        loss = int(robber_cash * (1 - probability))
        cursor.execute("UPDATE users SET cash = cash - %s WHERE id = %s", (loss, robber_id))
        db.commit()
        await interaction.response.send_message(f"<@{robber_id}> a échoué à voler <@{victim_id}> et a perdu {loss} AploucheCoins !")
        add_transaction(robber_id, -loss, "Failed Robbery")

def add_transaction(user_id, amount, type):
    cursor.execute("SELECT transactions FROM users WHERE id = %s", (user_id,))
    transactions = eval(cursor.fetchone()[0])
    transactions.append({"amount": amount, "type": type})
    cursor.execute("UPDATE users SET transactions = %s WHERE id = %s", (str(transactions), user_id))
    db.commit()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Commands synced")

bot.run(os.getenv("token"))

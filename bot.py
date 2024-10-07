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
cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT, amount BIGINT, type VARCHAR(255), timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
db.commit()

# --- Commands ---
@bot.tree.command(name="register", description="Register a new user")
async def register(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        cursor.execute("INSERT IGNORE INTO users (id) VALUES (%s)", (user_id,))
        cursor.execute("UPDATE users SET cash = 100, bank = 100 WHERE id = %s", (user_id,))
        db.commit()
        await interaction.response.send_message(f"<@{user_id}>, vous êtes inscrit ! Vous avez 100 AploucheCoins en cash et 100 en banque.")
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors de l'inscription : {err}")

@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        cursor.execute("SELECT cash, bank FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            cash, bank = result
            total = cash + bank
            await interaction.response.send_message(f"<@{user_id}>, votre solde est : Cash: {cash}, Banque: {bank}, Total: {total} AploucheCoins.")
        else:
            await interaction.response.send_message(f"<@{user_id}>, vous devez vous inscrire avec `/register`.")
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors de la vérification du solde : {err}")

@bot.tree.command(name="withdraw", description="Withdraw money from your bank")
async def withdraw(interaction: discord.Interaction, amount: int):
    try:
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
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors du retrait : {err}")

@bot.tree.command(name="deposit", description="Deposit money into your bank")
async def deposit(interaction: discord.Interaction, amount: int):
    try:
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
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors du dépôt : {err}")

@bot.tree.command(name="leaderboard", description="View the leaderboard")
async def leaderboard(interaction: discord.Interaction):
    try:
        cursor.execute("SELECT id, cash, bank FROM users ORDER BY cash + bank DESC")
        leaderboard = cursor.fetchall()
        message = "Classement des richesses:\n"
        for i, (user_id, cash, bank) in enumerate(leaderboard):
            message += f"{i+1}. <@{user_id}>: {cash + bank} AploucheCoins\n"
        await interaction.response.send_message(message)
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors de l'affichage du classement : {err}")

@bot.tree.command(name="stats", description="View your transaction history")
async def stats(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        cursor.execute("SELECT amount, type, timestamp FROM transactions WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
        transactions = cursor.fetchall()
        message = "Historique des transactions:\n"
        for transaction in transactions:
            message += f"{transaction[2]} - {transaction[1]} : {transaction[0]} AploucheCoins\n"
        await interaction.response.send_message(message)
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors de l'affichage de l'historique des transactions : {err}")

@bot.tree.command(name="transaction", description="Send money to another user")
async def transaction(interaction: discord.Interaction, user: discord.User, amount: int):
    try:
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
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors de la transaction : {err}")

@bot.tree.command(name="steal", description="Rob another user")
async def steal(interaction: discord.Interaction, user: discord.User):
    try:
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
    except mysql.connector.Error as err:
        await interaction.response.send_message(f"Erreur lors du vol : {err}")

def add_transaction(user_id, amount, type):
    try:
        cursor.execute("INSERT INTO transactions (user_id, amount, type) VALUES (%s, %s, %s)", (user_id, amount, type))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Erreur lors de l'ajout de la transaction : {err}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Commands synced")

bot.run(os.getenv("token"))
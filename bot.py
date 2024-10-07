import discord
import os
import mysql.connector
import random
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

# Constantes pour les noms de tables et les champs de la base de données
TABLE_USERS = "users"
TABLE_TRANSACTIONS = "transactions"
FIELD_ID = "id"
FIELD_CASH = "cash"
FIELD_BANK = "bank"
FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_AMOUNT = "amount"

# Fonction pour se connecter à la base de données
def connect_to_database():
    return mysql.connector.connect(
        host=os.getenv("host"),
        user=os.getenv("user"),
        password=os.getenv("password"),
        database=os.getenv("database")
    )

# Fonction pour exécuter une requête SQL
def execute_query(query, params):
    db = connect_to_database()
    cursor = db.cursor()
    cursor.execute(query, params)
    db.commit()
    cursor.close()
    db.close()

# Fonction pour récupérer des données de la base de données
def fetch_data(query, params):
    db = connect_to_database()
    cursor = db.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return data

# Fonction pour ajouter une transaction
def add_transaction(user_id, amount, type):
    query = f"INSERT INTO {TABLE_TRANSACTIONS} ({FIELD_ID}, {FIELD_AMOUNT}, {FIELD_TYPE}) VALUES (%s, %s, %s)"
    execute_query(query, (user_id, amount, type))

# Fonction pour vérifier si un utilisateur est enregistré
def is_registered(user_id):
    query = f"SELECT COUNT(*) FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    result = fetch_data(query, (user_id,))
    return result[0][0] > 0

# Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Commandes
@bot.tree.command(name="register", description="Register a new user")
async def register(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        query = f"SELECT COUNT(*) FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
        result = fetch_data(query, (user_id,))
        if result[0][0] == 0:
            query = f"INSERT IGNORE INTO {TABLE_USERS} ({FIELD_ID}) VALUES (%s)"
            execute_query(query, (user_id,))
            query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = 0, {FIELD_BANK} = 1000 WHERE {FIELD_ID} = %s"
            execute_query(query, (user_id,))
            embed = discord.Embed(title="Bienvenue !", description="Vous êtes désormais inscrit ! Vous avez reçu 1000 <:AploucheCoin:1286080674046152724> en banque.", color=0x00ff00)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous êtes déjà inscrit !", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors de l'inscription : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        if is_registered(user_id):
            query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
            data = fetch_data(query, (user_id,))
            if data:
                cash, bank = data[0]
                total = cash + bank
                embed = discord.Embed(title="Votre solde", description=f"Voici votre solde actuel :", color=0x00ff00)
                embed.add_field(name="Cash", value=f"{cash} <:AploucheCoin:1286080674046152724>", inline=False)
                embed.add_field(name="Banque", value=f"{bank} <:AploucheCoin:1286080674046152724>", inline=False)
                embed.add_field(name="Total", value=f"{total} <:AploucheCoin:1286080674046152724>", inline=False)
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(title="Erreur", description=f"Erreur lors de la vérification du solde.", color=0xff0000)
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors de la vérification du solde : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposit", description="Deposit money into your bank")
async def deposit(interaction: discord.Interaction, amount: int):
    try:
        user_id = interaction.user.id
        if is_registered(user_id):
            query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
            data = fetch_data(query, (user_id,))
            if data:
                cash = data[0][0]
                if cash >= amount:
                    query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s, {FIELD_BANK} = {FIELD_BANK} + %s WHERE {FIELD_ID} = %s"
                    execute_query(query, (amount, amount, user_id))
                    embed = discord.Embed(title="Dépôt", description=f"Vous avez déposé {amount} <:AploucheCoin:1286080674046152724> dans votre banque.", color=0x00ff00)
                    await interaction.response.send_message(embed=embed)
                    add_transaction(user_id, amount, "Received")
                else:
                    embed = discord.Embed(title="Erreur", description=f"Vous n'avez pas assez d'argent en cash.", color=0xff0000)
                    await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(title="Erreur", description=f"Erreur lors du dépôt.", color=0xff0000)
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors du dépôt : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="View the leaderboard")
async def leaderboard(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        if is_registered(user_id):
            query = f"SELECT {FIELD_ID}, {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} ORDER BY {FIELD_CASH} + {FIELD_BANK} DESC"
            data = fetch_data(query, ())
            embed = discord.Embed(title="Classement des richesses", description="Voici le classement des utilisateurs les plus riches :", color=0x00ff00)
            for i, (user_id, cash, bank) in enumerate(data):
                user = await bot.fetch_user(user_id)
                total = cash + bank
                embed.add_field(name="", value=f"#{i+1} {user.mention} : {total} <:AploucheCoin:1286080674046152724>", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register` pour accéder au leaderboard.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors de l'affichage du classement : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="transaction_history", description="View your transaction history")
async def transaction_history(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        if is_registered(user_id):
            query = f"SELECT {FIELD_AMOUNT}, {FIELD_TYPE}, {FIELD_TIMESTAMP} FROM {TABLE_TRANSACTIONS} WHERE {FIELD_ID} = %s ORDER BY {FIELD_TIMESTAMP} DESC"
            data = fetch_data(query, (user_id,))
            embed = discord.Embed(title="Transaction History", description="Voici votre historique des transactions :", color=0x00ff00)
            for transaction in data:
                embed.add_field(name=f"{transaction[2]}", value=f"{transaction[1]} : {transaction[0]} <:AploucheCoin:1286080674046152724>", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors de l'affichage de l'historique des transactions : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="steal", description="Rob another user")
async def steal(interaction: discord.Interaction, user: discord.User):
    try:
        robber_id = interaction.user.id
        victim_id = user.id
        if is_registered(robber_id) and is_registered(victim_id):
            query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
            robber_cash = fetch_data(query, (robber_id,))[0][0]
            query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
            victim_cash = fetch_data(query, (victim_id,))[0][0]
            
            # Calculate probability of success
            if victim_cash <= robber_cash:
                probability = 0.1
            else:
                probability = victim_cash / (victim_cash + robber_cash)
            
            if random.random() < probability:
                amount = int(victim_cash * random.uniform(0.1, 0.3))
                query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s"
                execute_query(query, (amount, victim_id))
                query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s"
                execute_query(query, (amount, robber_id))
                embed = discord.Embed(title="Vol", description=f"<@{robber_id}> a volé {amount} <:AploucheCoin:1286080674046152724> à <@{victim_id}> !", color=0x00ff00)
                await interaction.response.send_message(embed=embed)
                add_transaction(robber_id, amount, "Robbery")
                add_transaction(victim_id, -amount, "Robbery")
            else:
                loss = int(robber_cash * (1 - probability))
                query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s"
                execute_query(query, (loss, robber_id))
                embed = discord.Embed(title="Erreur", description=f"<@{robber_id}> a échoué à voler <@{victim_id}> et a perdu {loss} <:AploucheCoin:1286080674046152724> !", color=0xff0000)
                await interaction.response.send_message(embed=embed)
                add_transaction(robber_id, -loss, "Failed Robbery")
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors du vol : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="transaction", description="Send money to another user")
async def transaction(interaction: discord.Interaction, user: discord.User, amount: int):
    try:
        sender_id = interaction.user.id
        receiver_id = user.id
        if is_registered(sender_id) and is_registered(receiver_id):
            query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
            sender_cash = fetch_data(query, (sender_id,))[0][0]
            if sender_cash >= amount:
                query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s"
                execute_query(query, (amount, sender_id))
                query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s"
                execute_query(query, (amount, receiver_id))
                embed = discord.Embed(title="Transaction", description=f"<@{sender_id}> a envoyé {amount} <:AploucheCoin:1286080674046152724> à <@{receiver_id}>.", color=0x00ff00)
                await interaction.response.send_message(embed=embed)
                add_transaction(sender_id, -amount, "Sent")
                add_transaction(receiver_id, amount, "Received")
            else:
                embed = discord.Embed(title="Erreur", description=f"<@{sender_id}> n'a pas assez d'argent.", color=0xff0000)
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors de la transaction : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="withdraw", description="Withdraw money from your bank")
async def withdraw(interaction: discord.Interaction, amount: int):
    try:
        user_id = interaction.user.id
        if is_registered(user_id):
            query = f"SELECT {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
            bank = fetch_data(query, (user_id,))[0][0]
            if bank >= amount:
                query = f"UPDATE {TABLE_USERS} SET {FIELD_BANK} = {FIELD_BANK} - %s, {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s"
                execute_query(query, (amount, amount, user_id))
                embed = discord.Embed(title="Retrait", description=f"<@{user_id}> a retiré {amount} <:AploucheCoin:1286080674046152724> de sa banque.", color=0x00ff00)
                await interaction.response.send_message(embed=embed)
                add_transaction(user_id, -amount, "Withdrawal")
            else:
                embed = discord.Embed(title="Erreur", description=f"<@{user_id}> n'a pas assez d'argent en banque.", color=0xff0000)
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description=f"Erreur lors du retrait : {err}", color=0xff0000)
        await interaction.response.send_message(embed=embed)

# Lancement du bot
bot.run(os.getenv("token"))
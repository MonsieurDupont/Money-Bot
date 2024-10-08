# **Database**
import mysql.connector
from mysql.connector import Error

# **Logging**
import logging
from logging import getLogger

# **Environment**
import os
from dotenv import load_dotenv

# **Discord**
import discord
from discord.ext import commands
from discord import Interaction, User

# **Utilities**
import asyncio
import random

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

TOKEN = os.getenv("TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")
GUILD_ID = os.getenv("GUILD_ID")
HOST = os.getenv("HOST")
DATABASE = os.getenv("DATABASE")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

# Définition des constantes
TABLE_TRANSACTIONS = "transactions"
TABLE_USERS = "users"
FIELD_ID = "id"
FIELD_AMOUNT = "amount"
FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_CASH = "cash"

# Couleurs
COLOR_GREEN = 0x98d444
COLOR_BLUE = 0x448ad4
COLOR_RED = 0xd44e44

# Définition des erreurs personnalisées
class MoneyBotError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class DatabaseError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur de base de données : {error}")

class DiscordError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur de Discord : {error}")

class TransactionError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur lors de la transaction : {error}")

class InsufficientFundsError(MoneyBotError):
    def __init__(self, user_id, amount):
        self.user_id = user_id
        self.amount = amount
        super().__init__(f"Vous n'avez pas assez d'argent pour effectuer cette transaction : {amount} manquants")

class UserNotFoundError(MoneyBotError):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"L'utilisateur {user_id} n'a pas été trouvé")

class InvalidUserException(MoneyBotError):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"L'utilisateur {user_id} est invalide")

class CommandError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur lors de l'exécution de la commande : {error}")

class ConnectionError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur de connexion : {error}")

class QueryError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur lors de l'exécution de la requête : {error}")

class DataError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur lors de la récupération des données : {error}")

class UpdateError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur lors de la mise à jour des données : {error}")

class CreateError(MoneyBotError):
    def __init__(self, error):
        self.error = error
        super().__init__(f"Erreur lors de la création de nouvelles données : {error}")

# Fonction pour gérer les erreurs
def handle_error(error):
    if isinstance(error, MoneyBotError):
        return error.message
    else:
        return "Erreur inconnue"

# Décorateur pour gérer les erreurs dans les commandes
def error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MoneyBotError as err:
            message = handle_error(err)
            await args[0].response.send_message(message)
        except discord.HTTPException as err:
            error = DiscordError(err)
            message = handle_error(error)
            await args[0].response.send_message(message)
        except mysql.connector.Error as err:
            error = DatabaseError(err)
            message = handle_error(error)
            await args[0].response.send_message(message)
        except Exception as err:
            error = MoneyBotError(err)
            message = handle_error(error)
            await args[0].response.send_message(message)
    return wrapper

# Fonction pour se connecter à la base de données
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="password",
            database="money_bot"
        )
    except mysql.connector.Error as err:
        raise ConnectionError(err)

# Fonction pour exécuter une requête et récupérer les données
def execute_query_or_fetch_data(query, params=None, fetch=False, commit=True):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
        if fetch:
            return cursor.fetchall()
        else:
            return cursor.lastrowid
    except mysql.connector.Error as err:
        raise QueryError(err)

# Fonction pour vérifier si un utilisateur est inscrit
def is_registered(user_id):
    query = f"SELECT * FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    data = execute_query_or_fetch_data(query, (user_id,), fetch=True)
    if data is None:
        raise DataError("Erreur lors de la récupération des données")
    return len(data) > 0

# Fonction pour vérifier si un montant est valide
def is_valid_amount(amount):
    try:
        return amount > 0
    except Exception as err:
        raise ValueError("Montant invalide")

# Fonction pour récupérer l'argent d'un utilisateur
def get_user_cash(user_id):
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    data = execute_query_or_fetch_data(query, (user_id,), fetch=True)
    if data is None:
        raise DataError("Erreur lors de la récupération des données")
    return data[0][0]

# Fonction pour ajouter une transaction
def add_transaction(user_id, amount, transaction_type):
    query = f"INSERT INTO {TABLE_TRANSACTIONS} ({FIELD_ID}, {FIELD_AMOUNT}, {FIELD_TYPE}, {FIELD_TIMESTAMP}) VALUES (%s, %s, %s, NOW())"
    execute_query_or_fetch_data(query, (user_id, amount, transaction_type))

# Création du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Commande pour s'inscrire
@bot.tree.command(name="register", description="S'inscrire")
@error_handler
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    if is_registered(user_id):
        error = UserNotFoundError(user_id)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    
    execute_query(f"INSERT INTO {TABLE_USERS} ({FIELD_ID}, {FIELD_CASH}, {FIELD_BANK}) VALUES (%s, 0, 1000)", (user_id,))
    embed = discord.Embed(title="Inscription réussie", description=f"Vous êtes désormais inscrit ! Vous avez reçu 1000 <:AploucheCoin:1286080674046152724>.", color=COLOR_GREEN)
    await interaction.response.send_message(embed=embed)

# Commande pour vérifier son solde
@bot.tree.command(name="balance", description="Vérifier son solde")
@error_handler
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        error = UserNotFoundError(user_id)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    
    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    data = execute_query_or_fetch_data(query, (user_id,), fetch=True)
    if data is None:
        error = DatabaseError("Erreur lors de la récupération des données")
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    cash, bank = data[0]
    total = cash + bank
    embed = discord.Embed(title="Solde", description=f" **Cash** : {cash} <:AploucheCoin:1286080674046152724> \n **Banque** : {bank} <:AploucheCoin:1286080674046152724> \n **Total** : {total} <:AploucheCoin:1286080674046152724>", color=COLOR_BLUE)
    await interaction.response.send_message(embed=embed)

# Commande pour voler un joueur
@bot.tree.command(name="steal", description="Voler un joueur")
@error_handler
async def steal(interaction: discord.Interaction, user: discord.User):
    robber_id = interaction.user.id
    victim_id = user.id

    if not is_registered(robber_id) or not is_registered(victim_id):
        error = UserNotFoundError(robber_id)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return

    robber_cash = get_user_cash(robber_id)
    victim_cash = get_user_cash(victim_id)

    if victim_cash <= 0:
        error = InsufficientFundsError(victim_id, victim_cash)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    
    # Calcul de la probabilité de réussite
    if victim_cash <= robber_cash:
        probability = 0.1
    else:
        probability = victim_cash / (victim_cash + robber_cash)
    
    if random.random() < probability:
        amount = int(victim_cash * random.uniform(0.1, 0.3))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, victim_id))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, robber_id))
        embed = discord.Embed(title="Vol réussi", description=f"<@{robber_id}> a volé {amount} <:AploucheCoin:1286080674046152724> à <@{victim_id}> !", color=COLOR_GREEN)
        await interaction.response.send_message(embed=embed)
        add_transaction(robber_id, amount, "Vol")
        add_transaction(victim_id, -amount, "Vol")
    else:
        loss = int(robber_cash * (1 - probability))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (loss, robber_id))
        embed = discord.Embed(title="Vol échoué", description=f"<@{robber_id}> s'est fait chopper en train de voler <@{victim_id}> et a perdu {loss} <:AploucheCoin:1286080674046152724> !", color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        add_transaction(robber_id, -loss, "Échec de vol")

# Commande pour envoyer de l'argent à un joueur
@bot.tree.command(name="transaction", description="Envoyer de l'argent à un joueur")
@error_handler
async def transaction(interaction: discord.Interaction, user: discord.User, amount: int):
    sender_id = interaction.user.id
    receiver_id = user.id
    if not is_registered(sender_id) or not is_registered(receiver_id):
        error = UserNotFoundError(sender_id)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    sender_cash = execute_query_or_fetch_data(query, (sender_id,), fetch=True)
    if sender_cash is None:
        error = DatabaseError("Erreur lors de la récupération des données")
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    sender_cash = sender_cash[0][0]
    if sender_cash >= amount:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, sender_id))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, receiver_id))
        embed = discord.Embed(title="Transaction réussie", description=f"<@{sender_id}> a envoyé {amount} <:AploucheCoin:1286080674046152724> à <@{receiver_id}>.", color=COLOR_GREEN)
        await interaction.response.send_message(embed=embed)
        add_transaction(sender_id, -amount, "Envoi")
        add_transaction(receiver_id, amount, "Réception")
    else:
        error = InsufficientFundsError(sender_id, amount)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)

# Commande pour retirer de l'argent de la banque
@bot.tree.command(name="withdraw", description="Retirer de l'argent de la banque")
@error_handler
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        error = UserNotFoundError(user_id)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    
    query = f"SELECT {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    bank = execute_query_or_fetch_data(query, (user_id,), fetch=True)
    if bank is None:
        error = DatabaseError("Erreur lors de la récupération des données")
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    bank = bank[0][0]
    if bank >= amount:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_BANK} = {FIELD_BANK} - %s WHERE {FIELD_ID} = %s", (amount, user_id))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, user_id))
        embed = discord.Embed(title="Retrait réussi", description=f"<@{user_id}> a retiré {amount} <:AploucheCoin:1286080674046152724> de sa banque.", color=COLOR_GREEN)
        await interaction.response.send_message(embed=embed)
        add_transaction(user_id, -amount, "Retrait")
    else:
        error = InsufficientFundsError(user_id, amount)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)

# Commande pour déposer de l'argent dans la banque
@bot.tree.command(name="deposit", description="Déposer de l'argent dans la banque")
@error_handler
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        error = UserNotFoundError(user_id)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    cash = execute_query_or_fetch_data(query, (user_id,), fetch=True)
    if cash is None:
        error = DatabaseError("Erreur lors de la récupération des données")
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)
        return
    cash = cash[0][0]
    if cash >= amount:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, user_id))
        embed = discord.Embed(title="Dépôt réussi", description=f"<@{user_id}> a déposé {amount} <:AploucheCoin:1286080674046152724> dans sa banque.", color=COLOR_GREEN)
        await interaction.response.send_message(embed=embed)
        add_transaction(user_id, amount, "Dépôt")
    else:
        error = InsufficientFundsError(user_id, amount)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)

# Commande pour afficher le leaderboard
@bot.tree.command(name="leaderboard", description="Afficher le leaderboard")
@error_handler
async def leaderboard(interaction: discord.Interaction):
    try:
        query = f"SELECT {FIELD_ID}, {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} ORDER BY {FIELD_CASH} + {FIELD_BANK} DESC"
        data = execute_query_or_fetch_data(query, fetch=True)
        if data is None:
            error = DatabaseError("Erreur lors de la récupération des données")
            message = handle_error(error)
            embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
            await interaction.response.send_message(embed=embed)
            return
        embed = discord.Embed(title="Leaderboard", description="Voici le leaderboard des joueurs les plus riches :", color=COLOR_BLUE)
        for i, (user_id, cash, bank) in enumerate(data):
            user = await bot.fetch_user(user_id)
            total = cash + bank
            embed.add_field(name=f"#{i+1} - {user.mention} - {total} <:AploucheCoin:1286080674046152724>", value="\u200b", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        error = MoneyBotError(e)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)

# Commande pour afficher l'historique des transactions d'un joueur
@bot.tree.command(name="transaction_history", description="Afficher l'historique des transactions d'un joueur")
@error_handler
async def transaction_history(interaction: discord.Interaction, user: discord.User = None):
    try:
        if user is None:
            user = interaction.user
        query = f"SELECT {FIELD_AMOUNT}, {FIELD_TYPE}, {FIELD_TIMESTAMP} FROM {TABLE_TRANSACTIONS} WHERE {FIELD_ID} = %s ORDER BY {FIELD_TIMESTAMP} DESC"
        data = execute_query_or_fetch_data(query, (user.id,), fetch=True)
        if data is None:
            error = DatabaseError("Erreur lors de la récupération des données")
            message = handle_error(error)
            embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
            await interaction.response.send_message(embed=embed)
            return
        embed = discord.Embed(title="Historique des transactions", description=f"Historique des transactions de {user.mention} :", color=COLOR_BLUE)
        for transaction in data:
            amount, transaction_type, timestamp = transaction
            embed.add_field(name=f"{timestamp}", value=f"{transaction_type} : {amount} <:AploucheCoin:1286080674046152724>", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        error = MoneyBotError(e)
        message = handle_error(error)
        embed = discord.Embed(title="Erreur", description=message, color=COLOR_RED)
        await interaction.response.send_message(embed=embed)

# Commande pour supprimer un compte
@bot.tree.command(name="delete_account", description="Supprimer un compte")
@commands.has_permissions(administrator=True)
@error_handler
async def delete_account(interaction: discord.Interaction, user: discord.User):
    embed = discord.Embed(title="Confirmation de suppression", description=f"Voulez-vous vraiment supprimer le compte de {user.mention} ? Toute donnée sera perdue.", color=COLOR_RED)
    embed.add_field(name="Attention", value="Cette action est irréversible.", inline=False)
    message = await interaction.response.send_message(embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, user_reaction):
        return user_reaction == interaction.user and reaction.message == message and (str(reaction.emoji) == "✅" or str(reaction.emoji) == "❌")

    try:
        reaction, user_reaction = await bot.wait_for("reaction_add", check=check, timeout=60)
    except asyncio.TimeoutError:
        await message.edit(content="Temps écoulé, suppression annulée.")
        return

    if str(reaction.emoji) == "✅":
        try:
            execute_query(f"DELETE FROM {TABLE_USERS} WHERE {FIELD_ID} = %s", (user.id,))
            execute_query(f"DELETE FROM {TABLE_TRANSACTIONS} WHERE {FIELD_ID} = %s", (user.id,))
            await message.edit(content=f"Compte de {user.mention} supprimé avec succès.")
        except mysql.connector.Error as err:
            error = DatabaseError(err)
            message = handle_error(error)
            await message.edit(content=message)
    elif str(reaction.emoji) == "❌":
        await message.edit(content=f"Suppression annulée.")

# Lancement du bot
async def main():
    await bot.start(TOKEN)

asyncio.run(main())
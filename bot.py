# Importation des bibliothèques nécessaires
import os
import logging
import asyncio
import datetime
import mysql.connector
import discord
import typing
import random
import json
import configparser
from dotenv import load_dotenv
from discord.ext import commands
from treys import Card, Deck
from datetime import datetime
from typing import List, Dict
from discord.ui import TextInput, Select

# Chargement des variables d'environnement
load_dotenv()

# Chargement du fichier .ini 
commandsconfig = configparser.ConfigParser()
commandsconfig.read('settings.ini')

# Chargement des fichiers JSON
with open('commandphrases.json') as file:
    workdata = json.load(file)
    workphrases = workdata["workphrases"]
with open('cards.json') as file:
    card_map = json.load(file)
with open('roulette_config.json') as f:
    config = json.load(f)

# Définition des constantes
TOKEN = os.getenv("TOKEN")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GUILD_ID = os.getenv("GUILD_ID")
APPLICATION_ID = os.getenv("APPLICATION_ID")
COIN_EMOJI = "<:AploucheCoin:1286080674046152724>"
CARD_BACK = "<:cardback:1296606466920284234>"
WORK_MIN_PAY = commandsconfig.getint('Work', 'work_min_pay')
WORK_MAX_PAY = commandsconfig.getint('Work', 'work_max_pay')
WORK_COOLDOWN = commandsconfig.getint('Work', 'work_cooldown')
POKER_START_BET = commandsconfig.getint('Poker', 'poker_start_bet')
BLACKJACK_MIN_BET = commandsconfig.getint('Blackjack', 'blackjack_min_bet')
ROULETTE_NUMBERS = config['ROULETTE_NUMBERS']
ROULETTE_COLORS = config['ROULETTE_COLORS']
ROULETTE_MIN_BET = config['ROULETTE_MIN_BET']
ROULETTE_MAX_BET = config['ROULETTE_MAX_BET']
ROULETTE_WAIT_TIME = config['ROULETTE_WAIT_TIME']
ROULETTE_NUMBER_EMOJIS = config['ROULETTE_NUMBER_EMOJIS']
ROULETTE_COLOR_EMOJIS = config['ROULETTE_COLOR_EMOJIS']
ROULETTE_MONEY_EMOJI = config['ROULETTE_MONEY_EMOJI']
ROULETTE_TIMER_EMOJI = config['ROULETTE_TIMER_EMOJI']
ROULETTE_BET_TYPES = config['ROULETTE_BET_TYPES']

# Définition des couleurs
color_green = 0x98d444
color_blue = 0x448ad4
color_red = 0xd44e44
color_yellow = 0xffbf00

# Définition des tables et des champs
TABLE_USERS = "users"
TABLE_TRANSACTIONS = "transactions"
FIELD_USER_ID = "user_id"
FIELD_CASH = "cash"
FIELD_BANK = "bank"
FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_AMOUNT = "amount"

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Création du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Fonction pour se connecter à la base de données
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )
    except mysql.connector.Error as err:
        logging.error("Erreur de connexion à la base de données : {}".format(err))
        return None

# Fonction pour exécuter une requête SQL
def execute_query(query, params=None):
    try:
        conn = get_db_connection()
        if conn is None:
            raise mysql.connector.Error("Impossible de se connecter à la base de données")
        cursor = conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return True
    except mysql.connector.Error as err:
        logging.error("Erreur de requête SQL : {}".format(err))
        raise
    finally:
        if conn:
            conn.close()

# Fonction pour récupérer des données de la base de données
def fetch_data(query, params=None):
    try:
        conn = get_db_connection()
        if conn is None:
            raise mysql.connector.Error("Impossible de se connecter à la base de données")
        cursor = conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        logging.error("Erreur de requête SQL : {}".format(err))
        raise
    finally:
        if conn:
            conn.close()

# Fonction pour vérifier si un utilisateur est inscrit
def is_registered(user_id):
    try:
        query = f"SELECT * FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
        data = fetch_data(query, (user_id,))
        return len(data) > 0
    except mysql.connector.Error as err:
        logging.error("Erreur lors de la vérification de l'enregistrement : {}".format(err))
        raise

# Fonction pour ajouter une transaction
def add_transaction(user_id, amount, transaction_type):
    try:
        query = f"INSERT INTO {TABLE_TRANSACTIONS} ({FIELD_USER_ID}, {FIELD_AMOUNT}, {FIELD_TYPE}) VALUES (%s, %s, %s)"
        execute_query(query, (user_id, amount, transaction_type))
    except mysql.connector.Error as err:
        logging.error("Erreur lors de l'ajout d'une transaction : {}".format(err))
        raise

# Gestion d'erreur
async def handle_error(interaction: discord.Interaction, error: Exception, message: str = None):
    if isinstance(error, ValueError):
        await interaction.response.send_message(f"Erreur de valeur : {str(error)}", ephemeral=True)
    elif isinstance(error, mysql.connector.Error):
        logging.error(f"Erreur de base de données : {str(error)}")
        await interaction.response.send_message("Une erreur de base de données s'est produite. Veuillez réessayer plus tard.", ephemeral=True)
    elif isinstance(error, asyncio.TimeoutError):
        await interaction.response.send_message("Le temps d'attente est écoulé. Veuillez réessayer.", ephemeral=True)
    else:
        logging.error(f"Erreur inattendue : {str(error)}")
        await interaction.response.send_message(message or "Une erreur inattendue s'est produite.", ephemeral=True)

# Récupérer le solde d'un utilisateur
async def get_user_balance(user_id: int) -> int:
    try:
        query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
        data = fetch_data(query, (user_id,))
        if data and data[0]:
            return data[0][0]
        else:
            return 0
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du solde de l'utilisateur : {str(e)}")
        raise

# Mettre à jour le solde d'un utilisateur
async def update_user_balance(user_id: int, amount: int) -> None:
    try:
        query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_USER_ID} = %s"
        execute_query(query, (amount, user_id))
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du solde de l'utilisateur : {str(e)}")
        raise

# Synchronisation des commandes
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

class DeleteAccountView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()

# BASIC COMMANDS

# Commande pour s'inscrire
@bot.tree.command(name="register", description="S'inscrire")
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    if is_registered(user_id):
        embed = discord.Embed(title="Erreur", description=f"Vous êtes déjà inscrit, {interaction.user.mention}.", color=color_red)
        embed.add_field(name="Raison", value="Vous avez déjà un compte existant.", inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        query = f"""
            INSERT INTO 
                {TABLE_USERS} ({FIELD_USER_ID}, {FIELD_CASH}, {FIELD_BANK})
            VALUES 
                (%s, 1000, 0)
        """
        result = execute_query(query, (user_id,))
        if result:
            embed = discord.Embed(title="Succès", description=f"Vous êtes maintenant inscrit, {interaction.user.mention}. Vous avez reçu 1000 {COIN_EMOJI} en cash.", color=color_green)
            embed.add_field(name="Prochaines étapes", value="Vous pouvez maintenant utiliser les commandes `/balance`, `/deposit`, `/withdraw` et `/transaction`.", inline=False)
            embed.add_field(name="Aide", value="Si vous avez des questions, n'hésitez pas à demander.", inline=False)
            embed.set_footer(text="Bienvenue dans notre communauté !")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description=f"Erreur lors de l'inscription, {interaction.user.mention}.", color=color_red)
            embed.add_field(name="Raison", value="Veuillez réessayer plus tard.", inline=False)
            await interaction.response.send_message(embed=embed)

# Commande pour afficher les statistiques
@bot.tree.command(name="stats", description="Afficher les statistiques")
async def stats(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        SELECT 
            u.{FIELD_CASH}, 
            u.{FIELD_BANK}, 
            SUM(CASE WHEN t.{FIELD_TYPE} = 'Transaction' AND t.{FIELD_AMOUNT} > 0 THEN t.{FIELD_AMOUNT} ELSE 0 END) AS total_revenus,
            SUM(CASE WHEN t.{FIELD_TYPE} = 'Transaction' AND t.{FIELD_AMOUNT} < 0 THEN t.{FIELD_AMOUNT} ELSE 0 END) AS total_depenses
        FROM 
            {TABLE_USERS} u
        LEFT JOIN 
            {TABLE_TRANSACTIONS} t ON u.{FIELD_USER_ID} = t.{FIELD_USER_ID}
        WHERE 
            u.{FIELD_USER_ID} = %s
        GROUP BY 
            u.{FIELD_USER_ID}, u.{FIELD_CASH}, u.{FIELD_BANK}
    """
    data = fetch_data(query, (user_id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    cash, bank, total_revenus, total_depenses = data[0]
    if cash is None or bank is None or total_revenus is None or total_depenses is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    # Vérification de la cohérence des données
    if cash < 0 or bank < 0:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données. Veuillez contacter un administrateur.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if total_revenus < 0 or total_depenses > 0:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données. Veuillez contacter un administrateur.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    total = cash + bank
    moyenne_depenses = total_depenses / (total_revenus + abs(total_depenses)) if total_revenus + abs(total_depenses) > 0 else 0
    moyenne_revenus = total_revenus / (total_revenus + abs(total_depenses)) if total_revenus + abs(total_depenses) > 0 else 0

    embed = discord.Embed(title="Statistiques", description=f"Voici vos statistiques, {interaction.user.mention}.", color=color_green)
    embed.add_field(name="Cash", value=f"{cash} {COIN_EMOJI}", inline=False)
    embed.add_field(name="Banque", value=f"{bank} {COIN_EMOJI}", inline=False)
    embed.add_field(name="Total", value=f"{total} {COIN_EMOJI}", inline=False)
    embed.add_field(name="Revenus", value=f"{total_revenus} {COIN_EMOJI}", inline=False)
    embed.add_field(name="Dépenses", value=f"{total_depenses} {COIN_EMOJI}", inline=False)
    embed.add_field(name="Moyenne des dépenses", value=f"{moyenne_depenses * 100:.2f}%", inline=False)
    embed.add_field(name="Moyenne des revenus", value=f"{moyenne_revenus * 100:.2f}%", inline=False)
    await interaction.response.send_message(embed=embed)

# Commande pour vérifier son solde
@bot.tree.command(name="balance", description="Vérifier votre solde")
async def balance(interaction: discord.Interaction, user: typing.Optional[discord.Member]):
    if user is None:
        user_id = interaction.user.id
        user_name = interaction.user.display_name
    else:
        user_id = user.id
        user_name = user.display_name
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user_id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    cash, bank = data[0]
    if cash is None or bank is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    total = cash + bank
    embed = discord.Embed(title=f"Solde", description=f"**Cash** : {cash:,} {COIN_EMOJI}\n**Banque** : {bank:,} {COIN_EMOJI}\n**Total** : {total:,} {COIN_EMOJI}", color=color_blue)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
    if total <= 0:
        embed.add_field(name="", value="Wesh c'est la hess la ", inline=False)
    await interaction.response.send_message(embed=embed)

# Commande pour déposer de l'argent dans sa banque
@bot.tree.command(name="deposit", description="Déposer de l'argent")
async def deposit(interaction: discord.Interaction, amount: typing.Optional[int]):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount is None:
        query = f"""
            SELECT 
                u.{FIELD_CASH}
            FROM 
                {TABLE_USERS} u
            WHERE 
                u.{FIELD_USER_ID} = %s
        """
        data = fetch_data(query, (user_id,))
        amount = data[0][0]

    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    cash = data[0][0]
    if cash is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant doit être supérieur à 0.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    if amount < 0:
        embed = discord.Embed(title="Erreur", description="T'es pauvre mec", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    query = f"""
        SELECT 
            u.{FIELD_CASH}
        FROM 
            {TABLE_USERS} u
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    data = fetch_data(query, (user_id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    cash = data[0][0]
    if cash is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if cash < amount:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent pour déposer.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    if cash < 0:
        embed = discord.Embed(title="Erreur", description="C'est la hess y a rien a déposer.", color=color_red)
        await interaction.response.send_message(embed=embed)

    query = f"""
        UPDATE 
            {TABLE_USERS} u
        SET 
            u.{FIELD_CASH} = u.{FIELD_CASH} - %s,
            u.{FIELD_BANK} = u.{FIELD_BANK} + %s
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    result = execute_query(query, (amount, amount, user_id))
    if result:
        embed = discord.Embed(title="Succès", description=f"Vous avez déposé {amount} {COIN_EMOJI} avec succès.", color=color_green)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Erreur", description="Erreur lors du dépôt.", color=color_red)
        await interaction.response.send_message(embed=embed)

# Commande pour retirer de l'argent de sa banque
@bot.tree.command(name="withdraw", description="Retirer de l'argent")
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant doit être supérieur à 0.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        SELECT 
            u.{FIELD_BANK}
        FROM 
            {TABLE_USERS} u
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    data = fetch_data(query, (user_id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    bank = data[0][0]
    if bank is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if bank < amount:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent dans la banque pour retirer.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    # Vérification des transactions en cours
    query = f"""
        SELECT 
            t.{FIELD_USER_ID}
        FROM 
            {TABLE_TRANSACTIONS} t
        WHERE 
            t.{FIELD_USER_ID} = %s AND t.{FIELD_TYPE} = 'Transaction' AND t.{FIELD_TIMESTAMP} > NOW() - INTERVAL 1 MINUTE
    """
    data = fetch_data(query, (user_id,))
    if data is not None and len(data) > 0:
        embed = discord.Embed(title="Erreur", description="Vous avez déjà une transaction en cours. Veuillez attendre quelques instants avant de procéder à une nouvelle transaction.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        UPDATE 
            {TABLE_USERS} u
        SET 
            u.{FIELD_BANK} = u.{FIELD_BANK} - %s,
            u.{FIELD_CASH} = u.{FIELD_CASH} + %s
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    result = execute_query(query, (amount, amount, user_id))
    if result:
        embed = discord.Embed(title="Succès", description=f"Vous avez retiré {amount} {COIN_EMOJI} avec succès.", color=color_green)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Erreur", description="Erreur lors du retrait.", color=color_red)
        await interaction.response.send_message(embed=embed)

# Commande pour voler de l'argent à un u
@bot.tree.command(name="steal", description="Volé de l'argent à un utilisateur")
async def steal(interaction: discord.Interaction, user: discord.Member):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if user_id == user.id:
        embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas voler votre propre argent.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="L'utilisateur ciblé doit être inscrit.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    victim_data = fetch_data(query, (user.id,))
    stealer_data = fetch_data(query, (user_id,))
    if victim_data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de l'utilisateur ciblé.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(victim_data) == 0:
        embed = discord.Embed(title="Erreur", description="L'utilisateur ciblé n'a pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    victim_cash = victim_data[0][0]
    cash, bank = stealer_data[0]
    stealer_cash = cash + bank
    if victim_cash is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de l'utilisateur ciblé.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if victim_cash <= 0:
        embed = discord.Embed(title="Erreur", description="L'utilisateur ciblé n'a pas assez d'argent pour être volé.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    
    proba = max(0.2, min(0.8, stealer_cash / (victim_cash + stealer_cash)))
     # Probabilité de réussite
    amount = round(proba * victim_cash)
    print(proba)
    randoma = random.random()
    print(randoma)                       # Montant a voler

    if randoma <= proba:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_USER_ID} = %s", (amount, user.id))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_USER_ID} = %s", (amount, user_id))
        embed = discord.Embed(title="Vol réussi", description=f"Vous avez volé {amount :,} {COIN_EMOJI} à {user.mention}.", color=color_green)
        await interaction.response.send_message(embed=embed)
    else:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_USER_ID} = %s", (amount, user_id))
        embed = discord.Embed(title="Vol raté", description=f"Vous avez essayé de voler <@{user.id}> mais vous vous etes fait choper. Vous avez reçu une amende de {amount}  ", color=color_red)
        await interaction.response.send_message(embed=embed)
    try:
        add_transaction(user_id, amount, 'Steal')
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description="Erreur lors de l'ajout de la transaction.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return   

# Commande pour envoyer de l'argent à un utilisateur
@bot.tree.command(name="send", description="Envoyer de l'argent")
async def transaction(interaction: discord.Interaction, user: discord.Member, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant doit être supérieur à 0.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if user == interaction.user:
        embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas vous envoyew de l'argent a vous-même.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        SELECT 
            u.{FIELD_CASH}
        FROM 
            {TABLE_USERS} u
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    data = fetch_data(query, (user_id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    cash = data[0][0]
    if cash is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if cash < amount:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        UPDATE 
            {TABLE_USERS} u
        SET 
            u.{FIELD_CASH} = u.{FIELD_CASH} - %s
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    result = execute_query(query, (amount, user_id))
    if result:
        query = f"""
            INSERT INTO 
                {TABLE_TRANSACTIONS} ({FIELD_USER_ID}, {FIELD_TYPE}, {FIELD_AMOUNT})
            VALUES 
                (%s, 'Transaction', %s)
        """
        result = execute_query(query, (user.id, amount))
        if result:
            embed = discord.Embed(title="Succès", description=f"Vous avez envoyé {amount} {COIN_EMOJI} avec succès.", color=color_green)
            # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Erreur lors de l'envoi.", color=color_red)
            # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
            await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Erreur", description="Erreur lors de l'envoi.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)

# Commande pour afficher le leaderboard
@bot.tree.command(name="leaderboard", description="Voir le classement des joueurs")
async def leaderboard(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        SELECT 
            u.{FIELD_USER_ID}, 
            u.{FIELD_CASH} + u.{FIELD_BANK} AS total
        FROM 
            {TABLE_USERS} u
        ORDER BY 
            total DESC
        LIMIT 10
    """
    data = fetch_data(query)
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Aucune donnée disponible.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(title="Classement des utilisateurs", description="Voici le classement des 10 utilisateurs les plus riches :", color=color_blue)
    # embed.add_field(name="**Rang**", value="**Utilisateur**", inline=False)
    for i, (user_id, total) in enumerate(data, start=1):       
        user = await bot.fetch_user(user_id)
        if user is None:
           continue
        # await interaction.response.send_message(f"#{i} {user.display_name} {total} ")
        if i <= 3:
            embed.add_field(name=f"#{i}", value=f"<@{user.id}> : **{total:,}** {COIN_EMOJI}", inline=False)  
        else:
            embed.add_field(name=f"", value=f"**{i}** • <@{user.id}> : **{total:,}** {COIN_EMOJI}", inline=False)
    # embed.set_footer(text="Note : Ce classement est mis à jour en temps réel.")
    await interaction.response.send_message(embed=embed)

# Commande pour afficher l'historique des transactions
@bot.tree.command(name="transaction_history", description="Historique des transactions")
async def transaction_history(interaction: discord.Interaction, user: typing.Optional[discord.Member]):
    if user is None:
        user_id = interaction.user.id
    else:
        user_id = user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_USER_ID}, {FIELD_AMOUNT}, {FIELD_TYPE} FROM {TABLE_TRANSACTIONS} WHERE {FIELD_USER_ID} = %s ORDER BY {FIELD_USER_ID} DESC"
    data = fetch_data(query, (user_id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de transactions.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    transactions = []
    for row in data:
        transaction_id, amount, transaction_type = row
        if amount is None or transaction_type is None:
            continue
        transactions.append((transaction_id, amount, transaction_type))

    if len(transactions) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de transactions.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    foo = await bot.fetch_user(user_id)
    embed = discord.Embed(title=f"Historique de {foo.name}", description="Voici la liste des 10 dernieres transactions :", color=color_blue)
    embed.add_field(name="", value="**Montant** | **Type**", inline=False)
    for i, (transaction_id, amount, transaction_type) in enumerate(transactions[::-1][:10], start=1):
        embed.add_field(name="", value=f"**{i}** : {amount:,} {COIN_EMOJI} | {transaction_type}", inline=False)
    # embed.set_footer(text="Note : Ce classement est mis à jour en temps réel.")
    await interaction.response.send_message(embed=embed)

# Commande pour afficher la liste des commandes
@bot.tree.command(name="help", description="Afficher les commandes disponibles")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Aide", description="Bienvenue dans l'aide de notre bot !", color=color_blue)
    embed.add_field(name="Commandes", value="Voici les commandes disponibles :", inline=False)
    embed.add_field(name="/register", value="S'inscrire", inline=False)
    embed.add_field(name="/balance", value="Vérifier votre solde", inline=False)
    embed.add_field(name="/deposit", value="Déposer de l'argent dans la ban que", inline=False)
    embed.add_field(name="/withdraw", value="Retirer de l'argent de la banque", inline=False)
    # embed.add_field(name="/help", value="Afficher les commandes disponibles", inline=False)
    await interaction.response.send_message(embed=embed)

# Commande pour supprimer un compte
@bot.tree.command(name="delete_account", description="Supprimer le compte")
async def delete_account(interaction: discord.Interaction, user: discord.Member):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    ##  if user == interaction.user:
        embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas supprimer votre propre compte.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return ##

    if user.bot:
        embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas supprimer le compte d'un bot.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    query = f"""
        SELECT 
            {FIELD_USER_ID}, 
            {FIELD_CASH} + {FIELD_BANK} AS total
        FROM 
            {TABLE_USERS}
        WHERE 
            {FIELD_USER_ID} = %s
    """
    data = fetch_data(query, (user.id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de l'utilisateur.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="L'utilisateur n'a pas de compte.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    view = DeleteAccountView()
    if user == interaction.user:
        embed = discord.Embed(description=f"Voulez-vous supprimer votre compte ?", color=color_blue)
    else:
        embed = discord.Embed(description=f"Voulez-vous supprimer le compte de {user.mention} ?", color=color_blue)
    await interaction.response.send_message(embed=embed, view=view)
    await view.wait()
    if view.value is True:
        query = f"""
            DELETE FROM 
                {TABLE_USERS} u
            WHERE 
                u.{FIELD_USER_ID} = %s
        """
        result = execute_query(query, (user.id,))
        if result:
            query = f"""
                DELETE FROM 
                    {TABLE_TRANSACTIONS} t
                WHERE 
                    t.{FIELD_USER_ID} = %s
            """
            result = execute_query(query, (user.id,))
            if result:
                embed = discord.Embed(title="Succès", description=f"Le compte de {user.mention} a été supprimé avec succès.", color=color_green)
                # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(title="Erreur", description="Erreur lors de la suppression du compte.", color=color_red)
                # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
                await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Erreur lors de la suppression du compte.", color=color_red)
            # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
            await interaction.followup.send(embed=embed)
    else:
        embed = discord.Embed(description="La suppression du compte a été annulée.", color=color_green)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.followup.send(embed=embed)

# Commande pour give de l'argent à un utilisateur
@bot.tree.command(name="give", description="Se give de l'argent | ADMINS SEULEMENT")
async def give(interaction: discord.Interaction, amount: int, user: typing.Optional[discord.Member]):
    if user is None:
        user_id = interaction.user.id
    else:
        user_id = user.id

    query = f"""
    UPDATE 
        {TABLE_USERS} u
    SET 
        u.{FIELD_CASH} = u.{FIELD_CASH} + %s
    WHERE 
        u.{FIELD_USER_ID} = %s
    """
    execute_query(query, (amount, user_id))
    try:
        add_transaction(user_id, amount, 'Give')
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description="Erreur lors de l'ajout de la transaction.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if interaction.user.id == user_id:
        embed = discord.Embed(title="", description=f"{amount} {COIN_EMOJI} ont étés ajouté a votre compte", color=color_green)
    else:
        embed = discord.Embed(title="", description=f"{amount} {COIN_EMOJI} ont étés ajouté au compte de <@{user.id}>", color=color_green)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Commande pour retirer l'argent d'un utilisateur
@bot.tree.command(name="remove", description="Se retirer de l'argent | ADMINS SEULEMENT")
async def remove(interaction: discord.Interaction, amount: int, user: typing.Optional[discord.Member]):
    if user is None:
        user_id = interaction.user.id
    else:
        user_id = user.id

    query = f"""
    UPDATE 
        {TABLE_USERS} u
    SET 
        u.{FIELD_CASH} = u.{FIELD_CASH} - %s
    WHERE 
        u.{FIELD_USER_ID} = %s
    """
    execute_query(query, (amount, user_id))
    try:
        add_transaction(user_id, amount, 'Remove')
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description="Erreur lors de l'ajout de la transaction.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if interaction.user.id == user_id:
        embed = discord.Embed(title="", description=f"{amount} {COIN_EMOJI} ont étés retirés a votre compte", color=color_green)
    else:
        embed = discord.Embed(title="", description=f"{amount} {COIN_EMOJI} ont étés retirés au compte de <@{user.id}>", color=color_green)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Commande pour travailler
@bot.tree.command(name="work", description="Travailler")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return


    if WORK_COOLDOWN <= 0:
        embed = discord.Embed(title="Erreur", description="La valeur de cooldown est invalide.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    query = f"""
        SELECT 
            t.{FIELD_TIMESTAMP}
        FROM 
            {TABLE_TRANSACTIONS} t
        WHERE 
            t.{FIELD_USER_ID} = %s AND t.{FIELD_TYPE} = 'Work'
        ORDER BY 
            t.{FIELD_TIMESTAMP} DESC
        LIMIT 1
    """
    data = fetch_data(query, (user_id,))
    if data is not None and len(data) > 0:
        last_work_time = data[0][0]
        current_time = datetime.now()
        time_diff = (current_time - last_work_time).total_seconds()
        if time_diff < WORK_COOLDOWN:
            embed = discord.Embed(title="Erreur", description=f"Vous devez attendre {WORK_COOLDOWN - int(time_diff)} secondes avant de travailler à nouveau.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return
    biased_pay = WORK_MIN_PAY + (WORK_MAX_PAY - WORK_MIN_PAY) * (random.random() ** 2)
    pay = int(biased_pay)   # Nombre aleatoire definissant la paye
    if pay <= 0:
        embed = discord.Embed(title="Erreur", description="La valeur de pay est invalide.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    random_phrase = random.choice(workphrases) 

    query = f"""
        UPDATE 
            {TABLE_USERS} u
        SET 
            u.{FIELD_CASH} = u.{FIELD_CASH} + %s
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    result = execute_query(query, (pay, user_id))

    # Vérification si la table TABLE_USERS est vide ou si la colonne FIELD_CASH est vide
    if result is None or result == 0:
        embed = discord.Embed(title=" Erreur", description="Erreur lors de la mise à jour de votre solde.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Vérification si la colonne FIELD_CASH est vide
    query = f"""
        SELECT 
            u.{FIELD_CASH}
        FROM 
            {TABLE_USERS} u
        WHERE 
            u.{FIELD_USER_ID} = %s
    """
    data = fetch_data(query, (user_id,))
    if data is None or len(data) == 0 or data[0][0] is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la mise à jour de votre solde.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        add_transaction(user_id, pay, 'Work')
    except mysql.connector.Error as err:
        embed = discord.Embed(title="Erreur", description="Erreur lors de l'ajout de la transaction.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Vérification si la transaction a été ajoutée avec succès
    query = f"""
        SELECT 
            t.{FIELD_USER_ID}
        FROM 
            {TABLE_TRANSACTIONS} t
        WHERE 
            t.{FIELD_USER_ID} = %s AND t.{FIELD_TYPE} = 'Work'
        ORDER BY 
            t.{FIELD_TIMESTAMP} DESC
        LIMIT 1
    """
    data = fetch_data(query, (user_id,))
    if data is None or len(data) == 0 or data[0][0] is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de l'ajout de la transaction.", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(title=(f"{interaction.user.display_name}"), description=random_phrase.format(pay=pay) + COIN_EMOJI, color=color_green)
    await interaction.response.send_message(embed=embed)


# GAMES

# Congreenir une carte en emoji
def card_to_emoji(card):
   return card_map.get(card.lower(), "❓")

def card_to_name(card):
    value_map = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', 
    '7': '7', '8': '8', '9': '9', '10': '10', 
    'j': 'Valet', 'q': 'Reine', 'k': 'Roi', 'a': 'As'
    }
    suit_map = {
    'c': 'Trefle', 'd': 'Carré', 'h': 'Coeur', 's': 'Pique'
    }

    value = value_map.get(card[:-1].lower())
    suit = suit_map.get(card[-1].lower(), 'Unknown Suit')

    return f"{value} de {suit}"


# ROULETTE

class RouletteBet:
    def __init__(self, user: discord.Member, amount: int, bet_type: str, bet_value: str):
        if amount <= 0:
            raise ValueError("Le montant du pari doit être positif")
        if bet_type not in ["number", "color", "even_odd", "high_low", "dozen", "column", "split", "street", "corner", "line"]:
            raise ValueError("Type de pari invalide")
        self.user = user
        self.amount = amount
        self.bet_type = bet_type
        self.bet_value = bet_value

class RouletteGame:
    def __init__(self):
        self.is_running = False
        self.bets = []

    async def start_game(self, interaction: discord.Interaction):
        self.is_running = True
        self.bets = []

        embed = discord.Embed(title="🎰 Nouvelle partie de Roulette ! 🎰",
                            description=f"La roulette va tourner dans {ROULETTE_WAIT_TIME} secondes !\n"
                                        f"Utilisez les boutons ci-dessous pour placer vos paris ! ",
                            color=discord.Color.gold())
        embed.add_field(name="Mise minimale", value=f"{ROULETTE_MIN_BET} {ROULETTE_MONEY_EMOJI}")
        embed.add_field(name="Mise maximale", value=f"{ROULETTE_MAX_BET} {ROULETTE_MONEY_EMOJI}")
        embed.add_field(name="Temps restant", value=f"{ROULETTE_TIMER_EMOJI} {ROULETTE_WAIT_TIME} secondes")

        view = RouletteView(self)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        for i in range(ROULETTE_WAIT_TIME, 0, -1):
            if i % 10 == 0 or i <= 5:
                embed.set_field_at(2, name="Temps restant", value=f"{ROULETTE_TIMER_EMOJI} {i} secondes")
                await message.edit(embed=embed)
            await asyncio.sleep(1)

        view.roulette_game = None
        await self.spin_roulette(message)

    async def place_bet(self, interaction: discord.Interaction, amount: int, bet_type: str, bet_value: str):
        try:
            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET} {COIN_EMOJI}.")

            user_balance = await get_user_balance(interaction.user.id)
            if user_balance < amount:
                raise ValueError(f"Solde insuffisant. Votre solde actuel est de {user_balance} {COIN_EMOJI}.")

            if bet_type not in ["number", "color", "even_odd", "dozen", "column"]:
                raise ValueError(f"Type de pari invalide : {bet_type}")

            bet = RouletteBet(interaction.user, amount, bet_type, bet_value)
            self.bets.append(bet)

            await update_user_balance(interaction.user.id, -amount)

            await interaction.response.send_message(f"Pari placé ! Vous avez parié {amount} {COIN_EMOJI} sur {bet_value} {ROULETTE_COLOR_EMOJIS.get(bet_value, '')}.", ephemeral=True)
        except Exception as e:
            await handle_error(interaction, e, "Erreur lors du placement du pari.")

    def calculate_winnings(self, bet: RouletteBet, winning_number: int, winning_color: str) -> int:
        try:
            if bet.bet_type not in ROULETTE_BET_TYPES:
                raise ValueError(f"Type de pari invalide : {bet.bet_type}")

            payout = ROULETTE_BET_TYPES[bet.bet_type]['payout']

            if bet.bet_type == "number":
                if int(bet.bet_value) == winning_number:
                    return bet.amount * (payout + 1)
            elif bet.bet_type == "color":
                if bet.bet_value == winning_color:
                    return bet.amount * (payout + 1)
            elif bet.bet_type == "even_odd":
                if winning_number != 0:  # Le zéro n'est ni pair ni impair
                    if (bet.bet_value == "pair" and winning_number % 2 == 0) or \
                    (bet.bet_value == "impair" and winning_number % 2 != 0):
                        return bet.amount * (payout + 1)
            elif bet.bet_type == "dozen":
                if (bet.bet_value == "1-12" and 1 <= winning_number <= 12) or \
                (bet.bet_value == "13-24" and 13 <= winning_number <= 24) or \
                (bet.bet_value == "25-36" and 25 <= winning_number <= 36):
                    return bet.amount * (payout + 1)
            elif bet.bet_type == "column":
                if winning_number != 0:  # Le zéro n'appartient à aucune colonne
                    if (bet.bet_value == "1" and winning_number % 3 == 1) or \
                    (bet.bet_value == "2" and winning_number % 3 == 2) or \
                    (bet.bet_value == "3" and winning_number % 3 == 0):
                        return bet.amount * (payout + 1)

            return 0  # Si le pari n'est pas gagnant
        except Exception as e:
            logging.error(f"Erreur lors du calcul des gains : {str(e)}")
            raise ValueError(f"Erreur lors du calcul des gains : {str(e)}")

    async def spin_roulette(self, message: discord.InteractionMessage):
        try:
            if not self.bets:
                await message.edit(content="Aucun pari n'a été placé pour cette rotation.")
                return

            # Désactiver les boutons
            view = discord.utils.get(message.components, type=discord.ComponentType.view)
            if isinstance(view, RouletteView):
                view.disable_all_items()
                await message.edit(view=view)
                
            winning_number = random.choice(ROULETTE_NUMBERS)
            winning_color = ROULETTE_COLORS[str(winning_number)]

            embed = discord.Embed(title="La roulette a tourné ! ",
                                description=f"Le numéro gagnant est {winning_number} {ROULETTE_NUMBER_EMOJIS[str(winning_number)]} {ROULETTE_COLOR_EMOJIS[winning_color]}. ",
                                color=discord.Color.red())

            user_results = {}

            for bet in self.bets:
                try:
                    winnings = self.calculate_winnings(bet, winning_number, winning_color)
                    net_result = winnings - bet.amount  # Calcul du résultat net

                    if bet.user.name not in user_results:
                        user_results[bet.user.name] = 0
                    user_results[bet.user.name] += net_result

                    await update_user_balance(bet.user.id, net_result)
                except Exception as e:
                    logging.error(f"Erreur lors de la distribution des gains pour {bet.user.name}: {str(e)}")

            # Trier les résultats des utilisateurs
            sorted_results = sorted(user_results.items(), key=lambda x: x[1], reverse=True)

            # Ajouter les résultats à l'embed
            results_text = ""
            for name, result in sorted_results:
                if result > 0:
                    results_text += f"{name} a gagné {result} {COIN_EMOJI}\n"
                elif result < 0:
                    results_text += f"{name} a perdu {abs(result)} {COIN_EMOJI}\n"
                else:
                    results_text += f"{name} n'a ni gagné ni perdu\n"

            if results_text:
                embed.add_field(name="Résultats", value=results_text, inline=False)
            else:
                embed.add_field(name="Résultats", value="Aucun pari n'a été placé pour cette rotation. ", inline=False)

            await message.edit(embed=embed)
        except Exception as e:
            logging.error(f"Erreur lors de la rotation de la roulette : {str(e)}")
            await message.edit(content="Une erreur s'est produite lors de la rotation de la roulette.")
        finally:
            self.bets.clear()  # Nettoyez la liste des paris après chaque tour

    def get_current_bets_summary(self) -> str:
        if not self.bets:
            return "Aucun pari n'a encore été placé."
        
        summary = []
        for bet in self.bets:
            bet_info = f"{bet.user.name}: {bet.amount} {COIN_EMOJI} sur {bet.bet_value} ({bet.bet_type})"
            summary.append(bet_info)
        
        return "\n".join(summary)

class RouletteView(discord.ui.View):
    def __init__(self, game: RouletteGame):
        super().__init__()
        self.game = game
        self.last_message = None

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True

    async def send_bet_view(self, interaction: discord.Interaction, view, content):
        if self.last_message:
            try:
                await self.last_message.delete()
            except discord.NotFound:
                pass  # Message already deleted, ignore

        await interaction.response.defer()
        self.last_message = await interaction.followup.send(content, view=view, ephemeral=True)

    @discord.ui.button(label="Numéro", style=discord.ButtonStyle.red)
    async def number_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NumberBetModal(self.game))

    @discord.ui.button(label="Couleur", style=discord.ButtonStyle.blurple)
    async def color_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ColorBetView(self.game, self)
        await self.send_bet_view(interaction, view, "Choisissez une couleur :")

    @discord.ui.button(label="Pair/Impair", style=discord.ButtonStyle.green)
    async def even_odd_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EvenOddBetView(self.game, self)
        await self.send_bet_view(interaction, view, "Choisissez Pair ou Impair :")

    @discord.ui.button(label="Douzaine", style=discord.ButtonStyle.grey)
    async def dozen_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DozenBetView(self.game, self)
        await self.send_bet_view(interaction, view, "Choisissez une douzaine :")

    @discord.ui.button(label="Colonne", style=discord.ButtonStyle.primary)
    async def column_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ColumnBetView(self.game, self)
        await self.send_bet_view(interaction, view, "Choisissez une colonne :")

    @discord.ui.button(label="Voir les paris", style=discord.ButtonStyle.secondary)
    async def show_bets(self, interaction: discord.Interaction, button: discord.ui.Button):
        bets_summary = self.game.get_current_bets_summary()
        embed = discord.Embed(title="Paris actuels", description=bets_summary, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True

class AmountInputModal(discord.ui.Modal, title="Entrer le montant du pari"):
    def __init__(self, game: RouletteGame, bet_type: str, bet_value: str):
        super().__init__()
        self.game = game
        self.bet_type = bet_type
        self.bet_value = bet_value

    amount = discord.ui.TextInput(label=f"Montant ({ROULETTE_MIN_BET}-{ROULETTE_MAX_BET})", min_length=1, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}.")
            await self.game.place_bet(interaction, amount, self.bet_type, self.bet_value)
        except ValueError as e:
            await handle_error(interaction, e, "Erreur de saisie.")
        except Exception as e:
            await handle_error(interaction, e, "Une erreur est survenue lors du placement du pari.")

class NumberBetModal(discord.ui.Modal, title="Placer un pari sur un numéro"):
    def __init__(self, game: RouletteGame):
        super().__init__()
        self.game = game

    number_input = discord.ui.TextInput(
        label="Numéro",
        placeholder="Entrez un numéro entre 0 et 36",
        min_length=1,
        max_length=2
    )

    amount_input = discord.ui.TextInput(
        label=f"Montant ({ROULETTE_MIN_BET}-{ROULETTE_MAX_BET})",
        placeholder=f"Entrez un montant entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}",
        min_length=1,
        max_length=6
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            number = int(self.number_input.value)
            amount = int(self.amount_input.value)

            if number < 0 or number > 36:
                raise ValueError(f"Veuillez entrer un numéro entre 0 et 36.")

            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}.")

            await self.game.place_bet(interaction, amount, "number", str(number))
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            await handle_error(interaction, e, "Une erreur est survenue lors du placement du pari.")

class ColorBetModal(discord.ui.Modal, title="Pari sur une couleur"):
    def __init__(self, game: RouletteGame):
        super().__init__()
        self.game = game
        self.color = discord.ui.Select(
            placeholder="Choisissez une couleur",
            options=[
                discord.SelectOption(label="Rouge", value="red"),
                discord.SelectOption(label="Noir", value="black"),
                discord.SelectOption(label="Vert", value="green")
            ]
        )
        self.add_item(self.color)

    amount = discord.ui.TextInput(label=f"Montant ({ROULETTE_MIN_BET}-{ROULETTE_MAX_BET})", min_length=1, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = self.color.values[0]
            amount = int(self.amount.value)
            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}.")
            await self.game.place_bet(interaction, amount, "color", color)
        except ValueError as e:
            await handle_error(interaction, e, "Erreur de saisie.")
        except Exception as e:
            await handle_error(interaction, e, "Une erreur est survenue lors du placement du pari.")

class ColorBetView(discord.ui.View):
    def __init__(self, game: RouletteGame, parent_view: RouletteView):
        super().__init__()
        self.game = game
        self.parent_view = parent_view
        self.color = None

    @discord.ui.select(
        placeholder="Choisissez une couleur",
        options=[
            discord.SelectOption(label="Rouge", value="red"),
            discord.SelectOption(label="Noir", value="black"),
            discord.SelectOption(label="Vert", value="green")
        ]
    )
    async def select_color(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.color = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Placer le pari", style=discord.ButtonStyle.primary)
    async def place_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.color is None:
            await interaction.response.send_message("Veuillez choisir une couleur.", ephemeral=True)
            return

        modal = AmountInputModal(self.game, "color", self.color)
        await interaction.response.send_modal(modal)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message(f"Erreur : {error}", ephemeral=True)

class EvenOddBetModal(discord.ui.Modal, title="Pari Pair/Impair"):
    def __init__(self, game: RouletteGame):
        super().__init__()
        self.game = game
        self.choice = discord.ui.Select(
            placeholder="Choisissez pair ou impair",
            options=[
                discord.SelectOption(label="Pair", value="pair"),
                discord.SelectOption(label="Impair", value="impair")
            ]
        )
        self.add_item(self.choice)

    amount = discord.ui.TextInput(label=f"Montant ({ROULETTE_MIN_BET}-{ROULETTE_MAX_BET})", min_length=1, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            choice = self.choice.values[0]
            amount = int(self.amount.value)
            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}.")
            await self.game.place_bet(interaction, amount, "even_odd", choice)
        except ValueError as e:
            await handle_error(interaction, e, "Erreur de saisie.")
        except Exception as e:
            await handle_error(interaction, e, "Une erreur est survenue lors du placement du pari.")

class EvenOddBetView(discord.ui.View):
    def __init__(self, game: RouletteGame, parent_view: RouletteView):
        super().__init__()
        self.game = game
        self.parent_view = parent_view
        self.choice = None

    @discord.ui.select(
        placeholder="Choisissez pair ou impair",
        options=[
            discord.SelectOption(label="Pair", value="pair"),
            discord.SelectOption(label="Impair", value="impair")
        ]
    )
    async def select_even_odd(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.choice = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Placer le pari", style=discord.ButtonStyle.primary)
    async def place_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.choice is None:
            await interaction.response.send_message("Veuillez choisir pair ou impair.", ephemeral=True)
            return

        modal = AmountInputModal(self.game, "even_odd", self.choice)
        await interaction.response.send_modal(modal)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message(f"Erreur : {error}", ephemeral=True)

class DozenBetModal(discord.ui.Modal, title="Pari Douzaine"):
    def __init__(self, game: RouletteGame):
        super().__init__()
        self.game = game
        self.choice = discord.ui.Select(
            placeholder="Choisissez une douzaine",
            options=[
                discord.SelectOption(label="1-12", value="1-12"),
                discord.SelectOption(label="13-24", value="13-24"),
                discord.SelectOption(label="25-36", value="25-36")
            ]
        )
        self.add_item(self.choice)

    amount = discord.ui.TextInput(label=f"Montant ({ROULETTE_MIN_BET}-{ROULETTE_MAX_BET})", min_length=1, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            choice = self.choice.values[0]
            amount = int(self.amount.value)
            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}.")
            await self.game.place_bet(interaction, amount, "dozen", choice)
        except ValueError as e:
            await handle_error(interaction, e, "Erreur de saisie.")
        except Exception as e:
            await handle_error(interaction, e, "Une erreur est survenue lors du placement du pari.")

class DozenBetView(discord.ui.View):
    def __init__(self, game: RouletteGame, parent_view: RouletteView):
        super().__init__()
        self.game = game
        self.parent_view = parent_view
        self.choice = None

    @discord.ui.select(
        placeholder="Choisissez une douzaine",
        options=[
            discord.SelectOption(label="1-12", value="1-12"),
            discord.SelectOption(label="13-24", value="13-24"),
            discord.SelectOption(label="25-36", value="25-36")
        ]
    )
    async def select_dozen(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.choice = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Placer le pari", style=discord.ButtonStyle.primary)
    async def place_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.choice is None:
            await interaction.response.send_message("Veuillez choisir une douzaine.", ephemeral=True)
            return

        modal = AmountInputModal(self.game, "dozen", self.choice)
        await interaction.response.send_modal(modal)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message(f"Erreur : {error}", ephemeral=True)

class ColumnBetModal(discord.ui.Modal, title="Pari Colonne"):
    def __init__(self, game: RouletteGame):
        super().__init__()
        self.game = game
        self.choice = discord.ui.Select(
            placeholder="Choisissez une colonne",
            options=[
                discord.SelectOption(label="Première colonne", value="1"),
                discord.SelectOption(label="Deuxième colonne", value="2"),
                discord.SelectOption(label="Troisième colonne", value="3")
            ]
        )
        self.add_item(self.choice)

    amount = discord.ui.TextInput(label=f"Montant ({ROULETTE_MIN_BET}-{ROULETTE_MAX_BET})", min_length=1, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            choice = self.choice.values[0]
            amount = int(self.amount.value)
            if amount < ROULETTE_MIN_BET or amount > ROULETTE_MAX_BET:
                raise ValueError(f"La mise doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET}.")
            await self.game.place_bet(interaction, amount, "column", choice)
        except ValueError as e:
            await handle_error(interaction, e, "Erreur de saisie.")
        except Exception as e:
            await handle_error(interaction, e, "Une erreur est survenue lors du placement du pari.")

class ColumnBetView(discord.ui.View):
    def __init__(self, game: RouletteGame, parent_view: RouletteView):
        super().__init__()
        self.game = game
        self.parent_view = parent_view
        self.choice = None

    @discord.ui.select(
        placeholder="Choisissez une colonne",
        options=[
            discord.SelectOption(label="Première colonne", value="1"),
            discord.SelectOption(label="Deuxième colonne", value="2"),
            discord.SelectOption(label="Troisième colonne", value="3")
        ]
    )
    async def select_column(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.choice = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Placer le pari", style=discord.ButtonStyle.primary)
    async def place_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.choice is None:
            await interaction.response.send_message("Veuillez choisir une colonne.", ephemeral=True)
            return

        modal = AmountInputModal(self.game, "column", self.choice)
        await interaction.response.send_modal(modal)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message(f"Erreur : {error}", ephemeral=True)


@bot.tree.command(name="roulette", description="Lancer une nouvelle partie de roulette")
async def roulette(interaction: discord.Interaction):
    try:
        logging.info("Démarrage d'une nouvelle partie de roulette")
        game = RouletteGame()
        logging.info("Instance de RouletteGame créée avec succès")
        await game.start_game(interaction)
    except Exception as e:
        logging.error(f"Erreur lors du lancement de la partie de roulette : {str(e)}", exc_info=True)
        await handle_error(interaction, e, "Erreur lors du lancement de la partie de roulette.")


# POKER

class PokerPlayerClass:
    def __init__(self, id):
        self.id = id
        self.deck = []

    def set_deck(self, cards):
        self.deck = cards
        
class PokerSessionClass:
    def __init__(self, host_user, game_started=False): # Variables
        self.players = []
        self.playermessages = []
        self.host_user = host_user
        self.game_started = game_started
        pot = 0
        board = Deck
   
    def add_poker_player(self, player_id): # Ajouter un joueur
        self.players.append(PokerPlayerClass(player_id))
    def add_player_message(self, message):
        self.playermessages.append(message)
    def player_exists(self, player_id): # Verifier si un joueur a deja rejoint
        return any(player.id == player_id for player in self.players)
    def num_players(self):
        return len(self.players)
    def deal_cards(self):
        deck = Deck()
        for player in self.players:
            player_deck = deck.draw(2)
            player.set_deck(player_deck)

Poker_game_in_progress = False
poker_session = None

@bot.tree.command(name="poker", description=f"Jouer au poker. La mise initiale est de {POKER_START_BET}")
async def poker(interaction: discord.Interaction):
    user_id = interaction.user.id
    global Poker_game_in_progress, poker_session
    
    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user_id,))
    # Verifier si le joueur a assez d'argent pour lancer la partie
    cash, bank = data[0]
    total = cash + bank

    if total < POKER_START_BET:
        embed = discord.Embed(title="Erreur", description=f"Vous n'avez pas assez d'argent pour la mise initiale", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    else:
        if not Poker_game_in_progress:
            poker_session = PokerSessionClass(host_user=user_id, game_started=False)
            Poker_game_in_progress = True
        else: 
            if poker_session.player_exists(user_id):
                embed = discord.Embed(title="Erreur", description=f"Vous avez déja rejoint la partie", color=color_red)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            elif poker_session.game_started == True:
                embed = discord.Embed(title="Erreur", description=f"Une partie est déja en cours, attendez la fin.", color=color_red)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        embed = discord.Embed(title="Poker", description=f"Vous avez rejoint une partie de poker", color=color_green)
        poker_session.add_poker_player(user_id)
        print([player.id for player in poker_session.players])
        embed.add_field(name="", value="Pour lancer la partie, faites ***/poker_start***")
        embed.set_footer(text=f"Nombre de joueurs dans la partie : {poker_session.num_players()}")
        message = await interaction.response.send_message(embed=embed)
        poker_session.add_player_message(message)



        deck = Deck()
        p1_deck = deck.draw(2)
        p1_cards = [card_to_emoji(Card.int_to_str(card)) for card in p1_deck]
        formatted_cards = " ".join(p1_cards)
        # embed = discord.Embed(title="Poker", description=f"Vos cartes : {formatted_cards}", color=color_green)
        card_list = ""
        for card, emoji in card_map.items():
            card_list += f"{card_to_name(card)} : {emoji}\n"   
        # embed = discord.Embed(title="Poker", description=f"{card_list}", color=color_green)
        # await interaction.response.send_message(embed=embed)

@bot.tree.command(name="poker_start", description=f"Démarrer la partie de poker lorsque tous les joueurs ont rejoint")
async def poker_start(interaction: discord.Interaction):
    global Poker_game_in_progress, poker_session

    if not Poker_game_in_progress:
        embed = discord.Embed(title="Erreur", description=f"Aucune partie de poker n'a été démarée. Faites ***/poker***", color=color_red)
        await interaction.response.send_message(embed=embed) 
        return
    if poker_session.game_started == True:
        embed = discord.Embed(title="Erreur", description="Une partie a déja été lancée", color=color_red)
        await interaction.response.send_message(embed=embed) 
        return
    if poker_session.num_players() < 1:
        embed = discord.Embed(title="Erreur", description=f"Il faut au moins 2 joueurs pour commencer la partie", color=color_red)
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(title="Poker", description=f"La partie de poker va commencer. Bon jeu", color=color_green)
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(1)
    embed = discord.Embed(title="Poker", description=f"Cartes communes:", color=color_green)
    embed.add_field(name="", value=" :flower_playing_cards: :flower_playing_cards: :flower_playing_cards: :flower_playing_cards: :flower_playing_cards:")
    embed.set_footer(text="Vous allez recevoir vos cartes pour faire la mise initiale")
    await interaction.edit_original_response(embed=embed)
    poker_session.deal_cards()

    for player in poker_session.players:        
        deckemoji = [card_to_emoji(Card.int_to_str(card)) for card in player.deck]        
        embed = discord.Embed(title="Vos cartes", description=" ".join(deckemoji), color=color_green)
        deckname = [card_to_name(Card.int_to_str(card)) for card in player.deck]
        embed.set_footer(text=f'{" | ".join(deckname)}')
        await interaction.channel.send(embed=embed)  


# BLACKJACK

""" class BlackJackView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
        self.session = session
        self.interaction = discord.interaction

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.gray)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False

        
class BlackJackSession:
    def __init__(self):
        super().__init__()
        self.deck = Deck()
        self.player_hand = []  
        self.dealer_hand = []
        self.dealer_revealed = False

    # Distribuer les cartes
    def deal(self, hand, amount):
        
        for i in range(amount):
            cards = self.deck.draw(1)
            hand.extend(cards)
        return hand

    # Evaluer une main
    def rank_card(self, card):
    # Extract the rank from the card name (the first character(s))
        rank_str = card[:-1].lower()  # Exclude the suit (last character)
        if rank_str.isdigit():  # For ranks 2 to 9
            return int(rank_str)
        elif rank_str == 't':  # For the 10 card
            return 10
        elif rank_str in ['j', 'q', 'k']:
            return 10  # Face cards are worth 10
        elif rank_str == 'a':
            return 1  # Ace is worth 1 (you can handle 11 separately)
        else:
            print("ERROR: rank card | invalid card")
            return 0  # Invalid card
        
    def evaluate_hand(self, hand):
        total_value = 0
        aces = 0  # Count of Aces in hand

        for card in hand:
            strcard = Card.int_to_str(card)
            card_value = self.rank_card(strcard)
            total_value += card_value
            if strcard.endswith('A'):
                aces += 1  # Count Aces for adjustment later

    # Adjust for Aces if total exceeds 21
        while total_value > 21 and aces > 0:
            total_value -= 10  # Count one Ace as 1 instead of 11
            aces -= 1

        return total_value
    
blackjack_sessions = {}
blackjack_players = []  
@bot.tree.command(name="blackjack", description=f"Démarrer la partie de blackjack")
async def blackjack(interaction: discord.Interaction, amount: int):

    user_id = interaction.user.id
    global blackjack_players
    global blackjack_sessions

    # Verifier si le joueur ne joue pas deja
    if user_id in blackjack_players:
        embed = discord.Embed(title="Erreur", description=f"Vous jouez deja une partie de Black Jack", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return 

    # Verifier si la mise est inferieure a la mise minimale
    if amount < BLACKJACK_MIN_BET:
        embed = discord.Embed(title="Erreur", description=f"La mise minimale est de **{POKER_START_BET}** {COIN_EMOJI}", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Verifier si le joueur a assez d'argent
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user_id,))
    if amount > data[0][0]:
        embed = discord.Embed(title="Erreur", description=f"Vous n'avez pas assez d'argent pour jouer", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Ajouter le joueur a la liste des joueurs
    blackjack_players.append(user_id)

    # Creer une nouvelle session de blackjack
    blackjack_sessions[user_id] = BlackJackSession()

    # Obtenir les cartes pour l'affichage
    player_cards = blackjack_sessions[user_id].player_hand
    dealer_cards = blackjack_sessions[user_id].dealer_hand

    # Tirer les cartes initiales pour le joueur et le croupier
    blackjack_sessions[user_id].deal(blackjack_sessions[user_id].player_hand, 2)  # Player's initial cards
    blackjack_sessions[user_id].deal(blackjack_sessions[user_id].dealer_hand, 1)

    result = ""
    view = BlackJackView()
    embed = discord.Embed(title="", description=f"", color=color_blue)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
    
    # Cartes initiales du joueur
    embed.add_field(name="Vous", value="".join([card_to_emoji(Card.int_to_str(card)) for card in player_cards]))
    # Cartes initiales du croupier
    embed.add_field(name="Croupier", value=f"{card_to_emoji(Card.int_to_str(dealer_cards[0]))} {CARD_BACK}")
    embed.add_field(name="", value="\n")
    embed.add_field(name="", value=f"Score: {blackjack_sessions[user_id].evaluate_hand(player_cards)}")
    embed.add_field(name="", value=f"Score: {blackjack_sessions[user_id].evaluate_hand(dealer_cards)}")

    await interaction.response.send_message(embed=embed, view=view)
 """
class BlackJackView(discord.ui.View):
    def __init__(self, session, interaction):
        super().__init__()
        self.session = session
        self.interaction = interaction
        self.value = None

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Player chooses to "Hit"
        self.session.deal(self.session.player_hand, 1)  # Deal one card to the player
        player_cards = self.session.player_hand
        dealer_cards = self.session.dealer_hand
        
        # Update embed with the new hand
        embed = discord.Embed(title="Blackjack", color=discord.Color.blue())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="Vous", value="".join([card_to_emoji(Card.int_to_str(card)) for card in player_cards]) + f"\nScore: {self.session.evaluate_hand(player_cards)}")
        embed.add_field(name="Croupier", value=f"{card_to_emoji(Card.int_to_str(self.session.dealer_hand[0]))} {CARD_BACK} \nScore: {self.session.evaluate_hand(dealer_cards)}")

        # Check if player busts
        if self.session.evaluate_hand(player_cards) > 21:
            embed.add_field(name="Résultat", value="Vous avez dépassé 21! Perdu!")
            # self.disable_all_items()  # Disable buttons
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.gray)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Player chooses to "Stand"
        dealer_hand = self.session.dealer_hand
        self.session.dealer_revealed = True
        
        # Dealer hits until score is 17 or higher
        while self.session.evaluate_hand(dealer_hand) < 17:
            self.session.deal(dealer_hand, 1)
        
        player_score = self.session.evaluate_hand(self.session.player_hand)
        dealer_score = self.session.evaluate_hand(dealer_hand)

        # Determine the result
        result = ""
        if dealer_score > 21:
            result = "Le croupier a dépassé 21! Vous avez gagné!"
        elif dealer_score > player_score:
            result = "Le croupier a gagné!"
        elif dealer_score < player_score:
            result = "Vous avez gagné!"
        else:
            result = "Égalité!"
        
        # Update the embed
        embed = discord.Embed(title="Blackjack", color=discord.Color.blue())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="Vous", value="".join([card_to_emoji(Card.int_to_str(card)) for card in self.session.player_hand]) + f"\nScore: {player_score}")
        embed.add_field(name="Croupier", value="".join([card_to_emoji(Card.int_to_str(card)) for card in dealer_hand]) + f"\nScore: {dealer_score}")
        embed.add_field(name="Résultat", value=result)

        # Disable buttons after standing
        self.disable_all_items()
        await interaction.response.edit_message(embed=embed, view=self)

class BlackJackSession:
    def __init__(self):
        self.deck = Deck()
        self.player_hand = []  
        self.dealer_hand = []
        self.dealer_revealed = False

    # Deal cards to the hand
    def deal(self, hand, amount):
        for i in range(amount):
            cards = self.deck.draw(1)
            hand.extend(cards)
        return hand

    # Rank cards based on their value in blackjack
    def rank_card(self, card):
        rank_str = card[:-1].lower()  # Exclude the suit (last character)
        if rank_str.isdigit():  # For ranks 2 to 9
            return int(rank_str)
        elif rank_str == 't':  # For the 10 card
            return 10
        elif rank_str in ['j', 'q', 'k']:
            return 10  # Face cards are worth 10
        elif rank_str == 'a':
            return 1  # Ace is worth 1 (can handle 11 separately)
        else:
            print("ERROR: Invalid card")
            return 0  # Invalid card
        
    # Evaluate hand value, considering Ace as either 1 or 11
    def evaluate_hand(self, hand):
        total_value = 0
        aces = 0

        for card in hand:
            strcard = Card.int_to_str(card)
            card_value = self.rank_card(strcard)
            total_value += card_value
            if strcard.startswith('a'):
                aces += 1  # Count Aces for adjustment later

        # Adjust for Aces if total exceeds 21
        while total_value > 21 and aces > 0:
            total_value -= 10  # Count one Ace as 1 instead of 11
            aces -= 1

        return total_value

# Global dictionaries to manage blackjack sessions
blackjack_sessions = {}
blackjack_players = []

@bot.tree.command(name="blackjack", description="Démarrer la partie de blackjack")
async def blackjack(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id

    # Check if player is already playing
    if user_id in blackjack_players:
        embed = discord.Embed(title="Erreur", description="Vous jouez déjà une partie de Black Jack", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check if the bet amount is valid
    if amount < BLACKJACK_MIN_BET:
        embed = discord.Embed(title="Erreur", description=f"La mise minimale est de **{BLACKJACK_MIN_BET}** {COIN_EMOJI}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check if player has enough money
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user_id,))
    if amount > data[0][0]:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent pour jouer", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Add player to active players list and create a new session
    blackjack_players.append(user_id)
    blackjack_sessions[user_id] = BlackJackSession()

    # Deal initial cards to the player and dealer
    session = blackjack_sessions[user_id]
    session.deal(session.player_hand, 2)  # Player gets 2 cards
    session.deal(session.dealer_hand, 1)  # Dealer gets 1 card

    player_cards = session.player_hand
    dealer_cards = session.dealer_hand

    # Create the embed to display the initial cards
    embed = discord.Embed(title="Blackjack", color=discord.Color.blue())
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
    embed.add_field(name="Vous", value="".join([card_to_emoji(Card.int_to_str(card)) for card in player_cards]) + f"\nScore: {session.evaluate_hand(player_cards)}")
    embed.add_field(name="Croupier", value=f"{card_to_emoji(Card.int_to_str(dealer_cards[0]))} {CARD_BACK} \nScore: {session.evaluate_hand(dealer_cards)}" )

    # Send the initial game state with the view containing the buttons
    view = BlackJackView(session, interaction)
    await interaction.response.send_message(embed=embed, view=view)

if __name__ == "__main__":
    bot.run(TOKEN)
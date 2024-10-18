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
from discord import app_commands, Embed, Interaction, Member
from discord.ui import View, Select, Button
from treys import Card, Deck
from datetime import datetime
from typing import Dict, Set, Tuple
from mysql.connector import  Error


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
with open('constants.json') as file:
    CONSTANTS = json.load(file)

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
ROULETTE = CONSTANTS['ROULETTE']

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
    # Tentative de connexion à la base de données
    try:
        return mysql.connector.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )
    except mysql.connector.Error as err:
        # Envoi d'un message d'erreur si la connexion échoue
        logging.error("Erreur de connexion à la base de données : {}".format(err))
        return None

# Fonction pour exécuter une requête SQL
def execute_query(query, params=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return True
    except mysql.connector.Error as err:
        logging.error("Erreur de requête SQL : {}".format(err))
        return False

# Fonction pour récupérer des données de la base de données
def fetch_data(query, params=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        logging.error("Erreur de requête SQL : {}".format(err))
        return []

# Fonction pour vérifier si un utilisateur est inscrit
def is_registered(user_id):
    query = f"SELECT * FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user_id,))
    if data is None:
        return False
    return len(data) > 0

# Fonction pour ajouter une transaction
def add_transaction(user_id, amount, transaction_type):
    try:
        query = f"INSERT INTO {TABLE_TRANSACTIONS} ({FIELD_USER_ID}, {FIELD_AMOUNT}, {FIELD_TYPE}) VALUES (%s, %s, %s)"
        execute_query(query, (user_id, amount, transaction_type))
    except mysql.connector.Error as err:
        logging.error("Erreur lors de l'ajout d'une transaction : {}".format(err))

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

# Convertir une carte en emoji
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

class RouletteSession:
    def __init__(self, bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id
        self.players: Dict[int, int] = {}  # user_id: bet_amount
        self.bets: Dict[int, str] = {}  # user_id: bet_type
        self.bet_types: Dict[str, Set[int]] = {
            "rouge": set(), "noir": set(), "pair": set(), "impair": set(),
            "1-18": set(), "19-36": set(),
            "douzaine 1-12": set(), "douzaine 13-24": set(), "douzaine 25-36": set(),
            "colonne 1": set(), "colonne 2": set(), "colonne 3": set()
        }
        self.is_active = False
        self.winning_number = None

    async def add_player(self, user_id: int, bet_type: str, amount: int):
        if self.is_active:
            return False

        # Vérification des fonds
        user_balance = await self.get_user_balance(user_id)
        if user_balance < amount:
            return False  # Fonds insuffisants

        self.players[user_id] = amount
        self.bets[user_id] = bet_type
        self.bet_types[bet_type].add(user_id)
        return True

    async def spin_wheel(self):
        self.is_active = True
        self.winning_number = random.randint(0, 36)
        color = self.get_color(self.winning_number)
        color_emoji = CONSTANTS['ROULETTE']['EMOJIS'][color]

        channel = self.bot.get_channel(self.channel_id)
        embed = Embed(title="Roulette", description=f"La roue tourne... et le numéro gagnant est: **{self.winning_number}** {color_emoji}", color=0x0000ff)
        await channel.send(embed=embed)

        await self.process_results()

    def get_color(self, number: int) -> str:
        if number == 0:
            return "green"
        elif number in CONSTANTS['ROULETTE']['RED_NUMBERS']:
            return "red"
        else:
            return "black"

    async def process_results(self):
        results: Dict[int, Tuple[int, int]] = {}  # user_id: (winning_amount, bet_amount)
        
        for bet_type, users in self.bet_types.items():
            multiplier = self.get_multiplier(bet_type)
            for user_id in users:
                bet_amount = self.players[user_id]
                winning_amount = bet_amount * multiplier if multiplier > 0 else 0
                results[user_id] = (winning_amount, bet_amount)

        await self.update_player_balances(results)
        await self.send_results(results)

    def get_multiplier(self, bet_type: str) -> int:
        if bet_type == "rouge" and self.winning_number in CONSTANTS['ROULETTE']['RED_NUMBERS']:
            return CONSTANTS['ROULETTE']['PAYOUT_ROUGE']
        elif bet_type == "noir" and self.winning_number in CONSTANTS['ROULETTE']['BLACK_NUMBERS']:
            return CONSTANTS['ROULETTE']['PAYOUT_NOIR']
        elif bet_type == "pair" and self.winning_number % 2 == 0 and self.winning_number != 0:
            return CONSTANTS['ROULETTE']['PAYOUT_PAIR']
        elif bet_type == "impair" and self.winning_number % 2 != 0:
            return CONSTANTS['ROULETTE']['PAYOUT_IMPAIR']
        elif bet_type == "1-18" and 1 <= self.winning_number <= 18:
            return CONSTANTS['ROULETTE']['PAYOUT_1_18']
        elif bet_type == "19-36" and 19 <= self.winning_number <= 36:
            return CONSTANTS['ROULETTE']['PAYOUT_19_36']
        elif bet_type == "douzaine 1-12" and 1 <= self.winning_number <= 12:
            return CONSTANTS['ROULETTE']['PAYOUT_DOUZINE_1_12']
        elif bet_type == "douzaine 13-24" and 13 <= self.winning_number <= 24:
            return CONSTANTS['ROULETTE']['PAYOUT_DOUZINE_13_24']
        elif bet_type == "douzaine 25-36" and 25 <= self.winning_number <= 36:
            return CONSTANTS['ROULETTE']['PAYOUT_DOUZINE_25_36']
        elif bet_type == "colonne 1" and self.winning_number in CONSTANTS['ROULETTE']['COLONNE_1']:
            return CONSTANTS['ROULETTE']['PAYOUT_COLONNE_1']
        elif bet_type == "colonne 2" and self.winning_number in CONSTANTS['ROULETTE']['COLONNE_2']:
            return CONSTANTS['ROULETTE']['PAYOUT_COLONNE_2']
        elif bet_type == "colonne 3" and self.winning_number in CONSTANTS['ROULETTE']['COLONNE_3']:
            return CONSTANTS['ROULETTE']['PAYOUT_COLONNE_3']
        else:
            return 0

    async def update_player_balances(self, results: Dict[int, Tuple[int, int]]):
        try:
            connection = mysql.connector.connect(
                host=HOST,
                user=USER,
                password=PASSWORD,
                database=DATABASE
            )

            cursor = connection.cursor()

            # Début de la transaction
            connection.start_transaction()

            update_query = f"""
                UPDATE {TABLE_USERS} 
                SET {FIELD_CASH} = CASE
                    WHEN {FIELD_USER_ID} = %s THEN {FIELD_CASH} + %s
                    ELSE {FIELD_CASH}
                END
                WHERE {FIELD_USER_ID} IN ({','.join(['%s'] * len(results))})
            """

            # Préparer les données pour la mise à jour
            update_data = []
            user_ids = []
            for user_id, (winning_amount, bet_amount) in results.items():
                update_data.extend([user_id, winning_amount - bet_amount])
                user_ids.append(user_id)

            # Exécuter la mise à jour
            cursor.execute(update_query, update_data + user_ids)

            # Insérer les transactions
            insert_query = f"""
                INSERT INTO {TABLE_TRANSACTIONS} 
                ({FIELD_USER_ID}, {FIELD_AMOUNT}, {FIELD_TYPE}) 
                VALUES (%s, %s, %s)
            """
            transaction_data = [
                (user_id, winning_amount - bet_amount, 'Roulette')
                for user_id, (winning_amount, bet_amount) in results.items()
            ]
            cursor.executemany(insert_query, transaction_data)

            # Valider la transaction
            connection.commit()

            print(f"Successfully updated balances for {len(results)} players.")

        except Error as e:
            print(f"Error updating player balances: {e}")
            connection.rollback()

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    async def send_results(self, results: Dict[int, Tuple[int, int]]):
        channel = self.bot.get_channel(self.channel_id)
        embed = Embed(title="Résultats de la Roulette", color=0x0000ff)
        for user_id, (winning_amount, bet_amount) in results.items():
            user = await self.bot.fetch_user(user_id)
            if winning_amount > 0:
                embed.add_field(name=f"{user.name}", value=f"Gagné: {winning_amount} 🎉", inline=False)
            else:
                embed.add_field(name=f"{user.name}", value=f"Perdu: {bet_amount} 😢", inline=False)
        
        await channel.send(embed=embed)

roulette_sessions = {}

# Menu déroulant pour les types de mises
class BetTypeView(View):
    def __init__(self, session, user_id):
        super().__init__(timeout=60)
        self.session = session
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Choisissez votre type de pari",
        options=[
            discord.SelectOption(label="Rouge", value="rouge", emoji="🔴"),
            discord.SelectOption(label="Noir", value="noir", emoji="⚫"),
            discord.SelectOption(label="Pair", value="pair", emoji="2️⃣"),
            discord.SelectOption(label="Impair", value="impair", emoji="1️⃣"),
            discord.SelectOption(label="1-18", value="1-18", emoji="⬇️"),
            discord.SelectOption(label="19-36", value="19-36", emoji="⬆️"),
            discord.SelectOption(label="Douzaine 1-12", value="douzaine 1-12", emoji="1️⃣"),
            discord.SelectOption(label="Douzaine 13-24", value="douzaine 13-24", emoji=" 2️⃣"),
            discord.SelectOption(label="Douzaine 25-36", value="douzaine 25-36", emoji="3️⃣"),
            discord.SelectOption(label="Colonne 1", value="colonne 1", emoji="🏛️"),
            discord.SelectOption(label="Colonne 2", value="colonne 2", emoji="🏛️"),
            discord.SelectOption(label="Colonne 3", value="colonne 3", emoji="🏛️"),
        ]
    )

    async def select_callback(self, interaction: Interaction, select: Select):
        bet_type = select.values[0]
        self.session.bets[self.user_id] = bet_type

        if bet_type == "numero":
            await interaction.response.send_message("Veuillez entrer un numéro entre 0 et 36:", ephemeral=True)
            
            def check(m):
                return m.author.id == self.user_id and m.channel.id == interaction.channel.id and m.content.isdigit() and 0 <= int(m.content) <= 36

            try:
                msg = await bot.wait_for('message', check=check, timeout=30.0)
                self.session.bets[self.user_id] = int(msg.content)
            except asyncio.TimeoutError:
                await interaction.followup.send("Temps écoulé. Pari annulé.", ephemeral=True)
                del self.session.players[self.user_id]
                return
        else:
            await interaction.response.send_message(f"Vous avez choisi de parier sur: {bet_type}", ephemeral=True)

        # Si tous les joueurs ont parié, lancer la roulette
        if len(self.session.bets) == len(self.session.players):
            await spin_wheel(interaction, self.session)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: Interaction, button: Button):
        del self.session.players[self.user_id]
        await interaction.response.send_message("Pari annulé.", ephemeral=True)

class Roulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}  # {channel_id: RouletteSession}

    @bot.tree.command(name="roulette", description="Rejoindre une partie de roulette")
    async def roulette(self, interaction: Interaction, amount: int):
        user_id = interaction.user.id

        # Vérification de l'inscription
        if not is_registered(user_id):
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register` avant de jouer à la roulette.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return

        # Vérification de la validité du montant parié
        if amount <= 0:
            embed = discord.Embed(title="Erreur", description="Le montant du pari doit être supérieur à 0.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return

        # Récupération du solde de l'utilisateur
        query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
        data = fetch_data(query, (user_id,))
        if not data:
            embed = discord.Embed(title="Erreur", description="Impossible de récupérer vos données. Veuillez réessayer plus tard.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return
        
        # Vérification du solde de l'utilisateur
        cash = data[0][0]
        if cash < amount:
            embed = discord.Embed(title="Erreur", description=f"Vous n'avez pas assez d'argent pour ce pari. Votre solde actuel est de {cash} {COIN_EMOJI}.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return

        # Vérification  de la présence d'une partie en cours
        if user_id in roulette_sessions:
            embed = Embed(title="Erreur", description="Vous avez déjà une partie de roulette en cours.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
            return

        # Création d'une nouvelle session ou participation à une session existante
        if not roulette_sessions:
            roulette_sessions[user_id] = RouletteSession(user_id)
            embed = Embed(title="Roulette", description=f"Vous avez créé une nouvelle partie de roulette. Utilisez `/roulette_start` pour commencer la partie.", color=0x0000ff)
        else:
            host_id = next(iter(roulette_sessions))
            session = roulette_sessions[host_id]
            if session.is_active:
                embed = Embed(title="Erreur", description="Une partie est déjà en cours. Veuillez attendre la prochaine partie.", color=0xff0000)
                await interaction.response.send_message(embed=embed)
                return
            session.players[user_id] = amount
            embed = Embed(title="Roulette", description=f"Vous avez rejoint la partie de roulette. Attendez que l'hôte démarre la partie.", color=0x0000ff)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="roulette_start", description="Démarrer la partie de roulette")
    async def roulette_start(self, interaction: Interaction):
        user_id = interaction.user.id

        # Vérification des permission d'hôte de l'utilisateur
        if user_id not in roulette_sessions:
            embed = Embed(title="Erreur", description="Vous n'êtes pas l'hôte d'une partie de roulette.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
            return

        # Vérification de l'état de la session
        session = roulette_sessions[user_id]
        if session.is_active:
            embed = Embed(title="Erreur", description="La partie est déjà en cours.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
            return

        # Commencement de la session
        session.is_active = True
        embed = Embed(title="Roulette", description="La partie de roulette commence! Choisissez votre type de pari.", color=0x0000ff)
        await interaction.response.send_message(embed=embed)

        # Demander les paris à chaque joueur
        for player_id in session.players:
            player = await self.bot.fetch_user(player_id)
            view = BetTypeView(session, player_id)
            embed = Embed(title="🎰  Roulette", description="Choisissez votre type de pari:", color=0x0000ff)
            await player.send(embed=embed, view=view)

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

class BlackJackView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.gray)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        
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
    """ if user_id in blackjack_players:
        embed = discord.Embed(title="Erreur", description=f"Vous jouez deja une partie de Black Jack", color=color_red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return """

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



async def setup(bot):
    await bot.add_cog(Roulette(bot))

if __name__ == "__main__":
    asyncio.run(setup(bot))
    bot.run(TOKEN)
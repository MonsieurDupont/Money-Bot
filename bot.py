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
from discord import app_commands
from typing import Literal
from datetime import datetime

# Chargement des variables d'environnement
load_dotenv()

# Chargement du fichier .ini 
commandsconfig = configparser.ConfigParser()
commandsconfig.read('settings.ini')

# Chargement des fichiers JSON
with open('commandphrases.json') as file:
    workdata = json.load(file)
    workphrases = workdata["workphrases"]

# Définition des constantes
TOKEN = os.getenv("TOKEN")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GUILD_ID = os.getenv("GUILD_ID")
APPLICATION_ID = os.getenv("APPLICATION_ID")
CoinEmoji = "<:AploucheCoin:1286080674046152724>"

if 'Constants' in commandsconfig:
    min_work_pay = commandsconfig.getint('Constants', 'min_pay')
    max_work_pay = commandsconfig.getint('Constants', 'max_pay')
    work_cooldown_time = commandsconfig.getint('Constants', 'work_cooldown')
    print(f"Succesfully read {len(commandsconfig.options('Constants'))} 'Constants' in 'settings.ini.'")
else:
    logging.ERROR("Cannot find 'Constants' in settings.ini")

# Définition des couleurs
color_green = 0x98d444
color_blue = 0x448ad4
color_red = 0xd44e44

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
        # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
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
            embed = discord.Embed(title="Succès", description=f"Vous êtes maintenant inscrit, {interaction.user.mention}. Vous avez reçu 1000 {CoinEmoji} en cash.", color=color_green)
            embed.add_field(name="Prochaines étapes", value="Vous pouvez maintenant utiliser les commandes `/balance`, `/deposit`, `/withdraw` et `/transaction`.", inline=False)
            embed.add_field(name="Aide", value="Si vous avez des questions, n'hésitez pas à demander.", inline=False)
            embed.set_footer(text="Bienvenue dans notre communauté !")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description=f"Erreur lors de l'inscription, {interaction.user.mention}.", color=color_red)
            embed.add_field(name="Raison", value="Veuillez réessayer plus tard.", inline=False)
            # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
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
    embed.add_field(name="Cash", value=f"{cash} {CoinEmoji}", inline=False)
    embed.add_field(name="Banque", value=f"{bank} {CoinEmoji}", inline=False)
    embed.add_field(name="Total", value=f"{total} {CoinEmoji}", inline=False)
    embed.add_field(name="Revenus", value=f"{total_revenus} {CoinEmoji}", inline=False)
    embed.add_field(name="Dépenses", value=f"{total_depenses} {CoinEmoji}", inline=False)
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
    foo = await bot.fetch_user(user_id)
    embed = discord.Embed(title=f"Solde de {foo.name}", description=f"**Cash** : {cash:,} {CoinEmoji}\n**Banque** : {bank:,} {CoinEmoji}\n**Total** : {total:,} {CoinEmoji}", color=color_blue)
    if total <= 0:
        embed.add_field(name="", value="Wesh c'est la hess la ", inline=False)
    # embed.add_field(name="Aide", value="Pour voir les commandes disponibles, tapez `/help`.", inline=False)
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
        embed = discord.Embed(title="Succès", description=f"Vous avez déposé {amount} {CoinEmoji} avec succès.", color=color_green)
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
        embed = discord.Embed(title="Succès", description=f"Vous avez retiré {amount} {CoinEmoji} avec succès.", color=color_green)
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
        embed = discord.Embed(title="Vol réussi", description=f"Vous avez volé {amount :,} {CoinEmoji} à {user.mention}.", color=color_green)
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
            embed = discord.Embed(title="Succès", description=f"Vous avez envoyé {amount} {CoinEmoji} avec succès.", color=color_green)
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
            embed.add_field(name=f"#{i}", value=f"<@{user.id}> : **{total:,}** {CoinEmoji}", inline=False)  
        else:
            embed.add_field(name=f"", value=f"**{i}** • <@{user.id}> : **{total:,}** {CoinEmoji}", inline=False)
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
        embed.add_field(name="", value=f"**{i}** : {amount:,} {CoinEmoji} | {transaction_type}", inline=False)
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
        embed = discord.Embed(title="", description=f"{amount} {CoinEmoji} ont étés ajouté a votre compte", color=color_green)
    else:
        embed = discord.Embed(title="", description=f"{amount} {CoinEmoji} ont étés ajouté au compte de <@{user.id}>", color=color_green)
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
        embed = discord.Embed(title="", description=f"{amount} {CoinEmoji} ont étés retirés a votre compte", color=color_green)
    else:
        embed = discord.Embed(title="", description=f"{amount} {CoinEmoji} ont étés retirés au compte de <@{user.id}>", color=color_green)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Commande pour travailler
@bot.tree.command(name="work", description="Travailler")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return


    if work_cooldown_time <= 0:
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
        if time_diff < work_cooldown_time:
            embed = discord.Embed(title="Erreur", description=f"Vous devez attendre {work_cooldown_time - int(time_diff)} secondes avant de travailler à nouveau.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return
    biased_pay = min_work_pay + (max_work_pay - min_work_pay) * (random.random() ** 2)
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

    embed = discord.Embed(title=(f"{interaction.user.display_name}"), description=random_phrase.format(pay=pay) + CoinEmoji, color=color_green)
    await interaction.response.send_message(embed=embed)


# GAMES

# Commande pour jouer à la roulette
@bot.tree.command(name="roulette", description="Jouer à la roulette")
@app_commands.describe(amount="Montant à miser", bet="Type de mise (par exemple, 'rouge', 'noir', 'pair', 'impair', '1', '2', ...)")
async def roulette(interaction: discord.Interaction, amount: int, bet: str):
    user_id = interaction.user.id

    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant doit être supérieur à 0.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user_id,))
    user_cash = data[0][0] if data and data[0] else 0

    if user_cash < amount:
        embed = discord.Embed(title="Erreur", description=f"Vous n'avez pas assez de cash pour participer à la roulette. Votre solde : {user_cash} {CoinEmoji}", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    winning_conditions = {
        "rouge": lambda x: x == "rouge",
        "noir": lambda x: x == "noir",
        "pair": lambda x: x % 2 == 0,
        "impair": lambda x: x % 2 != 0,
        "1-18": lambda x: 1 <= x <= 18,
        "19-36": lambda x: 19 <= x <= 36,
        "1": lambda x: x == 1,
        "2": lambda x: x == 2,
        "3": lambda x: x == 3,
        "4": lambda x: x == 4,
        "5": lambda x: x == 5,
        "6": lambda x: x == 6,
        "7": lambda x: x == 7,
        "8": lambda x: x == 8,
        "9": lambda x: x == 9,
        "10": lambda x: x == 10,
        "11": lambda x: x == 11,
        "12": lambda x: x == 12,
        "13": lambda x: x == 13,
        "14": lambda x: x == 14,
        "15": lambda x: x == 15,
        "16": lambda x: x == 16,
        "17": lambda x: x == 17,
        "18": lambda x: x == 18,
        "19": lambda x: x == 19,
        "20": lambda x: x == 20,
        "21": lambda x: x == 21,
        "22": lambda x: x == 22,
        "23": lambda x: x == 23,
        "24": lambda x: x == 24,
        "25": lambda x: x == 25,
        "26": lambda x: x == 26,
        "27": lambda x: x == 27,
        "28": lambda x: x == 28,
        "29": lambda x: x == 29,
        "30": lambda x: x == 30,
        "31": lambda x: x == 31,
        "32": lambda x: x == 32,
        "33": lambda x: x == 33,
        "34": lambda x: x == 34,
        "35": lambda x: x == 35,
        "36": lambda x: x == 36,
        "douzaine 1-12": lambda x: 1 <= x <= 12,
        "douzaine 13-24": lambda x: 13 <= x <= 24,
        " douzaine 25-36": lambda x: 25 <= x <= 36,
        "colonne 1": lambda x: x in [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
        "colonne 2": lambda x: x in [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
        "colonne 3": lambda x: x in [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
        "carré 1": lambda x: x in [1, 4, 7, 10, 13, 16, 19, 22, 25],
        "carré 2": lambda x: x in [2, 5, 8, 11, 14, 17, 20, 23, 26],
        "carré 3": lambda x: x in [3, 6, 9, 12, 15, 18, 21, 24, 27],
        "sixain 1": lambda x: x in [1, 2, 3, 4, 5, 6],
        "sixain 2": lambda x: x in [7, 8, 9, 10, 11, 12],
        "sixain 3": lambda x: x in [13, 14, 15, 16, 17, 18],
        "sixain 4": lambda x: x in [19, 20, 21, 22, 23, 24],
        "sixain 5": lambda x: x in [25, 26, 27, 28, 29, 30],
        "sixain 6": lambda x: x in [31, 32, 33, 34, 35, 36],
        "transversale 1": lambda x: x in [1, 2, 3],
        "transversale 2": lambda x: x in [4, 5, 6],
        "transversale 3": lambda x: x in [7, 8, 9],
        "transversale 4": lambda x: x in [10, 11, 12],
        "transversale 5": lambda x: x in [13, 14, 15],
        "transversale 6": lambda x: x in [16, 17, 18],
        "transversale 7": lambda x: x in [19, 20, 21],
        "transversale 8": lambda x: x in [22, 23, 24],
        "transversale 9": lambda x: x in [25, 26, 27],
        "transversale 10": lambda x: x in [28, 29, 30],
        "transversale 11": lambda x: x in [31, 32, 33],
        "transversale 12": lambda x: x in [34, 35, 36]
    }

    if bet not in winning_conditions:
        embed = discord.Embed(title="Erreur", description="Type de mise invalide.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    # Génération du résultat aléatoire
    winning_number = random.randint(0, 36)
    winning_color = "rouge" if winning_number in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36] else "noir"
    winning_parity = "pair" if winning_number % 2 == 0 else "impair"
    winning_range = "1-18" if winning_number <= 18 else "19-36"
    winning_douzaine = "1-12" if winning_number <= 12 else "13-24" if winning_number <= 24 else "25-36"
    winning_colonne = "1" if winning_number in [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34] else "2" if winning_number in [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35] else "3"
    winning_square = [(1, 4, 7, 10, 13, 16, 19, 22, 25), (2, 5, 8, 11, 14, 17, 20, 23, 26), (3, 6, 9, 12, 15, 18, 21, 24, 27), (28, 31, 34, 4, 7, 10), (29, 32, 35, 5, 8, 11), (30, 33, 36, 6, 9, 12)][(winning_number - 1) // 3]
    winning_sixain = [(1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12), (13, 14, 15, 16, 17, 18), (19, 20, 21, 22, 23, 24), (25, 26, 27, 28, 29, 30), (31, 32, 33, 34, 35, 36)][(winning_number - 1) // 6]
    winning_transversale = [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12), (13, 14, 15), (16, 17, 18), (19, 20, 21), (22, 23, 24), (25, 26, 27), (28, 29, 30), (31, 32, 33), (34, 35, 36)][(winning_number - 1) // 3]

    if winning_conditions[bet](winning_number):
        if bet.isdigit():
            winnings = amount * 35
        elif bet in ["rouge", "noir", "pair", "impair", "1-18", "19-36"]:
            winnings = amount
        elif bet in ["douzaine 1-12", "douzaine 13-24", "douzaine 25-36", "colonne 1", "colonne 2", "colonne 3"]:
            winnings = amount * 2
        elif bet in ["carré 1", "carré 2", "carré 3"]:
            winnings = amount * 8
        elif bet in ["sixain 1", "sixain 2", "sixain 3", "sixain 4", "sixain 5", "sixain 6"]:
            winnings = amount * 5
        elif bet in ["transversale 1", "transversale 2", "transversale 3", "transversale 4", "transversale 5", "transversale 6", "transversale 7", "transversale 8", "transversale 9", "transversale 10", "transversale 11", "transversale 12"]:
            winnings = amount * 11
    else:
        winnings = -amount

    # Mise à jour du solde de l'utilisateur
    query = f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_USER_ID} = %s"
    execute_query(query, (winnings, user_id))

    # Envoi du résultat
    embed = discord.Embed(title="Résultat de la roulette", description=f"Le numéro gagnant est {winning_number} {winning_color}. Vous avez {'gagné' if winnings > 0 else 'perdu'} {abs(winnings)} {CoinEmoji}.", color=color_green if winnings > 0 else color_red)
    await interaction.response.send_message(embed=embed)

from treys import Card, Evaluator, Deck
@app_commands.describe(mise="Mise de départ")
@bot.tree.command(name="poker", description="Jouer au poker")
async def poker(interaction: discord.Interaction, mise: int):
    user_id = interaction.user.id
    deck = Deck()
    board = deck.draw(5)
    p1_deck = deck.draw(2)
    p2 = deck.draw(2)
    p1_cards = [Card.int_to_pretty_str(card) for card in p1_deck]
    embed = discord.Embed(title="Poker", description=f"Vos cartes : {p1_cards}", color=color_green)
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    bot.run(TOKEN)
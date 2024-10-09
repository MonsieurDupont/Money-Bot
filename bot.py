# Importation des bibliothèques nécessaires
import os
import logging
from dotenv import load_dotenv
import mysql.connector
import discord
import random
import json
from discord.ext import commands
import asyncio

# Chargement des variables d'environnement
load_dotenv()

# Chargement des fichiers JSON
with open('workphrases.json', 'r', encoding='utf-8') as file:
    workphrases = json.load(file)

# Définition des constantes
TOKEN = os.getenv("TOKEN")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GUILD_ID = os.getenv("GUILD_ID")
APPLICATION_ID = os.getenv("APPLICATION_ID")

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
            embed = discord.Embed(title="Succès", description=f"Vous êtes maintenant inscrit, {interaction.user.mention}. Vous avez reçu 1000 <:AploucheCoin:1286080674046152724> en cash.", color=color_green)
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
        # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
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
        # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    cash, bank, total_revenus, total_depenses = data[0]
    if cash is None or bank is None or total_revenus is None or total_depenses is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    total = cash + bank
    moyenne_depenses = total_depenses / (total_revenus + abs(total_depenses)) if total_revenus + abs(total_depenses) > 0 else 0
    moyenne_revenus = total_revenus / (total_revenus + abs(total_depenses)) if total_revenus + abs(total_depenses) > 0 else 0

    embed = discord.Embed(title="Statistiques", description=f"Voici vos statistiques, {interaction.user.mention}.", color=color_green)
    embed.add_field(name="Cash", value=f"{cash} <:AploucheCoin:1286080674046152724>", inline=False)
    embed.add_field(name="Banque", value=f"{bank} <:AploucheCoin:1286080674046152724>", inline=False)
    embed.add_field(name="Total", value=f"{total} <:AploucheCoin:1286080674046152724>", inline=False)
    embed.add_field(name="Revenus", value=f"{total_revenus} <:AploucheCoin:1286080674046152724>", inline=False)
    embed.add_field(name="Dépenses", value=f"{total_depenses} <:AploucheCoin:1286080674046152724>", inline=False)
    embed.add_field(name="Moyenne des dépenses", value=f"{moyenne_depenses * 100:.2f}%", inline=False)
    embed.add_field(name="Moyenne des revenus", value=f"{moyenne_revenus * 100:.2f}%", inline=False)
    # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
    await interaction.response.send_message(embed=embed)

# Commande pour vérifier son solde
@bot.tree.command(name="balance", description="Vérifier votre solde")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
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

    cash, bank = data[0]
    if cash is None or bank is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    total = cash + bank
    embed = discord.Embed(title="Solde", description=f"**Cash** : {cash:,} <:AploucheCoin:1286080674046152724>\n**Banque** : {bank:,} <:AploucheCoin:1286080674046152724>\n**Total** : {total:,} <:AploucheCoin:1286080674046152724>", color=color_blue)
    embed.add_field(name="Aide", value="Pour voir les commandes disponibles, tapez `/help`.", inline=False)
    # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposit", description="Déposer de l'argent")
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant doit être supérieur à 0.", color=color_red)
        # mbed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
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
        # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander .")
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
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent pour déposer.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

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
        embed = discord.Embed(title="Succès", description=f"Vous avez déposé {amount} <:AploucheCoin:1286080674046152724> avec succès.", color=color_green)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Erreur", description="Erreur lors du dépôt.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="withdraw", description="Retirer de l'argent")
async def withdraw(interaction: discord.Interaction, amount: int):
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
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas de données.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    bank = data[0][0]
    if bank is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération de vos données.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
        return

    if bank < amount:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent pour retirer.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
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
        embed = discord.Embed(title="Succès", description=f"Vous avez retiré {amount} <:AploucheCoin:1286080674046152724> avec succès.", color=color_green)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Erreur", description="Erreur lors du retrait.", color=color_red)
        # # embed.set_footer(text="Si vous avez des questions, n'hésitez pas à demander.")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="steal", description="Volé de l'argent à un utilisateur")
async def steal(interaction: discord.Interaction, user: discord.Member, amount: int):
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

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant à voler doit être positif.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
    data = fetch_data(query, (user.id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de l'utilisateur ciblé.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="L'utilisateur ciblé n'a pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    cash = data[0][0]
    if cash is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de l'utilisateur ciblé.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if cash < amount:
        embed = discord.Embed(title="Erreur", description="L'utilisateur ciblé n'a pas assez d'argent pour être volé.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_USER_ID} = %s", (amount, user.id))
    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_USER_ID} = %s", (amount, user_id))
    embed = discord.Embed(title="Vol réussi", description=f"Vous avez volé {amount :,} <:AploucheCoin:1286080674046152724> à {user.mention}.", color=color_green)
    await interaction.response.send_message(embed=embed)

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
            embed = discord.Embed(title="Succès", description=f"Vous avez envoyé {amount} <:AploucheCoin:1286080674046152724> avec succès.", color=color_green)
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
            embed.add_field(name=f"#{i}", value=f"<@{user.id}> - **{total:,}** <:AploucheCoin:1286080674046152724>", inline=False)  
        else:
            embed.add_field(name=f"", value=f"**{i}** • <@{user.id}> - **{total:,}** <:AploucheCoin:1286080674046152724>", inline=False)
    # embed.set_footer(text="Note : Ce classement est mis à jour en temps réel.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="transaction_history", description="Historique des transactions")
async def transaction_history(interaction: discord.Interaction):
    user_id = interaction.user.id
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

    embed = discord.Embed(title="Historique des transactions", description="Voici l'historique de vos transactions :", color=color_blue)
    embed.add_field(name="**Transaction**", value="**Montant** | **Type**", inline=False)
    for i, (transaction_id, amount, transaction_type) in enumerate(transactions, start=1):
        embed.add_field(name=f"#{i}", value=f"{amount:,} <:AploucheCoin:1286080674046152724> | {transaction_type}", inline=False)
    # embed.set_footer(text="Note : Ce classement est mis à jour en temps réel.")
    await interaction.response.send_message(embed=embed)

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
            u.{FIELD_USER_ID}
        FROM 
            {TABLE_USERS} u
        WHERE 
            u.{FIELD_USER_ID} = %s
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


@bot.tree.command(name="work", description="Travailler")
async def work(interaction: discord.Interaction, user: discord.Member):
    random_key = random.choice(list(workphrases.keys()))
    pay = random.randint(100, 2500)   # Nombre aleatoire definissant la paye

    embed = discord.Embed(description=random_key.replace("{pay}", str(pay)))


async def main():
    await bot.start(TOKEN)


asyncio.run(main())
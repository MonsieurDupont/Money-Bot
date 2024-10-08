import os
import logging
from dotenv import load_dotenv
import mysql.connector
import discord
from discord.ext import commands
import asyncio

# Chargement des variables d'environnement
load_dotenv()

# Définition des constantes
TOKEN = os.getenv("TOKEN")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GUILD_ID = os.getenv("GUILD_ID")
APPLICATION_ID = os.getenv("APPLICATION_ID")

# Couleurs
color_green = 0x98d444
color_blue = 0x448ad4
color_red = 0xd44e44

# Définition des tables et des champs
TABLE_USERS = "users"
TABLE_TRANSACTIONS = "transactions"
FIELD_ID = "id"
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
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        logging.error("Erreur de requête SQL : {}".format(err))
        return None

# Fonction pour récupérer des données de la base de données
def fetch_data(query, params=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except mysql.connector.Error as err:
        logging.error("Erreur de requête SQL : {}".format(err))
        return None

# Fonction pour vérifier si un utilisateur est inscrit
def is_registered(user_id):
    query = f"SELECT * FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    data = fetch_data(query, (user_id,))
    return len(data) > 0

# Commande pour s'inscrire
@bot.tree.command(name="register", description="S'inscrire")
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    if is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous êtes déjà inscrit.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    execute_query(f"INSERT INTO {TABLE_USERS} ({FIELD_ID}, {FIELD_CASH}, {FIELD_BANK}) VALUES (%s, %s, %s)", (user_id, 0, 0))
    embed = discord.Embed(title="Inscription réussie", description="Vous êtes maintenant inscrit.", color=color_green)
    await interaction.response.send_message(embed=embed)

# Commande pour vérifier son solde
@bot.tree.command(name="balance", description="Vérifier votre solde")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
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
    embed = discord.Embed(title="Solde", description=f"**Cash** : {cash:,} <:AploucheCoin:1286080674046152724>\n**Banque** : {bank:,} <:AploucheCoin:1286080674046152724>\n**Total** : {total:,} <:AploucheCoin:1286080674046152724>", color=color_blue)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposit", description="Déposer de l'argent dans la banque")
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant à déposer doit être positif.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
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

    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s, {FIELD_BANK} = {FIELD_BANK} + %s WHERE {FIELD_ID} = %s", (amount, amount, user_id))
    embed = discord.Embed(title="Dépôt réussi", description=f"Vous avez déposé {amount} <:AploucheCoin:1286080674046152724> dans votre banque.", color=color_green)
    await interaction.response.send_message(embed=embed)
    add_transaction(user_id, amount, "Dépôt")

@bot.tree.command(name="withdraw", description="Retirer de l'argent de la banque")
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant à retirer doit être positif.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
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
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent dans votre banque pour retirer.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_BANK} = {FIELD_BANK} - %s, {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, amount, user_id))
    embed = discord.Embed(title="Retrait réussi", description=f"Vous avez retiré {amount} <:AploucheCoin:1286080674046152724> de votre banque.", color=color_green)
    await interaction.response.send_message(embed=embed)
    add_transaction(user_id, amount, "Retrait")

@bot.tree.command(name="steal", description="Vol de l'argent d'un autre utilisateur")
async def steal(interaction: discord.Interaction, user: discord.Member):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if user == interaction.user:
        embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas voler votre propre argent.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
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

    if cash <= 0:
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent pour voler.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    data = fetch_data(query, (user.id,))
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de la victime.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="La victime n 'a pas de données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    victim_cash = data[0][0]
    if victim_cash is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données de la victime.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if victim_cash <= 0:
        embed = discord.Embed(title="Erreur", description="La victime n'a pas assez d'argent pour voler.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    amount = random.randint(1, victim_cash)
    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, user.id))
    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, user_id))
    embed = discord.Embed(title="Vol réussi", description=f"Vous avez volé {amount} <:AploucheCoin:1286080674046152724> à {user.mention}.", color=color_green)
    await interaction.response.send_message(embed=embed)
    add_transaction(user_id, amount, "Vol")
    add_transaction(user.id, -amount, "Vol")

@bot.tree.command(name="transaction", description="Envoi de l'argent à un autre utilisateur")
async def transaction(interaction: discord.Interaction, user: discord.Member, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if user == interaction.user:
        embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas envoyer de l'argent à vous-même.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if amount <= 0:
        embed = discord.Embed(title="Erreur", description="Le montant à envoyer doit être positif.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
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
        embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent pour envoyer.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, user_id))
    execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, user.id))
    embed = discord.Embed(title="Transaction réussie", description=f"Vous avez envoyé {amount} <:AploucheCoin:1286080674046152724> à {user.mention}.", color=color_green)
    await interaction.response.send_message(embed=embed)
    add_transaction(user_id, -amount, "Transaction")
    add_transaction(user.id, amount, "Transaction")

@bot.tree.command(name="leaderboard", description="Classement des utilisateurs")
async def leaderboard(interaction: discord.Interaction):
    query = f"SELECT {FIELD_ID}, {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} ORDER BY {FIELD_CASH} + {FIELD_BANK} DESC"
    data = fetch_data(query)
    if data is None:
        embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    if len(data) == 0:
        embed = discord.Embed(title="Erreur", description="Aucune donnée.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    leaderboard = []
    for row in data:
        user_id, cash, bank = row
        if cash is None or bank is None:
            continue
        leaderboard.append((user_id, cash + bank))

    embed = discord.Embed(title="Classement des utilisateurs", description="", color=color_blue)
    for i, (user_id, total) in enumerate(leaderboard):
        user = bot.get_user(user_id)
        if user is None:
            continue
        embed.add_field(name=f"{i+1}. {user.name}", value=f"Total : {total:,} <:AploucheCoin:1286080674046152724>", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="transaction_history", description="Historique des transactions")
async def transaction_history(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    query = f"SELECT {FIELD_ID}, {FIELD_AMOUNT}, {FIELD_TYPE} FROM {TABLE_TRANSACTIONS} WHERE {FIELD_USER_ID} = %s ORDER BY {FIELD_ID} DESC"
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

    embed = discord.Embed(title="Historique des transactions", description="", color=color_blue)
    for transaction_id, amount, transaction_type in transactions:
        embed.add_field(name=f"Transaction {transaction_id}", value=f"Montant : {amount} <:AploucheCoin:1286080674046152724>\nType : {transaction_type}", inline=False)
    await interaction.response.send_message(embed=embed)

# Commande pour supprimer un compte
class DeleteAccView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, Button: discord.ui.Button, user: discord.user):
        execute_query(f"DELETE FROM {TABLE_USERS} WHERE {FIELD_ID} = %s", (user.id,))
        execute_query(f"DELETE FROM {TABLE_TRANSACTIONS} WHERE {FIELD_ID} = %s", (user.id,))
        await interaction.response.send_message(content=f"Compte de {user.mention} supprimé avec succès.")
    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="Annuler")

@bot.tree.command(name="delete_account", description="Supprimer votre compte")
@commands.has_permissions(administrator=True)
async def delete_account(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
        await interaction.response.send_message(embed=embed)
        return

    confirm = await interaction.response.send_message("Êtes-vous sûr de vouloir supprimer votre compte ? (oui/non)")
    def check(msg):
        return msg.author == interaction.user and msg.channel == interaction.channel
    msg = await bot.wait_for("message", check=check)
    if msg.content.lower() == "oui":
        execute_query(f"DELETE FROM {TABLE_USERS} WHERE {FIELD_ID} = %s", (user_id,))
        execute_query(f"DELETE FROM {TABLE_TRANSACTIONS} WHERE {FIELD_USER_ID} = %s", (user_id,))
        embed = discord.Embed(title="Compte supprimé", description="Votre compte a été supprimé.", color=color_green)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Erreur", description="Suppression annulée.", color=color_red)
        await interaction.response.send_message(embed=embed)

# JEUX

    # BLACKJACK
# Lancement du bot

async def main():
    await bot.start(TOKEN)

asyncio.run(main())
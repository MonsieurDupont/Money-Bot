import discord
from discord.ext import commands
import mysql.connector
import asyncio
import random
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("token")

# Constantes
TABLE_USERS = "users"
TABLE_TRANSACTIONS = "transactions"
FIELD_ID = "id"
FIELD_CASH = "cash"
FIELD_BANK = "bank"
FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_AMOUNT = "amount"

# Fonction pour se connecter à la base de données
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="username",
            password="password",
            database="database"
        )
    except mysql.connector.Error as err:
        print("Erreur de connexion à la base de données : {}".format(err))
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
        print("Erreur de requête SQL : {}".format(err))
        return None

# Fonction pour récupérer des données de la base de données
def fetch_data(query, params=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print("Erreur de requête SQL : {}".format(err))
        return None

# Fonction pour ajouter une transaction
def add_transaction(user_id, amount, type):
    query = f"INSERT INTO {TABLE_TRANSACTIONS} ({FIELD_ID}, {FIELD_AMOUNT}, {FIELD_TYPE}) VALUES (%s, %s, %s)"
    return execute_query(query, (user_id, amount, type))

# Fonction pour vérifier si un utilisateur est enregistré
def is_registered(user_id):
    query = f"SELECT COUNT(*) FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    result = fetch_data(query, (user_id,))
    return result[0][0] > 0

# Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Commande pour s'inscrire
@bot.tree.command(name="register", description="S'inscrire")
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    if is_registered(user_id):
        await interaction.response.send_message("Vous êtes déjà inscrit !", ephemeral=True)
        return
    
    execute_query(f"INSERT INTO {TABLE_USERS} ({FIELD_ID}, {FIELD_CASH}, {FIELD_BANK}) VALUES (%s, 0, 1000)", (user_id,))
    await interaction.response.send_message("Vous êtes désormais inscrit ! Vous avez reçu 1000 <:AploucheCoin:1286080674046152724> en banque.", ephemeral=True)

# Commande pour vérifier son solde
@bot.tree.command(name="balance", description="Vérifier son solde")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_registered(user_id):
        await interaction.response.send_message("Vous devez vous inscrire avec `/register`.", ephemeral=True)
        return
    
    query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    data = fetch_data(query, (user_id,))
    if data:
        cash, bank = data[0]
        total = cash + bank
        await interaction.response.send_message(f"Votre solde actuel : {cash} <:AploucheCoin:1286080674046152724> en cash, {bank} <:AploucheCoin:1286080674046152724> en banque, pour un total de {total} <:AploucheCoin:1286080674046152724>.", ephemeral=True)
    else:
        await interaction.response.send_message("Erreur lors de la récupération de vos données.", ephemeral=True)

# Commande pour voler un utilisateur
@bot.tree.command(name="steal", description="Volé un utilisateur")
async def steal(interaction: discord.Interaction, user: discord.User):
    robber_id = interaction.user.id
    victim_id = user.id
    if not is_registered(robber_id) or not is_registered(victim_id):
        await interaction.response.send_message("Vous devez vous inscrire avec `/register`.", ephemeral=True)
        return
    
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    robber_cash = fetch_data(query, (robber_id,))[0][0]
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    victim_cash = fetch_data(query, (victim_id,))[0][0]
    
    # Calcul de la probabilité de réussite
    if victim_cash <= robber_cash:
        probability = 0.1
    else:
        probability = victim_cash / (victim_cash + robber_cash)
    
    if random.random() < probability:
        amount = int(victim_cash * random.uniform(0.1, 0.3))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, victim_id))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, robber_id))
        await interaction.response.send_message(f"<@{robber_id}> a volé {amount} <:AploucheCoin:1286080674046152724> à <@{victim_id}> !", ephemeral=True)
        add_transaction(robber_id, amount, "Vol")
        add_transaction(victim_id, -amount, "Vol")
    else:
        loss = int(robber_cash * (1 - probability))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (loss, robber_id))
        await interaction.response.send_message(f"<@{robber_id}> a échoué à voler <@{victim_id}> et a perdu {loss} <:AploucheCoin:1286080674046152724> !", ephemeral=True)
        add_transaction(robber_id, -loss, "Échec de vol")

# Commande pour envoyer de l'argent à un utilisateur
@bot.tree.command(name="transaction", description="Envoyer de l'argent à un utilisateur")
async def transaction(interaction: discord.Interaction, user: discord.User, amount: int):
    sender_id = interaction.user.id
    receiver_id = user.id
    if not is_registered(sender_id) or not is_registered(receiver_id):
        await interaction.response.send_message("Vous devez vous inscrire avec `/register`.", ephemeral=True)
        return
    
    query = f"SELECT {FIELD_CASH} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    sender_cash = fetch_data(query, (sender_id,))[0][0]
    if sender_cash >= amount:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_ID} = %s", (amount, sender_id))
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, receiver_id))
        await interaction.response.send_message(f"<@{sender_id}> a envoyé {amount} <:AploucheCoin:1286080674046152724> à <@{receiver_id}>.", ephemeral=True)
        add_transaction(sender_id, -amount, "Envoi")
        add_transaction(receiver_id, amount, "Réception")
    else:
        await interaction.response.send_message("Vous n'avez pas assez d'argent.", ephemeral=True)

# Commande pour retirer de l'argent de la banque
@bot.tree.command(name="withdraw", description="Retirer de l'argent de la banque")
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    if not is_registered(user_id):
        await interaction.response.send_message("Vous devez vous inscrire avec `/register`.", ephemeral=True)
        return
    
    query = f"SELECT {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_ID} = %s"
    bank = fetch_data(query, (user_id,))[0][0]
    if bank >= amount:
        execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_BANK} = {FIELD_BANK} - %s, {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_ID} = %s", (amount, amount, user_id))
        await interaction.response.send_message(f"<@{user_id}> a retiré {amount} <:AploucheCoin:1286080674046152724> de sa banque.", ephemeral=True)
        add_transaction(user_id, -amount, "Retrait")
    else:
        await interaction.response.send_message("Vous n'avez pas assez d'argent en banque.", ephemeral=True)

# Commande pour afficher le leaderboard
@bot.tree.command(name="leaderboard", description="Afficher le leaderboard")
async def leaderboard(interaction: discord.Interaction):
    try:
        query = f"SELECT {FIELD_ID}, {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} ORDER BY {FIELD_CASH} + {FIELD_BANK} DESC"
        data = fetch_data(query)
        if data:
            embed = discord.Embed(title="Leaderboard", description="Voici le leaderboard des utilisateurs les plus riches :", color=0x00ff00)
            for i, (user_id, cash, bank) in enumerate(data):
                user = await bot.fetch_user(user_id)
                total = cash + bank
                embed.add_field(name=f"#{i+1}", value=f"{user.mention} : {total} <:AploucheCoin:1286080674046152724>", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Erreur lors de la récupération des données.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Erreur : {str(e)}", ephemeral=True)

# Commande pour afficher l'historique des transactions d'un utilisateur
@bot.tree.command(name="transaction_history", description="Afficher l'historique des transactions d'un utilisateur")
async def transaction_history(interaction: discord.Interaction, user: discord.User = None):
    try:
        if user is None:
            user = interaction.user
        query = f"SELECT {FIELD_AMOUNT}, {FIELD_TYPE}, {FIELD_TIMESTAMP} FROM {TABLE_TRANSACTIONS} WHERE {FIELD_ID} = %s ORDER BY {FIELD_TIMESTAMP} DESC"
        data = fetch_data(query, (user.id,))
        if data:
            embed = discord.Embed(title="Historique des transactions", description=f"Historique des transactions de {user.mention} :", color=0x00ff00)
            for transaction in data:
                embed.add_field(name=f"{transaction[2]}", value=f"{transaction[1]} : {transaction[0]} <:AploucheCoin:1286080674046152724>", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Erreur lors de la récupération des données.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Erreur : {str(e)}", ephemeral=True)


# Commande pour supprimer un compte
@bot.tree.command(name="delete_account", description="Supprimer un compte")
@commands.has_permissions(administrator=True)
async def delete_account(interaction: discord.Interaction, user: discord.User):
    embed = discord.Embed(title="Confirmation de suppression", description=f"Voulez-vous vraiment supprimer le compte de {user.mention} ? Toute donnée sera perdue.", color=0xff0000)
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
        execute_query(f"DELETE FROM {TABLE_USERS} WHERE {FIELD_ID} = %s", (user.id,))
        execute_query(f"DELETE FROM {TABLE_TRANSACTIONS} WHERE {FIELD_ID} = %s", (user.id,))
        await message.edit(content=f"Compte de {user.mention} supprimé avec succès.")
    elif str(reaction.emoji) == "❌":
        await message.edit(content=f"Suppression annulée.")

# Lancement du bot
async def main():
    await bot.start(TOKEN)

asyncio.run(main())
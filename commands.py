import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from settings import *
from database import *
from utils import *
import typing
import logging

print("Début de l'exécution de commands.py")

logger = logging.getLogger(__name__)
workphrases = load_work_data()

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

def setup_commands(bot):
    # Commande pour s'inscrire
    @bot.tree.command(name="register", description="S'inscrire")
    async def register(interaction: discord.Interaction):
        user_id = interaction.user.id
        if is_registered(user_id):
            await interaction.response.send_message("Vous êtes déjà inscrit !", ephemeral=True)
            return
        query = f"INSERT INTO {TABLE_USERS} ({FIELD_USER_ID}, {FIELD_CASH}, {FIELD_BANK}) VALUES (%s, %s, %s)"
        execute_query(query, (user_id, 0, 0))
        await interaction.response.send_message("Vous êtes maintenant inscrit !", ephemeral=True)

    # Commande pour vérifier la solde d'un utilisateur
    @bot.tree.command(name="balance", description="Vérifier votre solde")
    @app_commands.describe(user="L'utilisateur dont vous voulez vérifier le solde (optionnel)")
    async def balance(interaction: discord.Interaction, user: typing.Optional[discord.Member] = None):
        try:
            await interaction.response.defer(ephemeral=True)
            logger.info(f"Commande balance appelée par {interaction.user.id}")

            if user is None:
                user_id = interaction.user.id
                user_name = interaction.user.display_name
            else:
                user_id = user.id
                user_name = user.display_name

            logger.info(f"Vérification du solde pour l'utilisateur {user_id}")

            if not is_registered(user_id):
                embed = discord.Embed(title="Erreur", description=f"{'Vous devez' if user is None else f'{user_name} doit'} vous inscrire avec `/register`.", color=color_red)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            query = f"SELECT {FIELD_CASH}, {FIELD_BANK} FROM {TABLE_USERS} WHERE {FIELD_USER_ID} = %s"
            data = fetch_data(query, (user_id,))

            if data is None or len(data) == 0:
                embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données.", color=color_red)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            cash, bank = data[0]
            if cash is None or bank is None:
                embed = discord.Embed(title="Erreur", description="Erreur lors de la récupération des données.", color=color_red)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            total = cash + bank
            foo = await bot.fetch_user(user_id)
            embed = discord.Embed(title=f"Solde de {foo.name}", color=color_blue)
            embed.add_field(name="Cash", value=f"{cash:,} {CoinEmoji}", inline=False)
            embed.add_field(name="Banque", value=f"{bank:,} {CoinEmoji}", inline=False)
            embed.add_field(name="Total", value=f"{total:,} {CoinEmoji}", inline=False)

            if total < 0:
                embed.add_field(name="", value="Wesh c'est la hess la ", inline=False)

            logger.info(f"Solde récupéré avec succès pour l'utilisateur {user_id}")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.errors.NotFound:
            logger.error(f"L'interaction a expiré avant que nous puissions répondre pour l'utilisateur {interaction.user.id}")
        except Exception as e:
            logger.error(f"Une erreur s'est produite dans la commande balance pour l'utilisateur {interaction.user.id}: {str(e)}")
            await interaction.followup.send("Une erreur s'est produite. Veuillez réessayer plus tard.", ephemeral=True)

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

    # Commande pour afficher les statistiques d'un utilisateur
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

    # Commande pour voler du cash à un utilisateur
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
        
        proba = round( stealer_cash / (victim_cash + stealer_cash )) # Probabilité de réussite
        amount = random.randint(0, victim_cash) 
        print(proba)
        randoma = random.random()
        print(randoma)                       # Montant a voler

        if randoma <= proba:
            execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_USER_ID} = %s", (amount, user.id))
            execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} + %s WHERE {FIELD_USER_ID} = %s", (amount, user_id))
            embed = discord.Embed(title="Vol réussi", description=f"Vous avez volé {amount :,} {CoinEmoji} à {user.mention}.", color=color_green)
            await interaction.response.send_message(embed=embed)
            try:
                add_transaction(user_id, amount, 'Steal')
            except mysql.connector.Error as err:
                embed = discord.Embed(title="Erreur", description="Erreur lors de l'ajout de la transaction.", color=color_red)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        else:
            execute_query(f"UPDATE {TABLE_USERS} SET {FIELD_CASH} = {FIELD_CASH} - %s WHERE {FIELD_USER_ID} = %s", (amount, user_id))
            embed = discord.Embed(title="Vol raté", description=f"Vous avez essayé de voler <@{user.id}> mais vous vous etes fait choper. Vous avez reçu une amende de {amount}  ", color=color_green)

    # Commande pour envoyer de l'argent à un utilisateur
    @bot.tree.command(name="send", description="Envoyer de l'argent")
    async def send(interaction: discord.Interaction, user: discord.Member, amount: int):
        user_id = interaction.user.id
        if not is_registered(user_id):
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return

        if amount <= 0:
            embed = discord.Embed(title="Erreur", description="Le montant doit être supérieur à 0.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return

        if user == interaction.user:
            embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas vous envoyew de l'argent a vous-même.", color=color_red)
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
            embed = discord.Embed(title="Erreur", description="Vous n'avez pas assez d'argent.", color=color_red)
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

                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(title="Erreur", description="Erreur lors de l'envoi.", color=color_red)

                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Erreur", description="Erreur lors de l'envoi.", color=color_red)
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
        for i, (user_id, total) in enumerate(data, start=1):       
            user = await bot.fetch_user(user_id)
            if user is None:
                continue
            if i <= 3:
                embed.add_field(name=f"#{i}", value=f"<@{user.id}> : **{total:,}** {CoinEmoji}", inline=False)  
            else:
                embed.add_field(name=f"", value=f"**{i}** • <@{user.id}> : **{total:,}** {CoinEmoji}", inline=False)
        await interaction.response.send_message(embed=embed)

    # Commande pour afficher l'historique des transactions d'un utilisateur
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
        await interaction.response.send_message(embed=embed)

    # Commands pour give de l'argent à un utilisateur
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

    # Commande pour supprimer le compte d'un utilisateur
    @bot.tree.command(name="delete_account", description="Supprimer le compte")
    async def delete_account(interaction: discord.Interaction, user: discord.Member):
        user_id = interaction.user.id
        if not is_registered(user_id):
            embed = discord.Embed(title="Erreur", description="Vous devez vous inscrire avec `/register`.", color=color_red)
            await interaction.response.send_message(embed=embed)
            return

        if user.bot:
            embed = discord.Embed(title="Erreur", description="Vous ne pouvez pas supprimer le compte d'un bot.", color=color_red)
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
            await interaction.response.send_message(embed=embed)
            return

        if len(data) == 0:
            embed = discord.Embed(title="Erreur", description="L'utilisateur n'a pas de compte.", color=color_red)
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
                    await interaction.followup.send(embed=embed)
                else:
                    embed = discord.Embed(title="Erreur", description="Erreur lors de la suppression du compte.", color=color_red)
                    await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(title="Erreur", description="Erreur lors de la suppression du compte.", color=color_red)
                await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(description="La suppression du compte a été annulée.", color=color_green)
            await interaction.followup.send(embed=embed)
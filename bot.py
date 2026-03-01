from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()





# Run Flask in a separate thread
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
import asyncio



# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Data storage files
INFRACTIONS_FILE = "infractions.json"
PROMOTIONS_FILE = "promotions.json"
TICKETS_FILE = "tickets.json"

# Load/Save data functions
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ==================== SAY COMMAND ====================
@bot.tree.command(name="say", description="Repeats what you say")
async def say(interaction: discord.Interaction, message: str):
    """Repeats what you say"""
    await interaction.response.send_message(message)

# ==================== SUPPORT TICKET SYSTEM ====================
SUPPORT_ROLES = []  # Add the role IDs of staff who should see tickets
MANAGEMENT_ROLES = []  # Add management role IDs

@bot.tree.command(name="ticketsetup", description="Creates the support ticket embed")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction):
    """Creates the support ticket embed"""
    embed = discord.Embed(
        title="🎟️ Support Ticket System",
        description="Click a button below to create a ticket",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Support System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    view = TicketCategoryView()
    await interaction.response.send_message(embed=embed, view=view)

# ------------------- Ticket Category Buttons -------------------
class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategoryButton(label="Support", category="Support", roles=1448361743129514257,
                                           banner="/Users/mishalshafeeq/Downloads/The Yakuza Family Do not mess with us..png"))
        self.add_item(TicketCategoryButton(label="Management", category="Management", roles=1448361815187787887,
                                           banner="https://i.imgur.com/ManagementBanner.png"))

class TicketCategoryButton(discord.ui.Button):
    def __init__(self, label, category, roles, banner):
        super().__init__(style=discord.ButtonStyle.green, label=label, emoji="🎫")
        self.category = category
        self.roles = roles
        self.banner = banner

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        tickets = load_json(TICKETS_FILE)
        user_id = str(user.id)

        # Check for existing ticket
        if user_id in tickets and tickets[user_id]['status'] == "open":
            await interaction.response.send_message("❌ You already have an open ticket!", ephemeral=True)
            return

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role_id in self.roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Create channel
        channel = await guild.create_text_channel(f"ticket-{user.name}", overwrites=overwrites)

        tickets[user_id] = {"channel_id": channel.id, "status": "open", "category": self.category,
                            "created_at": datetime.now().isoformat()}
        save_json(TICKETS_FILE, tickets)

        # Send ticket embed with banner
        embed = discord.Embed(
            title=f"🎫 {self.category} Ticket",
            description=f"Welcome {user.mention}! Staff will assist you shortly.",
            color=discord.Color.green()
        )
        if self.banner:
            embed.set_image(url=self.banner)

        await channel.send(embed=embed, view=TicketChannelView())
        await interaction.response.send_message(f"✅ Ticket created! <#{channel.id}>", ephemeral=True)

# ------------------- Ticket Channel Buttons -------------------
class TicketChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ClaimTicketButton())
        self.add_item(CloseTicketButton())

class ClaimTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Claim Ticket", emoji="🖐️")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ {interaction.user.mention} claimed this ticket!", ephemeral=True)

class CloseTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Close Ticket", emoji="❌")

    async def callback(self, interaction: discord.Interaction):
        tickets = load_json(TICKETS_FILE)
        for user_id, data in tickets.items():
            if data['channel_id'] == interaction.channel.id:
                tickets[user_id]['status'] = 'closed'
                save_json(TICKETS_FILE, tickets)
                
                embed = discord.Embed(
                    title="🎫 Ticket Closed",
                    description="This ticket has been closed.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                await asyncio.sleep(2)
                await interaction.channel.delete()
                return

        await interaction.response.send_message("❌ Ticket not found!", ephemeral=True)

# ==================== INFRACTIONS SYSTEM ====================
@bot.tree.command(name="infraction", description="Add an infraction to a member")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="The member to add infraction to", reason="Reason for infraction")
async def add_infraction(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    """Add an infraction to a member"""
    infractions = load_json(INFRACTIONS_FILE)
    user_id = str(user.id)
    
    if user_id not in infractions:
        infractions[user_id] = []
    
    infraction = {
        'id': len(infractions[user_id]) + 1,
        'reason': reason,
        'date': datetime.now().isoformat(),
        'moderator': interaction.user.name
    }
    
    infractions[user_id].append(infraction)
    save_json(INFRACTIONS_FILE, infractions)
    
    embed = discord.Embed(
        title="⚠️ Infraction Added",
        description=f"**User:** {user.mention}\n**Reason:** {reason}\n**Total Infractions:** {len(infractions[user_id])}",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Added by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)
    
    try:
        await user.send(f"⚠️ You received an infraction for: **{reason}**")
    except:
        pass

@bot.tree.command(name="infractions", description="View infractions of a member")
@app_commands.describe(user="The member to check infractions for")
async def view_infractions(interaction: discord.Interaction, user: discord.Member = None):
    """View infractions of a member"""
    if user is None:
        user = interaction.user
    
    infractions = load_json(INFRACTIONS_FILE)
    user_id = str(user.id)
    
    if user_id not in infractions or not infractions[user_id]:
        embed = discord.Embed(
            title="✅ No Infractions",
            description=f"{user.mention} has no infractions",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"⚠️ Infractions for {user.name}",
        color=discord.Color.orange()
    )
    
    for infraction in infractions[user_id]:
        embed.add_field(
            name=f"Infraction #{infraction['id']}",
            value=f"**Reason:** {infraction['reason']}\n**Date:** {infraction['date']}\n**Moderator:** {infraction['moderator']}",
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(infractions[user_id])} infractions")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearinfraction", description="Remove an infraction")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="The member", infraction_id="The infraction ID to remove")
async def clear_infraction(interaction: discord.Interaction, user: discord.Member, infraction_id: int):
    """Remove an infraction"""
    infractions = load_json(INFRACTIONS_FILE)
    user_id = str(user.id)
    
    if user_id not in infractions:
        await interaction.response.send_message("❌ User has no infractions")
        return
    
    infractions[user_id] = [i for i in infractions[user_id] if i['id'] != infraction_id]
    save_json(INFRACTIONS_FILE, infractions)
    
    embed = discord.Embed(
        title="✅ Infraction Removed",
        description=f"Infraction #{infraction_id} has been removed for {user.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# ==================== PROMOTIONS SYSTEM ====================
@bot.tree.command(name="promote", description="Promote a member to a new role")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="The member to promote", role="The role to give them")
async def promote(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    """Promote a member to a new role"""
    promotions = load_json(PROMOTIONS_FILE)
    user_id = str(user.id)
    
    # Add role to user
    await user.add_roles(role)
    
    # Save promotion info
    if user_id not in promotions:
        promotions[user_id] = []
    
    promotion = {
        'role': role.name,
        'date': datetime.now().isoformat(),
        'promoter': interaction.user.name
    }
    
    promotions[user_id].append(promotion)
    save_json(PROMOTIONS_FILE, promotions)
    
    embed = discord.Embed(
        title="🎉 Promotion!",
        description=f"{user.mention} has been promoted to {role.mention}",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Promoted by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)
    
    try:
        await user.send(f"🎉 Congratulations! You have been promoted to **{role.name}**!")
    except:
        pass

@bot.tree.command(name="promotions", description="View promotions of a member")
@app_commands.describe(user="The member to check promotions for")
async def view_promotions(interaction: discord.Interaction, user: discord.Member = None):
    """View promotions of a member"""
    if user is None:
        user = interaction.user
    
    promotions = load_json(PROMOTIONS_FILE)
    user_id = str(user.id)
    
    if user_id not in promotions or not promotions[user_id]:
        embed = discord.Embed(
            title="📊 No Promotions",
            description=f"{user.mention} has no promotions",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"🎉 Promotions for {user.name}",
        color=discord.Color.gold()
    )
    
    for i, promotion in enumerate(promotions[user_id], 1):
        embed.add_field(
            name=f"Promotion #{i} unacceptable",
            value=f"**Role:** {promotion['role']}\n**Date:** {promotion['date']}\n**Promoter:** {promotion['promoter']}",
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(promotions[user_id])} promotions")
    await interaction.response.send_message(embed=embed)

# ==================== MODERATION COMMANDS ====================
@bot.tree.command(name="mute", description="Mute a member")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(user="The member to mute", duration="Duration in seconds (default: 3600)", reason="Reason for mute")
async def mute(interaction: discord.Interaction, user: discord.Member, duration: int = 3600, reason: str = "No reason provided"):
    """Mute a member"""
    try:
        await user.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason=reason)
        
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"**User:** {user.mention}\n**Duration:** {duration} seconds\n**Reason:** {reason}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Muted by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
        
        try:
            await user.send(f"🔇 You have been muted for {duration} seconds. Reason: **{reason}**")
        except:
            pass
    except Exception as e:
        await interaction.response.send_message(f"❌ Error muting user: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(user="The member to unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    """Unmute a member"""
    try:
        await user.timeout(None)
        
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{user.mention} has been unmuted",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Unmuted by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
        
        try:
            await user.send("🔊 You have been unmuted!")
        except:
            pass
    except Exception as e:
        await interaction.response.send_message(f"❌ Error unmuting user: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(user="The member to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    """Kick a member from the server"""
    try:
        await user.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**User:** {user.mention}\n**Reason:** {reason}",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Kicked by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error kicking user: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(user="The member to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    """Ban a member from the server"""
    try:
        await user.ban(reason=reason)
        
        embed = discord.Embed(
            title="⛔ Member Banned",
            description=f"**User:** {user.mention}\n**Reason:** {reason}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Banned by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error banning user: {e}", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a member")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(user_id="The user ID to unban")
async def unban(interaction: discord.Interaction, user_id: int):
    """Unban a member"""
    try:
        user = await bot.fetch_user(user_id)
        await interaction.guild.unban(user)
        
        embed = discord.Embed(
            title="✅ Member Unbanned",
            description=f"{user.mention} has been unbanned",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Unbanned by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error unbanning user: {e}", ephemeral=True)





# Token
keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables.")

bot.run(TOKEN)

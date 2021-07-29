# import os
import os    

## SQL Stuff
import sqlalchemy as db## External lib that will need to be installed via pip
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy import select
import mysql.connector

from sqlalchemy.orm import sessionmaker

Base = declarative_base()

connectionStr = os.getenv('MYSQL_CONNECTION_STRING')
engine = db.create_engine(connectionStr)
Session = sessionmaker(bind=engine)

## API 
API_TOKEN = os.getenv('API_TOKEN')
SG_DEV_GUILD_ID = int(os.getenv('SG_DEV_GUILD_ID'))

## Discord Client 
import discord ## External lib that will need to be installed via pip
from discord.ext import commands

INTENTS = discord.Intents.default()
INTENTS.members = True
client = discord.Client(intents=INTENTS)
bot = commands.Bot(command_prefix="!",intents=INTENTS)

## Collection vars
web_roles = []
discord_roles = []

class WebRole(Base):
    __tablename__ = 'v_member_groups'
    id_group = Column(Integer, primary_key=True)
    group_name = Column(String)


class WebMember(Base):
    __tablename__ = 'v_discord_website_members'
    website_id = Column(Integer, primary_key=True)
    member_name = Column(String)
    discord_id = Column(Integer)
    group_ids = Column(Integer)
  
@bot.event
async def on_ready():
    print("Bot ready!")

@bot.command(name="get_sync_project_status")
async def get_sync_project_status(ctx):
    await ctx.send(">>> **Project Status To Do: ** \n- Update member view to include csv of groups \n- Compare Role Lists\n- Sync roles via Discord with website as source of truth")

@bot.command(name='get_guild_roles')
async def get_roles(ctx):
    print("[DEBUG] Getting roles")
    await ctx.send(">>> There are {0} roles for this server:".format(len(ctx.guild.roles)))
    for role in ctx.guild.roles:
        await ctx.send("{0}".format(role.name))

@bot.command(name='get_guild_members')
async def get_member_count(ctx):
    print("[DEBUG] Getting member count")
    await ctx.send(">>> There are {0} members in the {1} guild: [Note:  excluding 'everyone' role for now]".format(len(ctx.guild.members), ctx.guild.name))
    for member in ctx.guild.members:
        member_roles = []
        for role in member.roles:
            member_roles.append(role.name)
        await ctx.send("{0} [ID:  {1}] is in these roles: {2}.".format(member.name, member.id,", ".join(member_roles)))
            

@bot.command(name="process_differences")
async def process_differences(ctx):
    session = Session()
    q = session.query(WebMember)
    discord_ids = list(m.id for m in ctx.guild.members)
    ids_to_process = []

    await ctx.send("There are {0} discord members registered on the website:".format(len(q.all())))
    for m in q.all():
        if int(m.discord_id) in discord_ids:       
            ids_to_process.append(m.discord_id)
        # await ctx.send(m.member_name+ " with ID {0} is in groups:  ".format(m.discord_id) + ", ".join(get_groups_by_ids(m.group_ids)))

    await compare_role_diffs(ids_to_process, ctx)
        

@bot.command(name="get_web_roles")
async def process_web_roles(ctx):
    session = Session()
    q = session.query(WebRole).order_by(WebRole.id_group)
    await ctx.send("There are {0} roles on the website:".format(len(q.all())))
    for role in q.all():
        await ctx.send(role.group_name)


def process_guild_roles(guild):
    print("Processing {0} roles from the {1} guild.".format(len(guild.roles), guild.name))
    for role in guild.roles:
        print("Adding role:  {0}".format('\033[92m' + role.name +'\033[0m'))
        discord_roles.append(role.name)

def process_guild_members(guild):
    print("Processing {0} members from the {1} guild.".format(len(guild.members), guild.name))
    for member in guild.members:
        member_roles = ""
        for member_role in member.roles:
            member_roles += member_role.name + ", "
        print("Member:  {0}  ID:  {1} is in these roles in discord: {2}".format('\033[92m' + member.name + '\033[0m', member.id , '\033[94m'+  member_roles[:-2] +'\033[0m')) 

def process_list_diffs(l1,l2):
    list_diff = []
    for i in l1:
        if i not in l2:
            list_diff.append(i)
    print(list_diff)

def get_groups_by_ids(ids):
    ## TODO  Make the groups so we only query once
    session = Session()
    query = session.query(WebRole).order_by(WebRole.id_group)
    groups = query.all()
    ids_as_array = ids.split(",")
    out_groups = []

    for id in ids_as_array:
        for group in groups:
            if(int(id) == (int(group.id_group))):
                out_groups.append(group.group_name)

    return out_groups

def get_web_roles_by_id(id):    
    session = Session()
    query = session.query(WebMember)
    members = query.all()
    for m in members:
        if m.discord_id == id:
            return m.group_ids

async def get_discord_role_by_id(id, ctx):
    members = ctx.guild.members
    for m in members:
        if int(id) == m.id:
            return list(r.name for r in m.roles)

async def get_name_by_id(id, ctx):
    for m in ctx.guild.members:
        if int(id) == m.id:
            return m.name

async def compare_role_diffs(ids, ctx):
    await ctx.send(">>> ")
    for id in ids:
        name = await get_name_by_id(id,ctx)
        await ctx.send("Processing discord ID:  [{0}] \"{1}\":".format(id, name))
        web_role_ids = get_web_roles_by_id(id)
        web_roles_for_id = get_groups_by_ids(web_role_ids)
        await ctx.send("Discord Id:  [{0}] \"{1}\" is in these roles from the website {2}".format(id, name,  ", ".join(web_roles_for_id)))
        discord_roles_for_id = await get_discord_role_by_id(id, ctx)
        await ctx.send("Discord Id:  [{0}] \"{1}\" is in these roles in discord {2}".format(id, name, ", ".join(discord_roles_for_id)))

        list_diff = []
        for i in web_roles_for_id:
            if i not in discord_roles_for_id:
                list_diff.append(i)
        
        await ctx.send("Difference in roles for {0} [{1}] (should be):  {2}".format(name, id, list_diff))
        await ctx.send(">>> ")

bot.run(API_TOKEN)
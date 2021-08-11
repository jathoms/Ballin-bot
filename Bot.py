import discord
import os
from dotenv import load_dotenv
from important_ids import DISCORD_SNOWFLAKE_IDS
import ballin_embeds
from parse_start_args import parseInput, filterConfigs, getRandomMap
import serveme_interaction
import db_interaction as db
from db_interaction import teams
load_dotenv()


activity = discord.Activity(
    name='top 10 shadowburn airshots vol.19', type=discord.ActivityType.watching)

intents = discord.Intents.default()
intents.members = True
intents.dm_reactions = True
intents.dm_messages = True
intents.reactions = True
client = discord.Client(activity=activity, intents=intents)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    db.resetAFK()


@client.event
async def on_message(message):

    # and message.channel.id != 867478179094069258:
    if message.channel.id != DISCORD_SNOWFLAKE_IDS["FIRSTSERVER"]:
        return

    if message.content.startswith('!mention'):
        await message.channel.send("<@&867039167426068480>", allowed_mentions=discord.AllowedMentions.all())

    if message.content.startswith('!start'):
        await message.delete()

        if not db.ongoing():
            errors = parseInput(message.content)
            document = teams.find(
                {"config": {"$exists": True}})[0]

            if not document["map_set"]:
                teams.update_one(
                    {}, {"$set": {"map": getRandomMap(document["gamemode"]),
                                  "map_set": True}})

            config = filterConfigs(document["config"])
            if errors or config.split(" ")[0] == "invalid":
                await message.author.send(" ".join(errors) + ", try !help")
                db.resetAFK()
                return

            teams.update_one(
                {}, {"$set": {"ongoing": True, "config": config}})
            db.initializeTeams()
            check = await message.channel.send(embed=await ballin_embeds.createStartEmbed(message.author, client), allowed_mentions=discord.AllowedMentions.all())
            teams.update_one(
                {}, {"$set": {"msg_id": check.id, "starter": message.author.id}})
            BLU = client.get_emoji(DISCORD_SNOWFLAKE_IDS["BLU_EMOJI"])
            RED = client.get_emoji(DISCORD_SNOWFLAKE_IDS["RED_EMOJI"])
            await check.add_reaction(BLU)
            await check.add_reaction(RED)
        else:
            await message.author.send("A check is currently in progress, wait until it is over or participate in the current one.")
        return

    if message.content.startswith('!forcestart'):
        await message.delete()
        if db.ongoing() and message.author.id == teams.find_one({"starter": {"$exists": True}})["starter"]:
            oldmsg = await db.getCurrentCheckId(await client.fetch_channel(DISCORD_SNOWFLAKE_IDS["FIRSTSERVER"]))
            if oldmsg == -1:
                return
            await startGame(oldmsg, force=True)
            return

    if message.content.startswith('!rolled'):
        await message.channel.send("rolled")
        return

    if message.content.startswith("!maps"):
        await message.delete()
        mapArg = message.content.split(" ", 1)
        if len(mapArg) < 2:
            await message.author.send('You must include a term to search for! For example, try !maps koth\nFor a full, uninterrupted list of maps, head on over to serveme.tf/reservations/new and look in the "First map" dropdown box')
            return
        searchTerm = mapArg[1]
        maps = teams.find_one({"maps": {"$exists": True}})["maps"]
        mapStringList = ['Maps matching "'+searchTerm + '":\n']
        mapChars = 0
        anyMaps = False
        for _map in maps:
            if searchTerm in _map:
                anyMaps = True
                mapStringList.append(_map)
                mapChars += len(_map)
                if mapChars > 3800:
                    await message.author.send(embed=discord.Embed(description="\n".join(mapStringList), colour=0x42f5f2))
                    mapStringList = []
                    mapChars = 0

        if anyMaps:
            await message.author.send(embed=discord.Embed(description="\n".join(mapStringList), colour=0x42f5f2))
        else:
            await message.author.send(embed=discord.Embed(description='No maps matching "' + searchTerm + '"'))
        return

    if message.content.startswith('!fear'):
        await message.delete()
        oldmsg = await db.getCurrentCheckId(await client.fetch_channel(DISCORD_SNOWFLAKE_IDS["FIRSTSERVER"]))
        if oldmsg == -1:
            await message.channel.send(message.author.display_name + " fears...")
            return
        fearHaver = {"ID": message.author.id}
        if db.nextGamePlayers.count_documents(fearHaver) > 0:
            team = db.nextGamePlayers.find(fearHaver)[0]["TEAM"]
        else:
            return

        if db.completed():
            await message.channel.send("Now is not the time for fear " + message.author.display_name + ", the game is starting")
            return

        teamIndex = 0 if team == "BLU" else 1
        db.nextGamePlayers.delete_many(fearHaver)
        db.ballCheck.delete_many(fearHaver)
        db.removePlayer(message.author, team)
        newmsg = oldmsg.embeds[0]
        newmsg.set_field_at(teamIndex,
                            name=team, value=await db.getPlayersFromDB(team, client), inline=True)
        await oldmsg.edit(embed=newmsg)
        return

    # id is me
    if message.content.startswith('!cancel') and (message.author.id == teams.find_one({"starter": {"$exists": True}})["starter"] or message.author.id == 193435025193172993):
        await message.delete()
        if db.completed():
            return
        oldmsg = await db.getCurrentCheckId(await client.fetch_channel(DISCORD_SNOWFLAKE_IDS["FIRSTSERVER"]))

        if oldmsg == -1:
            return
        else:
            newmsg = oldmsg.embeds[0]
            newmsg.add_field(
                name="CANCELLED", value="Game cancelled", inline=False)
            await oldmsg.edit(embed=newmsg)
        db.resetAFK()
        return

    if message.content.startswith('!help'):
        await message.channel.send(embed=ballin_embeds.createHelpEmbed())
    # me n bot
    if message.author.id != DISCORD_SNOWFLAKE_IDS["ADMINISTRATORS"] and message.author.id != DISCORD_SNOWFLAKE_IDS["BALLINBOT"]:
        await message.delete()


def getTeam(emoji, swap=False):
    RED = client.get_emoji(DISCORD_SNOWFLAKE_IDS["RED_EMOJI"])
    BLU = client.get_emoji(DISCORD_SNOWFLAKE_IDS["BLU_EMOJI"])
    if emoji == BLU:
        if swap:
            team = "RED"
            teamEmoji = RED
            teamIndex = 1
        else:
            team = "BLU"
            teamEmoji = BLU
            teamIndex = 0
    elif emoji == RED:
        if swap:
            team = "BLU"
            teamEmoji = BLU
            teamIndex = 0
        else:
            team = "RED"
            teamEmoji = RED
            teamIndex = 1
    else:
        return 0, 0, 0
    return team, teamEmoji, teamIndex


@ client.event
async def on_reaction_add(reaction, user):
    # Don't respond to your own reactions or random other reactions dummy
    # ballin bot ID
    if(user.bot or not reaction.message.author.id == DISCORD_SNOWFLAKE_IDS["BALLINBOT"]):
        return

    embed = reaction.message.embeds
    team, teamEmoji, teamIndex = getTeam(reaction.emoji)
    if team == 0:
        return

    if embed:
        # Old Message e.g message to be editted
        oldmsg = await db.getCurrentCheckId(await client.fetch_channel(DISCORD_SNOWFLAKE_IDS["FIRSTSERVER"]))

        if oldmsg == -1:
            return
        # If reaction is to a ball check (descriptions match)
        embedIdentifier = embed[0].description

        if embedIdentifier == (await ballin_embeds.createStartEmbed(user, client)).description and reaction.message == oldmsg:
            initialReactor = {"NAME": user.name,
                              "ID": user.id}
            if db.ballCheck.count_documents(initialReactor) == 0:
                db.ballCheck.insert_one(initialReactor)
                msg = await user.send(embed=ballin_embeds.createConfirmEmbed(team))
                await msg.add_reaction(teamEmoji)

        # If reaction is to a DM confirm (descriptions match)
        if embedIdentifier == ballin_embeds.createConfirmEmbed(team).description or embedIdentifier == ballin_embeds.createChangeTeamEmbed("BLU").description or embedIdentifier == ballin_embeds.createChangeTeamEmbed("RED").description:
            if db.ongoing and db.ballCheck.count_documents({"ID": user.id}):
                team_size = db.getTeamSize()
                if db.completed():
                    await user.send("game is full, gg go next")
                    return
                # On team full, offer to join other team
                if db.nextGamePlayers.count_documents({"TEAM": team}) >= team_size:
                    changeEmbed = ballin_embeds.createChangeTeamEmbed(team)
                    msg = await user.send(embed=changeEmbed)
                    team, teamEmoji, _ = getTeam(  # _ probably works
                        reaction.emoji, swap=True)
                    await msg.add_reaction(teamEmoji)
                    return

                reactConfirmer = {"TEAM": team,
                                  "NAME": user.name,
                                  "ID": user.id}
                db.nextGamePlayers.insert_one(reactConfirmer)
                newmsg = oldmsg.embeds[0]
                db.addPlayer(user, team)
                newmsg.set_field_at(teamIndex,
                                    name=team, value=await db.getPlayersFromDB(team, client), inline=True)
                if db.completed():
                    # Once both teams are full, make a reservation, reset afk check, completion message
                    await startGame(oldmsg)
                    return

                await oldmsg.edit(embed=newmsg)


async def startGame(oldmsg, force=False):  # newmsg = oldmsg embed content
    newmsg = oldmsg.embeds[0]
    if not force:
        newmsg.add_field(
            name="All players confirmed!", value="Making reservation...", inline=False)
        await oldmsg.edit(embed=newmsg)
    else:
        playercount = db.nextGamePlayers.count_documents({})
        if playercount >= 1:
            newmsg.add_field(
                name="Starting with " + str(playercount) + "/" + str(db.getTeamSize()*2) + " players!", value="Making reservation...", inline=False)
            await oldmsg.edit(embed=newmsg)
        else:
            return

    # Make Reservation
    connectstring = serveme_interaction.reserveServer()

    # DM all players connect string
    player_ids = db.nextGamePlayers.find(
        projection={"_id": False, "ID": True})
    document = teams.find_one(
        {"gamemode": {"$exists": True}})
    for player_id in player_ids:
        player = await client.fetch_user(player_id["ID"])
        await player.send(embed=ballin_embeds.createReadyEmbed(connectstring, player_id["ID"], document["starter"], document["rcon"]))
    newmsg.set_field_at(
        2, name="Reservation made!", value="Check DMs for a link to the game!", inline=False)

    await oldmsg.edit(embed=newmsg)
    db.resetAFK()


client.run(os.getenv('TOKEN'))

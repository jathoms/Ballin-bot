import discord
import os
import requests
import datetime
import pymongo
import random
import string
from dotenv import load_dotenv
load_dotenv()


# IDEAS: Multiple channels for different gamemodes/concurrent checks

activity = discord.Activity(
    name='2013 frag movies', type=discord.ActivityType.watching)

intents = discord.Intents.default()
intents.members = True
intents.dm_reactions = True
intents.dm_messages = True
intents.reactions = True
client = discord.Client(activity=activity, intents=intents)
dbclient = pymongo.MongoClient('localhost', 27017)
db = dbclient["BallinDB"]
nextGamePlayers = db.nextGamePlayers
ballCheck = db.ballCheck
params = db.Ballin


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    #channel = client.get_channel(871878373352292394)
    resetAFK()


@client.event
async def on_message(message):

    # and message.channel.id != 867478179094069258:
    if message.channel.id != 871878373352292394:
        return

    if message.content.startswith("!mention"):
        await message.channel.send("<@&867039167426068480>", allowed_mentions=discord.AllowedMentions.all())

    if message.content.startswith('!start'):
        await message.delete()

        if not ongoing():
            errors = parseInput(message.content)
            document = params.find(
                {"config": {"$exists": True}})[0]

            if not document["map_set"]:
                params.update_one(
                    {}, {"$set": {"map": getRandomMap(document["gamemode"]),
                                  "map_set": True}})
            config = filterConfigs(document["config"])
            if errors or config.split(" ")[0] == "invalid":
                await message.author.send(" ".join(errors) + ", try !help")
                resetAFK()
                return

            params.update_one(
                {}, {"$set": {"ongoing": True, "config": config}})
            initializeTeams()
            check = await message.channel.send(embed=await createStartEmbed(message.author), allowed_mentions=discord.AllowedMentions.all())
            params.update_one(
                {}, {"$set": {"msg_id": check.id, "starter": message.author.id}})
            BLU = client.get_emoji(867868050811650068)
            RED = client.get_emoji(867869380209410088)
            await check.add_reaction(BLU)
            await check.add_reaction(RED)
        else:
            await message.author.send("A check is currently in progress, wait until it is over or participate in the current one.")
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
        maps = params.find_one({"maps": {"$exists": True}})["maps"]
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
        oldmsg = await getCurrentCheckId()
        if oldmsg == -1:
            await message.channel.send(message.author.display_name + " fears...")
            return
        fearHaver = {"ID": message.author.id}
        if nextGamePlayers.count_documents(fearHaver) > 0:
            team = nextGamePlayers.find(fearHaver)[0]["TEAM"]
        else:
            return

        if completed():
            await message.channel.send("Now is not the time for fear " + message.author.display_name + ", the game is starting")
            return

        teamIndex = 0 if team == "BLU" else 1
        nextGamePlayers.delete_many(fearHaver)
        ballCheck.delete_many(fearHaver)
        removePlayer(message.author, team)
        newmsg = oldmsg.embeds[0]
        newmsg.set_field_at(teamIndex,
                            name=team, value=await getPlayersFromDB(team), inline=True)
        await oldmsg.edit(embed=newmsg)
        return

    # id is me
    if message.content.startswith('!cancel') and (message.author.id == params.find_one({"starter": {"$exists": True}})["starter"] or message.author.id == 193435025193172993):
        await message.delete()
        if completed():
            return
        oldmsg = await getCurrentCheckId()

        if oldmsg == -1:
            return
        else:
            newmsg = oldmsg.embeds[0]
            newmsg.add_field(
                name="CANCELLED", value="Game cancelled", inline=False)
            await oldmsg.edit(embed=newmsg)
        resetAFK()
        return

    if message.content.startswith('!help'):
        await message.channel.send(embed=createHelpEmbed())
    if message.author.id != 193435025193172993 and message.author.id != 867179735301095424:  # me n bot
        await message.delete()


def createHelpEmbed():
    helpEmbed = discord.Embed(
        description="IN AUTOMATED BALLIN, You can type: ", timestamp=datetime.datetime.utcnow(), colour=0x68ff3b)
    helpEmbed.set_author(name="BALLIN BOT YOOOOO",
                         icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    helpEmbed.add_field(
        name="!start", value="Usage: !start <gamemode> <map> <config>\nMap and config are optional\ne.g: !start 6s cp_process_final etf2l\nOr !start hl\nIn a hurry? Simply type !start for some ballin", inline=False)
    helpEmbed.add_field(
        name="!fear", value="If you're participating in a check and you fear (or just want to switch teams) you can !fear\nIt's ok, everyone fears sometimes, you won't be shamed", inline=False)
    helpEmbed.add_field(
        name="!cancel", value="When a check is active, if you started it, you can !cancel it", inline=False)
    helpEmbed.add_field(
        name="!maps", value="Usage: !maps <term>\nReturns every map with the term you include with the command in DMs\ne.g: !maps pl_\nOr !maps e\n To get all maps containing the letter e (not recommended)", inline=False)
    helpEmbed.set_footer(
        text="this bot in early as hell development so expect it to be weird, dm @alltrees if and when it breaks\nThis bot was made possible by serveme.tf, support them at serveme.tf/donate")

    return helpEmbed


def genPassword():
    length = 13
    chars = string.ascii_letters + string.digits + '123456789aeio'
    random.seed = (os.urandom(1024))

    return ''.join(random.choice(chars) for _ in range(length))


def ongoing():
    cursor = params.find(projection={"ongoing": True, "_id": False})
    return cursor[0]["ongoing"]


def initializeTeams():
    empty = [-1 for _ in range(getTeamSize())]
    params.insert_one({"TEAM": "BLU", "PLAYERS": empty})
    params.insert_one({"TEAM": "RED", "PLAYERS": empty})


def resetAFK():
    ballCheck.delete_many({})
    nextGamePlayers.delete_many({})
    params.delete_many({"TEAM": {"$exists": True}})
    params.update_one({}, {"$set":
                           {"ongoing": False,
                            "msg_id": -1,
                            "team_size": 2,
                            "gamemode": "BBALL",
                            "map": "bball_eu_fix",
                            "config": "etf2l",
                            "gamemode_set": False,
                            "map_set": False,
                            "config_set": False}})


def getGoodArgs():
    document = params.find({"gamemode": {"$exists": True}})[0]
    gamemode = document["gamemode"]
    if gamemode == "BBALL":
        gamemode = "Ball"
    elif gamemode == "BBALL1v1":
        gamemode = "1v1 Ball"
    elif gamemode == "SIXES":
        gamemode = "6s"
    elif gamemode == "FOURS":
        gamemode = "4s"
    elif gamemode == "PROLANDER":
        gamemode = "Prolander"
    elif gamemode == "ULTIDUO":
        gamemode = "Ultiduo"
    elif gamemode == "HIGHLANDER":
        gamemode = "Highlander"

    mapSelection = document["map"]
    config = document["config"]

    return gamemode, mapSelection, config


async def createStartEmbed(author, region="eu"):
    gamemode, mapSelection, config = getGoodArgs()
    embedVar = discord.Embed(description='React with BLU or RED to join that team\nFirst ' + str(getTeamSize()) + ' confirmed reactions for each team will be sent server details',
                             timestamp=datetime.datetime.utcnow(), colour=0xa85202)
    embedVar.set_author(
        name=gamemode + " check started in " + region +
        " by " + author.display_name + " on " + mapSelection,
        icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")

    embedVar.add_field(name="BLU", value=await getPlayersFromDB("BLU"),
                       inline=True)
    embedVar.add_field(name="RED", value=await getPlayersFromDB("RED"), inline=True)
    embedVar.set_footer(text="Config: "+config)
    return embedVar


async def getPlayersFromDB(team):
    playersString = ""
    for id in params.find({"TEAM": team})[0]["PLAYERS"]:
        if id == -1:
            playersString += "-------------\n"
        else:
            playersString += (await client.fetch_user(id)).display_name + "\n"
    return playersString


def addPlayer(user, team):
    count = 0
    for id in params.find({"TEAM": team})[0]["PLAYERS"]:
        if id == -1:
            params.update_one(
                {"TEAM": team}, {"$set": {"PLAYERS." + str(count): user.id}})
            return
        count += 1
    return


def removePlayer(user, team):
    count = 0
    for id in params.find({"TEAM": team})[0]["PLAYERS"]:
        if id == user.id:
            params.update_one(
                {"TEAM": team}, {"$set": {"PLAYERS." + str(count): -1}})
            return
        count += 1
    return


def createConfirmEmbed(team):
    embedVar = discord.Embed(description='Confirm your reaction to join ' + team + '.\nIf you have changed your mind, do not react with ' + team + ' to this message',
                             timestamp=datetime.datetime.utcnow(), colour=0xa85202)
    embedVar.set_author(name="You have reacted " + team,
                        icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    return embedVar


def createChangeEmbed(team):
    if team == "RED":
        newTeam = "BLU"
    elif team == "BLU":
        newTeam = "RED"
    changeEmbed = discord.Embed(
        description="Join " + newTeam + "?", timestamp=datetime.datetime.utcnow())
    changeEmbed.set_author(name="" + team + " team is full",
                           icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    return changeEmbed


def createReadyEmbed(connectstring, user, starter):

    gamemode, _, _ = getGoodArgs()

    readyEmbed = discord.Embed(
        description="Click the link to join your " +
        gamemode +
        " game. (probably doesn't work)\nsteam://connect/" + connectstring,
        timestamp=datetime.datetime.utcnow())
    readyEmbed.add_field(name="Or paste the following string into the console: ", value="connect " +
                         connectstring.split("/", 1)[0] + ";password " + connectstring.split("/", 1)[1])

    if user == starter:
        readyEmbed.add_field(name='RCON password:"', value='rcon_address bolus.fakkelbrigade.eu:27035; rcon_password ' + params.find_one(
            {"rcon": {"$exists": True}})["rcon"], inline=False)

    readyEmbed.set_author(
        name="Game is ready",
        icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    return readyEmbed


def getTeamSize():
    team_size_cursor = params.find(
        projection={"team_size": True, "_id": False})
    team_size = team_size_cursor[0]["team_size"]
    return team_size


def getTeam(emoji, swap=False):
    RED = client.get_emoji(867869380209410088)
    BLU = client.get_emoji(867868050811650068)
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


def completed():

    team_size = getTeamSize()

    if(nextGamePlayers.count_documents({}) == team_size*2):
        return True


def getConfigs():
    apiKey = os.getenv("SERVEME")
    available = requests.get(
        "https://serveme.tf/api/reservations/new?api_key=" + apiKey).json()

    reservation, findServers = available["reservation"], available["actions"]["find_servers"]

    configs = requests.post(
        findServers+"?api_key=" + apiKey, json=reservation).json()["server_configs"]

    return configs


def parseInput(input):
    positions = ["gamemode", "map", "config"]
    print("\n")
    args = input.split(" ")[1:]
    if not args:
        params.update_one({},
                          {"$set": {"gamemode_set": True,
                                    "map_set": True}})
        return ""

    position = 0
    for arg in args:
        if "=" in arg:
            [variable, value] = arg.split("=", 1)
        else:
            variable, value = positions[position], arg
            position += 1

        value = normalizeAndValidateArg(variable, value)

        print(variable + ": " + value)

        split = value.split(" ", 1)

        if split[0] == "invalid":
            return split

        params.update_one({variable: {"$exists": True}},
                          {"$set": {variable: value, variable + "_set": True}})
    return ""


def getRandomMap(mode):
    if mode == "BBALL" or mode == "BBALL1v1":
        maps = ["bball_tf_v2", "ctf_ballin_sky",
                "ctf_bball2", "ctf_bball_sweethills_v1",
                "bball_royal", "ctf_bball2",
                "ctf_ballin_exile", "ctf_ballin_wisty",
                "ctf_bball_neon", "ctf_bball_eventide"
                "bball_eu_fix", "ctf_bball_hoopdreams"]
    elif mode == "SIXES" or mode == "FOURS":
        maps = ["cp_gullywash_pro", "cp_metalworks_rc7",
                "cp_process_final", "cp_snakewater_u18",
                "cp_sunshine", "cp_sunshine_event",
                "koth_product_rc9", "cp_granary_pro_rc9",
                "koth_bagel_fc4"]
    elif mode == "HIGHLANDER" or mode == "PROLANDER":
        maps = ["koth_product_rc8", "pl_borneo_rc4",
                "koth_lakeside", "pl_badwater_pro_rc12",
                "pl_upward", "koth_proplant_v7",
                "cp_steel", "koth_clearcut_b15d"]
    elif mode == "ULTIDUO":
        maps = ["koth_ultiduo", "ultiduo_baloo_b4",
                "ultiduo_seclusion_b3"]
    else:
        maps = ["koth_product_rc8", "pl_borneo_rc4",
                "koth_lakeside", "pl_badwater_pro_rc12",
                "pl_upward", "pl_barnblitz",
                "koth_clearcut_b15d", "cp_gullywash_pro",
                "cp_metalworks_rc7", "cp_process_final",
                "cp_snakewater_u18", "cp_sunshine",
                "cp_sunshine_event", "koth_product_rc9",
                "cp_granary_pro_rc9", "koth_bagel_fc4"]

    index = random.randrange(len(maps))
    return maps[index]


def teamSizeUpdate(size):
    params.update_one({"team_size": {"$exists": True}}, {
        "$set": {"team_size": size}})


def normalizeAndValidateArg(var, val):
    lowerCase = val.lower()
    mode = ""
    if var == "gamemode":
        if lowerCase in ["6v6", "6s", "6", "sixes", "6v"]:
            teamSize = 6
            mode = "SIXES"
        elif lowerCase in ["hl", "highlander", "9v9", "9v", "9"]:
            teamSize = 9
            mode = "HIGHLANDER"
        elif lowerCase in ["4v4", "4s", "4", "fours", "4v"]:
            teamSize = 4
            mode = "FOURS"
        elif lowerCase in ["7v7", "7s", "7v", "prolander", "sevens" "7"]:
            teamSize = 7
            mode = "PROLANDER"
        elif lowerCase in ["ultiduo", "ulti", "ud", "duo"]:
            teamSize = 2
            mode = "ULTIDUO"
        elif lowerCase in ["bball", "ball"]:
            teamSize = 2
            mode = "BBALL"
        elif lowerCase in ["bball1v1", "bball1"]:
            teamSize = 1
            mode = "BBALL1v1"
        if mode:
            teamSizeUpdate(teamSize)
            return mode
        return "invalid gamemode"

    elif var == "map":
        maps = params.find({"maps": {"$exists": True}})[0]
        if val in maps["maps"] or val in maps["cloud_maps"]:
            return val
        return "invalid map"

    elif var == "config":
        params.update_one({}, {"$set": {"config_set": True}})
        return filterConfigs(val)


def filterConfigs(val):
    # make sure map and gamemode are both set before config is set, as config is validated using map and gamemode names
    document = params.find_one({"map": {"$exists": True}})
    if not (document["map_set"] and document["gamemode_set"]):
        return "invalid order"
    gamemode = document["gamemode"]

    if document["config_set"] == False and gamemode == "PROLANDER":  # nothing has 7s except rgl
        val = "rgl"
    if document["config_set"] == False and gamemode == "BBALL":  # eu best config
        val = "eu"
    if document["config_set"] == False and gamemode == "BBALL1v1":
        val = "eu"
        # for test etc

    configs = getConfigs()

    if gamemode != "FOURS":
        viableConfigs = [
            config for config in configs if val in config["file"]]
        if len(viableConfigs) == 1:
            return viableConfigs[0]["file"]
    else:
        viableConfigs = configs

    mapName = document["map"].split("_", 1)
    mapPrefix = mapName[0]
    mapSuffix = mapName[1]
    if mapPrefix == "pl" or mapSuffix == "steel":       # No configs start with pl and steel is stopwatch
        mapPrefix = "stopwatch"
    teamLimit = str(getTeamSize())

    gamemode = document["gamemode"]

    print("viable configs: " + str(len(viableConfigs)))
    if gamemode == "BBALL" or gamemode == "ULTIDUO":
        withLimitAndMap = [
            config for config in viableConfigs if gamemode.lower() in config["file"]]
    elif gamemode == "HIGHLANDER":
        withLimitAndMap = [
            config for config in viableConfigs if mapPrefix in config["file"] and any(x in config["file"] for x in [teamLimit, "hl", "highlander", "HL"])]
    else:
        withLimitAndMap = [
            config for config in viableConfigs if any(x in config["file"] for x in ["standard", mapPrefix]) and teamLimit in config["file"]]

    print("after all : " + str(len(withLimitAndMap)))

    if not withLimitAndMap:
        return "invalid config"
    return withLimitAndMap[0]["file"]


def reserveServer():
    apiKey = os.getenv("SERVEME")
    available = requests.get(
        "https://serveme.tf/api/reservations/new?api_key=" + apiKey).json()

    document = params.find_one(
        {"gamemode": {"$exists": True}})

    reservation, findServers = available["reservation"], available["actions"]["find_servers"]

    servers = requests.post(
        findServers+"?api_key=" + apiKey, json=reservation).json()

    configs = servers["server_configs"]
    _config = document["config"]

    resForm = servers["reservation"]
    resForm["first_map"] = document["map"]

    resForm["server_config_id"] = [
        config for config in configs if config["file"] == _config][0]["id"]

   # choice = [
    #   server for server in servers["servers"] if server["location"]["id"] == 8]
   # if not choice:
    choice = servers["servers"]

    resForm["server_id"] = choice[0]["id"]

    password = genPassword()
    rcon = genPassword()
    params.update_one({}, {"$set": {"password": password, "rcon": rcon}})

    resForm["password"] = password
    resForm["rcon"] = rcon
    resForm["auto_end"] = True

    confirm = requests.post(
        servers["actions"]["create"] + "?api_key=" + apiKey, json=resForm).json()

    print(confirm["reservation"])

    params.update_one(
        {}, {"$set": {"delete": confirm["actions"]["delete"]}})
    print(confirm)
    return (confirm["reservation"]["server"]["ip_and_port"] + '/' + password)


async def getCurrentCheckId():
    channel = client.get_channel(871878373352292394)
    msg_cursor = params.find(projection={"msg_id": True})
    msg_id = msg_cursor[0]["msg_id"]
    oldmsg = await channel.fetch_message(msg_id) if msg_id != -1 else -1
    return oldmsg


@ client.event
async def on_reaction_add(reaction, user):
    # Don't respond to your own reactions or random other reactions dummy
    if(user.bot or not reaction.message.author.bot):
        return

    embed = reaction.message.embeds
    team, teamEmoji, teamIndex = getTeam(reaction.emoji)
    if team == 0:
        return

    if embed:
        oldmsg = await getCurrentCheckId()

        if oldmsg == -1:
            return
        # If reaction is to a ball check (descriptions match)
        embedIdentifier = embed[0].description

        if embedIdentifier == (await createStartEmbed(user)).description and reaction.message == oldmsg:
            initialReactor = {"NAME": user.name,
                              "ID": user.id}
            if ballCheck.count_documents(initialReactor) == 0:
                ballCheck.insert_one(initialReactor)
                msg = await user.send(embed=createConfirmEmbed(team))
                await msg.add_reaction(teamEmoji)

        # If reaction is to a DM confirm (descriptions match)
        if embedIdentifier == createConfirmEmbed(team).description or embedIdentifier == createChangeEmbed("BLU").description or embedIdentifier == createChangeEmbed("RED").description:
            if ongoing and ballCheck.count_documents({"ID": user.id}):
                team_size = getTeamSize()
                if completed():
                    await user.send("game is full, gg go next")
                    return
                # On team full, offer to join other team
                if nextGamePlayers.count_documents({"TEAM": team}) >= team_size:
                    changeEmbed = createChangeEmbed(team)
                    msg = await user.send(embed=changeEmbed)
                    team, teamEmoji, _ = getTeam(  # _ probably works
                        reaction.emoji, swap=True)
                    await msg.add_reaction(teamEmoji)
                    return

                reactConfirmer = {"TEAM": team,
                                  "NAME": user.name,
                                  "ID": user.id}
                nextGamePlayers.insert_one(reactConfirmer)

                newmsg = oldmsg.embeds[0]

                addPlayer(user, team)

                newmsg.set_field_at(teamIndex,
                                    name=team, value=await getPlayersFromDB(team), inline=True)
                if completed():
                    # Once both teams are full, make a reservation, reset afk check, completion message
                    newmsg.add_field(
                        name="All players confirmed!", value="Making reservation...", inline=False)
                    await oldmsg.edit(embed=newmsg)

                    # Make Reservation
                    connectstring = reserveServer()

                    # DM all players connect string
                    player_ids = nextGamePlayers.find(
                        projection={"_id": False, "ID": True})
                    starter_id = params.find_one(
                        {"gamemode": {"$exists": True}})["starter"]
                    for player_id in player_ids:
                        player = await client.fetch_user(player_id["ID"])
                        await player.send(embed=createReadyEmbed(connectstring, player_id["ID"], starter_id))
                    newmsg.set_field_at(
                        2, name="Reservation made!", value="Check DMs for a link to the game!", inline=False)

                    await oldmsg.edit(embed=newmsg)
                    resetAFK()
                    return

                await oldmsg.edit(embed=newmsg)

client.run(os.getenv('TOKEN'))

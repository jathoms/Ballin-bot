from discord import Embed
import datetime
from db_interaction import getTeamSize, getPlayersFromDB
from parse_start_args import getGoodArgs


async def createStartEmbed(author, client, region="eu", ):
    gamemode, mapSelection, config = getGoodArgs()
    embedVar = Embed(description='React with BLU or RED to join that team\nFirst ' + str(getTeamSize()) + ' confirmed reactions for each team will be sent server details',
                     timestamp=datetime.datetime.utcnow(), colour=0xa85202)
    embedVar.set_author(
        name=gamemode + " check started in " + region +
        " by " + author.display_name + " on " + mapSelection,
        icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")

    embedVar.add_field(name="BLU", value=await getPlayersFromDB("BLU", client),
                       inline=True)
    embedVar.add_field(name="RED", value=await getPlayersFromDB("RED", client), inline=True)
    embedVar.set_footer(text="Config: "+config)
    return embedVar


def createChangeTeamEmbed(team):
    if team == "RED":
        newTeam = "BLU"
    elif team == "BLU":
        newTeam = "RED"
    changeEmbed = Embed(
        description="Join " + newTeam + "?", timestamp=datetime.datetime.utcnow())
    changeEmbed.set_author(name="" + team + " team is full",
                           icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    return changeEmbed


def createReadyEmbed(connectstring, user, starter, rcon):

    gamemode, _, _ = getGoodArgs()

    readyEmbed = Embed(
        description="Click the link to join your " +
        gamemode +
        " game. (probably doesn't work)\nsteam://connect/" + connectstring,
        timestamp=datetime.datetime.utcnow(), colour=0xa85202)
    readyEmbed.add_field(name="Or paste the following string into the console: ", value="connect " +
                         connectstring.split("/", 1)[0] + ";password " + connectstring.split("/", 1)[1])

    if user == starter:
        readyEmbed.add_field(
            name='RCON password:', value='rcon_address bolus.fakkelbrigade.eu:27035; rcon_password ' + rcon)

    readyEmbed.set_author(
        name="Game is ready",
        icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    return readyEmbed


def createConfirmEmbed(team):

    embedVar = Embed(description='Confirm your reaction to join ' + team + '.\nIf you have changed your mind, do not react with ' + team + ' to this message',
                     timestamp=datetime.datetime.utcnow(), colour=0xa85202)
    embedVar.set_author(name="You have reacted " + team,
                        icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    return embedVar


def createHelpEmbed():
    helpEmbed = Embed(
        description="IN AUTOMATED BALLIN, You can type: ", timestamp=datetime.datetime.utcnow(), colour=0x68ff3b)
    helpEmbed.set_author(name="BALLIN BOT YOOOOO",
                         icon_url="https://cdn.discordapp.com/attachments/867864919785209866/867864962559115304/circleballin.png")
    helpEmbed.add_field(
        name="!start", value="Usage: !start <gamemode> <map> <config>\nMap and config are optional, map must be typed exactly\ne.g: !start 6s cp_process_final etf2l\nOr !start hl\nIn a hurry? Simply type !start for some ballin", inline=False)
    helpEmbed.add_field(
        name="!fear", value="If you're participating in a check and you fear (or just want to switch teams) you can !fear\nIt's ok, everyone fears sometimes, you won't be shamed", inline=False)
    helpEmbed.add_field(
        name="!cancel", value="When a check is active, if you started it, you can !cancel it", inline=False)
    helpEmbed.add_field(
        name="!maps", value="Usage: !maps <term>\nReturns every map with the term you include with the command in DMs\ne.g: !maps pl_\nOr !maps e\n To get all maps containing the letter e (not recommended)", inline=False)
    helpEmbed.set_footer(
        text="this bot in early as hell development so expect it to be weird, dm @alltrees if and when it breaks\nThis bot was made possible by serveme.tf, support them at serveme.tf/donate")

    return helpEmbed

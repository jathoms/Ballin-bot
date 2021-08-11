import pymongo
from os import getenv
from dotenv import load_dotenv
load_dotenv()
dbclient = pymongo.MongoClient(
    "mongodb+srv://admin:"+getenv("MONGOPASS")+"@jcl.m99h8.mongodb.net/BallinDB?retryWrites=true&w=majority")
db = dbclient["BallinDB"]
nextGamePlayers = db.nextGamePlayers
ballCheck = db.ballCheck
teams = db.Ballin
params = db.cappedParams
maps = db.cappedMaps


def ongoing():
    cursor = teams.find(projection={"ongoing": True, "_id": False})
    return cursor[0]["ongoing"]


def initializeTeams():
    empty = [-1 for _ in range(getTeamSize())]
    teams.insert_one({"TEAM": "BLU", "PLAYERS": empty})
    teams.insert_one({"TEAM": "RED", "PLAYERS": empty})


async def getPlayersFromDB(team, client):
    playersString = ""
    for id in teams.find({"TEAM": team})[0]["PLAYERS"]:
        if id == -1:
            playersString += "-------------\n"
        else:
            playersString += (await client.fetch_user(id)).display_name + "\n"
    return playersString


def addPlayer(user, team):
    count = 0
    for id in teams.find({"TEAM": team})[0]["PLAYERS"]:
        if id == -1:
            teams.update_one(
                {"TEAM": team}, {"$set": {"PLAYERS." + str(count): user.id}})
            return
        count += 1
    return


def removePlayer(user, team):
    count = 0
    for id in teams.find({"TEAM": team})[0]["PLAYERS"]:
        if id == user.id:
            teams.update_one(
                {"TEAM": team}, {"$set": {"PLAYERS." + str(count): -1}})
            return
        count += 1
    return


def getTeamSize():
    team_size_cursor = teams.find(
        projection={"team_size": True, "_id": False})
    team_size = team_size_cursor[0]["team_size"]
    return team_size


def findMap(_map):
    _map = maps.find_one({})
    if _map in maps["maps"] or _map in maps["cloud_maps"]:
        return _map
    return "invalid map"


def completed():

    team_size = getTeamSize()

    if(nextGamePlayers.count_documents({}) == team_size*2):
        return True


def teamSizeUpdate(size):
    teams.update_one({"team_size": {"$exists": True}}, {
        "$set": {"team_size": size}})


def resetAFK():

    ballCheck.delete_many({})
    nextGamePlayers.delete_many({})
    teams.delete_many({"TEAM": {"$exists": True}})
    teams.update_one({}, {"$set":
                          {"ongoing": False,
                           "msg_id": -1,
                           "team_size": 2,
                           "gamemode": "BBALL",
                           "map": "bball_eu_fix",
                           "config": "etf2l",
                           "gamemode_set": False,
                           "map_set": False,
                           "config_set": False}})


async def getCurrentCheckId(channel_id):
    channel = channel_id
    msg_cursor = teams.find(projection={"msg_id": True})
    msg_id = msg_cursor[0]["msg_id"]
    oldmsg = await channel.fetch_message(msg_id) if msg_id != -1 else -1
    return oldmsg

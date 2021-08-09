from db_interaction import params, teamSizeUpdate, getTeamSize
from serveme_interaction import getConfigs
from random import randrange


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

        if not value:
            return  # Add error message here

        print(variable + ": " + value)

        split = value.split(" ", 1)

        if split[0] == "invalid":
            return split

        params.update_one({variable: {"$exists": True}},
                          {"$set": {variable: value, variable + "_set": True}})
    return ""

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

    isSet = document["config_set"]
    if not isSet:
        if gamemode == "PROLANDER":  # nothing has 7s except rgl
            val = "rgl"
        elif gamemode == "BBALL" or gamemode == "BBALL1v1":  # eu best config
            val = "eu"

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

    if withLimitAndMap:
        return withLimitAndMap[0]["file"]
    elif isSet:
        return "invalid config"
    else:
        return "classic"  # value for no config

def getGoodArgs():  # This is for presentation, to show the arguments in the embed
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

    index = randrange(len(maps))
    return maps[index]
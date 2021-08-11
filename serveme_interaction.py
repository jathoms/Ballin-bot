import os
import requests
from db_interaction import params
import random
from string import ascii_letters, digits


def getConfigs():
    apiKey = os.getenv("SERVEME")
    available = requests.get(
        "https://serveme.tf/api/reservations/new?api_key=" + apiKey).json()

    reservation, findServers = available["reservation"], available["actions"]["find_servers"]

    configs = requests.post(
        findServers+"?api_key=" + apiKey, json=reservation).json()["server_configs"]

    return configs


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


def genPassword():
    length = 13
    chars = ascii_letters + digits + '123456789aeio'
    random.seed = (os.urandom(1024))

    return ''.join(random.choice(chars) for _ in range(length))

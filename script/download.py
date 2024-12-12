import os
import re
import subprocess
import requests
import json5


def download_file(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()

        filename = os.path.basename(url)
        file_path = save_path + filename

        with open(file_path, "wb") as file:
            file.write(response.content)

    except requests.exceptions.RequestException as e:
        print(f"Download file error: {e}")


def download_depot(depot_file: str):
    downloader = "./DepotDownloader.exe"
    depot_file_name = os.path.basename(depot_file)
    depot_id = os.path.splitext(depot_file_name)[0]
    out_dir = "../cs2"
    command = [
        downloader,
        "-app",
        str(730),
        "-depot",
        str(depot_id),
        "-filelist",
        depot_file,
        "-dir",
        out_dir,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if not re.search(r"100(\.|,)00%", result.stdout):
        raise Exception(f"Error on download depot file: {depot_file}.")


def read_jsonc(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json5.load(file)
    return data


def find_depot_files(directory):
    depot_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".depot"):
                depot_files.append(os.path.join(root, file))
    return depot_files


if __name__ == "__main__":
    config_gamedata = read_jsonc("../config/download.jsonc")

    for url in config_gamedata["urls"]:
        download_file(url, "../gamedata/")

    depot_files = find_depot_files("../config")
    for file in depot_files:
        download_depot(file)

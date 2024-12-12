import os
import re
import json5


def convert_to_regex(hex_signature):
    pattern = ""
    hex_signature = hex_signature.replace(" ", "")
    i = 0
    while i < len(hex_signature):
        if hex_signature[i] == "?":
            pattern += "."
            i += 1
        else:
            if i + 1 < len(hex_signature):
                byte = hex_signature[i : i + 2]
                pattern += f"\\x{byte}"
                i += 2
            else:
                pattern += "."
                i += 1
    return re.compile(pattern.encode("latin1"), re.DOTALL)


def count_binary_signature_with_regex(file, signature: str, key: str):
    file.seek(0)
    data = file.read()

    regex_pattern = convert_to_regex(signature)

    matches = regex_pattern.findall(data)

    return len(matches)


def library_load(library):
    if library in files and files[library] is not None:
        return files[library]

    try:
        if library == "server":
            file_path = game_path + "csgo/bin/win64/server.dll"
        else:
            file_path = game_path + "bin/win64/" + library + ".dll"

        files[library] = open(file_path, "rb")
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None
    except Exception as e:
        print(
            f"Error: An unexpected error occurred while opening the file {file_path}. Exception: {e}"
        )
        return None

    return files[library]


def read_files_in_directory(directory):
    result = {}
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as file:
                if os.path.basename(path).endswith("placeholder"):
                    continue

                signatures = json5.load(file)["Signature"]
                for key, val in signatures.items():
                    library_name = str(val["library"]).lower()
                    library = library_load(library_name)
                    count = count_binary_signature_with_regex(
                        library, str(val["windows"]), key
                    )

                    if count == 1:
                        continue

                    if library_name not in result:
                        result[library_name] = {}

                    result[library_name][key] = count
        elif os.path.isdir(path):
            result.update(read_files_in_directory(path))

    return result


if __name__ == "__main__":
    game_path = "../cs2/game/"

    files = {}

    result = read_files_in_directory("../gamedata")

    for lib, sig in result.items():
        sigs = [f"[{sig[s]}] {s}" for s in sig]
        print(f"Library: {lib}\n" + "\n".join(sigs))

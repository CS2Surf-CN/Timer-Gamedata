import os
import re
import json5


class GamedataCheck:
    def __init__(self, game_path, gamedata_dir):
        self.lib_pe = {}
        self.game_path = game_path
        self.gamedata_dir = gamedata_dir

    def convert_to_regex(self, hex_signature):
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

    def count_binary_signature_with_regex(self, file, signature: str, key: str):
        file.seek(0)
        data = file.read()

        regex_pattern = self.convert_to_regex(signature)

        matches = regex_pattern.findall(data)

        return len(matches)

    def library_load(self, library, platform):
        if (
            library in self.lib_pe
            and platform in self.lib_pe[library]
            and self.lib_pe[library][platform] is not None
        ):
            return self.lib_pe[library][platform]

        is_game_bin = library in ["server", "host", "matchmaking"]
        if platform == "windows":
            lib_bin_dir = "csgo/bin/win64/" if is_game_bin else "bin/win64/"
            lib_fullname = library + ".dll"
        elif platform == "linux":
            lib_bin_dir = (
                "csgo/bin/linuxsteamrt64/" if is_game_bin else "bin/linuxsteamrt64/"
            )
            lib_fullname = "lib" + library + ".so"
        else:
            raise Exception(f"platform {platform} not supported.")

        file_path = self.game_path + lib_bin_dir + lib_fullname

        if library not in self.lib_pe:
            self.lib_pe[library] = {}
            self.lib_pe[library]["windows"] = None
            self.lib_pe[library]["linux"] = None

        self.lib_pe[library][platform] = open(file_path, "rb")
        return self.lib_pe[library][platform]

    def read_files_in_directory(self):
        result = dict()
        for filename in os.listdir(self.gamedata_dir):
            path = os.path.join(self.gamedata_dir, filename)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as file:
                    if os.path.basename(path).endswith("placeholder"):
                        continue

                    signatures = json5.load(file)["Signature"]
                    for key, val in signatures.items():
                        library_name = str(val["library"]).lower()
                        if library_name not in result:
                            result[library_name] = {}
                            result[library_name]["windows"] = {}
                            result[library_name]["linux"] = {}

                        if "windows" in val.keys():
                            library = self.library_load(library_name, "windows")
                            count = self.count_binary_signature_with_regex(
                                library, str(val["windows"]), key
                            )

                            if count != 1:
                                result[library_name]["windows"][key] = count

                        if "linux" in val.keys():
                            library = self.library_load(library_name, "linux")
                            count = self.count_binary_signature_with_regex(
                                library, str(val["linux"]), key
                            )

                            if count != 1:
                                result[library_name]["linux"][key] = count
            elif os.path.isdir(path):
                result.update(self.read_files_in_directory(path))

        return result


if __name__ == "__main__":
    checker = GamedataCheck("../cs2/game/", "../gamedata")

    result = checker.read_files_in_directory()
    os_output = {}

    for library_name, os_data in result.items():
        for os_name, keys in os_data.items():
            if os_name not in os_output:
                os_output[os_name] = []
            os_output[os_name].append((library_name, keys))

    bad_sig = False
    for os_name, libraries in os_output.items():
        has_output = False
        for library_name, keys in libraries:
            if keys:
                if not has_output:
                    print(f"{os_name}:")
                    has_output = True
                print(f"  Library: {library_name}")
                bad_sig = True
                for key, value in keys.items():
                    print(f"    [{value}] {key}")

    if not bad_sig:
        print("All signature and address are good.")

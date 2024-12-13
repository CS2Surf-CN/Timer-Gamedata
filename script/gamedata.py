import os
import re
import json5
from datetime import datetime, timezone


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

    def read_files_in_directory(self, gamedata_dir):
        result = dict()
        for filename in os.listdir(gamedata_dir):
            path = os.path.join(gamedata_dir, filename)
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

    result = checker.read_files_in_directory(checker.gamedata_dir)
    os_output = {}

    for library_name, os_data in result.items():
        for os_name, keys in os_data.items():
            if os_name not in os_output:
                os_output[os_name] = []
            os_output[os_name].append((library_name, keys))

    last_updated = f"## Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"

    html_output = []
    html_output.append(last_updated)
    html_output.append("<table>")
    html_output.append(
        "<tr><th>Platform</th><th>Library</th><th>Signature</th><th>Count</th><th>Status</th></tr>"
    )

    bad_sig = False
    for os_name, libraries in os_output.items():
        total_rows = sum(len(keys) + 1 for _, keys in libraries if keys)

        platform_rowspan_added = False
        for library_name, keys in libraries:
            if not keys:
                continue

            bad_sig = True
            if not platform_rowspan_added:
                html_output.append(
                    f"<tr><td rowspan='{total_rows}'>{os_name.capitalize()}</td>"
                )
                platform_rowspan_added = True
            else:
                html_output.append("<tr>")

            html_output.append(
                f"<td rowspan='{len(keys) + 1}'>{library_name}</td></tr>"
            )

            for key, count in keys.items():
                html_output.append(
                    f"<tr><td>{key}</td><td>{count}</td><td>❌</td></tr>"
                )

    if not bad_sig:
        html_output.clear()
        html_output.append(last_updated)
        html_output.append("<table>")
        html_output.append("<tr><th>Platform</th><th>Status</th></tr>")
        html_output.append(f"<tr><td>Windows</td><td>✅</td></tr>")
        html_output.append(f"<tr><td>Linux</td><td>✅</td></tr>")

    html_output.append("</table>")

    with open("../README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(html_output))

    print("Gamedata check has been done!")

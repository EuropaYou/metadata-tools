import os
import json
import pathlib

folder = "YOUR_FOLDER_LOCATION"

if os.path.exists(folder):
    print("Folder exists! Searching the directory for JSON files.")

    result = list(pathlib.Path(folder).rglob("*.[jJ][sS][oO][nN]"))
    print("Search completed. Minify started.")

    for item in result:
        try:
            jsonData = None
            with open(item, mode="r", encoding="utf-8") as file:
                jsonData = json.load(file)

            shrink = json.dumps(jsonData, ensure_ascii=False, separators=(",", ":"))

            with open(item, mode="w", encoding="utf-8") as file:
                file.write(shrink)

        except Exception as e:
            print(f"Coudln't process file: {item}")
else:
  print("Folder doesnt exist! Exitting...\n In a world where data must be compressed and meaning reimagined… one dares to transform structure into story.")

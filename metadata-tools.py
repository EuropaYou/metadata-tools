import os
import sys
import json
import argparse
from pathlib import Path
from itertools import chain
import time
from jsonschema.exceptions import (
    ValidationError,
    UnknownType,
    UndefinedTypeCheck,
    SchemaError,
    FormatError,
)
from jsonschema.validators import validator_for

parser = argparse.ArgumentParser(
    prog="Metadata Tools",
    description="Provides tools for metadata files.",
    epilog="For the people, by the people.",
)

parser.add_argument("--input-folder", type=Path, required=True)
parser.add_argument("--input-schema", type=Path, default=None)
parser.add_argument("--shrink-metadata", action="store_true")
parser.add_argument("--delete-empty-metadata", action="store_true")
parser.add_argument("--treat-txt-as-json", action="store_true")

args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
curr = time.perf_counter()
empty_count = 0
shrink_count = 0
schema_success = 0
schema_fail = 0
schema_fail_types = {
    "ValidationError": 0,
    "FormatError": 0,
    "SchemaError": 0,
    "UndefinedTypeCheck": 0,
    "UnknownType": 0,
    "JSONDecodeError": 0,
    "UnknownError": 0,
}
deleted_metadata = {}
shrink_metadata = {}  # NYI
schema_fail_metadata = {}  # NYI

path = args.input_folder
schema_path = args.input_schema


def get_metadata(treat_txt_as_json):
    json_files = path.rglob("*.[jJ][sS][oO][nN]")
    result = list(json_files)
    if treat_txt_as_json:
        txt_files = path.rglob("*.[tT][xX][tT]")
        result = list(chain(json_files, txt_files))
    return result


def validate_file(file, validator):
    with file.open("r", encoding="utf-8") as f:
        js = json.load(f)
        validator.validate(js)


def load_schema(schema_path):
    if schema_path is None:
        return None

    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema file does not exist: {schema_path}")

    try:
        with schema_path.open("r", encoding="utf-8") as schema_file:
            return json.load(schema_file)
    except json.JSONDecodeError as e:
        print(f"JSON decode error for schema file... {schema_path}. {e}")
        raise


if not any(
    (
        args.shrink_metadata,
        args.delete_empty_metadata,
        args.input_schema,
    )
):
    parser.error("No operation specified.")


if path.is_dir():
    print(
        f"Folder exists! Searching the directory ({args.input_folder}) for JSON files."
    )
    result = get_metadata(args.treat_txt_as_json)
    schema = load_schema(schema_path)
    validator = None
    if schema is not None:
        Validator = validator_for(schema)
        Validator.check_schema(schema)
        validator = Validator(schema)
    for item in result:
        item_relative = item.relative_to(args.input_folder)
        if args.input_schema:
            try:
                validate_file(item, validator)
                schema_success += 1
            except ValidationError as e:
                schema_fail_types["ValidationError"] += 1
                schema_fail += 1
                print(f"Validation Failed for : {item_relative} {e}")
                continue
            except FormatError as e:
                schema_fail_types["FormatError"] += 1
                schema_fail += 1
                print(f"JSON format error: {item_relative} {e}")
                continue
            except UndefinedTypeCheck as e:
                schema_fail_types["UndefinedTypeCheck"] += 1
                schema_fail += 1
                print(f"Undefined JSON Type check error: {item_relative} {e}")
                continue
            except UnknownType as e:
                schema_fail_types["UnknownType"] += 1
                schema_fail += 1
                print(f"Unknown JSON error: {item_relative} {e}")
                continue
            except json.JSONDecodeError as e:
                schema_fail_types["JSONDecodeError"] += 1
                schema_fail += 1
                print(f"JSON decode error for: {item_relative} {e}")
                continue
            except Exception as e:
                schema_fail_types["UnknownError"] += 1
                schema_fail += 1
                print(f"Could not process file: {item_relative} {e}, {e.__class__}")
                continue

        if args.shrink_metadata:
            tmp = None
            try:
                with item.open("r", encoding="utf-8") as json_file:
                    json_data = json.load(json_file)

                shrink = json.dumps(
                    json_data,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

                tmp = item.with_suffix(item.suffix + ".tmp")

                with tmp.open("w", encoding="utf-8") as tmp_file:
                    tmp_file.write(shrink)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())

                tmp.replace(item)

                shrink_count += 1

            except Exception as e:
                if tmp is not None and tmp.exists():
                    tmp.unlink(missing_ok=True)
                print(f"Could not process file: {item} {e}")

        if args.delete_empty_metadata:
            item_info = item.stat()
            if item_info.st_size == 0:
                deleted_metadata[str(item_relative)] = {
                    i: getattr(item_info, i)
                    for i in dir(item_info)
                    if i.startswith("st_")
                }
                empty_count += 1
                item.unlink(missing_ok=True)

    if args.delete_empty_metadata:
        empty_metadata_report = Path("EMPTY_METADATA_FILES.json")

        with empty_metadata_report.open("w", encoding="utf-8") as data_file:
            json.dump(deleted_metadata, data_file, indent=2)

    print(
        f"\nThis program took: {time.perf_counter() - curr:.2f} seconds. Found {len(result)} metadata files"
        + f"\n\tSuccessfully deleted {empty_count} empty metadata files."
        + f"\n\tSuccessfully shrunk {shrink_count} files."
        + f"\n\tFound {schema_fail} schema fails, {schema_success} success out of {len(result)}"
        + f"{schema_fail_types if schema_fail > 0 else ''}"
    )

else:
    print(
        "Folder does not exist! Exitting...\n In a world where data must be compressed and meaning reimagined… one dares to transform structure into story."
    )

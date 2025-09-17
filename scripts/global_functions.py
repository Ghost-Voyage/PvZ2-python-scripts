import json
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(levelname)s] %(message)s")

file_handler = logging.FileHandler(Path(__file__).parent / "debug.log", mode="w", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


@dataclass
class Configuration:
    project: str
    main: list
    sub: dict


def save_json(file, data):
    with file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_json(file):
    try:
        with file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading {file}: {e}")
    return None


def load_json_config(section):
    config_path = Path(__file__).parent / "function_config.json"
    config = load_json(config_path)
    if config is None:
        logger.error(f"Could not load configuration file: {config_path}")
        return None

    project_path = config.get("ProjectPath")
    data_type = config.get(section)

    if not project_path:
        logger.error(f"Missing 'ProjectPath' in config: {config_path}")
        return None

    if not data_type:
        logger.error(f"Missing '{section}' in config: {config_path}")
        return None

    return Configuration(
        project=project_path,
        main=data_type.get("Main", []),
        sub=data_type.get("Sub", {})
    )



def normalize_json_structure(data):
    """
    Reorganizes the JSON data by removing 'version' and 'objects' keys, then re-adding them at the end.
    Modifies the input data in place.
    Returns 'objects' for convenience, usually unused.
    """
    objects = data["objects"]
    data.pop("version", None)
    data.pop("objects", None)
    data["version"] = 1
    data["objects"] = objects
    return objects

def normalize_json_objdata(data):
    for obj in data.get("objects", []):
        aliases = obj.get("aliases")
        objclass = obj.get("objclass")
        objdata = obj.get("objdata", {})
        obj.pop("aliases", None)
        obj.pop("objclass", None)
        obj.pop("objdata", {})
        if aliases is not None:
            obj["aliases"] = aliases
        if objclass is not None:
            obj["objclass"] = objclass
            obj["objdata"] = objdata


def apply_processing_to_objects(data, config):
    for obj in data.get("objects", []):
        objclass = obj.get("objclass")
        objdata = obj.get("objdata", {})
        order = get_combined_key_order(objclass, config)
        if objclass is not None:
            obj["objdata"] = sort_objdata_keys(objdata, order)
    return data


def sort_objdata_keys(objdata, order):
    ordered = {key: objdata[key] for key in order if key in objdata}
    ordered.update({key: value for key, value in objdata.items() if key not in ordered})
    return ordered


def resolve_references(sub_keys_dict, objclass, seen=None, path=None):
    if seen is None:
        seen = set()
    if path is None:
        path = []

    if objclass in seen:
        cycle = " -> ".join(path + [objclass])
        logger.warning(f"Circular reference detected: {cycle}. Resolution stopped to avoid infinite loop.")
        return []

    seen.add(objclass)
    path.append(objclass)

    keys = []
    for key in sub_keys_dict.get(objclass, []):
        if key.startswith("ref:"):
            ref_objclass = key[len("ref:"):]
            keys.extend(
                resolve_references(sub_keys_dict, ref_objclass, seen, path.copy())
            )
        else:
            keys.append(key)

    return keys


def get_combined_key_order(objclass, config):
    main_keys = config.main
    sub_keys_dict = config.sub

    if objclass is None:
        return main_keys

    if objclass in sub_keys_dict:
        resolved_sub_keys = resolve_references(sub_keys_dict, objclass)
        sub_keys_dict = sub_keys_dict[objclass]
        combined_keys = [key for key in resolved_sub_keys if key not in main_keys] + main_keys
    else:
        combined_keys = main_keys
        logger.warning(f"Missing sub-keys for objclass '{objclass}' or 'sub_keys' is None.")
    return combined_keys


"""
def increase_integer_id(objdata, amount):
    if isinstance(objdata.get("IntegerID"), int):
        objdata["IntegerID"] += amount

PlantTypes & PlantTypes should have objclass at the top instead of aliases
ProjectileTypes should have 'classname' at the top no matter what
"""

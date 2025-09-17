import scripts.global_functions as func
from pathlib import Path


def main(project):
    config = func.load_json_config(project)
    file_path = Path(config.project) / f"{project}.json"

    data = func.load_json(file_path)
    # Modifies 'data' in place by reorganizing its structure
    func.normalize_json_structure(data)
    func.normalize_json_objdata(data)

    processed_data = func.apply_processing_to_objects(data, config)
    func.save_json(file_path, processed_data)

    func.logger.info(f"Processed {project} data saved to: {file_path}")
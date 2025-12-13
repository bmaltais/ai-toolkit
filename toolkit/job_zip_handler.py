import os
import zipfile
import shutil
import tempfile
import yaml
from toolkit.config import get_config, possible_extensions
from toolkit.paths import TOOLKIT_ROOT

def find_config_file(job_name):
    config_dir = os.path.join(TOOLKIT_ROOT, 'config')
    for ext in possible_extensions:
        config_path = os.path.join(config_dir, f"{job_name}{ext}")
        if os.path.exists(config_path):
            return config_path
    return None

def export_job(job_name, output_path):
    """
    Exports a job's config, dataset(s) and output files to a zip file.

    :param job_name: The name of the job to export.
    :param output_path: The path to save the zip file to.
    """
    config_path = find_config_file(job_name)
    if not config_path:
        raise FileNotFoundError(f"Config file for job '{job_name}' not found.")

    config = get_config(config_path)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a directory inside temp_dir to hold all the job data
        job_dir = os.path.join(temp_dir, job_name)
        os.makedirs(job_dir)

        # Copy config file
        shutil.copy(config_path, job_dir)

        # Copy dataset(s)
        if 'process' in config['config']:
            for process in config['config']['process']:
                if 'datasets' in process:
                    for dataset in process['datasets']:
                        if 'folder_path' in dataset:
                            dataset_path = dataset['folder_path']
                            if os.path.exists(dataset_path):
                                # To avoid issues with absolute paths, we'll copy the dataset
                                # to a folder inside our job_dir
                                dataset_name = os.path.basename(dataset_path)
                                dest_dataset_path = os.path.join(job_dir, 'datasets', dataset_name)
                                shutil.copytree(dataset_path, dest_dataset_path)

        # Copy output folder
        if 'process' in config['config']:
            for process in config['config']['process']:
                if 'training_folder' in process:
                    training_folder = process['training_folder']
                    output_folder_path = os.path.join(training_folder, job_name)
                    if os.path.exists(output_folder_path):
                        dest_output_path = os.path.join(job_dir, 'output')
                        shutil.copytree(output_folder_path, dest_output_path)


        # Create zip file
        base_output_path = os.path.splitext(output_path)[0]
        shutil.make_archive(base_output_path, 'zip', temp_dir)


def import_job(zip_path):
    """
    Imports a job and its dataset(s) from a zip file.

    :param zip_path: The path to the zip file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # The job data is in a single folder inside the zip
        job_name = os.listdir(temp_dir)[0]
        job_dir = os.path.join(temp_dir, job_name)

        # Find and parse the config file
        config_filename = None
        for item in os.listdir(job_dir):
            if any(item.endswith(ext) for ext in possible_extensions):
                config_filename = item
                break

        if not config_filename:
            raise FileNotFoundError("Config file not found in zip.")

        config_path = os.path.join(job_dir, config_filename)
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Update paths in the config
        if 'process' in config['config']:
            for process in config['config']['process']:
                if 'datasets' in process:
                    for dataset in process['datasets']:
                        if 'folder_path' in dataset:
                            dataset_name = os.path.basename(dataset['folder_path'])
                            dataset['folder_path'] = os.path.join(TOOLKIT_ROOT, 'datasets', dataset_name)
                if 'training_folder' in process:
                    process['training_folder'] = os.path.join(TOOLKIT_ROOT, 'output')

        # Save the updated config
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Move config file
        shutil.move(config_path, os.path.join(TOOLKIT_ROOT, 'config'))

        # Move dataset(s)
        datasets_dir = os.path.join(job_dir, 'datasets')
        if os.path.exists(datasets_dir):
            # Ensure the top-level 'datasets' directory exists
            top_level_datasets_dir = os.path.join(TOOLKIT_ROOT, 'datasets')
            os.makedirs(top_level_datasets_dir, exist_ok=True)
            for dataset_name in os.listdir(datasets_dir):
                src_dataset_path = os.path.join(datasets_dir, dataset_name)
                dest_dataset_path = os.path.join(top_level_datasets_dir, dataset_name)
                if os.path.exists(dest_dataset_path):
                    shutil.rmtree(dest_dataset_path)
                shutil.move(src_dataset_path, dest_dataset_path)

        # Move output folder
        output_dir = os.path.join(job_dir, 'output')
        if os.path.exists(output_dir):
            dest_output_path = os.path.join(TOOLKIT_ROOT, 'output', job_name)
            if os.path.exists(dest_output_path):
                shutil.rmtree(dest_output_path)
            shutil.move(output_dir, dest_output_path)

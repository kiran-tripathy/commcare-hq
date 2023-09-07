import difflib
import json
from pathlib import Path

from django.core.management import BaseCommand

import corehq

COREHQ_BASE_DIR = Path(corehq.__file__).resolve().parent
DIFF_CONFIG_FILE = "apps/hqwebapp/tests/data/bootstrap5_diff_config.json"
DIFF_STORAGE_FOLDER = "apps/hqwebapp/tests/data/bootstrap5_diffs/"


def get_diff_filename(filename_bootstrap3, filename_bootstrap5, file_type):
    if filename_bootstrap3 == filename_bootstrap5:
        filename = filename_bootstrap5
    else:
        filename_bootstrap3 = get_renamed_filename(filename_bootstrap3)
        filename_bootstrap5 = get_renamed_filename(filename_bootstrap5)
        filename = f"{filename_bootstrap3}.{filename_bootstrap5}"
    if file_type == "stylesheet":
        filename = f"{filename}.style"
    return f"{filename}.diff.txt"


def get_renamed_filename(filename):
    return filename.replace('.scss', '').replace('.less', '').replace('/', '_')


def get_diff(file_v1, file_v2):
    with open(file_v1, "r") as fv1, open(file_v2, "r") as fv2:
        data_v1 = fv1.readlines()
        data_v2 = fv2.readlines()
        return list(difflib.unified_diff(data_v1, data_v2))


def get_bootstrap5_diff_config():
    config_file_path = COREHQ_BASE_DIR / DIFF_CONFIG_FILE
    with open(config_file_path, encoding='utf-8') as f:
        return json.loads(f.read())


def get_bootstrap5_filepaths(full_diff_config):
    for parent_path, directory_diff_config in full_diff_config.items():
        for diff_config in directory_diff_config:
            directory_bootstrap3, directory_bootstrap5 = diff_config['directories']
            migrated_files = diff_config.get('files')
            compare_all_files = diff_config.get('compare_all_files', False)
            file_type = diff_config["file_type"]
            label = diff_config["label"]

            path_bootstrap3 = COREHQ_BASE_DIR / parent_path / directory_bootstrap3
            path_bootstrap5 = COREHQ_BASE_DIR / parent_path / directory_bootstrap5

            if compare_all_files:
                migrated_files = [[x.name, x.name] for x in path_bootstrap3.glob('**/*') if x.is_file()]

            for filename_bootstrap3, filename_bootstrap5 in migrated_files:
                diff_filename = get_diff_filename(filename_bootstrap3, filename_bootstrap5, file_type)
                diff_filepath = COREHQ_BASE_DIR / DIFF_STORAGE_FOLDER / label / diff_filename
                diff_filepath.parent.mkdir(parents=True, exist_ok=True)
                bootstrap3_filepath = path_bootstrap3 / filename_bootstrap3
                bootstrap5_filepath = path_bootstrap5 / filename_bootstrap5

                yield bootstrap3_filepath, bootstrap5_filepath, diff_filepath


class Command(BaseCommand):
    help = """
    This command builds diffs between files that have undergone the Bootstrap 3 -> Bootstrap 5 Migration split.

    The motivation is to keep track of changes and flag new changes in tests, as the diffs will change
    from what was previously generated by this command. The expectation is that these changes should be propagated
    over to the Bootstrap 5 templates to ensure the two split Bootstrap 3 and Bootstrap 5 templates remain in sync.
    Once the two files are brought up to date, this command can be run again to ensure tests pass.
    """

    def handle(self, *args, **options):
        full_diff_config = get_bootstrap5_diff_config()
        for bootstrap3_filepath, bootstrap5_filepath, diff_filepath in get_bootstrap5_filepaths(full_diff_config):
            with open(diff_filepath, 'w') as df:
                df.writelines(get_diff(bootstrap3_filepath, bootstrap5_filepath))

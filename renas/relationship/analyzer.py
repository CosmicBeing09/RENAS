import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import traceback
from logging import INFO, Formatter, StreamHandler, getLogger

import pandas as pd

LOGGER = getLogger(__name__)


def set_argument():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source", help="set directory containing repositories to be analyzed"
    )
    parser.add_argument(
        "-threshold",
        help="use commit which has more than 3 renames",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    return args


def set_logger(level):
    root_logger = getLogger()
    LOGGER.setLevel(level)
    handler = StreamHandler()
    handler.setLevel(level)
    formatter = Formatter("[%(asctime)s] %(name)s -- %(levelname)s : %(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    return root_logger


def filter_data(data, threshold: int):
    LOGGER.info("filter data")
    commits = data.groupby("commit").size()

    commits = commits[commits > threshold]
    LOGGER.info(f"threshold = more than {threshold} renames")
    LOGGER.info(f"total {commits.sum()} renames")
    LOGGER.info(f"pick {len(commits)} commits")
    return data[data["commit"].isin(commits.index)]


def git_archive(root, directory, sha1):
    try:
        LOGGER.info(f"[{os.getpid()}] {directory}: archive commit {sha1}^")
        archive_dir = directory.joinpath(sha1).joinpath("repo")
        os.makedirs(archive_dir, exist_ok=True)

        archive = [
            "git",
            f'--git-dir={root.joinpath("repo").joinpath(".git")}',
            "archive",
            f"{sha1}^",
        ]
        extract = ["tar", "-xf", "-", "-C", archive_dir]
        p1 = subprocess.run(archive, capture_output=True, check=True)
        p2 = subprocess.run(extract, input=p1.stdout, check=True)
    except subprocess.CalledProcessError as cpe:
        LOGGER.error(cpe, file=sys.stderr)
    return


def do_table(directory: pathlib.Path, sha1: str):
    archiveDir = directory.joinpath(sha1)
    LOGGER.info(f"Running table.sh for archive: {archiveDir}")
    
    try:
        p1 = subprocess.run(
            f"sh renas/table.sh {archiveDir}", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if p1.stdout:
            LOGGER.info(f"table.sh stdout: {p1.stdout}")
        if p1.stderr:
            LOGGER.error(f"table.sh stderr: {p1.stderr}")
            
        if p1.returncode != 0:
            LOGGER.error(f"table.sh failed with return code {p1.returncode} for {archiveDir}")
            if p1.stderr:
                LOGGER.error(f"Error details: {p1.stderr}")
            LOGGER.info(f"Removing failed archive directory: {archiveDir}")
            shutil.rmtree(archiveDir)
            raise Exception(f"table.sh failed for {archiveDir}")
        else:
            LOGGER.info(f"table.sh completed successfully for {archiveDir}")
            
    except subprocess.CalledProcessError as cpe:
        LOGGER.error(f"CalledProcessError in do_table for {archiveDir}: {cpe}")
        LOGGER.error(f"Return code: {cpe.returncode}")
        LOGGER.error(f"Output: {cpe.output}")
        LOGGER.error(f"Stderr: {cpe.stderr}")
        traceback.print_exc()
        raise
    except Exception as e:
        LOGGER.error(f"Unexpected error in do_table for {archiveDir}: {e}")
        LOGGER.exception("Full traceback:")
        raise


def git_archive_wrapper(arg):
    return git_archive(*arg)


def main(root: pathlib.Path, rename_data: pd.DataFrame, threshold: int):
    set_logger(INFO)
    try:
        LOGGER.info(f"Starting analysis for {root}")
        LOGGER.info(f"Input rename_data has {len(rename_data)} records")
        
        rename_data = filter_data(rename_data, threshold)
        LOGGER.info(f"After filtering: {len(rename_data)} records remain")
        
        commits = rename_data["commit"].unique()
        LOGGER.info(f"Processing {len(commits)} unique commits")
        
        out_dir = root.joinpath("archives")
        git_archive_args = [(root, out_dir, c) for c in commits]

        LOGGER.info("create archives")
        count = 0
        for i in git_archive_args:
            count += 1
            LOGGER.info(f"{count} / {len(git_archive_args)}")
            try:
                git_archive_wrapper(i)
                do_table(i[1], i[2])
            except Exception as e:
                LOGGER.error(f"Error processing archive {i[2]}: {e}")
                LOGGER.exception("Full traceback:")
                continue

        goldset_path = root.joinpath("goldset.json.gz")
        LOGGER.info(f"Saving goldset to {goldset_path}")
        rename_data.to_json(
            goldset_path,
            orient="records",
            indent=4,
            compression="gzip",
        )
        LOGGER.info(f"Successfully saved goldset with {len(rename_data)} records")

    except Exception as e:
        LOGGER.error(f"Critical error in analyzer main: {e}")
        LOGGER.exception("Full traceback:")
        raise  # Re-raise the exception instead of silently passing


def read_rename_file(root: pathlib.Path):
    json_path = root.joinpath("rename.json")
    if not os.path.isfile(json_path) or not os.path.exists(root.joinpath("repo")):
        LOGGER.error("repo does not exist")
        exit(1)
    rename_data = pd.read_json(json_path, orient="records")
    if rename_data.empty:
        LOGGER.info("rename.json is empty")
        exit(1)
    return rename_data


if __name__ == "__main__":
    args = set_argument()
    root = pathlib.Path(args.source)
    rename_data = read_rename_file(root)
    main(root, rename_data, args.threshold)

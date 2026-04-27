#!/usr/bin/env python3
import os
import subprocess
import json
import shutil
import argparse

parser = argparse.ArgumentParser(
    prog="scraping.py",
    description="This programs does a post-treatment to detect compilable MPI files that are suitable for mutation.",
)
parser.add_argument(
    "-s",
    "--source",
    required=True,
    help="Path to the input directory containing all scraped MPI repositories",
)
parser.add_argument(
    "-d",
    "--destination",
    required=True,
    help="Path to the output directory for compiled MPI files",
)
parser.add_argument(
    "-include",
    "--basic_include_paths",
    help="Basic include paths for compilation, e.g., -I/usr/include -I/usr/local/include, etc. This is in addition to the include paths found in the projects, to increase the chances of successful compilation.",
    default="",
)

# get arguments
args = parser.parse_args()

source_dir = args.source
destination_dir = args.destination
basic_include_paths = args.basic_include_paths

mpi_scraped_files = os.path.join(destination_dir, "scraped_mpi_files.json")
compilable_files = os.path.join(destination_dir, "compilable_files.json")
compile_commands = os.path.join(destination_dir, "compile_commands.json")


if not os.path.exists(mpi_scraped_files):
    with open(mpi_scraped_files, "w") as file:
        json.dump([], file)
if not os.path.exists(compilable_files):
    with open(compilable_files, "w") as file:
        json.dump([], file)


def save_mpi_file(file_path, mpi_files, mpi_scraped_files_path=mpi_scraped_files):
    """
    Saves the MPI file path in the json file. Does not overwrite the json list, and does not add the file path if it is already in the list.
    """
    if file_path not in mpi_files:
        mpi_files.append(file_path)
        with open(mpi_scraped_files_path, "w") as file:
            json.dump(mpi_files, file)
        return True
    return False


def is_mpi_file(file_path):
    """
    Check if the file contains the MPI include directive.
    """
    try:
        with open(file_path, "r") as file:
            for line in file:
                if "#include <mpi.h>" in line:
                    return True
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        pass
    except PermissionError:
        print(f"Error: Permission denied to read the file '{file_path}'.")
        pass
    except Exception as e:
        print(f"An unexpected error occurred while reading the file '{file_path}': {e}")
        pass

    return False


def is_c(file_path):
    return file_path.endswith(".c")


def filter_repos(repos_path, mpi_files):
    """
    Filters the repos to keep only the files that contain the MPI include directive. Does not delete the other files. Retains the MPI paths in the json file.
    """
    total_count = 0
    for author in os.listdir(repos_path):
        author_path = os.path.join(repos_path, author)

        if not os.path.isdir(author_path) or author == ".git":
            continue
        author_count = 0
        for repo in os.listdir(author_path):
            count = 0
            mpi_count = 0
            repo_path = os.path.join(author_path, repo)
            for root, _, files in os.walk(repo_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_c(file_path) and is_mpi_file(file_path):
                        added = save_mpi_file(file_path, mpi_files)
                        mpi_count += 1
                        if added:
                            print(f"MPI file retained and added: {file_path}")
                            count += 1
            if mpi_count == 0:
                print(f"No MPI files found in {repo_path}")
                shutil.rmtree(repo_path)
            author_count += count

        total_count += author_count

    print("total number of MPI files added: ", total_count)
    print("total number of MPI files found: ", len(mpi_files))


def is_in_compile_commands(file, path):
    """
    Check if the file is in the compile_commands.json file.
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)
            for entry in data:
                if entry["file"] == file:
                    return True
    except FileNotFoundError:
        print(f"Error: The file '{path}' was not found.")
        pass
    except PermissionError:
        print(f"Error: Permission denied to read the file '{path}'.")
        pass
    except Exception as e:
        print(f"An unexpected error occurred while reading the file '{path}': {e}")
        pass

    return False


# Counters and logs
success_count = failure_count = 0
error_log = []


def load_mpi_files(path):
    """Load MPI files from the JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def save_mpi_files(files, path):
    """Save the MPI files back to the JSON file."""
    with open(path, "w") as f:
        json.dump(files, f, indent=4)


def process_mpi_files(mpi_files):
    """Process each MPI file and returns the dirs that contain them."""
    mpi_dirs = {}
    for mpi_file in mpi_files:
        relative_path = os.path.relpath(mpi_file, source_dir)
        parts = relative_path.split(os.sep)
        if len(parts) < 3:
            error_log.append(f"Incorrect path: {mpi_file}")
            continue
        dir_path = os.path.dirname(mpi_file)
        mpi_dirs.setdefault(dir_path, []).append(mpi_file)

    return mpi_dirs


def collect_include_flags(project_paths):
    """
    Collect include flags for a list of project paths, ensuring each project
    is processed only once to avoid duplicate entries.

    Args:
        project_paths (list of str): List of paths to project directories.

    Returns:
        directory of str: Dictionary of project paths to include flags.

    """
    include_flags = {}
    for project_path in project_paths:
        flags = []
        for root, _, _ in os.walk(project_path):
            flags.append(f"-I{root}")
        include_flags[project_path] = flags

    return include_flags


def get_projects_paths():
    """Get the paths of all the projects in the MPI repos."""
    projects_paths = []
    for author in os.listdir(source_dir):
        author_path = os.path.join(source_dir, author)
        # check if the path is a directory
        if not os.path.isdir(author_path) or author == ".git":
            continue
        for project in os.listdir(author_path):
            project_path = os.path.join(author_path, project)
            projects_paths.append(project_path)

    return projects_paths


def generate_compile_commands(mpi_dirs):
    """Generate compilation commands for each directory using 'bear --append'."""
    global success_count, failure_count
    correct_files = []
    projects_paths = get_projects_paths()
    projects_include_flags = collect_include_flags(projects_paths)
    os.chdir(source_dir)
    for dir_path, files in mpi_dirs.items():

        # Prepare the include flags for the directory's project
        relative_path = os.path.relpath(dir_path, source_dir)
        parts = relative_path.split(os.sep)
        author, project = parts[:2]
        project_path = os.path.join(source_dir, author, project)
        include_flags = projects_include_flags.get(project_path, [])

        # Iterate over files in each directory
        for file in files:
            print(f"Processing file: {file}")

            # Construct the bear command for appending the file's compile command
            bear_command = (
                f"bear --append -- gcc  "
                f" {basic_include_paths} "
                f"-fsyntax-only  {' '.join(include_flags)} {file}"
            )

            try:
                subprocess.check_call(bear_command, shell=True)
                with open(compile_commands, "r") as f:
                    data = json.load(f)
                    for entry in data:
                        if entry["file"] == file:
                            break
                    else:
                        raise subprocess.CalledProcessError
                print(f"Successfully generated compilation commands for {file}")
                success_count += 1
                correct_files.append(file)
            except OSError as e:
                print(f"OS error: {e}")
                error_log.append(f"OS error for {file}: {e}")
                failure_count += 1
            except subprocess.CalledProcessError:
                print(
                    f"Error generating compilation commands for {file}, it will be ignored."
                )
                failure_count += 1

    print(f"\nSuccess : {success_count}")
    print(f"Failures : {failure_count}")
    save_mpi_files(correct_files, compilable_files)


def main():

    # load the already scraped mpi files if they exist
    mpi_files = load_mpi_files(mpi_scraped_files)

    # complete the process if needed
    filter_repos(source_dir, mpi_files)

    # generate the compile commands file
    mpi_dirs = process_mpi_files(mpi_files)
    generate_compile_commands(mpi_dirs)

    # print the info about the created files
    with open(mpi_scraped_files, "r") as f:
        data = json.load(f)
        print(f"Number of scraped MPI files: {len(data)}")
    with open(compilable_files, "r") as f:
        data = json.load(f)
        print(f"Number of compilable MPI files: {len(data)}")
    print(f"Compilation commands saved in: {compile_commands}")
    print(f"Scraped MPI files saved in: {mpi_scraped_files}")
    print(f"Compilable MPI files saved in: {compilable_files}")


if __name__ == "__main__":
    main()

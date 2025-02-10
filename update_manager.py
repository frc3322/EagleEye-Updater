import os
import shutil
import sys
import zipfile
from multiprocessing import freeze_support

import requests

freeze_support()

def get_base_dir():
    """
    Returns the directory where the executable (or script) resides.
    This ensures that updates are stored in a permanent folder rather than
    a temporary working directory.
    """
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundled exe, use the folder of the executable.
        return os.path.dirname(sys.executable)
    else:
        # Otherwise, use the directory of this script.
        return os.path.abspath(os.path.dirname(__file__))

def get_update_dir():
    """
    Returns the full path of the update folder (placed alongside the executable).
    """
    return os.path.join(get_base_dir(), "update")

def get_current_version():
    """
    Read the current downloaded version from update/version.txt.
    Returns the version string or None if not found.
    """
    update_dir = get_update_dir()
    version_file = os.path.join(update_dir, "version.txt")
    if os.path.exists(version_file):
        with open(version_file, "r") as vf:
            return vf.read().strip()
    return None

def get_latest_version():
    """
    Query GitHub for the latest release version.
    Returns the version string or None on error.
    """
    try:
        api_url = "https://api.github.com/repos/frc3322/EagleEye-Object-Detection/releases/latest"
        r = requests.get(api_url)
        if r.status_code == 200:
            release_info = r.json()
            return release_info.get("tag_name", "Unknown")
    except Exception as e:
        print(f"Error fetching latest version: {e}")
    return None

def download_update(log_callback=print):
    """
    Download the latest release from GitHub, extract it, and move its 'src' folder
    to the update directory (located alongside the executable). Also saves the
    downloaded version into update/version.txt.
    Returns the tag name if successful, otherwise None.
    """
    try:
        # Get release info
        api_url = "https://api.github.com/repos/frc3322/EagleEye-Object-Detection/releases/latest"
        r = requests.get(api_url)
        if r.status_code != 200:
            log_callback(f"Failed to get release info. Status code: {r.status_code}")
            return None

        release_info = r.json()
        tag_name = release_info.get("tag_name")
        zipball_url = release_info.get("zipball_url")
        log_callback(f"Latest release: {tag_name}")

        base_dir = get_base_dir()
        update_dir = get_update_dir()
        temp_zip_path = os.path.join(base_dir, "update.zip")
        block_size = 1024

        # Download the zip file
        r_zip = requests.get(zipball_url, stream=True)
        if r_zip.status_code != 200:
            log_callback(f"Failed to download zip file. Status code: {r_zip.status_code}")
            return None
        with open(temp_zip_path, "wb") as f:
            for data in r_zip.iter_content(block_size):
                f.write(data)
        log_callback("Downloaded zip file.")

        # Extract the zip file
        temp_extract_path = os.path.join(base_dir, "temp_update")
        if not os.path.exists(temp_extract_path):
            os.makedirs(temp_extract_path)
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_path)
        log_callback("Extracted zip file.")

        # The zip archive usually contains one top-level folder.
        extracted_dirs = [d for d in os.listdir(temp_extract_path)
                          if os.path.isdir(os.path.join(temp_extract_path, d))]
        if not extracted_dirs:
            log_callback("No directory found in the extracted zip.")
            return None
        top_level_dir = os.path.join(temp_extract_path, extracted_dirs[0])
        src_path = os.path.join(top_level_dir, "src")
        if not os.path.exists(src_path):
            log_callback("No 'src' folder found in the release.")
            return None

        # Remove any existing update folder and recreate it.
        if os.path.exists(update_dir):
            shutil.rmtree(update_dir)
        os.makedirs(update_dir, exist_ok=True)
        update_src = os.path.join(update_dir, "src")
        shutil.move(src_path, update_src)
        log_callback(f"Update downloaded and extracted to {update_src}.")

        # Save the version tag.
        with open(os.path.join(update_dir, "version.txt"), "w") as vf:
            vf.write(tag_name)

        # Clean up temporary files.
        os.remove(temp_zip_path)
        shutil.rmtree(temp_extract_path)

        return tag_name

    except Exception as e:
        log_callback(f"Error in download_update: {e}")
        return None

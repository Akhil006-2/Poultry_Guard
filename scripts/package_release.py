"""
Packaging script for PoultryGuard Full Release.
Creates C:\\Dev\\12hr\\PoultryGuard_Full.zip adhering strictly to preservation
and exclusion rules:
  - Preserves source code, models, database, evidence frames, docs, batch scripts
  - Excludes .venv, node_modules, __pycache__, .pytest_cache, .env secrets, local_output duplicates
"""

import os
import sys
import zipfile
from pathlib import Path

SOURCE_DIR = Path(r"C:\Dev\12hr\PoultryGuard_Full").resolve()
OUTPUT_ZIP = Path(r"C:\Dev\12hr\PoultryGuard_Full.zip").resolve()

EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "local_output",
    "dist_temp",
    ".idea",
    ".vscode"
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".swp"
}

EXCLUDE_FILES = {
    ".env",  # Exclude active local secrets; preserve .env.example
    "PoultryGuard_Full.zip"
}

def should_exclude(rel_path_parts):
    # Check if any parent folder is in EXCLUDE_DIRS
    for part in rel_path_parts:
        if part in EXCLUDE_DIRS:
            return True
    return False

def create_archive():
    print(f"Creating PoultryGuard archive: {OUTPUT_ZIP}")
    if OUTPUT_ZIP.exists():
        print(f"Removing pre-existing zip: {OUTPUT_ZIP}")
        OUTPUT_ZIP.unlink()

    total_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(SOURCE_DIR):
            rel_dir = os.path.relpath(root, SOURCE_DIR)
            rel_parts = Path(rel_dir).parts if rel_dir != "." else ()

            # Prune excluded directories in-place for speed
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            if should_exclude(rel_parts):
                continue

            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in EXCLUDE_EXTENSIONS:
                    continue

                abs_file = os.path.join(root, file)
                rel_file = os.path.relpath(abs_file, SOURCE_DIR)
                arcname = os.path.join("PoultryGuard_Full", rel_file)

                file_size = os.path.getsize(abs_file)
                total_files += 1
                total_uncompressed_bytes += file_size

                zf.write(abs_file, arcname)

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    uncomp_size_mb = total_uncompressed_bytes / (1024 * 1024)
    print("=" * 60)
    print("POULTRYGUARD PACKAGING COMPLETE")
    print(f"Target Archive:     {OUTPUT_ZIP}")
    print(f"Total Files Added:  {total_files}")
    print(f"Uncompressed Size:  {uncomp_size_mb:.2f} MB")
    print(f"Compressed Size:    {zip_size_mb:.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    create_archive()

"""Read embedded metadata from the WT .tif files and print any scale
information found (pixel size / resolution / spacing / microns-per-pixel).

Read-only diagnostic -- does not modify or write anything. Exists to answer
the question "is there a real calibration hiding in the file metadata, or
is PIXEL_SIZE_UM = None in config.py correct until someone measures it?"

Usage:
    python diagnostics/tools/inspect_tif_metadata.py --dir data/WT
"""

from __future__ import annotations

import argparse
from pathlib import Path

import tifffile


def describe(image_path: Path) -> None:
    print(f"=== {image_path.name} ===")
    with tifffile.TiffFile(image_path) as tf:
        page = tf.pages[0]

        # Standard TIFF resolution tags.
        found_any = False
        for tag_name in ("XResolution", "YResolution", "ResolutionUnit"):
            tag = page.tags.get(tag_name)
            if tag is not None:
                print(f"  tag {tag_name}: {tag.value}")
                found_any = True

        # Any other tag whose name hints at spatial calibration.
        keywords = ("resolution", "spacing", "pixel", "scale", "calibrat", "micron", "unit")
        for tag in page.tags.values():
            name_lower = tag.name.lower()
            if tag.name in ("XResolution", "YResolution", "ResolutionUnit"):
                continue
            if any(k in name_lower for k in keywords):
                print(f"  tag {tag.name}: {tag.value}")
                found_any = True

        # ImageJ metadata block (where ImageJ stores 'unit', 'spacing', etc.).
        if tf.imagej_metadata:
            print(f"  imagej_metadata: {tf.imagej_metadata}")
            found_any = True

        # OME-XML metadata, if present.
        if tf.ome_metadata:
            print("  ome_metadata: present (see full XML if needed)")
            found_any = True

        # Shaped/other metadata dicts tifffile may expose.
        if tf.shaped_metadata:
            print(f"  shaped_metadata: {tf.shaped_metadata}")
            found_any = True

        if not found_any:
            print("  No pixel-size / resolution / spacing metadata found.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Print embedded scale metadata from .tif files.")
    parser.add_argument("--dir", type=Path, required=True, help="Directory of .tif images.")
    args = parser.parse_args()

    for image_path in sorted(args.dir.glob("*.tif")):
        describe(image_path)


if __name__ == "__main__":
    main()

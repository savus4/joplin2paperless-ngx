import argparse
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from urllib.parse import unquote

import yaml
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def find_resource_paths(content: str, file_path: Path) -> List[Tuple[Path, str]]:
    """Finds all referenced resource paths in the file content and their intended extension."""
    resource_paths = []

    # Process <img> tags first to get suffix from type attribute (preferred) or alt text (fallback)
    img_tags = re.findall(r"<img [^>]*>", content)
    for tag in img_tags:
        src_match = re.search(r"src=['\"](.*?)['\"]", tag)
        type_match = re.search(r"type=['\"](.*?)['\"]", tag)
        alt_match = re.search(r"alt=['\"](.*?)['\"]", tag)

        if src_match:
            name = src_match.group(1)
            decoded_name = unquote(name)
            resource_path_obj = Path(decoded_name)
            resource_name = resource_path_obj.name
            intended_suffix = resource_path_obj.suffix

            # Use type attribute if available
            if type_match:
                mime_type = type_match.group(1).lower()
                # Map common mime types to file extensions
                mime_to_ext = {
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/bmp": ".bmp",
                    "image/tiff": ".tif",
                    "image/webp": ".webp",
                    "image/heic": ".heic",
                    "application/pdf": ".pdf",
                }
                if mime_type in mime_to_ext:
                    intended_suffix = mime_to_ext[mime_type]
            # Fallback to alt text if no type
            elif alt_match:
                alt_text = alt_match.group(1)
                alt_suffix = Path(alt_text).suffix
                if alt_suffix:
                    intended_suffix = alt_suffix

            path = file_path.parent.parent / "_resources" / resource_name
            if path.exists():
                resource_paths.append((path, intended_suffix))

    # Remove img tags from content to avoid double processing src attributes
    content_without_imgs = re.sub(r"<img [^>]*>", "", content)

    # Find markdown links: [alt text](link)
    md_links = re.findall(r"\[([^\]]*)\]\(([^)]*)\)", content_without_imgs)
    for alt_text, name in md_links:
        decoded_name = unquote(name)
        resource_path_obj = Path(decoded_name)
        resource_name = resource_path_obj.name
        intended_suffix = resource_path_obj.suffix

        if not intended_suffix and alt_text:
            alt_suffix = Path(alt_text).suffix
            if alt_suffix:
                resource_name += alt_suffix
                intended_suffix = alt_suffix

        path = file_path.parent.parent / "_resources" / resource_name
        if path.exists() and not any(p == path for p, _ in resource_paths):
            resource_paths.append((path, intended_suffix))

    # Find a href links: <a href="link" type="...">alt text</a>
    a_tags = re.findall(r"<a [^>]*>.*?</a>", content_without_imgs)
    for tag in a_tags:
        href_match = re.search(r"href=['\"](.*?)['\"]", tag)
        type_match = re.search(r"type=['\"](.*?)['\"]", tag)
        alt_text_match = re.search(r">(.*?)<", tag)

        if href_match:
            name = href_match.group(1)
            alt_text = ""
            if alt_text_match:
                alt_text = alt_text_match.group(1).strip()

            decoded_name = unquote(name)
            resource_path_obj = Path(decoded_name)
            resource_name = resource_path_obj.name
            intended_suffix = resource_path_obj.suffix

            # Use type attribute if available
            if type_match:
                mime_type = type_match.group(1).lower()
                mime_to_ext = {
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/bmp": ".bmp",
                    "image/tiff": ".tif",
                    "image/webp": ".webp",
                    "image/heic": ".heic",
                    "application/pdf": ".pdf",
                }
                if mime_type in mime_to_ext:
                    intended_suffix = mime_to_ext[mime_type]
            # Fallback to alt text if no type
            elif alt_text and intended_suffix not in [".jpg", ".jpeg", ".png", ".pdf", ".tif"]:
                alt_suffix = Path(alt_text).suffix
                if alt_suffix:
                    intended_suffix = alt_suffix

            path = file_path.parent.parent / "_resources" / resource_name
            if path.exists() and not any(p == path for p, _ in resource_paths):
                resource_paths.append((path, intended_suffix))

    return list(set(resource_paths))  # Return unique paths


def create_pdf_from_images(image_paths: List[Path], output_path: Path) -> None:
    """Creates a single PDF from a list of image paths."""
    if not image_paths:
        return

    pil_images = []
    for path in image_paths:
        try:
            image = Image.open(path)
            # Convert to RGB to avoid issues with different image modes (e.g., RGBA, P)
            if image.mode != "RGB":
                image = image.convert("RGB")
            pil_images.append(image)
        except IOError:
            logging.warning(f"Could not open or process image {path}. Skipping.")
            continue

    if not pil_images:
        logging.warning(f"No valid images found to create PDF for {output_path.name}")
        return

    # Use the first image to save the PDF and append the rest
    pil_images[0].save(
        output_path,
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=pil_images[1:],
    )


def process_joplin_export(joplin_export_dir: Path, output_dir: Path) -> None:
    """
    Processes a Joplin export directory, converting each note into a PDF.
    """
    docs_path = joplin_export_dir / "Dokumente"
    if not docs_path.is_dir():
        logging.error(f"'Dokumente' directory not found in '{joplin_export_dir}'")
        return

    output_dir.mkdir(exist_ok=True)

    for extension in ["*.md", "*.html"]:
        for file_path in docs_path.glob(extension):
            logging.info(f"Processing {file_path.name}...")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # --- Front Matter Parsing ---
            title = file_path.stem
            created_time = None
            try:
                # Simple split based on '---' separators
                parts = content.split("---")
                if len(parts) >= 3:
                    front_matter_str = parts[1]
                    front_matter = yaml.safe_load(front_matter_str)

                    if isinstance(front_matter, dict):
                        if "title" in front_matter and front_matter["title"]:
                            title = front_matter["title"]
                        if "created" in front_matter and front_matter["created"]:
                            # Try to parse the timestamp
                            try:
                                created_str = str(front_matter["created"]).replace(" ", "T")
                                created_time = datetime.fromisoformat(
                                    created_str.replace("Z", "+00:00")
                                ).timestamp()
                            except (ValueError, TypeError):
                                logging.warning(f"Could not parse 'created' timestamp: {front_matter['created']}")
            except yaml.YAMLError as e:
                logging.warning(f"Could not parse front matter for {file_path.name}: {e}")
            # --- End Front Matter Parsing ---

            resource_data = find_resource_paths(content, file_path)
            output_filename = f"{title}.pdf"
            output_filepath = output_dir / output_filename

            pdf_files = [p for p, ext in resource_data if ext.lower() == ".pdf"]
            # Define a set of common image file extensions to include
            image_extensions = {
                ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".heic"
            }
            image_files = [
                p
                for p, ext in resource_data
                if ext.lower() in image_extensions
            ]

            if pdf_files:
                if len(pdf_files) == 1:
                    shutil.copy(pdf_files[0], output_filepath)
                    logging.info(f"  Copied PDF to {output_filepath.name}")
                    if created_time:
                        os.utime(output_filepath, (created_time, created_time))
                else:
                    for i, pdf_path in enumerate(pdf_files):
                        output_filename_with_suffix = f"{title}_{i}.pdf"
                        output_filepath_with_suffix = (
                            output_dir / output_filename_with_suffix
                        )
                        shutil.copy(pdf_path, output_filepath_with_suffix)
                        logging.info(f"  Copied PDF to {output_filepath_with_suffix.name}")
                        if created_time:
                            os.utime(output_filepath_with_suffix, (created_time, created_time))

            elif image_files:
                create_pdf_from_images(image_files, output_filepath)
                logging.info(
                    f"  Created PDF from {len(image_files)} image(s) at {output_filepath.name}"
                )
                if created_time:
                    os.utime(output_filepath, (created_time, created_time))
            else:
                logging.warning(f"  No PDF or images found for {file_path.name}. Skipping.")


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Convert Joplin Markdown exports to PDFs for Paperless-NGX."
    )
    parser.add_argument(
        "joplin_export_dir",
        type=Path,
        help="The root directory of the Joplin 'Markdown + Front Matter' export.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="The directory where the generated PDFs will be saved.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose (debug) logging."
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Ensures output to stdout
    )

    if not args.joplin_export_dir.is_dir():
        logging.error(f"Joplin export directory not found at '{args.joplin_export_dir}'")
        return

    process_joplin_export(args.joplin_export_dir, args.output_dir)
    logging.info("Done.")


if __name__ == "__main__":
    main()

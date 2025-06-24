import argparse
import logging
import os
from pathlib import Path
from typing import Optional
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv


def get_file_dates(file_path: Path) -> str:
    """Get creation date in YYYY-MM-DD format (UTC), using st_birthtime on macOS if available."""
    stat = file_path.stat()
    if hasattr(stat, "st_birthtime"):
        created_ts = stat.st_birthtime
    else:
        created_ts = stat.st_ctime
    created = datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime("%Y-%m-%d")
    return created


def upload_pdf(
    api_url: str,
    api_token: str,
    pdf_path: Path,
    created: str,
    verify_ssl: bool = True
) -> Optional[int]:
    """Upload a PDF to Paperless-ngx and set its created date."""
    headers = {
        "Authorization": f"Token {api_token}",
    }
    try:
        with open(pdf_path, "rb") as f:
            files = {"document": f}
            data = {
                "created": created,
                "title": pdf_path.stem,
            }
            response = requests.post(
                f"{api_url.rstrip('/')}/api/documents/post_document/",
                headers=headers,
                files=files,
                data=data,
                verify=verify_ssl,
                timeout=30,
            )
        if response.status_code in [201, 200]:
            doc_id = response.json()
            logging.info("Uploaded %s as document ID %s", pdf_path.name, doc_id)
            return doc_id
        else:
            logging.error("Failed to upload %s: %s %s", pdf_path.name, response.status_code, response.text)
    except requests.RequestException as e:
        logging.error("Exception uploading %s: %s", pdf_path.name, e)
    except Exception as e:
        logging.error("Unexpected error uploading %s: %s", pdf_path.name, e)
    return None


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Upload PDFs to Paperless-ngx with correct dates.")
    parser.add_argument("--api-url", default=os.getenv("PAPERLESS_API_URL"), help="Paperless-ngx API base URL, is read from .env file as default (e.g. http://localhost:8000)")
    parser.add_argument("--api-token", default=os.getenv("PAPERLESS_API_TOKEN"), help="Paperless-ngx API token, is read from .env file as default")
    parser.add_argument("--pdf-folder", required=True, type=Path, help="Folder containing PDFs to upload")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification (not recommended)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    if not args.api_url or not args.api_token:
        logging.error("API URL and token must be provided via CLI or .env file.")
        return

    if not args.pdf_folder.is_dir():
        logging.error("PDF folder not found: %s", args.pdf_folder)
        return

    pdf_files = list(args.pdf_folder.glob("*.pdf"))
    if not pdf_files:
        logging.warning("No PDF files found in %s", args.pdf_folder)
        return

    for pdf_path in pdf_files:
        created = get_file_dates(pdf_path)
        upload_pdf(
            api_url=args.api_url,
            api_token=args.api_token,
            pdf_path=pdf_path,
            created=created,
            verify_ssl=not args.no_verify_ssl,
        )

if __name__ == "__main__":
    main()

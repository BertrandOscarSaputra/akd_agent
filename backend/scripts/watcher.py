"""Folder watcher for daily monitoring.

Detects new PDFs in a directory and automatically runs them through the API.
"""

import logging
import os
import time
from pathlib import Path

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_URL = os.environ.get("API_URL", "http://backend:8000")
PDF_DIR = os.environ.get("PDF_DIR", "/app/data/pdfs")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")


class PDFHandler(FileSystemEventHandler):
    """Handles new file creation events in the watch folder."""

    def on_created(self, event):
        """Called when a file or directory is created."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() == ".pdf":
            logger.info("New PDF detected: %s", file_path.name)
            self.process_pdf(file_path)

    def process_pdf(self, file_path: Path):
        """Send the PDF to the backend for processing."""
        # Wait a moment to ensure the file is completely written to disk
        time.sleep(2)

        try:
            # 1. Upload
            logger.info("Uploading %s to backend...", file_path.name)
            with open(file_path, "rb") as f:
                upload_res = requests.post(
                    f"{API_URL}/upload",
                    files={"file": (file_path.name, f, "application/pdf")}
                )
            upload_res.raise_for_status()
            doc_id = upload_res.json()["id"]
            logger.info("Uploaded successfully. Document ID: %s", doc_id)

            # 2. Extract and Classify
            logger.info("Starting extraction for %s (this may take a while)...", doc_id)
            extract_res = requests.post(
                f"{API_URL}/extract/{doc_id}",
                json={"deduplicate": True, "classify_akd": True}
            )
            extract_res.raise_for_status()
            logger.info("Extraction and classification complete for %s", doc_id)

            # 3. Download Reports
            self._download_report(doc_id, file_path.stem, "excel", ".xlsx")
            self._download_report(doc_id, file_path.stem, "word", ".docx")

            logger.info("✅ Processing completely finished for: %s", file_path.name)

        except Exception as e:
            logger.error("Failed to process %s: %s", file_path.name, str(e))

    def _download_report(self, doc_id: str, original_stem: str, format_type: str, ext: str):
        """Download a report from the backend and save it to the output dir."""
        try:
            logger.info("Downloading %s report...", format_type)
            res = requests.get(f"{API_URL}/documents/{doc_id}/export/{format_type}")
            res.raise_for_status()

            output_path = Path(OUTPUT_DIR) / f"Report_{original_stem}{ext}"
            with open(output_path, "wb") as f:
                f.write(res.content)
            logger.info("Saved report to %s", output_path)
        except Exception as e:
            logger.error("Failed to download %s report: %s", format_type, str(e))


def main():
    """Start the folder observer."""
    logger.info("Starting Watcher Service")
    logger.info("Watching directory: %s", PDF_DIR)
    logger.info("Output directory: %s", OUTPUT_DIR)
    logger.info("API URL: %s", API_URL)

    # Ensure directories exist
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, PDF_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()

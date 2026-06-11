import os
import time
import sys

# Configure standard streams to use UTF-8 encoding to avoid Windows console UnicodeEncodeError
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import WATCHED_DIR
from celery_app import process_file_task, delete_file_task

class DocumentHandler(FileSystemEventHandler):
    """Handles filesystem events and dispatches Celery tasks."""

    def on_created(self, event):
        # Ignore directory creations
        if event.is_directory:
            return
        print(f"[Watcher] File created: {event.src_path}. Sending indexing task to Celery...")
        process_file_task.delay(event.src_path)

    def on_modified(self, event):
        # Ignore directory modifications
        if event.is_directory:
            return
        print(f"[Watcher] File modified: {event.src_path}. Sending re-indexing task to Celery...")
        process_file_task.delay(event.src_path)

    def on_deleted(self, event):
        # Ignore directory deletions
        if event.is_directory:
            return
        print(f"[Watcher] File deleted: {event.src_path}. Sending deletion task to Celery...")
        delete_file_task.delay(event.src_path)

def start_watcher():
    # Ensure the directory exists before starting
    os.makedirs(WATCHED_DIR, exist_ok=True)
    
    event_handler = DocumentHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=True)
    
    print(f"\n=========================================")
    print(f"Starting Directory Monitor...")
    print(f"Watching folder: '{os.path.abspath(WATCHED_DIR)}'")
    print(f"Press Ctrl+C to stop.")
    print(f"=========================================\n")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Watcher] Stopping folder monitoring...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watcher()

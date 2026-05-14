import os
import zipfile
import gzip
import shutil
import threading
import ttkbootstrap as tb
from tkinter import filedialog, messagebox
from warcio.archiveiterator import ArchiveIterator
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("extraction.log", encoding="utf-8")
    ]
)

cancel_flag = False

def unzip_wacz(wacz_path, output_folder):
    logging.info(f"Extracting: {wacz_path}")
    try:
        with zipfile.ZipFile(wacz_path, 'r') as zip_ref:
            zip_ref.extractall(output_folder)
        logging.info(f"Successfully extracted: {wacz_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to extract {wacz_path}: {e}")
        return False

def extract_and_validate_warc_files(output_folder):
    archive_folder = os.path.join(output_folder, 'archive')
    warc_output_folder = os.path.join(output_folder, 'warc_files')
    os.makedirs(warc_output_folder, exist_ok=True)

    warc_files_extracted = 0
    if not os.path.exists(archive_folder):
        logging.warning(f"Archive folder not found: {archive_folder}")
        return 0

    for file_name in os.listdir(archive_folder):
        if cancel_flag:
            break
        if file_name.endswith(".warc.gz"):
            gz_file_path = os.path.join(archive_folder, file_name)
            warc_file_path = os.path.join(warc_output_folder, file_name[:-3])
            try:
                with gzip.open(gz_file_path, 'rb') as f_in, open(warc_file_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                with open(warc_file_path, 'rb') as stream:
                    for _ in ArchiveIterator(stream):
                        pass
                logging.info(f"Validated: {warc_file_path}")
                warc_files_extracted += 1
            except Exception as e:
                logging.error(f"Error validating {warc_file_path}: {e}")
    return warc_files_extracted

def collect_and_merge_warcs(folder):
    merged_folder = os.path.join(folder, "Merged_WARCs")
    os.makedirs(merged_folder, exist_ok=True)
    merged_count = 0

    for root, _, files in os.walk(folder):
        if os.path.basename(root) == "warc_files":
            for file in files:
                if file.endswith(".warc"):
                    src = os.path.join(root, file)
                    base = os.path.splitext(file)[0]
                    dst = os.path.join(merged_folder, file)
                    i = 1
                    while os.path.exists(dst):
                        dst = os.path.join(merged_folder, f"{base}_{i}.warc")
                        i += 1
                    shutil.move(src, dst)
                    merged_count += 1

    return merged_count

def process_collection_folder(folder, progress_var, status_label, cleanup_flag, time_var):
    global cancel_flag
    cancel_flag = False
    start_time = time.time()

    entries = os.listdir(folder)
    subfolders = [os.path.join(folder, d) for d in entries if os.path.isdir(os.path.join(folder, d))]
    top_level_wacz = [os.path.join(folder, f) for f in entries if f.endswith(".wacz")]
    total_items = len(subfolders) + len(top_level_wacz)
    processed = 0

    stats = {"collection": 0, "top": 0, "warcs": 0, "merged": 0, "deleted": 0}

    for sub in subfolders:
        if cancel_flag: break
        wacz_files = [f for f in os.listdir(sub) if f.endswith(".wacz")]
        warc_count = 0
        merged = 0

        for wacz_file in wacz_files:
            if cancel_flag: break
            stats["collection"] += 1
            wacz_path = os.path.join(sub, wacz_file)
            output = os.path.join(sub, f"{os.path.splitext(wacz_file)[0]}_output")
            warc_dir = os.path.join(output, "warc_files")

            # ✅ Skip already-processed WACZs
            if os.path.isdir(warc_dir) and any(f.endswith(".warc") for f in os.listdir(warc_dir)):
                logging.info(f"Skipping already-processed: {wacz_path}")
                continue

            os.makedirs(output, exist_ok=True)

            if unzip_wacz(wacz_path, output):
                warcs = extract_and_validate_warc_files(output)
                stats["warcs"] += warcs
                warc_count += warcs

        if warc_count > 0:
            merged = collect_and_merge_warcs(sub)
            stats["merged"] += merged

        if cleanup_flag and merged == warc_count and warc_count > 0:
            for wacz_file in wacz_files:
                try:
                    os.remove(os.path.join(sub, wacz_file))
                    stats["deleted"] += 1
                    logging.info(f"Deleted processed WACZ: {wacz_file}")
                except Exception as e:
                    logging.warning(f"Could not delete {wacz_file}: {e}")

        processed += 1
        update_progress(processed, total_items, start_time, progress_var, status_label, time_var)

    for wacz_path in top_level_wacz:
        if cancel_flag: break
        stats["top"] += 1
        output = os.path.join(folder, f"{os.path.splitext(os.path.basename(wacz_path))[0]}_output")
        warc_dir = os.path.join(output, "warc_files")

        if os.path.isdir(warc_dir) and any(f.endswith(".warc") for f in os.listdir(warc_dir)):
            logging.info(f"Skipping already-processed: {wacz_path}")
            continue

        os.makedirs(output, exist_ok=True)

        if unzip_wacz(wacz_path, output):
            warcs = extract_and_validate_warc_files(output)
            stats["warcs"] += warcs
            if cleanup_flag and warcs > 0:
                try:
                    os.remove(wacz_path)
                    stats["deleted"] += 1
                    logging.info(f"Deleted processed WACZ: {wacz_path}")
                except Exception as e:
                    logging.warning(f"Could not delete {wacz_path}: {e}")

        processed += 1
        update_progress(processed, total_items, start_time, progress_var, status_label, time_var)

    elapsed = round(time.time() - start_time)
    messagebox.showinfo("Summary",
        f"Collection WACZs: {stats['collection']}\nTop-level WACZs: {stats['top']}\n"
        f"WARCs extracted: {stats['warcs']}\nWARCs merged: {stats['merged']}\n"
        f"WACZs deleted: {stats['deleted']}\nTime taken: {elapsed}s")

def update_progress(done, total, start_time, progress_var, status_label, time_var):
    percent = round(100 * done / total, 1)
    elapsed = time.time() - start_time
    eta = (total - done) * (elapsed / done) if done else 0
    progress_var.set(percent)
    time_var.set(f"{int(elapsed)}s elapsed")
    status_label.config(text=f"{percent}% complete - ETA: {int(eta)}s")
    status_label.update()

def start_processing(input_dir, progress_var, status_label, cleanup_flag, time_var):
    thread = threading.Thread(
        target=process_collection_folder,
        args=(input_dir, progress_var, status_label, cleanup_flag, time_var)
    )
    thread.start()

def cancel_process():
    global cancel_flag
    cancel_flag = True
    logging.info("Cancelled by user.")

def export_log():
    dest = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
    if dest:
        shutil.copyfile("extraction.log", dest)
        messagebox.showinfo("Log Exported", f"Saved to {dest}")

def start_gui():
    root = tb.Window(themename='flatly')
    root.title("WACZ/WARC Processor")

    tb.Label(root, text="Select folder with WACZ files/collections:").pack(pady=5)
    entry_var = tb.StringVar()
    entry = tb.Entry(root, textvariable=entry_var, width=60)
    entry.pack(pady=5)

    def browse():
        folder = filedialog.askdirectory()
        if folder:
            entry_var.set(folder)

    tb.Button(root, text="Browse", command=browse).pack(pady=5)

    progress_var = tb.DoubleVar()
    tb.Progressbar(root, variable=progress_var, maximum=100).pack(pady=5)

    status_label = tb.Label(root, text="Status: Idle")
    status_label.pack(pady=5)

    time_var = tb.StringVar(value="0s elapsed")
    tb.Label(root, textvariable=time_var).pack()

    cleanup_var = tb.BooleanVar(value=False)
    tb.Checkbutton(root, text="Delete WACZs after successful processing", variable=cleanup_var).pack(pady=5)

    tb.Button(root, text="Start", command=lambda: start_processing(entry_var.get(), progress_var, status_label, cleanup_var.get(), time_var)).pack(pady=5)
    tb.Button(root, text="Cancel", command=cancel_process).pack(pady=2)
    tb.Button(root, text="Save Log", command=export_log).pack(pady=2)

    log_frame = tb.Frame(root)
    log_frame.pack(padx=5, pady=5, fill='both', expand=True)
    log_text = tb.Text(log_frame, height=10, wrap='word')
    log_text.pack(side='left', fill='both', expand=True)
    scrollbar = tb.Scrollbar(log_frame, command=log_text.yview)
    scrollbar.pack(side='right', fill='y')
    log_text.config(yscrollcommand=scrollbar.set)

    class LogHandler(logging.Handler):
        def emit(self, record):
            log_text.insert('end', self.format(record) + '\\n')
            log_text.see('end')

    gui_handler = LogHandler()
    gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(gui_handler)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
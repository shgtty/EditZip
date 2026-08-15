# EditZip

An interactive CLI tool to batch rename and remove files inside ZIP archives directly via a text editor / CSV interface—without extracting them.

## Features

- 📝 **Interactive CSV Editing**: Automatically opens a temporary CSV file listing all entries. Simply edit filenames or delete rows to rename or remove files.
- 🗂️ **Batch Processing**: Supports editing multiple ZIP files at once in a single session.
- ⚡ **In-Memory Reconstruction**: Rebuilds archives in memory with compression progress bars (`tqdm`), minimizing unnecessary disk I/O.
- 🛡️ **Safe by Default**: Original ZIP files are moved to the Trash/Recycle Bin using `send2trash` rather than being permanently deleted.
- 🖱️ **Drag-and-Drop Support**: Easily run on Windows by dragging and dropping ZIP files onto `EditZip.bat`.

## Requirements

- Python 3.7+
- Dependencies:
  ```bash
  pip install tqdm send2trash
  ```

## Usage

### Command Line
```bash
python edit_zip.py <path_to_zip_1> [path_to_zip_2 ...]
```

### Windows (Drag & Drop)
Drag and drop one or more `.zip` files onto `EditZip.bat`.

---

## How It Works

1. **Launch**: Run the script with one or more ZIP archive paths.
2. **Edit**: A temporary CSV file opens automatically in your default text editor (or configured editor):
   ```csv
   # ZIP Archive Configuration CSV
   # Format: zip_path, original_path, new_path, file_size
   zip_path, original_path, new_path, file_size
   C:\archives\sample.zip, old_name.txt, new_name.txt, 1.2 KB
   C:\archives\sample.zip, unwanted_file.log, unwanted_file.log, 500 B
   ```
   - **To Rename**: Change the value in the 3rd column (`new_path`).
   - **To Delete**: Delete the entire row.
3. **Apply**: Save and close your editor. `EditZip` will detect the changes, reconstruct the ZIP file(s), and move the original archive(s) to the trash.

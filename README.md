# EditZip

An interactive CLI tool to batch rename and remove files inside ZIP archives directly via a text editor / CSV interface—without extracting them.

## Features

- 📝 **Interactive CSV Editing**: Automatically opens a temporary CSV file listing all entries. Simply edit filenames or delete/comment-out rows (`#`) to rename or remove files.
- 🚫 **Auto Pre-commenting via Config**: Define unwanted keywords in `config.json` (e.g. `.DS_Store`, `__MACOSX`, `Thumbs.db`). Matching files are automatically pre-commented (`#`) in the editor for easy bulk removal.
- 🗂️ **Batch Processing**: Supports editing multiple ZIP files at once in a single session.
- ⚡ **In-Memory Reconstruction**: Rebuilds archives in memory with compression progress bars (`tqdm`), minimizing unnecessary disk I/O.
- 🛡️ **Safe by Default**: Original ZIP files are moved to the Trash/Recycle Bin using `send2trash` rather than being permanently deleted. If no changes or comments are kept, archives remain untouched.
- 🖱️ **Drag-and-Drop Support**: Easily run on Windows by dragging and dropping ZIP files onto `EditZip.bat`.

## Requirements

- Python 3.7+
- Dependencies:
  ```bash
  pip install tqdm send2trash
  ```

## Configuration (`config.json`)

You can configure keywords to automatically comment out matching files in the CSV editor. If `config.json` does not exist, it will be automatically created with default settings.

```json
{
  "exclude_keywords": [
    "__MACOSX",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini"
  ]
}
```

- Any files matching these keywords will appear commented out with a leading `#` in the editor.
- Leave them commented to remove them, or simply delete the `#` in your editor to keep the file.

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
2. **Edit**: A temporary CSV file opens automatically in your default text editor:
   ```csv
   # ZIP Archive Configuration CSV
   # Format: zip_path, original_path, new_path, file_size
   zip_path, original_path, new_path, file_size
   C:\archives\sample.zip, valid_file.txt, valid_file.txt, 1.2 KB
   #C:\archives\sample.zip, .DS_Store, .DS_Store, 500 B
   ```
   - **To Rename**: Change the value in the 3rd column (`new_path`).
   - **To Delete**: Delete the row or leave/add `#` at the start of the line.
   - **To Restore**: Remove `#` from pre-commented lines.
3. **Apply**: Save and close your editor. `EditZip` will detect the changes, reconstruct the ZIP file(s), and move the original archive(s) to the trash. If no changes are made, nothing is modified.

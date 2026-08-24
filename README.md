# EditZip

An interactive CLI tool to batch rename and remove files inside ZIP archives directly via a text editor / CSV interface—without extracting them.

## Features

- 📝 **Interactive CSV Editing**: Automatically opens a temporary CSV file listing all entries. Simply edit filenames or delete/comment-out rows (`#`) to rename or remove files.
- 🚫 **Auto Pre-commenting via Config**: Define unwanted keywords in `config.json` (e.g. `.DS_Store`, `__MACOSX`, `Thumbs.db`). Matching files are automatically pre-commented (`#`) in the editor for easy bulk removal.
- 🗂️ **Batch Processing**: Supports editing multiple ZIP files at once in a single session.
- 📁 **Directory Rename Mode**: Modify folder/directory names in bulk. Only unique folder paths are listed, allowing you to rename an entire directory hierarchy with just one edit.
- ⚡ **In-Memory Reconstruction**: Rebuilds archives in memory with compression progress bars (`tqdm`), minimizing unnecessary disk I/O.
- 🛡️ **Safe by Default**: Original ZIP files are moved to the Trash/Recycle Bin using `send2trash` rather than being permanently deleted. If no changes or comments are kept, archives remain untouched.
- 🖱️ **Drag-and-Drop Support**: Easily run on Windows by dragging and dropping ZIP files onto `EditZip.bat` (normal mode) or `EditZip_Dir.bat` (directory mode).

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

### 1. Normal Mode (File-level Editing)

#### Command Line
```bash
python edit_zip.py <path_to_zip_1> [path_to_zip_2 ...]
```

#### Windows (Drag & Drop)
Drag and drop one or more `.zip` files onto `EditZip.bat`.

---

### 2. Directory Mode (Bulk Folder Renaming)

Lists only folder/directory paths instead of all individual files. Modifying a folder name automatically moves and renames all files and subfolders under it.

#### Command Line
```bash
python edit_zip.py --dir <path_to_zip_1> [path_to_zip_2 ...]
# or shorthand:
python edit_zip.py -d <path_to_zip_1> [path_to_zip_2 ...]
```

#### Windows (Drag & Drop)
Drag and drop one or more `.zip` files onto `EditZip_Dir.bat`.

---

## How It Works

### Normal Mode CSV
```csv
# ZIP Archive Configuration CSV
# Format: zip_path, original_path, new_path, file_size
zip_path, original_path, new_path, file_size
C:\archives\sample.zip, old_dir/file.txt, old_dir/file.txt, 1.2 KB
#C:\archives\sample.zip, .DS_Store, .DS_Store, 500 B
```
- **To Rename**: Change the value in the 3rd column (`new_path`).
- **To Delete**: Delete the row or leave/add `#` at the start of the line.

### Directory Mode CSV
```csv
# ZIP Directory Rename Mode
# Format: zip_path, original_dir, new_dir
zip_path, original_dir, new_dir
C:\archives\sample.zip, old_dir/, new_dir/
C:\archives\sample.zip, old_dir/sub_folder/, old_dir/sub_folder/
```
- **To Rename Directory**: Change the 3rd column (`new_dir`). All files under that folder will be automatically renamed.
- **To Keep Untouched**: Leave as is, delete the line, or add `#` at the start of the line.


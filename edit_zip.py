import sys
import os
import zipfile
import tempfile
import subprocess
import csv
import io
import json
from collections import defaultdict
from tqdm import tqdm
from send2trash import send2trash

CONFIG_FILE_NAME = "config.json"
DEFAULT_CONFIG = {
    "exclude_keywords": [
        "__MACOSX",
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini"
    ]
}


def load_config():
    """スクリプトと同階層の config.json を読み込み、なければデフォルトを作成して返します。"""
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, CONFIG_FILE_NAME)

    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            return DEFAULT_CONFIG
        except Exception as e:
            print(f"警告: 設定ファイルの作成に失敗しました: {e}")
            return DEFAULT_CONFIG

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if not isinstance(config, dict):
                return DEFAULT_CONFIG
            return config
    except Exception as e:
        print(f"警告: 設定ファイル '{config_path}' の読み込みに失敗しました。デフォルト設定を使用します: {e}")
        return DEFAULT_CONFIG


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def edit_zips_interactive(zip_paths):
    # 設定ファイルの読み込み
    config = load_config()
    exclude_keywords = [
        kw.strip().lower() for kw in config.get("exclude_keywords", []) if isinstance(kw, str) and kw.strip()
    ]

    # 有効なパスのみ抽出
    valid_zip_paths = []
    for path in zip_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and zipfile.is_zipfile(abs_path):
            valid_zip_paths.append(abs_path)
        else:
            print(f"警告: 指定されたZIPファイル '{path}' が存在しないか無効なファイルです。スキップします。")

    if not valid_zip_paths:
        print("エラー: 処理対象の有効なZIPファイルがありません。")
        return

    # 1. 一時CSVファイルの作成 (全ZIPファイルのエントリーを1つのCSVに出力)
    original_mappings = defaultdict(list)
    with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False, encoding='utf-8-sig', newline='') as temp_file:
        temp_csv_path = temp_file.name
        writer = csv.writer(temp_file, lineterminator='\n')

        writer.writerow(["# ZIPファイル一括構成定義CSV"])
        writer.writerow(["# フォーマット: ZIPファイルパス, 元のファイルパス, 変更後のファイルパス, ファイルサイズ"])
        writer.writerow(["# 3列目(変更後のファイルパス)を書き換えるとリネームされます。"])
        writer.writerow(["# 行を削除するか先頭に '#' を付けると除外されます（設定ファイルのキーワードに該当するファイルは事前にコメントアウトされています）。"])
        writer.writerow(["# 編集完了後、保存してテキストエディタを閉じてください。"])
        writer.writerow([])
        writer.writerow(["zip_path", "original_path", "new_path", "file_size"])

        for z_path in valid_zip_paths:
            try:
                with zipfile.ZipFile(z_path, 'r') as zf:
                    infolist = zf.infolist()
                    for info in infolist:
                        name = info.filename
                        original_mappings[z_path].append((name, name))
                        size_str = format_size(info.file_size)

                        # 除外キーワードが含まれる場合は行頭に '#' を付与してコメントアウト状態で出力
                        is_excluded = any(kw in name.lower() for kw in exclude_keywords)
                        row_zip_path = f"#{z_path}" if is_excluded else z_path

                        writer.writerow([row_zip_path, name, name, size_str])
            except Exception as e:
                print(f"エラー: '{z_path}' の読み込み中に問題が発生しました: {e}")

    print(f"構成定義CSVを作成しました: {temp_csv_path}")
    print("テキストエディタを起動しています...")

    # 2. エディタの自動起動と待機
    try:
        if sys.platform == 'darwin':       # macOS
            subprocess.run(['open', '-W', '-t', temp_csv_path], check=True)
        elif sys.platform == 'win32':      # Windows
            subprocess.run(['C:\\Program Files\\Hidemaru\\Hidemaru.exe', temp_csv_path], check=True)
        else:                              # Linux / その他
            editor = os.environ.get('EDITOR', 'nano')
            subprocess.run([editor, temp_csv_path], check=True)
    except Exception as e:
        print(f"エラー: エディタの起動または待機中に問題が発生しました: {e}")
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        return

    print("エディタの終了を確認しました。構成を検証しています...")

    # 3. 編集されたCSVファイルの読み込みとパース (ZIPファイルごとにグループ化)
    parsed_mappings = defaultdict(list)
    with open(temp_csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            # コメント行のスキップ
            if row[0].startswith('#'):
                continue

            z_path = row[0].strip()
            if not z_path:
                continue

            # ヘッダー行のスキップ
            if z_path.lower() in ("zip_path", "zipfile", "zip_file", "zip") and len(row) > 1 and row[1].strip().lower() in ("original_path", "old_path", "original"):
                continue

            if len(row) < 2:
                continue

            old_name = row[1].strip()
            if not old_name:
                continue

            if len(row) >= 3:
                new_name = row[2].strip() or old_name
            else:
                new_name = old_name

            parsed_mappings[z_path].append((old_name, new_name))

    # 一時CSVファイルの削除
    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)

    # 4. ZIPファイルごとに更新チェックと処理の実施
    for z_path in valid_zip_paths:
        zip_filename = os.path.basename(z_path)
        orig_mapping = original_mappings.get(z_path, [])
        mapping = parsed_mappings.get(z_path, [])

        if not mapping:
            print(f"[{zip_filename}] 警告: エントリーがありません。スキップします。")
            continue

        if mapping == orig_mapping:
            print(f"[{zip_filename}] 変更が見つかりませんでした。スキップします。")
            continue

        print(f"[{zip_filename}] メモリ上で再構築しています...")
        temp_output_zip = f"{z_path}.tmp_{os.getpid()}.zip"

        try:
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(z_path, 'r') as src_zf:
                src_entries = set(src_zf.namelist())
                with zipfile.ZipFile(mem_zip, 'w', compression=zipfile.ZIP_DEFLATED) as dst_zf:
                    for old_name, new_name in tqdm(mapping, desc=f"[{zip_filename}] 圧縮中", unit="files"):
                        if old_name in src_entries:
                            data = src_zf.read(old_name)
                            dst_zf.writestr(new_name, data)
                        else:
                            tqdm.write(f"  警告: 元のZIP内に '{old_name}' が見つかりませんでした。スキップします。")

            # 完成したメモリ上のZIPを一括でディスクへ書き出し
            with open(temp_output_zip, 'wb') as f:
                f.write(mem_zip.getvalue())

            send2trash(z_path)
            os.replace(temp_output_zip, z_path)
            print(f"[{zip_filename}] 成功: 元ファイルをゴミ箱へ移動し、更新しました。")

        except Exception as e:
            print(f"[{zip_filename}] エラー: ZIPファイルの作成中にエラーが発生しました: {e}")
            if os.path.exists(temp_output_zip):
                os.remove(temp_output_zip)


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python edit_zip.py <ZIPファイルパス1> [ZIPファイルパス2 ...]")
        print("")
        print("説明:")
        print("  - 複数のZIPファイルパスを指定するか、ドラッグ＆ドロップで実行できます。")
        print("  - 実行すると全ZIP構成を含むCSVが自動で開き、保存して閉じると一括で更新されます。")
        sys.exit(1)

    edit_zips_interactive(sys.argv[1:])


if __name__ == "__main__":
    main()

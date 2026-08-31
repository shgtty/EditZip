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


def open_editor_and_wait(temp_csv_path):
    """OSごとのテキストエディタを起動して終了を待機します。"""
    try:
        if sys.platform == 'darwin':       # macOS
            subprocess.run(['open', '-W', '-t', temp_csv_path], check=True)
        elif sys.platform == 'win32':      # Windows
            subprocess.run(['C:\\Program Files\\Hidemaru\\Hidemaru.exe', temp_csv_path], check=True)
        else:                              # Linux / その他
            editor = os.environ.get('EDITOR', 'nano')
            subprocess.run([editor, temp_csv_path], check=True)
        return True
    except Exception as e:
        print(f"エラー: エディタの起動または待機中に問題が発生しました: {e}")
        return False


def get_valid_zip_paths(zip_paths):
    """指定されたパスリストから有効なZIPファイルの絶対パスを返します。"""
    valid = []
    for path in zip_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and zipfile.is_zipfile(abs_path):
            valid.append(abs_path)
        else:
            print(f"警告: 指定されたZIPファイル '{path}' が存在しないか無効なファイルです。スキップします。")
    return valid


def rebuild_zip_file(z_path, mapping):
    """マッピングに従ってZIPファイルをメモリ上で再構築し、元ファイルをゴミ箱へ移動して更新します。"""
    zip_filename = os.path.basename(z_path)
    print(f"[{zip_filename}] メモリ上で再構築しています...")
    temp_output_zip = f"{z_path}.tmp_{os.getpid()}.zip"

    try:
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(z_path, 'r') as src_zf:
            src_entries = set(src_zf.namelist())
            with zipfile.ZipFile(mem_zip, 'w', compression=zipfile.ZIP_DEFLATED) as dst_zf:
                for old_name, new_name in tqdm(mapping, desc=f"[{zip_filename}] 圧縮中", unit="files"):
                    # 空文字のエントリ（ディレクトリ階層削除時など）はスキップ
                    if not new_name or not new_name.strip('/'):
                        continue
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


def extract_directories(namelist):
    """ZIP内の全エントリからユニークなディレクトリ一覧（末尾スラッシュなし）を抽出して返します。"""
    dirs = set()
    for name in namelist:
        parts = [p for p in name.split('/') if p]
        if name.endswith('/'):
            curr = []
            for p in parts:
                curr.append(p)
                dirs.add("/".join(curr))
        else:
            if len(parts) > 1:
                curr = []
                for p in parts[:-1]:
                    curr.append(p)
                    dirs.add("/".join(curr))
    # 階層の浅い順 -> アルファベット順でソート
    return sorted(dirs, key=lambda d: (d.count('/'), d))


def edit_zips_dir_mode(zip_paths):
    """ディレクトリ名変更モード: ディレクトリ一覧のみをCSVに出力し、一括でリネームします。"""
    config = load_config()
    exclude_keywords = [
        kw.strip().lower() for kw in config.get("exclude_keywords", []) if isinstance(kw, str) and kw.strip()
    ]

    valid_zip_paths = get_valid_zip_paths(zip_paths)
    if not valid_zip_paths:
        print("エラー: 処理対象の有効なZIPファイルがありません。")
        return

    # 1. 一時CSVファイルの作成 (全ZIPファイルのディレクトリ一覧を出力)
    zip_entries_map = {}
    with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False, encoding='utf-8-sig', newline='') as temp_file:
        temp_csv_path = temp_file.name
        writer = csv.writer(temp_file, lineterminator='\n')

        writer.writerow(["# ZIPディレクトリ名変更モード"])
        writer.writerow(["# フォーマット: ZIPファイルパス, 元のディレクトリ名, 変更後のディレクトリ名"])
        writer.writerow(["# 3列目(変更後のディレクトリ名)を書き換えると、そのディレクトリ配下のすべてのファイル/フォルダが一括リネームされます。"])
        writer.writerow(["# 3列目を空にすると、ディレクトリ階層が削除され配下のファイルがルート直下に移動します。"])
        writer.writerow(["# 行を削除するか先頭に '#' を付けると変更されません。"])
        writer.writerow(["# 編集完了後、保存してテキストエディタを閉じてください。"])
        writer.writerow([])
        writer.writerow(["zip_path", "original_dir", "new_dir"])

        for z_path in valid_zip_paths:
            try:
                with zipfile.ZipFile(z_path, 'r') as zf:
                    namelist = [info.filename for info in zf.infolist()]
                    zip_entries_map[z_path] = namelist
                    dir_list = extract_directories(namelist)

                    if not dir_list:
                        print(f"[{os.path.basename(z_path)}] 情報: ディレクトリ構造が存在しません（ルート直下のファイルのみ）。")

                    for d_name in dir_list:
                        is_excluded = any(kw in d_name.lower() for kw in exclude_keywords)
                        row_zip_path = f"#{z_path}" if is_excluded else z_path
                        writer.writerow([row_zip_path, d_name, d_name])
            except Exception as e:
                print(f"エラー: '{z_path}' の読み込み中に問題が発生しました: {e}")

    print(f"ディレクトリ構成定義CSVを作成しました: {temp_csv_path}")
    print("テキストエディタを起動しています...")

    # 2. エディタ起動と待機
    if not open_editor_and_wait(temp_csv_path):
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        return

    print("エディタの終了を確認しました。構成を検証しています...")

    # 3. 編集されたCSVファイルの読み込みとパース
    parsed_dir_rules = defaultdict(list)
    with open(temp_csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#'):
                continue

            z_path = row[0].strip()
            if not z_path:
                continue

            if z_path.lower() in ("zip_path", "zipfile", "zip_file", "zip") and len(row) > 1 and row[1].strip().lower() in ("original_dir", "old_dir", "original_path"):
                continue

            if len(row) < 2:
                continue

            old_dir = row[1].strip()
            if not old_dir:
                continue

            if len(row) >= 3:
                new_dir = row[2].strip()
            else:
                new_dir = old_dir

            parsed_dir_rules[z_path].append((old_dir, new_dir))

    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)

    # 4. ZIPファイルごとに置換ルールを適用して再構築
    for z_path in valid_zip_paths:
        zip_filename = os.path.basename(z_path)
        src_entries = zip_entries_map.get(z_path, [])
        dir_rules = parsed_dir_rules.get(z_path, [])

        # 変更されたルール (old_dir != new_dir) のみを抽出
        changed_rules = []
        for old_d, new_d in dir_rules:
            clean_old = old_d.strip().strip('/')
            clean_new = new_d.strip().strip('/')

            if not clean_old:
                continue

            # 内部のパス一致判定用に末尾スラッシュを付与（clean_new が空の場合はルート直下に移動するため空文字のまま）
            norm_old_d = clean_old + '/'
            norm_new_d = (clean_new + '/') if clean_new else ""

            if norm_old_d != norm_new_d:
                changed_rules.append((norm_old_d, norm_new_d))

        if not changed_rules:
            print(f"[{zip_filename}] 変更が見つかりませんでした。スキップします。")
            continue

        # 最長プレフィックス一致のために old_d の長さ降順でソート
        changed_rules.sort(key=lambda r: len(r[0]), reverse=True)

        mapping = []
        for entry in src_entries:
            new_entry = entry
            for old_d, new_d in changed_rules:
                if entry.startswith(old_d):
                    new_entry = new_d + entry[len(old_d):]
                    break
            mapping.append((entry, new_entry))

        rebuild_zip_file(z_path, mapping)


def edit_zips_interactive(zip_paths):
    # 設定ファイルの読み込み
    config = load_config()
    exclude_keywords = [
        kw.strip().lower() for kw in config.get("exclude_keywords", []) if isinstance(kw, str) and kw.strip()
    ]

    valid_zip_paths = get_valid_zip_paths(zip_paths)
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
    if not open_editor_and_wait(temp_csv_path):
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

        rebuild_zip_file(z_path, mapping)


def main():
    args = sys.argv[1:]
    if not args:
        print("使用方法:")
        print("  通常モード (ファイル単位の編集):")
        print("    python edit_zip.py <ZIPファイルパス1> [ZIPファイルパス2 ...]")
        print("")
        print("  ディレクトリ名変更モード (ディレクトリ名のみ抽出して一括変更):")
        print("    python edit_zip.py --dir <ZIPファイルパス1> [ZIPファイルパス2 ...]")
        print("    python edit_zip.py -d <ZIPファイルパス1> [ZIPファイルパス2 ...]")
        print("")
        print("説明:")
        print("  - 複数のZIPファイルパスを指定するか、ドラッグ＆ドロップで実行できます。")
        print("  - 実行すると構成CSVが自動で開き、保存して閉じると一括で更新されます。")
        sys.exit(1)

    dir_mode = False
    zip_paths = []
    for arg in args:
        if arg in ('--dir', '-d', '/d', '/dir'):
            dir_mode = True
        else:
            zip_paths.append(arg)

    if not zip_paths:
        print("エラー: 処理対象のZIPファイルが指定されていません。")
        sys.exit(1)

    if dir_mode:
        edit_zips_dir_mode(zip_paths)
    else:
        edit_zips_interactive(zip_paths)


if __name__ == "__main__":
    main()

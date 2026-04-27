# fix_encoding.py
# 文字化けしているHTMLファイルを自動で検出・修正するスクリプト
# 使い方: python fix_encoding.py

import os
import glob

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
UTF8 = 'utf-8'
SJIS = 'shift_jis'
ENCODINGS_TO_TRY = [SJIS, 'cp932', 'latin-1']

def fix_file(filepath):
    filename = os.path.basename(filepath)

    with open(filepath, 'rb') as f:
        raw = f.read()

    # BOM付きUTF-8 → BOMなしUTF-8に変換
    if raw.startswith(b'\xef\xbb\xbf'):
        content = raw[3:].decode('utf-8', errors='replace')
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        print(f'✅ BOM除去: {filename}')
        return True

    # UTF-8として読んで問題なければOK
    try:
        content = raw.decode('utf-8')
        if '\ufffd' not in content:
            print(f'⬜ 正常:    {filename}')
            return False
    except UnicodeDecodeError:
        pass

    # 文字化けあり → 別エンコードで読み直してUTF-8で保存
    for enc in ENCODINGS_TO_TRY:
        try:
            content = raw.decode(enc)
            # 読み直した内容にShift-JIS特有の文字があるか確認
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            print(f'✅ 修正({enc}→UTF-8): {filename}')
            return True
        except (UnicodeDecodeError, LookupError):
            continue

    print(f'❌ 修正失敗: {filename}')
    return False

def main():
    print('=' * 50)
    print('文字化け自動修正スクリプト')
    print('=' * 50)

    html_files = glob.glob(os.path.join(TEMPLATES_DIR, '*.html'))

    if not html_files:
        print(f'❌ templatesフォルダが見つかりません: {TEMPLATES_DIR}')
        return

    fixed = 0
    for filepath in sorted(html_files):
        if fix_file(filepath):
            fixed += 1

    print('=' * 50)
    print(f'完了！ {fixed}件修正しました（全{len(html_files)}ファイル）')

if __name__ == '__main__':
    main()

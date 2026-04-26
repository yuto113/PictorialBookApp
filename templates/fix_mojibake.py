import os
import glob

def main():
    # 元のHTMLファイルがあるフォルダ（現在のフォルダなら '.'）
    source_dir = '.'
    # 修正後のファイルを保存するフォルダ
    output_dir = './fixed_html'

    # 保存用フォルダを作成（すでに存在する場合はエラーにならない）
    os.makedirs(output_dir, exist_ok=True)

    # 現在のフォルダにある .html と .htm ファイルをすべて取得
    html_files = glob.glob(f"{source_dir}/*.html") + glob.glob(f"{source_dir}/*.htm")

    if not html_files:
        print("HTMLファイルが見つかりません。")
        return

    for file_path in html_files:
        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)

        try:
            # 1. 文字化けした状態のテキストをUTF-8として読み込む
            with open(file_path, 'r', encoding='utf-8') as f:
                mojibake_text = f.read()

            # 2. 誤って解釈された文字コード(cp932)のバイト列に戻し、正しいUTF-8でデコードし直す
            # ※完全に復元できない文字（「・」など）はエラー回避のため 'replace' で処理します
            fixed_text = mojibake_text.encode('cp932', errors='replace').decode('utf-8', errors='replace')

            # 3. 修正したテキストを新しいフォルダにUTF-8で保存する
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(fixed_text)

            print(f"✅ 修正成功: {filename}")
            
        except Exception as e:
            print(f"❌ エラー {filename}: {e}")

    print(f"\n🎉 すべての処理が完了しました！ '{output_dir}' フォルダの中身を確認してください。")

if __name__ == "__main__":
    main()
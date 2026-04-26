"""
templates/フォルダの文字化けを自動修正するスクリプト
"""
import os

templates_dir = 'templates'

replacements = {
    '図鑁E': '図鑑',
    '鑁E': '鑑',
    '蝗ｳ髑': '図鑑',
    '繧ｪ繝ｳ繝ｩ繧': 'オンライン',
    '縺ｮ': 'の',
    '縺励∪': 'しま',
    '縺励◆': 'した',
    '縺ｦ縺': 'てく',
    '縺上□': 'ださ',
    '縺輔＞': 'さい',
    '縺ｾ縺': 'まで',
    '縺励※': 'して',
    '縺ゅｊ': 'あり',
    '縺ｾ縺帙ｓ': 'ません',
    '縺ｾ縺吶': 'ます',
    '縺倥ａ': 'じめ',
    '縺ｯ縺': 'はじ',
    '繝ｭ繧ｰ繧': 'ログイ',
    '繝ｼ繧ｸ': 'ージ',
    '繝代せ繝ｯ繝ｼ繝': 'パスワード',
    '蜷榊燕': '名前',
    '謚慕ｨｿ': '投稿',
    '蟄ｦ譬｡': '学校',
    '邂｡逅': '管理',
    '逕溷ｾ': '学生',
    '謨吝ｸｫ': '教師',
    '繧ｯ繝ｩ繧ｹ': 'クラス',
    '隱ｲ鬘': '課題',
    '蜿嶺ｻ': '受付',
    '邱繧': '締め',
    '蜑企勁': '削除',
    '謌ｻ繧': '戻る',
    '繝帙・繝': 'ホーム',
    '逋ｻ骭ｲ': '登録',
    '蛻ｩ逕ｨ': '利用',
    '隕冗ｴ': '規約',
    '繝輔ぅ繝ｼ繝峨ヰ繝・け': 'フィードバック',
    '繝ｬ繝薙Η繝ｼ': 'レビュー',
    '繝輔Ξ繝ｳ繝': 'フレンド',
    '莉悶': '他の',
    '閾ｪ蛻': '自分',
    '縺ｻ縺': 'ほか',
}

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original = content
    
    # cp932でエンコードしてUTF-8に戻す
    try:
        fixed = content.encode('cp932', errors='ignore').decode('utf-8', errors='ignore')
        if 'の' in fixed or 'を' in fixed or 'に' in fixed:
            content = fixed
    except:
        pass
    
    # 残った文字化けパターンを置換
    for broken, fixed_str in replacements.items():
        content = content.replace(broken, fixed_str)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return True
    return False

html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
fixed = 0
for filename in html_files:
    filepath = os.path.join(templates_dir, filename)
    if fix_file(filepath):
        print(f'✅ Fixed: {filename}')
        fixed += 1
    else:
        print(f'⏭️  OK: {filename}')

print(f'\n🎉 {fixed}ファイルを修正しました')
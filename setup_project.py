#!/usr/bin/env python3
"""
プロジェクト初期化スクリプト
必要なディレクトリとファイルを自動作成します
"""
import os
from pathlib import Path

def create_directory_structure():
    """ディレクトリ構造の作成"""
    print("📁 ディレクトリ構造を作成中...")
    
    directories = [
        # コアモジュール
        'core',
        
        # 機能モジュール（今後実装）
        'modules',
        
        # データ保存
        'data',
        'data/images',
        'data/images/mercari',
        'data/images/alibaba', 
        'data/images/training',
        'data/images/training/professional',
        'data/images/training/amateur',
        'data/models',
        'data/backup',
        
        # ブラウザドライバー
        'drivers',
        
        # ログファイル
        'logs',
        
        # 出力結果
        'results',
        
        # テストコード
        'tests'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")
    
    print("✅ ディレクトリ構造の作成完了")

def create_init_files():
    """__init__.pyファイルの作成"""
    print("📄 __init__.pyファイルを作成中...")
    
    init_files = [
        'modules/__init__.py',
        'tests/__init__.py'
    ]
    
    for init_file in init_files:
        file_path = Path(init_file)
        if not file_path.exists():
            file_path.write_text('# -*- coding: utf-8 -*-\n')
            print(f"  ✅ {init_file}")
    
    print("✅ __init__.pyファイルの作成完了")

def create_gitignore():
    """gitignoreファイルの作成"""
    print("🚫 .gitignoreファイルを作成中...")
    
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# システム固有
.DS_Store
Thumbs.db

# プロジェクト固有
.env
.encryption_key
config.ini
data/database.db
data/backup/
logs/
results/
drivers/
*.log

# 一時ファイル
temp/
tmp/
cache/

# 商品画像（大量になるため）
data/images/mercari/*
data/images/alibaba/*
!data/images/mercari/.gitkeep
!data/images/alibaba/.gitkeep

# AIモデルファイル（サイズが大きいため）
data/models/*.h5
data/models/*.pkl
!data/models/.gitkeep

# 機密情報
*.key
*.pem
credentials.json
"""
    
    Path('.gitignore').write_text(gitignore_content.strip())
    print("✅ .gitignoreファイルの作成完了")

def create_gitkeep_files():
    """空ディレクトリ用の.gitkeepファイルを作成"""
    print("📌 .gitkeepファイルを作成中...")
    
    gitkeep_dirs = [
        'data/images/mercari',
        'data/images/alibaba',
        'data/images/training/professional',
        'data/images/training/amateur',
        'data/models',
        'data/backup',
        'drivers',
        'logs',
        'results',
        'tests'
    ]
    
    for directory in gitkeep_dirs:
        gitkeep_path = Path(directory) / '.gitkeep'
        gitkeep_path.write_text('')
        print(f"  ✅ {gitkeep_path}")
    
    print("✅ .gitkeepファイルの作成完了")

def create_config_ini():
    """デフォルトconfig.iniの作成"""
    print("⚙️  config.iniファイルを作成中...")
    
    if Path('config.ini').exists():
        print("  ℹ️  config.iniは既に存在します")
        return
    
    # Configクラスを使用してデフォルト設定を作成
    try:
        from core.config import Config
        config = Config()
        print("✅ config.iniファイルの作成完了")
    except ImportError:
        print("  ⚠️  core.configモジュールが見つかりません")

def create_env_file():
    """.envファイルの作成"""
    print("🔐 .envファイルを作成中...")
    
    if Path('.env').exists():
        print("  ℹ️  .envファイルは既に存在します")
        return
    
    if Path('.env.template').exists():
        import shutil
        shutil.copy('.env.template', '.env')
        print("✅ .env.templateから.envを作成しました")
        print("  ⚠️  .envファイルに実際の値を設定してください")
    else:
        print("  ⚠️  .env.templateが見つかりません")

def create_batch_files():
    """Windowsバッチファイルの作成"""
    print("🔧 バッチファイルを作成中...")
    
    # テスト実行用バッチ
    test_bat = """@echo off
echo テスト実行中...
python test_setup.py
pause
"""
    
    Path('test.bat').write_text(test_bat)
    print("  ✅ test.bat")
    
    # 環境構築用バッチ
    install_bat = """@echo off
echo 環境構築を開始します...

echo Python仮想環境を作成中...
python -m venv venv

echo 仮想環境を有効化中...
call venv\\Scripts\\activate.bat

echo 依存関係をインストール中...
pip install -r requirements.txt

echo Playwrightブラウザをインストール中...
playwright install chromium

echo 環境構築完了！
pause
"""
    
    Path('install.bat').write_text(install_bat)
    print("  ✅ install.bat")
    
    print("✅ バッチファイルの作成完了")

def show_next_steps():
    """次のステップを表示"""
    print("\n" + "=" * 60)
    print("🎉 プロジェクト初期化完了！")
    print("=" * 60)
    print()
    print("📋 次のステップ:")
    print()
    print("1. 依存関係のインストール:")
    print("   pip install -r requirements.txt")
    print()
    print("2. 環境変数の設定:")
    print("   .envファイルを編集してアカウント情報を設定")
    print()
    print("3. テストの実行:")
    print("   python test_setup.py")
    print()
    print("4. 動作確認:")
    print("   python -c \"from core import Config, Database; print('✅ インポート成功')\"")
    print()
    print("💡 ヒント:")
    print("   - Windowsの場合: install.bat を実行すると自動で環境構築されます")
    print("   - テストの場合: test.bat を実行すると基盤機能をテストできます")
    print()

def main():
    """メイン実行"""
    print("🚀 メルカリ自動化システム プロジェクト初期化")
    print("=" * 60)
    
    try:
        create_directory_structure()
        create_init_files()
        create_gitignore()
        create_gitkeep_files()
        create_config_ini()
        create_env_file()
        create_batch_files()
        
        show_next_steps()
        
    except Exception as e:
        print(f"❌ 初期化中にエラーが発生しました: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
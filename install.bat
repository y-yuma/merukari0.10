@echo off
echo 環境構築を開始します...

echo Python仮想環境を作成中...
python -m venv venv

echo 仮想環境を有効化中...
call venv\Scripts\activate.bat

echo 依存関係をインストール中...
pip install -r requirements.txt

echo Playwrightブラウザをインストール中...
playwright install chromium

echo 環境構築完了！
pause

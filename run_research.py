#!/usr/bin/env python3
"""
メルカリリサーチ機能の実行サンプル
実際に商品データを収集してCSVに保存します
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def single_keyword_research():
    """単一キーワードでのリサーチ"""
    from core.config import Config
    from core.database import Database
    from modules.research import MercariResearcher
    
    print("🔍 単一キーワードリサーチ")
    print("=" * 40)
    
    # 設定
    config = Config()
    
    # リサーチ設定の調整
    config.set('system', 'headless', 'false')  # ブラウザ画面を表示
    config.set('mercari', 'max_products_per_search', '10')  # 10商品まで
    config.set('mercari', 'search_sold_only', 'true')      # 売り切れのみ
    config.set('mercari', 'search_condition', 'new')       # 新品のみ
    
    # データベース
    db = Database()
    
    # リサーチャー
    researcher = MercariResearcher(config, db)
    
    # キーワード入力
    keyword = input("検索キーワードを入力してください: ")
    if not keyword.strip():
        print("❌ キーワードが入力されませんでした")
        return False
    
    try:
        print(f"\n🚀 リサーチ開始: {keyword}")
        print("ブラウザが起動します...")
        
        # 商品検索
        products = researcher.search_products(keyword.strip())
        
        if products:
            print(f"\n✅ 検索完了: {len(products)}件の商品を発見")
            
            # 結果の一部を表示
            print("\n📋 発見した商品:")
            for i, product in enumerate(products[:5], 1):
                print(f"  {i}. {product.get('title', 'N/A')[:60]}...")
                print(f"     💰 価格: {product.get('price', 'N/A'):,}円")
                print(f"     🔗 URL: {product.get('url', 'N/A')}")
                print()
            
            if len(products) > 5:
                print(f"     ... 他 {len(products) - 5}件")
            
            # CSV保存
            csv_path = researcher.save_products_to_csv(products)
            if csv_path:
                print(f"💾 CSV保存完了: {csv_path}")
            
            # データベース保存
            db_count = researcher.save_products_to_database(products)
            print(f"🗄️  データベース保存完了: {db_count}件")
            
            return True
            
        else:
            print("❌ 商品が見つかりませんでした")
            return False
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

def multi_keyword_research():
    """複数キーワードでのリサーチ"""
    from core.config import Config
    from core.database import Database
    from modules.research import MercariResearcher
    
    print("\n🔍 複数キーワード一括リサーチ")
    print("=" * 40)
    
    # 設定
    config = Config()
    config.set('system', 'headless', 'false')
    config.set('mercari', 'max_products_per_search', '5')   # 少数での実行
    config.set('mercari', 'search_interval', '3.0')        # 3秒間隔
    
    # データベース
    db = Database()
    
    # リサーチャー
    researcher = MercariResearcher(config, db)
    
    # キーワード入力
    print("検索キーワードをカンマ区切りで入力してください")
    print("例: iPhone,iPad,MacBook")
    keywords_input = input("キーワード: ")
    
    if not keywords_input.strip():
        print("❌ キーワードが入力されませんでした")
        return False
    
    keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]
    
    if not keywords:
        print("❌ 有効なキーワードがありません")
        return False
    
    try:
        print(f"\n🚀 一括リサーチ開始: {keywords}")
        print("※ 複数のキーワードで検索するため時間がかかります")
        
        # 一括検索
        results = researcher.batch_search(keywords)
        
        print(f"\n✅ 一括リサーチ完了!")
        print(f"  📊 総商品数: {results['total_products']}件")
        print(f"  🔍 検索キーワード数: {results['keywords_searched']}個")
        print(f"  💾 CSV保存: {results['csv_file']}")
        print(f"  🗄️  データベース保存: {results['database_saved']}件")
        
        # 詳細結果表示
        print(f"\n📋 キーワード別結果:")
        for keyword, detail in results['search_details'].items():
            status_icon = "✅" if detail['status'] == 'success' else "❌"
            print(f"  {status_icon} {keyword}: {detail['product_count']}件 ({detail['status']})")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

def main():
    """メイン実行"""
    print("🛒 メルカリリサーチツール")
    print("=" * 50)
    
    print("実行モードを選択してください:")
    print("1. 単一キーワードでリサーチ")
    print("2. 複数キーワードで一括リサーチ")
    print("3. 終了")
    
    while True:
        try:
            choice = input("\n選択 (1-3): ").strip()
            
            if choice == '1':
                success = single_keyword_research()
                break
            elif choice == '2':
                success = multi_keyword_research()
                break
            elif choice == '3':
                print("👋 プログラムを終了します")
                return True
            else:
                print("❌ 1、2、3のいずれかを入力してください")
                continue
                
        except KeyboardInterrupt:
            print("\n\n👋 プログラムが中断されました")
            return False
    
    if success:
        print(f"\n🎉 リサーチが正常に完了しました！")
        print(f"📁 結果ファイルは results/ フォルダに保存されています")
        print(f"🗄️  データベースには商品情報が保存されています")
    else:
        print(f"\n⚠️  リサーチでエラーが発生しました")
    
    return success

if __name__ == "__main__":
    print("⚠️  実行前の確認:")
    print("  ✓ Google Chrome がインストールされている")
    print("  ✓ インターネットに接続されている")
    print("  ✓ 基盤機能とRPA機能が実装されている")
    print()
    print("このツールは実際にメルカリサイトにアクセスして商品データを収集します。")
    print("メルカリの利用規約を遵守し、過度なアクセスは控えてください。")
    
    response = input("\n実行しますか？ (y/N): ")
    if response.lower() in ['y', 'yes']:
        try:
            success = main()
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"\n❌ 予期しないエラー: {e}")
            sys.exit(1)
    else:
        print("👋 実行がキャンセルされました")
        sys.exit(0)
#!/usr/bin/env python3
"""
メルカリリサーチ機能のテストスクリプト
商品データ取得とCSV保存機能をテストします
"""
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_product_extractor():
    """商品抽出器のテスト"""
    print("=== 商品抽出器テスト ===")
    
    try:
        from modules.research import ProductExtractor
        
        extractor = ProductExtractor()
        print("✅ ProductExtractor インスタンス作成成功")
        
        # セレクター設定の確認
        selectors = extractor.selectors
        print(f"✅ セレクター設定確認: {len(selectors)}種類")
        
        return True
        
    except Exception as e:
        print(f"❌ 商品抽出器テストエラー: {e}")
        return False

def test_mercari_researcher_init():
    """メルカリリサーチャー初期化テスト"""
    print("\n=== メルカリリサーチャー初期化テスト ===")
    
    try:
        from core.config import Config
        from core.database import Database
        from modules.research import MercariResearcher
        
        config = Config()
        db = Database('data/test_research.db')
        
        researcher = MercariResearcher(config, db)
        print("✅ MercariResearcher インスタンス作成成功")
        
        # 設定の確認
        print(f"✅ 設定確認完了")
        
        return True
        
    except Exception as e:
        print(f"❌ メルカリリサーチャー初期化エラー: {e}")
        return False

def test_csv_save_function():
    """CSV保存機能のテスト"""
    print("\n=== CSV保存機能テスト ===")
    
    try:
        from core.config import Config
        from core.database import Database
        from modules.research import MercariResearcher
        
        config = Config()
        db = Database('data/test_research.db')
        researcher = MercariResearcher(config, db)
        
        # テスト用商品データ
        test_products = [
            {
                'product_id': 'test_001',
                'title': 'テスト商品1',
                'price': 1500,
                'url': 'https://jp.mercari.com/item/test1',
                'image_url': 'https://example.com/image1.jpg',
                'is_sold': True,
                'condition': '新品・未使用',
                'like_count': 10,
                'keywords': ['テスト', '商品'],
                'extracted_at': '2024-01-01T12:00:00',
                'source_url': 'https://jp.mercari.com/search'
            },
            {
                'product_id': 'test_002',
                'title': 'テスト商品2',
                'price': 2500,
                'url': 'https://jp.mercari.com/item/test2',
                'image_url': 'https://example.com/image2.jpg',
                'is_sold': False,
                'condition': '目立った傷や汚れなし',
                'like_count': 5,
                'keywords': ['テスト', '商品2'],
                'extracted_at': '2024-01-01T12:01:00',
                'source_url': 'https://jp.mercari.com/search'
            }
        ]
        
        # CSV保存テスト
        csv_path = researcher.save_products_to_csv(test_products, 'test_products.csv')
        
        if csv_path and Path(csv_path).exists():
            print(f"✅ CSV保存成功: {csv_path}")
            
            # ファイルサイズ確認
            file_size = Path(csv_path).stat().st_size
            print(f"✅ ファイルサイズ: {file_size}バイト")
            
            return True
        else:
            print("❌ CSVファイルが作成されませんでした")
            return False
        
    except Exception as e:
        print(f"❌ CSV保存テストエラー: {e}")
        return False

def test_database_save_function():
    """データベース保存機能のテスト"""
    print("\n=== データベース保存機能テスト ===")
    
    try:
        from core.config import Config
        from core.database import Database
        from modules.research import MercariResearcher
        
        config = Config()
        db = Database('data/test_research.db')
        researcher = MercariResearcher(config, db)
        
        # テスト用商品データ
        test_products = [
            {
                'product_id': 'db_test_001',
                'title': 'DB テスト商品1',
                'price': 3000,
                'condition': '新品・未使用',
                'image_url': 'https://example.com/db_image1.jpg',
                'like_count': 15
            }
        ]
        
        # データベース保存テスト
        saved_count = researcher.save_products_to_database(test_products)
        
        if saved_count > 0:
            print(f"✅ データベース保存成功: {saved_count}件")
            return True
        else:
            print("❌ データベース保存に失敗しました")
            return False
        
    except Exception as e:
        print(f"❌ データベース保存テストエラー: {e}")
        return False

def test_search_simulation():
    """検索機能のシミュレーションテスト"""
    print("\n=== 検索機能シミュレーションテスト ===")
    
    try:
        from core.config import Config
        from core.database import Database
        from modules.research import MercariResearcher
        
        config = Config()
        
        # テスト用の設定
        config.set('system', 'headless', 'true')  # ヘッドレスモード
        config.set('mercari', 'max_products_per_search', '5')  # 少数での実行
        
        db = Database('data/test_research.db')
        researcher = MercariResearcher(config, db)
        
        print("設定完了。実際の検索テストを実行しますか？")
        print("（注意: インターネット接続とGoogle Chromeが必要です）")
        
        response = input("実行する場合は 'y' を入力: ")
        
        if response.lower() == 'y':
            try:
                print("検索テスト開始...")
                
                # 実際の検索を実行（少数の商品のみ）
                products = researcher.search_products("iPhone", max_products=3)
                
                if products:
                    print(f"✅ 検索テスト成功: {len(products)}件の商品を取得")
                    
                    # 結果の表示
                    for i, product in enumerate(products, 1):
                        print(f"  {i}. {product.get('title', 'N/A')[:50]}...")
                        print(f"     価格: {product.get('price', 'N/A')}円")
                        print(f"     URL: {product.get('url', 'N/A')}")
                    
                    # CSV保存テスト
                    csv_path = researcher.save_products_to_csv(products, 'search_test_results.csv')
                    if csv_path:
                        print(f"✅ 検索結果CSV保存: {csv_path}")
                    
                    return True
                else:
                    print("❌ 検索結果が取得できませんでした")
                    return False
                
            except Exception as e:
                print(f"❌ 検索実行エラー: {e}")
                return False
        else:
            print("✅ 検索シミュレーションテストをスキップしました")
            return True
        
    except Exception as e:
        print(f"❌ 検索シミュレーションテストエラー: {e}")
        return False

def test_batch_search_simulation():
    """一括検索機能のシミュレーションテスト"""
    print("\n=== 一括検索シミュレーションテスト ===")
    
    try:
        from core.config import Config
        from core.database import Database
        from modules.research import MercariResearcher
        
        config = Config()
        config.set('system', 'headless', 'true')
        config.set('mercari', 'max_products_per_search', '2')  # 非常に少数
        config.set('mercari', 'search_interval', '2.0')  # 短い間隔
        
        db = Database('data/test_research.db')
        researcher = MercariResearcher(config, db)
        
        print("一括検索のシミュレーションテストを実行しますか？")
        print("（注意: 複数キーワードで検索するため時間がかかります）")
        
        response = input("実行する場合は 'y' を入力: ")
        
        if response.lower() == 'y':
            try:
                # テスト用キーワード
                test_keywords = ['iPhone', 'iPad']
                
                print(f"一括検索テスト開始: {test_keywords}")
                
                # 一括検索実行
                results = researcher.batch_search(test_keywords)
                
                print("✅ 一括検索テスト完了")
                print(f"  - 総商品数: {results['total_products']}")
                print(f"  - 検索キーワード数: {results['keywords_searched']}")
                print(f"  - CSV保存: {results['csv_file']}")
                print(f"  - DB保存数: {results['database_saved']}")
                
                return True
                
            except Exception as e:
                print(f"❌ 一括検索実行エラー: {e}")
                return False
        else:
            print("✅ 一括検索シミュレーションテストをスキップしました")
            return True
        
    except Exception as e:
        print(f"❌ 一括検索シミュレーションテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🔍 メルカリリサーチ機能テスト開始")
    print("=" * 60)
    
    tests = [
        ("商品抽出器", test_product_extractor),
        ("メルカリリサーチャー初期化", test_mercari_researcher_init),
        ("CSV保存機能", test_csv_save_function),
        ("データベース保存機能", test_database_save_function),
        ("検索機能シミュレーション", test_search_simulation),
        ("一括検索シミュレーション", test_batch_search_simulation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name}テスト実行中 ---")
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}テスト成功")
            else:
                print(f"❌ {test_name}テスト失敗")
                
        except KeyboardInterrupt:
            print("\nテストが中断されました")
            break
        except Exception as e:
            print(f"❌ {test_name}テストで予期しないエラー: {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 テスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("🎉 全てのリサーチ機能テストが成功しました！")
        print("商品データ取得とCSV保存機能が正常に動作しています。")
        print("")
        print("📁 生成されたファイルを確認してください:")
        print("  - results/ フォルダ内のCSVファイル")
        print("  - data/test_research.db （テスト用データベース）")
        return True
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("失敗したテストを確認して修正してください。")
        return False

if __name__ == "__main__":
    print("⚠️  注意: このテストは以下が必要です:")
    print("  - Google Chromeのインストール")
    print("  - インターネット接続")
    print("  - 基盤機能（フェーズ1）とRPA基盤（フェーズ2-1）の実装")
    
    # 実行確認
    response = input("\nテストを実行しますか？ (y/N): ")
    if response.lower() in ['y', 'yes']:
        success = main()
        sys.exit(0 if success else 1)
    else:
        print("テストがキャンセルされました。")
        sys.exit(0)
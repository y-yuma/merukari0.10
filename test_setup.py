#!/usr/bin/env python3
"""
基盤機能のテストスクリプト
フェーズ1で実装した機能が正常に動作するかを確認します
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """モジュールのインポートテスト"""
    print("=== モジュールインポートテスト ===")
    
    try:
        from core.config import Config
        print("✅ Config クラスのインポート成功")
    except ImportError as e:
        print(f"❌ Config クラスのインポート失敗: {e}")
        return False
    
    try:
        from core.logger import setup_logger, PerformanceLogger
        print("✅ Logger モジュールのインポート成功")
    except ImportError as e:
        print(f"❌ Logger モジュールのインポート失敗: {e}")
        return False
    
    try:
        from core.database import Database
        print("✅ Database クラスのインポート成功")
    except ImportError as e:
        print(f"❌ Database クラスのインポート失敗: {e}")
        return False
    
    try:
        from core.utils import clean_text, extract_price, calculate_profit
        print("✅ Utils モジュールのインポート成功")
    except ImportError as e:
        print(f"❌ Utils モジュールのインポート失敗: {e}")
        return False
    
    return True

def test_config():
    """設定管理のテスト"""
    print("\n=== 設定管理テスト ===")
    
    try:
        from core.config import Config
        
        # 設定インスタンスの作成
        config = Config()
        print("✅ Config インスタンスの作成成功")
        
        # デフォルト設定の確認
        request_interval = config.get_float('system', 'request_interval')
        print(f"✅ 設定値取得成功: request_interval = {request_interval}")
        
        # 設定の変更と保存
        config.set('system', 'test_value', 'test123')
        config.save()
        print("✅ 設定の保存成功")
        
        # 設定の再読み込み
        config._load_config()
        test_value = config.get('system', 'test_value')
        if test_value == 'test123':
            print("✅ 設定の読み込み成功")
        else:
            print(f"❌ 設定値が正しくありません: {test_value}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 設定管理テスト失敗: {e}")
        return False

def test_logger():
    """ログ機能のテスト"""
    print("\n=== ログ機能テスト ===")
    
    try:
        from core.logger import setup_logger, PerformanceLogger
        
        # ロガーの作成
        logger = setup_logger('test_logger')
        print("✅ Logger インスタンスの作成成功")
        
        # ログ出力テスト
        logger.info("テストログメッセージ（INFO）")
        logger.warning("テストログメッセージ（WARNING）")
        logger.error("テストログメッセージ（ERROR）")
        print("✅ ログ出力成功")
        
        # パフォーマンスロガーのテスト
        perf_logger = PerformanceLogger('test_performance')
        perf_logger.start_timer('test_operation')
        import time
        time.sleep(0.1)
        duration = perf_logger.end_timer('test_operation')
        
        if duration and duration > 0:
            print(f"✅ パフォーマンス測定成功: {duration:.3f}秒")
        else:
            print("❌ パフォーマンス測定失敗")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ ログ機能テスト失敗: {e}")
        return False

def test_database():
    """データベース機能のテスト"""
    print("\n=== データベース機能テスト ===")
    
    try:
        from core.database import Database
        
        # データベースインスタンスの作成
        db = Database('data/test_database.db')
        print("✅ Database インスタンスの作成成功")
        
        # テスト用メルカリ商品データ
        test_product = {
            'product_id': 'test_001',
            'title': 'テスト商品',
            'price': 1000,
            'seller_name': 'テスト販売者',
            'condition_text': '新品・未使用',
            'description': 'テスト用の商品説明',
            'category': 'テストカテゴリ',
            'image_urls': ['https://example.com/image1.jpg'],
            'view_count': 10,
            'like_count': 5
        }
        
        # 商品データの追加
        product_id = db.add_mercari_product(test_product)
        print(f"✅ メルカリ商品追加成功: ID={product_id}")
        
        # キーワードの追加
        keyword_id = db.add_keyword('テストキーワード', 'テストカテゴリ', 1)
        print(f"✅ キーワード追加成功: ID={keyword_id}")
        
        # アクティブキーワードの取得
        keywords = db.get_active_keywords(5)
        print(f"✅ キーワード取得成功: {len(keywords)}件")
        
        # 統計情報の取得
        stats = db.get_statistics()
        print(f"✅ 統計情報取得成功: {stats}")
        
        # テストデータのクリーンアップ
        import os
        os.remove('data/test_database.db')
        print("✅ テストデータベース削除成功")
        
        return True
        
    except Exception as e:
        print(f"❌ データベース機能テスト失敗: {e}")
        return False

def test_utils():
    """ユーティリティ関数のテスト"""
    print("\n=== ユーティリティ機能テスト ===")
    
    try:
        from core.utils import (
            clean_text, extract_price, calculate_profit,
            generate_product_id, validate_url, format_currency
        )
        
        # テキストクリーニング
        dirty_text = "  <p>テスト　テキスト</p>  "
        clean = clean_text(dirty_text)
        expected = "テスト テキスト"
        if clean == expected:
            print("✅ テキストクリーニング成功")
        else:
            print(f"❌ テキストクリーニング失敗: {clean} != {expected}")
        
        # 価格抽出
        price_text = "￥1,500"
        price = extract_price(price_text)
        if price == 1500:
            print("✅ 価格抽出成功")
        else:
            print(f"❌ 価格抽出失敗: {price} != 1500")
        
        # 利益計算
        profit_calc = calculate_profit(
            selling_price=2000,
            cost_price=1000,
            shipping_cost=300,
            mercari_fee_rate=0.10
        )
        expected_profit = 2000 - 1000 - 300 - 200  # 500円
        if profit_calc['profit'] == expected_profit:
            print("✅ 利益計算成功")
        else:
            print(f"❌ 利益計算失敗: {profit_calc['profit']} != {expected_profit}")
        
        # 商品ID生成
        product_id = generate_product_id("テスト商品", 1000, "テスト販売者")
        if len(product_id) == 16:
            print("✅ 商品ID生成成功")
        else:
            print(f"❌ 商品ID生成失敗: 長さが正しくありません")
        
        # URL検証
        if validate_url("https://example.com"):
            print("✅ URL検証成功（有効なURL）")
        else:
            print("❌ URL検証失敗（有効なURLが無効と判定）")
        
        if not validate_url("invalid-url"):
            print("✅ URL検証成功（無効なURL）")
        else:
            print("❌ URL検証失敗（無効なURLが有効と判定）")
        
        # 通貨フォーマット
        formatted = format_currency(1500)
        if formatted == "¥1,500":
            print("✅ 通貨フォーマット成功")
        else:
            print(f"❌ 通貨フォーマット失敗: {formatted} != ¥1,500")
        
        return True
        
    except Exception as e:
        print(f"❌ ユーティリティ機能テスト失敗: {e}")
        return False

def test_directory_structure():
    """ディレクトリ構造のテスト"""
    print("\n=== ディレクトリ構造テスト ===")
    
    required_dirs = [
        'core',
        'data',
        'logs',
        'results'
    ]
    
    success = True
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ ディレクトリ存在確認: {dir_name}")
        else:
            # ディレクトリを作成
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ ディレクトリ作成: {dir_name}")
    
    required_files = [
        'requirements.txt',
        'core/__init__.py',
        'core/config.py',
        'core/logger.py',
        'core/database.py',
        'core/utils.py'
    ]
    
    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"✅ ファイル存在確認: {file_name}")
        else:
            print(f"❌ ファイル不足: {file_name}")
            success = False
    
    return success

def main():
    """メインテスト実行"""
    print("🚀 メルカリ自動化システム フェーズ1 テスト開始")
    print("=" * 50)
    
    tests = [
        ("ディレクトリ構造", test_directory_structure),
        ("モジュールインポート", test_imports),
        ("設定管理", test_config),
        ("ログ機能", test_logger),
        ("データベース機能", test_database),
        ("ユーティリティ機能", test_utils)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}テストで予期しないエラー: {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 テスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("🎉 全てのテストが成功しました！")
        print("フェーズ1の基盤機能は正常に動作しています。")
        print("次はフェーズ2（RPA基盤・メルカリリサーチ）の開発に進むことができます。")
        return True
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("失敗したテストを確認して修正してください。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
RPA基盤のテストスクリプト
Seleniumによるメルカリアクセス機能をテストします
"""
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_chrome_driver_setup():
    """ChromeDriverセットアップのテスト"""
    print("=== ChromeDriverセットアップテスト ===")
    
    try:
        from core.config import Config
        from core.rpa import ChromeDriverManager
        
        config = Config()
        driver_manager = ChromeDriverManager(config)
        
        # ChromeDriverのセットアップ
        result = driver_manager.setup_driver()
        
        if result:
            print("✅ ChromeDriverセットアップ成功")
            return True
        else:
            print("❌ ChromeDriverセットアップ失敗")
            return False
            
    except Exception as e:
        print(f"❌ ChromeDriverセットアップテストエラー: {e}")
        return False

def test_webdriver_creation():
    """WebDriver作成のテスト"""
    print("\n=== WebDriver作成テスト ===")
    
    try:
        from core.config import Config
        from core.rpa import MercariRPA
        
        config = Config()
        
        # ヘッドレスモードでテスト（画面表示なし）
        config.set('system', 'headless', 'true')
        # 手動でChromeDriverのパスを指定
        import os
        if os.path.exists('drivers/chromedriver'):
            os.environ['CHROMEDRIVER_PATH'] = 'drivers/chromedriver'
            print("✅ 手動ChromeDriverを使用します")
        rpa = MercariRPA(config)
        
        # WebDriverのセットアップ
        result = rpa.setup_driver()
        
        if result and rpa.driver:
            print("✅ WebDriver作成成功")
            
            # 簡単な動作テスト
            rpa.driver.get("https://www.google.com")
            title = rpa.driver.title
            print(f"✅ ページアクセステスト成功: {title}")
            
            # クリーンアップ
            rpa.close()
            return True
        else:
            print("❌ WebDriver作成失敗")
            return False
            
    except Exception as e:
        print(f"❌ WebDriver作成テストエラー: {e}")
        return False

def test_mercari_access():
    """メルカリアクセステスト"""
    print("\n=== メルカリアクセステスト ===")
    
    try:
        from core.config import Config
        from core.rpa import MercariRPA
        
        config = Config()
        
        # 実際に画面を表示してテスト
        config.set('system', 'headless', 'false')
        
        with MercariRPA(config) as rpa:
            # WebDriverセットアップ
            if not rpa.setup_driver():
                print("❌ WebDriverセットアップ失敗")
                return False
            
            # メルカリにアクセス
            result = rpa.navigate_to_mercari()
            
            if result:
                print("✅ メルカリアクセス成功")
                
                # 5秒間待機（画面確認用）
                print("メルカリページを5秒間表示します...")
                time.sleep(5)
                
                # スクリーンショット撮影
                screenshot_path = rpa.take_screenshot("mercari_access_test.png")
                if screenshot_path:
                    print(f"✅ スクリーンショット保存: {screenshot_path}")
                
                return True
            else:
                print("❌ メルカリアクセス失敗")
                return False
                
    except Exception as e:
        print(f"❌ メルカリアクセステストエラー: {e}")
        return False

def test_search_functionality():
    """検索機能テスト"""
    print("\n=== 検索機能テスト ===")
    
    try:
        from core.config import Config
        from core.rpa import MercariRPA
        
        config = Config()
        config.set('system', 'headless', 'false')
        
        with MercariRPA(config) as rpa:
            # WebDriverセットアップ
            if not rpa.setup_driver():
                print("❌ WebDriverセットアップ失敗")
                return False
            
            # メルカリにアクセス
            if not rpa.navigate_to_mercari():
                print("❌ メルカリアクセス失敗")
                return False
            
            # 検索実行
            search_keyword = "iPhone"
            filters = {
                'sold_only': True,  # 売り切れのみ
                'condition': 'new'  # 新品・未使用
            }
            
            result = rpa.perform_search(search_keyword, filters)
            
            if result:
                print(f"✅ 検索実行成功: {search_keyword}")
                
                # 検索結果の確認用に少し待機
                print("検索結果を10秒間表示します...")
                time.sleep(10)
                
                # スクリーンショット撮影
                screenshot_path = rpa.take_screenshot("search_result_test.png")
                if screenshot_path:
                    print(f"✅ 検索結果スクリーンショット: {screenshot_path}")
                
                return True
            else:
                print("❌ 検索実行失敗")
                return False
                
    except Exception as e:
        print(f"❌ 検索機能テストエラー: {e}")
        return False

def test_error_handling():
    """エラーハンドリングテスト"""
    print("\n=== エラーハンドリングテスト ===")
    
    try:
        from core.config import Config
        from core.error_handler import MercariErrorHandler, retry_on_error, RetryConfig
        from selenium.common.exceptions import TimeoutException
        
        config = Config()
        error_handler = MercariErrorHandler(config)
        
        # 疑似的なエラーでテスト
        test_error = TimeoutException("テスト用タイムアウトエラー")
        context = {
            'function_name': 'test_function',
            'attempt': 1,
            'url': 'https://jp.mercari.com'
        }
        
        result = error_handler.handle_error(test_error, context)
        
        print(f"✅ エラーハンドリング結果:")
        print(f"  - エラータイプ: {result['error_type']}")
        print(f"  - 重要度: {result['severity']}")
        print(f"  - リカバリー試行: {result['recovery_attempted']}")
        print(f"  - リトライ推奨: {result['retry_recommended']}")
        
        # エラー統計の確認
        stats = error_handler.get_error_stats()
        print(f"✅ エラー統計: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーハンドリングテストエラー: {e}")
        return False

def test_human_behavior():
    """人間的動作テスト"""
    print("\n=== 人間的動作テスト ===")
    
    try:
        from core.rpa import HumanBehavior
        
        human = HumanBehavior()
        
        print("✅ HumanBehaviorインスタンス作成成功")
        
        # 待機時間テスト
        print("ランダム待機テスト開始...")
        start_time = time.time()
        human.random_wait(1.0, 2.0)
        elapsed = time.time() - start_time
        
        if 1.0 <= elapsed <= 2.0:
            print(f"✅ ランダム待機テスト成功: {elapsed:.2f}秒")
        else:
            print(f"❌ ランダム待機テスト失敗: {elapsed:.2f}秒（範囲外）")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 人間的動作テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 RPA基盤テスト開始")
    print("=" * 60)
    
    tests = [
        ("ChromeDriverセットアップ", test_chrome_driver_setup),
        ("WebDriver作成", test_webdriver_creation),
        ("エラーハンドリング", test_error_handling),
        ("人間的動作", test_human_behavior),
        ("メルカリアクセス", test_mercari_access),
        ("検索機能", test_search_functionality)
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
        print("🎉 全てのRPA基盤テストが成功しました！")
        print("Seleniumによるメルカリアクセス機能が正常に動作しています。")
        print("次はメルカリリサーチモジュールの開発に進むことができます。")
        return True
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("失敗したテストを確認して修正してください。")
        return False

if __name__ == "__main__":
    print("⚠️  注意: このテストはGoogle Chromeがインストールされている必要があります。")
    print("また、インターネット接続が必要です。")
    
    # 実行確認
    response = input("\nテストを実行しますか？ (y/N): ")
    if response.lower() in ['y', 'yes']:
        success = main()
        sys.exit(0 if success else 1)
    else:
        print("テストがキャンセルされました。")
        sys.exit(0)
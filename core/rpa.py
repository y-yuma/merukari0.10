"""
RPA基盤モジュール - Selenium制御と人間的動作
"""
import time
import random
import math
import json
import subprocess
import platform
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager as WDManager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException
)

from core.logger import setup_logger
from core.utils import random_delay

class HumanBehavior:
    """人間的な動作を実装するクラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = setup_logger(__name__ + '.HumanBehavior')
        
        # 動作パラメータ
        self.typing_speed_range = (0.05, 0.20)  # 秒/文字
        self.mouse_speed = 1000  # ピクセル/秒
        self.think_time_range = (0.5, 2.0)  # 考える時間
        
    def random_wait(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """ランダムな待機時間"""
        wait_time = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"待機: {wait_time:.2f}秒")
        time.sleep(wait_time)
    
    def human_type(self, element, text: str):
        """人間的なタイピング"""
        # 要素にフォーカス
        element.click()
        self.random_wait(0.3, 0.8)
        
        # 既存のテキストをクリア
        element.clear()
        self.random_wait(0.2, 0.5)
        
        # 文字を1つずつ入力
        for i, char in enumerate(text):
            # タイピング速度の変動
            speed = random.uniform(*self.typing_speed_range)
            
            # たまに早くなったり遅くなったり
            if random.random() < 0.1:
                speed *= random.uniform(0.5, 2.0)
            
            element.send_keys(char)
            time.sleep(speed)
            
            # 誤字の挿入（5%の確率）
            if random.random() < 0.05 and i < len(text) - 1:
                self._insert_typo(element)
            
            # たまに一時停止（考えている風）
            if random.random() < 0.1:
                self.random_wait(*self.think_time_range)
    
    def _insert_typo(self, element):
        """誤字の挿入と修正"""
        # ランダムな文字を入力
        wrong_chars = 'あいうえおかきくけこ'
        wrong_char = random.choice(wrong_chars)
        element.send_keys(wrong_char)
        time.sleep(random.uniform(0.2, 0.5))
        
        # 気づいて修正
        element.send_keys(Keys.BACKSPACE)
        time.sleep(random.uniform(0.1, 0.3))
    
    def human_scroll(self, driver, direction: str = 'down', distance: int = None):
        """人間的なスクロール"""
        if distance is None:
            distance = random.randint(200, 800)
        
        # スクロール回数を分割（一気にスクロールしない）
        scroll_count = random.randint(3, 7)
        scroll_per_step = distance // scroll_count
        
        for i in range(scroll_count):
            if direction == 'down':
                driver.execute_script(f"window.scrollBy(0, {scroll_per_step});")
            else:
                driver.execute_script(f"window.scrollBy(0, -{scroll_per_step});")
            
            # スクロール間の待機時間
            time.sleep(random.uniform(0.1, 0.3))
    
    def human_click(self, driver, element):
        """人間的なクリック"""
        # 要素が見えるまでスクロール
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        self.random_wait(0.5, 1.0)
        
        # マウスを要素に移動（ActionChains使用）
        actions = ActionChains(driver)
        actions.move_to_element(element)
        
        # 少し待ってからクリック
        self.random_wait(0.2, 0.8)
        actions.click()
        actions.perform()

class ChromeDriverManager:
    """ChromeDriverの管理クラス"""
    
    def __init__(self, config):
        """初期化"""
        self.config = config
        self.logger = setup_logger(__name__ + '.ChromeDriverManager')
        self.driver_path = Path('drivers/chromedriver.exe')
    
    def get_chrome_version(self) -> str:
        """インストール済みChromeのバージョンを取得"""
        try:
            # Windowsの場合
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version.split('.')[0]  # メジャーバージョンのみ
        except:
            try:
                # Macの場合
                import subprocess
                result = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                                      capture_output=True, text=True)
                version = result.stdout.split()[-1]
                return version.split('.')[0]
            except:
                # デフォルト
                return "119"
    
    def download_chromedriver(self) -> bool:
        """ChromeDriverを自動ダウンロード"""
        try:
            import requests
            import zipfile
            
            chrome_version = self.get_chrome_version()
            self.logger.info(f"Chrome バージョン: {chrome_version}")
            
            # ChromeDriver ダウンロードURL
            url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{chrome_version}"
            
            # 最新バージョン取得
            response = requests.get(url)
            if response.status_code == 200:
                driver_version = response.text.strip()
            else:
                # フォールバック
                driver_version = f"{chrome_version}.0.6312.86"
            
            # ダウンロードURL
            if 'windows' in platform.system().lower():
                download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
            elif 'darwin' in platform.system().lower():  # macOS
                download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_mac64.zip"
            else:
                download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_linux64.zip"
            
            self.logger.info(f"ChromeDriver をダウンロード中: {driver_version}")
            
            # ダウンロード実行
            response = requests.get(download_url)
            response.raise_for_status()
            
            # 保存とUnzip
            zip_path = Path('drivers/chromedriver.zip')
            zip_path.parent.mkdir(exist_ok=True)
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('drivers')
            
            # 実行権限を付与（Mac/Linux）
            if not 'windows' in platform.system().lower():
                import os
                os.chmod(self.driver_path, 0o755)
            
            # zipファイルを削除
            zip_path.unlink()
            
            self.logger.info("ChromeDriver のダウンロード完了")
            return True
            
        except Exception as e:
            self.logger.error(f"ChromeDriver ダウンロードエラー: {e}")
            return False
    
    def setup_driver(self) -> bool:
        """ChromeDriverのセットアップ"""
        if not self.driver_path.exists():
            self.logger.info("ChromeDriver が見つかりません。ダウンロードを開始します。")
            return self.download_chromedriver()
        
        self.logger.info("ChromeDriver は既にセットアップ済みです。")
        return True

class MercariRPA:
    """メルカリ専用RPAクラス"""
    
    def __init__(self, config):
        """初期化"""
        self.config = config
        self.logger = setup_logger(__name__ + '.MercariRPA')
        self.human = HumanBehavior()
        
        # WebDriver関連
        self.driver = None
        self.wait = None
        
        # 古いChromeDriverManagerは使用しない（コメントアウト）
        # self.driver_manager = ChromeDriverManager(config)
        
    def setup_driver(self) -> bool:
        """WebDriverのセットアップ"""
        try:
            # 古いChromeDriverセットアップは使用しない（コメントアウト）
            # if not self.driver_manager.setup_driver():
            #     return False
            
            # Chrome オプションの設定
            options = Options()
            
            # ヘッドレスモード
            if self.config.get_boolean('system', 'headless', False):
                options.add_argument('--headless')
                self.logger.info("ヘッドレスモードで実行")
            
            # 自動化検出を回避するオプション
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # 画像読み込みを無効化（高速化）
            options.add_argument('--disable-javascript')  # JavaScriptを無効化
            options.add_argument('--disable-css')  # CSSを無効化
            
            # より高度な自動化検出回避
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("detach", True)
            
            # 追加のprefsで自動化検出を回避
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,  # 通知をブロック
                    "geolocation": 2,    # 位置情報をブロック
                },
                "profile.managed_default_content_settings": {
                    "images": 2  # 画像をブロック
                }
            }
            options.add_experimental_option("prefs", prefs)
            
            # User-Agentを最新のものに変更
            user_agent = self.config.get('system', 'user_agent', 
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')
            options.add_argument(f'--user-agent={user_agent}')
            
            # プロキシ設定
            proxy = self.config.get('system', 'proxy')
            if proxy:
                options.add_argument(f'--proxy-server={proxy}')
                self.logger.info(f"プロキシを使用: {proxy}")
            
            # ウィンドウサイズ
            options.add_argument('--window-size=1920,1080')
            
            # Cookie、キャッシュの保持
            user_data_dir = Path('data/chrome_user_data')
            user_data_dir.mkdir(exist_ok=True)
            options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # webdriver-managerを使用（最も確実な方法）
            service = Service(WDManager().install())
            
            # WebDriverの作成
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # 暗黙の待機時間
            self.driver.implicitly_wait(10)
            
            # 明示的待機のセットアップ
            self.wait = WebDriverWait(self.driver, 
                                    self.config.get_int('system', 'timeout_seconds', 30))
            
            # 自動化検出を回避するスクリプトを追加
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # さらなる自動化検出回避
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['ja-JP', 'ja']})")
            
            self.logger.info("WebDriver のセットアップ完了")
            return True
            
        except Exception as e:
            self.logger.error(f"WebDriver セットアップエラー: {e}")
            return False
    
    def navigate_to_mercari(self) -> bool:
        """メルカリサイトにアクセス"""
        try:
            self.logger.info("メルカリサイトにアクセス中...")
            self.driver.get("https://jp.mercari.com/")
            
            # ページロードの確認
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # 人間らしい待機
            self.human.random_wait(2.0, 4.0)
            
            self.logger.info("メルカリサイトへのアクセス完了")
            return True
            
        except TimeoutException:
            self.logger.error("メルカリサイトへのアクセスがタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"メルカリサイトアクセスエラー: {e}")
            return False
    
    def perform_search(self, keyword: str, filters: Dict[str, Any] = None) -> bool:
        """検索の実行"""
        try:
            self.logger.info(f"検索実行: {keyword}")
            
            # 検索ボックスを探す
            search_selectors = [
                'input[name="keyword"]',
                'input[placeholder*="検索"]',
                'input[type="search"]',
                '.search-input input',
                '#search-input'
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not search_box:
                self.logger.error("検索ボックスが見つかりません")
                return False
            
            # 検索キーワードを入力（人間らしく）
            self.human.human_type(search_box, keyword)
            
            # 検索実行
            search_box.send_keys(Keys.RETURN)
            
            # 検索結果ページの読み込み待機
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="item-list"]')))
            
            # フィルター適用
            if filters:
                self._apply_filters(filters)
            
            self.logger.info(f"検索完了: {keyword}")
            return True
            
        except TimeoutException:
            self.logger.error("検索結果の読み込みがタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"検索エラー: {e}")
            return False
    
    def _apply_filters(self, filters: Dict[str, Any]):
        """検索フィルターの適用"""
        try:
            # 売り切れフィルター
            if filters.get('sold_only', False):
                self._click_sold_filter()
            
            # 商品状態フィルター
            condition = filters.get('condition')
            if condition:
                self._click_condition_filter(condition)
            
            # 価格フィルター
            price_range = filters.get('price_range')
            if price_range:
                self._set_price_filter(price_range)
            
            # フィルター適用後の待機
            self.human.random_wait(1.0, 2.0)
            
        except Exception as e:
            self.logger.warning(f"フィルター適用エラー: {e}")
    
    def _click_sold_filter(self):
        """売り切れフィルターのクリック"""
        sold_selectors = [
            'label[for="soldout"]',
            'input[value="sold_out"]',
            '*[data-testid*="sold"]',
            'span:contains("売り切れ")'
        ]
        
        for selector in sold_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                self.human.human_click(self.driver, element)
                self.logger.debug("売り切れフィルターを適用")
                return
            except:
                continue
    
    def _click_condition_filter(self, condition: str):
        """商品状態フィルターのクリック"""
        # condition: "new", "like_new", "good", etc.
        condition_map = {
            "new": "新品・未使用",
            "like_new": "未使用に近い", 
            "good": "目立った傷や汚れなし"
        }
        
        condition_text = condition_map.get(condition, condition)
        
        try:
            # 商品状態フィルターを探してクリック
            element = self.driver.find_element(By.XPATH, f"//span[contains(text(), '{condition_text}')]")
            self.human.human_click(self.driver, element)
            self.logger.debug(f"商品状態フィルターを適用: {condition_text}")
        except Exception as e:
            self.logger.warning(f"商品状態フィルター適用エラー: {e}")
    
    def _set_price_filter(self, price_range: Dict[str, int]):
        """価格フィルターの設定"""
        try:
            min_price = price_range.get('min')
            max_price = price_range.get('max')
            
            # 最小価格の設定
            if min_price:
                min_price_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="price_min"]')
                self.human.human_type(min_price_input, str(min_price))
            
            # 最大価格の設定
            if max_price:
                max_price_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="price_max"]')
                self.human.human_type(max_price_input, str(max_price))
            
            self.logger.debug(f"価格フィルターを適用: {min_price}-{max_price}")
            
        except Exception as e:
            self.logger.warning(f"価格フィルター適用エラー: {e}")
    
    def scroll_to_load_all(self, max_scrolls: int = 20) -> bool:
        """全商品を読み込むためのスクロール"""
        try:
            self.logger.info("全商品読み込みのためにスクロール開始")
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            
            while scroll_count < max_scrolls:
                # 人間らしくスクロール
                self.human.human_scroll(self.driver, 'down', random.randint(300, 800))
                
                # スクロール後の待機（新しいコンテンツの読み込み待ち）
                time.sleep(random.uniform(1.0, 3.0))
                
                # 新しい高さを取得
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # 高さが変わらなければスクロール終了
                if new_height == last_height:
                    self.logger.info("全商品の読み込み完了")
                    break
                
                last_height = new_height
                scroll_count += 1
                
                self.logger.debug(f"スクロール進行中: {scroll_count}/{max_scrolls}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"スクロールエラー: {e}")
            return False
    
    def get_current_page_source(self) -> str:
        """現在のページのHTMLソースを取得"""
        try:
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"ページソース取得エラー: {e}")
            return ""
    
    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """スクリーンショットの撮影"""
        try:
            if filename is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshot_path = Path(f"logs/{filename}")
            screenshot_path.parent.mkdir(exist_ok=True)
            
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.debug(f"スクリーンショット保存: {screenshot_path}")
            
            return str(screenshot_path)
            
        except Exception as e:
            self.logger.error(f"スクリーンショットエラー: {e}")
            return None
    
    def close(self):
        """WebDriverの終了"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver を終了しました")
            except Exception as e:
                self.logger.error(f"WebDriver 終了エラー: {e}")
    
    def __enter__(self):
        """コンテキストマネージャー（with文対応）"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了処理"""
        self.close()
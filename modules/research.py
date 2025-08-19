"""
メルカリリサーチモジュール - 商品データ取得とCSV保存
"""
import time
import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import requests

from core.logger import setup_logger
from core.rpa import MercariRPA
from core.error_handler import MercariErrorHandler, retry_on_error, RetryConfig
from core.utils import (
    extract_price, clean_text, generate_product_id,
    extract_keywords_from_title, format_currency
)

class ProductExtractor:
    """商品データ抽出クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = setup_logger(__name__ + '.ProductExtractor')
        
        # メルカリの要素セレクター（2024年版）
        self.selectors = {
            # 商品リスト
            'product_list': [
                'div[data-testid="item-list"] > ul > li',
                'div[data-testid="item-cell"]',
                'ul[data-testid*="item"] li',
                '.items-box-content',
                'mer-item-thumbnail'
            ],
            
            # 商品リンク
            'product_link': [
                'a[data-testid="item-link"]',
                'mer-item-thumbnail a',
                'a[href*="/item/"]',
                '.item-link'
            ],
            
            # 商品タイトル
            'product_title': [
                'mer-item-thumbnail .item-name',
                '[data-testid="item-name"]',
                'h3.item-name',
                '.item-name span',
                'figcaption span'
            ],
            
            # 商品価格
            'product_price': [
                'mer-item-thumbnail .item-price',
                '[data-testid="item-price"]',
                '.price',
                '.item-price span',
                'span[class*="price"]'
            ],
            
            # 商品画像
            'product_image': [
                'mer-item-thumbnail img',
                '[data-testid="item-image"]',
                '.item-photo img',
                'figure img'
            ],
            
            # 売り切れバッジ
            'sold_badge': [
                '.item-sold-out-badge',
                '[data-testid="sold-badge"]',
                '.sold-out',
                'span:contains("SOLD")'
            ],
            
            # 商品状態
            'condition': [
                '.item-condition',
                '[data-testid="condition"]',
                '.condition-label'
            ],
            
            # いいね数
            'like_count': [
                '[data-testid="like-count"]',
                '.like-count',
                '.heart-count span'
            ]
        }
    
    def extract_products_from_page(self, driver) -> List[Dict[str, Any]]:
        """現在のページから商品データを抽出"""
        try:
            self.logger.info("ページから商品データを抽出中...")
            
            # ページソースを取得
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 商品要素を取得
            product_elements = self._find_product_elements(driver, soup)
            
            if not product_elements:
                self.logger.warning("商品要素が見つかりませんでした")
                return []
            
            products = []
            
            for i, element in enumerate(product_elements):
                try:
                    product_data = self._extract_single_product(element, soup, driver)
                    if product_data:
                        products.append(product_data)
                        self.logger.debug(f"商品抽出成功 ({i+1}/{len(product_elements)}): {product_data.get('title', 'N/A')[:30]}...")
                    
                    # レート制限対策
                    if i % 10 == 9:
                        time.sleep(0.5)
                        
                except Exception as e:
                    self.logger.warning(f"商品抽出エラー ({i+1}/{len(product_elements)}): {e}")
                    continue
            
            self.logger.info(f"商品データ抽出完了: {len(products)}件")
            return products
            
        except Exception as e:
            self.logger.error(f"ページ商品抽出エラー: {e}")
            return []
    
    def _find_product_elements(self, driver, soup) -> List:
        """商品要素を検索"""
        # Selenium経由で検索
        for selector in self.selectors['product_list']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self.logger.debug(f"商品要素発見: {len(elements)}件 (セレクター: {selector})")
                    return elements
            except:
                continue
        
        # BeautifulSoup経由で検索
        for selector in self.selectors['product_list']:
            elements = soup.select(selector)
            if elements:
                self.logger.debug(f"商品要素発見 (BS4): {len(elements)}件 (セレクター: {selector})")
                return elements
        
        return []
    
    def _extract_single_product(self, element, soup, driver) -> Optional[Dict[str, Any]]:
        """単一商品のデータ抽出"""
        product_data = {
            'extracted_at': datetime.now().isoformat(),
            'source_url': driver.current_url
        }
        
        try:
            # 商品URL
            product_data['url'] = self._extract_product_url(element, driver)
            
            # 商品タイトル
            product_data['title'] = self._extract_product_title(element)
            
            # 商品価格
            product_data['price'] = self._extract_product_price(element)
            
            # 商品画像URL
            product_data['image_url'] = self._extract_product_image(element, driver)
            
            # 売り切れ状態
            product_data['is_sold'] = self._extract_sold_status(element)
            
            # 商品状態
            product_data['condition'] = self._extract_condition(element)
            
            # いいね数
            product_data['like_count'] = self._extract_like_count(element)
            
            # 商品ID生成
            if product_data.get('title') and product_data.get('price'):
                product_data['product_id'] = generate_product_id(
                    product_data['title'], 
                    product_data['price']
                )
            
            # キーワード抽出
            if product_data.get('title'):
                product_data['keywords'] = extract_keywords_from_title(product_data['title'])
            
            # データ検証
            if self._validate_product_data(product_data):
                return product_data
            
        except Exception as e:
            self.logger.debug(f"単一商品抽出エラー: {e}")
        
        return None
    
    def _extract_product_url(self, element, driver) -> Optional[str]:
        """商品URLの抽出"""
        for selector in self.selectors['product_link']:
            try:
                # Selenium経由
                link_element = element.find_element(By.CSS_SELECTOR, selector)
                href = link_element.get_attribute('href')
                if href:
                    # 相対URLを絶対URLに変換
                    return urljoin(driver.current_url, href)
            except:
                continue
        
        return None
    
    def _extract_product_title(self, element) -> Optional[str]:
        """商品タイトルの抽出"""
        for selector in self.selectors['product_title']:
            try:
                title_element = element.find_element(By.CSS_SELECTOR, selector)
                title = title_element.get_attribute('textContent') or title_element.text
                if title:
                    return clean_text(title)
            except:
                continue
        
        return None
    
    def _extract_product_price(self, element) -> Optional[int]:
        """商品価格の抽出"""
        for selector in self.selectors['product_price']:
            try:
                price_element = element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_element.get_attribute('textContent') or price_element.text
                if price_text:
                    price = extract_price(price_text)
                    if price:
                        return price
            except:
                continue
        
        return None
    
    def _extract_product_image(self, element, driver) -> Optional[str]:
        """商品画像URLの抽出"""
        for selector in self.selectors['product_image']:
            try:
                img_element = element.find_element(By.CSS_SELECTOR, selector)
                src = img_element.get_attribute('src') or img_element.get_attribute('data-src')
                if src:
                    return urljoin(driver.current_url, src)
            except:
                continue
        
        return None
    
    def _extract_sold_status(self, element) -> bool:
        """売り切れ状態の抽出"""
        for selector in self.selectors['sold_badge']:
            try:
                element.find_element(By.CSS_SELECTOR, selector)
                return True  # 売り切れバッジが見つかった
            except:
                continue
        
        return False
    
    def _extract_condition(self, element) -> Optional[str]:
        """商品状態の抽出"""
        for selector in self.selectors['condition']:
            try:
                condition_element = element.find_element(By.CSS_SELECTOR, selector)
                condition = condition_element.get_attribute('textContent') or condition_element.text
                if condition:
                    return clean_text(condition)
            except:
                continue
        
        return None
    
    def _extract_like_count(self, element) -> int:
        """いいね数の抽出"""
        for selector in self.selectors['like_count']:
            try:
                like_element = element.find_element(By.CSS_SELECTOR, selector)
                like_text = like_element.get_attribute('textContent') or like_element.text
                if like_text:
                    # 数字を抽出
                    numbers = re.findall(r'\d+', like_text)
                    if numbers:
                        return int(numbers[0])
            except:
                continue
        
        return 0
    
    def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """商品データの検証"""
        required_fields = ['title', 'price']
        
        for field in required_fields:
            if not product_data.get(field):
                return False
        
        # 価格の妥当性チェック
        price = product_data.get('price')
        if not isinstance(price, int) or price <= 0 or price > 10000000:
            return False
        
        return True

class MercariResearcher:
    """メルカリ商品リサーチクラス"""
    
    def __init__(self, config, database):
        """初期化"""
        self.config = config
        self.db = database
        self.logger = setup_logger(__name__)
        
        # 商品抽出器
        self.extractor = ProductExtractor()
        
        # エラーハンドラー
        self.error_handler = MercariErrorHandler(config)
        
        # リトライ設定
        self.retry_config = RetryConfig(
            max_retries=self.config.get_int('system', 'max_retry_count', 3),
            base_delay=self.config.get_float('system', 'request_interval', 2.0)
        )
    
    @retry_on_error()
    def search_products(self, keyword: str, max_products: int = None) -> List[Dict[str, Any]]:
        """商品検索とデータ抽出"""
        try:
            self.logger.info(f"商品検索開始: {keyword}")
            
            max_products = max_products or self.config.get_int('mercari', 'max_products_per_search', 50)
            
            with MercariRPA(self.config) as rpa:
                # WebDriverセットアップ
                if not rpa.setup_driver():
                    raise Exception("WebDriverのセットアップに失敗しました")
                
                # メルカリにアクセス
                if not rpa.navigate_to_mercari():
                    raise Exception("メルカリへのアクセスに失敗しました")
                
                # 検索フィルター設定
                filters = {
                    'sold_only': self.config.get_boolean('mercari', 'search_sold_only', True),
                    'condition': self.config.get('mercari', 'search_condition', 'new'),
                    'price_range': self._get_price_filter()
                }
                
                # 検索実行
                if not rpa.perform_search(keyword, filters):
                    raise Exception(f"検索の実行に失敗しました: {keyword}")
                
                # 商品データを収集
                all_products = []
                page_count = 0
                max_pages = self.config.get_int('mercari', 'max_pages', 5)
                
                while len(all_products) < max_products and page_count < max_pages:
                    page_count += 1
                    self.logger.info(f"ページ {page_count} の商品を抽出中...")
                    
                    # 全商品を読み込むためにスクロール
                    rpa.scroll_to_load_all()
                    
                    # 商品データを抽出
                    products = self.extractor.extract_products_from_page(rpa.driver)
                    
                    if not products:
                        self.logger.warning(f"ページ {page_count} で商品が見つかりませんでした")
                        break
                    
                    # 重複除去
                    new_products = self._remove_duplicates(products, all_products)
                    all_products.extend(new_products)
                    
                    self.logger.info(f"ページ {page_count} から {len(new_products)}件の新規商品を取得")
                    
                    # 次のページに進む
                    if len(all_products) < max_products and page_count < max_pages:
                        if not self._go_to_next_page(rpa):
                            break
                
                # 結果を制限
                final_products = all_products[:max_products]
                
                self.logger.info(f"商品検索完了: {len(final_products)}件取得")
                return final_products
                
        except Exception as e:
            self.logger.error(f"商品検索エラー: {e}")
            # エラーハンドリング
            context = {'keyword': keyword, 'function': 'search_products'}
            self.error_handler.handle_error(e, context)
            raise
    
    def _get_price_filter(self) -> Optional[Dict[str, int]]:
        """価格フィルターの取得"""
        min_price = self.config.get_int('mercari', 'min_price')
        max_price = self.config.get_int('mercari', 'max_price')
        
        if min_price or max_price:
            return {
                'min': min_price,
                'max': max_price
            }
        
        return None
    
    def _remove_duplicates(self, new_products: List[Dict], existing_products: List[Dict]) -> List[Dict]:
        """重複商品の除去"""
        existing_urls = {p.get('url') for p in existing_products if p.get('url')}
        
        unique_products = []
        for product in new_products:
            if product.get('url') not in existing_urls:
                unique_products.append(product)
        
        return unique_products
    
    def _go_to_next_page(self, rpa: MercariRPA) -> bool:
        """次のページに移動"""
        try:
            # 次へボタンのセレクター
            next_selectors = [
                '[data-testid="pagination-next"]',
                '.pagination-next',
                'a[aria-label="次のページ"]',
                'a:contains("次へ")'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = rpa.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled():
                        rpa.human.human_click(rpa.driver, next_button)
                        time.sleep(random.uniform(2.0, 4.0))
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"次ページ移動エラー: {e}")
            return False
    
    def save_products_to_csv(self, products: List[Dict[str, Any]], 
                           filename: str = None) -> str:
        """商品データをCSVファイルに保存"""
        try:
            if not products:
                self.logger.warning("保存する商品データがありません")
                return None
            
            # ファイル名の生成
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"mercari_products_{timestamp}.csv"
            
            # 保存ディレクトリの作成
            csv_path = Path(f"results/{datetime.now().strftime('%Y-%m-%d')}")
            csv_path.mkdir(parents=True, exist_ok=True)
            
            full_path = csv_path / filename
            
            # CSV列の定義
            fieldnames = [
                'product_id', 'title', 'price', 'url', 'image_url',
                'is_sold', 'condition', 'like_count', 'keywords',
                'extracted_at', 'source_url'
            ]
            
            # CSVファイルに書き込み
            with open(full_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # ヘッダー行
                writer.writeheader()
                
                # データ行
                for product in products:
                    # キーワードをカンマ区切り文字列に変換
                    if isinstance(product.get('keywords'), list):
                        product['keywords'] = ', '.join(product['keywords'])
                    
                    # 価格を通貨形式でフォーマット
                    if product.get('price'):
                        product['price_formatted'] = format_currency(product['price'])
                    
                    writer.writerow(product)
            
            self.logger.info(f"CSV保存完了: {full_path} ({len(products)}件)")
            return str(full_path)
            
        except Exception as e:
            self.logger.error(f"CSV保存エラー: {e}")
            return None
    
    def save_products_to_database(self, products: List[Dict[str, Any]]) -> int:
        """商品データをデータベースに保存"""
        try:
            saved_count = 0
            
            for product in products:
                try:
                    # データベース形式に変換
                    db_product = {
                        'product_id': product.get('product_id'),
                        'title': product.get('title'),
                        'price': product.get('price'),
                        'condition_text': product.get('condition'),
                        'image_urls': json.dumps([product.get('image_url')]) if product.get('image_url') else None,
                        'like_count': product.get('like_count', 0),
                        'view_count': 0  # 初期値
                    }
                    
                    # データベースに保存
                    self.db.add_mercari_product(db_product)
                    saved_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"商品DB保存エラー: {e}")
                    continue
            
            self.logger.info(f"データベース保存完了: {saved_count}件")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"データベース保存エラー: {e}")
            return 0
    
    def batch_search(self, keywords: List[str]) -> Dict[str, Any]:
        """複数キーワードでの一括検索"""
        try:
            self.logger.info(f"一括検索開始: {len(keywords)}個のキーワード")
            
            all_products = []
            search_results = {}
            
            for i, keyword in enumerate(keywords, 1):
                self.logger.info(f"検索進行 ({i}/{len(keywords)}): {keyword}")
                
                try:
                    products = self.search_products(keyword)
                    
                    if products:
                        all_products.extend(products)
                        search_results[keyword] = {
                            'product_count': len(products),
                            'status': 'success'
                        }
                    else:
                        search_results[keyword] = {
                            'product_count': 0,
                            'status': 'no_results'
                        }
                    
                    # 検索間隔の調整
                    if i < len(keywords):
                        interval = self.config.get_float('mercari', 'search_interval', 3.0)
                        self.logger.debug(f"次の検索まで {interval}秒 待機中...")
                        time.sleep(interval)
                
                except Exception as e:
                    self.logger.error(f"キーワード検索エラー ({keyword}): {e}")
                    search_results[keyword] = {
                        'product_count': 0,
                        'status': 'error',
                        'error': str(e)
                    }
                    continue
            
            # 重複除去
            unique_products = self._remove_duplicates_global(all_products)
            
            # 結果を保存
            if unique_products:
                csv_path = self.save_products_to_csv(unique_products)
                db_count = self.save_products_to_database(unique_products)
            else:
                csv_path = None
                db_count = 0
            
            result = {
                'total_products': len(unique_products),
                'keywords_searched': len(keywords),
                'csv_file': csv_path,
                'database_saved': db_count,
                'search_details': search_results,
                'completed_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"一括検索完了: {result['total_products']}件の商品を収集")
            return result
            
        except Exception as e:
            self.logger.error(f"一括検索エラー: {e}")
            raise
    
    def _remove_duplicates_global(self, products: List[Dict]) -> List[Dict]:
        """グローバル重複除去"""
        seen_urls = set()
        unique_products = []
        
        for product in products:
            url = product.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_products.append(product)
        
        return unique_products
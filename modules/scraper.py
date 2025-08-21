#!/usr/bin/env python3
"""
軽量スクレイピングモジュール
BeautifulSoupとrequestsを使用してRPAなしで商品情報を取得
ChromeDriver/Seleniumの問題を完全に回避
"""
import time
import json
import random
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from bs4 import BeautifulSoup

# プロジェクトのcoreモジュールをインポート（エラーハンドリング追加）
try:
    from core.logger import setup_logger, PerformanceLogger
    from core.utils import clean_text, extract_price, random_delay
except ImportError:
    # 最小限の実装を提供
    import logging
    
    def setup_logger(name):
        """簡易ロガー"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
        return logger
    
    class PerformanceLogger:
        """簡易パフォーマンスロガー"""
        def __init__(self, logger_name=None):
            self.logger = setup_logger(logger_name or __name__)
        
        def measure(self, operation_name):
            """コンテキストマネージャー（簡易版）"""
            class SimpleMeasure:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return SimpleMeasure()
    
    def clean_text(text):
        """テキストクリーニング（簡易版）"""
        if not text:
            return ""
        return text.strip().replace('\n', ' ').replace('\r', '')
    
    def extract_price(text):
        """価格抽出（簡易版）"""
        import re
        if not text:
            return 0
        text = text.replace(',', '').replace('￥', '').replace('¥', '')
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0
    
    def random_delay(min_sec, max_sec):
        """ランダム待機（簡易版）"""
        time.sleep(random.uniform(min_sec, max_sec))

class MercariScraper:
    """メルカリ商品情報スクレイパー（RPA不使用）"""
    
    def __init__(self, config=None):
        """
        初期化
        
        Args:
            config: 設定オブジェクト（オプション）
        """
        self.config = config
        self.logger = setup_logger(__name__ + '.MercariScraper')
        # PerformanceLoggerは使わない（エラー回避）
        # self.perf = PerformanceLogger(__name__ + '.MercariScraper')
        
        # セッション設定（ブラウザを偽装）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # メルカリのベースURL
        self.base_url = "https://jp.mercari.com"
        
        # レート制限
        self.min_delay = 2.0  # 最小待機時間（秒）
        self.max_delay = 5.0  # 最大待機時間（秒）
        
        self.logger.info("MercariScraper 初期化完了（RPA不使用）")
    
    def search_products(self, keyword: str, 
                       conditions: Dict = None,
                       max_items: int = 50) -> List[Dict]:
        """
        商品検索（軽量スクレイピング）
        
        Args:
            keyword: 検索キーワード
            conditions: 検索条件の辞書
            max_items: 最大取得件数
            
        Returns:
            商品情報リスト
        """
        # デフォルト条件
        if conditions is None:
            conditions = {}
        
        self.logger.info(f"検索開始: '{keyword}' (最大{max_items}件)")
        if conditions:
            self.logger.info(f"検索条件: {conditions}")
        
        products = []
        
        try:
            # 検索URLを構築
            search_url = self._build_search_url_with_conditions(keyword, conditions)
            self.logger.debug(f"検索URL: {search_url}")
            
            # ページ取得（PerformanceLoggerを使わない）
            response = self._fetch_page(search_url)
            
            if not response:
                self.logger.error("ページ取得失敗")
                return products
            
            # HTMLパース
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 商品要素を抽出
            product_elements = self._extract_product_elements(soup)
            self.logger.info(f"商品要素検出: {len(product_elements)}件")
            
            # 各商品の情報を抽出
            for i, element in enumerate(product_elements[:max_items]):
                try:
                    product_data = self._parse_product_element(element, i + 1)
                    if product_data:
                        product_data['keyword'] = keyword
                        product_data['scraped_at'] = datetime.now().isoformat()
                        products.append(product_data)
                        
                except Exception as e:
                    self.logger.debug(f"商品パースエラー #{i+1}: {str(e)}")
                    continue
            
            self.logger.info(f"取得完了: {len(products)}件の商品情報")
            
        except Exception as e:
            self.logger.error(f"検索エラー: {str(e)}")
        
        return products
    
    def _build_search_url(self, keyword: str, sold_only: bool = False) -> str:
        """
        検索URLを構築（旧メソッド、互換性のため残す）
        
        Args:
            keyword: 検索キーワード
            sold_only: 売り切れのみ
            
        Returns:
            検索URL
        """
        conditions = {'status': 'sold_out' if sold_only else 'on_sale'}
        return self._build_search_url_with_conditions(keyword, conditions)
    
    def _build_search_url_with_conditions(self, keyword: str, conditions: Dict) -> str:
        """
        条件付き検索URLを構築
        
        Args:
            keyword: 検索キーワード
            conditions: 検索条件
                - status: 'on_sale'（販売中）, 'sold_out'（売り切れ）
                - item_condition: 商品の状態
                    1: 新品、未使用
                    2: 未使用に近い
                    3: 目立った傷や汚れなし
                    4: やや傷や汚れあり
                    5: 傷や汚れあり
                    6: 全体的に状態が悪い
                - price_min: 最低価格
                - price_max: 最高価格
                - shipping_payer: 配送料の負担
                    1: 送料込み（出品者負担）
                    2: 着払い（購入者負担）
                - category_id: カテゴリーID
                - brand_id: ブランドID
                - size_id: サイズID
                - shipping_method: 配送方法
                - days_to_ship: 発送までの日数
                - sort: ソート順
                    'created_time': 新着順
                    'price': 価格順
                    'num_likes': いいね順
                - order: 'desc'（降順）, 'asc'（昇順）
            
        Returns:
            検索URL
        """
        # URLエンコード
        encoded_keyword = quote(keyword)
        
        # 基本URL
        url = f"{self.base_url}/search?keyword={encoded_keyword}"
        
        # 販売状態
        status = conditions.get('status', 'on_sale')
        url += f"&status={status}"
        
        # 商品の状態
        if 'item_condition' in conditions:
            if isinstance(conditions['item_condition'], list):
                # 複数条件
                for cond in conditions['item_condition']:
                    url += f"&item_condition_id[]={cond}"
            else:
                # 単一条件
                url += f"&item_condition_id={conditions['item_condition']}"
        
        # 価格帯
        if 'price_min' in conditions:
            url += f"&price_min={conditions['price_min']}"
        if 'price_max' in conditions:
            url += f"&price_max={conditions['price_max']}"
        
        # 配送料の負担
        if 'shipping_payer' in conditions:
            url += f"&shipping_payer_id={conditions['shipping_payer']}"
        
        # カテゴリー
        if 'category_id' in conditions:
            url += f"&category_id={conditions['category_id']}"
        
        # ブランド
        if 'brand_id' in conditions:
            url += f"&brand_id={conditions['brand_id']}"
        
        # サイズ
        if 'size_id' in conditions:
            url += f"&size_id={conditions['size_id']}"
        
        # 配送方法
        if 'shipping_method' in conditions:
            url += f"&shipping_method_id={conditions['shipping_method']}"
        
        # 発送までの日数
        if 'days_to_ship' in conditions:
            url += f"&shipping_from_duration={conditions['days_to_ship']}"
        
        # ソート順
        sort = conditions.get('sort', 'created_time')
        order = conditions.get('order', 'desc')
        url += f"&sort={sort}&order={order}"
        
        return url
    
    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        """
        ページを取得
        
        Args:
            url: 取得するURL
            
        Returns:
            レスポンスオブジェクト
        """
        try:
            # リクエスト前に待機（レート制限）
            random_delay(self.min_delay, self.max_delay)
            
            # ページ取得
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"HTTP要求エラー: {str(e)}")
            return None
    
    def _extract_product_elements(self, soup: BeautifulSoup) -> List:
        """
        商品要素を抽出
        
        Args:
            soup: BeautifulSoupオブジェクト
            
        Returns:
            商品要素のリスト
        """
        # メルカリの商品リスト要素のセレクター候補
        selectors = [
            # 新しいデザイン
            'li[data-testid="item-cell"]',
            'div[data-testid="item-cell"]',
            'article[data-testid="item-cell"]',
            
            # 旧デザイン
            'section.items-box',
            'div.items-box',
            'a.items-box',
            
            # より一般的なセレクター
            'div[class*="ItemCard"]',
            'div[class*="item-card"]',
            'li[class*="item"]',
            
            # グリッド表示
            'div[class*="grid"] > div > a',
            'ul[class*="grid"] > li > a'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                self.logger.debug(f"商品要素セレクター使用: {selector}")
                return elements
        
        # フォールバック：リンクから商品を探す
        all_links = soup.find_all('a', href=True)
        product_links = [
            link for link in all_links 
            if '/item/' in link.get('href', '')
        ]
        
        if product_links:
            self.logger.debug(f"フォールバック：商品リンクから{len(product_links)}件検出")
            return product_links
        
        self.logger.warning("商品要素が見つかりません")
        return []
    
    def _parse_product_element(self, element, index: int = 0) -> Optional[Dict]:
        """
        商品要素から情報を抽出
        
        Args:
            element: 商品要素
            index: インデックス（デバッグ用）
            
        Returns:
            商品情報辞書
        """
        try:
            product = {}
            
            # 商品URL
            product_url = self._extract_product_url(element)
            if not product_url:
                self.logger.debug(f"商品#{index}: URLが見つかりません")
                return None
            product['url'] = product_url
            
            # 商品IDを抽出
            product['product_id'] = self._extract_product_id(product_url)
            
            # タイトル
            product['title'] = self._extract_title(element)
            
            # 価格
            product['price'] = self._extract_price_from_element(element)
            
            # 画像URL
            product['image_url'] = self._extract_image_url(element)
            
            # 販売状態
            product['is_sold'] = self._check_sold_status(element)
            
            # いいね数（取得できる場合）
            product['likes'] = self._extract_likes(element)
            
            self.logger.debug(f"商品#{index}: {product['title'][:30]}... ¥{product['price']:,}")
            
            return product
            
        except Exception as e:
            self.logger.debug(f"商品#{index} パースエラー: {str(e)}")
            return None
    
    def _extract_product_url(self, element) -> Optional[str]:
        """商品URLを抽出"""
        # elementがaタグの場合
        if element.name == 'a':
            href = element.get('href', '')
            if href:
                return urljoin(self.base_url, href)
        
        # 子要素からaタグを探す
        link = element.find('a', href=True)
        if link:
            href = link.get('href', '')
            if '/item/' in href:
                return urljoin(self.base_url, href)
        
        return None
    
    def _extract_product_id(self, url: str) -> str:
        """URLから商品IDを抽出"""
        if '/item/' in url:
            # URLから商品ID部分を抽出
            parts = url.split('/item/')
            if len(parts) > 1:
                # クエリパラメータを除去
                product_id = parts[1].split('?')[0].split('/')[0]
                return product_id
        
        return f"unknown_{int(time.time())}"
    
    def _extract_title(self, element) -> str:
        """タイトルを抽出"""
        # タイトル要素のセレクター候補
        title_selectors = [
            'h3', 'h4', 'h5',
            '[aria-label]',
            '.items-box-name',
            '[class*="ItemCard__title"]',
            '[class*="item-name"]',
            '[class*="title"]',
            'span[class*="name"]'
        ]
        
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem:
                # aria-labelがある場合はそれを優先
                if title_elem.get('aria-label'):
                    return clean_text(title_elem['aria-label'])
                
                text = title_elem.get_text(strip=True)
                if text:
                    return clean_text(text)
        
        # imgのalt属性から取得
        img = element.find('img')
        if img and img.get('alt'):
            return clean_text(img['alt'])
        
        return "商品名不明"
    
    def _extract_price_from_element(self, element) -> int:
        """価格を抽出"""
        # 価格要素のセレクター候補
        price_selectors = [
            '.items-box-price',
            '[class*="price"]',
            '[class*="Price"]',
            'span[class*="amount"]',
            '[data-testid*="price"]'
        ]
        
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text()
                price = extract_price(price_text)
                if price > 0:
                    return price
        
        # テキスト全体から価格パターンを探す
        text = element.get_text()
        price = extract_price(text)
        
        return price
    
    def _extract_image_url(self, element) -> str:
        """画像URLを抽出"""
        # img要素を探す
        img = element.find('img')
        if img:
            # 優先順位: data-src > src
            return img.get('data-src') or img.get('src', '')
        
        # 背景画像から取得
        for elem in element.find_all(style=True):
            style = elem.get('style', '')
            if 'background-image' in style and 'url(' in style:
                # URLを抽出
                import re
                match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                if match:
                    return match.group(1)
        
        return ""
    
    def _check_sold_status(self, element) -> bool:
        """売り切れ状態をチェック"""
        # 売り切れを示すテキスト
        sold_indicators = ['SOLD', 'sold', '売り切れ', '売切れ', 'SOLD OUT']
        
        text = element.get_text()
        for indicator in sold_indicators:
            if indicator in text:
                return True
        
        # 売り切れバッジを探す
        sold_badge = element.select_one('[class*="sold"], [class*="Sold"], .badge-sold')
        if sold_badge:
            return True
        
        return False
    
    def _extract_likes(self, element) -> int:
        """いいね数を抽出"""
        # いいね要素のセレクター
        like_selectors = [
            '[class*="like"]',
            '[class*="Like"]',
            '[data-testid*="like"]',
            '.icon-like-border + span'
        ]
        
        for selector in like_selectors:
            like_elem = element.select_one(selector)
            if like_elem:
                text = like_elem.get_text()
                # 数字を抽出
                import re
                match = re.search(r'\d+', text)
                if match:
                    return int(match.group())
        
        return 0
    
    def get_product_details(self, product_url: str) -> Optional[Dict]:
        """
        商品詳細情報を取得（個別ページ）
        
        Args:
            product_url: 商品URL
            
        Returns:
            詳細商品情報
        """
        self.logger.info(f"商品詳細取得: {product_url}")
        
        try:
            # ページ取得
            response = self._fetch_page(product_url)
            if not response:
                return None
            
            # パース
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 詳細情報を抽出
            details = {
                'url': product_url,
                'product_id': self._extract_product_id(product_url),
                'title': self._extract_detail_title(soup),
                'price': self._extract_detail_price(soup),
                'description': self._extract_description(soup),
                'condition': self._extract_condition(soup),
                'shipping_payer': self._extract_shipping_payer(soup),
                'shipping_method': self._extract_shipping_method(soup),
                'shipping_from': self._extract_shipping_from(soup),
                'category': self._extract_category(soup),
                'brand': self._extract_brand(soup),
                'seller': self._extract_seller_info(soup),
                'images': self._extract_all_images(soup),
                'likes': self._extract_detail_likes(soup),
                'comments': self._extract_comments_count(soup),
                'updated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"詳細取得完了: {details['title'][:30]}...")
            return details
            
        except Exception as e:
            self.logger.error(f"詳細取得エラー: {str(e)}")
            return None
    
    def _extract_detail_title(self, soup: BeautifulSoup) -> str:
        """詳細ページからタイトル抽出"""
        # タイトル要素の候補
        selectors = [
            'h1[class*="heading"]',
            'h1[class*="title"]',
            'h1',
            '[data-testid="item-name"]',
            '.item-name'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return clean_text(elem.get_text())
        
        # metaタグから取得
        meta_title = soup.find('meta', {'property': 'og:title'})
        if meta_title:
            return clean_text(meta_title.get('content', ''))
        
        return "タイトル不明"
    
    def _extract_detail_price(self, soup: BeautifulSoup) -> int:
        """詳細ページから価格抽出"""
        # 価格要素の候補
        selectors = [
            '[class*="item-price"]',
            '[class*="Price"]',
            '[data-testid="price"]',
            '.mer-spacing-b-2'  # メルカリ特有のクラス
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                price = extract_price(elem.get_text())
                if price > 0:
                    return price
        
        return 0
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """商品説明を抽出"""
        # 説明要素の候補
        selectors = [
            '[data-testid="description"]',
            '[class*="description"]',
            '[class*="Description"]',
            'pre[class*="mer-spacing"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return clean_text(elem.get_text())
        
        return ""
    
    def _extract_condition(self, soup: BeautifulSoup) -> str:
        """商品の状態を抽出"""
        # 商品情報テーブルから抽出
        for row in soup.select('tr'):
            header = row.select_one('th')
            if header and '商品の状態' in header.get_text():
                value = row.select_one('td')
                if value:
                    return clean_text(value.get_text())
        
        return "不明"
    
    def _extract_shipping_payer(self, soup: BeautifulSoup) -> str:
        """配送料の負担を抽出"""
        for row in soup.select('tr'):
            header = row.select_one('th')
            if header and '配送料の負担' in header.get_text():
                value = row.select_one('td')
                if value:
                    return clean_text(value.get_text())
        
        return "不明"
    
    def _extract_shipping_method(self, soup: BeautifulSoup) -> str:
        """配送方法を抽出"""
        for row in soup.select('tr'):
            header = row.select_one('th')
            if header and '配送の方法' in header.get_text():
                value = row.select_one('td')
                if value:
                    return clean_text(value.get_text())
        
        return "不明"
    
    def _extract_shipping_from(self, soup: BeautifulSoup) -> str:
        """発送元を抽出"""
        for row in soup.select('tr'):
            header = row.select_one('th')
            if header and '発送元' in header.get_text():
                value = row.select_one('td')
                if value:
                    return clean_text(value.get_text())
        
        return "不明"
    
    def _extract_category(self, soup: BeautifulSoup) -> List[str]:
        """カテゴリを抽出"""
        categories = []
        
        # パンくずリストから取得
        breadcrumbs = soup.select('nav[aria-label="Breadcrumb"] a')
        for crumb in breadcrumbs:
            text = clean_text(crumb.get_text())
            if text and text != 'メルカリ':
                categories.append(text)
        
        return categories
    
    def _extract_brand(self, soup: BeautifulSoup) -> str:
        """ブランドを抽出"""
        for row in soup.select('tr'):
            header = row.select_one('th')
            if header and 'ブランド' in header.get_text():
                value = row.select_one('td')
                if value:
                    return clean_text(value.get_text())
        
        return ""
    
    def _extract_seller_info(self, soup: BeautifulSoup) -> Dict:
        """出品者情報を抽出"""
        seller_info = {
            'name': '',
            'rating': 0.0,
            'ratings_count': 0
        }
        
        # 出品者セクションを探す
        seller_section = soup.select_one('[data-testid="seller-info"]')
        if seller_section:
            # 名前
            name_elem = seller_section.select_one('a')
            if name_elem:
                seller_info['name'] = clean_text(name_elem.get_text())
            
            # 評価
            rating_elem = seller_section.select_one('[class*="rating"]')
            if rating_elem:
                import re
                rating_text = rating_elem.get_text()
                # 数値を抽出
                numbers = re.findall(r'\d+\.?\d*', rating_text)
                if numbers:
                    seller_info['rating'] = float(numbers[0])
                    if len(numbers) > 1:
                        seller_info['ratings_count'] = int(numbers[1])
        
        return seller_info
    
    def _extract_all_images(self, soup: BeautifulSoup) -> List[str]:
        """全ての商品画像URLを抽出"""
        images = []
        
        # 画像ギャラリーから取得
        for img in soup.select('[data-testid*="image"] img'):
            src = img.get('data-src') or img.get('src')
            if src and src not in images:
                images.append(src)
        
        # メタタグから取得
        if not images:
            meta_image = soup.find('meta', {'property': 'og:image'})
            if meta_image:
                images.append(meta_image.get('content', ''))
        
        return images
    
    def _extract_detail_likes(self, soup: BeautifulSoup) -> int:
        """詳細ページからいいね数を抽出"""
        like_button = soup.select_one('button[aria-label*="いいね"]')
        if like_button:
            import re
            text = like_button.get_text()
            match = re.search(r'\d+', text)
            if match:
                return int(match.group())
        
        return 0
    
    def _extract_comments_count(self, soup: BeautifulSoup) -> int:
        """コメント数を抽出"""
        comment_section = soup.select_one('[data-testid="comment-list"]')
        if comment_section:
            comments = comment_section.select('[data-testid="comment"]')
            return len(comments)
        
        return 0
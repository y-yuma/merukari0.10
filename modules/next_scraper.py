#!/usr/bin/env python3
"""
NextDataScraperモジュール
メルカリの__NEXT_DATA__から商品情報を取得
"""
import json
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class NextDataScraper:
    """メルカリの__NEXT_DATA__から商品情報を取得（名前を短く変更）"""
    
    def __init__(self, db_path: str = "mercari.db"):
        """初期化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # データベース初期化
        self.db_path = db_path
        self._init_db()
        
        print("✅ NextDataScraper 初期化完了")
    
    def _init_db(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                title TEXT,
                price INTEGER,
                thumb_url TEXT,
                item_url TEXT,
                status TEXT,
                image_hash TEXT,
                ocr_text TEXT,
                is_professional BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_items (
                item_id TEXT PRIMARY KEY,
                first_seen TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def fetch_items(self, keyword: str, conditions: Dict = None, max_items: int = 30) -> List[Dict]:
        """
        商品を取得（__NEXT_DATA__方式）
        
        Args:
            keyword: 検索キーワード
            conditions: 検索条件
            max_items: 最大取得件数
        
        Returns:
            商品リスト
        """
        # URL構築
        url = self._build_url(keyword, conditions or {})
        print(f"🔍 検索URL: {url}")
        
        try:
            # ページ取得
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # __NEXT_DATA__を抽出
            items = self._extract_next_data(response.text)
            
            if items:
                print(f"✅ {len(items)}件の商品データを取得")
                # 新規商品のみフィルタ
                new_items = self._filter_new_items(items)
                print(f"🆕 新規商品: {len(new_items)}件")
                return new_items[:max_items]  # 最大件数で制限
            else:
                print("⚠️ __NEXT_DATA__が見つかりません")
                return []
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            return []
    
    def _build_url(self, keyword: str, conditions: Dict) -> str:
        """検索URL構築"""
        base = "https://jp.mercari.com/search"
        params = [f"keyword={keyword}"]
        
        # 販売状態
        if conditions.get('status') == 'on_sale':
            params.append("status=on_sale")
        elif conditions.get('status') == 'sold_out':
            params.append("status=sold_out")
        
        # 商品の状態（1=新品）
        if conditions.get('item_condition'):
            params.append(f"item_condition_id={conditions['item_condition']}")
        
        # 価格帯
        if conditions.get('price_min'):
            params.append(f"price_min={conditions['price_min']}")
        if conditions.get('price_max'):
            params.append(f"price_max={conditions['price_max']}")
        
        # 配送料（2=送料込み）
        if conditions.get('shipping_payer'):
            params.append("shipping_payer_id=2")
        
        # ソート
        sort = conditions.get('sort', 'created_time')
        order = conditions.get('order', 'desc')
        params.append(f"sort={sort}")
        params.append(f"order={order}")
        
        return f"{base}?{'&'.join(params)}"
    
    def _extract_next_data(self, html: str) -> List[Dict]:
        """HTMLから__NEXT_DATA__を抽出"""
        soup = BeautifulSoup(html, 'lxml')
        
        # __NEXT_DATA__スクリプトタグを探す
        script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
        
        if not script or not script.string:
            # フォールバック: 別のパターンを試す
            scripts = soup.find_all('script')
            for s in scripts:
                if s.string and '"pageProps"' in s.string and '"initialState"' in s.string:
                    try:
                        data = json.loads(s.string)
                        return self._parse_items(data)
                    except:
                        continue
            return []
        
        try:
            data = json.loads(script.string)
            return self._parse_items(data)
        except json.JSONDecodeError as e:
            print(f"❌ JSON パースエラー: {str(e)}")
            return []
    
    def _parse_items(self, data: Dict) -> List[Dict]:
        """JSONデータから商品を抽出"""
        items = []
        
        # パターン1: initialState.searchResult.itemGrid.items
        try:
            item_list = (data.get('props', {})
                        .get('pageProps', {})
                        .get('initialState', {})
                        .get('searchResult', {})
                        .get('itemGrid', {})
                        .get('items', []))
            
            if item_list:
                for item in item_list:
                    items.append(self._format_item(item))
                return items
        except:
            pass
        
        # パターン2: pageProps.items
        try:
            item_list = (data.get('props', {})
                        .get('pageProps', {})
                        .get('items', []))
            
            if item_list:
                for item in item_list:
                    items.append(self._format_item(item))
                return items
        except:
            pass
        
        # パターン3: initialState.entities.items
        try:
            entities = (data.get('props', {})
                       .get('pageProps', {})
                       .get('initialState', {})
                       .get('entities', {})
                       .get('items', {}))
            
            for item_id, item in entities.items():
                items.append(self._format_item(item))
            return items
        except:
            pass
        
        return items
    
    def _format_item(self, item: Dict) -> Dict:
        """商品データを統一フォーマットに変換"""
        # IDの取得（複数パターン対応）
        item_id = item.get('id') or item.get('itemId') or item.get('productId', '')
        
        # サムネイル画像の取得
        thumb = (item.get('thumbnailUrl') or 
                item.get('thumbnail') or 
                item.get('thumbnails', [None])[0] or
                item.get('imageUrl', ''))
        
        # タイトルの取得
        title = item.get('name') or item.get('title') or item.get('itemName', '')
        
        # 価格の取得
        price = item.get('price', 0)
        if isinstance(price, dict):
            price = price.get('value', 0)
        
        # URLの生成
        item_url = f"https://jp.mercari.com/item/{item_id}"
        if 'url' in item:
            item_url = item['url'] if item['url'].startswith('http') else f"https://jp.mercari.com{item['url']}"
        
        return {
            'id': str(item_id),
            'title': title,
            'price': int(price),
            'thumb_url': thumb,
            'url': item_url,  # item_url → url に変更
            'status': item.get('status', ''),
            'seller': item.get('seller', {}).get('name', ''),
            'likes': item.get('numLikes', 0),
            'condition': item.get('condition', ''),
            'shipping': item.get('shippingPayer', ''),
            'created_at': datetime.now().isoformat()
        }
    
    def _filter_new_items(self, items: List[Dict]) -> List[Dict]:
        """新規商品のみフィルタ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_items = []
        for item in items:
            # 既に見た商品かチェック
            cursor.execute('SELECT item_id FROM seen_items WHERE item_id = ?', (item['id'],))
            if not cursor.fetchone():
                new_items.append(item)
                # 見た商品として記録
                cursor.execute(
                    'INSERT INTO seen_items (item_id, first_seen) VALUES (?, ?)',
                    (item['id'], datetime.now())
                )
        
        conn.commit()
        conn.close()
        
        return new_items
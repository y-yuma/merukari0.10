"""
データベース操作モジュール
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from core.logger import setup_logger

class Database:
    """データベース操作クラス"""
    
    def __init__(self, db_path='data/database.db'):
        """初期化"""
        self.db_path = Path(db_path)
        self.logger = setup_logger(__name__)
        
        # データディレクトリの作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベースの初期化
        self._initialize_database()
    
    def _initialize_database(self):
        """データベースの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # メルカリ商品テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mercari_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    seller_name TEXT,
                    condition_text TEXT,
                    description TEXT,
                    category TEXT,
                    brand TEXT,
                    shipping_method TEXT,
                    shipping_cost INTEGER,
                    image_urls TEXT,  -- JSON形式
                    sold_date TEXT,
                    view_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # アリババ商品テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alibaba_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    price_cny REAL NOT NULL,
                    price_jpy REAL NOT NULL,
                    min_order_quantity INTEGER,
                    supplier_name TEXT,
                    supplier_rating REAL,
                    image_urls TEXT,  -- JSON形式
                    specifications TEXT,  -- JSON形式
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 商品分析テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS product_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mercari_product_id TEXT NOT NULL,
                    alibaba_product_id TEXT,
                    image_quality_score REAL,
                    profit_rate REAL,
                    profit_amount INTEGER,
                    investment_amount INTEGER,
                    roi REAL,
                    risk_score REAL,
                    recommendation TEXT,  -- BUY, SKIP, WATCH
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mercari_product_id) REFERENCES mercari_products(product_id),
                    FOREIGN KEY (alibaba_product_id) REFERENCES alibaba_products(product_id)
                )
            ''')
            
            # 出品履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS listing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id TEXT UNIQUE NOT NULL,
                    original_product_id TEXT,
                    title TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    category TEXT,
                    condition_text TEXT,
                    description TEXT,
                    shipping_method TEXT,
                    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE, SOLD, STOPPED
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sold_at TIMESTAMP,
                    sold_price INTEGER,
                    profit INTEGER,
                    FOREIGN KEY (original_product_id) REFERENCES mercari_products(product_id)
                )
            ''')
            
            # キーワード管理テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    category TEXT,
                    priority INTEGER DEFAULT 1,
                    last_searched TIMESTAMP,
                    search_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # システムログテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    module TEXT,
                    message TEXT NOT NULL,
                    details TEXT,  -- JSON形式
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # パフォーマンステーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_name TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    memory_usage REAL,
                    cpu_usage REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックスの作成
            self._create_indexes(cursor)
            
            conn.commit()
            self.logger.info("データベースの初期化が完了しました")
    
    def _create_indexes(self, cursor):
        """インデックスの作成"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_mercari_price ON mercari_products(price)",
            "CREATE INDEX IF NOT EXISTS idx_mercari_created_at ON mercari_products(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_mercari_category ON mercari_products(category)",
            "CREATE INDEX IF NOT EXISTS idx_alibaba_price ON alibaba_products(price_jpy)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_profit ON product_analysis(profit_rate)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_date ON product_analysis(analysis_date)",
            "CREATE INDEX IF NOT EXISTS idx_listing_status ON listing_history(status)",
            "CREATE INDEX IF NOT EXISTS idx_keywords_active ON keywords(is_active)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    def add_mercari_product(self, product_data: Dict[str, Any]) -> int:
        """メルカリ商品の追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO mercari_products 
                    (product_id, title, price, seller_name, condition_text, description,
                     category, brand, shipping_method, shipping_cost, image_urls,
                     sold_date, view_count, like_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    product_data.get('product_id'),
                    product_data.get('title'),
                    product_data.get('price'),
                    product_data.get('seller_name'),
                    product_data.get('condition_text'),
                    product_data.get('description'),
                    product_data.get('category'),
                    product_data.get('brand'),
                    product_data.get('shipping_method'),
                    product_data.get('shipping_cost'),
                    json.dumps(product_data.get('image_urls', [])),
                    product_data.get('sold_date'),
                    product_data.get('view_count', 0),
                    product_data.get('like_count', 0)
                ))
                
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                self.logger.error(f"メルカリ商品追加エラー: {e}")
                raise
    
    def add_alibaba_product(self, product_data: Dict[str, Any]) -> int:
        """アリババ商品の追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO alibaba_products 
                    (product_id, title, price_cny, price_jpy, min_order_quantity,
                     supplier_name, supplier_rating, image_urls, specifications, url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    product_data.get('product_id'),
                    product_data.get('title'),
                    product_data.get('price_cny'),
                    product_data.get('price_jpy'),
                    product_data.get('min_order_quantity'),
                    product_data.get('supplier_name'),
                    product_data.get('supplier_rating'),
                    json.dumps(product_data.get('image_urls', [])),
                    json.dumps(product_data.get('specifications', {})),
                    product_data.get('url')
                ))
                
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                self.logger.error(f"アリババ商品追加エラー: {e}")
                raise
    
    def add_product_analysis(self, analysis_data: Dict[str, Any]) -> int:
        """商品分析の追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO product_analysis 
                    (mercari_product_id, alibaba_product_id, image_quality_score,
                     profit_rate, profit_amount, investment_amount, roi, risk_score, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis_data.get('mercari_product_id'),
                    analysis_data.get('alibaba_product_id'),
                    analysis_data.get('image_quality_score'),
                    analysis_data.get('profit_rate'),
                    analysis_data.get('profit_amount'),
                    analysis_data.get('investment_amount'),
                    analysis_data.get('roi'),
                    analysis_data.get('risk_score'),
                    analysis_data.get('recommendation')
                ))
                
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                self.logger.error(f"商品分析追加エラー: {e}")
                raise
    
    def get_profitable_products(self, min_profit_rate: float = 0.3, limit: int = 50) -> List[Dict]:
        """利益率の高い商品を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT m.*, a.*, pa.profit_rate, pa.profit_amount, pa.roi
                FROM mercari_products m
                JOIN product_analysis pa ON m.product_id = pa.mercari_product_id
                LEFT JOIN alibaba_products a ON pa.alibaba_product_id = a.product_id
                WHERE pa.profit_rate >= ? AND pa.recommendation = 'BUY'
                ORDER BY pa.profit_rate DESC, pa.roi DESC
                LIMIT ?
            ''', (min_profit_rate, limit))
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # JSON文字列を辞書に変換
                if result.get('image_urls'):
                    result['image_urls'] = json.loads(result['image_urls'])
                if result.get('specifications'):
                    result['specifications'] = json.loads(result['specifications'])
                results.append(result)
            
            return results
    
    def add_keyword(self, keyword: str, category: str = None, priority: int = 1) -> int:
        """キーワードの追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO keywords (keyword, category, priority)
                    VALUES (?, ?, ?)
                ''', (keyword, category, priority))
                
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                self.logger.error(f"キーワード追加エラー: {e}")
                raise
    
    def update_keyword_stats(self, keyword: str, success_count: int, total_count: int):
        """キーワード統計の更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            success_rate = success_count / total_count if total_count > 0 else 0.0
            
            cursor.execute('''
                UPDATE keywords 
                SET last_searched = CURRENT_TIMESTAMP,
                    search_count = search_count + 1,
                    success_rate = ?
                WHERE keyword = ?
            ''', (success_rate, keyword))
    
    def get_active_keywords(self, limit: int = None) -> List[Dict]:
        """アクティブなキーワード一覧を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            sql = '''
                SELECT * FROM keywords 
                WHERE is_active = 1 
                ORDER BY priority DESC, success_rate DESC
            '''
            
            if limit:
                sql += f' LIMIT {limit}'
            
            cursor.execute(sql)
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def log_performance(self, operation_name: str, execution_time: float, 
                       memory_usage: float = None, cpu_usage: float = None):
        """パフォーマンス情報の記録"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (operation_name, execution_time, memory_usage, cpu_usage)
                VALUES (?, ?, ?, ?)
            ''', (operation_name, execution_time, memory_usage, cpu_usage))
    
    def cleanup_old_data(self, days: int = 30):
        """古いデータのクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 古いシステムログを削除
            cursor.execute('''
                DELETE FROM system_logs 
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            # 古いパフォーマンスデータを削除
            cursor.execute('''
                DELETE FROM performance_metrics 
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            deleted_logs = cursor.rowcount
            self.logger.info(f"古いデータを削除しました: {deleted_logs}件")
    
    def backup_database(self, backup_path: str = None):
        """データベースのバックアップ"""
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"data/backup/database_backup_{timestamp}.db"
        
        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        # ファイルコピーによるバックアップ
        import shutil
        shutil.copy2(self.db_path, backup_file)
        
        self.logger.info(f"データベースをバックアップしました: {backup_file}")
        return backup_file
    
    def get_statistics(self) -> Dict[str, Any]:
        """データベース統計情報の取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 各テーブルのレコード数
            tables = ['mercari_products', 'alibaba_products', 'product_analysis', 
                     'listing_history', 'keywords']
            
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()[0]
            
            # 今日の分析件数
            cursor.execute('''
                SELECT COUNT(*) FROM product_analysis 
                WHERE DATE(analysis_date) = DATE('now')
            ''')
            stats['today_analysis_count'] = cursor.fetchone()[0]
            
            # 利益率の平均
            cursor.execute('''
                SELECT AVG(profit_rate) FROM product_analysis 
                WHERE profit_rate > 0
            ''')
            result = cursor.fetchone()[0]
            stats['avg_profit_rate'] = result if result else 0.0
            
            return stats
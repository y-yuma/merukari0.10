#!/usr/bin/env python3
"""
条件設定対応版 実行スクリプト
メルカリの詳細な検索条件を設定して商品を取得
"""
import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# インポート（エラーハンドリング追加）
try:
    from core.config import Config
    from core.logger import setup_logger
except ImportError:
    # Config, loggerが無い場合の簡易実装
    import logging
    
    class Config:
        """簡易設定クラス"""
        def get(self, section, key, default=None):
            return default
        def get_float(self, section, key, default=0.0):
            return default
        def get_int(self, section, key, default=0):
            return default
        def get_boolean(self, section, key, default=False):
            return default
    
    def setup_logger(name):
        """簡易ロガー"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

from modules.scraper import MercariScraper

class ConditionBuilder:
    """検索条件を対話的に構築するヘルパークラス"""
    
    @staticmethod
    def build_conditions() -> Dict:
        """対話的に検索条件を構築"""
        conditions = {}
        
        print("\n" + "=" * 60)
        print("⚙️  検索条件の設定（Enterでスキップ）")
        print("=" * 60)
        
        # 1. 販売状態
        print("\n【販売状態】")
        print("1: 販売中")
        print("2: 売り切れ")
        status_input = input("選択 (1-2): ").strip()
        if status_input == '1':
            conditions['status'] = 'on_sale'
        elif status_input == '2':
            conditions['status'] = 'sold_out'
        else:
            conditions['status'] = 'on_sale'  # デフォルト
        
        # 2. 商品の状態
        print("\n【商品の状態】")
        print("1: 新品、未使用")
        print("2: 未使用に近い")
        print("3: 目立った傷や汚れなし")
        print("4: やや傷や汚れあり")
        print("5: 傷や汚れあり")
        print("6: 全体的に状態が悪い")
        print("複数選択可（例: 1,2,3）")
        condition_input = input("選択: ").strip()
        if condition_input:
            if ',' in condition_input:
                # 複数選択
                conditions['item_condition'] = [int(x.strip()) for x in condition_input.split(',') if x.strip().isdigit()]
            elif condition_input.isdigit():
                # 単一選択
                conditions['item_condition'] = int(condition_input)
        
        # 3. 価格帯
        print("\n【価格帯】")
        min_price = input("最低価格（円）: ").strip()
        if min_price and min_price.isdigit():
            conditions['price_min'] = int(min_price)
        
        max_price = input("最高価格（円）: ").strip()
        if max_price and max_price.isdigit():
            conditions['price_max'] = int(max_price)
        
        # 4. 配送料の負担
        print("\n【配送料の負担】")
        print("1: 送料込み（出品者負担）")
        print("2: 着払い（購入者負担）")
        shipping_input = input("選択 (1-2): ").strip()
        if shipping_input == '1':
            conditions['shipping_payer'] = 1
        elif shipping_input == '2':
            conditions['shipping_payer'] = 2
        
        # 5. ソート順
        print("\n【並び順】")
        print("1: 新着順（おすすめ）")
        print("2: 価格の安い順")
        print("3: 価格の高い順")
        print("4: いいね順")
        sort_input = input("選択 (1-4): ").strip()
        if sort_input == '1':
            conditions['sort'] = 'created_time'
            conditions['order'] = 'desc'
        elif sort_input == '2':
            conditions['sort'] = 'price'
            conditions['order'] = 'asc'
        elif sort_input == '3':
            conditions['sort'] = 'price'
            conditions['order'] = 'desc'
        elif sort_input == '4':
            conditions['sort'] = 'num_likes'
            conditions['order'] = 'desc'
        else:
            conditions['sort'] = 'created_time'
            conditions['order'] = 'desc'
        
        return conditions
    
    @staticmethod
    def build_quick_presets() -> Dict:
        """よく使う条件のプリセット"""
        print("\n" + "=" * 60)
        print("🎯 クイック設定（よく使う条件）")
        print("=" * 60)
        print("1: 新品・未使用のみ（送料込み）")
        print("2: 売り切れ商品（人気商品リサーチ）")
        print("3: 激安商品（1000円以下）")
        print("4: 高額商品（10000円以上）")
        print("5: 美品狙い（状態1-3）")
        print("6: カスタム設定")
        print("0: 条件なし（全商品）")
        
        choice = input("\n選択 (0-6): ").strip()
        
        if choice == '1':
            return {
                'status': 'on_sale',
                'item_condition': 1,
                'shipping_payer': 1,
                'sort': 'created_time',
                'order': 'desc'
            }
        elif choice == '2':
            return {
                'status': 'sold_out',
                'sort': 'created_time',
                'order': 'desc'
            }
        elif choice == '3':
            return {
                'status': 'on_sale',
                'price_max': 1000,
                'sort': 'price',
                'order': 'asc'
            }
        elif choice == '4':
            return {
                'status': 'on_sale',
                'price_min': 10000,
                'sort': 'price',
                'order': 'desc'
            }
        elif choice == '5':
            return {
                'status': 'on_sale',
                'item_condition': [1, 2, 3],
                'sort': 'created_time',
                'order': 'desc'
            }
        elif choice == '6':
            return ConditionBuilder.build_conditions()
        else:
            return {}

def format_conditions_display(conditions: Dict) -> str:
    """条件を見やすく表示"""
    if not conditions:
        return "条件なし（全商品）"
    
    display_parts = []
    
    # 販売状態
    if 'status' in conditions:
        status_text = "販売中" if conditions['status'] == 'on_sale' else "売り切れ"
        display_parts.append(f"状態:{status_text}")
    
    # 商品の状態
    if 'item_condition' in conditions:
        condition_map = {
            1: "新品", 2: "未使用に近い", 3: "美品",
            4: "やや傷あり", 5: "傷あり", 6: "状態悪い"
        }
        if isinstance(conditions['item_condition'], list):
            cond_texts = [condition_map.get(c, str(c)) for c in conditions['item_condition']]
            display_parts.append(f"商品状態:{','.join(cond_texts)}")
        else:
            display_parts.append(f"商品状態:{condition_map.get(conditions['item_condition'], '')}")
    
    # 価格帯
    if 'price_min' in conditions or 'price_max' in conditions:
        min_p = conditions.get('price_min', 0)
        max_p = conditions.get('price_max', '上限なし')
        display_parts.append(f"価格:¥{min_p:,}〜{max_p:,}" if max_p != '上限なし' else f"価格:¥{min_p:,}〜")
    
    # 配送料
    if 'shipping_payer' in conditions:
        ship_text = "送料込み" if conditions['shipping_payer'] == 1 else "着払い"
        display_parts.append(f"配送:{ship_text}")
    
    # ソート
    if 'sort' in conditions:
        sort_map = {
            'created_time': '新着順',
            'price': '価格順',
            'num_likes': 'いいね順'
        }
        display_parts.append(f"並び:{sort_map.get(conditions['sort'], '')}")
    
    return " / ".join(display_parts)

def save_results(products: List[Dict], conditions: Dict, keyword: str):
    """結果を保存"""
    if not products:
        return None
    
    # タイムスタンプ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 条件をファイル名に含める
    condition_str = ""
    if conditions.get('item_condition') == 1:
        condition_str = "_新品"
    elif conditions.get('status') == 'sold_out':
        condition_str = "_売切"
    
    # ファイル名
    filename = f"results/{keyword}{condition_str}_{timestamp}.csv"
    
    # ディレクトリ作成
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # CSV書き込み
    fieldnames = ['product_id', 'title', 'price', 'url', 'image_url', 
                  'is_sold', 'likes', 'keyword', 'scraped_at']
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(products)
    
    print(f"✅ CSV保存: {output_path}")
    
    # 条件もJSONで保存
    json_path = output_path.with_suffix('.json')
    save_data = {
        'keyword': keyword,
        'conditions': conditions,
        'count': len(products),
        'timestamp': timestamp,
        'products': products
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    return output_path

def main():
    """メイン処理"""
    print("""
╔══════════════════════════════════════════════════╗
║   メルカリ商品検索ツール - 詳細条件設定版         ║
║   新品のみ、価格帯指定など細かい条件で検索可能     ║
╚══════════════════════════════════════════════════╝
    """)
    
    # スクレイパー初期化
    config = Config()
    logger = setup_logger(__name__)
    scraper = MercariScraper(config)
    
    # キーワード入力
    print("\n📝 検索キーワードを入力してください")
    keyword = input("キーワード: ").strip()
    
    if not keyword:
        keyword = "ワイヤレスマウス"
        print(f"ℹ️ デフォルト: {keyword}")
    
    # 条件設定
    conditions = ConditionBuilder.build_quick_presets()
    
    # 取得件数
    max_items_input = input("\n最大取得件数 (デフォルト: 30): ").strip()
    max_items = int(max_items_input) if max_items_input and max_items_input.isdigit() else 30
    
    # 検索実行
    print("\n" + "=" * 70)
    print("🔍 検索実行")
    print(f"キーワード: {keyword}")
    print(f"検索条件: {format_conditions_display(conditions)}")
    print(f"最大件数: {max_items}")
    print("=" * 70)
    
    try:
        # 商品検索
        products = scraper.search_products(
            keyword=keyword,
            conditions=conditions,
            max_items=max_items
        )
        
        if products:
            print(f"\n✅ {len(products)}件の商品を取得しました")
            
            # 結果表示
            print("\n【取得した商品（上位5件）】")
            for i, product in enumerate(products[:5], 1):
                print(f"\n{i}. {product.get('title', '不明')[:50]}")
                print(f"   価格: ¥{product.get('price', 0):,}")
                if product.get('is_sold'):
                    print(f"   状態: 売り切れ")
            
            # 保存
            save_input = input("\n💾 CSVに保存しますか？ (Y/n): ").strip().lower()
            if save_input != 'n':
                save_results(products, conditions, keyword)
        else:
            print("\n❌ 商品が見つかりませんでした")
            print("条件を変更して再度お試しください")
    
    except Exception as e:
        logger.error(f"エラー: {str(e)}")
        print(f"\n❌ エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 中断されました")
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
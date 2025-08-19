"""
ユーティリティ関数モジュール
"""
import re
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import requests
from pathlib import Path

def clean_text(text: str) -> str:
    """テキストのクリーニング"""
    if not text:
        return ""
    
    # HTMLタグの除去
    text = re.sub(r'<[^>]+>', '', text)
    
    # 余分な空白の除去
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 特殊文字の正規化
    text = text.replace('\u3000', ' ')  # 全角スペース
    text = text.replace('\xa0', ' ')    # non-breaking space
    
    return text

def extract_numbers(text: str) -> List[int]:
    """テキストから数字を抽出"""
    if not text:
        return []
    
    # カンマ区切りの数字も対応
    numbers = re.findall(r'[0-9,]+', text)
    result = []
    
    for num_str in numbers:
        try:
            # カンマを除去して整数に変換
            num = int(num_str.replace(',', ''))
            result.append(num)
        except ValueError:
            continue
    
    return result

def extract_price(text: str) -> Optional[int]:
    """価格文字列から金額を抽出"""
    if not text:
        return None
    
    # 「￥1,000」「1000円」「1,000」等のパターンに対応
    patterns = [
        r'[￥¥]?\s*([0-9,]+)\s*円?',
        r'([0-9,]+)\s*[￥¥円]',
        r'([0-9,]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                price = int(match.group(1).replace(',', ''))
                # 妥当な価格範囲チェック（10円〜1,000,000円）
                if 10 <= price <= 1000000:
                    return price
            except ValueError:
                continue
    
    return None

def calculate_profit(selling_price: int, cost_price: int, 
                    shipping_cost: int = 300, mercari_fee_rate: float = 0.10) -> Dict[str, Any]:
    """利益計算"""
    # メルカリ手数料
    mercari_fee = int(selling_price * mercari_fee_rate)
    
    # 総コスト
    total_cost = cost_price + shipping_cost + mercari_fee
    
    # 利益
    profit = selling_price - total_cost
    
    # 利益率
    profit_rate = profit / selling_price if selling_price > 0 else 0
    
    # ROI（投資収益率）
    roi = profit / cost_price if cost_price > 0 else 0
    
    return {
        'selling_price': selling_price,
        'cost_price': cost_price,
        'shipping_cost': shipping_cost,
        'mercari_fee': mercari_fee,
        'total_cost': total_cost,
        'profit': profit,
        'profit_rate': profit_rate,
        'roi': roi
    }

def generate_product_id(title: str, price: int, seller: str = "") -> str:
    """商品IDの生成"""
    # タイトル、価格、販売者を組み合わせてハッシュ化
    content = f"{title}_{price}_{seller}_{datetime.now().strftime('%Y%m%d')}"
    return hashlib.md5(content.encode()).hexdigest()[:16]

def validate_url(url: str) -> bool:
    """URL形式の検証"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def safe_request(url: str, headers: Dict[str, str] = None, 
                timeout: int = 30, max_retries: int = 3) -> Optional[requests.Response]:
    """安全なHTTPリクエスト"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                # 指数バックオフで待機
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            else:
                return None
    
    return None

def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """ランダムな遅延"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def format_currency(amount: int, currency: str = "JPY") -> str:
    """通貨フォーマット"""
    if currency == "JPY":
        return f"¥{amount:,}"
    elif currency == "CNY":
        return f"¥{amount:.2f}"
    else:
        return f"{amount:,}"

def get_file_age(filepath: Path) -> int:
    """ファイルの経過日数を取得"""
    if not filepath.exists():
        return float('inf')
    
    file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
    age = datetime.now() - file_time
    return age.days

def ensure_directory(path: Path):
    """ディレクトリの存在確認と作成"""
    path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """ファイル名の無害化"""
    # 使用できない文字を置換
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 長すぎるファイル名を短縮
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def convert_cny_to_jpy(cny_price: float, exchange_rate: float = 21.0) -> int:
    """人民元から日本円への変換"""
    jpy_price = cny_price * exchange_rate
    return int(jpy_price)

def is_business_hours(start_hour: int = 9, end_hour: int = 23) -> bool:
    """営業時間内かどうかの判定"""
    current_hour = datetime.now().hour
    return start_hour <= current_hour < end_hour

def get_next_business_day() -> datetime:
    """次の営業日を取得"""
    tomorrow = datetime.now() + timedelta(days=1)
    
    # 土曜日(5)、日曜日(6)をスキップ
    while tomorrow.weekday() >= 5:
        tomorrow += timedelta(days=1)
    
    return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """リストを指定サイズのチャンクに分割"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def calculate_similarity(text1: str, text2: str) -> float:
    """テキスト類似度の計算（簡易版）"""
    if not text1 or not text2:
        return 0.0
    
    # 文字レベルの類似度
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    # 共通文字数を計算
    common_chars = set(text1_lower) & set(text2_lower)
    total_chars = set(text1_lower) | set(text2_lower)
    
    if not total_chars:
        return 0.0
    
    return len(common_chars) / len(total_chars)

def extract_keywords_from_title(title: str, max_keywords: int = 5) -> List[str]:
    """タイトルからキーワードを抽出"""
    if not title:
        return []
    
    # ストップワード（除外する単語）
    stop_words = {
        '新品', '未使用', '中古', '美品', '送料無料', '即日発送', 
        '限定', 'セット', 'まとめ', 'お得', '格安', '激安',
        'の', 'に', 'は', 'が', 'を', 'で', 'と', 'から'
    }
    
    # 単語分割（簡易版）
    words = re.findall(r'[一-龯ァ-ヶa-zA-Z0-9]+', title)
    
    # ストップワードを除外し、長さでフィルタリング
    keywords = []
    for word in words:
        if (word not in stop_words and 
            len(word) >= 2 and 
            len(word) <= 20 and
            len(keywords) < max_keywords):
            keywords.append(word)
    
    return keywords

def validate_product_data(product_data: Dict[str, Any]) -> List[str]:
    """商品データの検証"""
    errors = []
    
    # 必須フィールドの確認
    required_fields = ['title', 'price']
    for field in required_fields:
        if not product_data.get(field):
            errors.append(f"必須フィールドが不足: {field}")
    
    # 価格の妥当性チェック
    price = product_data.get('price')
    if price is not None:
        if not isinstance(price, (int, float)) or price <= 0:
            errors.append("価格が無効です")
        elif price > 1000000:
            errors.append("価格が高すぎます")
    
    # タイトルの長さチェック
    title = product_data.get('title')
    if title and len(title) > 100:
        errors.append("タイトルが長すぎます")
    
    return errors
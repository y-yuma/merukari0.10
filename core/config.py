"""
設定管理モジュール
"""
import os
import configparser
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

class Config:
    """設定管理クラス"""
    
    def __init__(self, config_file='config.ini'):
        """初期化"""
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # 環境変数の読み込み
        load_dotenv()
        
        # 設定ファイルの読み込み
        self._load_config()
        
        # 暗号化キーの設定
        self._setup_encryption()
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        if not os.path.exists(self.config_file):
            self._create_default_config()
        
        self.config.read(self.config_file, encoding='utf-8')
    
    def _create_default_config(self):
        """デフォルト設定ファイルの作成"""
        default_config = """
[system]
# システム全般設定
request_interval = 2.0
max_retry_count = 3
timeout_seconds = 30
working_hours_start = 09:00
working_hours_end = 23:00
headless = false
proxy = 
user_agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

[mercari]
# メルカリ設定
email = MERCARI_EMAIL_ENCRYPTED
password = MERCARI_PASSWORD_ENCRYPTED
search_interval = 3.0
max_products_per_search = 50
max_pages = 5
image_quality_threshold = 0.7
search_sold_only = true
search_condition = new
min_price = 
max_price = 

[alibaba]
# アリババ設定
search_interval = 2.5
exchange_rate = 21.0
min_order_quantity = 1
max_order_quantity = 50

[business]
# ビジネス設定
min_profit_rate = 0.30
max_investment = 50000
initial_order_quantity = 3
shipping_cost = 300
mercari_fee_rate = 0.10

[listing]
# 出品設定
auto_listing = true
interval_minutes = 30
max_listings_per_day = 10
default_shipping_method = らくらくメルカリ便

[database]
# データベース設定
backup_interval_days = 7
max_backup_files = 30

[logging]
# ログ設定
level = INFO
max_file_size_mb = 10
backup_count = 5

[debug]
# デバッグ設定
verbose_errors = false
save_screenshots = true
save_page_source = false
"""
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(default_config.strip())
        
        # 設定を再読み込み
        self.config.read(self.config_file, encoding='utf-8')
    
    def _setup_encryption(self):
        """暗号化キーの設定"""
        key_file = '.encryption_key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            # 新しいキーを生成
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
        
        self.cipher = Fernet(key)
    
    def get(self, section, option, fallback=None):
        """設定値の取得"""
        try:
            value = self.config.get(section, option)
            # 暗号化された値の場合は復号化
            if value.endswith('_ENCRYPTED'):
                return self.get_encrypted(section, option)
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_int(self, section, option, fallback=0):
        """整数値の取得"""
        try:
            return self.config.getint(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_float(self, section, option, fallback=0.0):
        """浮動小数点値の取得"""
        try:
            return self.config.getfloat(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_boolean(self, section, option, fallback=False):
        """真偽値の取得"""
        try:
            return self.config.getboolean(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def set(self, section, option, value):
        """設定値の設定"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, option, str(value))
    
    def get_encrypted(self, section, option):
        """暗号化された値の取得"""
        encrypted_value = self.config.get(section, option)
        
        # 環境変数から実際の暗号化された値を取得
        actual_value = os.getenv(f"{section.upper()}_{option.upper()}")
        
        if actual_value:
            return self.cipher.decrypt(actual_value.encode()).decode()
        
        return encrypted_value
    
    def set_encrypted(self, section, option, value):
        """値の暗号化と保存"""
        encrypted_value = self.cipher.encrypt(value.encode())
        
        # 環境変数に保存
        os.environ[f"{section.upper()}_{option.upper()}"] = encrypted_value.decode()
        
        # 設定ファイルにはプレースホルダーを保存
        self.config.set(section, option, f"{option.upper()}_ENCRYPTED")
        self.save()
    
    def save(self):
        """設定の保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
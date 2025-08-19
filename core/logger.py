"""
ログ機能モジュール
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

def setup_logger(name, log_dir='logs'):
    """ロガーのセットアップ"""
    # ログディレクトリの作成
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # ロガーの作成
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # ハンドラーが既に設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    # フォーマッターの設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（通常ログ）
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / 'app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # エラーログ専用ハンドラー
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / 'error.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # 日別ログハンドラー
    daily_handler = logging.handlers.TimedRotatingFileHandler(
        log_path / f'daily_{datetime.now().strftime("%Y%m%d")}.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    daily_handler.setLevel(logging.DEBUG)
    daily_handler.setFormatter(formatter)
    logger.addHandler(daily_handler)
    
    return logger

class PerformanceLogger:
    """パフォーマンス測定用ロガー"""
    
    def __init__(self, logger_name):
        """初期化"""
        self.logger = setup_logger(f"{logger_name}.performance")
        self.start_times = {}
    
    def start_timer(self, operation_name):
        """タイマー開始"""
        self.start_times[operation_name] = datetime.now()
        self.logger.debug(f"開始: {operation_name}")
    
    def end_timer(self, operation_name):
        """タイマー終了"""
        if operation_name in self.start_times:
            start_time = self.start_times[operation_name]
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"完了: {operation_name} - 実行時間: {duration:.2f}秒")
            del self.start_times[operation_name]
            
            return duration
        else:
            self.logger.warning(f"タイマーが開始されていません: {operation_name}")
            return None
    
    def log_memory_usage(self):
        """メモリ使用量のログ"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            self.logger.info(f"メモリ使用量: {memory_mb:.2f}MB")
            return memory_mb
        except ImportError:
            self.logger.warning("psutilがインストールされていません")
            return None

def get_file_logger(name, filename, level=logging.INFO):
    """特定ファイル用のロガーを取得"""
    logger = logging.getLogger(name)
    
    # 既にハンドラーが設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # ログディレクトリの作成
    log_path = Path('logs')
    log_path.mkdir(exist_ok=True)
    
    # ファイルハンドラー
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / filename,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
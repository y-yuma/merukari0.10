"""
エラーハンドリング強化モジュール
"""
import time
import random
import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException, ElementClickInterceptedException
)

from core.logger import setup_logger

class ErrorSeverity(Enum):
    """エラーの重要度"""
    LOW = "low"           # 軽微なエラー（再試行で解決可能）
    MEDIUM = "medium"     # 中程度のエラー（対策が必要）
    HIGH = "high"         # 重大なエラー（処理停止が必要）
    CRITICAL = "critical" # 致命的エラー（システム停止）

class RetryConfig:
    """リトライ設定"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_multiplier: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier

class MercariErrorHandler:
    """メルカリRPA専用エラーハンドラー"""
    
    def __init__(self, config):
        """初期化"""
        self.config = config
        self.logger = setup_logger(__name__)
        
        # エラー統計
        self.error_stats = {}
        
        # エラー分類
        self._setup_error_classification()
        
        # リカバリー戦略
        self._setup_recovery_strategies()
    
    def _setup_error_classification(self):
        """エラーの分類設定"""
        self.error_classification = {
            # 軽微なエラー（再試行で解決可能）
            ErrorSeverity.LOW: {
                TimeoutException: "ページ読み込みタイムアウト",
                StaleElementReferenceException: "要素の参照が無効",
                ElementNotInteractableException: "要素との相互作用不可",
                ElementClickInterceptedException: "クリックが妨害された"
            },
            
            # 中程度のエラー（対策が必要）
            ErrorSeverity.MEDIUM: {
                NoSuchElementException: "要素が見つからない",
                WebDriverException: "WebDriverエラー"
            },
            
            # 重大なエラー（処理停止が必要）
            ErrorSeverity.HIGH: {
                ConnectionError: "ネットワーク接続エラー",
                MemoryError: "メモリ不足",
            },
            
            # 致命的エラー（システム停止）
            ErrorSeverity.CRITICAL: {
                SystemError: "システムエラー",
                KeyboardInterrupt: "ユーザー中断"
            }
        }
    
    def _setup_recovery_strategies(self):
        """リカバリー戦略の設定"""
        self.recovery_strategies = {
            TimeoutException: self._handle_timeout_error,
            NoSuchElementException: self._handle_element_not_found,
            StaleElementReferenceException: self._handle_stale_element,
            ElementNotInteractableException: self._handle_element_not_interactable,
            ElementClickInterceptedException: self._handle_click_intercepted,
            WebDriverException: self._handle_webdriver_error
        }
    
    def classify_error(self, error: Exception) -> ErrorSeverity:
        """エラーの分類"""
        error_type = type(error)
        
        for severity, error_types in self.error_classification.items():
            if error_type in error_types:
                return severity
        
        # 未分類のエラーは中程度として扱う
        return ErrorSeverity.MEDIUM
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """エラーハンドリングのメイン処理"""
        error_type = type(error)
        severity = self.classify_error(error)
        
        # エラー統計の更新
        self._update_error_stats(error_type)
        
        # ログ出力
        self._log_error(error, severity, context)
        
        # リカバリー戦略の実行
        recovery_result = self._execute_recovery_strategy(error, context)
        
        return {
            'error_type': error_type.__name__,
            'severity': severity.value,
            'message': str(error),
            'context': context,
            'recovery_attempted': recovery_result.get('attempted', False),
            'recovery_successful': recovery_result.get('successful', False),
            'retry_recommended': recovery_result.get('retry_recommended', False),
            'wait_time': recovery_result.get('wait_time', 0)
        }
    
    def _update_error_stats(self, error_type: type):
        """エラー統計の更新"""
        error_name = error_type.__name__
        if error_name not in self.error_stats:
            self.error_stats[error_name] = 0
        self.error_stats[error_name] += 1
    
    def _log_error(self, error: Exception, severity: ErrorSeverity, context: Dict[str, Any]):
        """エラーログの出力"""
        error_msg = f"エラー発生: {type(error).__name__}: {str(error)}"
        
        if severity == ErrorSeverity.LOW:
            self.logger.info(error_msg)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error_msg)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(error_msg)
        else:  # CRITICAL
            self.logger.critical(error_msg)
        
        # コンテキスト情報の出力
        if context:
            self.logger.debug(f"エラーコンテキスト: {context}")
        
        # デバッグモードの場合はトレースバックも出力
        if self.config.get_boolean('debug', 'verbose_errors', False):
            self.logger.debug(traceback.format_exc())
    
    def _execute_recovery_strategy(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """リカバリー戦略の実行"""
        error_type = type(error)
        
        if error_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[error_type](error, context)
            except Exception as recovery_error:
                self.logger.error(f"リカバリー戦略実行エラー: {recovery_error}")
                return {'attempted': True, 'successful': False, 'retry_recommended': False}
        
        # デフォルトリカバリー
        return self._default_recovery_strategy(error, context)
    
    def _handle_timeout_error(self, error: TimeoutException, context: Dict[str, Any]) -> Dict[str, Any]:
        """タイムアウトエラーの処理"""
        self.logger.info("タイムアウトエラーのリカバリーを実行中...")
        
        driver = context.get('driver')
        if driver:
            try:
                # ページのリフレッシュ
                driver.refresh()
                time.sleep(random.uniform(3.0, 6.0))
                
                return {
                    'attempted': True,
                    'successful': True,
                    'retry_recommended': True,
                    'wait_time': random.uniform(2.0, 5.0)
                }
            except Exception:
                pass
        
        return {
            'attempted': True,
            'successful': False,
            'retry_recommended': True,
            'wait_time': random.uniform(5.0, 10.0)
        }
    
    def _handle_element_not_found(self, error: NoSuchElementException, context: Dict[str, Any]) -> Dict[str, Any]:
        """要素が見つからないエラーの処理"""
        self.logger.info("要素不在エラーのリカバリーを実行中...")
        
        driver = context.get('driver')
        if driver:
            try:
                # ページを少し待ってから再試行
                time.sleep(random.uniform(2.0, 4.0))
                
                # スクロールして要素を探す
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1.0)
                
                return {
                    'attempted': True,
                    'successful': True,
                    'retry_recommended': True,
                    'wait_time': random.uniform(1.0, 3.0)
                }
            except Exception:
                pass
        
        return {
            'attempted': True,
            'successful': False,
            'retry_recommended': True,
            'wait_time': random.uniform(3.0, 6.0)
        }
    
    def _handle_stale_element(self, error: StaleElementReferenceException, context: Dict[str, Any]) -> Dict[str, Any]:
        """要素参照無効エラーの処理"""
        self.logger.info("要素参照無効エラーのリカバリーを実行中...")
        
        # 要素を再取得する必要がある
        return {
            'attempted': True,
            'successful': True,
            'retry_recommended': True,
            'wait_time': random.uniform(1.0, 2.0)
        }
    
    def _handle_element_not_interactable(self, error: ElementNotInteractableException, context: Dict[str, Any]) -> Dict[str, Any]:
        """要素相互作用不可エラーの処理"""
        self.logger.info("要素相互作用不可エラーのリカバリーを実行中...")
        
        driver = context.get('driver')
        element = context.get('element')
        
        if driver and element:
            try:
                # 要素をビューに移動
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(random.uniform(1.0, 2.0))
                
                # JavaScriptでクリック
                driver.execute_script("arguments[0].click();", element)
                
                return {
                    'attempted': True,
                    'successful': True,
                    'retry_recommended': False,
                    'wait_time': 0
                }
            except Exception:
                pass
        
        return {
            'attempted': True,
            'successful': False,
            'retry_recommended': True,
            'wait_time': random.uniform(2.0, 4.0)
        }
    
    def _handle_click_intercepted(self, error: ElementClickInterceptedException, context: Dict[str, Any]) -> Dict[str, Any]:
        """クリック妨害エラーの処理"""
        self.logger.info("クリック妨害エラーのリカバリーを実行中...")
        
        driver = context.get('driver')
        if driver:
            try:
                # オーバーレイやモーダルを閉じる試行
                overlays = driver.find_elements(By.CSS_SELECTOR, '.modal, .overlay, .popup')
                for overlay in overlays:
                    try:
                        close_btn = overlay.find_element(By.CSS_SELECTOR, '.close, .cancel, [aria-label="close"]')
                        close_btn.click()
                        time.sleep(0.5)
                    except:
                        continue
                
                return {
                    'attempted': True,
                    'successful': True,
                    'retry_recommended': True,
                    'wait_time': random.uniform(1.0, 3.0)
                }
            except Exception:
                pass
        
        return {
            'attempted': True,
            'successful': False,
            'retry_recommended': True,
            'wait_time': random.uniform(2.0, 5.0)
        }
    
    def _handle_webdriver_error(self, error: WebDriverException, context: Dict[str, Any]) -> Dict[str, Any]:
        """WebDriverエラーの処理"""
        self.logger.warning("WebDriverエラーのリカバリーを実行中...")
        
        # WebDriverの再起動が必要な可能性
        return {
            'attempted': True,
            'successful': False,
            'retry_recommended': False,
            'restart_driver_recommended': True,
            'wait_time': random.uniform(5.0, 10.0)
        }
    
    def _default_recovery_strategy(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """デフォルトリカバリー戦略"""
        severity = self.classify_error(error)
        
        if severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]:
            return {
                'attempted': True,
                'successful': False,
                'retry_recommended': True,
                'wait_time': random.uniform(3.0, 8.0)
            }
        else:
            return {
                'attempted': True,
                'successful': False,
                'retry_recommended': False,
                'wait_time': 0
            }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """エラー統計の取得"""
        total_errors = sum(self.error_stats.values())
        return {
            'total_errors': total_errors,
            'error_breakdown': self.error_stats.copy(),
            'most_common_error': max(self.error_stats.items(), key=lambda x: x[1])[0] if self.error_stats else None
        }

def retry_on_error(retry_config: RetryConfig = None, 
                   error_handler: MercariErrorHandler = None):
    """エラー時リトライデコレータ"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            config = retry_config or RetryConfig()
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # 最後の試行の場合は例外を再発生
                    if attempt == config.max_retries:
                        break
                    
                    # エラーハンドラーがある場合は処理
                    if error_handler:
                        context = {
                            'function_name': func.__name__,
                            'attempt': attempt + 1,
                            'max_attempts': config.max_retries + 1,
                            'args': args,
                            'kwargs': kwargs
                        }
                        
                        result = error_handler.handle_error(e, context)
                        
                        # リトライが推奨されない場合は即座に終了
                        if not result.get('retry_recommended', True):
                            break
                        
                        # 待機時間の取得
                        wait_time = result.get('wait_time', 0)
                    else:
                        # 指数バックオフで待機時間を計算
                        wait_time = min(
                            config.base_delay * (config.backoff_multiplier ** attempt),
                            config.max_delay
                        )
                    
                    # ランダム性を追加
                    actual_wait_time = wait_time * random.uniform(0.8, 1.2)
                    time.sleep(actual_wait_time)
            
            # 全ての再試行が失敗した場合は最後の例外を再発生
            raise last_exception
        
        return wrapper
    return decorator
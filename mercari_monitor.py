#!/usr/bin/env python3
"""
メルカリ商品監視システム - メインスクリプト
__NEXT_DATA__方式で安定動作
"""
import yaml
import time
import sys
from pathlib import Path
from datetime import datetime
import sqlite3

# プロジェクトルート追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.next_scraper import NextDataScraper
from modules.image_filter import ImageFilter

class MercariMonitor:
    """メルカリ監視システム"""
    
    def __init__(self, config_path="config.yaml"):
        """初期化"""
        # 設定読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # モジュール初期化
        self.scraper = NextDataScraper(
            db_path=self.config['storage']['database']
        )
        
        self.image_filter = ImageFilter(
            config=self.config['image_filter']
        ) if self.config['image_filter']['enabled'] else None
        
        # 結果保存ディレクトリ
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        print("=" * 60)
        print("🚀 メルカリ監視システム起動")
        print("=" * 60)
        self._print_config()
    
    def _print_config(self):
        """設定内容を表示"""
        search = self.config['search']
        print(f"📍 監視キーワード: {', '.join(search['keywords'])}")
        print(f"💰 価格帯: ¥{search['conditions']['price_min']:,} ~ ¥{search['conditions']['price_max']:,}")
        print(f"📦 状態: {'新品' if search['conditions']['item_condition'] == 1 else '中古可'}")
        print(f"🚚 送料: {'込み' if search['conditions']['shipping_payer'] else '指定なし'}")
        print(f"⏱️  間隔: {self.config['monitor']['interval']}秒")
        print(f"🖼️  画像フィルター: {'ON' if self.config['image_filter']['enabled'] else 'OFF'}")
        print("=" * 60)
    
    def start(self):
        """監視開始"""
        interval = self.config['monitor']['interval']
        keywords = self.config['search']['keywords']
        conditions = self.config['search']['conditions']
        
        print(f"\n📡 監視を開始します（Ctrl+C で終了）\n")
        
        check_count = 0
        total_found = 0
        
        while True:
            try:
                check_count += 1
                print(f"\n--- チェック #{check_count} ({datetime.now().strftime('%H:%M:%S')}) ---")
                
                all_items = []
                
                # 各キーワードで検索
                for keyword in keywords:
                    print(f"🔍 検索: {keyword}")
                    
                    items = self.scraper.fetch_items(
                        keyword=keyword,
                        conditions=conditions,
                        max_items=self.config['monitor']['max_items_per_check']
                    )
                    
                    if items:
                        print(f"  → {len(items)}件の新商品")
                        
                        # 画像フィルター適用
                        if self.image_filter:
                            filtered = self.image_filter.filter_items(items)
                            print(f"  → 画像フィルター後: {len(filtered)}件")
                            items = filtered
                        
                        # NGワードチェック
                        items = self._filter_ng_words(items)
                        
                        all_items.extend(items)
                
                # 結果処理
                if all_items:
                    total_found += len(all_items)
                    print(f"\n🎯 合計 {len(all_items)}件の商品が条件に一致")
                    
                    # 通知
                    self._notify(all_items)
                    
                    # 保存
                    self._save_results(all_items)
                    
                    # 上位表示
                    self._display_items(all_items[:5])
                else:
                    print("  新着商品なし")
                
                # 統計表示
                print(f"\n📊 統計: チェック{check_count}回 / 累計{total_found}件発見")
                
                # 次回まで待機
                print(f"💤 {interval}秒後に次回チェック...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\n👋 監視を終了します")
                self._show_summary(check_count, total_found)
                break
            except Exception as e:
                print(f"\n❌ エラー: {str(e)}")
                print(f"🔄 {interval}秒後にリトライ...")
                time.sleep(interval)
    
    def _filter_ng_words(self, items):
        """NGワードフィルタリング"""
        ng_words = self.config['image_filter'].get('ng_words', [])
        ok_words = self.config['image_filter'].get('ok_words', [])
        
        filtered = []
        for item in items:
            title = item.get('title', '').lower()
            
            # NGワードチェック
            has_ng = any(ng.lower() in title for ng in ng_words)
            if has_ng:
                continue
            
            # OKワード優先
            has_ok = any(ok.lower() in title for ok in ok_words)
            if has_ok:
                item['priority'] = True
            
            filtered.append(item)
        
        return filtered
    
    def _notify(self, items):
        """通知処理"""
        if not self.config['monitor']['notification']['enabled']:
            return
        
        # ローカル通知
        if self.config['monitor']['notification']['local']['enabled']:
            self._local_notify(items)
        
        # LINE通知
        if self.config['monitor']['notification']['line']['enabled']:
            self._line_notify(items)
        
        # Discord通知
        if self.config['monitor']['notification']['discord']['enabled']:
            self._discord_notify(items)
    
    def _local_notify(self, items):
        """ローカル通知（デスクトップ）"""
        try:
            import platform
            
            title = f"🎯 {len(items)}件の新商品"
            message = items[0]['title'][:50] if items else ""
            
            if platform.system() == 'Darwin':  # macOS
                import subprocess
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script])
            elif platform.system() == 'Windows':
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            else:  # Linux
                import subprocess
                subprocess.run(['notify-send', title, message])
            
            # 音を鳴らす
            if self.config['monitor']['notification']['local']['sound']:
                print('\a')  # ビープ音
                
        except Exception as e:
            print(f"通知エラー: {str(e)}")
    
    def _line_notify(self, items):
        """LINE Notify通知"""
        try:
            import requests
            
            token = self.config['monitor']['notification']['line']['token']
            if token == "YOUR_LINE_NOTIFY_TOKEN":
                return
            
            message = f"\n🎯 {len(items)}件の新商品\n\n"
            for item in items[:3]:
                message += f"▫️ {item['title'][:30]}\n"
                message += f"  ¥{item['price']:,}\n"
                message += f"  {item['url']}\n\n"
            
            headers = {'Authorization': f'Bearer {token}'}
            data = {'message': message}
            
            requests.post(
                'https://notify-api.line.me/api/notify',
                headers=headers,
                data=data
            )
        except:
            pass
    
    def _discord_notify(self, items):
        """Discord Webhook通知"""
        try:
            import requests
            
            webhook_url = self.config['monitor']['notification']['discord']['webhook_url']
            if webhook_url == "YOUR_DISCORD_WEBHOOK_URL":
                return
            
            embeds = []
            for item in items[:3]:
                embeds.append({
                    "title": item['title'][:100],
                    "url": item['url'],
                    "fields": [
                        {"name": "価格", "value": f"¥{item['price']:,}", "inline": True},
                        {"name": "状態", "value": "販売中", "inline": True}
                    ],
                    "thumbnail": {"url": item.get('thumb_url', '')}
                })
            
            requests.post(webhook_url, json={"embeds": embeds})
        except:
            pass
    
    def _display_items(self, items):
        """商品表示"""
        if not items:
            return
        
        print("\n【発見した商品】")
        for i, item in enumerate(items, 1):
            priority = "⭐ " if item.get('priority') else ""
            print(f"\n{priority}{i}. {item['title']}")
            print(f"   💰 ¥{item['price']:,}")
            print(f"   🔗 {item['url']}")
    
    def _save_results(self, items):
        """結果保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # CSV保存
        if self.config['storage']['csv_export']:
            import csv
            csv_path = self.results_dir / f"items_{timestamp}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                if items:
                    writer = csv.DictWriter(f, fieldnames=items[0].keys())
                    writer.writeheader()
                    writer.writerows(items)
        
        # JSON保存
        if self.config['storage']['json_export']:
            import json
            json_path = self.results_dir / f"items_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
    
    def _show_summary(self, check_count, total_found):
        """終了時のサマリー表示"""
        print("\n" + "=" * 60)
        print("📊 監視サマリー")
        print("=" * 60)
        print(f"総チェック回数: {check_count}回")
        print(f"発見商品数: {total_found}件")
        if check_count > 0:
            print(f"平均発見数: {total_found/check_count:.1f}件/回")
        print("=" * 60)


if __name__ == "__main__":
    # 設定ファイル確認
    if not Path("config.yaml").exists():
        print("❌ config.yaml が見つかりません")
        print("上記のconfig.yamlを作成してください")
        sys.exit(1)
    
    # 監視開始
    monitor = MercariMonitor()
    monitor.start()
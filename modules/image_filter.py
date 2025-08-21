#!/usr/bin/env python3
"""
画像フィルターモジュール
プロ画像とアマチュア画像を判定
"""
import requests
import io
from PIL import Image
import imagehash
from typing import List, Dict
import numpy as np

class ImageFilter:
    """画像フィルタークラス"""
    
    def __init__(self, config: Dict):
        """初期化"""
        self.config = config
        self.seen_hashes = set()  # 既に見た画像のハッシュ
        
    def filter_items(self, items: List[Dict]) -> List[Dict]:
        """
        商品リストをフィルタリング
        
        Args:
            items: 商品リスト
            
        Returns:
            フィルタ後の商品リスト
        """
        filtered = []
        
        for item in items:
            if self._is_professional_item(item):
                filtered.append(item)
        
        return filtered
    
    def _is_professional_item(self, item: Dict) -> bool:
        """
        プロ商品かどうか判定
        
        Args:
            item: 商品情報
            
        Returns:
            プロ商品ならTrue
        """
        thumb_url = item.get('thumb_url', '')
        if not thumb_url:
            return False
        
        try:
            # 画像ダウンロード
            img = self._download_image(thumb_url)
            if not img:
                return False
            
            # 重複チェック（ハッシュ）
            if self._is_duplicate(img):
                return False
            
            # プロ画像判定
            score = 0
            max_score = 0
            
            # 1. 背景チェック
            if self.config['professional_features']['white_background']:
                if self._has_white_background(img):
                    score += 2
                max_score += 2
            
            # 2. 解像度チェック
            min_res = self.config['professional_features']['min_resolution']
            width, height = img.size
            if min(width, height) >= min_res:
                score += 1
            max_score += 1
            
            # 3. 画像の明るさ・コントラスト
            if self._has_good_lighting(img):
                score += 1
            max_score += 1
            
            # 4. 画像の鮮明さ
            if self._is_sharp_image(img):
                score += 1
            max_score += 1
            
            # スコア計算（60%以上でプロ判定）
            if max_score > 0:
                ratio = score / max_score
                return ratio >= 0.6
            
            return False
            
        except Exception as e:
            print(f"画像判定エラー: {str(e)}")
            return False
    
    def _download_image(self, url: str) -> Image.Image:
        """画像ダウンロード"""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            return img.convert('RGB')
        except:
            return None
    
    def _is_duplicate(self, img: Image.Image) -> bool:
        """重複チェック"""
        # perceptual hash を計算
        hash_val = str(imagehash.phash(img))
        
        # 既存のハッシュと比較
        for seen_hash in self.seen_hashes:
            # ハミング距離が4以下なら類似画像
            if self._hamming_distance(hash_val, seen_hash) <= 4:
                return True
        
        # 新規画像として記録
        self.seen_hashes.add(hash_val)
        return False
    
    def _hamming_distance(self, s1: str, s2: str) -> int:
        """ハミング距離計算"""
        return sum(c1 != c2 for c1, c2 in zip(s1, s2))
    
    def _has_white_background(self, img: Image.Image) -> bool:
        """白背景チェック"""
        # 画像の端をサンプリング
        width, height = img.size
        edge_pixels = []
        
        # 上端
        for x in range(0, width, 10):
            edge_pixels.append(img.getpixel((x, 0)))
        # 下端
        for x in range(0, width, 10):
            edge_pixels.append(img.getpixel((x, height-1)))
        # 左端
        for y in range(0, height, 10):
            edge_pixels.append(img.getpixel((0, y)))
        # 右端
        for y in range(0, height, 10):
            edge_pixels.append(img.getpixel((width-1, y)))
        
        # 白色度を計算（RGB値が高いほど白い）
        white_count = 0
        for pixel in edge_pixels:
            if all(c > 240 for c in pixel):  # RGB全て240以上なら白
                white_count += 1
        
        # 80%以上が白なら白背景
        return white_count / len(edge_pixels) > 0.8
    
    def _has_good_lighting(self, img: Image.Image) -> bool:
        """良好な照明チェック"""
        # 画像を numpy 配列に変換
        img_array = np.array(img)
        
        # 明度計算
        brightness = np.mean(img_array)
        
        # コントラスト計算
        contrast = np.std(img_array)
        
        # 明度が適切（100-200）かつコントラストがある（30以上）
        return 100 < brightness < 200 and contrast > 30
    
    def _is_sharp_image(self, img: Image.Image) -> bool:
        """画像の鮮明さチェック（ラプラシアンフィルタ）"""
        # グレースケール変換
        gray = img.convert('L')
        gray_array = np.array(gray)
        
        # ラプラシアンフィルタ（エッジ検出）
        from scipy import ndimage
        laplacian = ndimage.laplace(gray_array)
        
        # 分散が高いほど鮮明
        variance = np.var(laplacian)
        
        # しきい値（経験的に100以上なら鮮明）
        return variance > 100
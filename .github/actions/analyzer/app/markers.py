"""
dependahuntマーカーの埋め込み・抽出を管理するモジュール

使用例:
    >>> from markers import ANALYZED, TARGET_PACKAGE, ANALYZED_PACKAGE
    >>> text = ANALYZED.create()
    >>> has_marker = TARGET_PACKAGE.exists_in(pr_body)
    >>> data = ANALYZED_PACKAGE.extract(comment)
"""

import json
import re
from typing import Dict, Any, Optional, List
from enum import Enum


class _MarkerType(str, Enum):
    """マーカーの種類（内部使用）"""
    ANALYZED = "analyzed"  # PR分析済みマーカー
    TARGET_PACKAGE = "target-package"  # 対象パッケージ情報マーカー
    ANALYZED_PACKAGE = "analyzed-package"  # 分析済みパッケージ情報マーカー


class _Marker:
    """個別のマーカーを管理するクラス（内部実装）

    このクラスは直接使用せず、モジュールレベルで公開されている
    インスタンス（ANALYZED, TARGET_PACKAGE, ANALYZED_PACKAGE）を使用してください。
    """

    # マーカーのプレフィックス
    MARKER_PREFIX = "dependahunt"

    def __init__(self, marker_type: _MarkerType):
        """初期化

        Args:
            marker_type: マーカーの種類
        """
        self.marker_type = marker_type
        self.tag = f"{self.MARKER_PREFIX}:{marker_type.value}"

    def _build_pattern(self, with_data: bool = False) -> str:
        """マーカー検出用の正規表現パターンを生成

        Args:
            with_data: データを含むマーカーの場合True

        Returns:
            正規表現パターン文字列
        """
        if with_data:
            return rf'<!--\s+{re.escape(self.tag)}\s+([^\n]+?)\s*-->'
        else:
            return rf'<!--\s+{re.escape(self.tag)}\s+-->'

    def create(self, data: Optional[Dict[str, Any]] = None) -> str:
        """マーカーを生成

        Args:
            data: マーカーに埋め込むデータ（辞書形式）

        Returns:
            HTMLコメント形式のマーカー文字列

        Examples:
            >>> ANALYZED.create()
            '<!-- dependahunt:analyzed -->'

            >>> TARGET_PACKAGE.create({
            ...     'packageName': 'lodash',
            ...     'currentVersion': '4.17.20',
            ...     'newVersion': '4.17.21'
            ... })
            '<!-- dependahunt:target-package {"packageName":"lodash",...} -->'
        """
        if data is None:
            return f"<!-- {self.tag} -->"
        else:
            # JSONに変換（非ASCII文字もそのまま出力）
            json_str = json.dumps(data, ensure_ascii=False)
            return f"<!-- {self.tag} {json_str} -->"

    def exists_in(self, text: str) -> bool:
        """テキスト内にマーカーが存在するかチェック

        Args:
            text: 検索対象のテキスト

        Returns:
            マーカーが見つかった場合True

        Examples:
            >>> pr_body = "PR description <!-- dependahunt:analyzed -->"
            >>> ANALYZED.exists_in(pr_body)
            True
        """
        pattern = self._build_pattern(with_data=False)
        data_pattern = self._build_pattern(with_data=True)

        # データなしマーカーとデータありマーカーの両方をチェック
        return bool(re.search(pattern, text)) or bool(re.search(data_pattern, text))

    def extract(self, text: str) -> Optional[Dict[str, Any]]:
        """マーカーからデータを抽出（最初に見つかった1つ）

        Args:
            text: 検索対象のテキスト

        Returns:
            抽出したデータ（辞書形式）、見つからない場合はNone

        Examples:
            >>> comment = '<!-- dependahunt:analyzed-package {"package":"lodash"} -->'
            >>> ANALYZED_PACKAGE.extract(comment)
            {'package': 'lodash'}
        """
        pattern = self._build_pattern(with_data=True)
        match = re.search(pattern, text)

        if not match:
            return None

        try:
            json_str = match.group(1)
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"⚠️ マーカー '{self.tag}' からのJSONパース失敗: {e}")
            return None

    def extract_all(self, text: str) -> List[Dict[str, Any]]:
        """テキスト内の全てのマーカーからデータを抽出

        Args:
            text: 検索対象のテキスト

        Returns:
            抽出したデータのリスト（見つからない場合は空リスト）

        Examples:
            >>> text = '''
            ... <!-- dependahunt:target-package {"package":"lodash"} -->
            ... <!-- dependahunt:target-package {"package":"axios"} -->
            ... '''
            >>> TARGET_PACKAGE.extract_all(text)
            [{'package': 'lodash'}, {'package': 'axios'}]
        """
        pattern = self._build_pattern(with_data=True)
        matches = re.finditer(pattern, text)

        results = []
        for match in matches:
            try:
                json_str = match.group(1)
                data = json.loads(json_str)
                results.append(data)
            except (json.JSONDecodeError, IndexError) as e:
                print(f"⚠️ マーカー '{self.tag}' からのJSONパース失敗: {e}")
                continue

        return results

    def __repr__(self) -> str:
        """文字列表現"""
        return f"<Marker: {self.tag}>"


# 公開するマーカーインスタンス
ANALYZED = _Marker(_MarkerType.ANALYZED)
TARGET_PACKAGE = _Marker(_MarkerType.TARGET_PACKAGE)
ANALYZED_PACKAGE = _Marker(_MarkerType.ANALYZED_PACKAGE)

"""
バージョン関連のユーティリティ関数
"""

import re
from typing import Dict, List
from packaging.specifiers import SpecifierSet
from packaging.version import Version
import markers


def extract_all_version_info(pr_body: str) -> List[Dict[str, str]]:
    """PR本文から全てのパッケージ名とバージョン情報を抽出

    Args:
        pr_body: PR本文

    Returns:
        [{'package': 'lodash', 'from': '4.17.20', 'to': '4.17.21'}, ...]
        抽出できない場合は空のリスト
    """

    # for renovate - dependahunt:target-package 形式を検索
    package_infos = markers.TARGET_PACKAGE.extract_all(pr_body)
    if package_infos:
        return [{
            'package': package_info.get('packageName', ''),
            'from': package_info.get('currentVersion', ''),
            'to': package_info.get('newVersion', '')
        } for package_info in package_infos]

    # for dependabot - 従来の単一パッケージ形式もチェック
    # パターン1: "Bumps [package](URL) from [version] to [version]" (Markdownリンク形式)
    pattern1 = r'Bumps?\s+\[(@?[a-zA-Z0-9\-_./]+)\]\([^)]+\)\s+from\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)\s+to\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)'
    match = re.search(pattern1, pr_body, re.IGNORECASE)

    if match:
        return [{
            'package': match.group(1),
            'from': match.group(2),
            'to': match.group(3)
        }]

    # パターン2: "Bumps package from [version] to [version]" (プレーンテキスト)
    pattern2 = r'Bumps?\s+(@?[a-zA-Z0-9\-_./]+)\s+from\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)\s+to\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)'
    match = re.search(pattern2, pr_body, re.IGNORECASE)

    if match:
        return [{
            'package': match.group(1),
            'from': match.group(2),
            'to': match.group(3)
        }]

    return []

def compare_versions(v1: str, v2: str) -> int:
    """セマンティックバージョンを比較

    Args:
        v1: バージョン文字列 (例: "4.17.20")
        v2: バージョン文字列 (例: "4.17.21")

    Returns:
        v1 < v2: -1
        v1 == v2: 0
        v1 > v2: 1
    """
    try:
        version1 = Version(v1)
        version2 = Version(v2)

        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0
    except Exception:
        # バージョンのパースに失敗した場合は文字列比較にフォールバック
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0


def version_in_range(version: str, range_str: str) -> bool:
    """バージョンが指定範囲に含まれるか判定

    Args:
        version: バージョン文字列 (例: "4.17.20")
        range_str: 範囲文字列 (例: ">= 4.0.0, < 4.17.21")

    Returns:
        範囲に含まれる場合 True
    """
    try:
        # 範囲条件をパース
        specifiers = SpecifierSet(range_str)
        # 現在のバージョンをパース
        version = Version(version)
        
        # 範囲に含まれるか判定
        return version in specifiers
    except Exception as e:
        print(f"Error parsing versions: {e}")
        return False
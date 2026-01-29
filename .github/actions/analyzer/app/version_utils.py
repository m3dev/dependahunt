"""
バージョン関連のユーティリティ関数
"""

import re
from typing import Dict, Optional, Tuple


def extract_version_info(pr_body: str) -> Optional[Dict[str, str]]:
    """PR本文からパッケージ名とバージョン情報を抽出

    Args:
        pr_body: PR本文

    Returns:
        {'package': 'lodash', 'from': '4.17.20', 'to': '4.17.21'}
        抽出できない場合は None
    """
    # for dependabot
    # パターン1: "Bumps [package](URL) from [version] to [version]" (Markdownリンク形式)
    pattern1 = r'Bumps?\s+\[(@?[a-zA-Z0-9\-_./]+)\]\([^)]+\)\s+from\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)\s+to\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)'
    match = re.search(pattern1, pr_body, re.IGNORECASE)

    if match:
        return {
            'package': match.group(1),
            'from': match.group(2),
            'to': match.group(3)
        }

    # パターン2: "Bumps package from [version] to [version]" (プレーンテキスト)
    pattern2 = r'Bumps?\s+(@?[a-zA-Z0-9\-_./]+)\s+from\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)\s+to\s+([\d]+(?:\.[\d]+)*(?:-[a-zA-Z0-9.]+)?)'
    match = re.search(pattern2, pr_body, re.IGNORECASE)

    if match:
        return {
            'package': match.group(1),
            'from': match.group(2),
            'to': match.group(3)
        }

    # for renovate
    pattern3 = r'<!-- dependahunt\npackageName: (\S+)\ncurrentVersion: (\S+)\nnewVersion: (\S+)'
    match = re.search(pattern3, pr_body)

    if match:
        return {
            'package': match.group(1),
            'from': match.group(2),
            'to': match.group(3)
        }

    return None


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
    def parse_version(v: str) -> Tuple[list, Optional[str]]:
        # プレリリース版対応: 4.17.20-alpha.1
        parts = v.split('-')
        main_version = parts[0]
        prerelease = parts[1] if len(parts) > 1 else None

        # メインバージョンを数値化
        nums = [int(x) for x in main_version.split('.')]

        return (nums, prerelease)

    v1_parts, v1_pre = parse_version(v1)
    v2_parts, v2_pre = parse_version(v2)

    # パディング（長さを揃える）
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts += [0] * (max_len - len(v1_parts))
    v2_parts += [0] * (max_len - len(v2_parts))

    # メインバージョン比較
    for n1, n2 in zip(v1_parts, v2_parts):
        if n1 < n2:
            return -1
        elif n1 > n2:
            return 1

    # プレリリース版の扱い
    if v1_pre is None and v2_pre is None:
        return 0
    elif v1_pre is None:
        return 1  # 正式版 > プレリリース版
    elif v2_pre is None:
        return -1  # プレリリース版 < 正式版
    else:
        # 両方プレリリース版の場合は文字列比較
        if v1_pre < v2_pre:
            return -1
        elif v1_pre > v2_pre:
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
    # カンマで分割して各条件をチェック
    conditions = [c.strip() for c in range_str.split(',')]

    for condition in conditions:
        # ">= 4.0.0" のような条件をパース
        if condition.startswith('>='):
            compare_ver = condition[2:].strip()
            if compare_versions(version, compare_ver) < 0:
                return False
        elif condition.startswith('<='):
            compare_ver = condition[2:].strip()
            if compare_versions(version, compare_ver) > 0:
                return False
        elif condition.startswith('>'):
            compare_ver = condition[1:].strip()
            if compare_versions(version, compare_ver) <= 0:
                return False
        elif condition.startswith('<'):
            compare_ver = condition[1:].strip()
            if compare_versions(version, compare_ver) >= 0:
                return False
        elif condition.startswith('='):
            compare_ver = condition[1:].strip()
            if compare_versions(version, compare_ver) != 0:
                return False

    return True

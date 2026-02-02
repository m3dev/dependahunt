"""
設定と定数の管理
"""

import os

# リスクレベルアイコン
RISK_ICONS = {
    "極低": "🟢",
    "低": "🟢",
    "中": "🟡",
    "高": "🔴",
    "Critical": "🔴"
}

# 重要度の日本語マッピング
SEVERITY_MAP = {
    'CRITICAL': '緊急',
    'HIGH': '高',
    'MEDIUM': '中',
    'LOW': '低',
    'Unknown': '不明'
}


def get_env_int(key: str, default: int) -> int:
    """環境変数からint値を取得"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

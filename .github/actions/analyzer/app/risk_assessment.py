"""
リスク評価・抽出関連の関数
"""

import os
import re
from typing import Dict, Any, List

from config import RISK_ICONS


# リスクレベルの優先順位（数値が大きいほど高リスク）
RISK_PRIORITY = {
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}


def normalize_risk_level(risk_text: str) -> str:
    """リスクテキストを正規化してlow/medium/high/criticalに変換

    Args:
        risk_text: AI分析やextract_risk_from_ai_analysisから返されたリスク評価テキスト

    Returns:
        正規化されたリスクレベル (low/medium/high/critical)
    """
    risk_lower = risk_text.lower()

    if "critical" in risk_lower or "緊急" in risk_lower:
        return "critical"
    elif "高" in risk_text or "high" in risk_lower:
        return "high"
    elif "中" in risk_text or "medium" in risk_lower:
        return "medium"
    elif "低" in risk_text or "low" in risk_lower:
        return "low"

    # デフォルトはmedium（安全側に倒す）
    return "medium"


def get_max_risk_level(risk_levels: List[str]) -> str:
    """複数のリスクレベルから最大値を取得

    Args:
        risk_levels: リスクレベルのリスト（'unknown'を含む可能性あり）

    Returns:
        最大のリスクレベル (low/medium/high/critical/unknown)
    """

    max_priority = 0
    max_level = "unknown"

    for level in risk_levels:
        normalized = normalize_risk_level(level)
        priority = RISK_PRIORITY.get(normalized, 0)
        if priority > max_priority:
            max_priority = priority
            max_level = normalized

    return max_level


def extract_risk_from_ai_analysis(ai_analysis: str, vuln_data: List[Dict[str, Any]], cves: List[str]) -> tuple[str, str]:
    """AI分析結果から結論部分を抽出

    Returns:
        tuple[str, str]: (formatted_text, risk_level)
            - formatted_text: フォーマットされたリスク評価テキスト
            - risk_level: 正規化されたリスクレベル (low/medium/high/critical/unknown)
    """

    debug_mode = os.getenv('DEBUG_MODE') == '1'

    # 構造化ヘッダーの抽出を試みる
    header_match = re.search(
        r'---RISK_ASSESSMENT_START---\s*\n'
        r'RISK_LEVEL:\s*(.+?)\s*\n'
        r'CONFIDENCE:\s*(.+?)\s*\n'
        r'PRIMARY_REASON:\s*(.+?)\s*\n'
        r'---RISK_ASSESSMENT_END---',
        ai_analysis,
        re.DOTALL
    )

    if header_match:
        # 構造化ヘッダーが見つかった場合
        risk_level = header_match.group(1).strip()
        confidence = header_match.group(2).strip()
        reason = header_match.group(3).strip()

        if debug_mode:
            print(f"✅ DEBUG: 構造化ヘッダー検出成功")
            print(f"  RISK_LEVEL: {risk_level}")
            print(f"  CONFIDENCE: {confidence}")
            print(f"  PRIMARY_REASON: {reason}")

        icon = RISK_ICONS.get(risk_level, "🟡")

        # CVE情報を追加
        cve_info = ""
        if cves:
            cve_list = ", ".join(cves)
            max_cvss = 0.0
            for vuln in vuln_data:
                severity_str = vuln.get('severity', '')
                score_match = re.search(r'(\d+\.\d+)', severity_str)
                if score_match:
                    max_cvss = max(max_cvss, float(score_match.group(1)))

            cve_info = f"\n**対象CVE**: {cve_list}\n**最大CVSS**: {max_cvss} (参考値)\n**信頼度**: {confidence}"

        # 推奨アクションを抽出
        action_match = re.search(r"### 推奨対策[^\n]*\n(.*?)(?=\n##|\n---|\Z)", ai_analysis, re.DOTALL)
        actions_text = ""
        if action_match:
            actions_content = action_match.group(1)
            actions_text = f"\n\n### 📋 推奨アクション\n" + actions_content

        formatted_text = f"""### {icon} 総合リスク判定: {risk_level}リスク

**判定根拠**: {reason}{cve_info}{actions_text}

### 💡 重要
この評価は下記の詳細分析に基づく総合判断です。技術的根拠は詳細分析結果をご確認ください。"""

        # risk_levelを正規化して返す
        normalized_risk = normalize_risk_level(risk_level)
        return (formatted_text, normalized_risk)

    # 構造化ヘッダーが見つからない場合のフォールバック
    if debug_mode:
        print("⚠️ DEBUG: 構造化ヘッダーが見つかりません。フォールバック処理に移行します。")

    # AI分析失敗の検出
    if "AI分析失敗" in ai_analysis or "AI分析エラー:" in ai_analysis or "AI分析がタイムアウト" in ai_analysis:
        if debug_mode:
            print("⚠️ DEBUG: AI分析失敗を検出")

        # AI分析が失敗した場合は、分析失敗メッセージをそのまま返す
        error_text = f"""### ❌ リスク評価: 分析失敗

AI分析が正常に完了しませんでした。分析を再実行するか、手動でのレビューを実施してください。

{ai_analysis}"""
        return (error_text, "unknown")  # エラー時は'unknown'

    # AI分析から「総合リスク判定」の部分を抽出
    conclusion_patterns = [
        r"### 総合リスク判定.*?(?=\n### 推奨対策|\n##|\n---|\Z)",
        r"\*\*総合リスクレベル\*\*[:\s]*.*?(?=\n\n|\n\*\*|\n###|\Z)",
        r"\*\*リスクレベル\*\*[:\s]*.*?(?=\n\n|\n\*\*|\n###|\Z)",
    ]

    extracted_conclusion = ""
    for pattern in conclusion_patterns:
        match = re.search(pattern, ai_analysis, re.DOTALL | re.IGNORECASE)
        if match:
            extracted_conclusion = match.group(0).strip()
            if debug_mode:
                print(f"✅ DEBUG: 総合リスク判定を抽出成功（パターン: {pattern[:50]}...）")
                print(f"抽出内容: {extracted_conclusion[:200]}...")
            break

    if not extracted_conclusion and debug_mode:
        print("⚠️ DEBUG: 総合リスク判定セクションを抽出できませんでした")
        print("⚠️ DEBUG: フォールバック処理に移行します")

    # 結論が見つかった場合、そのまま使用
    if extracted_conclusion:
        # アイコンを追加
        detected_risk = "medium"  # デフォルト
        if "低" in extracted_conclusion or "極低" in extracted_conclusion:
            icon = "🟢"
            detected_risk = "low"
        elif "中" in extracted_conclusion:
            icon = "🟡"
            detected_risk = "medium"
        elif "高" in extracted_conclusion:
            icon = "🔴"
            detected_risk = "high"
        elif "critical" in extracted_conclusion.lower() or "緊急" in extracted_conclusion:
            icon = "🔴"
            detected_risk = "critical"

        # 推奨アクションを「推奨対策」から抽出
        action_match = re.search(r"### 推奨対策[^\n]*\n(.*?)(?=\n##|\n---|\Z)", ai_analysis, re.DOTALL)
        actions_text = ""
        if action_match:
            actions_content = action_match.group(1)
            actions_text = f"\n\n### 📋 推奨アクション\n" + actions_content

        # CVE情報を追加
        cve_info = ""
        if cves:
            cve_list = ", ".join(cves)
            max_cvss = 0.0
            for vuln in vuln_data:
                severity_str = vuln.get('severity', '')
                score_match = re.search(r'(\d+\.\d+)', severity_str)
                if score_match:
                    max_cvss = max(max_cvss, float(score_match.group(1)))

            cve_info = f"\n**対象CVE**: {cve_list}\n**最大CVSS**: {max_cvss} (参考値)"

        formatted_text = f"### {icon} 総合リスク判定\n{extracted_conclusion.replace('### 総合リスク判定', '')}{cve_info}{actions_text}"
        return (formatted_text, detected_risk)

    # AI分析全体から重要な判定を抽出（フォールバック）
    if debug_mode:
        print("🔄 DEBUG: フォールバック判定ロジックを実行中...")

    risk_level = "未評価"
    normalized_risk = "unknown"  # デフォルト

    # 低リスク（ゼロリスクも含む）
    if ("**低**" in ai_analysis or "低リスク" in ai_analysis or "ゼロリスク" in ai_analysis or "ほぼゼロ" in ai_analysis or
          "リスクレベル「低」" in ai_analysis or "リスクレベル：低" in ai_analysis or
          "LOW" in ai_analysis):
        risk_level = "低リスク"
        normalized_risk = "low"
        icon = "🟢"
        if debug_mode:
            print("✅ DEBUG: 低リスクを検出")
    # 中リスク
    elif ("**中**" in ai_analysis or "中リスク" in ai_analysis or
          "リスクレベル「中」" in ai_analysis or "リスクレベル：中" in ai_analysis or
          "MEDIUM" in ai_analysis or "CVSS 5." in ai_analysis or "CVSS 6." in ai_analysis):
        risk_level = "中リスク"
        normalized_risk = "medium"
        icon = "🟡"
        if debug_mode:
            print("⚠️ DEBUG: 中リスクを検出")
    # 高リスク
    elif ("**高**" in ai_analysis or "高リスク" in ai_analysis or
          "リスクレベル「高」" in ai_analysis or "リスクレベル：高" in ai_analysis or
          "HIGH" in ai_analysis or "CVSS 7." in ai_analysis):
        risk_level = "高リスク"
        normalized_risk = "high"
        icon = "🔴"
        if debug_mode:
            print("🚨 DEBUG: 高リスクを検出")
    # Critical/緊急レベル
    elif ("Critical" in ai_analysis or "critical" in ai_analysis or
        "🚨 Critical" in ai_analysis or "緊急" in ai_analysis or
        "CVSS 9." in ai_analysis or "CVSS 8." in ai_analysis):
        risk_level = "Critical（緊急）"
        normalized_risk = "critical"
        icon = "🔴"
        if debug_mode:
            print("🔴 DEBUG: Critical（緊急）を検出")
    else:
        icon = "🔴"
        normalized_risk = "unknown"  # リスクレベルを特定できなかった場合は'unknown'
        if debug_mode:
            print("❓ DEBUG: リスクレベルを特定できませんでした")

    # 主な理由を抽出
    reasons = []
    if "本番環境" in ai_analysis and ("影響なし" in ai_analysis or "影響を受けない" in ai_analysis):
        reasons.append("本番環境への直接影響なし")
    if "devDependencies" in ai_analysis:
        reasons.append("開発依存関係のみ")
    if "PHP" in ai_analysis and ("中心" in ai_analysis or "ベース" in ai_analysis):
        reasons.append("PHPベースシステム")

    reason_text = "、".join(reasons) if reasons else "詳細分析による総合判断"

    # CVE情報の付加
    cve_info = ""
    if cves:
        cve_list = ", ".join(cves)
        max_cvss = 0.0
        for vuln in vuln_data:
            severity_str = vuln.get('severity', '')
            score_match = re.search(r'(\d+\.\d+)', severity_str)
            if score_match:
                max_cvss = max(max_cvss, float(score_match.group(1)))

        cve_info = f"\n**対象CVE**: {cve_list}\n**最大CVSS**: {max_cvss} (参考値)"

    # アクションを決定
    if "低" in risk_level:
        actions = ["✅ PR承認・マージ推奨", "📅 通常メンテナンス時に適用", "📊 継続的な依存関係監査"]
    elif "中" in risk_level:
        actions = ["🔍 システム固有影響の確認", "📅 1-2週間以内の適用検討", "📋 使用箇所の詳細確認"]
    else:
        actions = ["⚡ 早急な影響範囲確認", "🔍 攻撃可能性の詳細分析", "👥 セキュリティチームとの連携"]

    formatted_text = f"""### {icon} 総合リスク判定: {risk_level}

**判定根拠**: {reason_text}{cve_info}

### 📋 推奨アクション
{chr(10).join([f"{i+1}. {action}" for i, action in enumerate(actions)])}

### 💡 重要
この評価は下記の詳細分析に基づく総合判断です。技術的根拠は詳細分析結果をご確認ください。"""

    return (formatted_text, normalized_risk)

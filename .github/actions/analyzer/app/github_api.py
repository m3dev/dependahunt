"""
GitHub API関連の関数
"""

import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple

from version_utils import version_in_range, compare_versions
from config import CVE_INFO_MARKER


def get_pr_details(repo: str, pr_number: int, github_token: str) -> Dict[str, Any]:
    """GitHub APIからPR詳細を取得"""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {github_token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def extract_cve_numbers(pr_body: str) -> List[str]:
    """PR本文からCVE番号を抽出"""
    cve_pattern = r'CVE-\d{4}-\d+'
    cves = re.findall(cve_pattern, pr_body, re.IGNORECASE)
    return list(set(cves))  # 重複を除去


def find_cves_by_package_and_version(
    repo: str,
    package_name: str,
    from_version: str,
    to_version: str,
    github_token: str
) -> List[Tuple[str, int, str]]:
    """パッケージ名とバージョンからこのPRで修正されるCVE番号を取得

    Args:
        repo: リポジトリ名（owner/repo形式）
        package_name: パッケージ名 (例: "lodash")
        from_version: 現在のバージョン (例: "4.17.20")
        to_version: 修正先のバージョン (例: "4.17.21")
        github_token: GitHub トークン

    Returns:
        このPRで修正されるCVE情報のリスト [(cve_id, alert_number, alert_url), ...]
    """
    try:
        print(f"🔍 パッケージ '{package_name}' (v{from_version} → v{to_version}) のCVE番号を検索中...")
        print(f"   リポジトリ: {repo}")

        url = f"https://api.github.com/repos/{repo}/dependabot/alerts?state=open&per_page=100"

        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {github_token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")

        print(f"   API URL: {url}")
        print(f"   リクエスト送信中...")

        with urllib.request.urlopen(req) as response:
            alerts = json.loads(response.read().decode())

        print(f"   ✅ {len(alerts)} 件のアラートを取得")

        matching_cves = []
        checked_alerts = 0
        package_matched = 0

        for alert in alerts:
            checked_alerts += 1

            # パッケージ名でフィルタ
            if 'dependency' not in alert or 'package' not in alert['dependency']:
                continue

            alert_package = alert['dependency']['package'].get('name', '')
            if alert_package != package_name:
                continue

            package_matched += 1

            # Dependabot Alert番号とURL
            alert_number = alert.get('number', 0)
            alert_url = alert.get('html_url', '')
            print(f"   📦 パッケージ一致: {alert_package} - Alert #{alert_number}")

            # このアラートのCVE番号を取得
            alert_cves = []
            if 'security_advisory' in alert and 'identifiers' in alert['security_advisory']:
                for identifier in alert['security_advisory']['identifiers']:
                    if identifier.get('type') == 'CVE':
                        alert_cves.append(identifier['value'])

            if not alert_cves:
                continue

            # vulnerabilitiesをチェック
            if 'security_advisory' not in alert or 'vulnerabilities' not in alert['security_advisory']:
                continue

            for vuln in alert['security_advisory']['vulnerabilities']:
                # このvulnerabilityが対象パッケージか確認
                if vuln.get('package', {}).get('name') != package_name:
                    continue

                # 条件1: from_version が vulnerable_version_range に含まれる
                vulnerable_range = vuln.get('vulnerable_version_range', '')
                if not vulnerable_range:
                    continue

                if not version_in_range(from_version, vulnerable_range):
                    continue

                # 条件2: to_version が first_patched_version 以上
                patched_version_obj = vuln.get('first_patched_version')
                if not patched_version_obj:
                    continue

                patched_version = patched_version_obj.get('identifier', '')
                if not patched_version:
                    continue

                if compare_versions(to_version, patched_version) < 0:
                    continue

                # 両方の条件を満たした場合、このアラートのCVEを追加
                for cve in alert_cves:
                    cve_info = (cve, alert_number, alert_url)
                    if cve_info not in matching_cves:
                        matching_cves.append(cve_info)
                        print(f"  ✅ {cve} - Alert #{alert_number}")

        print(f"   📊 検索結果: {checked_alerts}件のアラートを確認, {package_matched}件がパッケージに一致")

        if matching_cves:
            cve_ids = [cve_id for cve_id, _, _ in matching_cves]
            print(f"✅ {len(matching_cves)} 件のCVE番号を取得: {', '.join(cve_ids)}")
        else:
            print(f"⚠️ パッケージ '{package_name}' v{from_version}→v{to_version} に一致するCVEが見つかりません")

        return matching_cves

    except urllib.error.HTTPError as e:
        print(f"⚠️ Dependabotアラート検索エラー (HTTP {e.code}): {e.reason}")
        return []
    except Exception as e:
        print(f"⚠️ Dependabotアラート検索エラー: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_previous_analysis(repo: str, pr_number: int, github_token: str) -> str:
    """同じPRの過去のvulnerability_analyzer.py生成コメントを取得

    Args:
        repo: リポジトリ名（owner/repo形式）
        pr_number: PR番号
        github_token: GitHub トークン

    Returns:
        前回の分析結果（見つからない場合は空文字列）
    """
    try:
        # direction=desc is not working
        # TODO: support pagination if there are many comments
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments?sort=created&direction=asc&per_page=100"

        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {github_token}")
        req.add_header("Accept", "application/vnd.github.v3+json")

        with urllib.request.urlopen(req) as response:
            comments = json.loads(response.read().decode())

        # vulnerability_analyzer.pyによって生成されたコメントを探す
        for comment in reversed(comments):
            if 'This comment was automatically generated by dependahunt.' in comment['body']:
                # 詳細分析結果セクションを抽出
                body = comment['body']

                # 結論部分と詳細分析部分を分離
                match = re.search(r'## 🔒 詳細分析結果.*?(?=## 📋 CVE基本情報|\Z)', body, re.DOTALL)
                if match:
                    return match.group(0).strip()

                # フォールバック: 全体を返す
                return body

        return ""

    except Exception as e:
        print(f"⚠️ 前回分析の取得に失敗: {e}")
        return ""


def has_cve_section(pr_body: str) -> bool:
    """PR本文に既にCVE情報セクションが追記されているかチェック"""
    return CVE_INFO_MARKER in pr_body


def format_cve_section(cve_info_list: List[Tuple[str, int, str]], repo: str) -> str:
    """CVE番号のリストをPR本文追記用にフォーマット

    Args:
        cve_info_list: [(cve_id, alert_number, alert_url), ...]
        repo: リポジトリ名 (owner/repo形式)
    """
    if not cve_info_list:
        return ""

    # CVE番号でグループ化
    from collections import defaultdict
    cve_groups = defaultdict(list)
    for cve_id, alert_number, alert_url in cve_info_list:
        if alert_number > 0 and alert_url:
            cve_groups[cve_id].append((alert_number, alert_url))

    # ユニークなCVE数を計算
    unique_cve_count = len(cve_groups)

    section = "\n\n---\n\n"
    section += f"{CVE_INFO_MARKER}\n\n"
    section += f"## 🔒 検出されたCVE ({unique_cve_count}件)\n\n"

    # CVE番号でソートして表示
    for cve_id in sorted(cve_groups.keys()):
        alerts = cve_groups[cve_id]
        section += f"- **{cve_id}** "
        if alerts:
            # 複数のアラートがある場合はカンマ区切りで表示
            alert_links = [f"[#{num}]({url})" for num, url in sorted(alerts)]
            section += f"(Dependabot Alert {', '.join(alert_links)})\n"
        else:
            section += "\n"

    return section


def update_pr_body(repo: str, pr_number: int, new_body: str, github_token: str) -> bool:
    """PR本文を更新"""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"

    data = {"body": new_body}

    try:
        req = urllib.request.Request(url, method='PATCH')
        req.add_header("Authorization", f"token {github_token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("Content-Type", "application/json")

        json_data = json.dumps(data).encode('utf-8')

        with urllib.request.urlopen(req, json_data) as response:
            if response.getcode() == 200:
                print(f"✅ PR本文を更新しました")
                return True
            else:
                print(f"❌ PR本文更新失敗: HTTP {response.getcode()}")
                return False

    except Exception as e:
        print(f"❌ PR本文更新エラー: {e}")
        return False


def add_cve_info_to_pr(repo: str, pr_number: int, pr_body: str, cve_info_list: List[Tuple[str, int, str]], github_token: str) -> bool:
    """PR本文にCVE情報を追記

    Args:
        repo: リポジトリ名 (owner/repo形式)
        pr_number: PR番号
        pr_body: 現在のPR本文
        cve_info_list: [(cve_id, alert_number, alert_url), ...]
        github_token: GitHub トークン

    Returns:
        追記に成功した場合True
    """
    # 既に追記済みかチェック
    if has_cve_section(pr_body):
        print("ℹ️ CVE情報は既にPR本文に追記済みです")
        return True

    if not cve_info_list:
        print("ℹ️ 追記するCVE情報がありません")
        # CVE番号がない場合も、マーカーだけ追加して重複実行を防止
        new_body = pr_body + f"\n\n{CVE_INFO_MARKER}\n"
        return update_pr_body(repo, pr_number, new_body, github_token)

    # CVE情報セクションを作成
    cve_section = format_cve_section(cve_info_list, repo)

    # PR本文に追記
    new_body = pr_body + cve_section

    print("📝 PR本文にCVE情報を追記中...")
    return update_pr_body(repo, pr_number, new_body, github_token)


def post_github_comment(repo: str, pr_number: int, comment: str, github_token: str) -> bool:
    """GitHub APIを使ってPRにコメントを投稿"""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"

    data = {
        "body": comment
    }

    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {github_token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("Content-Type", "application/json")

        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data

        with urllib.request.urlopen(req) as response:
            if response.getcode() == 201:
                response_data = json.loads(response.read().decode())
                print(f"✅ コメントを投稿しました: {response_data['html_url']}")
                return True
            else:
                print(f"❌ コメント投稿に失敗しました: HTTP {response.getcode()}")
                return False

    except urllib.error.URLError as e:
        print(f"❌ GitHub APIエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ コメント投稿エラー: {e}")
        return False

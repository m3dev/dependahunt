"""
CVE情報の取得と分析
"""

import json
import re
import urllib.request
from typing import Dict, Any, List

from config import SEVERITY_MAP


def get_nvd_vulnerability_info(cve_id: str) -> Dict[str, Any]:
    """NVD APIから脆弱性情報を取得"""
    try:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "vulnerability-analyzer/1.0")

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        if data.get('vulnerabilities'):
            vuln = data['vulnerabilities'][0]['cve']
            return {
                'id': cve_id,
                'description': vuln['descriptions'][0]['value'] if vuln.get('descriptions') else 'No description available',
                'severity': get_cvss_severity(vuln),
                'published': vuln.get('published', 'Unknown'),
                'modified': vuln.get('lastModified', 'Unknown')
            }
        else:
            return {'id': cve_id, 'error': 'CVE not found in NVD database'}

    except Exception as e:
        return {'id': cve_id, 'error': f'Failed to fetch CVE data: {str(e)}'}


def get_cvss_severity(cve_data: Dict[str, Any]) -> str:
    """CVSS情報から重要度を取得"""
    try:
        metrics = cve_data.get('metrics', {})

        # CVSS v4.0を優先
        if 'cvssMetricV40' in metrics:
            cvss = metrics['cvssMetricV40'][0]['cvssData']
            return f"{cvss.get('baseSeverity', 'Unknown')} ({cvss.get('baseScore', 'N/A')})"

        # CVSS v3.1
        if 'cvssMetricV31' in metrics:
            cvss = metrics['cvssMetricV31'][0]['cvssData']
            return f"{cvss.get('baseSeverity', 'Unknown')} ({cvss.get('baseScore', 'N/A')})"

        # CVSS v3.0
        elif 'cvssMetricV30' in metrics:
            cvss = metrics['cvssMetricV30'][0]['cvssData']
            return f"{cvss.get('baseSeverity', 'Unknown')} ({cvss.get('baseScore', 'N/A')})"

        # CVSS v2
        elif 'cvssMetricV2' in metrics:
            cvss = metrics['cvssMetricV2'][0]['cvssData']
            return f"CVSS v2: {cvss.get('baseScore', 'N/A')}"

        return "Unknown"
    except:
        return "Unknown"


def translate_severity_to_japanese(severity: str) -> str:
    """重要度を日本語に翻訳"""
    for eng, jp in SEVERITY_MAP.items():
        if eng.upper() in severity.upper():
            return severity.replace(eng.upper(), jp).replace(eng.lower(), jp).replace(eng, jp)

    return severity


def extract_updated_packages(pr_body: str) -> List[str]:
    """PR本文から更新対象のパッケージ名を抽出"""
    packages = []

    # パッケージ名の抽出パターン（@scope/package対応）
    patterns = [
        r'Bump\s+(@?[a-zA-Z0-9\-_./]+)\s+from',  # Bump @scope/package from
        r'Updates?\s+`(@?[a-zA-Z0-9\-_./]+)`\s+from',  # Updates `@scope/package` from
        r'\[(@?[a-zA-Z0-9\-_./]+)\]\(',  # [@scope/package](url)
    ]

    for pattern in patterns:
        matches = re.findall(pattern, pr_body)
        packages.extend(matches)

    # Dependabot PRのタイトルからも抽出
    title_patterns = [
        r'Bump\s+(@?[a-zA-Z0-9\-_./]+)\s+from',
        r'Update\s+(@?[a-zA-Z0-9\-_./]+)\s+to'
    ]

    for pattern in title_patterns:
        matches = re.findall(pattern, pr_body)
        packages.extend(matches)

    # 重複を除去し、有効なパッケージ名のみを保持
    unique_packages = list(set(packages))
    # 短すぎる名前やURLは除外
    filtered_packages = [pkg for pkg in unique_packages
                        if len(pkg) > 1 and not pkg.startswith('http')
                        and not pkg.endswith('.git')]

    return filtered_packages

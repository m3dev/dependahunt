# dependahunt
Dependabot/Renovateが作成したPRを自動的に分析し、脆弱性の影響をAIで評価するワークフローです。
前提としてDependabot alertsが有効になっている必要があります。Renovateおよび本ツールは脆弱性情報のソースとしてDependabot alertsを参照しているため、Renovateを利用する場合も有効にする必要があります。

## 導入方法
### GitHub Appの作成
次の権限を付与したGitHub Appを作成してください。
- Contents: read only
- Pull requests: read and write
- Dependabot alerts: read only

### ワークフローの配置
次のYAML を `.github/workflows` の中に配置してください。
なお、実運用においては、直接本リポジトリのワークフローを参照するのではなく、本リポジトリをforkしたうえでそちらを参照することを推奨します。

```yaml
name: dependahunt Caller

on:
  workflow_run: # Dependabot/RenovateのPR作成時（チェックが行われた後）にトリガする
    workflows: ["Dependabot Updates", "(Your Renovate Workflow Name)"]
    types: [completed]
  issue_comment: # PRコメント時にトリガする
    types: [created]
  workflow_dispatch:  # GitHubのUI上から手動実行できるようにする

permissions:
  contents: read
  pull-requests: write
  id-token: write
  security-events: read

jobs:
  run:
    uses: m3dev/dependahunt/.github/workflows/analyze.yml@v1
    with:
      runs_on: '"ubuntu-latest"'
      event_name: ${{ github.event_name }}
      ai_provider: 'claude-vertex' 
      ai_model: 'claude-sonnet-4-5@20250929'
      vertex_project_id: '(your project id)'
      vertex_region: '(your region)'
      pr_creator: '(your Dependabot or Renovate bot name)'
    secrets:
      APP_ID: ${{ secrets.APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}
      WORKLOAD_IDENTITY_PROVIDER: ${{ secrets.WORKLOAD_IDENTITY_PROVIDER }}
      SERVICE_ACCOUNT: ${{ secrets.SERVICE_ACCOUNT }}
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

```

#### パラメータ・シークレット

##### `with` パラメータ

| パラメータ名 | 必須 | 説明 |
|------------|------|------|
| `event_name` | ○ | イベントタイプ判別用。通常は`${{ github.event_name }}`を指定すること。 |
| `runs_on` | ○ | ワークフローを実行するランナーの指定（JSON文字列形式）。単一ランナーの場合は`'"ubuntu-latest"'`のようにダブルクォートで囲む。配列の場合は`'["self-hosted", "ubuntu"]'`のように配列形式で指定。 |
| `ai_provider` | ○ | 使用するAIプロバイダ。指定可能な値: `claude-vertex`, `claude-direct`, `gemini-vertex`, `gemini-direct` |
| `ai_model` | ○ | 使用するAIモデル。プロバイダに応じて適切なモデルを指定。例: `claude-sonnet-4-5@20250929`, `gemini-2.5-pro` |
| `vertex_project_id` | △ | Vertex AIを使用するGCPプロジェクトID。Vertex AI使用時（`ai_provider`が`claude-vertex`または`gemini-vertex`の場合）は必須。 |
| `vertex_region` | △ | Vertex AIのGCPリージョン |
| `pr_creator` | - | チェック対象にするPRの作成者名。ここで指定したユーザが作成したPRがチェック対象になる。デフォルトは `dependabot[bot]` |
| `trigger_word` | - | PRコメントで分析を起動するトリガーワード。デフォルトは`/dependahunt` |

##### `secrets` シークレット

| シークレット名 | 必須 | 説明 |
|------------|------|------|
| `APP_ID` | ○ | 作成したGitHub AppのApp ID |
| `APP_PRIVATE_KEY` | ○ | GitHub Appの秘密鍵（PEM形式） |
| `WORKLOAD_IDENTITY_PROVIDER` | △ | GCP Workload Identity Providerのリソースパス（例: `projects/123456789/locations/global/workloadIdentityPools/github/providers/github-oidc`）。Vertex AI使用時は必須。 |
| `SERVICE_ACCOUNT` | △ | Vertex AIアクセス用のGCPサービスアカウント（例: `github-actions@project-id.iam.gserviceaccount.com`）。Vertex AI使用時は必須。 |
| `ANTHROPIC_API_KEY` | △ | Anthropic APIキー（例: `sk-ant-api03-...`）。`ai_provider`が`claude-direct`の場合に必須。 |
| `GEMINI_API_KEY` | △ | Google AI Studio APIキー（例: `AIzaSy...`）。`ai_provider`が`gemini-direct`の場合に必須。 |

### `renovate.json`の編集（Renovateを利用する場合のみ）
Renovateを使用する場合、PR本文内にパッケージ情報を埋め込む必要があります。`extends` に `github>m3dev/dependahunt#v1` を追加してください。
この設定により `vulnerabilityAlerts` が有効化され、 `prBodyNotes` にパッケージ情報が埋め込まれるようになります。

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    "github>m3dev/dependahunt#v1"
  ],
}
```
上記のShareable Config Presetsを利用せず細かくルールをカスタマイズする場合は、 `<!-- dependahunt:target-package {{{ toJSON (toObject 'packageName' packageName 'depName' depName 'currentVersion' currentVersion 'newVersion' newVersion) }}} -->` を脆弱性アップデートの `prBodyNotes` に追加してください。


## 使用方法
### PR作成時の自動チェック
Dependabot/RenovateがパッチPRを作成したタイミングで自動的に実行され、未分析のPRの内容が分析されます。無効化するにはYAMLの `workflow_run` キーを削除してください。
なお、Dependabot自体はデフォルトブランチを分析対象としています。対象ブランチを変更する場合は [`dependabot.yaml`](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference#target-branch-)で設定してください。

### PRコメント内での手動チェック
Dependabot/Renovateが作成したPRのコメントに特定のコマンドを入力することで、そのPRの内容が分析されます。

#### コマンド
- `/dependahunt analyze [パッケージ名] [--comment "追加の指示"] [--include-previous]`
  - `パッケージ名`
    1つのPRに含まれる複数のパッケージのうち特定のパッケージのみを再分析したい場合にパッケージ名を指定します。例：`/dependahunt analyze lodash`
    省略した場合はPRに含まれる全てのパッケージを分析します。
    なお、1つのPRに複数のパッケージのアップデートが混在している設定は非推奨です。
  - `--comment`
    分析の際に重視しておいてほしい点や質問などの追加の指示を与えることができます。
  - `--include-previous`
    直近の分析結果も今回の分析に含めます。 `--comment`と組み合わせることで、直近の結果を踏まえた指示（例：他の対策はないか、など）を与えることができます。
- `/dependahunt re-analyze [パッケージ名] [--comment "追加の指示"]`
  `/dependahunt analyze --include-previous` のシンタックスシュガーです。


### GitHubのUI上からの手動チェック（一括実行したい場合など）
GitHubのActions画面から追加したワークフローを選択し、「Run workflow」を押下すると、未分析のPRに対して実行されます。

## 制限事項
- 1つのPRに複数のパッケージのアップデートが混在している設定は非推奨です。Dependabot/Renovateの設定で、各パッケージごとに個別のPRを作成するようにしてください。
- 本ツールはリポジトリのDependabot alertsに記録されている脆弱性情報を参照して分析を行います。Renovateが対応していてもDependabotが対応していないパッケージマネージャの場合、脆弱性情報が見つからず脆弱性の影響有無を正しく判断できません。

## ⚠️注意
公開リポジトリなど、信頼できないメンバーが閲覧できるリポジトリでこのワークフローを使用しないでください。
仕様上プロンプトインジェクションが可能であり、APIトークンの漏洩等が発生する可能性があります。

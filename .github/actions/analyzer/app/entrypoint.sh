#!/bin/bash

set -e

# Python出力のバッファリングを無効化
export PYTHONUNBUFFERED=1

# デバッグ情報を表示
echo "=== Dependabot Vulnerability Analyzer ==="
echo "Repository: $INPUT_TARGET_REPOSITORY"
echo "PR Number: $INPUT_TARGET_PR_NUMBER"
echo "Comment: $INPUT_COMMENT"
echo "Silent: $INPUT_SILENT"
echo "Additional Comment: $INPUT_ADDITIONAL_COMMENT"
echo "Include Previous: $INPUT_INCLUDE_PREVIOUS"
echo "=========================================="

# Claude CLIの存在確認とバージョン表示
echo "=== Claude CLI Environment Check ==="
echo "PATH: $PATH"
echo -n "Claude CLI location: "
which claude || echo "NOT FOUND in PATH"
if command -v claude &> /dev/null; then
    echo "Claude CLI version:"
    claude --version || echo "Version check failed"
else
    echo "ERROR: Claude CLI is not installed"
    exit 1
fi
echo "NPM global packages:"
npm list -g --depth=0 2>/dev/null || echo "npm list failed"
echo "=========================================="

# 必要な環境変数をチェック
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$INPUT_TARGET_REPOSITORY" ]; then
    echo "Error: repository input is required"
    exit 1
fi

if [ -z "$INPUT_TARGET_PR_NUMBER" ]; then
    echo "Error: pr_number input is required"
    exit 1
fi

# オプションフラグを構築
FLAGS=""
if [ "$INPUT_COMMENT" = "true" ]; then
    FLAGS="$FLAGS --comment"
fi
if [ "$INPUT_SILENT" = "true" ]; then
    FLAGS="$FLAGS --silent"
fi

# 追加指示
if [ -n "$INPUT_ADDITIONAL_COMMENT" ]; then
    FLAGS="$FLAGS --additional-comment \"$INPUT_ADDITIONAL_COMMENT\""
fi

# 前回分析を含める
if [ "$INPUT_INCLUDE_PREVIOUS" = "true" ]; then
    FLAGS="$FLAGS --include-previous"
fi

# 作業ディレクトリに移動
if [ -n "$INPUT_WORKING_DIRECTORY" ] && [ "$INPUT_WORKING_DIRECTORY" != "." ]; then
    echo "Changing to working directory: $INPUT_WORKING_DIRECTORY"
    cd "$INPUT_WORKING_DIRECTORY" || {
        echo "Error: Failed to change to directory $INPUT_WORKING_DIRECTORY"
        exit 1
    }
    echo "Current directory: $(pwd)"
fi

cd "$GITHUB_WORKSPACE"
# 脆弱性分析スクリプトを実行
echo "Running vulnerability analysis..."
eval python3 -u /app/vulnerability_analyzer.py "$INPUT_TARGET_REPOSITORY" "$INPUT_TARGET_PR_NUMBER" $FLAGS

echo "Analysis completed successfully!"

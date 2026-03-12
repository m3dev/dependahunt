#!/usr/bin/env python3
"""
AIプロバイダの抽象化レイヤー
複数のAI API（Claude、Gemini、Codex等）を統一インターフェースで利用可能にする
"""

import os
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AIProvider(ABC):
    """AIプロバイダの基底クラス"""

    @abstractmethod
    def analyze(self, prompt: str, timeout: int = 360) -> str:
        """
        プロンプトを送信して分析結果を取得

        Args:
            prompt: 分析用プロンプト
            timeout: タイムアウト時間（秒）

        Returns:
            分析結果のテキスト
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を取得"""
        pass

    def _debug_print(self, message: str):
        """デバッグメッセージを出力"""
        if os.getenv('DEBUG_MODE') == '1':
            print(f"🔍 DEBUG [{self.get_provider_name()}]: {message}")


class ClaudeCLIProvider(AIProvider):
    """Claude CLI共通基底クラス"""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def _configure_environment(self, env: Dict[str, str]) -> None:
        """
        環境変数を設定（サブクラスで実装）

        Args:
            env: 環境変数辞書（この辞書に必要な環境変数を追加する）
        """
        pass

    def analyze(self, prompt: str, timeout: int = 360) -> str:
        """Claude CLIを使って分析（共通実装）"""
        self._debug_print(f"Starting analysis (prompt length: {len(prompt)} chars)")

        try:
            start_time = __import__('time').time()
            print(f"🚀 {self.get_provider_name()} 実行開始...")

            # Claude CLIコマンドを構築（標準入力からプロンプトを渡す）
            cmd = ['claude', '--print', '--tools', 'Read,Glob,Grep,Task,TodoWrite', '--model', self.model]

            # 環境変数を設定
            env = os.environ.copy()
            self._configure_environment(env)

            # Claude CLIを実行（標準入力経由でプロンプトを渡す）
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=True
            )

            elapsed_time = __import__('time').time() - start_time
            print(f"⏱️  実行完了: {elapsed_time:.2f}秒")

            # 出力を取得
            output = result.stdout.strip()

            if not output:
                raise RuntimeError("Claude CLIの出力が空です")

            return output

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Claude CLIがタイムアウトしました（{timeout}秒）")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Claude CLI実行エラー: {e.stderr or e.stdout}")
        except FileNotFoundError:
            raise RuntimeError("Claude CLIが見つかりません。インストールされているか確認してください")
        except Exception as e:
            raise RuntimeError(f"分析エラー: {type(e).__name__}: {str(e)}")


class ClaudeVertexAIProvider(ClaudeCLIProvider):
    """Claude via Vertex AI プロバイダー (CLI経由)"""

    def __init__(self, project_id: str, region: str, model: str):
        super().__init__(model)
        self.project_id = project_id
        self.region = region
        self._debug_print(f"Initialized with project_id={project_id}, region={region}, model={model}")

    def get_provider_name(self) -> str:
        return "Claude (Vertex AI via CLI)"

    def _configure_environment(self, env: Dict[str, str]) -> None:
        """Vertex AI用の環境変数を設定"""
        env['CLAUDE_CODE_USE_VERTEX'] = 'true'
        env['ANTHROPIC_VERTEX_PROJECT_ID'] = self.project_id
        env['CLOUD_ML_REGION'] = self.region


class ClaudeDirectAPIProvider(ClaudeCLIProvider):
    """Claude Direct API プロバイダー (CLI経由)"""

    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.api_key = api_key
        self._debug_print(f"Initialized with model={model}")

    def get_provider_name(self) -> str:
        return "Claude (Direct API via CLI)"

    def _configure_environment(self, env: Dict[str, str]) -> None:
        """Direct API用の環境変数を設定"""
        env['ANTHROPIC_API_KEY'] = self.api_key


class ClaudeBedrockProvider(ClaudeCLIProvider):
    """Claude via AWS Bedrock プロバイダー (CLI経由)"""

    def __init__(self, region: str, model: str):
        super().__init__(model)
        self.region = region
        self._debug_print(f"Initialized with region={region}, model={model}")

    def get_provider_name(self) -> str:
        return "Claude (AWS Bedrock via CLI)"

    def _configure_environment(self, env: Dict[str, str]) -> None:
        """Bedrock用の環境変数を設定"""
        env['CLAUDE_CODE_USE_BEDROCK'] = '1'
        env['AWS_DEFAULT_REGION'] = self.region


class GeminiCLIProvider(AIProvider):
    """Gemini CLI共通基底クラス"""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def _configure_environment(self, env: Dict[str, str]) -> None:
        """
        環境変数を設定（サブクラスで実装）

        Args:
            env: 環境変数辞書（この辞書に必要な環境変数を追加する）
        """
        pass

    def analyze(self, prompt: str, timeout: int = 360) -> str:
        """Gemini CLIを使って分析（共通実装）"""
        self._debug_print(f"Starting analysis (prompt length: {len(prompt)} chars)")

        try:
            start_time = __import__('time').time()
            print(f"🚀 {self.get_provider_name()} 実行開始...")

            # Gemini CLIコマンドを構築（位置引数としてプロンプトを渡す）
            cmd = ['gemini', '--model', self.model, prompt]

            # 環境変数を設定
            env = os.environ.copy()
            self._configure_environment(env)

            # Gemini CLIを実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=True
            )

            elapsed_time = __import__('time').time() - start_time
            print(f"⏱️  実行完了: {elapsed_time:.2f}秒")

            # 出力を取得
            output = result.stdout.strip()

            if not output:
                raise RuntimeError("Gemini CLIの出力が空です")

            return output

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Gemini CLIがタイムアウトしました（{timeout}秒）")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Gemini CLI実行エラー: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("Gemini CLIが見つかりません。インストールされているか確認してください")
        except Exception as e:
            raise RuntimeError(f"分析エラー: {type(e).__name__}: {str(e)}")


class GeminiVertexAIProvider(GeminiCLIProvider):
    """Gemini via Vertex AI プロバイダー (CLI経由)"""

    def __init__(self, project_id: str, region: str, model: str):
        super().__init__(model)
        self.project_id = project_id
        self.region = region
        self._debug_print(f"Initialized with project_id={project_id}, region={region}, model={model}")

    def get_provider_name(self) -> str:
        return "Gemini (Vertex AI via CLI)"

    def _configure_environment(self, env: Dict[str, str]) -> None:
        """Vertex AI用の環境変数を設定"""
        env['GOOGLE_GENAI_USE_VERTEXAI'] = 'true'
        env['GOOGLE_CLOUD_PROJECT'] = self.project_id
        env['GOOGLE_CLOUD_LOCATION'] = self.region


class GeminiDirectAPIProvider(GeminiCLIProvider):
    """Gemini Direct API プロバイダー (CLI経由)"""

    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.api_key = api_key
        self._debug_print(f"Initialized with model={model}")

    def get_provider_name(self) -> str:
        return "Gemini (Direct API via CLI)"

    def _configure_environment(self, env: Dict[str, str]) -> None:
        """Direct API用の環境変数を設定"""
        env['GEMINI_API_KEY'] = self.api_key


def create_ai_provider(
    provider_type: str,
    anthropic_api_key: Optional[str] = None,
    vertex_project_id: Optional[str] = None,
    vertex_region: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    model: Optional[str] = None,
    aws_region: Optional[str] = None,
) -> AIProvider:
    """
    AIプロバイダのインスタンスを作成

    Args:
        provider_type: プロバイダータイプ (claude-vertex/claude-direct/claude-bedrock/gemini-vertex/gemini-direct)
        anthropic_api_key: Anthropic API キー (Claude Direct API用)
        vertex_project_id: Vertex AI プロジェクトID
        vertex_region: Vertex AI リージョン
        gemini_api_key: Gemini Direct API キー
        model: 使用するモデル名
        aws_region: AWS リージョン (Claude Bedrock用)

    Returns:
        AIProvider インスタンス
    """

    # プロバイダーインスタンスを作成
    if provider_type == "claude-vertex":
        if not vertex_project_id:
            raise ValueError("Vertex AI project ID is required for claude-vertex provider")
        if not vertex_region:
            raise ValueError("Vertex AI region is required for claude-vertex provider")
        if not model:
            raise ValueError("Model name is required for claude-vertex provider")
        return ClaudeVertexAIProvider(
            vertex_project_id,
            vertex_region,
            model
        )

    elif provider_type == "claude-direct":
        if not anthropic_api_key:
            raise ValueError("Anthropic API key is required for claude-direct provider")
        if not model:
            raise ValueError("Model name is required for claude-direct provider")
        return ClaudeDirectAPIProvider(anthropic_api_key, model)

    elif provider_type == "gemini-vertex":
        if not vertex_project_id:
            raise ValueError("Vertex AI project ID is required for gemini-vertex provider")
        if not vertex_region:
            raise ValueError("Vertex AI region is required for gemini-vertex provider")
        if not model:
            raise ValueError("Model name is required for gemini-vertex provider")
        return GeminiVertexAIProvider(
            vertex_project_id,
            vertex_region,
            model
        )

    elif provider_type == "claude-bedrock":
        if not model:
            raise ValueError("Model name is required for claude-bedrock provider")
        return ClaudeBedrockProvider(aws_region or "us-east-1", model)

    elif provider_type == "gemini-direct":
        if not gemini_api_key:
            raise ValueError("Gemini API key is required for gemini-direct provider")
        if not model:
            raise ValueError("Model name is required for gemini-direct provider")
        return GeminiDirectAPIProvider(gemini_api_key, model)

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

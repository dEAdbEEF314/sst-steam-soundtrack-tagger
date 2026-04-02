"""
VGMdb Browser-Use PoC スクリプト

環境変数 LLM_PROVIDER (ollama または openai) に基づいて
LLMを初期化し、browser-use エージェントでVGMdbを検索します。
事前に Chromium のインストールが必要です。
"""
import os
import asyncio
from dotenv import load_dotenv

# テレメトリ等がネットワーク起因でフリーズするのを防ぐ
os.environ["ANONYMIZED_TELEMETRY"] = "false"
# 内部のログレベルをデバッグに設定する（出力先は後でファイルに切り替えます）
os.environ["BROWSER_USE_LOGGING_LEVEL"] = "debug"

# dotenv を読み込み
load_dotenv()

from config import load_config as load_scout_config
from core.config import LlmConfig

def get_llm(llm_cfg: LlmConfig):
    """Configに基づいてLLMを初期化する。"""
    # BaseChatModel は遅延ロード
    provider = llm_cfg.provider.lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        
        # PydanticのAttributeError回避用ラッパークラス
        class PatchedChatOpenAI(ChatOpenAI):
            model_config = {"extra": "allow"}
            
            @property
            def provider(self):
                return "openai"

            @property
            def model(self):
                return self.model_name

        print("Using OpenAI API...")
        # OPENAI_API_KEY が自動で読み込まれます
        return PatchedChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    # Ollama がネイティブでサポートしている OpenAI 互換 API 経由で呼び出します。
    from langchain_openai import ChatOpenAI
    
    class PatchedOllamaChatOpenAI(ChatOpenAI):
        model_config = {"extra": "allow"}
        
        @property
        def provider(self):
            return "ollama"

        @property
        def model(self):
            return self.model_name

    base_url = llm_cfg.base_url.rstrip("/")
    model = llm_cfg.model
    print(f"Using Ollama via OpenAI API compatible mode (URL: {base_url}/v1, Model: {model})...")
    
    from langchain_core.callbacks import BaseCallbackHandler
    import json

    class HumanReadableLogHandler(BaseCallbackHandler):
        def __init__(self, filename):
            self.filename = filename

        def _log(self, text):
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(text + "\n")

        def on_chat_model_start(self, serialized, messages, **kwargs):
            self._log("\n" + "="*60)
            self._log("★★★ LLMへのリクエスト (Input) ★★★")
            self._log("="*60)
            # 各メッセージを分かりやすく出力 (DOMテキストなどで長い場合もそのまま出します)
            for batch in messages:
                for idx, msg in enumerate(batch):
                    role = getattr(msg, 'type', getattr(msg, 'role', 'unknown')).upper()
                    content = getattr(msg, 'content', '')
                    self._log(f"\n[{idx+1}. 送信者: {role} ]")
                    self._log("-" * 40)
                    if isinstance(content, list):
                        # Vision等で画像やテキストが複数組になっている場合
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                self._log(item.get("text", ""))
                            else:
                                self._log(f"<{type(item).__name__} data>")
                    else:
                        self._log(str(content).strip())

        def on_llm_end(self, response, **kwargs):
            self._log("\n" + "="*60)
            self._log("★★★ LLMからの返答 (Output) ★★★")
            self._log("="*60)
            for gen in response.generations:
                for g in gen:
                    text = getattr(g, 'text', '')
                    msg = getattr(g, 'message', None)
                    if msg and getattr(msg, 'tool_calls', None):
                        # OpenAI等ネイティブのTool Callの場合
                        self._log(json.dumps(msg.tool_calls, indent=2, ensure_ascii=False))
                        continue
                    
                    try:
                        # 文字列の中にJSONの返答が含まれている場合（Ollamaの関数呼び出し等）
                        # 余分なマークダウンバッククォートがある場合の対応
                        clean_text = text.replace('```json', '').replace('```', '').strip()
                        parsed = json.loads(clean_text)
                        self._log(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except (json.JSONDecodeError, TypeError):
                        self._log(str(text))
            self._log("="*60 + "\n")

    # 人間向けに整形したログを扱うカスタムハンドラ
    file_callback = HumanReadableLogHandler("debug.log")

    return PatchedOllamaChatOpenAI(
        base_url=f"{base_url}/v1",
        api_key="ollama", # Ollama では値は何でもOKだが必須
        model=model,
        temperature=0.0,
        # max_tokens を指定して応答を安定化
        max_tokens=4096,
        callbacks=[file_callback]
    )

async def main():
    print("Initializing libraries...")
    try:
        from browser_use import Agent
        from browser_use.browser.browser import Browser, BrowserConfig
        import logging
        
        # 標準のコンソール出力（ターミナル）を無効化し、すべて debug.log に書き出す
        log_file = "debug.log"
        root_logger = logging.getLogger()
        
        # 既存のすべてのハンドラ（画面出力用など）を取り除く
        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)
            
        browser_logger = logging.getLogger("browser_use")
        for h in browser_logger.handlers[:]:
            browser_logger.removeHandler(h)

        # ファイルへ書き出すためのハンドラを新規登録
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        # browser_use の詳細はDEBUGで吐き出す
        browser_logger.setLevel(logging.DEBUG)
        # browser_logger独自で画面に出さないよう root に任せる
        browser_logger.propagate = True
        
        print(f"ターミナル出力を抑制し、エージェントの思考ログを '{log_file}' に書き出します...")
        
    except ImportError as e:
        print(f"Error: {e}")
        print("実行: uv pip install -r requirements.txt")
        return

    # 設定ファイルの読み込み
    try:
        config_path = os.getenv("SCOUT_CONFIG", "/app/config.yaml")
        cfg = load_scout_config(config_path)
    except Exception as e:
        print(f"Failed to load config, using defaults: {e}")
        from config import ScoutConfig, PathsConfig, VGMdbConfig
        from core.config import StorageConfig, LlmConfig, ModeConfig
        cfg = ScoutConfig(
            paths=PathsConfig(),
            vgmdb=VGMdbConfig(),
            storage=StorageConfig(),
            llm=LlmConfig(),
            mode=ModeConfig()
        )

    print("Initializing LLM...")
    llm = get_llm(cfg.llm)
    
    # ブラウザの起動設定
    # Linux環境（特にroot権限や特殊なユーザー環境）でChromiumが即時クラッシュするのを防ぐため、
    # サンドボックスの無効化などを明示的に指定します。
    print("Configuring Browser...")
    browser = Browser(
        config=BrowserConfig(
            headless=False, # GUI表示
            extra_chromium_args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
    )
    
    # テスト対象のアルバム名
    test_title = "Victory Heat Rally OST"
    # urlエンコード用のモジュール
    import urllib.parse
    encoded_title = urllib.parse.quote(test_title)
    
    prompt = (
        f"直接 VGMdb の検索ページ ( https://vgmdb.net/search?q={encoded_title} ) にアクセスしてください。Google検索は絶対に使わないでください。\n"
        f"その後、検索結果の中から最も関連性の高い '{test_title}' のアルバム詳細ページを開き、そのページから以下の情報を取得して出力してください。\n"
        "1. アルバム名 (Album Title)\n"
        "2. リリース日 (Release Date)\n"
        "3. パブリッシャーまたはアーティスト名\n"
        "目的の情報を取得したらタスクを終了してください。"
    )
    
    print(f"Starting browser-use agent for '{test_title}'...")
    agent = Agent(
        task=prompt,
        llm=llm,
        browser=browser
    )
    
    try:
        # エージェントの実行
        result = await agent.run()
        print("\n=== Agent Result ===")
        print(result)
    except Exception as e:
        print("\n=== Error ===")
        print(f"Agent execution failed: {e}")
    finally:
        # ブラウザのクリーンアップを追加
        if browser:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

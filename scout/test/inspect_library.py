#!/usr/bin/env python
"""Steam ライブラリ検査スクリプト

実際の Steam ライブラリに対して、以下の3ステップを段階的に実行・表示します。

  Step 1: ACF ファイルの内容判別
           - steamapps/ 以下の全 appmanifest_*.acf を読み込み
           - app_id / name / StateFlags / installdir を表示
  Step 2: サウンドトラック ACF ファイルの収集
           - キーワード判定 + FullyInstalled フラグで絞り込み
  Step 3: 音源ファイルの収集
           - 各サウンドトラックの installdir 以下を再帰検索

使い方
------
  # 全件処理
  python test/inspect_library.py

  # 最大 5 件でテスト
  python test/inspect_library.py --max 5

  # Step 1 のみ（ACF 判別だけ確認）
  python test/inspect_library.py --step 1

  # 特定ライブラリパスを直接指定
  python test/inspect_library.py --steam-library "D:/SteamLibrary"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 実行場所に関係なく scout/src を import できるようにする
# ---------------------------------------------------------------------------
_SCOUT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCOUT_ROOT / "src"))

from dotenv import load_dotenv

# .env は scout/.env を優先し、なければ scout/src/.env も試みる
_env_path = _SCOUT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

from acf_parser import (
    get_app_id,
    get_install_dir,
    get_name,
    get_state_flags,
    is_installed,
    parse_acf,
)
from library_scanner import (
    AUDIO_EXTENSIONS,
    FORMAT_PRIORITY,
    SOUNDTRACK_KEYWORDS,
    _detect_format_subdirs,
    _find_audio_files,
    _is_soundtrack_name,
    _resolve_install_path,
)

# ---------------------------------------------------------------------------
# ANSI カラーコード（Windows 10 1511 以降対応）
# ---------------------------------------------------------------------------
_USE_COLOR = sys.stdout.isatty() or os.getenv("FORCE_COLOR", "").lower() in ("1", "true")

# stdout が UTF-8 でない場合（例: Windows CP932 ターミナル）は記号を ASCII に落とす
_UTF8_OK = (getattr(sys.stdout, "encoding", "") or "").upper().replace("-", "") in ("UTF8", "UTF8BOM")

_C = {
    "RESET":  "\033[0m"  if _USE_COLOR else "",
    "BOLD":   "\033[1m"  if _USE_COLOR else "",
    "GREEN":  "\033[32m" if _USE_COLOR else "",
    "YELLOW": "\033[33m" if _USE_COLOR else "",
    "CYAN":   "\033[36m" if _USE_COLOR else "",
    "DIM":    "\033[2m"  if _USE_COLOR else "",
    "RED":    "\033[31m" if _USE_COLOR else "",
}

# 記号定義（UTF-8 環境ではリッチ、非 UTF-8 では ASCII）
_SYM_OK   = "[OK] " if not _UTF8_OK else "✓ "
_SYM_SKIP = "---  " if not _UTF8_OK else "─  "
_SYM_WARN = "[!]  " if not _UTF8_OK else "⚠  "
_SYM_ERR  = "[X]  " if not _UTF8_OK else "✗  "
_SYM_BAR  = "-"     if not _UTF8_OK else "─"


def _head(text: str) -> str:
    return f"{_C['BOLD']}{_C['CYAN']}{text}{_C['RESET']}"


def _ok(text: str) -> str:
    return f"{_C['GREEN']}{text}{_C['RESET']}"


def _skip(text: str) -> str:
    return f"{_C['DIM']}{text}{_C['RESET']}"


def _warn(text: str) -> str:
    return f"{_C['YELLOW']}{text}{_C['RESET']}"


def _err(text: str) -> str:
    return f"{_C['RED']}{text}{_C['RESET']}"


# ---------------------------------------------------------------------------
# ステップ関数
# ---------------------------------------------------------------------------

def step1_inspect_acf(
    steamapps_dir: Path,
    max_count: int | None,
    app_id: int | None = None,
) -> list[dict]:
    """全 ACF ファイルを読み込んで内容を表示。処理済みレコードのリストを返す。"""
    print(_head(f"\n{'='*60}"))
    print(_head(" Step 1: ACF ファイルの内容判別"))
    print(_head(f"{'='*60}"))
    print(f"  場所: {steamapps_dir}\n")

    if app_id is not None:
        target = steamapps_dir / f"appmanifest_{app_id}.acf"
        acf_files = [target] if target.exists() else []
        print(f"  [ --app-id {app_id} ]")
    else:
        acf_files = sorted(steamapps_dir.glob("appmanifest_*.acf"))
    if not acf_files:
        print(_warn("  ACF ファイルが見つかりませんでした。"))
        return []

    print(f"  ACF ファイル総数: {len(acf_files)}")
    if max_count is not None:
        acf_files = acf_files[:max_count]
        print(f"  [ --max {max_count} ]\n")
    else:
        print()

    records: list[dict] = []
    parse_errors = 0

    for idx, acf_path in enumerate(acf_files, start=1):
        try:
            state = parse_acf(acf_path)
        except Exception as exc:
            print(_err(f"  [{idx:3d}] {acf_path.name}  → パースエラー: {exc}"))
            parse_errors += 1
            continue

        app_id     = get_app_id(state)
        name       = get_name(state)
        flags      = get_state_flags(state)
        install_dir= get_install_dir(state)
        installed  = is_installed(state)
        is_ost     = _is_soundtrack_name(name)

        # フラグラベル (bit flags)
        flag_labels: list[str] = []
        if flags & 4:   flag_labels.append("FullyInstalled")
        if flags & 2:   flag_labels.append("UpdateRequired")
        if flags & 8:   flag_labels.append("UpdateRunning")
        if flags & 16:  flag_labels.append("UpdatePaused")
        flag_str = "|".join(flag_labels) if flag_labels else "none"

        mark  = _ok(f"{_SYM_OK}OST") if (installed and is_ost) else (_skip(_SYM_SKIP) if not is_ost else _warn(f"{_SYM_WARN}not installed"))
        print(
            f"  [{idx:3d}] {acf_path.name}\n"
            f"         app_id     : {app_id}\n"
            f"         name       : {name}\n"
            f"         StateFlags : {flags} ({flag_str})\n"
            f"         installdir : {install_dir}\n"
            f"         判定       : {mark}"
        )
        print()

        records.append({
            "acf_path":    str(acf_path),
            "app_id":      app_id,
            "name":        name,
            "state_flags": flags,
            "install_dir": install_dir,
            "installed":   installed,
            "is_ost":      is_ost,
        })

    print(f"  -- Step 1 完了: 総計={len(acf_files)}件  パースエラー={parse_errors}件 --")
    return records


def step2_filter_soundtracks(records: list[dict]) -> list[dict]:
    """Step 1 レコードからサウンドトラックのみ絞り込む。"""
    print(_head(f"\n{'='*60}"))
    print(_head(" Step 2: サウンドトラック ACF ファイルの収集"))
    print(_head(f"{'='*60}\n"))

    print(f"  検索キーワード: {', '.join(SOUNDTRACK_KEYWORDS)}\n")

    soundtracks: list[dict] = []
    skipped_not_ost     = 0
    skipped_not_installed = 0

    for r in records:
        if not r["is_ost"]:
            skipped_not_ost += 1
            continue
        if not r["installed"]:
            skipped_not_installed += 1
            print(_warn(f"  スキップ (未インストール): [{r['app_id']}] {r['name']}"))
            continue
        soundtracks.append(r)
        print(_ok(f"  {_SYM_OK}[{r['app_id']:>10}] {r['name']}"))
        print(f"    installdir: {r['install_dir']}")
        print()

    print(f"  -- Step 2 完了: サウンドトラック={len(soundtracks)}件  "
          f"非OST={skipped_not_ost}件  未インストール={skipped_not_installed}件 --")
    return soundtracks


def step3_collect_audio_files(soundtracks: list[dict], steamapps_dir: Path) -> list[dict]:
    """各サウンドトラックの音源ファイルを収集して表示。

    steamapps/music/ → steamapps/common/ の順でディレクトリを探索。
    music/ 内にフォーマット別サブディレクトリが存在する場合は最優先フォーマットを選択。
    """
    print(_head(f"\n{'='*60}"))
    print(_head(" Step 3: 音源ファイルの収集"))
    print(_head(f"{'='*60}\n"))

    print(f"  対応拡張子 : {', '.join(sorted(AUDIO_EXTENSIONS))}")
    print(f"  フォーマット優先順位: {' > '.join(FORMAT_PRIORITY)}\n")

    results: list[dict] = []
    total_files = 0
    missing_dirs = 0

    for idx, st in enumerate(soundtracks, start=1):
        install_path, location = _resolve_install_path(steamapps_dir, st["install_dir"])

        print(f"  [{idx}/{len(soundtracks)}] {st['name']}  (app_id={st['app_id']})")
        print(f"    installdir  : {st['install_dir']}")

        if install_path is None:
            print(_err(f"    {_SYM_ERR}ディレクトリが存在しません（common/ も music/ も未発見）"))
            missing_dirs += 1
            print()
            continue

        print(f"    場所        : steamapps/{location}/")
        print(f"    パス        : {install_path}")

        # --- フォーマット別サブディレクトリ検出 ---
        format_dirs = _detect_format_subdirs(install_path)
        format_dir: str | None = None
        audio_dir = install_path

        if format_dirs:
            # 検出されたフォーマットとパスを表示
            fmt_list = ", ".join(f"{k} ({v.name})" for k, v in format_dirs.items())
            print(f"    フォーマットディレクトリ: {fmt_list}")
            # 優先フォーマット選択
            for fmt in FORMAT_PRIORITY:
                if fmt in format_dirs:
                    format_dir = format_dirs[fmt].name
                    audio_dir = format_dirs[fmt]
                    print(_ok(f"    {_SYM_OK}選択フォーマット: {fmt}  ({format_dir})"))
                    break

        audio_files = _find_audio_files(audio_dir)

        if not audio_files:
            all_files = [f for f in install_path.rglob("*") if f.is_file()]
            exts = sorted({f.suffix.lower() for f in all_files if f.suffix})
            print(_warn(f"    {_SYM_WARN}音源ファイルなし（全ファイル数={len(all_files)}、拡張子={', '.join(exts[:8])}）"))
            if exts:
                print(f"    　※ OST がゲームエンジン内にパックされている場合は収集対象外")
        else:
            print(_ok(f"    {_SYM_OK}音源ファイル数 : {len(audio_files)}"))
            for f in audio_files[:5]:
                rel = Path(f).relative_to(audio_dir)
                size_kb = Path(f).stat().st_size / 1024
                print(f"      {_C['DIM']}{rel}{_C['RESET']}  ({size_kb:,.0f} KB)")
            if len(audio_files) > 5:
                print(f"      {_C['DIM']}... 他 {len(audio_files) - 5} 件{_C['RESET']}")
            total_files += len(audio_files)

        print()

        results.append({
            "app_id":         st["app_id"],
            "name":           st["name"],
            "location":       location,
            "install_path":   str(install_path),
            "format_dir":     format_dir,
            "audio_dir":      str(audio_dir),
            "audio_files":    audio_files,
            "audio_count":    len(audio_files),
        })

    print(f"  -- Step 3 完了: 処理={len(results)}件  合計音源={total_files}ファイル  "
          f"ディレクトリ不在={missing_dirs}件 --")
    return results


# ---------------------------------------------------------------------------
# サマリ表示
# ---------------------------------------------------------------------------

def print_summary(step1_total: int, soundtracks: list[dict], audio_results: list[dict]) -> None:
    print(_head(f"\n{'='*60}"))
    print(_head(" 最終サマリ"))
    print(_head(f"{'='*60}"))
    total_audio = sum(r["audio_count"] for r in audio_results)
    print(f"  検査した ACF 総数       : {step1_total}")
    print(f"  サウンドトラック数       : {len(soundtracks)}")
    print(f"  音源ファイル合計         : {total_audio}")

    if audio_results:
        print(f"\n  {'AppID':>10}  {'音源数':>6}  名前")
        print(f"  {_SYM_BAR*10}  {_SYM_BAR*6}  {_SYM_BAR*40}")
        for r in audio_results:
            mark = _ok(f"{r['audio_count']:>6}") if r["audio_count"] > 0 else _warn(f"{r['audio_count']:>6}")
            print(f"  {r['app_id']:>10}  {mark}  {r['name']}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Steam ライブラリ検査スクリプト（本番 .env 対応）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--steam-library",
        metavar="PATH",
        help="Steam ライブラリパス (STEAM_LIBRARY_PATH env または .env から自動取得)",
    )
    p.add_argument(
        "--max",
        type=int,
        metavar="N",
        help="Step 1 で処理する ACF ファイルの最大件数",
    )
    p.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        help="指定ステップまで実行して停止 (省略時: 全ステップ実行)",
    )
    p.add_argument(
        "--output-json",
        metavar="FILE",
        help="サマリ結果を JSON ファイルに出力",
    )
    p.add_argument(
        "--app-id",
        type=int,
        metavar="APPID",
        help="指定 AppID のみ処理（複数指定不可）",
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()

    steam_library = (
        args.steam_library
        or os.getenv("STEAM_LIBRARY_PATH")
    )
    if not steam_library:
        print(_err("エラー: STEAM_LIBRARY_PATH が設定されていません。"))
        print("  --steam-library オプション、または scout/.env の STEAM_LIBRARY_PATH を設定してください。")
        return 1

    steam_library = steam_library.strip('"').strip("'")
    root = Path(steam_library)
    steamapps_dir = root / "steamapps"

    if not steamapps_dir.is_dir():
        print(_err(f"エラー: steamapps ディレクトリが見つかりません: {steamapps_dir}"))
        return 1

    stop_at = args.step or 3

    # ── Step 1 ──
    records = step1_inspect_acf(
        steamapps_dir,
        max_count=args.max,
        app_id=args.app_id,
    )
    if stop_at == 1 or not records:
        return 0

    # ── Step 2 ──
    soundtracks = step2_filter_soundtracks(records)
    if stop_at == 2 or not soundtracks:
        return 0

    # AppID フィルタ（--app-id が指定された場合）
    if args.app_id is not None:
        soundtracks = [s for s in soundtracks if s["app_id"] == args.app_id]
        if not soundtracks:
            print(_warn(f"AppID {args.app_id} はサウンドトラック一覧内に見つかりませんでした。"))
            return 1

    # ── Step 3 ──
    audio_results = step3_collect_audio_files(soundtracks, steamapps_dir)

    print_summary(len(records), soundtracks, audio_results)

    if args.output_json:
        import json
        summary = {
            "steam_library": steam_library,
            "acf_total": len(records),
            "soundtrack_count": len(soundtracks),
            "results": [
                {
                    "app_id":       r["app_id"],
                    "name":         r["name"],
                    "location":     r.get("location"),
                    "install_path": r["install_path"],
                    "format_dir":   r.get("format_dir"),
                    "audio_dir":    r.get("audio_dir", r["install_path"]),
                    "audio_count":  r["audio_count"],
                    "audio_files":  r["audio_files"],
                }
                for r in audio_results
            ],
        }
        Path(args.output_json).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON 出力: {args.output_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any
from urllib.parse import quote


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")


PLATFORM_ALIASES = {
    "boss": ["boss", "boss直聘", "BOSS直聘", "直聘", "zhipin"],
    "liepin": ["猎聘", "liepin"],
    "zhilian": ["智联", "智联招聘", "zhaopin"],
}


def load_config() -> dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def detect_platforms(text: str, config: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for key, aliases in PLATFORM_ALIASES.items():
        if any(alias.lower() in text.lower() for alias in aliases):
            found.append(key)
    if any(word in text for word in ["同时", "一起", "多平台", "全平台"]) and not found:
        return list(config.get("platforms", {}).get("enabled") or ["boss", "liepin", "zhilian"])
    if not found:
        default = config.get("platforms", {}).get("default") or "boss"
        found.append(default)
    return found


def extract_field(text: str, labels: list[str]) -> str:
    joined = "|".join(re.escape(label) for label in labels)
    patterns = [
        rf"(?:{joined})[:：]\s*([^\s,，。；;]+)",
        rf"(?:投递|搜索|岗位)[\s:：]*([^\s,，。；;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def build_search_url(platform: str, keyword: str, city: str, config: dict[str, Any]) -> str:
    platforms = config.get("platforms", {})
    base = platforms.get(platform, {}).get("base_url", "")
    encoded = quote(keyword or config.get("search_params", {}).get("keyword") or "")
    if platform == "boss":
        city_code = config.get("search_params", {}).get("city_code") or ""
        return f"{base}/web/geek/job?query={encoded}&city={city_code}" if encoded else f"{base}/web/geek/job"
    if platform == "liepin":
        return f"{base}/zhaopin/?key={encoded}" if encoded else base
    if platform == "zhilian":
        return f"{base}/sou/jl0/kw{encoded}" if encoded else base
    return base


def plan(prompt: str) -> dict[str, Any]:
    config = load_config()
    search_params = config.get("search_params", {})
    platforms = detect_platforms(prompt, config)
    keyword = extract_field(prompt, ["岗位", "职位", "关键词", "搜索"]) or search_params.get("keyword") or ""
    city = extract_field(prompt, ["城市", "地点", "地区"]) or search_params.get("city_name") or ""

    tasks = []
    runtime_key = "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "default"
    for idx, platform in enumerate(platforms):
        meta = config.get("platforms", {}).get(platform, {})
        runners = meta.get("runners") or {}
        selected_runner = runners.get(runtime_key) or runners.get("default") or meta.get("runner", "")
        city_code = meta.get("city_code") or (search_params.get("city_code") if platform == "boss" else "")
        tasks.append(
            {
                "platform": platform,
                "display_name": meta.get("display_name", platform),
                "status": meta.get("status", "planned"),
                "workflow": meta.get("workflow", ""),
                "browser": meta.get("browser", ""),
                "runner": selected_runner,
                "runtime": runtime_key,
                "city_code": city_code,
                "open_url": build_search_url(platform, keyword, city, config),
                "execution_order": idx + 1,
            }
        )
    return {
        "ok": True,
        "keyword": keyword,
        "city": city,
        "mode": "multi_platform_round_robin" if len(tasks) > 1 else "single_platform",
        "tasks": tasks,
        "rule": "多平台时先全部打开并让用户登录，再按队列轮询执行；不要并发抢同一个前台窗口。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified job application dispatcher")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("prompt", nargs="*", help="User request text")
    args = parser.parse_args()
    if args.cmd == "plan":
        print(json.dumps(plan(" ".join(args.prompt)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

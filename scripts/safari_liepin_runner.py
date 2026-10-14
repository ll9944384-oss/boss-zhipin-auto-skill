#!/usr/bin/env python3
"""Deterministic Safari runner for Liepin job-search workflows."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote, urlencode, urlparse, parse_qsl, urlunparse


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")
SAFARI_BRIDGE = os.path.join(SCRIPT_DIR, "safari_boss_bridge.applescript")
TAB_HINT = "liepin.com"


def load_config() -> dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def run_bridge(mode: str, *args: str, timeout: int = 25) -> str:
    proc = subprocess.run(
        ["osascript", SAFARI_BRIDGE, mode, *args],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def navigate(url: str) -> None:
    try:
        run_bridge("navigate", url)
    except subprocess.TimeoutExpired:
        # Safari can briefly stop answering Apple Events while restoring tabs.
        run_bridge("navigate", url, timeout=45)


def safari_js(source: str, timeout: int = 25) -> str:
    fd, js_path = tempfile.mkstemp(prefix="hermes_liepin_js_", suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(source)
        return run_bridge("js-file", js_path, TAB_HINT, timeout=timeout)
    finally:
        try:
            os.unlink(js_path)
        except OSError:
            pass


def json_js(body: str) -> dict[str, Any]:
    wrapped = f"""
    (function() {{
      try {{
        const result = (function() {{ {body} }})();
        return JSON.stringify({{ok: true, result}});
      }} catch (err) {{
        return JSON.stringify({{ok: false, error: String(err && err.stack || err)}});
      }}
    }})()
    """
    return json.loads(safari_js(wrapped))


def search_url(keyword: str) -> str:
    return f"https://www.liepin.com/zhaopin/?key={quote(keyword)}" if keyword else "https://www.liepin.com/zhaopin/"


def with_city(url: str, city_code: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["city"] = city_code
    query["dq"] = city_code
    return urlunparse(parsed._replace(query=urlencode(query)))


def city_values(args: argparse.Namespace, config: dict[str, Any]) -> tuple[str, str]:
    code = args.city_code or config.get("platforms", {}).get("liepin", {}).get("city_code", "")
    name = args.city or config.get("search_params", {}).get("city_name", "")
    return str(code), str(name)


def city_state(city_code: str, city_name: str) -> dict[str, Any]:
    return json_js(f"""
      const url = new URL(location.href);
      const code = {json.dumps(city_code)};
      const name = {json.dumps(city_name, ensure_ascii=False)};
      const city = url.searchParams.get('city') || '';
      const dq = url.searchParams.get('dq') || '';
      const visible = n => {{ const r=n.getBoundingClientRect(); return r.width>0 && r.height>0; }};
      const labels = Array.from(document.querySelectorAll('[class*="city"], [class*="location"], [class*="area"], [data-selector*="city"]'))
        .filter(visible).map(n => (n.innerText || n.textContent || '').replace(/\\s+/g,' ').trim()).filter(Boolean).slice(0,30);
      return {{url: location.href, city, dq, cityCode: code, cityName: name,
        urlMatched: !!code && (city === code || dq === code),
        labelMatched: !!name && labels.some(t => t === name || t.startsWith(name + ' ')), labels}};
    """)


def apply_city(city_code: str, city_name: str, wait: float) -> dict[str, Any]:
    if not city_code:
        return {"ok": False, "status": "city_selection_failed", "reason": "missing_liepin_city_code"}
    current = json_js("return {url: location.href};")
    current_url = current.get("result", {}).get("url", "")
    if "/zhaopin/" not in current_url:
        return {"ok": False, "status": "city_selection_failed", "reason": "not_on_liepin_search_page", "url": current_url}
    target = with_city(current_url, city_code)
    navigate(target)
    time.sleep(wait)
    state = city_state(city_code, city_name)
    result = state.get("result", {})
    ok = bool(state.get("ok") and (result.get("urlMatched") or result.get("labelMatched")))
    return {"ok": ok, "status": "city_verified" if ok else "city_selection_failed", "method": "safari_navigation", "target": target, "state": result}


def extract_cards_value() -> dict[str, Any]:
    return json_js(r"""
      const normalize = t => String(t || '').replace(/\s+/g,' ').trim();
      const anchors = Array.from(document.querySelectorAll('a[href]'));
      const seen = new Set(); const cards = [];
      for (const a of anchors) {
        const href = a.href || ''; const title = normalize(a.innerText || a.textContent);
        if (!/liepin\.com\/(?:a\/)?job\//.test(href) && !/\/job\/\d+/.test(href)) continue;
        if (!title || title.length < 2 || title.length > 80) continue;
        const box = a.closest('[class*="job"], [class*="card"], li, article, section, div') || a.parentElement;
        const text = normalize(box ? box.innerText : title);
        const key = href + '|' + title; if (seen.has(key)) continue; seen.add(key);
        cards.push({idx: cards.length, title, url: href, text: text.slice(0,500)});
        if (cards.length >= 30) break;
      }
      return {url: location.href, count: cards.length, cards};
    """)


def filtered_cards_value() -> dict[str, Any]:
    state = extract_cards_value()
    if not state.get("ok"):
        return state
    result = state.get("result", {})
    city_name = str(load_config().get("search_params", {}).get("city_name", "")).strip()
    cards = result.get("cards", [])
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for card in cards:
        text = str(card.get("text") or card.get("title") or "")
        match = re.search(r"【\s*([^】\-\s]+)", text)
        actual_city = match.group(1) if match else ""
        item = dict(card)
        item["actualCity"] = actual_city
        item["cityMatched"] = not city_name or not actual_city or actual_city == city_name
        (accepted if item["cityMatched"] else rejected).append(item)
    for idx, card in enumerate(accepted):
        card["idx"] = idx
    result["rawCount"] = len(cards)
    result["count"] = len(accepted)
    result["cards"] = accepted
    result["filteredOutOfCity"] = [{"title": x.get("title"), "actualCity": x.get("actualCity")} for x in rejected]
    return state


def extract_detail_value() -> dict[str, Any]:
    return json_js(r"""
      const n = t => String(t || '').replace(/\s+/g,' ').trim();
      const body = document.body.innerText || ''; const text = n(body);
      const rawTitle = n((document.querySelector('h1, [class*="job-title"], [class*="title"]') || {}).textContent);
      const company = n((document.querySelector('[class*="company"] a, [class*="company"], a[href*="/company/"]') || {}).textContent);
      const jd = document.querySelector('[class*="job-intro"], [class*="job-desc"], [class*="description"], [class*="require"]');
      return {url: location.href, title: rawTitle, company, jdText: n(jd ? jd.innerText : text).slice(0,5000),
        text: text.slice(0,6000), loginNeeded: /登录|验证码|扫码/.test(body) && !/职位描述|岗位职责|任职要求/.test(body)};
    """)


def build_greeting(detail: dict[str, Any], config: dict[str, Any]) -> str:
    profile = config.get("user_profile", {})
    title = detail.get("title") or profile.get("target_role") or "这个岗位"
    company = detail.get("company") or "贵公司"
    skills = profile.get("skills") or profile.get("transferable_skills") or ["沟通理解", "信息整理", "项目推进"]
    skill_text = "、".join(str(x) for x in skills[:4])
    text = f"您好，看到{company}在招聘{title}，我认真看了岗位要求。我的{skill_text}等能力与这个岗位较匹配，做事会先对齐目标和交付标准，再按优先级推进。希望有机会进一步沟通。"
    return text[: int(config.get("greeting_rules", {}).get("max_chars", 220))]


def cmd_open_search(args: argparse.Namespace) -> None:
    config = load_config(); keyword = args.keyword or config.get("search_params", {}).get("keyword", "")
    navigate(search_url(keyword)); time.sleep(args.wait)
    code, name = city_values(args, config); city = apply_city(code, name, args.wait)
    emit({"ok": city["ok"], "status": "opened" if city["ok"] else city["status"], "platform": "liepin", "browser": "Safari", "keyword": keyword, "city": city})


def cmd_set_city(args: argparse.Namespace) -> None:
    config = load_config(); code, name = city_values(args, config); emit(apply_city(code, name, args.wait))


def cmd_extract_cards(_: argparse.Namespace) -> None:
    emit(filtered_cards_value())


def cmd_open_detail(args: argparse.Namespace) -> None:
    cards = filtered_cards_value(); items = cards.get("result", {}).get("cards", [])
    if args.index < 0 or args.index >= len(items):
        emit({"ok": False, "status": "card_index_not_found", "index": args.index}); return
    navigate(items[args.index]["url"]); time.sleep(args.wait)
    emit({"ok": True, "status": "detail_opened", "target": items[args.index], "detail": extract_detail_value()})


def cmd_extract_detail(_: argparse.Namespace) -> None:
    emit(extract_detail_value())


def cmd_generate_greeting(_: argparse.Namespace) -> None:
    detail_state = extract_detail_value(); detail = detail_state.get("result", {})
    emit({"ok": detail_state.get("ok", False), "greeting": build_greeting(detail, load_config()), "detail": detail})


def cmd_apply_current_job(args: argparse.Namespace) -> None:
    config = load_config(); detail_state = extract_detail_value(); detail = detail_state.get("result", {})
    if detail.get("loginNeeded"):
        emit({"ok": False, "status": "login_or_verification_required", "detail": detail}); return
    greeting = args.greeting or build_greeting(detail, config)
    action = json_js(f"""
      const visible = n => {{ const r=n.getBoundingClientRect(); return r.width>0 && r.height>0; }};
      const text = n => (n.innerText || n.textContent || '').replace(/\\s+/g,' ').trim();
      const nodes = Array.from(document.querySelectorAll('button,a,[role="button"],span,div')).filter(visible);
      const chat = nodes.find(n => /^(继续聊|聊一聊|沟通|联系TA|立即沟通)$/.test(text(n)));
      if (!chat) return {{ok:false,status:'chat_button_not_found'}};
      chat.click(); return {{ok:true,status:'chat_clicked',text:text(chat)}};
    """)
    time.sleep(args.wait)
    send = json_js(f"""
      const visible = n => {{ const r=n.getBoundingClientRect(); return r.width>0 && r.height>0; }};
      const modal = Array.from(document.querySelectorAll('.select-resume-modal-container,[role="dialog"],[class*="modal"]')).find(visible);
      if (modal) {{
        const b=Array.from(modal.querySelectorAll('button,[role="button"]')).find(n=>/立即投递|确认投递|投递|确定/.test(n.innerText||''));
        if (b) b.click();
      }}
      const input = Array.from(document.querySelectorAll('textarea.ant-im-input,textarea,[contenteditable="true"]')).find(visible);
      if (!input) return {{ok:false,status:'chat_input_not_found'}};
      input.focus();
      const value={json.dumps(greeting, ensure_ascii=False)};
      if ('value' in input) {{ input.value=value; input.dispatchEvent(new Event('input',{{bubbles:true}})); }} else {{ input.textContent=value; input.dispatchEvent(new InputEvent('input',{{bubbles:true,data:value,inputType:'insertText'}})); }}
      const button=Array.from(document.querySelectorAll('button,[role="button"]')).find(n=>visible(n)&&/发送/.test(n.innerText||''));
      if (!button) return {{ok:false,status:'send_button_not_found'}};
      button.click(); return {{ok:true,status:'greeting_sent',greeting:value}};
    """)
    time.sleep(args.wait)
    body = json_js("const t=document.body.innerText||''; return {verified:/已投递|投递成功|申请成功|简历已投递/.test(t), text:t.slice(-2500)};")
    sent = bool(send.get("ok") and send.get("result", {}).get("ok")); verified = bool(body.get("result", {}).get("verified"))
    emit({"ok": sent and verified, "status": "sent_verified" if sent and verified else "partial_needs_manual_check" if sent else "needs_manual_apply", "browser": "Safari", "detail": detail, "greeting": greeting, "steps": [{"step": "open_chat", "result": action}, {"step": "send_greeting", "result": send}, {"step": "verify", "result": body}]})


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True)
    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--city", default=""); p.add_argument("--city-code", default=""); p.add_argument("--wait", type=float, default=2.0)
    p=sub.add_parser("open-search"); p.add_argument("--keyword", default=""); common(p); p.set_defaults(func=cmd_open_search)
    p=sub.add_parser("set-city"); common(p); p.set_defaults(func=cmd_set_city)
    sub.add_parser("extract-cards").set_defaults(func=cmd_extract_cards)
    p=sub.add_parser("open-detail"); p.add_argument("--index", type=int, default=0); p.add_argument("--wait", type=float, default=2.0); p.set_defaults(func=cmd_open_detail)
    sub.add_parser("extract-detail").set_defaults(func=cmd_extract_detail)
    sub.add_parser("generate-greeting").set_defaults(func=cmd_generate_greeting)
    p=sub.add_parser("apply-current-job"); p.add_argument("--greeting", default=""); p.add_argument("--wait", type=float, default=2.0); p.set_defaults(func=cmd_apply_current_job)
    args=parser.parse_args(argv)
    try: args.func(args); return 0
    except Exception as exc: emit({"ok": False, "status": "runner_error", "browser": "Safari", "error": str(exc)}); return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

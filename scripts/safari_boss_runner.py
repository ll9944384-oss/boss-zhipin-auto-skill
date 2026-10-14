#!/usr/bin/env python3
"""
Fixed Safari runner for BOSS web workflows.

Use this instead of generating one-off AppleScript files for every action.
It returns structured JSON so Hermes can spend tokens on decisions instead of
low-level browser plumbing.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Any


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")
SAFARI_BRIDGE = os.path.join(SCRIPT_DIR, "safari_boss_bridge.applescript")


def run_bridge(mode: str, *args: str, timeout: int = 20) -> str:
    proc = subprocess.run(
        ["osascript", SAFARI_BRIDGE, mode, *args],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def safari_js(js: str, tab_hint: str = "zhipin.com", timeout: int = 20) -> str:
    fd, js_path = tempfile.mkstemp(prefix="hermes_boss_js_", suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(js)
        return run_bridge("js-file", js_path, tab_hint, timeout=timeout)
    finally:
        try:
            os.unlink(js_path)
        except OSError:
            pass


def json_js(js_body: str, tab_hint: str = "zhipin.com") -> Any:
    wrapped = f"""
    (function() {{
      try {{
        const result = (function() {{
          {js_body}
        }})();
        return JSON.stringify({{ok: true, result}});
      }} catch (err) {{
        return JSON.stringify({{ok: false, error: String(err && err.stack || err)}});
      }}
    }})()
    """
    raw = safari_js(wrapped, tab_hint=tab_hint)
    return json.loads(raw)


def cmd_tabs(_: argparse.Namespace) -> None:
    print(run_bridge("tabs"))


def cmd_navigate(args: argparse.Namespace) -> None:
    run_bridge("navigate", args.url)
    time.sleep(args.wait)
    print(json.dumps({"ok": True, "url": args.url}, ensure_ascii=False))


def cmd_extract_cards(_: argparse.Namespace) -> None:
    js = r"""
    const cards = Array.from(document.querySelectorAll('.job-card-wrap, .job-card-box')).slice(0, 30);
    const seen = new Set();
    return cards.map((card, idx) => {
      const titleEl = card.querySelector('.job-name, a[href*="/job_detail/"]');
      const href = titleEl ? titleEl.getAttribute('href') : '';
      const title = titleEl ? titleEl.textContent.trim() : '';
      const text = card.innerText.replace(/\s+/g, ' ').trim();
      const areaMatch = text.match(/杭州[·\u4e00-\u9fa5A-Za-z0-9]+/);
      const item = {
        idx, title, href,
        url: href && href.startsWith('/job_detail/') ? location.origin + href : href,
        text,
        area: areaMatch ? areaMatch[0] : ''
      };
      const fp = [item.title, item.href, item.area].join('|');
      if (!item.title || seen.has(fp)) return null;
      seen.add(fp);
      return item;
    }).filter(Boolean);
    """
    print(json.dumps(json_js(js), ensure_ascii=False))


def extract_detail_value() -> Any:
    js = r"""
    const body = document.body.innerText || '';
    const salary = (body.match(/\d+\s*-\s*\d+\s*K(?:·\d+薪)?|\d+\s*K(?:·\d+薪)?/i) || [''])[0];
    const title = (document.querySelector('.job-name, h1, .name') || {}).textContent || '';
    const company = (
      document.querySelector('.company-name, .sider-company .name, .job-detail-company .name, a[href*="/gongsi/"]')
      || {}
    ).textContent || '';
    const jdNode = document.querySelector('.job-sec-text, .detail-text, .job-detail, [class*="job-sec"]');
    const jdText = jdNode ? jdNode.innerText : body;
    return {
      url: location.href,
      title: title.trim(),
      company: company.trim(),
      salary,
      jdText: jdText.replace(/\s+/g, ' ').trim().slice(0, 4000),
      text: body.slice(0, 5000)
    };
    """
    return json_js(js)


def cmd_extract_detail(_: argparse.Namespace) -> None:
    print(json.dumps(extract_detail_value(), ensure_ascii=False))


def ensure_job_detail_page_value(wait: float = 2.0) -> dict[str, Any]:
    state = json_js(r"""
    const path = location.pathname;
    const isDetail = /\/job_detail\//.test(path);
    const isSearch = /\/web\/geek\/job/.test(path);
    if (isDetail) return {ok: true, status: 'already_detail_page', url: location.href};
    if (!isSearch) return {ok: false, status: 'not_search_or_detail_page', url: location.href, path};

    const visible = node => {
      const r = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return r.width > 80 && r.height > 40 && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const cards = Array.from(document.querySelectorAll('.job-card-wrap, .job-card-box'))
      .filter(visible)
      .map((card, idx) => {
        const titleEl = card.querySelector('.job-name, a[href*="/job_detail/"]');
        const hrefEl = card.querySelector('a[href*="/job_detail/"]') || titleEl;
        const href = hrefEl ? hrefEl.getAttribute('href') || '' : '';
        const title = titleEl ? (titleEl.textContent || '').trim() : '';
        const text = (card.innerText || '').replace(/\s+/g, ' ').trim();
        const cls = String(card.className || '');
        const r = card.getBoundingClientRect();
        const selected = /active|selected|cur|checked|focus/i.test(cls) || card.matches(':hover');
        return {idx, selected, href, title, text: text.slice(0, 240), rect: {left: r.left, top: r.top, width: r.width, height: r.height}};
      })
      .filter(card => card.href && card.title);
    const target = cards.find(card => card.selected) || cards[0];
    if (!target) return {ok: false, status: 'job_card_not_found', url: location.href, count: cards.length};
    let url = target.href;
    if (url.startsWith('/')) url = location.origin + url;
    if (/\/job_detail\//.test(url) && !/\.html(?:$|\?)/.test(url)) url = url.replace(/(?:\?.*)?$/, '.html');
    return {ok: true, status: 'detail_navigation_needed', url, target, candidates: cards.slice(0, 5)};
    """)
    result = state.get("result", {}) if state.get("ok") else {}
    if result.get("status") == "detail_navigation_needed" and result.get("url"):
        run_bridge("navigate", result["url"])
        time.sleep(wait)
        detail = extract_detail_value()
        return {"ok": True, "status": "navigated_to_detail", "target": result.get("target"), "url": result["url"], "detail": detail}
    return result if result else {"ok": False, "status": "detail_probe_failed", "probe": state}


def cmd_open_current_detail(args: argparse.Namespace) -> None:
    print(json.dumps(ensure_job_detail_page_value(wait=args.wait), ensure_ascii=False))


CONTACT_BUTTON_JS = r"""
const visible = node => {
  const r = node.getBoundingClientRect();
  const style = getComputedStyle(node);
  return r.width >= 30 && r.height >= 18 && style.visibility !== 'hidden' && style.display !== 'none';
};
const ownText = node => Array.from(node.childNodes)
  .filter(ch => ch.nodeType === Node.TEXT_NODE)
  .map(ch => ch.textContent || '')
  .join('')
  .trim();
const textOf = node => (ownText(node) || node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim();
const scoreNode = node => {
  if (!visible(node)) return null;
  const r = node.getBoundingClientRect();
  const text = textOf(node);
  const cls = String(node.className || '');
  const tag = node.tagName.toLowerCase();
  if (!/^(立即沟通|继续沟通|感兴趣)$/.test(text)) return null;
  if (/消息|在线客服|推荐|首页|职位|公司|校园/.test(text)) return null;
  if (r.width > 360 || r.height > 90) return null;
  let score = 0;
  if (tag === 'button' || tag === 'a') score += 100;
  if (/btn|button|op-btn|start|chat|沟通|sure/i.test(cls)) score += 80;
  if (r.width >= 60 && r.width <= 220) score += 30;
  if (r.height >= 28 && r.height <= 64) score += 30;
  if (text === '感兴趣') score -= 300;
  score -= Math.max(0, r.width * r.height / 10000);
  return {node, score, text, tag, className: cls, rect: {left: r.left, top: r.top, width: r.width, height: r.height}};
};
const raw = Array.from(document.querySelectorAll('button, a, [role="button"], .btn, [class*="btn"], [class*="op-btn"], [class*="chat"], span, div'));
const candidates = raw.map(scoreNode).filter(Boolean).sort((a, b) => b.score - a.score);
const best = candidates[0];
if (!best) return {found: false, reason: 'contact_button_not_found', url: location.href, title: document.title, candidates: candidates.slice(0, 8)};
const target = best.node;
target.scrollIntoView({block: 'center', inline: 'center'});
const rr = target.getBoundingClientRect();
return {
  found: true,
  text: best.text,
  tag: best.tag,
  className: best.className,
  score: best.score,
  url: location.href,
  rect: {left: rr.left, top: rr.top, width: rr.width, height: rr.height},
  candidates: candidates.slice(0, 8).map(c => ({text: c.text, tag: c.tag, className: c.className, score: c.score, rect: c.rect})),
  screen: {
    x: window.screenX, y: window.screenY,
    outerWidth: window.outerWidth, outerHeight: window.outerHeight,
    innerWidth: window.innerWidth, innerHeight: window.innerHeight
  }
};
"""


CONTACT_BUTTON_DOM_CLICK_JS = r"""
const visible = node => {
  const r = node.getBoundingClientRect();
  const style = getComputedStyle(node);
  return r.width >= 30 && r.height >= 18 && style.visibility !== 'hidden' && style.display !== 'none';
};
const ownText = node => Array.from(node.childNodes)
  .filter(ch => ch.nodeType === Node.TEXT_NODE)
  .map(ch => ch.textContent || '')
  .join('')
  .trim();
const textOf = node => (ownText(node) || node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim();
const scoreNode = node => {
  if (!visible(node)) return null;
  const r = node.getBoundingClientRect();
  const text = textOf(node);
  const cls = String(node.className || '');
  const tag = node.tagName.toLowerCase();
  if (!/^(立即沟通|继续沟通|感兴趣)$/.test(text)) return null;
  if (/消息|在线客服|推荐|首页|职位|公司|校园/.test(text)) return null;
  if (r.width > 360 || r.height > 90) return null;
  let score = 0;
  if (tag === 'button' || tag === 'a') score += 100;
  if (/btn|button|op-btn|start|chat|沟通|sure/i.test(cls)) score += 80;
  if (r.width >= 60 && r.width <= 220) score += 30;
  if (r.height >= 28 && r.height <= 64) score += 30;
  if (text === '感兴趣') score -= 300;
  score -= Math.max(0, r.width * r.height / 10000);
  return {node, score, text, tag, className: cls, rect: {left: r.left, top: r.top, width: r.width, height: r.height}};
};
const raw = Array.from(document.querySelectorAll('button, a, [role="button"], .btn, [class*="btn"], [class*="op-btn"], [class*="chat"], span, div'));
const candidates = raw.map(scoreNode).filter(Boolean).sort((a, b) => b.score - a.score);
const best = candidates[0];
if (!best) return {clicked: false, reason: 'contact_button_not_found', url: location.href, title: document.title, candidates: candidates.slice(0, 8)};
const target = best.node;
target.scrollIntoView({block: 'center', inline: 'center'});
target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
target.click();
const rr = target.getBoundingClientRect();
return {
  clicked: true,
  text: best.text,
  tag: best.tag,
  className: best.className,
  score: best.score,
  url: location.href,
  rect: {left: rr.left, top: rr.top, width: rr.width, height: rr.height},
  candidates: candidates.slice(0, 8).map(c => ({text: c.text, tag: c.tag, className: c.className, score: c.score, rect: c.rect}))
};
"""


def cmd_click_chat(_: argparse.Namespace) -> None:
    pre_state = chat_state_value()
    if pre_state.get("ok") and pre_state.get("result", {}).get("hasChatInput"):
        print(json.dumps({"clicked": True, "method": "already_in_chat", "chat_state": pre_state}, ensure_ascii=False))
        return
    dom_click = json_js(CONTACT_BUTTON_DOM_CLICK_JS)
    time.sleep(1.2)
    dom_state = chat_state_value()
    if dom_state.get("ok") and dom_state.get("result", {}).get("hasChatInput"):
        print(json.dumps({"clicked": True, "method": "dom_click", "target": dom_click, "chat_state": dom_state}, ensure_ascii=False))
        return

    found = json_js(CONTACT_BUTTON_JS)
    if not (found.get("ok") and found.get("result", {}).get("found")):
        print(json.dumps({"clicked": False, "reason": "chat_button_not_found", "dom_click": dom_click, "dom_state": dom_state, "detail": found}, ensure_ascii=False))
        return
    result = found["result"]
    clicks = []
    for point in screen_click_points(result["rect"], result["screen"]):
        if "x" not in point:
            continue
        click = click_screen_point(point["x"], point["y"], pause=1.0)
        clicks.append({"point": point, "click": click})
        state = chat_state_value()
        if state.get("ok") and state.get("result", {}).get("hasChatInput"):
            print(json.dumps({"clicked": True, "target": result, "clicks": clicks, "chat_state": state}, ensure_ascii=False))
            return
    print(json.dumps({"clicked": False, "reason": "click_did_not_open_chat", "dom_click": dom_click, "dom_state": dom_state, "target": result, "clicks": clicks}, ensure_ascii=False))


def click_screen_point(x: int, y: int, pause: float = 0.6) -> dict[str, Any]:
    try:
        import pyautogui
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"pyautogui_unavailable: {exc}", "click": {"x": x, "y": y}}
    try:
        pyautogui.FAILSAFE = False
        pyautogui.click(x, y)
        time.sleep(pause)
        return {"ok": True, "click": {"x": x, "y": y}}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc), "click": {"x": x, "y": y}}


def screen_click_points(rect: dict[str, Any], screen: dict[str, Any]) -> list[dict[str, Any]]:
    chrome_left = max((screen.get("outerWidth", 0) - screen.get("innerWidth", 0)) / 2, 0)
    chrome_top = max(screen.get("outerHeight", 0) - screen.get("innerHeight", 0) - chrome_left, 70)
    js_x = int(screen.get("x", 0) + chrome_left + rect["left"] + rect["width"] / 2)
    js_y = int(screen.get("y", 0) + chrome_top + rect["top"] + rect["height"] / 2)
    points = [{"method": "js_screen", "x": js_x, "y": js_y}]
    try:
        bounds = safari_bounds()
        toolbar_top = max(bounds["height"] - screen.get("innerHeight", 0), 70)
        points.insert(0, {
            "method": "safari_bounds",
            "x": int(bounds["left"] + rect["left"] + rect["width"] / 2),
            "y": int(bounds["top"] + toolbar_top + rect["top"] + rect["height"] / 2),
            "bounds": bounds,
        })
    except Exception as exc:  # noqa: BLE001
        points.append({"method": "bounds_unavailable", "error": str(exc), "x": js_x, "y": js_y})
    return points


def click_contact_button_value(wait: float = 1.8) -> dict[str, Any]:
    dom_click = json_js(CONTACT_BUTTON_DOM_CLICK_JS)
    time.sleep(wait)
    state_after_dom_click = chat_state_value()
    if state_after_dom_click.get("ok") and state_after_dom_click.get("result", {}).get("hasChatInput"):
        return {"ok": True, "domClick": dom_click, "stateAfterDomClick": state_after_dom_click, "nativeClicks": []}

    probe = json_js(CONTACT_BUTTON_JS)
    result = {"domClick": dom_click, "stateAfterDomClick": state_after_dom_click, "probe": probe, "nativeClicks": []}
    if not (probe.get("ok") and probe.get("result", {}).get("found")):
        return {"ok": False, **result}
    rect = probe["result"]["rect"]
    screen = probe["result"]["screen"]
    for point in screen_click_points(rect, screen):
        if "x" not in point:
            continue
        click = click_screen_point(point["x"], point["y"], pause=wait)
        result["nativeClicks"].append({"point": point, "click": click})
        state = chat_state_value()
        result["stateAfterNativeClick"] = state
        if state.get("ok") and state.get("result", {}).get("hasChatInput"):
            return {"ok": True, **result}
    return {"ok": False, **result}


def open_recent_chat_value(wait: float = 2.0) -> dict[str, Any]:
    current_state = chat_state_value()
    steps = [{"step": "initial_chat_state", "result": current_state}]
    if current_state.get("ok") and current_state.get("result", {}).get("hasChatInput"):
        return {"ok": True, "steps": steps}

    run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
    time.sleep(wait)
    after_nav = chat_state_value()
    steps.append({"step": "navigate_chat", "result": after_nav})
    if after_nav.get("ok") and after_nav.get("result", {}).get("hasChatInput"):
        return {"ok": True, "steps": steps}

    click = json_js(r"""
    const visible = node => {
      const r = node.getBoundingClientRect();
      return r.width > 50 && r.height > 20;
    };
    const candidates = Array.from(document.querySelectorAll(
      '.chat-list li, .friend-list li, .conversation-list li, [class*="chat"] [class*="item"], [class*="conversation"] [class*="item"], a[href*="/web/geek/chat"]'
    )).filter(visible).filter(n => {
      const text = (n.innerText || '').trim();
      return text && !/消息|客服|首页|职位|公司|校园/.test(text);
    });
    const target = candidates[0];
    if (!target) return {clicked: false, reason: 'recent_chat_item_not_found', url: location.href, count: candidates.length};
    const r = target.getBoundingClientRect();
    target.click();
    return {clicked: true, text: (target.innerText || '').trim().slice(0, 200), rect: {left: r.left, top: r.top, width: r.width, height: r.height}, count: candidates.length};
    """)
    steps.append({"step": "click_recent_chat", "result": click})
    time.sleep(wait)
    final_state = chat_state_value()
    steps.append({"step": "final_chat_state", "result": final_state})
    return {"ok": bool(final_state.get("ok") and final_state.get("result", {}).get("hasChatInput")), "steps": steps}


def chat_state_value() -> Any:
    js = r"""
    const inputs = Array.from(document.querySelectorAll(
      'div.chat-input[contenteditable="true"], div.chat-input[contenteditable], textarea.input-area'
    ));
    const visibleInputs = inputs.filter(input => {
      const r = input.getBoundingClientRect();
      return r.width > 20 && r.height > 10;
    });
    const controls = Array.from(document.querySelectorAll('.chat-controls, [class*="chat-controls"], [class*="toolbar"]'))
      .filter(n => {
        const r = n.getBoundingClientRect();
        return r.width > 20 && r.height > 10;
      });
    return {
      url: location.href,
      pathname: location.pathname,
      isJobsSearchPage: /\/web\/geek\/jobs/.test(location.pathname),
      isChatPage: /\/web\/geek\/chat/.test(location.pathname),
      hasChatInput: visibleInputs.length > 0,
      hasChatControls: controls.length > 0,
      inputCount: visibleInputs.length,
      inputInfo: visibleInputs.slice(0, 3).map(input => ({
        tag: input.tagName,
        className: String(input.className || ''),
        placeholder: input.getAttribute('placeholder') || '',
        text: (input.innerText || input.value || '').slice(0, 80)
      })),
      title: document.title
    };
    """
    return json_js(js)


def send_text_value(text: str) -> Any:
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    js = f"""
    const text = new TextDecoder().decode(Uint8Array.from(atob('{encoded}'), c => c.charCodeAt(0)));
    const input = Array.from(document.querySelectorAll(
      'div.chat-input[contenteditable="true"], div.chat-input[contenteditable], textarea.input-area'
    )).find(el => {{
      const r = el.getBoundingClientRect();
      return r.width > 20 && r.height > 10;
    }});
    if (!input) return {{
      sent: false,
      reason: 'not_in_chat_context',
      url: location.href,
      pathname: location.pathname,
      title: document.title
    }};
    input.focus();
    if (input.isContentEditable) {{
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, text);
      input.dispatchEvent(new InputEvent('input', {{bubbles: true, inputType: 'insertText', data: text}}));
    }} else {{
      input.value = text;
      input.dispatchEvent(new Event('input', {{bubbles: true}}));
    }}
    const isVisible = node => {{
      const r = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return r.width > 10 && r.height > 10 && style.visibility !== 'hidden' && style.display !== 'none';
    }};
    const buttons = Array.from(document.querySelectorAll('button, div, span, [role="button"]')).filter(isVisible);
    const send = buttons.find(b => {{
      const txt = (b.innerText || b.textContent || '').trim();
      const cls = String(b.className || '');
      return /^(发送|Send)$/.test(txt) && !b.disabled && !/disabled|disable/i.test(cls);
    }}) || document.querySelector('button.btn-send, button[class*="send"], [class*="btn-send"]');
    if (input.isContentEditable) {{
      input.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}}));
      input.dispatchEvent(new KeyboardEvent('keyup', {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}}));
    }}
    if (send) {{
      send.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, cancelable: true, view: window}}));
      send.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, cancelable: true, view: window}}));
      send.click();
    }}
    return {{
      sent: true,
      text,
      clickedSend: Boolean(send),
      sendButton: send ? {{
        text: (send.innerText || send.textContent || '').trim(),
        tag: send.tagName,
        className: String(send.className || '')
      }} : null
    }};
    """
    return json_js(js)


def cmd_send_text(args: argparse.Namespace) -> None:
    print(json.dumps(send_text_value(args.text), ensure_ascii=False))


def send_text_verified_value(text: str, company_marker: str) -> Any:
    """Only send if we are inside a chat whose open pane shows company_marker."""
    chat_state = chat_state_value()
    chat_result = chat_state.get("result", {}) if chat_state.get("ok") else {}
    if not chat_result.get("hasChatInput"):
        return {"ok": False, "sent": False, "reason": "not_in_chat_context", "chat_state": chat_state}
    if company_marker:
        try:
            body = safari_js("return (document.body.innerText || '');")
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "sent": False, "reason": f"body_read_failed: {exc}", "chat_state": chat_state}
        recent = (body or "")[-1500:]
        marker_ok = company_marker in recent
        if not marker_ok:
            return {
                "ok": False,
                "sent": False,
                "reason": "company_marker_not_in_open_chat",
                "marker": company_marker,
                "recentTail": recent,
                "chat_state": chat_state,
            }
    send = send_text_value(text)
    return {
        "ok": bool(send.get("ok") and send.get("result", {}).get("sent")),
        "sent": bool(send.get("result", {}).get("sent")),
        "reason": send.get("result", {}).get("reason", ""),
        "marker_ok": True,
        "send": send,
        "chat_state": chat_state,
    }


def cmd_send_text_verified(args: argparse.Namespace) -> None:
    print(json.dumps(send_text_verified_value(args.text, args.marker), ensure_ascii=False))


def click_send_value() -> Any:
    js = r"""
    const isVisible = node => {
      const r = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return r.width > 10 && r.height > 10 && style.visibility !== 'hidden' && style.display !== 'none';
    };
    const buttons = Array.from(document.querySelectorAll('button, div, span, [role="button"]')).filter(isVisible);
    const send = buttons.find(b => {
      const txt = (b.innerText || b.textContent || '').trim();
      const cls = String(b.className || '');
      return /^(发送|Send)$/.test(txt) && !b.disabled && !/disabled|disable/i.test(cls);
    }) || document.querySelector('button.btn-send, button[class*="send"], [class*="btn-send"]');
    if (!send) return {clicked: false, reason: 'send_button_not_found'};
    send.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
    send.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
    send.click();
    return {
      clicked: true,
      text: (send.innerText || send.textContent || '').trim(),
      tag: send.tagName,
      className: String(send.className || '')
    };
    """
    return json_js(js)


def cmd_click_send(_: argparse.Namespace) -> None:
    print(json.dumps(click_send_value(), ensure_ascii=False))


def verify_message_value(contains: str) -> Any:
    encoded = base64.b64encode(contains.encode("utf-8")).decode("ascii")
    js = f"""
    const needle = new TextDecoder().decode(Uint8Array.from(atob('{encoded}'), c => c.charCodeAt(0)));
    const text = document.body.innerText || '';
    const recent = text.slice(-5000);
    return {{verified: recent.includes(needle), contains: needle, recentTail: recent.slice(-1000)}};
    """
    return json_js(js)


def cmd_verify_message(args: argparse.Namespace) -> None:
    print(json.dumps(verify_message_value(args.contains), ensure_ascii=False))


def image_marker_value() -> Any:
    js = r"""
    const text = document.body.innerText || '';
    const recent = text.slice(-8000);
    const textCount = (recent.match(/\[图片\]|图片/g) || []).length;
    const imgCount = Array.from(document.querySelectorAll('img')).filter(img => {
      const r = img.getBoundingClientRect();
      return r.width > 20 && r.height > 20;
    }).length;
    return {textCount, imgCount, total: textCount + imgCount, recentTail: recent.slice(-1000)};
    """
    return json_js(js)


def safari_bounds() -> dict[str, int]:
    raw = run_bridge("bounds")
    parts = [int(float(x.strip())) for x in raw.split(",")]
    if len(parts) != 4:
        raise RuntimeError(f"unexpected Safari bounds: {raw}")
    left, top, right, bottom = parts
    return {"left": left, "top": top, "right": right, "bottom": bottom, "width": right - left, "height": bottom - top}


def click_file_dialog_path(path: str, x: int, y: int) -> dict[str, Any]:
    try:
        import pyautogui
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"pyautogui_unavailable: {exc}"}

    try:
        pyautogui.FAILSAFE = False
        pyautogui.click(x, y)
        time.sleep(1.2)
        pyautogui.hotkey("command", "shift", "g")
        time.sleep(0.5)
        subprocess.run("pbcopy", input=path, text=True, check=False)
        pyautogui.hotkey("command", "v")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(2.5)
        pyautogui.press("enter")
        time.sleep(1.2)
        return {"ok": True, "click": {"x": x, "y": y}}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc), "click": {"x": x, "y": y}}


def set_clipboard_image(path: str) -> dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    image_types = ["JPEG picture", "PNG picture", "TIFF picture"]
    if ext in {".png"}:
        image_types = ["PNG picture", "TIFF picture", "JPEG picture"]
    elif ext in {".tif", ".tiff"}:
        image_types = ["TIFF picture", "PNG picture", "JPEG picture"]

    attempts = []
    for image_type in image_types:
        script = f"""
        on run argv
          set imagePath to item 1 of argv
          set the clipboard to (read (POSIX file imagePath) as {image_type})
          return "ok"
        end run
        """
        try:
            proc = subprocess.run(
                ["osascript", "-e", script, path],
                text=True,
                capture_output=True,
                timeout=10,
            )
            attempts.append({"type": image_type, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()})
            if proc.returncode == 0:
                return {"ok": True, "type": image_type, "attempts": attempts}
        except Exception as exc:  # noqa: BLE001
            attempts.append({"type": image_type, "error": str(exc)})
    return {"ok": False, "reason": "set_clipboard_image_failed", "attempts": attempts}


def focus_chat_input_value() -> Any:
    js = r"""
    const input = Array.from(document.querySelectorAll(
      'div.chat-input[contenteditable="true"], div.chat-input[contenteditable], textarea.input-area'
    )).find(el => {
      const r = el.getBoundingClientRect();
      return r.width > 20 && r.height > 10;
    });
    if (!input) return {focused: false, reason: 'chat_input_not_found'};
    input.focus();
    const r = input.getBoundingClientRect();
    return {
      focused: true,
      tag: input.tagName,
      className: String(input.className || ''),
      rect: {left: r.left, top: r.top, width: r.width, height: r.height}
    };
    """
    return json_js(js)


def paste_image_from_clipboard_value(path: str, wait: float = 1.5) -> dict[str, Any]:
    before = image_marker_value()
    before_total = int(before.get("result", {}).get("total", 0)) if before.get("ok") else 0
    clipboard = set_clipboard_image(path)
    if not clipboard.get("ok"):
        return {"ok": False, "status": "resume_image_manual_required", "reason": "clipboard_image_unavailable", "path": path, "clipboard": clipboard}
    focus = focus_chat_input_value()
    if not (focus.get("ok") and focus.get("result", {}).get("focused")):
        return {"ok": False, "status": "resume_image_manual_required", "reason": "chat_input_focus_failed", "path": path, "clipboard": clipboard, "focus": focus}
    paste = {}
    enter = {}
    try:
        paste_raw = run_bridge("paste", timeout=8)
        paste = {"ok": True, "raw": paste_raw}
        time.sleep(wait)
        enter_raw = run_bridge("enter", timeout=8)
        enter = {"ok": True, "raw": enter_raw}
        time.sleep(wait)
    except Exception as exc:  # noqa: BLE001
        paste = {"ok": False, "reason": str(exc)}
    after = image_marker_value()
    after_total = int(after.get("result", {}).get("total", 0)) if after.get("ok") else 0
    if after_total > before_total:
        return {
            "ok": True,
            "status": "resume_image_sent_verified",
            "method": "clipboard_paste",
            "path": path,
            "clipboard": clipboard,
            "focus": focus,
            "paste": paste,
            "enter": enter,
            "before": before,
            "after": after,
        }
    return {
        "ok": False,
        "status": "resume_image_manual_required",
        "reason": "clipboard_paste_not_verified",
        "method": "clipboard_paste",
        "path": path,
        "clipboard": clipboard,
        "focus": focus,
        "paste": paste,
        "enter": enter,
        "before": before,
        "after": after,
    }


def upload_image_value(path: str) -> Any:
    if not path:
        return {"ok": False, "status": "resume_image_skipped", "reason": "empty_path"}
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"ok": False, "status": "resume_image_manual_required", "reason": "file_not_found", "path": path}

    chat_state = chat_state_value()
    chat_result = chat_state.get("result", {}) if chat_state.get("ok") else {}
    if not chat_result.get("hasChatInput"):
        return {
            "ok": False,
            "status": "resume_image_manual_required",
            "reason": "not_in_chat_context",
            "path": path,
            "chat_state": chat_state,
        }

    clipboard_result = paste_image_from_clipboard_value(path)
    if clipboard_result.get("ok"):
        return clipboard_result

    rect_result = json_js(r"""
    const candidates = [];
    const push = (node, label) => {
      if (!node) return;
      const r = node.getBoundingClientRect();
      if (!r || r.width < 2 || r.height < 2) return;
      candidates.push({
        label,
        rect: {left: r.left, top: r.top, width: r.width, height: r.height},
        text: (node.innerText || node.title || node.getAttribute('aria-label') || '').trim(),
        tag: node.tagName,
        className: String(node.className || '')
      });
    };
    const isBadTarget = node => {
      const txt = (node.innerText || node.title || node.getAttribute('aria-label') || '').trim();
      const cls = String(node.className || '');
      return /附件简历|新增附件|在线简历|简历/.test(txt) || /attachment-resume|resume-upload|upload-login/i.test(cls);
    };
    const chatRoots = Array.from(document.querySelectorAll('.chat-controls, [class*="chat-controls"], [class*="toolbar"]'))
      .filter(n => !isBadTarget(n));
    const rootContains = node => chatRoots.some(root => root.contains(node) || node.contains(root));
    const input = Array.from(document.querySelectorAll('input[type="file"]'))
      .find(i => rootContains(i) && /image|jpeg|jpg|png|gif/i.test(i.accept || ''));
    if (input) {
      push(input.closest('.btn-sendimg, .toolbar-btn-content, [class*="sendimg"], [class*="image"], [class*="upload"]'), 'input.closest');
      push(input, 'input');
    }
    Array.from(document.querySelectorAll('.chat-controls .btn-sendimg, [class*="chat-controls"] [class*="sendimg"], [class*="toolbar"] [class*="sendimg"], [class*="toolbar"] [class*="image"], button, div, span'))
      .forEach(n => {
        if (!rootContains(n) || isBadTarget(n)) return;
        const txt = (n.innerText || n.title || n.getAttribute('aria-label') || '').trim();
        const cls = String(n.className || '');
        if (/图片|照片/.test(txt) || /sendimg|image|photo/i.test(cls)) push(n, 'candidate');
      });
    const safeCandidates = candidates.filter(c => !/附件简历|新增附件|在线简历|简历/.test(c.text) && !/attachment-resume|resume-upload|upload-login/i.test(c.className));
    const target = safeCandidates.find(c => /sendimg|image|photo/i.test(c.className) || /图片|照片/.test(c.text)) || safeCandidates[0];
    if (!target) return {found: false, reason: 'image_button_not_found'};
    return {
      found: true,
      target,
      candidates: candidates.slice(0, 8),
      screen: {
        x: window.screenX, y: window.screenY,
        outerWidth: window.outerWidth, outerHeight: window.outerHeight,
        innerWidth: window.innerWidth, innerHeight: window.innerHeight
      }
    };
    """)
    if not rect_result.get("ok") or not rect_result.get("result", {}).get("found"):
        return {"ok": False, "status": "resume_image_manual_required", "reason": "image_button_not_found", "detail": rect_result}

    result = rect_result["result"]
    rect = result["target"]["rect"]
    screen = result["screen"]
    chrome_left = max((screen.get("outerWidth", 0) - screen.get("innerWidth", 0)) / 2, 0)
    chrome_top = max(screen.get("outerHeight", 0) - screen.get("innerHeight", 0) - chrome_left, 70)
    js_x = int(screen.get("x", 0) + chrome_left + rect["left"] + rect["width"] / 2)
    js_y = int(screen.get("y", 0) + chrome_top + rect["top"] + rect["height"] / 2)

    clicks = [{"method": "js_screen", "x": js_x, "y": js_y}]
    try:
        bounds = safari_bounds()
        toolbar_top = max(bounds["height"] - screen.get("innerHeight", 0), 70)
        clicks.insert(0, {
            "method": "safari_bounds",
            "x": int(bounds["left"] + rect["left"] + rect["width"] / 2),
            "y": int(bounds["top"] + toolbar_top + rect["top"] + rect["height"] / 2),
            "bounds": bounds,
        })
    except Exception as exc:  # noqa: BLE001
        clicks.append({"method": "bounds_unavailable", "error": str(exc), "x": js_x, "y": js_y})

    attempts = []
    before = image_marker_value()
    before_total = int(before.get("result", {}).get("total", 0)) if before.get("ok") else 0
    for click in clicks:
        if "x" not in click or "y" not in click:
            continue
        dialog = click_file_dialog_path(path, click["x"], click["y"])
        attempts.append({"click": click, "dialog": dialog})
        time.sleep(1.5)
        after = image_marker_value()
        after_total = int(after.get("result", {}).get("total", 0)) if after.get("ok") else 0
        if after_total > before_total:
            return {
                "ok": True,
                "status": "resume_image_sent_verified",
                "path": path,
                "attempts": attempts,
                "before": before,
                "after": after,
            }

    return {
        "ok": False,
        "status": "resume_image_manual_required",
        "reason": "image_not_verified_after_upload_attempt",
        "path": path,
        "attempts": attempts,
        "target": result.get("target"),
        "candidates": result.get("candidates", []),
    }


def cmd_upload_image(args: argparse.Namespace) -> None:
    print(json.dumps(upload_image_value(args.path), ensure_ascii=False))


def cmd_resume_image_only(args: argparse.Namespace) -> None:
    result = upload_image_value(args.path)
    print(json.dumps({
        "ok": bool(result.get("ok")),
        "status": "resume_image_only_sent" if result.get("ok") else "resume_image_manual_required",
        "upload_resume_image": {"result": result},
        "note": "existing chat: no greeting or portfolio was sent",
    }, ensure_ascii=False))


def chat_has_prior_intro(portfolio: str) -> dict[str, Any]:
    keys = ["pan.baidu.com", "作品集", "看到贵公司在招聘"]
    if portfolio and "pan.baidu.com" not in portfolio:
        keys.append(portfolio[:18])
    result = {}
    for key in keys:
        if not key:
            continue
        result[key] = verify_message_value(key)
    has_portfolio = any(
        k in result and result[k].get("ok") and result[k].get("result", {}).get("verified")
        for k in ("pan.baidu.com", "作品集")
    )
    has_greeting = bool(
        result.get("看到贵公司在招聘", {}).get("ok")
        and result.get("看到贵公司在招聘", {}).get("result", {}).get("verified")
    )
    return {"has_prior_intro": has_portfolio or has_greeting, "has_portfolio": has_portfolio, "has_greeting": has_greeting, "checks": result}


def load_skill_config() -> dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def compact_text(text: str, max_len: int = 160) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rstrip()
    sentence_end = max(cut.rfind("。"), cut.rfind("！"), cut.rfind("？"))
    if sentence_end >= max_len * 0.65:
        return cut[: sentence_end + 1]
    comma_end = max(cut.rfind("，"), cut.rfind("；"))
    if comma_end >= max_len * 0.65:
        return cut[:comma_end].rstrip("，；") + "。"
    return cut.rstrip("，；、 ") + "。"


def normalize_terms(items: Any) -> list[str]:
    if not items:
        return []
    if isinstance(items, str):
        items = re.split(r"[、,，/|\n]+", items)
    return [str(item).strip() for item in items if str(item).strip()]


def term_in_text(term: str, text: str) -> bool:
    return bool(term and term.lower() in text.lower())


def configured_aliases(config: dict[str, Any], key: str) -> list[tuple[str, list[str]]]:
    aliases = []
    for item in (config.get("greeting_rules", {}).get(key) or []):
        label = str(item.get("label", "")).strip()
        words = normalize_terms(item.get("aliases"))
        if label:
            aliases.append((label, words + [label]))
    return aliases


def pick_jd_matches(jd_text: str, profile: dict[str, Any]) -> dict[str, list[str]]:
    config = load_skill_config()
    jd = jd_text or ""
    matched_skills: list[str] = []
    matched_needs: list[str] = []
    matched_profile: list[str] = []

    alias_groups = configured_aliases(config, "universal_skill_aliases")
    alias_groups += [(skill, [skill]) for skill in normalize_terms(profile.get("skills"))]
    alias_groups += [(kw, [kw]) for kw in normalize_terms(profile.get("industry_keywords"))]

    for label, aliases in alias_groups:
        if any(term_in_text(alias, jd) for alias in aliases) and label not in matched_skills:
            matched_skills.append(label)

    for label, aliases in configured_aliases(config, "universal_need_aliases"):
        if any(term_in_text(alias, jd) for alias in aliases) and label not in matched_needs:
            matched_needs.append(label)

    for item in normalize_terms(profile.get("experience_highlights")) + normalize_terms(profile.get("transferable_skills")):
        if term_in_text(item, jd) and item not in matched_profile:
            matched_profile.append(item)

    if not matched_skills:
        matched_skills = normalize_terms(profile.get("skills"))[:3]
    if not matched_profile:
        matched_profile = normalize_terms(profile.get("strengths"))[:3] or normalize_terms(profile.get("transferable_skills"))[:3]

    return {
        "skills": matched_skills[:4],
        "projects": matched_skills[:4],
        "focus": matched_needs[:4],
        "profile": matched_profile[:4],
    }


def choose_greeting_angle(jd_text: str, projects: list[str], focus: list[str]) -> dict[str, str]:
    project_text = "、".join(projects[:3]) if projects else "岗位要求"
    focus_text = "、".join(focus[:3]) if focus else "执行质量、沟通配合和结果落地"
    return {
        "project": project_text,
        "need": f"我理解这个岗位核心不是简单完成动作，而是把{focus_text}真正做好",
        "response": "我做事会先对齐业务目标和交付标准，再把信息拆清楚、按优先级推进，过程中及时反馈关键进展",
    }


def skill_display_name(skill: str) -> str:
    normalized = skill.lower()
    if "premiere" in normalized:
        return "PR"
    if "after effects" in normalized:
        return "AE"
    if "davinci" in normalized or "resolve" in normalized or "达芬奇" in skill:
        return "达芬奇"
    if "photoshop" in normalized:
        return "PS"
    if "illustrator" in normalized:
        return "AI"
    if "final cut" in normalized:
        return "Final Cut Pro"
    return skill


def core_skill_text(matched_skills: list[str], profile: dict[str, Any]) -> str:
    combined: list[str] = []
    fallback = normalize_terms(profile.get("skills")) + normalize_terms(profile.get("transferable_skills"))
    for skill in matched_skills + fallback:
        label = skill_display_name(skill)
        if label and label not in combined:
            combined.append(label)
    return "、".join(combined[:4]) or "沟通理解、信息整理、执行推进、复盘优化"


def build_greeting(job_title: str, company: str, profile: dict[str, Any], jd_text: str = "", portfolio: str = "") -> str:
    config = load_skill_config()
    max_chars = int(config.get("greeting_rules", {}).get("max_chars") or 170)
    title = job_title.strip() or profile.get("job_title") or profile.get("target_role") or "这个岗位"
    company_label = company.strip() or "贵公司"
    matches = pick_jd_matches(jd_text, profile)
    skill_text = core_skill_text(matches["skills"], profile)
    angle = choose_greeting_angle(jd_text, matches["projects"], matches["focus"])
    profile_hits = "、".join(matches.get("profile", [])[:3])
    focus_hint = f"JD里提到的{'、'.join(matches['focus'][:3])}我会重点兼顾。" if matches["focus"] else ""
    profile_hint = f"我这边能匹配的是{skill_text}，优势在{profile_hits}。" if profile_hits else f"我这边能匹配的是{skill_text}。"
    greeting = (
        f"您好，看到{company_label}在招聘{title}，我认真看了JD，重点应该在{angle['project']}。"
        f"{angle['need']}。{profile_hint}"
        f"{angle['response']}。{focus_hint}"
        "如果需要一个能快速理解业务、把事情推进到结果的人，希望有机会进一步沟通。"
    )
    forbidden_claims = ["在线简历已发送", "简历已发送", "已发送在线简历", "作品集可随时查看"]
    for claim in forbidden_claims:
        greeting = greeting.replace(claim, "")
    return compact_text(greeting, max_chars)


def cmd_quick_apply(args: argparse.Namespace) -> None:
    config = load_skill_config()
    profile = config.get("user_profile", {})
    portfolio = args.portfolio.strip() or profile.get("portfolio_link", "")
    resume_image = args.resume_image.strip() or profile.get("resume_image", "")
    detail = extract_detail_value()
    detail_result = detail.get("result", {}) if detail.get("ok") else {}
    jd_text = detail_result.get("jdText") or detail_result.get("text") or ""
    job_title = args.job_title or detail_result.get("title", "")
    company = args.company or detail_result.get("company", "")
    greeting = build_greeting(job_title, company, profile, jd_text, portfolio)
    bundle_args = argparse.Namespace(
        greeting=greeting,
        portfolio=portfolio,
        resume_image=resume_image,
        greeting_verify=args.greeting_verify or "看到贵公司在招聘",
        portfolio_verify=args.portfolio_verify or ("pan.baidu.com" if "pan.baidu.com" in portfolio else portfolio[:18]),
        wait=args.wait,
        ensure_chat=True,
        separate_portfolio=True,
    )
    cmd_send_bundle(bundle_args)


def cmd_smart_apply(args: argparse.Namespace) -> None:
    config = load_skill_config()
    profile = config.get("user_profile", {})
    portfolio = args.portfolio.strip() or profile.get("portfolio_link", "")
    resume_image = args.resume_image.strip() or profile.get("resume_image", "")
    chat_state = chat_state_value()
    if not (chat_state.get("ok") and chat_state.get("result", {}).get("hasChatInput")):
        print(json.dumps({
            "ok": False,
            "status": "needs_manual_check",
            "reason": "not_in_chat_context",
            "chat_state": chat_state,
        }, ensure_ascii=False))
        return
    prior = chat_has_prior_intro(portfolio)
    if prior["has_prior_intro"]:
        image_result = upload_image_value(resume_image)
        print(json.dumps({
            "ok": bool(image_result.get("ok")),
            "status": "resume_image_only_sent" if image_result.get("ok") else "resume_image_manual_required",
            "mode": "resume_image_only_existing_chat",
            "prior_chat": prior,
            "upload_resume_image": {"result": image_result},
        }, ensure_ascii=False))
        return
    detail = extract_detail_value()
    detail_result = detail.get("result", {}) if detail.get("ok") else {}
    jd_text = detail_result.get("jdText") or detail_result.get("text") or ""
    job_title = args.job_title or detail_result.get("title", "")
    company = args.company or detail_result.get("company", "")
    greeting = build_greeting(job_title, company, profile, jd_text, portfolio)
    bundle_args = argparse.Namespace(
        greeting=greeting,
        portfolio=portfolio,
        resume_image=resume_image,
        greeting_verify=args.greeting_verify or "看到贵公司在招聘",
        portfolio_verify=args.portfolio_verify or ("pan.baidu.com" if "pan.baidu.com" in portfolio else portfolio[:18]),
        wait=args.wait,
        ensure_chat=True,
        separate_portfolio=True,
    )
    cmd_send_bundle(bundle_args)


def cmd_apply_current_job(args: argparse.Namespace) -> None:
    steps: list[dict[str, Any]] = []
    initial_state = chat_state_value()
    steps.append({"step": "initial_chat_state", "result": initial_state})
    detail_page = ensure_job_detail_page_value(wait=args.wait)
    steps.append({"step": "ensure_job_detail_page", "result": detail_page})
    detail_before_chat = extract_detail_value()
    steps.append({"step": "extract_job_detail_for_greeting", "result": detail_before_chat})

    if not (initial_state.get("ok") and initial_state.get("result", {}).get("hasChatInput")):
        contact = click_contact_button_value(wait=args.wait)
        steps.append({"step": "click_contact_button", "result": contact})
        state_after_contact = chat_state_value()
        steps.append({"step": "state_after_contact", "result": state_after_contact})
        if not (state_after_contact.get("ok") and state_after_contact.get("result", {}).get("hasChatInput")):
            recent = open_recent_chat_value(wait=args.wait)
            steps.append({"step": "open_recent_chat", "result": recent})

    final_state = chat_state_value()
    steps.append({"step": "final_chat_state_before_apply", "result": final_state})
    if not (final_state.get("ok") and final_state.get("result", {}).get("hasChatInput")):
        print(json.dumps({
            "ok": False,
            "status": "needs_manual_check",
            "reason": "could_not_enter_chat_context",
            "steps": steps,
        }, ensure_ascii=False))
        return

    config = load_skill_config()
    profile = config.get("user_profile", {})
    portfolio = args.portfolio.strip() or profile.get("portfolio_link", "")
    resume_image = args.resume_image.strip() or profile.get("resume_image", "")
    prior = chat_has_prior_intro(portfolio)
    if prior["has_prior_intro"]:
        image_result = upload_image_value(resume_image)
        print(json.dumps({
            "ok": bool(image_result.get("ok")),
            "status": "resume_image_only_sent" if image_result.get("ok") else "resume_image_manual_required",
            "mode": "apply_current_job_existing_chat_resume_only",
            "prior_chat": prior,
            "upload_resume_image": {"result": image_result},
            "steps": steps,
        }, ensure_ascii=False))
        return

    detail_result = detail_before_chat.get("result", {}) if detail_before_chat.get("ok") else {}
    jd_text = detail_result.get("jdText") or detail_result.get("text") or ""
    job_title = args.job_title or detail_result.get("title", "")
    company = args.company or detail_result.get("company", "")
    greeting = build_greeting(job_title, company, profile, jd_text, portfolio)
    bundle_args = argparse.Namespace(
        greeting=greeting,
        portfolio=portfolio,
        resume_image=resume_image,
        greeting_verify=args.greeting_verify or "看到贵公司在招聘",
        portfolio_verify=args.portfolio_verify or ("pan.baidu.com" if "pan.baidu.com" in portfolio else portfolio[:18]),
        wait=args.wait,
        ensure_chat=False,
        separate_portfolio=True,
    )

    # Inline send-bundle so we can preserve entry steps in the final JSON.
    original_print = print
    try:
        import builtins
        captured: list[str] = []
        builtins.print = lambda *a, **k: captured.append(" ".join(str(x) for x in a))
        cmd_send_bundle(bundle_args)
    finally:
        builtins.print = original_print
    send_result = {}
    if captured:
        try:
            send_result = json.loads(captured[-1])
        except Exception:
            send_result = {"raw": captured[-1]}
    if isinstance(send_result, dict):
        send_result.setdefault("steps", [])
        send_result["steps"] = steps + send_result.get("steps", [])
        print(json.dumps(send_result, ensure_ascii=False))
    else:
        print(json.dumps({"ok": False, "status": "needs_manual_check", "steps": steps, "send_result": send_result}, ensure_ascii=False))


def cmd_send_bundle(args: argparse.Namespace) -> None:
    steps: list[dict[str, Any]] = []

    if args.ensure_chat:
        click = json_js(r"""
        const nodes = Array.from(document.querySelectorAll('a, button, div, span'));
        const target = nodes.find(n => /立即沟通|继续沟通|感兴趣/.test((n.innerText || '').trim()));
        if (!target) return {clicked: false, reason: 'chat_button_not_found', url: location.href};
        target.click();
        return {clicked: true, text: (target.innerText || '').trim(), url: location.href};
        """)
        steps.append({"step": "click_chat", "result": click})
        time.sleep(args.wait)
        chat_state = chat_state_value()
        steps.append({"step": "verify_chat_context", "result": chat_state})
        if not (chat_state.get("ok") and chat_state.get("result", {}).get("hasChatInput")):
            print(json.dumps({
                "ok": False,
                "status": "needs_manual_check",
                "reason": "not_in_chat_context_after_click_chat",
                "verified": {"greeting": False, "portfolio": False, "resume_image": False},
                "steps": steps,
            }, ensure_ascii=False))
            return

    bundle_text = args.greeting.strip()
    portfolio_text = args.portfolio.strip()
    portfolio_key = args.portfolio_verify or ("pan.baidu.com" if "pan.baidu.com" in portfolio_text else portfolio_text[:18])
    if portfolio_text and portfolio_key and portfolio_key not in bundle_text and not args.separate_portfolio:
        bundle_text = f"{bundle_text}\n\n{portfolio_text}"

    forbidden_claims = ["在线简历已发送", "简历已发送", "已发送在线简历", "作品集可随时查看"]
    sanitized_text = bundle_text
    for claim in forbidden_claims:
        sanitized_text = sanitized_text.replace(claim, "")

    image_result = {"ok": False, "status": "resume_image_skipped", "reason": "no_resume_image"}
    if args.resume_image:
        image_result = upload_image_value(args.resume_image)
    steps.append({"step": "upload_resume_image", "result": image_result})
    time.sleep(args.wait)
    if not image_result.get("ok"):
        print(json.dumps({
            "ok": False,
            "status": image_result.get("status") or "resume_image_manual_required",
            "reason": "resume_image_first_step_failed",
            "verified": {"greeting": False, "portfolio": False, "resume_image": False},
            "steps": steps,
        }, ensure_ascii=False))
        return

    portfolio_verify = {"ok": False, "result": {"verified": False}, "reason": "no_portfolio"}
    if args.separate_portfolio and portfolio_text:
        portfolio_result = send_text_value(portfolio_text)
        steps.append({"step": "send_portfolio_separately", "result": portfolio_result})
        time.sleep(args.wait)
        portfolio_verify = verify_message_value(portfolio_key)
        steps.append({"step": "verify_portfolio_separate", "result": portfolio_verify})

    greeting_result = send_text_value(sanitized_text)
    steps.append({"step": "send_greeting", "result": greeting_result, "text": sanitized_text})
    time.sleep(args.wait)

    greeting_key = args.greeting_verify or args.greeting[:18]
    greeting_verify = verify_message_value(greeting_key)
    steps.append({"step": "verify_greeting", "result": greeting_verify})

    greeting_ok = bool(greeting_verify.get("ok") and greeting_verify.get("result", {}).get("verified"))
    portfolio_ok = bool(portfolio_verify.get("ok") and portfolio_verify.get("result", {}).get("verified"))
    image_ok = bool(image_result.get("ok"))

    if greeting_ok and portfolio_ok and image_ok:
        status = "sent_verified"
    elif greeting_ok and portfolio_ok:
        status = "partial_sent_verified"
    else:
        status = "needs_manual_check"

    print(json.dumps({
        "ok": status in {"sent_verified", "partial_sent_verified"},
        "status": status,
        "verified": {"greeting": greeting_ok, "portfolio": portfolio_ok, "resume_image": image_ok},
        "steps": steps,
    }, ensure_ascii=False))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tabs").set_defaults(func=cmd_tabs)

    p = sub.add_parser("navigate")
    p.add_argument("url")
    p.add_argument("--wait", type=float, default=3.0)
    p.set_defaults(func=cmd_navigate)

    sub.add_parser("extract-cards").set_defaults(func=cmd_extract_cards)
    sub.add_parser("extract-detail").set_defaults(func=cmd_extract_detail)

    p = sub.add_parser("open-current-detail")
    p.add_argument("--wait", type=float, default=2.0)
    p.set_defaults(func=cmd_open_current_detail)

    sub.add_parser("click-chat").set_defaults(func=cmd_click_chat)

    p = sub.add_parser("send-text")
    p.add_argument("text")
    p.set_defaults(func=cmd_send_text)

    p = sub.add_parser("send-verified")
    p.add_argument("text")
    p.add_argument("marker")
    p.set_defaults(func=cmd_send_text_verified)

    sub.add_parser("click-send").set_defaults(func=cmd_click_send)

    p = sub.add_parser("verify-message")
    p.add_argument("contains")
    p.set_defaults(func=cmd_verify_message)

    p = sub.add_parser("upload-image")
    p.add_argument("path")
    p.set_defaults(func=cmd_upload_image)

    p = sub.add_parser("resume-image-only")
    p.add_argument("path")
    p.set_defaults(func=cmd_resume_image_only)

    p = sub.add_parser("quick-apply")
    p.add_argument("--job-title", default="")
    p.add_argument("--company", default="")
    p.add_argument("--resume-image", default="")
    p.add_argument("--portfolio", default="")
    p.add_argument("--greeting-verify", default="")
    p.add_argument("--portfolio-verify", default="")
    p.add_argument("--wait", type=float, default=1.8)
    p.set_defaults(func=cmd_quick_apply)

    p = sub.add_parser("smart-apply")
    p.add_argument("--job-title", default="")
    p.add_argument("--company", default="")
    p.add_argument("--resume-image", default="")
    p.add_argument("--portfolio", default="")
    p.add_argument("--greeting-verify", default="")
    p.add_argument("--portfolio-verify", default="")
    p.add_argument("--wait", type=float, default=1.8)
    p.set_defaults(func=cmd_smart_apply)

    p = sub.add_parser("apply-current-job")
    p.add_argument("--job-title", default="")
    p.add_argument("--company", default="")
    p.add_argument("--resume-image", default="")
    p.add_argument("--portfolio", default="")
    p.add_argument("--greeting-verify", default="")
    p.add_argument("--portfolio-verify", default="")
    p.add_argument("--wait", type=float, default=2.0)
    p.set_defaults(func=cmd_apply_current_job)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

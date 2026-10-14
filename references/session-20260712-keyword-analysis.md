# Session Findings: 2026-07-12 Keyword Analysis

## Search Keywords Tested

| Keyword | URL Encoded | Quality | Notes |
|---------|-------------|---------|-------|
| 视频剪辑 | %E8%A7%86%E9%A2%91%E5%89%AA%E8%BE%91 | Low | ~60%短视频/口播/直播相关污染 |
| 宣传片 剪辑 | %E5%AE%A3%E4%BC%A0%E7%89%87+%E5%89%AA%E8%BE%91 | Medium | 出现大量AIGC/AI漫剧内容，有效候选约20% |
| 后期剪辑 | %E5%90%8E%E6%9C%9F%E5%89%AA%E8%BE%91 | Medium | 混合结果，短剧+AI约占50% |
| 影视后期 | %E5%BD%B1%E8%A7%86%E5%90%8E%E6%9C%9F | Medium | 短期/AI含量较高，但有几条传统后期 |
| 企业视频剪辑 | %E4%BC%81%E4%B8%9A%E8%A7%86%E9%A2%91%E5%89%AA%E8%BE%91 | Low | 污染严重，同视频剪辑 |

## Candidates That Passed Initial Filter

1. **恒彩装饰 — 后期特效剪辑师** (8-12K·13薪，西湖区·西溪)
   - Skill match: PR/AE/达芬奇，品牌宣传片/TVC
   - Cons: 单休，本科要求
   - Result: `could_not_enter_chat_context` (no prior chat)

2. **霖禾文化创意 — 视频剪辑师** (9-11K，西湖区·西溪)
   - Skill match: PR/AE，企业宣传片
   - Cons: 公司新(2025-12成立)，兼做短视频
   - Result: `could_not_enter_chat_context` (no prior chat)

## `could_not_enter_chat_context` Pattern

Both new-company candidates returned this. The rect for "立即沟通" was always:
- `{left: 0, top: 49, width: 1415, height: 225}` — the entire card header
- JS `.click()` can't trigger React event bindings
- `pyautogui` native click clicks the center of the card, not the button specifically

This is a fundamental SPA limitation — no workaround found within this session.

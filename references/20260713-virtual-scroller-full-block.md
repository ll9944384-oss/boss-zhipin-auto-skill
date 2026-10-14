# 虚拟滚动器完全阻塞：会话记录 2026-07-13

## 背景

本会话是一次 cron job 触发，目标是检查 BOSS直聘聊天页面是否有 HR 发来的新消息并回复。

## 发现：所有交互方法均失效

当前页面约有 200+ 条历史对话，激活了 vue-virtual-scroller。测试了以下方法，全部失败：

### 已排除的方法

| 方法 | 结果 | 说明 |
|------|------|------|
| `el.click()` (JS) | ❌ | `isTrusted=false` |
| `dispatchEvent(MouseEvent)` mousedown+mouseup+click | ❌ | `isTrusted=false` |
| `dispatchEvent(TouchEvent)` touchstart+touchend | ❌ | `isTrusted=false` |
| pyautogui 物理点击（精确坐标） | ❌ | 虚拟滚动器忽略 |
| pyautogui mouseDown+mouseUp 序列 | ❌ | 同上 |
| AppleScript `do JavaScript` native `.click()` | ❌ | Vue 未绑定 |
| 键盘 Tab + ArrowDown 导航 | ❌ | 焦点在 chat-input 上 |
| 搜索框输入「<HR>先生」+ Enter | ❌ | Vue v-model 未响应编程写入 |
| Safari bounds 公式计算坐标点击 | ❌ | 坐标已验证正确 |
| 点击标题-box / 头像 / 消息预览等子元素 | ❌ | 均忽略 |

### 已验证正确的事项

- **「全部」标签点击正常**：pyautogui 点击「全部」标签（`.selected` 元素）每次都能正确切换 —— 说明屏幕坐标计算完全正确，不是坐标偏移问题
- **getBoundingClientRect() 正确**：`devicePixelRatio=2` (Retina) 但 macOS 自动处理逻辑像素到物理像素的映射
- **Safari 窗口激活正常**：`osascript -e 'tell application "Safari" to activate'` 执行成功

### 结论

虚拟滚动器激活后，所有基于 DOM 元素物理位置的事件均被拦截。**没有找到任何编程方法**能切换对话。

## 页面坐标参考

```
Safari window bounds (AppleScript):  left=0, top=38, right=1430, bottom=789
JS innerWidth=1430, innerHeight=671
toolbar = outerHeight - innerHeight = 751 - 671 = 80px

左面板 (chat-user):       left=123, top=69,  w=368, h=582
对话项 (friend-content):   left=131, top=247, w=348, h=75 (<HR>先生)
全部标签 (selected tab):   left=143, top=127, w=38,  h=24

坐标转换：
  screen_x = 0 (window left) + viewport_x
  screen_y = 38 (window top) + 80 (toolbar) + viewport_y
```

## DOM 特征（虚拟滚动器激活时）

```html
<UL role="thead" class="">  ← 空 UL，虚拟滚动器不渲染子元素
```

虚拟滚动器只在可见区域内渲染少量 `<li>` 元素。整个列表高度由 `padding-bottom: 4680px` 模拟：
```html
<UL role="group" style="padding: 0px 0px 4680px;">
```

每个可见 `<li>` 的结构：
```html
<LI role="listitem">
  <DIV class="friend-content-warp" data-v-3d67f5a8="">
    <DIV class="friend-content" data-v-3d67f5a8="">
      <DIV class="figure"><IMG class="image-circle"></DIV>
      <DIV class="text">
        <DIV><SPAN class="time">10:52</SPAN></DIV>
        <DIV class="title-box"><SPAN class="name-box"><HR>先生COMPANY_16艺术总监</SPAN></DIV>
        <DIV class="gray last-msg">你好，我们正在诚聘动画剪辑（合肥办公），有兴趣聊聊吗</DIV>
      </DIV>
    </DIV>
  </DIV>
</LI>
```

关键属性：
- 所有 `.friend-content` 都有 `data-v-3d67f5a8=""`（Vue scoped style）
- cursor: `pointer`（仅 `.friend-content` 内部元素有 pointer 光标）
- 无 onclick、onmousedown、tabindex、role="button" 等交互属性
- 无 data-* 属性或 id 用于标识对话
- `<LI>` 只有 `role="listitem"`，无 class

## 可用数据源（只读）

```javascript
window.chatStore.friends  // 包含所有对话的元数据
window.chatStore.getFriendInfoById(uniqueId)  // 获取对话详情
```

格式：
```javascript
{
  key: "0",
  val: "647893278-0",       // uniqueId
  info: {
    friendId: 647893278,
    uid: 647893278,
    name: "<HR>先生",
    brandName: "COMPANY_16",
    encryptBossId: "a2dd0abaca...",
    uniqueId: "647893278-0",
    lastTS: 1783772806704,  // 毫秒时间戳
    lastText: "你好，我们正在诚聘动画剪辑（合肥办公），有兴趣聊聊吗"
  }
}
```

`chatStore.friends` 按最后消息时间降序排列，`lastText` 字段可直接用于判断最新消息内容。

# BOSS直聘完整投递流程 (2026-07-22 更新)

## 新公司投递流程

```
1. navigate → job_detail页面
2. click-chat → 点"立即沟通"，进入初始textarea
3. send-text '打招呼语+作品集链接' → 填文字
   （pyautogui自动点发送按钮）
4. navigate → /web/geek/chat 聊天页
5. JS找到该公司对话项 → pyautogui点击
6. upload-image → 发图片简历
7. send-text '作品集链接' + click-send → 发作品集
```

## 注意事项

- **初始textarea (hasChatControls: false)**：发完第一条消息后必须 navigate 到聊天页才能发图片
- **完整聊天页 (hasChatControls: true)**：可以直接 upload-image 和 click-send
- **click-send**：动态查找"发送"按钮位置，用 pyautogui 点击，适配两种UI
- **简历路径**: /Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg

## HR要附件简历

1. 点击聊天中的"同意"按钮
2. 弹窗中选择第一个 .pdf 文件
3. 点击弹窗中的"发送"按钮 (坐标约 928,565 区别于主聊天发送按钮)

## 定时任务

- **boss-hr-auto-reply**: 每30分钟检查一次HR消息，自动回复
- **boss-auto-apply-8am**: 每天早上8:00自动投递新岗位

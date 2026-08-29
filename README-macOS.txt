DeepSeek Web Agent - macOS 客户端
=================================

选择版本
--------
- M1、M2、M3、M4 等 Apple 芯片：使用 apple-silicon 安装包。
- Intel 处理器的旧款 Mac：使用 intel 安装包。

安装与首次启动
--------------
1. 打开 DMG，将“DeepSeek Web Agent”拖入 Applications（应用程序）。
2. 本测试版尚未使用 Apple Developer ID 签名和公证。首次启动若被拦截：
   - 在 Finder 中找到应用；
   - 按住 Control 点击应用，选择“打开”；
   - 在确认窗口中再次选择“打开”。
3. 选择 Agent 可以访问的项目目录，输入任务并点击“开始会话并发送”。
4. 首次使用会打开专用 Chrome/Edge 窗口，请登录 DeepSeek。

示例指令
--------
先查看项目目录和必要文件，然后新建 hello.py，实现打印 Hello World；完成后运行并验证结果。

安全与数据
----------
- Agent 只能通过内置工具在所选项目目录中操作。
- 读取目录和文件可自动批准；写文件、改文件和运行代码仍会弹窗确认。
- 不确定某项操作是否安全时请选择“拒绝”，再向 Agent 补充要求。
- 专用浏览器资料和日志保存在：~/Library/Application Support/DeepSeekWebAgent
- 运行需要 macOS 11 或更高版本、可正常访问 DeepSeek 网页，并安装 Chrome 或 Edge。

# Temu Market Dashboard

本地网页控制台，用于：

- 上传 Temu 类目 CSV
- 从浏览器插件接收手动采集的数据
- 运行市场容量、集中度、价格带、配置和新上架指标
- 可选调用 OpenAI Responses API 生成分析解读

## 启动

```powershell
.\webapp\start.ps1
```

浏览器打开：

```text
http://127.0.0.1:8766
```

## OpenAI

API Key 只从服务端环境变量读取，不会发送给网页：

```powershell
Copy-Item webapp\.env.example webapp\.env
# 编辑 webapp\.env，填写 OPENAI_API_KEY
.\webapp\start.ps1
```

也可以直接设置 `$env:OPENAI_API_KEY`。默认模型为 `gpt-6.1-sol`，可通过
`OPENAI_MODEL` 覆盖；自定义兼容网关可通过 `OPENAI_BASE_URL` 设置。

不配置 API Key 时，上传、指标计算和图表仍可正常使用，只有“AI 分析”会显示未配置。

## 浏览器插件

插件目录：`webapp/extension/`

安装：

1. 打开 Chrome/比特浏览器的扩展程序页面。
2. 开启开发者模式。
3. 选择“加载未打包的扩展程序”。
4. 选择本目录的 `extension` 文件夹。
5. 打开 Temu 类目页。
6. 点击插件，选择市场和销量口径，手动触发采集。
7. 采集成功后发送到本地分析台，或下载 CSV/JSON。

插件只读取当前由用户主动触发页面中的可见商品信息，不读取 Cookie、Token 或账号资料，不调用隐藏接口，也不绕过验证码。

## 安全边界

- 服务只监听 `127.0.0.1`
- API Key 只存在于本地后端环境变量
- 请求体上限 20 MB
- 网页和插件不上传数据到第三方服务
- 只有在点击“AI 分析”时，指标摘要才发送给 OpenAI
- OpenAI 请求设置为不存储响应（`store: false`）

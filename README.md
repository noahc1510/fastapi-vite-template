# Laplacelab Remote Access

结合 Logto 登录、个人访问令牌（PAT）管理与简易网关转发。

### 后端能力

- Logto access_token 校验（`LOGTO_INTROSPECTION_ENDPOINT` + client_id/secret）。
- PAT 管理（创建、列举、删除），本地存储哈希值，可选调用 Logto Management API 生成远端 PAT（配置 `LOGTO_MANAGEMENT_API_BASE` 与 `LOGTO_MANAGEMENT_API_TOKEN` 后生效）。
- PAT 兑换 gateway access_token（JWT，`GATEWAY_JWT_SECRET` 控制签名）。
- 通用网关转发函数（`/api/gateway/target/{path}`）；未设置 `TARGET_SERVICE_BASE_URL` 时返回回显，便于调试。

主要接口：

- `GET /api/pat`：需要 Logto access_token，返回当前用户的 PAT 列表（不含明文）。
- `POST /api/pat`：需要 Logto access_token，创建 PAT，响应包含新生成的 PAT 明文。
- `DELETE /api/pat/{id}`：撤销/删除 PAT。
- `POST /api/pat/exchange`：`Authorization: Bearer <PAT>` 或 `X-PAT-TOKEN`，返回 gateway JWT。
- `GET /api/gateway/ping`：携带 gateway JWT 验证。
- `ANY /api/gateway/target/{path}`：携带 gateway JWT，转发到 `TARGET_SERVICE_BASE_URL`。

环境变量（`.env`）示例：

```
POSTGRES_PASSWORD=your-db-password
LOGTO_INTROSPECTION_ENDPOINT=https://<your-logto>/oidc/token/introspection
LOGTO_CLIENT_ID=<frontend-app-id>
LOGTO_CLIENT_SECRET=<frontend-secret>
LOGTO_MANAGEMENT_API_BASE=https://<your-logto>/api/management
LOGTO_MANAGEMENT_API_TOKEN=<optional-management-token>
GATEWAY_JWT_SECRET=change-me
TARGET_SERVICE_BASE_URL=https://httpbin.org
VITE_LOGTO_ENDPOINT=https://<your-logto>
VITE_LOGTO_APP_ID=<frontend-app-id>
VITE_LOGTO_RESOURCE=https://your.api.resource (可选，逗号分隔多个)
```

### 前端

- React + Vite + shadcn 风格组件。
- Logto 登录态展示。
- PAT 创建、列表、删除，创建后展示新 PAT 明文。
- PAT 兑换 access_token，并用 JWT 直接调用网关。

常用脚本：

```bash
uvicorn main:main --reload  # 启动后端
cd frontend && npm install && npm run dev  # 启动前端
```

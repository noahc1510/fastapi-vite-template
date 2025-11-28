# Laplacelab Remote Access

结合 Logto 登录、个人访问令牌（PAT）管理与简易网关转发。

### 后端能力

- Logto access_token 本地校验（JWT + JWKS），无需调用 introspection。
- PAT 管理全程调用 Logto Management API（创建/列表/删除），无本地存储。
- PAT → access_token 兑换：后端代理调用 Logto OIDC token 端点（`LOGTO_TOKEN_ENDPOINT`），可附带 `resource`（默认 `TARGET_SERVICE_BASE_URL`）。
- 网关鉴权：使用 Logto access_token（PAT 兑换得到的 JWT）做 introspection，校验通过后转发；`/api/gateway/target/{path}` 未配置 `TARGET_SERVICE_BASE_URL` 时返回回显。

主要接口：

- `GET /api/pat`：需要 Logto access_token，返回 Logto PAT 列表（由管理端 token 获取）。
- `POST /api/pat`：需要 Logto access_token，调用 Logto 管理端创建 PAT（仅需 name 与可选 expires_at），响应包含 PAT 明文。
- `DELETE /api/pat/{name}`：撤销/删除 PAT（通过管理端）。
- `POST /api/pat/exchange`：`Authorization: Bearer <PAT>` 或 `X-PAT-TOKEN`，后端调用 Logto token 端点返回 access_token（JWT）。
- `GET /api/gateway/ping`：携带 Logto access_token 验证。
- `ANY /api/gateway/target/{path}`：携带 Logto access_token，转发到 `TARGET_SERVICE_BASE_URL`。

环境变量（`.env`）示例：

```
POSTGRES_PASSWORD=your-db-password
LOGTO_ENDPOINT=https://<your-logto>
LOGTO_OIDC_TOKEN_ENDPOINT=https://<your-logto>/oidc/token  # 可选，未填则由 LOGTO_ENDPOINT 推导
LOGTO_JWKS_ENDPOINT=https://<your-logto>/oidc/jwks       # 可选，未填则由 LOGTO_ENDPOINT 推导
LOGTO_CLIENT_ID=<frontend-app-id>
LOGTO_CLIENT_SECRET=<frontend-secret>
LOGTO_MANAGEMENT_API_BASE=https://<your-logto>/api/management
LOGTO_MANAGEMENT_API_TOKEN=<optional-static-management-token>
LOGTO_M2M_CLIENT_ID=<m2m-client-id 或直接复用 LOGTO_CLIENT_ID>
LOGTO_M2M_CLIENT_SECRET=<m2m-client-secret 或直接复用 LOGTO_CLIENT_SECRET>
LOGTO_M2M_RESOURCE=https://<your-logto>/api/management  # 可选，默认为管理 API Base
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

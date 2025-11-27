import { ArrowRightLeft, KeyRound, LogIn, LogOut, RefreshCcw, ShieldCheck } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useHandleSignInCallback, useLogto } from "@logto/react"
import { NavLink, Route, Routes, Navigate, useLocation } from "react-router-dom"

import "./App.css"
import { Badge } from "./components/ui/badge"
import { Button } from "./components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card"
import { Input } from "./components/ui/input"
import { Label } from "./components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./components/ui/table"
import { Textarea } from "./components/ui/textarea"

type Pat = {
  id: number
  name: string
  description?: string | null
  scopes: string[]
  expires_at?: string | null
  last_used_at?: string | null
  logto_pat_id?: string | null
  is_revoked: boolean
  created_at: string
  token?: string
}

type ExchangeResult = {
  access_token: string
  expires_in: number
  pat_id: number
}

const apiFetch = async <T,>(url: string, options: RequestInit = {}) => {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `请求失败（${res.status}）`)
  }
  if (res.status === 204) return null as T
  return (await res.json()) as T
}

function App() {
  const { isAuthenticated, isLoading, signIn, signOut, fetchUserInfo, getAccessToken } = useLogto()
  const location = useLocation()
  const [logtoAccessToken, setLogtoAccessToken] = useState<string | null>(null)
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null)

  const [pats, setPats] = useState<Pat[]>([])
  const [patForm, setPatForm] = useState({ name: "", description: "", scopes: "gateway", expires_at: "" })
  const [creatingPat, setCreatingPat] = useState(false)
  const [loadingPats, setLoadingPats] = useState(false)
  const [patError, setPatError] = useState<string | null>(null)

  const [patToken, setPatToken] = useState("")
  const [exchangeResult, setExchangeResult] = useState<ExchangeResult | null>(null)
  const [gatewayPath, setGatewayPath] = useState("gateway/ping")
  const [gatewayResponse, setGatewayResponse] = useState<string>("")
  const [gatewayError, setGatewayError] = useState<string | null>(null)

  const heading = useMemo(
    () => ({
      title: "Remote Access Gateway",
      subtitle: "使用 Logto 登录、管理个人令牌，并通过网关安全访问后端服务。",
    }),
    []
  )

  useEffect(() => {
    const bootstrap = async () => {
      if (!isAuthenticated) {
        setProfile(null)
        setLogtoAccessToken(null)
        return
      }
      try {
        const [user, token] = await Promise.all([fetchUserInfo(), getAccessToken()])
        setProfile(user ?? null)
        setLogtoAccessToken(token ?? null)
      } catch (err) {
        console.error("加载 Logto 信息失败", err)
        setProfile(null)
        setLogtoAccessToken(null)
      }
    }
    void bootstrap()
  }, [isAuthenticated, fetchUserInfo, getAccessToken])

  useEffect(() => {
    const loadPats = async () => {
      if (!logtoAccessToken) return
      setLoadingPats(true)
      setPatError(null)
      try {
        const data = await apiFetch<Pat[]>("/api/pat", {
          headers: { Authorization: `Bearer ${logtoAccessToken}` },
        })
        setPats(data)
      } catch (err) {
        setPatError((err as Error).message)
      } finally {
        setLoadingPats(false)
      }
    }
    void loadPats()
  }, [logtoAccessToken])

  const formatDate = (value?: string | null) => {
    if (!value) return "长期有效"
    return new Intl.DateTimeFormat("zh-CN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value))
  }

  const handleCreatePat = async () => {
    if (!logtoAccessToken || !patForm.name.trim()) return
    setCreatingPat(true)
    setPatError(null)
    try {
      const payload = {
        name: patForm.name,
        description: patForm.description || null,
        scopes: patForm.scopes.split(",").map((scope) => scope.trim()),
        expires_at: patForm.expires_at ? new Date(patForm.expires_at).toISOString() : null,
      }
      const created = await apiFetch<Pat>("/api/pat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${logtoAccessToken}`,
        },
        body: JSON.stringify(payload),
      })
      setPats((prev) => [created, ...prev])
      setPatToken(created.token ?? "")
    } catch (err) {
      setPatError((err as Error).message)
    } finally {
      setCreatingPat(false)
    }
  }

  const handleDelete = async (patId: number) => {
    if (!logtoAccessToken) return
    setPatError(null)
    try {
      await apiFetch(`/api/pat/${patId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${logtoAccessToken}` },
      })
      setPats((prev) => prev.filter((p) => p.id !== patId))
    } catch (err) {
      setPatError((err as Error).message)
    }
  }

  const handleExchange = async () => {
    setGatewayError(null)
    if (!patToken.trim()) {
      setGatewayError("请输入 PAT")
      return
    }
    try {
      const res = await apiFetch<ExchangeResult>("/api/pat/exchange", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-PAT-TOKEN": patToken.trim(),
        },
        body: JSON.stringify({ token: patToken.trim() }),
      })
      setExchangeResult(res)
      setGatewayResponse("已成功兑换 access_token，可用于调用网关")
    } catch (err) {
      setGatewayError((err as Error).message)
    }
  }

  const callGateway = async () => {
    setGatewayError(null)
    if (!exchangeResult?.access_token) {
      setGatewayError("先兑换 access_token")
      return
    }
    try {
      const res = await apiFetch<unknown>(`/api/${gatewayPath}`, {
        headers: { Authorization: `Bearer ${exchangeResult.access_token}` },
        method: "GET",
      })
      setGatewayResponse(JSON.stringify(res, null, 2))
    } catch (err) {
      setGatewayError((err as Error).message)
    }
  }

  const renderAuthActions = () => {
    if (isLoading) return <Badge variant="muted">加载中...</Badge>
    if (!isAuthenticated) {
      return (
        <Button size="lg" onClick={() => signIn(`${window.location.origin}/callback`)} className="gap-2">
          <LogIn className="size-4" />
          使用 Logto 登录
        </Button>
      )
    }
    return (
      <div className="flex items-center gap-3">
        <Badge variant="success">已登录</Badge>
        <Button variant="outline" onClick={() => signOut(window.location.origin)} className="gap-2">
          <LogOut className="size-4" />
          退出
        </Button>
      </div>
    )
  }

  const renderOverview = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-5 text-sky-600" />
          登录态 / Profile
        </CardTitle>
        <CardDescription>Logto 登录信息，后端调用会自动带上 access_token。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between rounded-xl bg-sky-50 px-4 py-3 text-sm text-sky-900">
          <div>
            <p className="font-semibold">状态</p>
            <p className="text-xs text-sky-800/80">{isAuthenticated ? "已连接 Logto" : "未登录"}</p>
          </div>
          {renderAuthActions()}
        </div>
        <div className="rounded-xl bg-slate-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">用户信息</p>
          <pre className="mt-2 max-h-64 overflow-auto text-xs text-slate-700">
            {profile ? JSON.stringify(profile, null, 2) : "未登录"}
          </pre>
        </div>
      </CardContent>
    </Card>
  )

  const renderPat = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="size-5 text-amber-500" />
          创建 / 管理 PAT
        </CardTitle>
        <CardDescription>使用 Logto access_token 与后端交互，创建后会返回完整 PAT 值（仅显示一次）。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>名称</Label>
            <Input
              placeholder="例如：前端调试令牌"
              value={patForm.name}
              onChange={(e) => setPatForm((s) => ({ ...s, name: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>作用域（逗号分隔）</Label>
            <Input
              placeholder="gateway,read-only"
              value={patForm.scopes}
              onChange={(e) => setPatForm((s) => ({ ...s, scopes: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>描述</Label>
            <Textarea
              placeholder="用途说明，方便后续管理"
              value={patForm.description}
              onChange={(e) => setPatForm((s) => ({ ...s, description: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>到期时间（可选）</Label>
            <Input
              type="datetime-local"
              value={patForm.expires_at}
              onChange={(e) => setPatForm((s) => ({ ...s, expires_at: e.target.value }))}
            />
          </div>
        </div>
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm text-slate-600">
            {patToken ? (
              <span>
                新 PAT：<span className="font-mono text-slate-900">{patToken}</span>
              </span>
            ) : (
              "点击创建后会在此显示新的 PAT，仅出现一次。"
            )}
          </div>
          <Button onClick={handleCreatePat} disabled={!isAuthenticated || creatingPat} className="gap-2">
            {creatingPat ? <RefreshCcw className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
            创建 PAT
          </Button>
        </div>
        {patError && <p className="text-sm text-rose-600">{patError}</p>}

        <div className="rounded-xl border border-slate-200/80">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>作用域</TableHead>
                <TableHead>到期</TableHead>
                <TableHead>最近使用</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingPats && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-slate-500">
                    加载中...
                  </TableCell>
                </TableRow>
              )}
              {!loadingPats && pats.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-slate-500">
                    暂无 PAT
                  </TableCell>
                </TableRow>
              )}
              {pats.map((pat) => (
                <TableRow key={pat.id}>
                  <TableCell className="font-medium text-slate-900">
                    <div>{pat.name}</div>
                    {pat.description && <div className="text-xs text-slate-500">{pat.description}</div>}
                  </TableCell>
                  <TableCell className="space-x-1">
                    {pat.scopes.map((scope) => (
                      <Badge key={scope} variant="muted">
                        {scope}
                      </Badge>
                    ))}
                  </TableCell>
                  <TableCell>{formatDate(pat.expires_at)}</TableCell>
                  <TableCell>{pat.last_used_at ? formatDate(pat.last_used_at) : "-"}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-rose-600 hover:bg-rose-50"
                      onClick={() => handleDelete(pat.id)}
                    >
                      删除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )

  const renderExchange = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ArrowRightLeft className="size-5 text-emerald-600" />
          PAT 兑换 access_token
        </CardTitle>
        <CardDescription>PAT → Gateway JWT，用于后续调用 /api/gateway/*。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>个人访问令牌 (PAT)</Label>
          <Input
            placeholder="pat_xxx..."
            value={patToken}
            onChange={(e) => setPatToken(e.target.value)}
            autoComplete="off"
          />
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={handleExchange} className="gap-2">
            <ArrowRightLeft className="size-4" />
            兑换 access_token
          </Button>
          {exchangeResult && (
            <Badge variant="success">
              已生成 · 有效期 {Math.round(exchangeResult.expires_in / 60)} 分钟
            </Badge>
          )}
        </div>
        {exchangeResult && (
          <div className="rounded-xl bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">access_token (JWT)</p>
            <pre className="mt-2 max-h-48 overflow-auto text-xs text-slate-700">
              {exchangeResult.access_token}
            </pre>
          </div>
        )}
        {gatewayError && <p className="text-sm text-rose-600">{gatewayError}</p>}
        {gatewayResponse && !gatewayError && <p className="text-sm text-emerald-700">{gatewayResponse}</p>}
      </CardContent>
    </Card>
  )

  const renderGateway = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RefreshCcw className="size-5 text-indigo-600" />
          Gateway 调用
        </CardTitle>
        <CardDescription>
          已预留通用转发函数，目标 API 留空时会回显请求内容（后续可在后端配置 TARGET_SERVICE_BASE_URL）。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label>网关路径</Label>
          <Input
            value={gatewayPath}
            onChange={(e) => setGatewayPath(e.target.value)}
            placeholder="gateway/target/your-api"
          />
          <p className="text-xs text-slate-500">
            示例：gateway/ping 或 gateway/target/anything。请求会带上上一步生成的 access_token。
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={callGateway} className="gap-2" disabled={!exchangeResult}>
            <ShieldCheck className="size-4" />
            调用网关
          </Button>
          {!exchangeResult && <Badge variant="warning">先兑换 access_token</Badge>}
        </div>
        <div className="rounded-xl bg-slate-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">响应</p>
          <pre className="mt-2 max-h-64 overflow-auto text-xs text-slate-700">
            {gatewayResponse || "等待调用..."}
          </pre>
        </div>
      </CardContent>
    </Card>
  )

  if (location.pathname === "/callback") {
    return <CallbackPage />
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">Zero-trust remote access</p>
          <h1>{heading.title}</h1>
          <p className="muted">{heading.subtitle}</p>
          <div className="mt-4">{renderAuthActions()}</div>
        </div>
        <div className="hero-mark">
          <div className="icon-wrap">
            <ShieldCheck className="size-8 text-sky-600" />
            <KeyRound className="size-8 text-indigo-600" />
            <ArrowRightLeft className="size-8 text-emerald-600" />
          </div>
          <p className="muted text-xs">Logto 登录 · PAT 管理 · 网关转发</p>
        </div>
      </header>

      <div className="switcher">
        <NavLink to="/" className={({ isActive }: { isActive: boolean }) => (isActive ? "tab active" : "tab")}>
          登录 / Profile
        </NavLink>
        <NavLink
          to="/pat"
          className={({ isActive }: { isActive: boolean }) => (isActive ? "tab active" : "tab")}
        >
          PAT 管理
        </NavLink>
        <NavLink
          to="/exchange"
          className={({ isActive }: { isActive: boolean }) => (isActive ? "tab active" : "tab")}
        >
          PAT 兑换 access_token
        </NavLink>
        <NavLink
          to="/gateway"
          className={({ isActive }: { isActive: boolean }) => (isActive ? "tab active" : "tab")}
        >
          网关调用
        </NavLink>
      </div>

      <section className="content">
        <Routes>
          <Route path="/" element={renderOverview()} />
          <Route path="/pat" element={renderPat()} />
          <Route path="/exchange" element={renderExchange()} />
          <Route path="/gateway" element={renderGateway()} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </section>
    </div>
  )
}

export default App

function CallbackPage() {
  useHandleSignInCallback(() => {
    window.location.replace("/")
  })
  return (
    <div className="page">
      <Card>
        <CardHeader>
          <CardTitle>正在完成登录</CardTitle>
          <CardDescription>请稍候，正在处理 Logto 返回的凭据…</CardDescription>
        </CardHeader>
        <CardContent>Loading...</CardContent>
      </Card>
    </div>
  )
}

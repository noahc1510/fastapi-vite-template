import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { LogtoProvider } from "@logto/react"
import { BrowserRouter } from "react-router-dom"

import App from "./App.tsx"
import "./index.css"

const logtoConfig = {
  endpoint: import.meta.env.VITE_LOGTO_ENDPOINT,
  appId: import.meta.env.VITE_LOGTO_APP_ID,
  resources: (() => {
    const value = import.meta.env.VITE_LOGTO_RESOURCE
    if (!value) return undefined
    return value
      .split(",")
      .map((item: string) => item.trim())
      .filter((v: string) => Boolean(v))
  })(),
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <LogtoProvider config={logtoConfig}>
        <App />
      </LogtoProvider>
    </BrowserRouter>
  </StrictMode>
)

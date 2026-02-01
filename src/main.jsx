import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import i18n from './i18n'

const BOOT_TIMEOUT_MS = 5000
const rootElement = document.getElementById('root')
const t = i18n.t.bind(i18n)

window.__APP_BOOTED__ = false
window.__APP_ERRORS__ = window.__APP_ERRORS__ || []

const recordAppError = (error, meta = {}) => {
    const entry = {
        time: new Date().toISOString(),
        message: error?.message || String(error),
        stack: error?.stack || '',
        meta
    }
    window.__APP_ERRORS__.push(entry)
    if (window.__APP_ERRORS__.length > 50) {
        window.__APP_ERRORS__.shift()
    }
    return entry
}

const buildErrorPayload = (error, meta = {}) => {
    const latest = recordAppError(error, meta)
    return JSON.stringify({ latest, errors: window.__APP_ERRORS__ }, null, 2)
}

const copyText = async (text) => {
    try {
        if (navigator?.clipboard?.writeText) {
            await navigator.clipboard.writeText(text)
            return true
        }
    } catch { }
    try {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.setAttribute('readonly', '')
        textarea.style.position = 'absolute'
        textarea.style.left = '-9999px'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
        return true
    } catch {
        return false
    }
}

const renderFallbackDom = (error, meta = {}) => {
    if (!rootElement) return
    const payload = buildErrorPayload(error, meta)
    rootElement.innerHTML = `
      <div style="position:fixed;inset:0;background:#0b0b0c;color:#f3f3f3;display:flex;align-items:center;justify-content:center;font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial;">
        <div style="width:min(900px,92vw);background:#141416;border:1px solid #2a2a2d;border-radius:12px;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,0.4);">
          <div style="font-size:18px;font-weight:700;margin-bottom:8px;">${t('Tapnow 启动失败')}</div>
          <div style="font-size:12px;color:#b6b6c2;margin-bottom:16px;">${t('应用启动过程中发生异常，已启用黑屏保护。')}</div>
          <div style="background:#0f0f12;border:1px solid #2a2a2d;border-radius:8px;padding:12px;font-size:12px;white-space:pre-wrap;max-height:240px;overflow:auto;">${payload.replace(/</g, '&lt;')}</div>
          <div style="display:flex;gap:10px;margin-top:16px;">
            <button id="tapnow-reload" style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 12px;font-size:12px;cursor:pointer;">${t('重新加载')}</button>
            <button id="tapnow-copy" style="background:#27272a;color:#fff;border:1px solid #3f3f46;border-radius:8px;padding:8px 12px;font-size:12px;cursor:pointer;">${t('复制错误详情')}</button>
          </div>
        </div>
      </div>
    `
    const reloadBtn = document.getElementById('tapnow-reload')
    const copyBtn = document.getElementById('tapnow-copy')
    if (reloadBtn) reloadBtn.onclick = () => window.location.reload()
    if (copyBtn) copyBtn.onclick = () => copyText(payload)
}

const attachGlobalErrorHandlers = () => {
    const previousOnError = window.onerror
    const previousOnUnhandled = window.onunhandledrejection

    window.onerror = (message, source, lineno, colno, error) => {
        recordAppError(error || message, { type: 'onerror', source, lineno, colno })
        if (typeof previousOnError === 'function') {
            return previousOnError(message, source, lineno, colno, error)
        }
        return false
    }

    window.onunhandledrejection = (event) => {
        recordAppError(event?.reason || 'UnhandledRejection', { type: 'unhandledrejection' })
        if (typeof previousOnUnhandled === 'function') {
            return previousOnUnhandled(event)
        }
        return false
    }
}

const FatalScreen = ({ error, meta }) => {
    const payload = buildErrorPayload(error, meta)
    return (
        <div style={{ position: 'fixed', inset: 0, background: '#0b0b0c', color: '#f3f3f3', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'system-ui,Segoe UI,Roboto,Helvetica,Arial' }}>
            <div style={{ width: 'min(900px,92vw)', background: '#141416', border: '1px solid #2a2a2d', borderRadius: 12, padding: 24, boxShadow: '0 20px 60px rgba(0,0,0,0.4)' }}>
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{t('Tapnow 启动失败')}</div>
                <div style={{ fontSize: 12, color: '#b6b6c2', marginBottom: 16 }}>{t('应用启动过程中发生异常，已启用黑屏保护。')}</div>
                <div style={{ background: '#0f0f12', border: '1px solid #2a2a2d', borderRadius: 8, padding: 12, fontSize: 12, whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto' }}>{payload}</div>
                <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                    <button onClick={() => window.location.reload()} style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 12px', fontSize: 12, cursor: 'pointer' }}>{t('重新加载')}</button>
                    <button onClick={() => copyText(payload)} style={{ background: '#27272a', color: '#fff', border: '1px solid #3f3f46', borderRadius: 8, padding: '8px 12px', fontSize: 12, cursor: 'pointer' }}>{t('复制错误详情')}</button>
                </div>
            </div>
        </div>
    )
}

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = { error: null }
    }
    static getDerivedStateFromError(error) {
        return { error }
    }
    componentDidCatch(error, info) {
        recordAppError(error, { type: 'error_boundary', info })
    }
    render() {
        if (this.state.error) {
            return <FatalScreen error={this.state.error} meta={{ type: 'error_boundary' }} />
        }
        return this.props.children
    }
}

const BootGuard = ({ children }) => {
    const [timedOut, setTimedOut] = React.useState(false)
    React.useEffect(() => {
        const timer = window.setTimeout(() => {
            if (!window.__APP_BOOTED__) {
                recordAppError(new Error('APP_BOOT_TIMEOUT'), { type: 'boot_timeout' })
                setTimedOut(true)
            }
        }, BOOT_TIMEOUT_MS)
        window.__APP_BOOT_TIMER__ = timer
        return () => window.clearTimeout(timer)
    }, [])

    if (timedOut) {
        return <FatalScreen error={new Error(t('启动超时'))} meta={{ type: 'boot_timeout' }} />
    }
    return children
}

attachGlobalErrorHandlers()

try {
    if (!rootElement) throw new Error('Root element not found')
    const root = ReactDOM.createRoot(rootElement)
    root.render(
        <React.StrictMode>
            <ErrorBoundary>
                <BootGuard>
                    <App />
                </BootGuard>
            </ErrorBoundary>
        </React.StrictMode>
    )
} catch (error) {
    renderFallbackDom(error, { type: 'bootstrap' })
}

import { useEffect, useRef, useState } from 'react'
import './Auth.css'

// Local dev uses the Vite proxy (/api). In production set VITE_API_URL to the backend URL.
const API = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
const RESEND_SECONDS = 60

async function post(path, body) {
  const response = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    // FastAPI validation errors come as a list
    const detail = Array.isArray(data.detail)
      ? data.detail.map(d => d.msg).join(', ')
      : data.detail
    throw new Error(detail || 'Something went wrong. Please try again.')
  }
  return data
}

function OtpInput({ value, onChange, disabled }) {
  const refs = useRef([])
  const digits = value.padEnd(6, ' ').split('')

  function setDigit(index, digit) {
    const next = digits.map((d, i) => (i === index ? digit : d)).join('').replace(/\s/g, '')
    onChange(next.slice(0, 6))
  }

  function handleChange(index, e) {
    const typed = e.target.value.replace(/\D/g, '')
    if (!typed) return

    if (typed.length > 1) {
      // pasted full code
      onChange(typed.slice(0, 6))
      refs.current[Math.min(typed.length, 5)]?.focus()
      return
    }
    setDigit(index, typed)
    refs.current[index + 1]?.focus()
  }

  function handleKeyDown(index, e) {
    if (e.key === 'Backspace') {
      e.preventDefault()
      if (digits[index].trim()) {
        onChange(value.slice(0, index) + value.slice(index + 1))
      } else if (index > 0) {
        onChange(value.slice(0, index - 1) + value.slice(index))
        refs.current[index - 1]?.focus()
      }
    }
    if (e.key === 'ArrowLeft') refs.current[index - 1]?.focus()
    if (e.key === 'ArrowRight') refs.current[index + 1]?.focus()
  }

  return (
    <div className="otp-boxes">
      {digits.map((digit, i) => (
        <input
          key={i}
          ref={el => (refs.current[i] = el)}
          inputMode="numeric"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          maxLength={6}
          value={digit.trim()}
          disabled={disabled}
          autoFocus={i === 0}
          onChange={e => handleChange(i, e)}
          onKeyDown={e => handleKeyDown(i, e)}
          onFocus={e => e.target.select()}
        />
      ))}
    </div>
  )
}

export default function Auth({ onAuthenticated, onClose }) {
  const [mode, setMode] = useState('login') // 'login' | 'register' | 'otp'
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown(c => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  function update(field) {
    return e => setForm({ ...form, [field]: e.target.value })
  }

  function switchMode(next) {
    setMode(next)
    setError('')
    setInfo('')
  }

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await post('/auth/login', { email: form.email, password: form.password })
      onAuthenticated(data.token, data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    setError('')

    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm) return setError('Passwords do not match.')

    setLoading(true)
    try {
      const data = await post('/auth/register', {
        name: form.name,
        email: form.email,
        password: form.password
      })
      setOtp('')
      setInfo(data.message)
      setCooldown(RESEND_SECONDS)
      setMode('otp')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleVerify(e) {
    e?.preventDefault()
    if (otp.length !== 6) return setError('Enter the 6-digit code.')

    setLoading(true)
    setError('')
    try {
      const data = await post('/auth/verify-otp', { email: form.email, otp })
      onAuthenticated(data.token, data.user)
    } catch (err) {
      setError(err.message)
      setOtp('')
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    setLoading(true)
    setError('')
    try {
      const data = await post('/auth/resend-otp', { email: form.email })
      setInfo(data.message)
      setOtp('')
      setCooldown(RESEND_SECONDS)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-backdrop" onClick={onClose}>
      <div className="auth-card" onClick={e => e.stopPropagation()}>
        <button className="close-button" onClick={onClose} aria-label="Close">✕</button>

        <div className="auth-brand">
          <span className="brand-icon">BB</span>
          <span>Bharat <strong>Brief</strong></span>
        </div>

        {mode !== 'otp' && (
          <div className="auth-tabs">
            <button
              className={mode === 'login' ? 'active' : ''}
              onClick={() => switchMode('login')}
            >
              Login
            </button>
            <button
              className={mode === 'register' ? 'active' : ''}
              onClick={() => switchMode('register')}
            >
              Sign up
            </button>
          </div>
        )}

        {mode === 'login' && (
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Welcome back</h2>
            <label>
              Email
              <input type="email" required value={form.email} onChange={update('email')} placeholder="you@gmail.com" autoComplete="email" />
            </label>
            <label>
              Password
              <input type="password" required value={form.password} onChange={update('password')} placeholder="Your password" autoComplete="current-password" />
            </label>
            {error && <div className="auth-error">{error}</div>}
            <button className="auth-submit" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
            <p className="auth-switch">
              New here? <button type="button" onClick={() => switchMode('register')}>Create an account</button>
            </p>
          </form>
        )}

        {mode === 'register' && (
          <form onSubmit={handleRegister} className="auth-form">
            <h2>Create your account</h2>
            <label>
              Full name
              <input required minLength={2} value={form.name} onChange={update('name')} placeholder="Your name" autoComplete="name" />
            </label>
            <label>
              Email
              <input type="email" required value={form.email} onChange={update('email')} placeholder="you@gmail.com" autoComplete="email" />
            </label>
            <label>
              Password
              <input type="password" required minLength={8} value={form.password} onChange={update('password')} placeholder="At least 8 characters" autoComplete="new-password" />
            </label>
            <label>
              Confirm password
              <input type="password" required value={form.confirm} onChange={update('confirm')} placeholder="Re-enter password" autoComplete="new-password" />
            </label>
            {error && <div className="auth-error">{error}</div>}
            <button className="auth-submit" disabled={loading}>
              {loading ? 'Sending OTP...' : 'Send OTP'}
            </button>
            <p className="auth-switch">
              Already have an account? <button type="button" onClick={() => switchMode('login')}>Login</button>
            </p>
          </form>
        )}

        {mode === 'otp' && (
          <form onSubmit={handleVerify} className="auth-form">
            <h2>Verify your email</h2>
            <p className="auth-sub">
              We sent a 6-digit code to <strong>{form.email}</strong>. Check your inbox (and spam folder).
            </p>

            <OtpInput value={otp} onChange={setOtp} disabled={loading} />

            {info && !error && <div className="auth-info">{info}</div>}
            {error && <div className="auth-error">{error}</div>}

            <button className="auth-submit" disabled={loading || otp.length !== 6}>
              {loading ? 'Verifying...' : 'Verify & create account'}
            </button>

            <div className="otp-actions">
              <button type="button" onClick={handleResend} disabled={loading || cooldown > 0}>
                {cooldown > 0 ? `Resend OTP in ${cooldown}s` : 'Resend OTP'}
              </button>
              <button type="button" onClick={() => switchMode('register')}>
                Change email
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

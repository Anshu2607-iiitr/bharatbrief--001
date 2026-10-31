
import { useEffect, useState } from 'react'
import './App.css'
import Auth from './Auth.jsx'

// Local dev uses the Vite proxy (/api). In production set VITE_API_URL to the backend URL.
const API = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

const categories = [
  'All News',
  'Politics & Governance',
  'Agriculture',
  'Sports',
  'Economy',
  'Science & Technology',
  'Defence',
  'Education',
  'Health',
  'Environment',
  'International Relations'
]

function App() {
  const [news, setNews] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('All News')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNews, setSelectedNews] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [user, setUser] = useState(null)
  const [showAuth, setShowAuth] = useState(false)

  // restore login session on page load
  useEffect(() => {
    const token = localStorage.getItem('bb_token')
    if (!token) return

    fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => (res.ok ? res.json() : Promise.reject()))
      .then(data => setUser(data.user))
      .catch(() => localStorage.removeItem('bb_token'))
  }, [])

  function handleAuthenticated(token, loggedInUser) {
    localStorage.setItem('bb_token', token)
    setUser(loggedInUser)
    setShowAuth(false)
  }

  function logout() {
    localStorage.removeItem('bb_token')
    setUser(null)
  }

  useEffect(() => {
    async function fetchNews() {
      setLoading(true)
      setError('')

      try {
        const url = selectedCategory === 'All News'
          ? `${API}/news`
          : `${API}/news?category=${encodeURIComponent(selectedCategory)}`

        const response = await fetch(url)

        if (!response.ok) {
          throw new Error('Unable to fetch news')
        }

        const data = await response.json()
        setNews(data.news || [])
      } catch {
        setError('Backend se connection nahi ho pa raha. Backend server check karein.')
      } finally {
        setLoading(false)
      }
    }

    fetchNews()
  }, [selectedCategory])

  async function openNews(item) {
    setSelectedNews(item)
    setDetailLoading(true)
    setDetailError('')

    try {
      const response = await fetch(`${API}/news/${item.id}`)

      if (!response.ok) {
        throw new Error('Article details could not be loaded')
      }

      const data = await response.json()
      setSelectedNews(data.news)
    } catch {
      setDetailError('Full article load nahi ho paya. Original PIB link se article padhein.')
    } finally {
      setDetailLoading(false)
    }
  }

  const filteredNews = news.filter(item =>
    item.title?.toLowerCase().includes(search.toLowerCase())
  )

  function formatDate(date) {
    if (!date) return 'Date unavailable'

    return new Date(date).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <a className="brand" href="/">
            <span className="brand-icon">BB</span>
            <span>Bharat <strong>Brief</strong></span>
          </a>
          <div className="header-actions">
            <span className="header-tagline">
              News that matters. Straight from the source.
            </span>
            {user ? (
              <div className="user-chip">
                <span className="user-avatar">{user.name?.[0]?.toUpperCase()}</span>
                <span className="user-name">{user.name}</span>
                <button className="logout-button" onClick={logout}>Logout</button>
              </div>
            ) : (
              <button className="login-button" onClick={() => setShowAuth(true)}>
                Login / Sign up
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="container">
        <section className="hero-section">
          <div className="hero-label">OFFICIAL NEWS • PIB INDIA</div>
          <h1>Stay Informed.<br /><span>Stay Ahead.</span></h1>
          <p>
            Discover the latest updates from across India,
            collected directly from official government sources.
          </p>

          <div className="search-box">
            <span>⌕</span>
            <input
              type="text"
              placeholder="Search news by title..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </section>

        <section className="news-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">YOUR NEWS FEED</span>
              <h2>Latest News</h2>
            </div>
            <span className="news-count">{filteredNews.length} Articles</span>
          </div>

          <div className="category-list">
            {categories.map(category => (
              <button
                key={category}
                className={selectedCategory === category ? 'category active' : 'category'}
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>

          {loading && <div className="message">Loading latest news...</div>}
          {error && <div className="message error">{error}</div>}

          {!loading && !error && filteredNews.length === 0 && (
            <div className="message">No news articles found.</div>
          )}

          {!loading && !error && (
            <div className="news-grid">
              {filteredNews.map(item => (
                <article className="news-card" key={item.id}>
                  <div className="card-top">
                    <span className="source-tag">PIB INDIA</span>
                    <span className="date">{formatDate(item.published_date)}</span>
                  </div>

                  <h3>{item.title}</h3>

                  <p className="description">
                    {item.description || 'Read the full official article for more information.'}
                  </p>

                  <div className="card-bottom">
                    <span className="category-tag">{item.category}</span>
                    <button onClick={() => openNews(item)}>
                      Read More →
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <strong>Bharat Brief</strong>
        <p>Official news. Reliable information. One platform.</p>
        <span>News source: Press Information Bureau, Government of India</span>
      </footer>

      {selectedNews && (
        <div className="modal-backdrop" onClick={() => setSelectedNews(null)}>
          <article className="article-modal" onClick={e => e.stopPropagation()}>
            <button
              className="close-button"
              onClick={() => setSelectedNews(null)}
            >
              ✕
            </button>

            <span className="source-tag">PRESS INFORMATION BUREAU</span>
            <h2>{selectedNews.title}</h2>
            <p className="modal-date">
              {formatDate(selectedNews.published_date)}
            </p>

            <div className="article-content">
              {detailLoading
                ? 'Loading full article...'
                : detailError
                  ? detailError
                  : selectedNews.content || selectedNews.description || 'Full article content unavailable.'}
            </div>

            <a
              className="source-link"
              href={selectedNews.url}
              target="_blank"
              rel="noreferrer"
            >
              Read Original PIB Article ↗
            </a>
          </article>
        </div>
      )}

      {showAuth && (
        <Auth
          onAuthenticated={handleAuthenticated}
          onClose={() => setShowAuth(false)}
        />
      )}
    </div>
  )
}

export default App

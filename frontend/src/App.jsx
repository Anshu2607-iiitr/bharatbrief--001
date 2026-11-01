import { useEffect, useState, useRef } from 'react'
import './App.css'
import Auth from './Auth.jsx'

// Local dev: Vite proxies /api. On Vercel: frontend/vercel.json forwards /api to the backend.
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

const podcastLanguages = [
  { name: 'Hindi', code: 'hi-IN' },
  { name: 'English', code: 'en-IN' },
  { name: 'Bengali', code: 'bn-IN' },
  { name: 'Gujarati', code: 'gu-IN' },
  { name: 'Kannada', code: 'kn-IN' },
  { name: 'Marathi', code: 'mr-IN' },
  { name: 'Punjabi', code: 'pa-IN' },
  { name: 'Tamil', code: 'ta-IN' },
  { name: 'Telugu', code: 'te-IN' }
]

const audioSpeeds = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]

function App() {
  const [news, setNews] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('All News')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNews, setSelectedNews] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  const [relatedNews, setRelatedNews] = useState([])
  const [relatedLoading, setRelatedLoading] = useState(false)
  const [relatedError, setRelatedError] = useState('')

  const [timeline, setTimeline] = useState([])
  const [timelineLoading, setTimelineLoading] = useState(true)
  const [timelineError, setTimelineError] = useState('')

  // Navigation
  const [menuOpen, setMenuOpen] = useState(false)
  const [activeView, setActiveView] = useState('home')

  // Translation states
  const [languages, setLanguages] = useState([])
  const [selectedLanguage, setSelectedLanguage] = useState('hi-IN')
  const [translatedArticle, setTranslatedArticle] = useState(null)
  const [translationLoading, setTranslationLoading] = useState(false)
  const [translationError, setTranslationError] = useState('')
  const [showTranslation, setShowTranslation] = useState(false)

  // Article audio states
  const [audioUrl, setAudioUrl] = useState('')
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioError, setAudioError] = useState('')
  const [articleAudioSpeed, setArticleAudioSpeed] = useState(1)
  const articleAudioRef = useRef(null)

  // Podcast states
  const [podcastCategories, setPodcastCategories] = useState([])
  const [podcastLanguage, setPodcastLanguage] = useState('hi-IN')
  const [podcastDuration, setPodcastDuration] = useState(5)
  const [podcastLoading, setPodcastLoading] = useState(false)
  const [podcastError, setPodcastError] = useState('')
  const [podcastData, setPodcastData] = useState(null)
  const [podcastAudioUrl, setPodcastAudioUrl] = useState('')
  const [podcastAudioSpeed, setPodcastAudioSpeed] = useState(1)
  const podcastAudioRef = useRef(null)

  // Chatbot states
  const [chatOpen, setChatOpen] = useState(false)
  const [chatLanguages, setChatLanguages] = useState([])
  const [chatLanguage, setChatLanguage] = useState(() => {
    return localStorage.getItem('bharatBriefChatLanguage') || 'hi-IN'
  })
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')

  // AUTH
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

  // Revoke old article audio URL
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  // Revoke old podcast audio URL
  useEffect(() => {
    return () => {
      if (podcastAudioUrl) URL.revokeObjectURL(podcastAudioUrl)
    }
  }, [podcastAudioUrl])

  // Apply article playback speed
  useEffect(() => {
    if (articleAudioRef.current) {
      articleAudioRef.current.playbackRate = articleAudioSpeed
    }
  }, [articleAudioSpeed, audioUrl])

  // Apply podcast playback speed
  useEffect(() => {
    if (podcastAudioRef.current) {
      podcastAudioRef.current.playbackRate = podcastAudioSpeed
    }
  }, [podcastAudioSpeed, podcastAudioUrl])

  // Fetch available languages
  useEffect(() => {
    async function fetchLanguages() {
      try {
        const response = await fetch(`${API}/languages`)

        if (!response.ok) {
          throw new Error('Unable to fetch languages')
        }

        const data = await response.json()
        setLanguages(data.languages || [])
        setChatLanguages(data.languages || [])
      } catch {
        setTranslationError('Languages load nahi ho paayi.')
        setChatError('Languages load nahi ho paayi.')
      }
    }

    fetchLanguages()
  }, [])

  // Save chatbot language preference
  useEffect(() => {
    localStorage.setItem('bharatBriefChatLanguage', chatLanguage)
  }, [chatLanguage])

  // Fetch news
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

  // Fetch News Timeline
  useEffect(() => {
    async function fetchTimeline() {
      setTimelineLoading(true)
      setTimelineError('')

      try {
        const response = await fetch(`${API}/news/timeline?days=30&limit=500`)

        if (!response.ok) {
          throw new Error('Unable to fetch timeline')
        }

        const data = await response.json()
        setTimeline(data.timeline || [])
      } catch {
        setTimelineError('News timeline load nahi ho payi.')
      } finally {
        setTimelineLoading(false)
      }
    }

    fetchTimeline()
  }, [])

  function navigateTo(view) {
    setActiveView(view)
    setMenuOpen(false)

    if (view === 'home') {
      setSelectedCategory('All News')
    }

    if (view === 'latest') {
      setSelectedCategory('All News')
    }

    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function resetAudio() {
    setAudioUrl('')
    setAudioError('')
    setAudioLoading(false)
    setArticleAudioSpeed(1)
  }

  async function openNews(item) {
    setSelectedNews(item)

    setDetailLoading(true)
    setDetailError('')

    setRelatedNews([])
    setRelatedLoading(true)
    setRelatedError('')

    setTranslatedArticle(null)
    setShowTranslation(false)
    setTranslationError('')
    resetAudio()

    const detailRequest = fetch(`${API}/news/${item.id}`)
    const relatedRequest = fetch(`${API}/news/${item.id}/related?limit=5`)

    try {
      const response = await detailRequest

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

    try {
      const response = await relatedRequest

      if (!response.ok) {
        throw new Error('Related news could not be loaded')
      }

      const data = await response.json()
      setRelatedNews(data.related_news || [])
    } catch {
      setRelatedError('Related news abhi load nahi ho pa rahi.')
    } finally {
      setRelatedLoading(false)
    }
  }

  // Translate complete article
  async function translateArticle() {
    if (!selectedNews) return

    setTranslationLoading(true)
    setTranslationError('')
    setTranslatedArticle(null)
    setShowTranslation(false)
    resetAudio()

    try {
      const response = await fetch(
        `${API}/news/${selectedNews.id}/translate?target_language=${encodeURIComponent(selectedLanguage)}`,
        {
          method: 'POST'
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Translation failed')
      }

      if (data.status !== 'success' || !data.translated_article) {
        throw new Error('Invalid translation response')
      }

      setTranslatedArticle(data.translated_article)
      setShowTranslation(true)
    } catch (err) {
      setTranslationError(
        err.message || 'Article translate nahi ho paya. Dobara try karein.'
      )
    } finally {
      setTranslationLoading(false)
    }
  }

  function showOriginalArticle() {
    setShowTranslation(false)
    setTranslationError('')
    resetAudio()
  }

  // Generate and play news audio
  async function listenToNews() {
    if (!selectedNews || audioLoading) return

    setAudioLoading(true)
    setAudioError('')
    setAudioUrl('')

    const audioLanguage = showTranslation && translatedArticle
      ? selectedLanguage
      : 'en-IN'

    try {
      const response = await fetch(
        `${API}/news/${selectedNews.id}/listen?target_language=${encodeURIComponent(audioLanguage)}`,
        {
          method: 'POST'
        }
      )

      if (!response.ok) {
        let errorMessage = 'Audio generate nahi ho paya.'

        try {
          const data = await response.json()
          errorMessage = data.detail || errorMessage
        } catch {
          // Keep default error message
        }

        throw new Error(errorMessage)
      }

      const audioBlob = await response.blob()

      if (!audioBlob.size) {
        throw new Error('Generated audio is empty.')
      }

      const newAudioUrl = URL.createObjectURL(audioBlob)
      setAudioUrl(newAudioUrl)

    } catch (err) {
      setAudioError(
        err.message || 'Audio generate nahi ho paya. Dobara try karein.'
      )
    } finally {
      setAudioLoading(false)
    }
  }

  function closeNews() {
    setSelectedNews(null)
    setRelatedNews([])
    setRelatedError('')
    setTranslatedArticle(null)
    setShowTranslation(false)
    setTranslationError('')
    resetAudio()
  }

  // Toggle podcast category
  function togglePodcastCategory(category) {
    setPodcastCategories(previous => {
      if (previous.includes(category)) {
        return previous.filter(item => item !== category)
      }

      return [...previous, category]
    })
  }

  // Generate podcast
  async function generatePodcast() {
    if (podcastLoading) return

    setPodcastLoading(true)
    setPodcastError('')
    setPodcastData(null)
    setPodcastAudioUrl('')

    try {
      const response = await fetch(`${API}/podcast/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          categories: podcastCategories,
          language_code: podcastLanguage,
          duration: Number(podcastDuration)
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Podcast generation failed')
      }

      if (!data.audio_base64 || !data.transcript) {
        throw new Error('Podcast audio or transcript is missing.')
      }

      const audioBlob = await fetch(
        `data:${data.audio_mime_type || 'audio/mpeg'};base64,${data.audio_base64}`
      ).then(result => result.blob())

      if (!audioBlob.size) {
        throw new Error('Generated podcast audio is empty.')
      }

      const newAudioUrl = URL.createObjectURL(audioBlob)

      setPodcastData(data)
      setPodcastAudioUrl(newAudioUrl)

    } catch (err) {
      setPodcastError(
        err.message || 'Podcast generate nahi ho paya. Dobara try karein.'
      )
    } finally {
      setPodcastLoading(false)
    }
  }

  // Send message to Sarvam chatbot
  async function sendChatMessage(event) {
    event?.preventDefault()

    const message = chatInput.trim()

    if (!message || chatLoading) return

    setChatError('')
    setChatInput('')

    setChatMessages(previous => [
      ...previous,
      {
        role: 'user',
        text: message
      }
    ])

    setChatLoading(true)

    try {
      const response = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          message: message,
          language_code: chatLanguage
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to get chatbot response')
      }

      if (!data.response) {
        throw new Error('Empty response received from chatbot')
      }

      setChatMessages(previous => [
        ...previous,
        {
          role: 'assistant',
          text: data.response
        }
      ])

    } catch (err) {
      setChatError(
        err.message || 'Something went wrong. Please try again.'
      )
    } finally {
      setChatLoading(false)
    }
  }

  function clearChat() {
    if (chatLoading) return

    setChatMessages([])
    setChatError('')
    setChatInput('')
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

  function formatTimelineDate(date) {
    const parsedDate = new Date(`${date}T00:00:00`)

    return parsedDate.toLocaleDateString('en-IN', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  const displayedTitle = showTranslation && translatedArticle
    ? translatedArticle.title
    : selectedNews?.title

  const displayedContent = showTranslation && translatedArticle
    ? translatedArticle.content
    : selectedNews?.content || selectedNews?.description

  const displayedDescription = showTranslation && translatedArticle
    ? translatedArticle.description
    : selectedNews?.description

  return (
    <div className="app">

      {/* HEADER */}
      <header className="header">
        <div className="header-inner">

          <button
            className="hamburger-button"
            onClick={() => setMenuOpen(previous => !previous)}
            aria-label="Open navigation menu"
            aria-expanded={menuOpen}
          >
            <span></span>
            <span></span>
            <span></span>
          </button>

          <a
            className="brand"
            href="/"
            onClick={e => {
              e.preventDefault()
              navigateTo('home')
            }}
          >
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

      {/* LEFT NAVIGATION DRAWER */}
      {menuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMenuOpen(false)}
        ></div>
      )}

      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div>
            <span className="brand-icon">BB</span>
            <strong>Bharat Brief</strong>
          </div>

          <button
            className="sidebar-close"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <div className="sidebar-label">MAIN MENU</div>

        <button
          className={`sidebar-link ${activeView === 'home' ? 'sidebar-active' : ''}`}
          onClick={() => navigateTo('home')}
        >
          <span>⌂</span>
          Home
        </button>

        <button
          className={`sidebar-link ${activeView === 'latest' ? 'sidebar-active' : ''}`}
          onClick={() => navigateTo('latest')}
        >
          <span>▤</span>
          Latest News
        </button>

        <button
          className={`sidebar-link ${activeView === 'podcast' ? 'sidebar-active' : ''}`}
          onClick={() => navigateTo('podcast')}
        >
          <span>🎙️</span>
          My Podcast
        </button>

        <button
          className={`sidebar-link ${activeView === 'timeline' ? 'sidebar-active' : ''}`}
          onClick={() => navigateTo('timeline')}
        >
          <span>◷</span>
          News Timeline
        </button>

        <div className="sidebar-divider"></div>

        <div className="sidebar-info">
          <span className="sidebar-info-icon">✦</span>
          <strong>Stay Informed</strong>
          <p>Reliable updates directly from official government sources.</p>
        </div>

        <div className="sidebar-footer">
          <span>BHARAT BRIEF</span>
          <p>Official News Platform</p>
        </div>
      </aside>

      <main className="container">

        {/* HOME VIEW */}
        {activeView === 'home' && (
          <>
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

            {/* HOME TIMELINE PREVIEW */}
            <section className="timeline-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">EXPLORE NEWS HISTORY</span>
                  <h2>News Timeline</h2>
                  <p>Explore government updates day by day</p>
                </div>

                <button
                  className="original-button"
                  onClick={() => navigateTo('timeline')}
                >
                  View All →
                </button>
              </div>

              {timelineLoading && (
                <div className="message">Loading news timeline...</div>
              )}

              {timelineError && (
                <div className="message error">{timelineError}</div>
              )}

              {!timelineLoading && !timelineError && timeline.length === 0 && (
                <div className="message">No timeline articles available.</div>
              )}

              {!timelineLoading && !timelineError && timeline.length > 0 && (
                <div className="timeline-list">
                  {timeline.slice(0, 3).map(day => (
                    <div className="timeline-day" key={day.date}>
                      <div className="timeline-date">
                        <span className="timeline-dot"></span>
                        <h3>{formatTimelineDate(day.date)}</h3>
                        <span className="timeline-count">
                          {day.total_news} Articles
                        </span>
                      </div>

                      <div className="timeline-news-list">
                        {day.news.slice(0, 3).map(item => (
                          <article className="timeline-news-card" key={item.id}>
                            <div className="timeline-card-top">
                              <span className="category-tag">
                                {item.category || 'Uncategorized'}
                              </span>
                              <span className="date">
                                {formatDate(item.published_date)}
                              </span>
                            </div>

                            <h4>{item.title}</h4>

                            <p>
                              {item.description || 'Read the full official article for more information.'}
                            </p>

                            <button onClick={() => openNews(item)}>
                              Read Article →
                            </button>
                          </article>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        {/* LATEST NEWS VIEW */}
        {activeView === 'latest' && (
          <section className="news-section page-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">OFFICIAL PIB UPDATES</span>
                <h2>Latest News</h2>
                <p>Browse and search government news updates.</p>
              </div>
              <span className="news-count">{filteredNews.length} Articles</span>
            </div>

            <div className="search-box">
              <span>⌕</span>
              <input
                type="text"
                placeholder="Search news by title..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
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
        )}

        {/* PODCAST VIEW */}
        {activeView === 'podcast' && (
          <section className="podcast-section page-section">
            <div className="podcast-page-hero">
              <span className="eyebrow">YOUR PERSONAL NEWS EXPERIENCE</span>
              <h1>My Podcast <span>🎙️</span></h1>
              <p>
                Turn the latest government news into your own multilingual
                audio podcast.
              </p>
            </div>

            <div className="podcast-builder">
              <div className="podcast-builder-heading">
                <span className="podcast-step">01</span>
                <div>
                  <h3>Customize Your Podcast</h3>
                  <p>Choose what you want to listen to.</p>
                </div>
              </div>

              <p className="podcast-help">
                Select one or more news categories. Leave all unchecked
                to include all available news.
              </p>

              <div className="podcast-category-grid">
                {categories.filter(category => category !== 'All News').map(category => (
                  <label className="podcast-category-option" key={category}>
                    <input
                      type="checkbox"
                      checked={podcastCategories.includes(category)}
                      onChange={() => togglePodcastCategory(category)}
                      disabled={podcastLoading}
                    />
                    <span>{category}</span>
                  </label>
                ))}
              </div>

              <div className="podcast-settings">
                <div className="podcast-setting">
                  <label htmlFor="podcast-language">Podcast Language</label>
                  <select
                    id="podcast-language"
                    value={podcastLanguage}
                    onChange={e => setPodcastLanguage(e.target.value)}
                    disabled={podcastLoading}
                  >
                    {podcastLanguages.map(language => (
                      <option key={language.code} value={language.code}>
                        {language.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="podcast-setting">
                  <label htmlFor="podcast-duration">Target Duration</label>
                  <select
                    id="podcast-duration"
                    value={podcastDuration}
                    onChange={e => setPodcastDuration(Number(e.target.value))}
                    disabled={podcastLoading}
                  >
                    {[1, 2, 3, 5, 7, 10, 15].map(duration => (
                      <option key={duration} value={duration}>
                        {duration} Minutes
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                className="podcast-generate-button"
                onClick={generatePodcast}
                disabled={podcastLoading}
              >
                {podcastLoading ? 'Generating Your Podcast...' : '🎙️ Generate Podcast'}
              </button>

              {podcastLoading && (
                <div className="message">
                  AI is preparing your news script and generating audio.
                  Please wait. This may take a little time.
                </div>
              )}

              {podcastError && (
                <div className="message error">{podcastError}</div>
              )}
            </div>

            {podcastData && (
              <div className="podcast-result">
                <div className="podcast-result-heading">
                  <span className="eyebrow">YOUR PODCAST IS READY</span>
                  <h3>Today's News Podcast</h3>
                  <p>
                    {podcastData.total_articles} news articles included
                    {' • '}
                    {podcastLanguages.find(
                      language => language.code === podcastData.language_code
                    )?.name || podcastData.language_code}
                  </p>
                </div>

                {podcastAudioUrl && (
                  <div className="podcast-audio-player">
                    <div className="audio-speed-control">
                      <label htmlFor="podcast-speed">Playback Speed</label>
                      <select
                        id="podcast-speed"
                        value={podcastAudioSpeed}
                        onChange={e => setPodcastAudioSpeed(Number(e.target.value))}
                      >
                        {audioSpeeds.map(speed => (
                          <option key={speed} value={speed}>{speed}x</option>
                        ))}
                      </select>
                    </div>

                    <audio
                      ref={podcastAudioRef}
                      key={podcastAudioUrl}
                      controls
                      autoPlay
                      preload="metadata"
                      src={podcastAudioUrl}
                      onLoadedMetadata={e => {
                        e.currentTarget.playbackRate = podcastAudioSpeed
                      }}
                    >
                      Your browser does not support audio playback.
                    </audio>
                  </div>
                )}

                <div className="podcast-transcript">
                  <h3>Podcast Transcript</h3>
                  <p>{podcastData.transcript}</p>
                </div>

                <div className="podcast-sources">
                  <h3>News Sources</h3>

                  {podcastData.sources?.length > 0 ? (
                    <div className="podcast-source-list">
                      {podcastData.sources.map(source => (
                        <article className="podcast-source-card" key={source.id}>
                          <span className="category-tag">
                            {source.category || 'Uncategorized'}
                          </span>

                          <h4>{source.title}</h4>

                          <p>
                            {source.source || 'PIB India'}
                            {' • '}
                            {formatDate(source.published_date)}
                          </p>

                          {source.url && (
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Read Original Article →
                            </a>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p>No source articles available.</p>
                  )}
                </div>
              </div>
            )}
          </section>
        )}

        {/* TIMELINE VIEW */}
        {activeView === 'timeline' && (
          <section className="timeline-section page-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">EXPLORE NEWS HISTORY</span>
                <h2>News Timeline</h2>
                <p>Explore government updates day by day.</p>
              </div>
              <span className="news-count">
                {timeline.reduce((total, day) => total + day.total_news, 0)} Articles
              </span>
            </div>

            {timelineLoading && (
              <div className="message">Loading news timeline...</div>
            )}

            {timelineError && (
              <div className="message error">{timelineError}</div>
            )}

            {!timelineLoading && !timelineError && timeline.length === 0 && (
              <div className="message">No timeline articles available.</div>
            )}

            {!timelineLoading && !timelineError && timeline.length > 0 && (
              <div className="timeline-list">
                {timeline.map(day => (
                  <div className="timeline-day" key={day.date}>
                    <div className="timeline-date">
                      <span className="timeline-dot"></span>
                      <h3>{formatTimelineDate(day.date)}</h3>
                      <span className="timeline-count">
                        {day.total_news} Articles
                      </span>
                    </div>

                    <div className="timeline-news-list">
                      {day.news.map(item => (
                        <article className="timeline-news-card" key={item.id}>
                          <div className="timeline-card-top">
                            <span className="category-tag">
                              {item.category || 'Uncategorized'}
                            </span>
                            <span className="date">
                              {formatDate(item.published_date)}
                            </span>
                          </div>

                          <h4>{item.title}</h4>

                          <p>
                            {item.description || 'Read the full official article for more information.'}
                          </p>

                          <button onClick={() => openNews(item)}>
                            Read Article →
                          </button>
                        </article>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="footer">
        <strong>Bharat Brief</strong>
        <p>Official news. Reliable information. One platform.</p>
        <span>News source: Press Information Bureau, Government of India</span>
      </footer>

      {/* ARTICLE DETAIL MODAL */}
      {selectedNews && (
        <div className="modal-backdrop" onClick={closeNews}>
          <article className="article-modal" onClick={e => e.stopPropagation()}>
            <button
              className="close-button"
              onClick={closeNews}
            >
              ✕
            </button>

            <span className="source-tag">PRESS INFORMATION BUREAU</span>

            <h2>{displayedTitle}</h2>

            <p className="modal-date">
              {formatDate(selectedNews.published_date)}
            </p>

            {/* Translation controls */}
            <section className="translation-controls">
              <label htmlFor="language-select">
                Translate article into:
              </label>

              <div className="translation-actions">
                <select
                  id="language-select"
                  value={selectedLanguage}
                  onChange={e => {
                    setSelectedLanguage(e.target.value)
                    setTranslatedArticle(null)
                    setShowTranslation(false)
                    setTranslationError('')
                    resetAudio()
                  }}
                  disabled={translationLoading}
                >
                  {languages.map(language => (
                    <option key={language.code} value={language.code}>
                      {language.name}
                    </option>
                  ))}
                </select>

                <button
                  className="translate-button"
                  onClick={translateArticle}
                  disabled={translationLoading || languages.length === 0}
                >
                  {translationLoading ? 'Translating...' : 'Translate Article'}
                </button>
              </div>

              {translationError && (
                <div className="message error">{translationError}</div>
              )}

              {translationLoading && (
                <div className="message">
                  Translating complete article. Please wait...
                </div>
              )}

              {showTranslation && translatedArticle && (
                <div className="translation-status">
                  <span>
                    Translated into {languages.find(
                      language => language.code === selectedLanguage
                    )?.name || selectedLanguage}
                  </span>

                  <button
                    className="original-button"
                    onClick={showOriginalArticle}
                  >
                    Show Original
                  </button>
                </div>
              )}
            </section>

            {/* Article audio */}
            <section className="listen-section">
              <div className="listen-heading">
                <div>
                  <span className="eyebrow">AUDIO EXPERIENCE</span>
                  <h3>Listen to News</h3>
                  <p>
                    {showTranslation
                      ? `Audio language: ${languages.find(
                          language => language.code === selectedLanguage
                        )?.name || selectedLanguage}`
                      : 'Audio language: English'}
                  </p>
                </div>
              </div>

              <button
                className="listen-button"
                onClick={listenToNews}
                disabled={audioLoading || detailLoading}
              >
                {audioLoading
                  ? 'Generating Audio...'
                  : audioUrl
                    ? 'Generate Again'
                    : '▶ Listen to News'}
              </button>

              {audioLoading && (
                <div className="message">
                  Generating news audio. Please wait...
                </div>
              )}

              {audioError && (
                <div className="message error">{audioError}</div>
              )}

              {audioUrl && (
                <div className="audio-player">
                  <div className="audio-speed-control">
                    <label htmlFor="article-speed">Playback Speed</label>
                    <select
                      id="article-speed"
                      value={articleAudioSpeed}
                      onChange={e => setArticleAudioSpeed(Number(e.target.value))}
                    >
                      {audioSpeeds.map(speed => (
                        <option key={speed} value={speed}>{speed}x</option>
                      ))}
                    </select>
                  </div>

                  <audio
                    ref={articleAudioRef}
                    key={audioUrl}
                    controls
                    autoPlay
                    preload="metadata"
                    src={audioUrl}
                    onLoadedMetadata={e => {
                      e.currentTarget.playbackRate = articleAudioSpeed
                    }}
                  >
                    Your browser does not support audio playback.
                  </audio>
                </div>
              )}
            </section>

            {displayedDescription && (
              <p className="article-description">
                {displayedDescription}
              </p>
            )}

            <div className="article-content">
              {detailLoading
                ? 'Loading full article...'
                : detailError
                  ? detailError
                  : displayedContent || 'Full article content unavailable.'}
            </div>

            <a
              className="source-link"
              href={selectedNews.url}
              target="_blank"
              rel="noreferrer"
            >
              Read Original PIB Article ↗
            </a>

            {/* Related News */}
            <section className="related-section">
              <div className="related-heading">
                <span className="eyebrow">EXPLORE MORE</span>
                <h3>Related News</h3>
                <p>More stories related to this article</p>
              </div>

              {relatedLoading && (
                <div className="message">Finding related news...</div>
              )}

              {relatedError && (
                <div className="message error">{relatedError}</div>
              )}

              {!relatedLoading && !relatedError && relatedNews.length === 0 && (
                <div className="message">
                  No related articles found for this news.
                </div>
              )}

              {!relatedLoading && relatedNews.length > 0 && (
                <div className="related-news-list">
                  {relatedNews.map(item => (
                    <article className="related-news-card" key={item.id}>
                      <div className="related-card-info">
                        <span className="category-tag">
                          {item.category || 'Uncategorized'}
                        </span>

                        <span className="date">
                          {formatDate(item.published_date)}
                        </span>
                      </div>

                      <h4>{item.title}</h4>

                      <p>
                        {item.description || 'Read the full article for more information.'}
                      </p>

                      <div className="related-card-bottom">
                        <span className="similarity-score">
                          Relevance: {(item.similarity_score * 100).toFixed(2)}%
                        </span>

                        <button onClick={() => openNews(item)}>
                          Read Article →
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </article>
        </div>
      )}

      {/* FLOATING AI CHATBOT */}
      <div style={chatStyles.container}>
        {chatOpen && (
          <section style={chatStyles.panel}>
            <div style={chatStyles.header}>
              <div>
                <div style={chatStyles.title}>Bharat Brief AI</div>
                <div style={chatStyles.subtitle}>Powered by Sarvam AI</div>
              </div>

              <div style={chatStyles.headerActions}>
                <button
                  type="button"
                  style={chatStyles.headerButton}
                  onClick={clearChat}
                  disabled={chatLoading}
                  title="Clear conversation"
                >
                  ↻
                </button>

                <button
                  type="button"
                  style={chatStyles.headerButton}
                  onClick={() => setChatOpen(false)}
                  title="Close chatbot"
                >
                  ✕
                </button>
              </div>
            </div>

            <div style={chatStyles.languageArea}>
              <label htmlFor="chat-language" style={chatStyles.languageLabel}>
                Response language
              </label>

              <select
                id="chat-language"
                style={chatStyles.languageSelect}
                value={chatLanguage}
                onChange={e => setChatLanguage(e.target.value)}
                disabled={chatLoading}
              >
                {chatLanguages.map(language => (
                  <option key={language.code} value={language.code}>
                    {language.name}
                  </option>
                ))}
              </select>
            </div>

            <div style={chatStyles.messages}>
              {chatMessages.length === 0 && (
                <div style={chatStyles.welcome}>
                  <div style={chatStyles.welcomeIcon}>✦</div>
                  <h3 style={chatStyles.welcomeTitle}>
                    Hello! Welcome to Bharat Brief.
                  </h3>
                  <p style={chatStyles.welcomeText}>
                    Ask me anything about education, coding, science,
                    technology, news or general knowledge.
                  </p>
                  <p style={chatStyles.welcomeHint}>
                    Aap apna question kisi bhi supported language mein pooch sakte hain.
                  </p>
                </div>
              )}

              {chatMessages.map((message, index) => (
                <div
                  key={index}
                  style={{
                    ...chatStyles.messageRow,
                    justifyContent: message.role === 'user'
                      ? 'flex-end'
                      : 'flex-start'
                  }}
                >
                  <div
                    style={{
                      ...chatStyles.messageBubble,
                      ...(message.role === 'user'
                        ? chatStyles.userBubble
                        : chatStyles.assistantBubble)
                    }}
                  >
                    {message.text}
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div style={chatStyles.typing}>
                  Bharat Brief AI is thinking...
                </div>
              )}
            </div>

            {chatError && (
              <div style={chatStyles.error}>{chatError}</div>
            )}

            <form style={chatStyles.inputArea} onSubmit={sendChatMessage}>
              <textarea
                style={chatStyles.input}
                placeholder="Type your message..."
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    sendChatMessage(e)
                  }
                }}
                rows={2}
                disabled={chatLoading}
              />

              <button
                type="submit"
                style={{
                  ...chatStyles.sendButton,
                  opacity: chatLoading || !chatInput.trim() ? 0.5 : 1
                }}
                disabled={chatLoading || !chatInput.trim()}
              >
                ➤
              </button>
            </form>

            <div style={chatStyles.footer}>
              AI responses may occasionally be inaccurate. Verify important information.
            </div>
          </section>
        )}

        <button
          type="button"
          style={chatStyles.floatingButton}
          onClick={() => setChatOpen(previous => !previous)}
          aria-label="Open Bharat Brief AI chatbot"
        >
          {chatOpen ? '✕' : '✦'}
          {!chatOpen && <span style={chatStyles.buttonLabel}>Ask AI</span>}
        </button>
      </div>

      {showAuth && (
        <Auth
          onAuthenticated={handleAuthenticated}
          onClose={() => setShowAuth(false)}
        />
      )}
    </div>
  )
}

const chatStyles = {
  container: {
    position: 'fixed',
    right: '24px',
    bottom: '24px',
    zIndex: 2000,
    fontFamily: 'inherit'
  },
  panel: {
    position: 'absolute',
    right: 0,
    bottom: '76px',
    width: 'min(380px, calc(100vw - 32px))',
    height: 'min(560px, calc(100vh - 120px))',
    background: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '16px',
    boxShadow: '0 12px 45px rgba(0,0,0,0.18)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  },
  header: {
    background: '#173b68',
    color: '#ffffff',
    padding: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  title: {
    fontSize: '17px',
    fontWeight: '700'
  },
  subtitle: {
    fontSize: '12px',
    opacity: 0.8,
    marginTop: '3px'
  },
  headerActions: {
    display: 'flex',
    gap: '8px'
  },
  headerButton: {
    border: '1px solid rgba(255,255,255,0.35)',
    background: 'transparent',
    color: '#ffffff',
    borderRadius: '7px',
    padding: '6px 10px',
    cursor: 'pointer',
    fontSize: '15px'
  },
  languageArea: {
    padding: '10px 14px',
    background: '#f8fafc',
    borderBottom: '1px solid #e5e7eb'
  },
  languageLabel: {
    display: 'block',
    fontSize: '12px',
    fontWeight: '600',
    marginBottom: '5px',
    color: '#475569'
  },
  languageSelect: {
    width: '100%',
    padding: '8px',
    borderRadius: '7px',
    border: '1px solid #cbd5e1',
    background: '#ffffff',
    fontSize: '13px',
    color: '#1e293b'
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '14px',
    background: '#f8fafc'
  },
  welcome: {
    textAlign: 'center',
    padding: '30px 12px'
  },
  welcomeIcon: {
    fontSize: '32px',
    color: '#2563eb'
  },
  welcomeTitle: {
    fontSize: '17px',
    color: '#173b68',
    margin: '12px 0 8px'
  },
  welcomeText: {
    fontSize: '13px',
    lineHeight: 1.6,
    color: '#475569'
  },
  welcomeHint: {
    fontSize: '12px',
    color: '#64748b',
    lineHeight: 1.5
  },
  messageRow: {
    display: 'flex',
    marginBottom: '12px'
  },
  messageBubble: {
    maxWidth: '88%',
    padding: '10px 12px',
    borderRadius: '12px',
    fontSize: '13px',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
    overflowWrap: 'anywhere'
  },
  userBubble: {
    background: '#173b68',
    color: '#ffffff',
    borderBottomRightRadius: '3px'
  },
  assistantBubble: {
    background: '#ffffff',
    color: '#1e293b',
    border: '1px solid #e2e8f0',
    borderBottomLeftRadius: '3px'
  },
  typing: {
    fontSize: '12px',
    color: '#64748b',
    padding: '8px 4px'
  },
  error: {
    padding: '8px 12px',
    color: '#b91c1c',
    background: '#fef2f2',
    fontSize: '12px'
  },
  inputArea: {
    display: 'flex',
    gap: '8px',
    padding: '12px',
    borderTop: '1px solid #e5e7eb',
    background: '#ffffff',
    alignItems: 'flex-end'
  },
  input: {
    flex: 1,
    minWidth: 0,
    resize: 'none',
    border: '1px solid #cbd5e1',
    borderRadius: '9px',
    padding: '10px',
    fontFamily: 'inherit',
    fontSize: '13px',
    outline: 'none'
  },
  sendButton: {
    background: '#173b68',
    color: '#ffffff',
    border: 'none',
    borderRadius: '9px',
    padding: '11px 14px',
    fontSize: '17px',
    cursor: 'pointer'
  },
  footer: {
    textAlign: 'center',
    padding: '7px 10px',
    fontSize: '10px',
    color: '#64748b',
    background: '#ffffff'
  },
  floatingButton: {
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    border: 'none',
    background: '#173b68',
    color: '#ffffff',
    boxShadow: '0 5px 20px rgba(23,59,104,0.35)',
    cursor: 'pointer',
    fontSize: '24px',
    fontWeight: '700',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '5px'
  },
  buttonLabel: {
    fontSize: '12px'
  }
}

export default App
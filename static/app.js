// ==============================================
// SPA ROUTER - Для непрерывного воспроизведения
// ==============================================

const Router = {
  routes: {},
  currentRoute: null,
  
  init() {
    // Перехватываем клики по ссылкам
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href^="/"]');
      if (link && !link.hasAttribute('data-no-spa')) {
        const href = link.getAttribute('href');
        // Исключаем административные и auth роуты
        if (!href.startsWith('/admin') && !href.startsWith('/auth')) {
          e.preventDefault();
          this.navigate(href);
        }
      }
    });
    
    // Обрабатываем кнопки назад/вперед
    window.addEventListener('popstate', (e) => {
      if (e.state && e.state.url) {
        this.loadRoute(e.state.url, false);
      }
    });
  },
  
  navigate(url, pushState = true) {
    if (pushState && url !== this.currentRoute) {
      history.pushState({ url }, '', url);
    }
    this.loadRoute(url, pushState);
  },
  
  async loadRoute(url, pushState = true) {
    this.currentRoute = url;
    
    try {
      // Загружаем HTML страницы
      const response = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      
      if (!response.ok) {
        throw new Error('Page not found');
      }
      
      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      
      // Извлекаем контент
      const newHero = doc.querySelector('.hero');
      const newContent = doc.querySelector('.content');
      
      if (newHero && newContent) {
        // Обновляем только контент, не трогая плеер и сайдбар
        const heroEl = document.querySelector('.hero');
        const contentEl = document.querySelector('.content');
        
        if (heroEl) heroEl.innerHTML = newHero.innerHTML;
        if (contentEl) contentEl.innerHTML = newContent.innerHTML;
        
        // Обновляем активную ссылку в навигации
        this.updateActiveNav(url);
        
        // Обновляем данные из SERVER_DATA если они есть
        const scripts = doc.querySelectorAll('script');
        scripts.forEach(script => {
          if (script.textContent.includes('window.SERVER_DATA')) {
            eval(script.textContent);
            if (window.SERVER_DATA) {
              tracks = window.SERVER_DATA.tracks || tracks;
              playlists = window.SERVER_DATA.playlists || playlists;
              genres = window.SERVER_DATA.genres || genres;
              state.originalTracks = tracks;
            }
          }
        });
        
        // Переинициализируем обработчики событий
        this.reinitializeHandlers();
      }
      
      // Прокручиваем наверх
      const contentScroll = document.querySelector('.content');
      if (contentScroll) contentScroll.scrollTop = 0;
      
    } catch (error) {
      console.error('Navigation error:', error);
    }
  },
  
  updateActiveNav(url) {
    // Убираем активный класс со всех ссылок
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    
    // Добавляем активный класс к текущей ссылке
    const activeLink = document.querySelector(`.nav-btn[href="${url}"]`);
    if (activeLink) {
      activeLink.classList.add('active');
    }
  },
  
  reinitializeHandlers() {
    // Переинициализируем обработчики для треков
    document.querySelectorAll('.track-row').forEach(row => {
      const trackId = parseInt(row.getAttribute('data-id'));
      
      const titleEl = row.querySelector('.track-title');
      const coverEl = row.querySelector('.track-cover');
      
      if (titleEl) titleEl.onclick = () => playTrack(trackId);
      if (coverEl) coverEl.onclick = () => playTrack(trackId);
      
      const likeBtn = row.querySelector('.like-btn');
      if (likeBtn) {
        likeBtn.onclick = (e) => {
          e.stopPropagation();
          toggleLike(trackId);
        };
      }
      
      const queueBtn = row.querySelector('.queue-add');
      if (queueBtn) {
        queueBtn.onclick = (e) => {
          e.stopPropagation();
          addToQueue(trackId);
        };
      }
      
      const addPlBtn = row.querySelector('.add-to-pl');
      if (addPlBtn) {
        addPlBtn.onclick = (e) => {
          e.stopPropagation();
          showAddToPlaylistMenu(trackId);
        };
      }
    });
    
    // Переинициализируем плитки плейлистов
    document.querySelectorAll('.tile[data-playlist-id]').forEach(tile => {
      const playlistId = tile.getAttribute('data-playlist-id');
      tile.onclick = (e) => {
        e.preventDefault();
        Router.navigate(`/playlist/${playlistId}`);
      };
    });
    
    // Переинициализируем формы поиска
    const searchForms = document.querySelectorAll('form[action*="search"]');
    searchForms.forEach(form => {
      form.onsubmit = (e) => {
        e.preventDefault();
        const query = form.querySelector('input[name="q"]').value;
        Router.navigate(`/search?q=${encodeURIComponent(query)}`);
      };
    });
  }
};

// ==============================================
// ОСНОВНОЙ КОД ПРИЛОЖЕНИЯ
// ==============================================

const DATA = window.SERVER_DATA || {tracks: [], playlists: [], genres: []};
let tracks = DATA.tracks || [];
let playlists = DATA.playlists || [];
let genres = DATA.genres || [];

const audio = document.getElementById('audio');
const trackListEl = document.getElementById('track-list');
const tilesEl = document.getElementById('tiles');
const heroInner = document.getElementById('hero-inner');
const contentTitle = document.getElementById('content-title');
const searchInput = document.getElementById('search-input');

// Player controls
const playBtn = document.getElementById('play-btn');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const shuffleBtn = document.getElementById('shuffle-btn');
const repeatBtn = document.getElementById('repeat-btn');
const muteBtn = document.getElementById('mute-btn');
const volumeRange = document.getElementById('volume');
const timeCurrent = document.getElementById('time-current');
const timeDuration = document.getElementById('time-duration');
const progressBar = document.getElementById('progress-bar');
const progress = document.getElementById('progress');
const nowPlayingEl = document.getElementById('now-playing');

// State
let state = {
  currentTrack: null,
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: parseFloat(volumeRange?.value || 0.7),
  isMuted: false,
  isShuffle: false,
  repeatMode: 0,
  liked: new Set(),
  queue: [],
  history: [],
  view: 'home',
  searchQuery: '',
  currentPlaylist: null,
  currentGenre: null,
  originalTracks: DATA.tracks || []
};

// Load liked tracks from API
async function loadLikedTracks() {
  try {
    const res = await fetch('/api/user/liked');
    if (res.ok) {
      const likedTracks = await res.json();
      state.liked = new Set(likedTracks.map(t => t.id));
    }
  } catch (e) {
    console.log('Not logged in or error loading liked tracks');
  }
}

// Utilities
function formatTime(sec) {
  if (!sec || isNaN(sec)) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

async function apiCall(url, options = {}) {
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    return res.ok ? await res.json() : null;
  } catch (e) {
    console.error('API Error:', e);
    return null;
  }
}

// Сохраняем состояние плеера
function savePlayerState() {
  if (state.currentTrack) {
    const playerState = {
      trackId: state.currentTrack.id,
      currentTime: audio.currentTime,
      isPlaying: !audio.paused,
      volume: audio.volume
    };
    localStorage.setItem('playerState', JSON.stringify(playerState));
  }
}

// Восстанавливаем состояние плеера
function restorePlayerState() {
  const saved = localStorage.getItem('playerState');
  if (saved) {
    try {
      const playerState = JSON.parse(saved);
      const track = state.originalTracks.find(t => t.id === playerState.trackId);
      if (track) {
        state.currentTrack = track;
        audio.src = track.media;
        audio.currentTime = playerState.currentTime || 0;
        audio.volume = playerState.volume || 0.7;
        
        renderNowPlaying();
        
        if (playerState.isPlaying) {
          setTimeout(() => {
            audio.play().catch(e => {
              console.log('Cannot autoplay:', e);
              playBtn && (playBtn.textContent = '▶');
            });
          }, 500);
        }
      }
    } catch (e) {
      console.log('Error restoring player state:', e);
    }
  }
}

// Авто-продолжение при возвращении на вкладку
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    const saved = localStorage.getItem('playerState');
    if (saved) {
      try {
        const playerState = JSON.parse(saved);
        if (playerState.isPlaying && audio.src) {
          audio.play().catch(e => {
            console.log('Autoplay prevented');
          });
        }
      } catch (e) {
        console.log('Error restoring playback:', e);
      }
    }
  } else {
    savePlayerState();
  }
});

// Сохраняем состояние при изменениях
audio.addEventListener('timeupdate', savePlayerState);
audio.addEventListener('play', savePlayerState);
audio.addEventListener('pause', savePlayerState);
audio.addEventListener('volumechange', savePlayerState);

function renderNowPlaying() {
  if (!nowPlayingEl) return;
  
  if (state.currentTrack) {
    const t = state.currentTrack;
    const isLiked = state.liked.has(t.id);
    
    nowPlayingEl.innerHTML = `
      <div style="display:flex;gap:12px;align-items:center;min-width:0">
        <div class="track-cover" style="width:56px;height:56px;background:${t.gradient}">${t.cover}</div>
        <div style="min-width:0;flex:1">
          <div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.title}</div>
          <div style="color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.artist}</div>
        </div>
        <button class="like-btn-player" style="background:none;border:none;font-size:20px;cursor:pointer;opacity:0.8;transition:opacity 0.2s" onclick="toggleLike(${t.id})">${isLiked ? '💚' : '🤍'}</button>
      </div>`;
  } else {
    nowPlayingEl.innerHTML = '<div style="color:var(--muted)">No track playing</div>';
  }
}

// Playback functions
function setAudioForTrack(t) {
  audio.src = t.media || '';
  audio.currentTime = 0;
  state.duration = t.duration || 0;
  timeDuration && (timeDuration.textContent = formatTime(state.duration));
  
  if ('mediaSession' in navigator) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t.title,
      artist: t.artist,
      album: t.album,
      artwork: [
        { 
          src: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="%237d3aed"/><text x="50" y="60" font-size="40" text-anchor="middle" fill="white">' + t.cover + '</text></svg>', 
          sizes: '96x96', 
          type: 'image/svg+xml' 
        }
      ]
    });
  }
}

async function playTrack(id) {
  const t = state.originalTracks.find(x => x.id === id);
  if (!t) return;
  
  if (state.currentTrack) state.history.push(state.currentTrack);
  state.currentTrack = t;
  
  setAudioForTrack(t);
  audio.volume = state.isMuted ? 0 : state.volume;
  
  try {
    await audio.play();
    state.isPlaying = true;
    playBtn && (playBtn.textContent = '❚❚');
    
    await apiCall(`/api/tracks/${id}/play`, { method: 'POST' });
    
    renderNowPlaying();
    savePlayerState();
  } catch (e) {
    state.isPlaying = false;
    playBtn && (playBtn.textContent = '▶');
  }
}

function togglePlay() {
  if (!state.currentTrack) {
    if (state.originalTracks.length > 0) {
      playTrack(state.originalTracks[0].id);
    }
    return;
  }
  
  if (state.isPlaying) {
    audio.pause();
    state.isPlaying = false;
    playBtn && (playBtn.textContent = '▶');
  } else {
    audio.play();
    state.isPlaying = true;
    playBtn && (playBtn.textContent = '❚❚');
  }
  savePlayerState();
}

function handleNext() {
  if (state.queue.length > 0) {
    const next = state.queue.shift();
    playTrack(next.id);
    return;
  }
  
  if (!state.currentTrack) return;
  
  const idx = state.originalTracks.findIndex(t => t.id === state.currentTrack.id);
  let nextIdx;
  
  if (state.isShuffle) {
    nextIdx = Math.floor(Math.random() * state.originalTracks.length);
  } else {
    nextIdx = (idx + 1) % state.originalTracks.length;
  }
  
  if (state.repeatMode === 2) {
    playTrack(state.currentTrack.id);
    return;
  }
  
  playTrack(state.originalTracks[nextIdx].id);
}

function handlePrev() {
  if (!state.currentTrack) return;
  
  if (audio.currentTime > 3) {
    audio.currentTime = 0;
    return;
  }
  
  const idx = state.originalTracks.findIndex(t => t.id === state.currentTrack.id);
  const prevIdx = (idx - 1 + state.originalTracks.length) % state.originalTracks.length;
  playTrack(state.originalTracks[prevIdx].id);
}

function addToQueue(id) {
  const t = state.originalTracks.find(x => x.id === id);
  if (t) {
    state.queue.push(t);
    showNotification(`Added "${t.title}" to queue`);
  }
}

async function toggleLike(id) {
  const res = await apiCall(`/api/tracks/${id}/like`, { method: 'POST' });
  
  if (res) {
    if (res.liked) {
      state.liked.add(id);
      showNotification('Added to Liked Songs');
    } else {
      state.liked.delete(id);
      showNotification('Removed from Liked Songs');
    }
    
    // Обновляем кнопки лайков на странице
    document.querySelectorAll(`.like-btn`).forEach(btn => {
      const row = btn.closest('.track-row');
      if (row) {
        const trackId = parseInt(row.getAttribute('data-id'));
        if (trackId === id) {
          btn.textContent = res.liked ? '💚' : '🤍';
        }
      }
    });
    
    renderNowPlaying();
  }
}

function toggleMute() {
  state.isMuted = !state.isMuted;
  audio.volume = state.isMuted ? 0 : state.volume;
  muteBtn && (muteBtn.textContent = state.isMuted ? '🔈' : '🔊');
  savePlayerState();
}

function toggleShuffle() {
  state.isShuffle = !state.isShuffle;
  shuffleBtn && (shuffleBtn.style.opacity = state.isShuffle ? '1' : '0.6');
  showNotification(`Shuffle ${state.isShuffle ? 'on' : 'off'}`);
}

function toggleRepeat() {
  state.repeatMode = (state.repeatMode + 1) % 3;
  const modes = ['off', 'all', 'one'];
  repeatBtn && (repeatBtn.textContent = state.repeatMode === 0 ? '🔁' : state.repeatMode === 1 ? '🔁' : '🔂');
  repeatBtn && (repeatBtn.style.opacity = state.repeatMode === 0 ? '0.6' : '1');
  showNotification(`Repeat ${modes[state.repeatMode]}`);
}

// View functions
async function loadPlaylist(id) {
  Router.navigate(`/playlist/${id}`);
}

async function createNewPlaylist() {
  const name = prompt('Playlist name:', 'My Playlist');
  if (!name) return;
  
  const pl = await apiCall('/api/playlists', {
    method: 'POST',
    body: JSON.stringify({ name })
  });
  
  if (pl) {
    playlists.push(pl);
    showNotification(`Created "${name}"`);
    await loadUserPlaylists();
  } else {
    showNotification('Please log in to create playlists');
  }
}

async function loadUserPlaylists() {
  try {
    const res = await fetch('/api/playlists');
    if (res.ok) {
      const allPlaylists = await res.json();
      
      const container = document.getElementById('user-playlists');
      if (container) {
        container.innerHTML = allPlaylists.map(p => `
          <a href="/playlist/${p.id}" class="playlist-row" style="display: flex; align-items: center; gap: 12px; padding: 8px 16px; color: var(--muted); text-decoration: none; border-radius: 4px;">
            <div style="width: 32px; height: 32px; border-radius: 4px; background: ${p.gradient}; display: flex; align-items: center; justify-content: center; font-size: 14px;">
              ${p.cover}
            </div>
            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${p.name}</span>
          </a>
        `).join('');
      }
    }
  } catch (e) {
    console.log('Error loading playlists for sidebar');
  }
}

function showAddToPlaylistMenu(trackId) {
  if (playlists.length === 0) {
    showNotification('No playlists yet. Create one first!');
    return;
  }
  
  const menu = document.createElement('div');
  menu.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#282828;border-radius:8px;padding:16px;box-shadow:0 16px 48px rgba(0,0,0,0.5);z-index:1000;min-width:300px';
  
  menu.innerHTML = `
    <div style="font-weight:700;margin-bottom:12px">Add to playlist</div>
    ${playlists.map(p => `
      <div class="playlist-menu-item" data-id="${p.id}" style="padding:8px;border-radius:4px;cursor:pointer;transition:background 0.2s">
        ${p.name}
      </div>
    `).join('')}
    <button onclick="this.parentElement.remove()" style="margin-top:12px;width:100%;padding:8px;background:rgba(255,255,255,0.1);border:none;border-radius:4px;color:#fff;cursor:pointer">Cancel</button>
  `;
  
  document.body.appendChild(menu);
  
  menu.querySelectorAll('.playlist-menu-item').forEach(item => {
    item.onmouseenter = () => item.style.background = 'rgba(255,255,255,0.1)';
    item.onmouseleave = () => item.style.background = 'transparent';
    item.onclick = async () => {
      const plId = item.getAttribute('data-id');
      const res = await apiCall(`/api/playlists/${plId}/tracks`, {
        method: 'POST',
        body: JSON.stringify({ track_id: trackId })
      });
      if (res) {
        showNotification('Added to playlist');
        menu.remove();
      }
    };
  });
}

function showNotification(msg) {
  const notif = document.createElement('div');
  notif.className = 'notification';
  notif.textContent = msg;
  notif.style.cssText = 'position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#1db954;color:#fff;padding:12px 24px;border-radius:24px;font-size:14px;font-weight:600;z-index:1000;animation:slideUp 0.3s ease';
  document.body.appendChild(notif);
  
  setTimeout(() => {
    notif.style.animation = 'slideDown 0.3s ease';
    setTimeout(() => notif.remove(), 300);
  }, 2000);
}

// Event listeners
playBtn?.addEventListener('click', togglePlay);
prevBtn?.addEventListener('click', handlePrev);
nextBtn?.addEventListener('click', handleNext);
shuffleBtn?.addEventListener('click', toggleShuffle);
repeatBtn?.addEventListener('click', toggleRepeat);
muteBtn?.addEventListener('click', toggleMute);

volumeRange?.addEventListener('input', (e) => {
  state.volume = parseFloat(e.target.value);
  if (!state.isMuted) audio.volume = state.volume;
  savePlayerState();
});

audio?.addEventListener('timeupdate', () => {
  state.currentTime = audio.currentTime;
  timeCurrent && (timeCurrent.textContent = formatTime(state.currentTime));
  const pct = state.duration ? (state.currentTime / state.duration) * 100 : (audio.duration ? (audio.currentTime / audio.duration) * 100 : 0);
  progress && (progress.style.width = pct + '%');
});

audio?.addEventListener('loadedmetadata', () => {
  state.duration = audio.duration || state.currentTrack?.duration || 0;
  timeDuration && (timeDuration.textContent = formatTime(state.duration));
});

audio?.addEventListener('ended', () => {
  if (state.repeatMode === 2) {
    playTrack(state.currentTrack.id);
  } else {
    handleNext();
  }
});

progressBar?.addEventListener('click', (e) => {
  const rect = progressBar.getBoundingClientRect();
  const pct = (e.clientX - rect.left) / rect.width;
  if (audio.duration) audio.currentTime = pct * audio.duration;
  savePlayerState();
});

searchInput?.addEventListener('input', (e) => {
  state.searchQuery = e.target.value;
  const query = e.target.value.trim();
  if (query) {
    Router.navigate(`/search?q=${encodeURIComponent(query)}`);
  }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  
  if (e.code === 'Space') {
    e.preventDefault();
    togglePlay();
  } else if (e.code === 'ArrowRight') {
    e.preventDefault();
    handleNext();
  } else if (e.code === 'ArrowLeft') {
    e.preventDefault();
    handlePrev();
  }
});

// Глобальные функции
window.playTrack = playTrack;
window.toggleLike = toggleLike;
window.addToQueue = addToQueue;
window.loadPlaylist = loadPlaylist;
window.showAddToPlaylistMenu = showAddToPlaylistMenu;
window.createNewPlaylist = createNewPlaylist;

// Initialize
async function init() {
  await loadLikedTracks();
  restorePlayerState();
  renderNowPlaying();
  await loadUserPlaylists();
  
  // Инициализируем роутер
  Router.init();
}

document.addEventListener('DOMContentLoaded', init);
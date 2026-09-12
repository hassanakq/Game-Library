const grid = document.getElementById('grid');
const status = document.getElementById('status');
const count = document.getElementById('count');
const refreshBtn = document.getElementById('refreshBtn');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const favoritesToggle = document.getElementById('favoritesToggle');

const colorPicker = document.getElementById('colorPicker');
const filtersBar = document.getElementById('filters');

const settingsBtn = document.getElementById('settingsBtn');
const settingsBackdrop = document.getElementById('settingsBackdrop');
const settingsDrawer = document.getElementById('settingsDrawer');
const settingsClose = document.getElementById('settingsClose');

const wallpaperLayer = document.getElementById('wallpaperLayer');
const appScrim = document.getElementById('appScrim');

const wpModeInputs = document.querySelectorAll('input[name="wallpaperMode"]');
const wpHint = document.getElementById('wpHint');
const wpCustomRow = document.getElementById('wpCustomRow');
const wpChooseBtn = document.getElementById('wpChooseBtn');
const wpPreview = document.getElementById('wpPreview');
const wpPreviewImg = document.getElementById('wpPreviewImg');
const wpOpacity = document.getElementById('wpOpacity');
const wpOpacityValue = document.getElementById('wpOpacityValue');
const wpDarken = document.getElementById('wpDarken');
const wpDarkenValue = document.getElementById('wpDarkenValue');
const wpGlassToggle = document.getElementById('wpGlassToggle');
const wpBlurField = document.getElementById('wpBlurField');
const wpBlur = document.getElementById('wpBlur');
const wpBlurValue = document.getElementById('wpBlurValue');
const invertYToggle = document.getElementById('invertYToggle');
const invertXToggle = document.getElementById('invertXToggle');

const tbMinimize = document.getElementById('tbMinimize');
const tbMaximize = document.getElementById('tbMaximize');
const tbClose = document.getElementById('tbClose');

const modalBackdrop = document.getElementById('modalBackdrop');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');
const modalActions = document.getElementById('modalActions');


// ============================================================
// PLATFORM META
// ============================================================

const PLATFORM_META = {
    steam: {
        label: 'Steam',
        color: '#1b2838'
    },

    epic: {
        label: 'Epic',
        color: '#2a2a2a'
    },

    gog: {
        label: 'GOG',
        color: '#5c2d91'
    },

    ubisoft: {
        label: 'Ubisoft',
        color: '#0f4c9c'
    },

    ea: {
        label: 'EA',
        color: '#e31837'
    },

    battlenet: {
        label: 'Battle.net',
        color: '#148eff'
    },

    custom: {
        label: 'Custom',
        color: '#444'
    }
};


let allGames = [];
let activePlatform = 'all';
let favoritesOnly = false;
let renderedGames = [];


// ============================================================
// PYWEBVIEW
// ============================================================

let pywebviewReady = false;

window.addEventListener('pywebviewready', () => {
    pywebviewReady = true;

    console.log('Game Library native API ready');
});


// ============================================================
// MODAL
// ============================================================

let modalReturnFocus = null;

function closeModal() {

    modalBackdrop.hidden = true;

    modalActions.innerHTML = '';

    if (modalReturnFocus) {

        modalReturnFocus.focus?.();

        modalReturnFocus = null;
    }
}

/**
 * actions: [{ label, variant: 'default'|'danger'|'outline', onSelect }]
 * Esc / backdrop click always cancels.
 */
function openModal({ title, body, actions }) {

    modalReturnFocus = document.activeElement;

    modalTitle.textContent = title;
    modalBody.textContent = body || '';

    modalActions.innerHTML = '';

    actions.forEach(action => {

        const btn = document.createElement('button');

        btn.type = 'button';
        btn.textContent = action.label;

        btn.className =
            'btn' +
            (action.variant === 'danger' ? ' btn-danger' : ' btn-outline');

        btn.addEventListener('click', () => {

            closeModal();

            action.onSelect?.();
        });

        modalActions.appendChild(btn);
    });

    modalBackdrop.hidden = false;

    modalActions.querySelector('button')?.focus();
}

modalBackdrop.addEventListener('click', e => {

    if (e.target === modalBackdrop) {
        closeModal();
    }
});

document.addEventListener('keydown', e => {

    if (e.key === 'Escape' && !modalBackdrop.hidden) {
        closeModal();
    }
});


// ============================================================
// TITLE BAR / WINDOW CONTROLS
// ============================================================

async function callNative(method, ...args) {

    if (!pywebviewReady || !window.pywebview?.api?.[method]) {
        return null;
    }

    try {
        return await window.pywebview.api[method](...args);
    } catch (err) {
        console.error(`Native call "${method}" failed:`, err);
        return null;
    }
}

tbMinimize?.addEventListener('click', () => callNative('minimize_window'));
tbMaximize?.addEventListener('click', () => callNative('toggle_maximize_window'));
tbClose?.addEventListener('click', () => callNative('close_window'));


// ============================================================
// FULLSCREEN
// ============================================================

let isFullscreen = false;

async function toggleFullscreen() {

    const result = await callNative('toggle_fullscreen');

    isFullscreen = !isFullscreen;

    fullscreenBtn?.classList.toggle('active', isFullscreen);

    // The custom title bar is regular page content, not OS chrome, so
    // pywebview's native fullscreen doesn't hide it on its own -- do that
    // here, otherwise the title bar stays visible over "fullscreen" video.
    document.body.classList.toggle('is-fullscreen', isFullscreen);

    return result;
}

fullscreenBtn?.addEventListener('click', toggleFullscreen);

document.addEventListener('keydown', e => {

    if (e.key === 'F11') {

        e.preventDefault();

        toggleFullscreen();
    }
});


// ============================================================
// WINDOW RESIZE (frameless window has no OS-drawn resize border)
// ============================================================

(() => {

    const handles = document.querySelectorAll('.resize-handle');

    let dragging = false;
    let dir = null;
    let startX = 0;
    let startY = 0;
    let startWin = null;
    let pending = null;

    function applyResize(dx, dy) {

        let { width, height } = startWin;

        if (dir.includes('e')) width += dx;
        if (dir.includes('w')) width -= dx;
        if (dir.includes('s')) height += dy;
        if (dir.includes('n')) height -= dy;

        width = Math.max(width, 1000);
        height = Math.max(height, 650);

        callNative('resize_window', Math.round(width), Math.round(height), dir);
    }

    function onMouseMove(e) {

        if (!dragging) return;

        const dx = e.screenX - startX;
        const dy = e.screenY - startY;

        // Throttle native calls to one per animation frame instead of one
        // per mousemove event.
        if (pending) return;

        pending = requestAnimationFrame(() => {
            pending = null;
            applyResize(dx, dy);
        });
    }

    function onMouseUp() {

        dragging = false;
        dir = null;

        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
    }

    handles.forEach(handle => {

        handle.addEventListener('mousedown', async e => {

            e.preventDefault();

            const size = await callNative('get_window_size');

            if (!size) return;

            dragging = true;
            dir = handle.dataset.dir;
            startX = e.screenX;
            startY = e.screenY;
            startWin = size;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    });

})();


// ============================================================
// IMPORT EXE BUTTON
// ============================================================

const importExeBtn = document.createElement('button');

importExeBtn.type = 'button';
importExeBtn.textContent = 'import .exe';

if (refreshBtn) {
    importExeBtn.className = refreshBtn.className;

    refreshBtn.parentNode.insertBefore(
        importExeBtn,
        refreshBtn
    );
}


importExeBtn.addEventListener('click', async () => {

    if (!pywebviewReady) {
        console.warn('Native API is not ready yet.');

        status.hidden = false;
        status.textContent = 'Game Library is still starting...';

        return;
    }


    importExeBtn.disabled = true;
    importExeBtn.textContent = 'selecting…';


    try {

        /*
         * This calls Python:
         *
         * GameLibraryAPI.select_game()
         *
         * which opens the REAL Windows file picker.
         */
        const data = await window.pywebview.api.select_game();


        // User pressed Cancel
        if (!data || data.cancelled) {
            return;
        }


        // Import failed
        if (!data.success) {

            console.error(
                data.message || 'Could not import game'
            );

            status.hidden = false;
            status.textContent =
                data.message || 'Could not import game';

            return;
        }


        // Successfully imported
        console.log(
            'Game imported:',
            data.game
        );


        // Reload the library
        await loadGames();


    } catch (err) {

        console.error(
            'Could not import EXE:',
            err
        );

        status.hidden = false;
        status.textContent =
            'Could not select the game executable.';

    } finally {

        importExeBtn.disabled = false;
        importExeBtn.textContent = 'import .exe';
    }
});


// ============================================================
// SETTINGS
//
// The backend (settings.json under the app's data folder, see
// backend/settings_store.py) is the source of truth so nothing has to be
// redone after closing the app. A localStorage copy is kept only so
// settings can be applied instantly on boot, before pywebview's API
// bridge is ready -- it's overwritten by whatever the backend returns
// as soon as that call resolves.
// ============================================================

const SETTINGS_DEFAULTS = {
    accentColor: '#ff2b2b',
    wallpaperMode: 'none',       // 'none' | 'custom' | 'current_game'
    wallpaperImage: null,
    wallpaperOpacity: 35,
    wallpaperDarken: 55,
    glassEffect: true,
    wallpaperBlur: 18,
    invertY: false,
    invertX: false,
};

let settings = { ...SETTINGS_DEFAULTS };

// The image currently shown for wallpaperMode === 'current_game' --
// updated as the mouse hovers or the controller/keyboard selection moves.
let focusedGameImage = null;

// Exposed so controller.js can read invertX/invertY without importing
// anything -- both files just share `window.GameLibrary`.
window.GameLibrarySettings = settings;

let saveSettingsTimer = null;

function persistSettings() {

    localStorage.setItem('gameLibrarySettings', JSON.stringify(settings));

    // Debounced so dragging a slider doesn't spam the native bridge.
    clearTimeout(saveSettingsTimer);

    saveSettingsTimer = setTimeout(() => {
        callNative('save_settings', settings);
    }, 250);
}

function applyAccentColor() {

    colorPicker.value = settings.accentColor;

    document.documentElement.style.setProperty('--accent', settings.accentColor);
}

function applyWallpaper() {

    const isCustom = settings.wallpaperMode === 'custom';
    const isCurrentGame = settings.wallpaperMode === 'current_game';

    const activeImage = isCustom
        ? settings.wallpaperImage
        : isCurrentGame
            ? focusedGameImage
            : null;

    const hasWallpaper = !!activeImage;

    wallpaperLayer.style.backgroundImage = activeImage
        ? `url("${activeImage}")`
        : 'none';

    wallpaperLayer.style.opacity = hasWallpaper
        ? String(settings.wallpaperOpacity / 100)
        : '0';

    appScrim.style.opacity = hasWallpaper
        ? String(settings.wallpaperDarken / 100)
        : '0';

    document.documentElement.style.setProperty(
        '--glass-blur',
        `${settings.wallpaperBlur}px`
    );

    document.body.classList.toggle('has-wallpaper', hasWallpaper);
    document.body.classList.toggle('glass-on', hasWallpaper && !!settings.glassEffect);
}

/**
 * Called whenever the mouse hovers a card, or the controller/keyboard
 * selection moves (see controller.js). Only actually changes anything
 * while wallpaperMode is 'current_game'.
 */
function onGameFocus(game) {

    if (!game || settings.wallpaperMode !== 'current_game') {
        return;
    }

    const image = game.image_url || null;

    if (image === focusedGameImage) {
        return;
    }

    focusedGameImage = image;

    applyWallpaper();
}

function syncWallpaperControlsUI() {

    wpModeInputs.forEach(input => {
        input.checked = input.value === settings.wallpaperMode;
    });

    wpCustomRow.hidden = settings.wallpaperMode !== 'custom';

    wpHint.textContent = settings.wallpaperMode === 'current_game'
        ? "The background follows whichever game you're hovering or have selected."
        : 'Pick any image from your computer to use as the background.';

    wpHint.hidden = settings.wallpaperMode === 'none';

    if (settings.wallpaperImage) {
        wpPreview.hidden = false;
        wpPreviewImg.src = settings.wallpaperImage;
    } else {
        wpPreview.hidden = true;
    }

    wpOpacity.value = settings.wallpaperOpacity;
    wpOpacityValue.textContent = `${settings.wallpaperOpacity}%`;

    wpDarken.value = settings.wallpaperDarken;
    wpDarkenValue.textContent = `${settings.wallpaperDarken}%`;

    wpGlassToggle.checked = !!settings.glassEffect;

    wpBlur.value = settings.wallpaperBlur;
    wpBlurValue.textContent = `${settings.wallpaperBlur}px`;
    wpBlurField.classList.toggle('is-disabled', !settings.glassEffect);

    invertYToggle.checked = !!settings.invertY;
    invertXToggle.checked = !!settings.invertX;
}

function applyAllSettings() {

    applyAccentColor();
    applyWallpaper();
    syncWallpaperControlsUI();
}

// ---- instant-apply from localStorage (before the native bridge is up) ----
try {

    const cached = JSON.parse(localStorage.getItem('gameLibrarySettings') || 'null');

    if (cached && typeof cached === 'object') {
        settings = { ...SETTINGS_DEFAULTS, ...cached };
        window.GameLibrarySettings = settings;
    }

} catch {
    // Corrupt cache -- fall back to defaults, no big deal.
}

applyAllSettings();

// ---- backend is the real source of truth, once it's reachable ----
window.addEventListener('pywebviewready', async () => {

    const backendSettings = await callNative('get_settings');

    if (backendSettings && typeof backendSettings === 'object') {
        settings = { ...SETTINGS_DEFAULTS, ...backendSettings };
        window.GameLibrarySettings = settings;

        localStorage.setItem('gameLibrarySettings', JSON.stringify(settings));

        applyAllSettings();
    }
});

// ---- accent color ----

colorPicker.addEventListener('input', () => {

    settings.accentColor = colorPicker.value;

    document.documentElement.style.setProperty('--accent', settings.accentColor);

    persistSettings();
});

// ---- wallpaper mode ----

wpModeInputs.forEach(input => {

    input.addEventListener('change', () => {

        if (!input.checked) return;

        settings.wallpaperMode = input.value;

        syncWallpaperControlsUI();
        applyWallpaper();
        persistSettings();

        if (settings.wallpaperMode === 'current_game' && !focusedGameImage) {
            onGameFocus(renderedGames[0]);
        }
    });
});

wpChooseBtn.addEventListener('click', async () => {

    wpChooseBtn.disabled = true;

    const original = wpChooseBtn.textContent;
    wpChooseBtn.textContent = 'selecting…';

    try {

        const result = await callNative('select_wallpaper_image');

        if (!result || result.cancelled) {
            return;
        }

        if (!result.success) {
            console.error(result.message || 'Could not set wallpaper');
            return;
        }

        settings.wallpaperImage = result.image_url;

        syncWallpaperControlsUI();
        applyWallpaper();
        persistSettings();

    } finally {
        wpChooseBtn.disabled = false;
        wpChooseBtn.textContent = original;
    }
});

// ---- sliders ----

wpOpacity.addEventListener('input', () => {
    settings.wallpaperOpacity = Number(wpOpacity.value);
    wpOpacityValue.textContent = `${settings.wallpaperOpacity}%`;
    applyWallpaper();
    persistSettings();
});

wpDarken.addEventListener('input', () => {
    settings.wallpaperDarken = Number(wpDarken.value);
    wpDarkenValue.textContent = `${settings.wallpaperDarken}%`;
    applyWallpaper();
    persistSettings();
});

wpBlur.addEventListener('input', () => {
    settings.wallpaperBlur = Number(wpBlur.value);
    wpBlurValue.textContent = `${settings.wallpaperBlur}px`;
    applyWallpaper();
    persistSettings();
});

wpGlassToggle.addEventListener('change', () => {
    settings.glassEffect = wpGlassToggle.checked;
    wpBlurField.classList.toggle('is-disabled', !settings.glassEffect);
    applyWallpaper();
    persistSettings();
});

// ---- controller inversion ----

invertYToggle.addEventListener('change', () => {
    settings.invertY = invertYToggle.checked;
    persistSettings();
});

invertXToggle.addEventListener('change', () => {
    settings.invertX = invertXToggle.checked;
    persistSettings();
});

// ---- drawer open/close ----

function openSettingsDrawer() {

    settingsBackdrop.hidden = false;
    settingsDrawer.hidden = false;
    settingsDrawer.setAttribute('aria-hidden', 'false');

    // Force a layout flush so the browser doesn't collapse the "hidden ->
    // visible" transition into the "add .open" transition and skip the
    // slide-in animation entirely.
    void settingsDrawer.offsetWidth;

    settingsBackdrop.classList.add('open');
    settingsDrawer.classList.add('open');
}

function closeSettingsDrawer() {

    settingsBackdrop.classList.remove('open');
    settingsDrawer.classList.remove('open');
    settingsDrawer.setAttribute('aria-hidden', 'true');

    setTimeout(() => {
        settingsBackdrop.hidden = true;
        settingsDrawer.hidden = true;
    }, 300);
}

settingsBtn?.addEventListener('click', openSettingsDrawer);
settingsClose?.addEventListener('click', closeSettingsDrawer);
settingsBackdrop?.addEventListener('click', closeSettingsDrawer);

document.addEventListener('keydown', e => {

    if (e.key === 'Escape' && settingsDrawer.classList.contains('open')) {
        closeSettingsDrawer();
    }
});


// ============================================================
// FAVORITES
// ============================================================

async function setFavorite(game) {

    try {

        const res = await fetch('/api/favorites/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: game.platform,
                id: game.id
            })
        });

        const data = await res.json();

        if (data.success) {
            game.is_favorite = data.is_favorite;
        }

        return game.is_favorite;

    } catch (err) {

        console.error('Could not update favorite:', err);

        return game.is_favorite;
    }
}

favoritesToggle?.addEventListener('click', () => {

    favoritesOnly = !favoritesOnly;

    favoritesToggle.classList.toggle('active', favoritesOnly);

    renderGrid();
});


// ============================================================
// REMOVE CUSTOM GAME
// ============================================================

function confirmRemoveGame(game) {

    openModal({
        title: 'Remove game?',
        body: `"${game.name}" will be removed from your library. This only removes it from Game Library — nothing is deleted from your computer.`,
        actions: [
            {
                label: 'Cancel',
                variant: 'outline',
                onSelect: () => {}
            },
            {
                label: 'Remove',
                variant: 'danger',
                onSelect: () => removeCustomGame(game)
            }
        ]
    });
}

async function removeCustomGame(game) {

    try {

        const res = await fetch(
            `/api/games/custom/${encodeURIComponent(game.id)}`,
            { method: 'DELETE' }
        );

        const data = await res.json();

        if (!data.success) {

            status.hidden = false;
            status.textContent = data.message || 'Could not remove game.';

            return;
        }

        await loadGames();

    } catch (err) {

        console.error('Could not remove game:', err);

        status.hidden = false;
        status.textContent = 'Could not remove game.';
    }
}

function openGameOptions(game) {

    const actions = [
        {
            label: game.is_favorite ? 'Unfavorite' : 'Favorite',
            variant: 'outline',
            onSelect: async () => {
                await setFavorite(game);
                renderGrid();
            }
        }
    ];

    if (game.platform === 'custom') {
        actions.push({
            label: 'Remove',
            variant: 'danger',
            onSelect: () => confirmRemoveGame(game)
        });
    }

    actions.push({
        label: 'Close',
        variant: 'outline',
        onSelect: () => {}
    });

    openModal({
        title: game.name,
        body: PLATFORM_META[game.platform]?.label || game.platform,
        actions
    });
}


// ============================================================
// LAUNCHING
// ============================================================

async function launchGame(game) {

    /*
     * Custom EXE games and Battle.net games
     * must be launched by Python.
     */
    if (
        game.launch_type === 'exe' ||
        game.launch_type === 'battlenet'
    ) {

        try {

            const res = await fetch(
                '/api/games/launch',
                {
                    method: 'POST',

                    headers: {
                        'Content-Type': 'application/json'
                    },

                    body: JSON.stringify({
                        platform: game.platform,
                        id: game.id
                    })
                }
            );


            const data = await res.json();


            if (!data.success) {

                console.error(
                    data.message ||
                    'Could not launch game'
                );

                status.hidden = false;

                status.textContent =
                    data.message ||
                    'Could not launch game';
            }


        } catch (err) {

            console.error(
                'Could not launch game:',
                err
            );

            status.hidden = false;

            status.textContent =
                'Could not launch game.';
        }


        return;
    }


    /*
     * Steam / Epic / GOG / Ubisoft
     *
     * These use their normal launch URI.
     */
    if (game.launch_uri) {
        window.location.href = game.launch_uri;
    }
}


// ============================================================
// INITIALS
// ============================================================

function initials(name) {

    const words = name
        .trim()
        .split(/\s+/)
        .slice(0, 2);


    return words
        .map(w => w[0])
        .join('')
        .toUpperCase();
}


// ============================================================
// PLACEHOLDER TILE
// ============================================================

function buildPlaceholderTile(game) {

    const meta =
        PLATFORM_META[game.platform] ||
        {
            color: '#333'
        };


    const tile =
        document.createElement('div');


    tile.className =
        'card-art is-tile';


    tile.style.background =
        meta.color;


    tile.textContent =
        initials(game.name);


    return tile;
}


// ============================================================
// GAME CARD
// ============================================================

function buildCard(game) {

    const meta =
        PLATFORM_META[game.platform] ||
        {
            label: game.platform
        };


    const card =
        document.createElement('div');


    card.className = 'card';

    card.tabIndex = 0;

    card.dataset.platform = game.platform;
    card.dataset.id = game.id;

    card.setAttribute(
        'role',
        'button'
    );

    card.setAttribute(
        'aria-label',
        `Launch ${game.name}`
    );


    // --------------------------------------------------------
    // PLATFORM BADGE
    // --------------------------------------------------------

    const badge =
        document.createElement('span');


    badge.className =
        'platform-badge';


    badge.textContent =
        meta.label;


    card.appendChild(badge);


    // --------------------------------------------------------
    // FAVORITE BUTTON
    // --------------------------------------------------------

    const favoriteBtn = document.createElement('button');

    favoriteBtn.type = 'button';
    favoriteBtn.className = 'card-favorite';
    favoriteBtn.classList.toggle('is-favorite', !!game.is_favorite);
    favoriteBtn.innerHTML = '&#9733;';
    favoriteBtn.setAttribute(
        'aria-label',
        game.is_favorite ? `Unfavorite ${game.name}` : `Favorite ${game.name}`
    );

    favoriteBtn.addEventListener('click', async e => {

        e.stopPropagation();

        favoriteBtn.classList.toggle('is-favorite');

        await setFavorite(game);

        favoriteBtn.classList.toggle('is-favorite', !!game.is_favorite);

        if (favoritesOnly && !game.is_favorite) {
            renderGrid();
        }
    });

    card.appendChild(favoriteBtn);


    // --------------------------------------------------------
    // REMOVE BUTTON (custom games only)
    // --------------------------------------------------------

    if (game.platform === 'custom') {

        const removeBtn = document.createElement('button');

        removeBtn.type = 'button';
        removeBtn.className = 'card-remove';
        removeBtn.innerHTML = '&#128465;';
        removeBtn.setAttribute('aria-label', `Remove ${game.name}`);

        removeBtn.addEventListener('click', e => {

            e.stopPropagation();

            confirmRemoveGame(game);
        });

        card.appendChild(removeBtn);
    }


    // --------------------------------------------------------
    // ARTWORK
    // --------------------------------------------------------

    let art;


    if (game.has_image) {

        art =
            document.createElement('div');


        art.className =
            'card-art is-placeholder';


        art.textContent =
            'loading art…';


        card.appendChild(art);


        swapInImage(
            art,
            game.image_url
        );

    } else {

        art =
            document.createElement('div');


        art.className =
            'card-art is-placeholder';


        art.textContent =
            'loading art…';


        card.appendChild(art);


        loadArt(
            game,
            art
        );
    }


    // --------------------------------------------------------
    // PLAY OVERLAY
    // --------------------------------------------------------

    const overlay =
        document.createElement('div');


    overlay.className =
        'card-overlay';


    const playIcon =
        document.createElement('span');


    playIcon.className =
        'play-icon';


    overlay.appendChild(
        playIcon
    );


    overlay.appendChild(
        document.createTextNode('play')
    );


    card.appendChild(
        overlay
    );


    // --------------------------------------------------------
    // GAME NAME
    // --------------------------------------------------------

    const label =
        document.createElement('p');


    label.className =
        'card-label';


    label.textContent =
        game.name;


    card.appendChild(
        label
    );


    // --------------------------------------------------------
    // CLICK / KEYBOARD
    // --------------------------------------------------------

    const open = () =>
        launchGame(game);


    card.addEventListener(
        'click',
        open
    );


    // Lets the "current game" wallpaper mode follow whatever the mouse is
    // sitting on (controller/keyboard focus is handled separately, in
    // controller.js, since hover events don't fire for those).
    card.addEventListener(
        'mouseenter',
        () => onGameFocus(game)
    );


    card.addEventListener(
        'keydown',
        e => {

            if (
                e.key === 'Enter' ||
                e.key === ' '
            ) {

                e.preventDefault();

                open();
            }
        }
    );


    return card;
}


// ============================================================
// IMAGE
// ============================================================

function swapInImage(art, url) {

    const img =
        new Image();


    img.className =
        'card-art';


    img.src =
        url;


    img.alt = '';


    img.onload = () => {

        art.replaceWith(
            img
        );
    };


    img.onerror = () => {

        art.textContent =
            'no art available';
    };
}


// ============================================================
// ARTWORK FAILURE
// ============================================================

function buildFallbackAfterFailure(
    game,
    art
) {

    const tile =
        buildPlaceholderTile(game);


    tile.textContent =
        'no art available';


    art.replaceWith(
        tile
    );
}


// ============================================================
// LOAD ARTWORK
// ============================================================

async function loadArt(
    game,
    art
) {

    try {

        const res =
            await fetch(
                `/api/games/${encodeURIComponent(game.platform)}/${encodeURIComponent(game.id)}/image`,
                {
                    method: 'POST'
                }
            );


        const data =
            await res.json();


        if (data.success) {

            swapInImage(
                art,
                data.image_url
            );

        } else {

            buildFallbackAfterFailure(
                game,
                art
            );
        }


    } catch {

        buildFallbackAfterFailure(
            game,
            art
        );
    }
}


// ============================================================
// FILTERS
// ============================================================

function getFilterOptions() {

    const present = [
        ...new Set(
            allGames.map(
                g => g.platform
            )
        )
    ];

    return ['all', ...present];
}

function setActivePlatform(platform) {

    activePlatform = platform;

    renderFilters();
    renderGrid();
}

/**
 * Move the active platform filter forward/back by `step`
 * (used by the controller's LB/RB shoulder buttons).
 */
function cyclePlatformFilter(step) {

    const options = getFilterOptions();

    if (options.length <= 1) {
        return;
    }

    const currentIndex = Math.max(0, options.indexOf(activePlatform));

    const nextIndex =
        (currentIndex + step + options.length) % options.length;

    setActivePlatform(options[nextIndex]);
}

function renderFilters() {

    const options = getFilterOptions();

    if (options.length <= 2) {

        filtersBar.hidden = true;

        return;
    }


    filtersBar.hidden = false;

    filtersBar.innerHTML = '';


    options.forEach(platform => {

        const chip =
            document.createElement('button');


        chip.type =
            'button';


        chip.className =
            'filter-chip' +
            (
                platform === activePlatform
                    ? ' active'
                    : ''
            );


        chip.textContent =
            platform === 'all'
                ? 'all'
                : (
                    PLATFORM_META[platform]?.label ||
                    platform
                );


        chip.addEventListener(
            'click',
            () => setActivePlatform(platform)
        );


        filtersBar.appendChild(
            chip
        );
    });
}


// ============================================================
// GRID
// ============================================================

function currentFilteredGames() {

    let games =
        activePlatform === 'all'
            ? allGames
            : allGames.filter(
                g =>
                    g.platform ===
                    activePlatform
            );

    if (favoritesOnly) {
        games = games.filter(g => g.is_favorite);
    }

    return games;
}

function renderGrid() {

    const games = currentFilteredGames();

    renderedGames = games;

    grid.innerHTML = '';


    if (games.length === 0) {

        status.hidden = false;

        grid.hidden = true;

        status.textContent = favoritesOnly
            ? 'no favorites yet — star a game to add it here.'
            : 'no games in this view.';

        return;
    }


    games.forEach(game => {

        grid.appendChild(
            buildCard(game)
        );
    });


    status.hidden = true;

    grid.hidden = false;

    document.dispatchEvent(new CustomEvent('gamelibrary:grid-rendered'));

    // "Current game" wallpaper mode needs *something* focused before the
    // user has hovered or moved a controller/keyboard selector at all.
    if (settings.wallpaperMode === 'current_game') {
        onGameFocus(games[0]);
    }
}


// ============================================================
// LOAD GAMES
// ============================================================

async function loadGames() {

    status.hidden = false;

    grid.hidden = true;

    filtersBar.hidden = true;


    status.textContent =
        'scanning installed launchers…';


    try {

        const res =
            await fetch(
                '/api/games'
            );


        const data =
            await res.json();


        allGames =
            data.games || [];


        if (allGames.length === 0) {

            status.textContent =
                'no games found on this machine.';

            count.textContent =
                '';

            return;
        }


        count.textContent =
            `${allGames.length} game${
                allGames.length === 1
                    ? ''
                    : 's'
            }`;


        renderFilters();

        renderGrid();


    } catch (err) {

        console.error(
            'Could not load games:',
            err
        );


        status.textContent =
            'could not reach the Game Library backend.';
    }
}


// ============================================================
// REFRESH
// ============================================================

refreshBtn.addEventListener(
    'click',
    loadGames
);


// ============================================================
// PUBLIC SURFACE (used by controller.js)
// ============================================================

window.GameLibrary = {
    getRenderedGames: () => renderedGames,
    launch: launchGame,
    toggleFavorite: setFavorite,
    openOptions: openGameOptions,
    cyclePlatformFilter,
    refresh: loadGames,
    toggleFullscreen,
    isModalOpen: () => !modalBackdrop.hidden,
    closeModal,
    onGameFocus,
    isSettingsOpen: () => settingsDrawer.classList.contains('open'),
    closeSettings: closeSettingsDrawer,
};


// ============================================================
// INITIAL LOAD
// ============================================================

loadGames();

/**
 * Controller support.
 *
 * The actual gamepad reading happens in Python (backend/controller.py) via
 * pygame's joystick module, which on Windows sits on top of XInput. This
 * file just polls `GameLibraryAPI.get_controller_state()` and turns the
 * result into grid navigation / actions, using the same UI that mouse and
 * keyboard already drive (window.GameLibrary from app.js).
 */

(() => {

    const POLL_INTERVAL_MS = 90;

    const controllerBadge = document.getElementById('controllerBadge');
    const controllerBadgeText = document.getElementById('controllerBadgeText');

    let focusIndex = 0;
    let connected = false;
    let pollTimer = null;

    // --------------------------------------------------------------
    // Grid focus
    // --------------------------------------------------------------

    function gridCards() {
        return Array.from(document.querySelectorAll('#grid .card'));
    }

    function columnsInGrid(cards) {

        if (cards.length === 0) {
            return 1;
        }

        const firstTop = cards[0].offsetTop;

        let columns = 0;

        for (const card of cards) {
            if (card.offsetTop === firstTop) {
                columns += 1;
            } else {
                break;
            }
        }

        return Math.max(1, columns);
    }

    function clearGridFocus() {

        gridCards().forEach(c => c.classList.remove('controller-focused'));

        // Also drop *native* DOM focus if it's sitting on a card -- just
        // removing the CSS class isn't enough, since the card's own
        // `:focus-visible` style (border/lift) would otherwise keep making
        // it look selected even with the class gone.
        const active = document.activeElement;

        if (active?.classList?.contains('card')) {
            active.blur();
        }
    }

    function applyGridFocus() {

        const cards = gridCards();

        clearGridFocus();

        if (cards.length === 0) {
            return;
        }

        focusIndex = Math.min(focusIndex, cards.length - 1);
        focusIndex = Math.max(focusIndex, 0);

        const card = cards[focusIndex];

        card.classList.add('controller-focused');

        card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });

        // Move real DOM focus too (not just the CSS highlight), so that
        // native Enter/Space activation (handled by the card's own keydown
        // listener in app.js) works for keyboard users without us having to
        // duplicate that launch logic here.
        card.focus({ preventScroll: true });

        notifyWallpaperFocus();
    }

    function moveGridFocus(direction) {

        const cards = gridCards();

        if (cards.length === 0) {
            return;
        }

        const columns = columnsInGrid(cards);
        const column = focusIndex % columns;
        const lastIndex = cards.length - 1;

        let next = focusIndex;

        if (direction === 'left' || direction === 'right') {

            next += direction === 'left' ? -1 : 1;

            // Wrap around the whole list instead of getting stuck at
            // either end -- left from the very first card goes to the
            // last one, right from the last card goes back to the first.
            next = ((next % cards.length) + cards.length) % cards.length;

        } else if (direction === 'up' || direction === 'down') {

            next += direction === 'up' ? -columns : columns;

            if (next < 0) {
                // Wrap to the same column in the bottom-most row. If that
                // row is shorter and doesn't reach this column, fall back
                // to the very last card rather than leaving the selection
                // stuck (or, previously, visually dropped) at the top.
                const bottomRowStart = Math.floor(lastIndex / columns) * columns;
                const candidate = bottomRowStart + column;
                next = candidate <= lastIndex ? candidate : lastIndex;

            } else if (next > lastIndex) {
                // Wrap back to the same column in the top row.
                next = column <= lastIndex ? column : 0;
            }
        }

        focusIndex = next;

        applyGridFocus();
    }

    /**
     * Lets the "current game" wallpaper mode (see app.js) follow the
     * controller/keyboard selection the same way it already follows mouse
     * hover -- hover events don't fire for keyboard/controller-driven focus.
     */
    function notifyWallpaperFocus() {
        const game = focusedGame();
        if (game) {
            window.GameLibrary.onGameFocus?.(game);
        }
    }

    document.addEventListener('gamelibrary:grid-rendered', () => {
        if (connected || keyboardNavActive) {
            applyGridFocus();
        }
    });

    // --------------------------------------------------------------
    // Modal focus
    // --------------------------------------------------------------

    function modalButtons() {
        return Array.from(document.querySelectorAll('#modalActions button'));
    }

    let modalFocusIndex = 0;

    function applyModalFocus() {

        const buttons = modalButtons();

        buttons.forEach(b => b.classList.remove('is-controller-focused'));

        if (buttons.length === 0) {
            return;
        }

        modalFocusIndex = Math.max(0, Math.min(modalFocusIndex, buttons.length - 1));

        buttons[modalFocusIndex].classList.add('is-controller-focused');
        buttons[modalFocusIndex].focus();
    }

    function moveModalFocus(direction) {

        const buttons = modalButtons();

        if (buttons.length === 0) {
            return;
        }

        if (direction === 'left' || direction === 'up') {
            modalFocusIndex -= 1;
        } else if (direction === 'right' || direction === 'down') {
            modalFocusIndex += 1;
        }

        modalFocusIndex =
            (modalFocusIndex + buttons.length) % buttons.length;

        applyModalFocus();
    }

    // --------------------------------------------------------------
    // Action handling
    // --------------------------------------------------------------

    // Some controllers (particularly non-Xbox/generic pads, which pygame
    // reads through its raw Joystick API rather than the normalized
    // GameController API) report their D-pad/stick with the opposite
    // polarity. Rather than guess, the Settings drawer exposes a manual
    // "invert" switch per axis; this is where that gets applied.
    const OPPOSITE = { up: 'down', down: 'up', left: 'right', right: 'left' };

    function applyAxisInversion(direction) {

        const settings = window.GameLibrarySettings;

        if (!settings) {
            return direction;
        }

        if ((direction === 'up' || direction === 'down') && settings.invertY) {
            return OPPOSITE[direction];
        }

        if ((direction === 'left' || direction === 'right') && settings.invertX) {
            return OPPOSITE[direction];
        }

        return direction;
    }

    function handleNav(direction) {

        if (!direction) {
            return;
        }

        // The Settings drawer uses plain browser focus/tab order, not this
        // grid/modal system -- leave its inputs alone (and let Escape/click
        // outside be the only way out) instead of moving the grid behind it.
        if (window.GameLibrary.isSettingsOpen?.()) {
            return;
        }

        direction = applyAxisInversion(direction);

        if (window.GameLibrary.isModalOpen()) {
            moveModalFocus(direction);
        } else {
            moveGridFocus(direction);
        }
    }

    function focusedGame() {

        const games = window.GameLibrary.getRenderedGames();

        return games[focusIndex] || null;
    }

    function handlePressed(action) {

        if (window.GameLibrary.isSettingsOpen?.()) {
            if (action === 'b' || action === 'start') {
                window.GameLibrary.closeSettings();
            }
            return;
        }

        const modalOpen = window.GameLibrary.isModalOpen();

        if (modalOpen) {

            if (action === 'a') {
                modalButtons()[modalFocusIndex]?.click();
            } else if (action === 'b') {
                window.GameLibrary.closeModal();
            }

            return;
        }

        switch (action) {

            case 'a': {
                const game = focusedGame();
                if (game) window.GameLibrary.launch(game);
                break;
            }

            case 'x': {
                const game = focusedGame();
                if (game) {
                    window.GameLibrary.toggleFavorite(game).then(() => {
                        // Refresh the star's visual state without a full re-render.
                        const card = gridCards()[focusIndex];
                        card?.querySelector('.card-favorite')
                            ?.classList.toggle('is-favorite', !!game.is_favorite);
                    });
                }
                break;
            }

            case 'y': {
                const game = focusedGame();
                if (game) window.GameLibrary.openOptions(game);
                break;
            }

            case 'lb':
                window.GameLibrary.cyclePlatformFilter(-1);
                break;

            case 'rb':
                window.GameLibrary.cyclePlatformFilter(1);
                break;

            case 'start':
                window.GameLibrary.toggleFullscreen();
                break;

            case 'select':
                window.GameLibrary.refresh();
                break;

            case 'b':
                // Nothing to "go back" to at the top level.
                break;
        }
    }

    // --------------------------------------------------------------
    // Keyboard navigation
    //
    // Arrow keys drive the same grid/modal focus as the controller's D-pad
    // and stick. This is independent of `connected` (which tracks gamepad
    // presence) so it works whether or not a controller is plugged in.
    //
    // Note this only needs to move focus, not launch games: moving focus
    // onto a grid card or modal button (see applyGridFocus/applyModalFocus)
    // puts real DOM focus on it, so native Enter/Space activation -- the
    // card's own keydown listener in app.js, or the browser's default
    // button behavior -- takes it from there.
    // --------------------------------------------------------------

    const KEY_NAV = {
        ArrowUp: 'up',
        ArrowDown: 'down',
        ArrowLeft: 'left',
        ArrowRight: 'right',
    };

    let keyboardNavActive = false;

    document.addEventListener('keydown', e => {

        const direction = KEY_NAV[e.key];

        if (direction) {

            const target = e.target;
            const tag = (target?.tagName || '').toLowerCase();

            // Don't hijack arrow keys while the user is interacting with a
            // native form control (e.g. the accent color picker).
            if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) {
                return;
            }

            e.preventDefault();

            keyboardNavActive = true;

            handleNav(direction);

            return;
        }

        // Escape: drop keyboard/controller selection entirely instead of
        // leaving a card looking "selected" with nothing to dismiss it.
        // Modal/settings-drawer Escape handling lives in app.js and takes
        // priority over this -- only clear the grid highlight when neither
        // of those is actually open.
        if (
            e.key === 'Escape' &&
            !window.GameLibrary.isModalOpen() &&
            !window.GameLibrary.isSettingsOpen?.()
        ) {
            keyboardNavActive = false;
            clearGridFocus();
        }
    });

    // Genuine mouse movement (not just a card shifting under a stationary
    // cursor when the page scrolls during keyboard/controller nav) hands
    // the selection back to the mouse, instead of leaving both a
    // controller-focused card AND a mouse-hovered card looking selected
    // at once.
    let lastMouseX = null;
    let lastMouseY = null;

    document.addEventListener('mousemove', e => {

        const moved =
            lastMouseX === null ||
            Math.hypot(e.clientX - lastMouseX, e.clientY - lastMouseY) > 3;

        lastMouseX = e.clientX;
        lastMouseY = e.clientY;

        if (!moved) {
            return;
        }

        const card = e.target.closest?.('#grid .card');

        if (card && gridCards().indexOf(card) !== focusIndex) {
            keyboardNavActive = false;
            clearGridFocus();
        }
    });

    // --------------------------------------------------------------
    // Polling loop
    // --------------------------------------------------------------

    async function poll() {

        if (!window.pywebview?.api?.get_controller_state) {
            return;
        }

        let state;

        try {
            state = await window.pywebview.api.get_controller_state();
        } catch {
            return;
        }

        if (!state) {
            return;
        }

        if (state.connected && !connected) {

            connected = true;

            if (controllerBadge) {
                controllerBadge.hidden = false;
                controllerBadgeText.textContent =
                    `${state.name || 'controller'} connected`;
            }

            focusIndex = 0;
            applyGridFocus();

        } else if (!state.connected && connected) {

            connected = false;

            if (controllerBadge) {
                controllerBadge.hidden = true;
            }

            clearGridFocus();
        }

        if (!connected) {
            return;
        }

        handleNav(state.nav);

        (state.pressed || []).forEach(handlePressed);
    }

    function start() {

        if (pollTimer) {
            return;
        }

        pollTimer = setInterval(poll, POLL_INTERVAL_MS);
    }

    if (window.pywebview) {
        start();
    } else {
        window.addEventListener('pywebviewready', start);
    }

})();
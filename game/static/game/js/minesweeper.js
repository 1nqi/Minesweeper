(function () {
    'use strict';

    var CSRF = document.querySelector('meta[name="csrf-token"]').content;

    var board = document.getElementById('board');
    var boardUnit = document.getElementById('board-unit');
    var minesLeft = document.getElementById('mines-left');
    var timerEl = document.getElementById('timer');
    var gameBanner = document.getElementById('game-banner');
    var bannerText = document.getElementById('banner-text');
    var panelStatus = document.getElementById('panel-status');
    var diffCurrentLabel = document.getElementById('diff-current-label');

    var gameState = null;
    var timerInterval = null;
    var localTime = 0;
    var currentDifficulty = 'beginner';
    var currentTheme = localStorage.getItem('ms-theme') || 'classic';

    var diffLabels = {
        beginner: 'Новичок',
        intermediate: 'Любитель',
        expert: 'Эксперт',
        custom: 'Своя игра'
    };

    function api(url, data) {
        var opts = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF
            }
        };
        if (data !== undefined) {
            opts.method = 'POST';
            opts.body = JSON.stringify(data);
        }
        return fetch(url, opts).then(function (r) { return r.json(); });
    }

    function padTimer(n) {
        if (n < 10) return '00' + n;
        if (n < 100) return '0' + n;
        return '' + n;
    }

    function startTimer() {
        stopTimer();
        localTime = 0;
        timerEl.textContent = '000';
        timerInterval = setInterval(function () {
            localTime++;
            timerEl.textContent = padTimer(localTime);
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function isDark(r, c) {
        return (r + c) % 2 === 1;
    }

    // вычисляет макс. размер клетки чтобы доска влезла на экран
    function calcCellSize(rows, cols) {
        var sidebar = window.innerWidth > 900 ? 220 : 0;
        var sidePanel = window.innerWidth > 900 ? 280 : 0;
        var hPad = 48 + 20;
        var vPad = 44 + 60;

        var availW = window.innerWidth - sidebar - sidePanel - hPad;
        var availH = window.innerHeight - vPad;

        if (window.innerWidth <= 900) {
            availW = window.innerWidth - 32;
            availH = window.innerHeight * 0.7;
        }

        var maxByW = Math.floor(availW / cols);
        var maxByH = Math.floor(availH / rows);
        var size = Math.min(maxByW, maxByH);
        return Math.max(18, Math.min(size, 48));
    }

    function applyCellSize(rows, cols) {
        var size = calcCellSize(rows, cols);
        board.style.setProperty('--cell-size', size + 'px');
        board.style.fontSize = Math.max(10, Math.round(size * 0.38)) + 'px';
    }

    function render(state) {
        gameState = state;

        applyCellSize(state.rows, state.cols);
        board.style.gridTemplateColumns = 'repeat(' + state.cols + ', var(--cell-size))';
        board.style.gridTemplateRows = 'repeat(' + state.rows + ', var(--cell-size))';
        board.innerHTML = '';

        minesLeft.textContent = state.mines - state.flags_count;

        boardUnit.classList.remove('game-won', 'game-lost');
        gameBanner.className = 'game-banner hidden';

        if (state.status === 'won') {
            boardUnit.classList.add('game-won');
            gameBanner.className = 'game-banner won';
            bannerText.textContent = 'Победа! Время: ' + state.elapsed.toFixed(1) + 's';
            panelStatus.textContent = 'Вы победили!';
            stopTimer();
            timerEl.textContent = padTimer(Math.floor(state.elapsed));
        } else if (state.status === 'lost') {
            boardUnit.classList.add('game-lost');
            gameBanner.className = 'game-banner lost';
            bannerText.textContent = 'Игра окончена — мина!';
            panelStatus.textContent = 'Игра проиграна';
            stopTimer();
            timerEl.textContent = padTimer(Math.floor(state.elapsed));
        } else if (state.status === 'playing') {
            panelStatus.textContent = 'Игра идёт...';
        } else {
            panelStatus.textContent = 'Готов к игре';
        }

        for (var r = 0; r < state.rows; r++) {
            for (var c = 0; c < state.cols; c++) {
                var cellData = state.cells[r][c];
                var el = document.createElement('div');
                el.className = 'cell';
                el.setAttribute('data-row', r);
                el.setAttribute('data-col', c);

                var dark = isDark(r, c);

                if (cellData.revealed) {
                    if (cellData.mine) {
                        el.classList.add('cell-mine');
                        el.textContent = '💣';
                    } else {
                        el.classList.add('cell-revealed');
                        if (dark) el.classList.add('cell-dark');
                        if (cellData.value > 0) {
                            el.textContent = cellData.value;
                            el.setAttribute('data-value', cellData.value);
                        }
                    }
                } else if (cellData.flagged) {
                    el.classList.add('cell-hidden', 'cell-flagged');
                    if (dark) el.classList.add('cell-dark');
                    el.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M6 3v14" stroke="#c62828" stroke-width="2.5" stroke-linecap="round"/><path d="M6 3l9 4.5L6 12V3z" fill="#c62828"/></svg>';
                } else {
                    el.classList.add('cell-hidden');
                    if (dark) el.classList.add('cell-dark');
                }

                board.appendChild(el);
            }
        }
    }

    board.addEventListener('click', function (e) {
        var cell = e.target.closest('.cell');
        if (!cell) return;
        if (!gameState || gameState.status === 'won' || gameState.status === 'lost') return;

        var row = parseInt(cell.getAttribute('data-row'));
        var col = parseInt(cell.getAttribute('data-col'));

        if (gameState.status === 'ready') startTimer();

        api('/play/api/reveal/', { row: row, col: col }).then(function (state) {
            render(state);
            if (state.status === 'won') {
                setTimeout(function () { showWinModal(state.elapsed); }, 400);
            }
        });
    });

    board.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        var cell = e.target.closest('.cell');
        if (!cell) return;
        if (!gameState || gameState.status === 'won' || gameState.status === 'lost') return;

        var row = parseInt(cell.getAttribute('data-row'));
        var col = parseInt(cell.getAttribute('data-col'));

        if (gameState.status === 'ready') startTimer();

        api('/play/api/flag/', { row: row, col: col }).then(function (state) {
            render(state);
        });
    });

    // средняя кнопка мыши — chord (раскрыть соседей)
    board.addEventListener('auxclick', function (e) {
        if (e.button !== 1) return;
        e.preventDefault();
        var cell = e.target.closest('.cell');
        if (!cell) return;
        if (!gameState || gameState.status !== 'playing') return;

        var row = parseInt(cell.getAttribute('data-row'));
        var col = parseInt(cell.getAttribute('data-col'));

        api('/play/api/reveal/', { row: row, col: col }).then(function (state) {
            render(state);
            if (state.status === 'won') {
                setTimeout(function () { showWinModal(state.elapsed); }, 400);
            }
        });
    });

    function newGame(difficulty, rows, cols, mines) {
        stopTimer();
        localTime = 0;
        timerEl.textContent = '000';
        currentDifficulty = difficulty;
        diffCurrentLabel.textContent = diffLabels[difficulty] || 'Своя игра';

        var payload = { difficulty: difficulty };
        if (rows) payload.rows = rows;
        if (cols) payload.cols = cols;
        if (mines) payload.mines = mines;

        api('/play/api/new/', payload).then(render);
    }

    document.getElementById('btn-restart').addEventListener('click', function () {
        newGame(currentDifficulty);
    });

    document.getElementById('banner-new-game').addEventListener('click', function () {
        newGame(currentDifficulty);
    });

    var dropdownBtn = document.getElementById('diff-dropdown-btn');
    var dropdownMenu = document.getElementById('diff-dropdown-menu');

    dropdownBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        dropdownMenu.classList.toggle('open');
    });

    // закрыть дропдаун при клике куда угодно
    document.addEventListener('click', function () {
        dropdownMenu.classList.remove('open');
    });

    document.querySelectorAll('.diff-dropdown__item').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.diff-dropdown__item').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            dropdownMenu.classList.remove('open');

            var diff = btn.getAttribute('data-diff');
            if (diff === 'custom') {
                showModal('custom-modal');
            } else {
                newGame(diff);
            }
        });
    });

    function setTheme(theme) {
        currentTheme = theme;
        boardUnit.setAttribute('data-theme', theme);
        localStorage.setItem('ms-theme', theme);
        document.querySelectorAll('.theme-swatch').forEach(function (s) {
            s.classList.toggle('active', s.getAttribute('data-theme') === theme);
        });
    }

    document.querySelectorAll('.theme-swatch').forEach(function (swatch) {
        swatch.addEventListener('click', function () {
            setTheme(swatch.getAttribute('data-theme'));
        });
    });

    setTheme(currentTheme);

    function showModal(id) {
        document.getElementById(id).classList.add('active');
    }

    function hideModal(id) {
        document.getElementById(id).classList.remove('active');
    }

    document.getElementById('custom-start').addEventListener('click', function () {
        var rows = parseInt(document.getElementById('custom-rows').value) || 16;
        var cols = parseInt(document.getElementById('custom-cols').value) || 16;
        var mines = parseInt(document.getElementById('custom-mines').value) || 40;
        hideModal('custom-modal');
        newGame('custom', rows, cols, mines);
    });

    document.getElementById('custom-cancel').addEventListener('click', function () {
        hideModal('custom-modal');
    });

    function showWinModal(elapsed) {
        document.getElementById('win-time').textContent = elapsed.toFixed(1);
        showModal('win-modal');
    }

    document.getElementById('win-save').addEventListener('click', function () {
        var name = document.getElementById('win-name').value.trim() || 'Аноним';
        api('/play/api/save/', { name: name }).then(function () {
            hideModal('win-modal');
        });
    });

    document.getElementById('win-skip').addEventListener('click', function () {
        hideModal('win-modal');
    });

    document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) overlay.classList.remove('active');
        });
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(function (m) {
                m.classList.remove('active');
            });
        }
    });

    var resizeTimeout;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function () {
            if (gameState) applyCellSize(gameState.rows, gameState.cols);
        }, 100);
    });

    newGame('beginner');
})();

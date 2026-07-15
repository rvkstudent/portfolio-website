/**
 * Anki Study — English-Russian cards
 * SM-2 spaced repetition in the browser
 * v3 — search with add-to-queue, improved repetition
 */
(function() {
    'use strict';

    const state = {
        cards: [],
        currentIndex: 0,
        isFlipped: false,
        isProcessing: false,
        searchedCards: {},
        stats: { studied: 0, due: 0, total: 0, intervals: { new: 0, learning: 0, young: 0, mature: 0 } }
    };

    const $ = (id) => document.getElementById(id);
    const qs = (sel) => document.querySelector(sel);
    const qsa = (sel) => document.querySelectorAll(sel);
    const dom = {};

    function initDom() {
        dom.loading = $('state-loading');
        dom.empty = $('state-empty');
        dom.cardContainer = $('card-container');
        dom.flashcard = $('flashcard');
        dom.front = $('card-front');
        dom.back = $('card-back');
        dom.showAnswer = $('btn-show-answer');
        dom.ratingButtons = $('rating-buttons');
        dom.cardWord = $('card-word');
        dom.cardIpa = $('card-ipa');
        dom.cardContext = $('card-context');
        dom.cardNumber = $('card-number');
        dom.cardTags = $('card-tags');
        dom.cardProgressInfo = $('card-progress-info');
        dom.backWord = $('back-word');
        dom.backTranslation = $('back-translation');
        dom.progressFill = $('progress-fill');
        dom.searchPanel = $('search-panel');
        dom.searchInput = $('search-input');
        dom.searchResults = $('search-results');
        dom.btnSearch = $('btn-search');
        dom.btnMoreNew = $('btn-more-new');
        dom.nextReviewInfo = $('next-review-info');
        dom.statStudied = $('stat-studied');
        dom.statDue = $('stat-due');
        dom.statTotal = $('stat-total');
        dom.chartNew = $('chart-new');
        dom.chartLearning = $('chart-learning');
        dom.chartYoung = $('chart-young');
        dom.chartMature = $('chart-mature');
    }

    // ===================== API =====================
    async function apiFetch(url, options = {}) {
        const resp = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest', ...options.headers },
            ...options
        });
        if (!resp.ok) {
            try {
                const err = await resp.json();
                throw new Error(err.error || resp.statusText);
            } catch (e) {
                if (e instanceof SyntaxError) throw new Error('Ошибка сервера');
                throw e;
            }
        }
        return resp.json();
    }

    async function loadCards() {
        try {
            const data = await apiFetch('/anki/api/due/');
            state.cards = [...data.due_cards, ...data.new_cards];
            state.stats.total = data.total;
            state.stats.due = data.due_count;
            state.stats.studied = data.studied_count;
            state.currentIndex = 0;
            return data;
        } catch (e) {
            console.error('Failed to load cards:', e);
            showError('Не удалось загрузить карточки: ' + e.message);
            return null;
        }
    }

    async function loadStats() {
        try {
            const data = await apiFetch('/anki/api/stats/');
            state.stats.intervals = data.intervals;
            updateStats(data);
        } catch (e) { console.error(e); }
    }

    async function submitReview(noteId, quality) {
        try {
            state.isProcessing = true;
            const data = await apiFetch('/anki/api/submit/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note_id: noteId, quality })
            });
            state.stats.studied++;
            return data;
        } catch (e) {
            console.error('Submit failed:', e);
            return null;
        } finally {
            state.isProcessing = false;
        }
    }

    async function searchCards(query) {
        try {
            return await apiFetch(`/anki/api/search/?q=${encodeURIComponent(query)}`);
        } catch (e) { return { results: [] }; }
    }

    async function addToQueue(noteId) {
        try {
            const data = await apiFetch('/anki/api/add-to-queue/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note_id: noteId })
            });
            return data;
        } catch (e) {
            console.error('Add to queue failed:', e);
            return null;
        }
    }

    // ===================== UI =====================
    function showState(name) {
        dom.loading.classList.toggle('hidden', name !== 'loading');
        dom.empty.classList.toggle('hidden', name !== 'empty');
        dom.cardContainer.classList.toggle('hidden', name !== 'cardContainer');
        dom.showAnswer.classList.add('hidden');
        dom.ratingButtons.classList.add('hidden');
    }

    function showCard(index) {
        if (index >= state.cards.length) {
            showState('empty');
            updateNextReviewInfo();
            return;
        }
        showState('cardContainer');
        const card = state.cards[index];
        if (!card) return;

        const progress = state.cards.length > 0 ? Math.round((index / state.cards.length) * 100) : 0;
        dom.progressFill.style.width = progress + '%';

        dom.cardNumber.textContent = `#${card.order_num || '?'}`;
        dom.cardWord.textContent = card.english || '?';
        dom.cardIpa.textContent = card.ipa ? `/${card.ipa.replace(/[\[\]]/g, '')}/` : '';
        dom.cardIpa.style.display = card.ipa ? '' : 'none';

        if (card.oxford_example) {
            const cleanExample = card.oxford_example.replace(/<[^>]+>/g, '').substring(0, 80);
            dom.cardContext.textContent = cleanExample ? `— ${cleanExample}…` : '';
            dom.cardContext.style.display = cleanExample ? '' : 'none';
        } else {
            dom.cardContext.style.display = 'none';
        }

        dom.cardTags.textContent = card.progress ? '\uD83D\uDD04' : '\uD83C\uDD95 Новое';
        if (card.progress) {
            dom.cardProgressInfo.textContent = `Инт: ${card.progress.interval}д | Повт: ${card.progress.reps} | Ф: ${card.progress.ease_factor}`;
        } else {
            dom.cardProgressInfo.textContent = 'Новая карточка';
        }

        dom.backWord.textContent = card.english || '';
        dom.backTranslation.textContent = card.russian || '';

        setDetail('detail-ipa', card.ipa ? `/${card.ipa.replace(/[\[\]]/g, '')}/` : '');
        setDetail('detail-example', card.oxford_example);
        setDetail('detail-example-enru', card.example_en_ru);
        setDetail('detail-collocations', card.collocations);
        setDetail('detail-synonyms', card.synonyms);
        setDetail('detail-wordfamily', card.word_family);
        setDetail('detail-definition', card.full_definition || card.oxford_definition);
        setDetail('detail-irregular', card.irregular_verbs);
        setDetail('detail-common-error', card.common_error);
        setDetail('detail-idioms', card.idioms_list || card.idiom);
        setDetail('detail-proverb', card.proverb);
        setDetail('detail-homonyms', card.homonyms);

        state.isFlipped = false;
        dom.front.classList.remove('hidden');
        dom.back.classList.add('hidden');
        dom.showAnswer.classList.remove('hidden');
        dom.ratingButtons.classList.add('hidden');

        dom.flashcard.classList.remove('card-enter');
        void dom.flashcard.offsetWidth;
        dom.flashcard.classList.add('card-enter');
    }

    function setDetail(id, content) {
        const el = document.getElementById(id);
        if (!el) return;
        if (content && content.trim()) {
            el.classList.remove('hidden');
            el.innerHTML = content;
        } else {
            el.classList.add('hidden');
        }
    }

    function flipCard() {
        if (state.isFlipped || state.isProcessing) return;
        state.isFlipped = true;
        dom.front.classList.add('hidden');
        dom.back.classList.remove('hidden');
        dom.showAnswer.classList.add('hidden');
        dom.ratingButtons.classList.remove('hidden');
    }

    function updateStats(data) {
        dom.statStudied.textContent = data.total_studied || state.stats.studied;
        dom.statDue.textContent = data.due_count || state.stats.due;
        dom.statTotal.textContent = state.stats.total;
        const intervals = data.intervals || state.stats.intervals;
        dom.chartNew.textContent = intervals.new || 0;
        dom.chartLearning.textContent = intervals.learning || 0;
        dom.chartYoung.textContent = intervals.young || 0;
        dom.chartMature.textContent = intervals.mature || 0;
    }

    function updateNextReviewInfo() {
        if (state.cards.length === 0) {
            dom.nextReviewInfo.textContent = 'Все карточки изучены! Возвращайтесь завтра.';
        }
    }

    function showMessage(msg, isError) {
        const el = document.createElement('div');
        el.className = 'anki-toast' + (isError ? ' anki-toast-error' : '');
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(() => { el.classList.add('anki-toast-show'); }, 10);
        setTimeout(() => {
            el.classList.remove('anki-toast-show');
            setTimeout(() => el.remove(), 300);
        }, 2000);
    }

    function showError(msg) {
        showMessage(msg, true);
    }

    // ===================== Actions =====================
    async function handleRating(quality) {
        if (state.isProcessing) return;
        const card = state.cards[state.currentIndex];
        if (!card) return;
        await submitReview(card.note_id, quality);
        state.currentIndex++;
        showCard(state.currentIndex);
        loadStats();
    }

    async function handleSearch(query) {
        if (!query || query.length < 2) {
            dom.searchResults.innerHTML = '';
            return;
        }
        const data = await searchCards(query);
        if (!data.results || data.results.length === 0) {
            dom.searchResults.innerHTML = '<div class="search-result-item search-result-empty">Ничего не найдено</div>';
            return;
        }

        // Get all studied note_ids to show correct status
        const studiedIds = new Set(state.cards.map(c => c.note_id));

        dom.searchResults.innerHTML = data.results.map(card => {
            const inQueue = studiedIds.has(card.note_id) || (card.progress && card.progress.reps > 0);
            return `
                <div class="search-result-item" data-note-id="${card.note_id}">
                    <div class="search-result-info" data-note-id="${card.note_id}">
                        <div class="search-result-word">${card.english}</div>
                        <div class="search-result-translation">${card.russian || ''}</div>
                        <div class="search-result-detail">${card.ipa ? '/' + card.ipa.replace(/[\[\]]/g, '') + '/' : ''} ${card.tags || ''}</div>
                    </div>
                    <div class="search-result-action">
                        ${inQueue
                            ? '<span class="search-result-check" title="Уже в изучении">\u2705</span>'
                            : '<button class="search-add-btn" data-note-id="' + card.note_id + '">\u2795 Добавить</button>'
                        }
                    </div>
                </div>
            `;
        }).join('');

        // Click on info area — navigate to card
        dom.searchResults.querySelectorAll('.search-result-info').forEach(el => {
            el.addEventListener('click', function() {
                const noteId = parseInt(this.dataset.noteId);
                const idx = state.cards.findIndex(c => c.note_id === noteId);
                if (idx >= 0) {
                    state.currentIndex = idx;
                    showCard(idx);
                    toggleSearch();
                } else {
                    showMessage('Сначала добавьте карточку в изучение через кнопку \u2795 Добавить');
                }
            });
        });

        // Click on add button — add to queue
        dom.searchResults.querySelectorAll('.search-add-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation();
                const noteId = parseInt(this.dataset.noteId);
                this.disabled = true;
                this.textContent = '\u23F3';
                const result = await addToQueue(noteId);
                if (result && result.success) {
                    this.textContent = '\u2705';
                    this.classList.add('search-add-btn-added');
                    showMessage('Карточка добавлена в изучение!');
                    // Reload cards in background
                    loadCards();
                    loadStats();
                } else {
                    this.textContent = '\u2795 Добавить';
                    this.disabled = false;
                    showMessage('Ошибка при добавлении', true);
                }
            });
        });
    }

    function toggleSearch() {
        dom.searchPanel.classList.toggle('hidden');
        if (!dom.searchPanel.classList.contains('hidden')) {
            dom.searchInput.focus();
            dom.searchInput.value = '';
            dom.searchResults.innerHTML = '';
        } else {
            dom.searchResults.innerHTML = '';
            dom.searchInput.value = '';
        }
    }

    // ===================== Keyboard =====================
    function handleKeydown(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            toggleSearch();
            return;
        }
        if (e.key === 'Escape') {
            if (!dom.searchPanel.classList.contains('hidden')) {
                toggleSearch();
                return;
            }
        }
        if (!dom.searchPanel.classList.contains('hidden')) return;
        switch (e.key) {
            case ' ':
                e.preventDefault();
                if (!state.isFlipped) handleShowAnswer();
                break;
            case '1': handleRating(1); break;
            case '2': handleRating(2); break;
            case '3': handleRating(3); break;
            case '4': handleRating(4); break;
            case '5': handleRating(5); break;
        }
    }

    function handleShowAnswer() { flipCard(); }

    // ===================== Init =====================
    async function init() {
        initDom();
        const data = await loadCards();
        if (!data) return;
        updateStats(data);
        if (state.cards.length > 0) showCard(0);
        else showState('empty');

        dom.flashcard.addEventListener('click', (e) => {
            if (!state.isFlipped) handleShowAnswer();
        });
        dom.showAnswer.addEventListener('click', handleShowAnswer);
        dom.btnMoreNew.addEventListener('click', async () => {
            showState('loading');
            const data = await loadCards();
            if (data) {
                updateStats(data);
                if (state.cards.length > 0) showCard(0);
                else showState('empty');
            }
        });
        dom.btnSearch.addEventListener('click', toggleSearch);

        qsa('.rating-btn').forEach(btn => {
            btn.addEventListener('click', () => handleRating(parseInt(btn.dataset.quality)));
        });

        let searchTimer;
        dom.searchInput.addEventListener('input', () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => handleSearch(dom.searchInput.value), 300);
        });

        document.addEventListener('keydown', handleKeydown);
        loadStats();
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();

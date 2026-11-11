// Review session: shows due cards one at a time and records each rating.
document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('review');
    const dataEl = document.getElementById('review-data');
    if (!root || !dataEl) return;

    let queue;
    try {
        queue = JSON.parse(dataEl.textContent).cards || [];
    } catch (e) {
        queue = [];
    }
    if (!queue.length) return;

    const STAGE_LABELS = { new: 'New', learning: 'Learning', mastered: 'Mastered' };
    const rateUrl = root.dataset.rateUrl;                       // ends with /0
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.content : '';

    const el = {
        session: document.getElementById('review-session'),
        summary: document.getElementById('review-summary'),
        summaryText: document.getElementById('review-summary-text'),
        fill: document.getElementById('review-progress-fill'),
        bar: document.getElementById('review-progressbar'),
        count: document.getElementById('review-count'),
        deck: document.getElementById('review-deck'),
        stage: document.getElementById('review-stage'),
        question: document.getElementById('review-question'),
        answerWrap: document.getElementById('review-answer-wrap'),
        answer: document.getElementById('review-answer'),
        reveal: document.getElementById('review-reveal'),
        ratings: document.getElementById('review-ratings'),
        rateButtons: Array.from(document.querySelectorAll('.review-rate')),
    };

    const total = queue.length;       // distinct cards in this session
    const finished = new Set();       // card ids rated Hard/Good/Easy (or gone)
    const tally = { 0: 0, 1: 0, 2: 0, 3: 0 };
    let current = null;
    let revealed = false;
    let saving = false;

    const notify = (message, category) => {
        if (window.BrainDump && window.BrainDump.toast) window.BrainDump.toast(message, category);
    };

    function updateProgress() {
        const done = finished.size;
        el.fill.style.width = `${(done / total) * 100}%`;
        el.bar.setAttribute('aria-valuenow', String(done));
        el.count.textContent = `${done} of ${total}`;
    }

    function showCard(card) {
        current = card;
        revealed = false;
        el.deck.textContent = card.deck;
        el.stage.textContent = STAGE_LABELS[card.stage] || '';
        el.stage.dataset.stage = card.stage;
        el.question.textContent = card.question;
        el.answer.textContent = card.answer;
        el.answerWrap.hidden = true;
        el.ratings.hidden = true;
        el.reveal.hidden = false;
        document.querySelectorAll('[data-when]').forEach((span) => {
            span.textContent = card.preview[span.dataset.when] || '';
        });
        setSaving(false);
        el.reveal.focus({ preventScroll: true });
    }

    function reveal() {
        if (!current || revealed) return;
        revealed = true;
        el.answerWrap.hidden = false;
        el.reveal.hidden = true;
        el.ratings.hidden = false;
        el.answer.focus({ preventScroll: true });
        el.answerWrap.scrollIntoView({ block: 'nearest' });
    }

    function setSaving(value) {
        saving = value;
        el.rateButtons.forEach((button) => { button.disabled = value; });
    }

    function next() {
        updateProgress();
        if (!queue.length) {
            finish();
            return;
        }
        showCard(queue.shift());
    }

    function finish() {
        current = null;
        el.session.hidden = true;
        el.summary.hidden = false;
        const reviews = tally[0] + tally[1] + tally[2] + tally[3];
        el.summaryText.textContent =
            `You reviewed ${total} card${total === 1 ? '' : 's'}` +
            (reviews > total ? ` in ${reviews} answers.` : '.');
        Object.keys(tally).forEach((rating) => {
            const cell = el.summary.querySelector(`[data-summary="${rating}"]`);
            if (cell) cell.textContent = String(tally[rating]);
        });
        el.summary.focus({ preventScroll: true });
    }

    async function rate(rating) {
        if (!current || !revealed || saving) return;
        const card = current;
        setSaving(true);

        let response;
        let body = null;
        try {
            response = await fetch(rateUrl.replace(/0$/, String(card.id)), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ rating, version: card.version }),
            });
            const isJson = (response.headers.get('content-type') || '').includes('application/json');
            if (response.redirected || !isJson) {
                throw new Error('Your session may have expired. Reload the page and sign in again.');
            }
            body = await response.json();
        } catch (error) {
            setSaving(false);
            notify(error.message && !/fetch/i.test(error.message)
                ? error.message
                : 'Could not save your answer. Check your connection and try again.', 'danger');
            return;
        }

        if (response.status === 404) {
            // Deleted elsewhere while this session was open: skip it
            finished.add(card.id);
            notify('That card was deleted, so it was skipped.', 'info');
            next();
            return;
        }
        if (response.status === 409) {
            // Already recorded (double tap or another tab): move on without counting twice
            finished.add(card.id);
            next();
            return;
        }
        if (!response.ok || !body.success) {
            setSaving(false);
            notify(body.error || 'Could not save your answer. Try again.', 'danger');
            return;
        }

        tally[rating] += 1;
        if (rating === 0) {
            // Again: see it once more at the end of this session
            queue.push({ ...card, version: body.version, preview: body.preview, stage: body.stage });
        } else {
            finished.add(card.id);
        }
        next();
    }

    el.reveal.addEventListener('click', reveal);
    el.rateButtons.forEach((button) => {
        button.addEventListener('click', () => rate(Number(button.dataset.rating)));
    });

    document.addEventListener('keydown', (event) => {
        if (!current || event.ctrlKey || event.metaKey || event.altKey) return;
        const target = event.target instanceof Element ? event.target : document.body;
        if (target.closest('a, input, textarea, select')) return;
        if (document.documentElement.classList.contains('sheet-open')) return;
        if (!revealed && (event.key === ' ' || event.key === 'Enter')) {
            // Let Enter/Space act normally when another button has focus
            if (target.closest('button') && target !== el.reveal) return;
            event.preventDefault();
            reveal();
        } else if (revealed && ['1', '2', '3', '4'].includes(event.key)) {
            event.preventDefault();
            rate(Number(event.key) - 1);
        }
    });

    updateProgress();
    showCard(queue.shift());
});

/* 自訂字卡：中英文學習 + 測驗
   資料儲存在 localStorage，格式：
   decks = [{ id, name, cards: [{ id, zh, en }] }]
*/

const STORAGE_KEY = 'flashcard_decks_v1';
const CURRENT_DECK_KEY = 'flashcard_current_deck_v1';

let decks = [];
let currentDeckId = null;

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function defaultDecks() {
  return [{
    id: uid(),
    name: '範例字卡',
    cards: [
      { id: uid(), zh: '蘋果', en: 'apple' },
      { id: uid(), zh: '香蕉', en: 'banana' },
      { id: uid(), zh: '貓', en: 'cat' },
      { id: uid(), zh: '狗', en: 'dog' },
      { id: uid(), zh: '書', en: 'book' },
      { id: uid(), zh: '學校', en: 'school' },
    ]
  }];
}

function loadDecks() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    decks = raw ? JSON.parse(raw) : defaultDecks();
    if (!Array.isArray(decks) || decks.length === 0) decks = defaultDecks();
  } catch (e) {
    decks = defaultDecks();
  }
  const savedCurrent = localStorage.getItem(CURRENT_DECK_KEY);
  currentDeckId = decks.some(d => d.id === savedCurrent) ? savedCurrent : decks[0].id;
  saveDecks();
}

function saveDecks() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(decks));
  localStorage.setItem(CURRENT_DECK_KEY, currentDeckId);
}

function getCurrentDeck() {
  return decks.find(d => d.id === currentDeckId) || decks[0];
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function normalize(s) {
  return (s || '').trim().toLowerCase().replace(/\s+/g, ' ');
}

/* ---------------- Modal dialogs (replaces prompt/confirm/alert,
   which sandboxed embeds such as the Artifact preview block) ---------------- */
function showModal({ message, input = false, defaultValue = '', cancel = true }) {
  return new Promise(resolve => {
    const overlay = document.getElementById('modalOverlay');
    const msgEl = document.getElementById('modalMessage');
    const inputEl = document.getElementById('modalInput');
    const okBtn = document.getElementById('modalOkBtn');
    const cancelBtn = document.getElementById('modalCancelBtn');

    msgEl.textContent = message;
    inputEl.style.display = input ? 'block' : 'none';
    inputEl.value = defaultValue;
    cancelBtn.style.display = cancel ? 'inline-block' : 'none';

    overlay.hidden = false;
    if (input) { inputEl.focus(); inputEl.select(); } else { okBtn.focus(); }

    function cleanup(result) {
      overlay.hidden = true;
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      inputEl.removeEventListener('keydown', onKeydown);
      overlay.removeEventListener('mousedown', onOverlayClick);
      resolve(result);
    }
    function onOk() { cleanup(input ? inputEl.value.trim() : true); }
    function onCancel() { cleanup(input ? null : false); }
    function onKeydown(e) {
      if (e.key === 'Enter') { e.preventDefault(); onOk(); }
      if (e.key === 'Escape') onCancel();
    }
    function onOverlayClick(e) { if (e.target === overlay) onCancel(); }

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    inputEl.addEventListener('keydown', onKeydown);
    overlay.addEventListener('mousedown', onOverlayClick);
  });
}

function modalPrompt(message, defaultValue = '') {
  return showModal({ message, input: true, defaultValue, cancel: true });
}
function modalConfirm(message) {
  return showModal({ message, input: false, cancel: true });
}
function modalAlert(message) {
  return showModal({ message, input: false, cancel: false });
}

/* ---------------- Tabs ---------------- */
function initTabs() {
  document.querySelectorAll('.nav-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'study') restartStudy();
      if (btn.dataset.tab === 'quiz') { renderQuizDeckSelect(); showQuizSetup(); }
      if (btn.dataset.tab === 'manage') renderManage();
    });
  });
}

/* ---------------- Deck selects (shared) ---------------- */
function populateDeckSelect(selectEl) {
  selectEl.innerHTML = '';
  decks.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = `${d.name} (${d.cards.length})`;
    if (d.id === currentDeckId) opt.selected = true;
    selectEl.appendChild(opt);
  });
}

function renderAllDeckSelects() {
  populateDeckSelect(document.getElementById('deckSelect'));
  populateDeckSelect(document.getElementById('studyDeckSelect'));
  populateDeckSelect(document.getElementById('quizDeckSelect'));
}

function setCurrentDeck(id) {
  currentDeckId = id;
  saveDecks();
  renderAllDeckSelects();
  renderManage();
  restartStudy();
  renderQuizDeckSelect();
  showQuizSetup();
}

/* ---------------- Manage tab ---------------- */
function renderManage() {
  renderAllDeckSelects();
  const deck = getCurrentDeck();
  const tbody = document.getElementById('cardTableBody');
  tbody.innerHTML = '';
  document.getElementById('cardCount').textContent = deck.cards.length;
  document.getElementById('cardEmptyState').style.display = deck.cards.length === 0 ? 'block' : 'none';

  deck.cards.forEach(card => {
    const tr = document.createElement('tr');

    const zhTd = document.createElement('td');
    const zhInput = document.createElement('input');
    zhInput.type = 'text';
    zhInput.value = card.zh;
    zhInput.addEventListener('change', () => { card.zh = zhInput.value.trim(); saveDecks(); });
    zhTd.appendChild(zhInput);

    const enTd = document.createElement('td');
    const enInput = document.createElement('input');
    enInput.type = 'text';
    enInput.value = card.en;
    enInput.addEventListener('change', () => { card.en = enInput.value.trim(); saveDecks(); });
    enTd.appendChild(enInput);

    const actionTd = document.createElement('td');
    actionTd.className = 'row-actions';
    const delBtn = document.createElement('button');
    delBtn.textContent = '🗑️';
    delBtn.title = '刪除這張字卡';
    delBtn.addEventListener('click', () => {
      deck.cards = deck.cards.filter(c => c.id !== card.id);
      saveDecks();
      renderManage();
    });
    actionTd.appendChild(delBtn);

    tr.appendChild(zhTd);
    tr.appendChild(enTd);
    tr.appendChild(actionTd);
    tbody.appendChild(tr);
  });
}

function initManage() {
  document.getElementById('deckSelect').addEventListener('change', e => setCurrentDeck(e.target.value));

  document.getElementById('newDeckBtn').addEventListener('click', async () => {
    const name = await modalPrompt('新字卡集名稱：', '我的字卡');
    if (!name) return;
    const deck = { id: uid(), name: name.trim(), cards: [] };
    decks.push(deck);
    setCurrentDeck(deck.id);
  });

  document.getElementById('renameDeckBtn').addEventListener('click', async () => {
    const deck = getCurrentDeck();
    const name = await modalPrompt('重新命名字卡集：', deck.name);
    if (!name) return;
    deck.name = name.trim();
    saveDecks();
    renderAllDeckSelects();
    renderManage();
  });

  document.getElementById('deleteDeckBtn').addEventListener('click', async () => {
    if (decks.length <= 1) { await modalAlert('至少需要保留一個字卡集。'); return; }
    const deck = getCurrentDeck();
    const ok = await modalConfirm(`確定要刪除字卡集「${deck.name}」嗎？此操作無法復原。`);
    if (!ok) return;
    decks = decks.filter(d => d.id !== deck.id);
    setCurrentDeck(decks[0].id);
  });

  document.getElementById('addCardBtn').addEventListener('click', async () => {
    const zhInput = document.getElementById('newZh');
    const enInput = document.getElementById('newEn');
    const zh = zhInput.value.trim();
    const en = enInput.value.trim();
    if (!zh || !en) { await modalAlert('請同時輸入中文與英文。'); return; }
    getCurrentDeck().cards.push({ id: uid(), zh, en });
    saveDecks();
    zhInput.value = '';
    enInput.value = '';
    zhInput.focus();
    renderManage();
  });

  document.getElementById('newEn').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('addCardBtn').click();
  });

  document.getElementById('bulkImportBtn').addEventListener('click', async () => {
    const text = document.getElementById('bulkText').value;
    const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
    let added = 0;
    const deck = getCurrentDeck();
    lines.forEach(line => {
      const parts = line.split(/,|-| - /).map(p => p.trim()).filter(Boolean);
      if (parts.length >= 2) {
        const zh = parts[0];
        const en = parts.slice(1).join(' ');
        if (zh && en) {
          deck.cards.push({ id: uid(), zh, en });
          added++;
        }
      }
    });
    if (added === 0) {
      await modalAlert('沒有解析到有效字卡，請確認格式為「中文,英文」或「中文 - 英文」，每行一筆。');
      return;
    }
    saveDecks();
    document.getElementById('bulkText').value = '';
    renderManage();
    await modalAlert(`已匯入 ${added} 筆字卡。`);
  });

  document.getElementById('bulkClearBtn').addEventListener('click', () => {
    document.getElementById('bulkText').value = '';
  });
}

/* ---------------- Study tab ---------------- */
let studyQueue = [];
let studyIndex = 0;
let studyFlipped = false;

function restartStudy() {
  const deck = getCurrentDeck();
  document.getElementById('studyDeckSelect').value = currentDeckId;
  const order = document.getElementById('studyOrder').value;
  const cards = order === 'shuffle' ? shuffle(deck.cards) : deck.cards.slice();
  studyQueue = cards;
  studyIndex = 0;
  studyFlipped = false;

  const empty = studyQueue.length === 0;
  document.getElementById('studyEmpty').style.display = empty ? 'block' : 'none';
  document.getElementById('studyStage').style.display = empty ? 'none' : 'flex';
  if (!empty) renderStudyCard();
}

function renderStudyCard() {
  const card = studyQueue[studyIndex];
  const flashcard = document.getElementById('flashcard');
  flashcard.textContent = studyFlipped ? card.en : card.zh;
  document.getElementById('studyProgress').textContent =
    `第 ${studyIndex + 1} / ${studyQueue.length} 張　${studyFlipped ? '（英文）點擊可翻回中文' : '（中文）點擊可翻至英文'}`;
}

function studyNext() {
  if (studyQueue.length === 0) return;
  studyIndex = (studyIndex + 1) % studyQueue.length;
  studyFlipped = false;
  renderStudyCard();
}

function studyPrev() {
  if (studyQueue.length === 0) return;
  studyIndex = (studyIndex - 1 + studyQueue.length) % studyQueue.length;
  studyFlipped = false;
  renderStudyCard();
}

function initStudy() {
  document.getElementById('studyDeckSelect').addEventListener('change', e => setCurrentDeck(e.target.value));
  document.getElementById('studyOrder').addEventListener('change', restartStudy);
  document.getElementById('studyRestartBtn').addEventListener('click', restartStudy);
  document.getElementById('flipCardBtn').addEventListener('click', () => {
    if (studyQueue.length === 0) return;
    studyFlipped = !studyFlipped;
    renderStudyCard();
  });
  document.getElementById('flashcard').addEventListener('click', () => {
    if (studyQueue.length === 0) return;
    studyFlipped = !studyFlipped;
    renderStudyCard();
  });
  document.getElementById('prevCardBtn').addEventListener('click', studyPrev);
  document.getElementById('nextCardBtn').addEventListener('click', studyNext);
  document.getElementById('markKnownBtn').addEventListener('click', studyNext);
  document.getElementById('markUnknownBtn').addEventListener('click', studyNext);
}

/* ---------------- Quiz tab ---------------- */
let quizQuestions = [];
let quizIndex = 0;
let quizScore = 0;
let quizAnswers = [];
let quizLocked = false;

function renderQuizDeckSelect() {
  document.getElementById('quizDeckSelect').value = currentDeckId;
}

function showQuizSetup() {
  document.getElementById('quizSetupPanel').style.display = 'block';
  document.getElementById('quizPlayPanel').style.display = 'none';
  document.getElementById('quizResultPanel').style.display = 'none';
}

function buildQuizQuestions(deck, direction, count) {
  const pool = shuffle(deck.cards).slice(0, count);
  return pool.map(card => {
    let dir = direction;
    if (direction === 'mixed') dir = Math.random() < 0.5 ? 'zh2en' : 'en2zh';
    return { card, dir };
  });
}

function startQuiz() {
  const deck = getCurrentDeck();
  const direction = document.getElementById('quizDirection').value;
  const type = document.getElementById('quizType').value;
  let count = parseInt(document.getElementById('quizCount').value, 10) || 10;
  count = Math.max(1, Math.min(count, deck.cards.length));

  if (deck.cards.length === 0 || (type === 'choice' && deck.cards.length < 4)) {
    document.getElementById('quizEmpty').style.display = 'block';
    return;
  }
  document.getElementById('quizEmpty').style.display = 'none';

  quizQuestions = buildQuizQuestions(deck, direction, count);
  quizIndex = 0;
  quizScore = 0;
  quizAnswers = [];

  document.getElementById('quizSetupPanel').style.display = 'none';
  document.getElementById('quizPlayPanel').style.display = 'block';
  document.getElementById('quizResultPanel').style.display = 'none';
  renderQuizQuestion();
}

function currentAnswerField(dir) {
  return dir === 'zh2en' ? 'en' : 'zh';
}
function currentPromptField(dir) {
  return dir === 'zh2en' ? 'zh' : 'en';
}

function renderQuizQuestion() {
  quizLocked = false;
  const type = document.getElementById('quizType').value;
  const q = quizQuestions[quizIndex];
  const promptField = currentPromptField(q.dir);
  const answerField = currentAnswerField(q.dir);

  document.getElementById('quizProgress').textContent =
    `第 ${quizIndex + 1} / ${quizQuestions.length} 題　目前得分：${quizScore}`;
  document.getElementById('quizPromptLabel').textContent =
    q.dir === 'zh2en' ? '請選出正確的英文' : '請選出正確的中文';
  document.getElementById('quizPromptText').textContent = q.card[promptField];
  document.getElementById('quizFeedback').textContent = '';
  document.getElementById('quizFeedback').className = 'quiz-feedback';

  const optionsEl = document.getElementById('quizOptions');
  const typeinEl = document.getElementById('quizTypein');
  optionsEl.innerHTML = '';

  if (type === 'choice') {
    typeinEl.style.display = 'none';
    optionsEl.style.display = 'grid';
    const correct = q.card[answerField];
    const deck = getCurrentDeck();
    const otherValues = deck.cards
      .filter(c => c.id !== q.card.id)
      .map(c => c[answerField])
      .filter((v, i, arr) => v !== correct && arr.indexOf(v) === i);
    const distractors = shuffle(otherValues).slice(0, 3);
    const options = shuffle([correct, ...distractors]);
    options.forEach(optText => {
      const btn = document.createElement('button');
      btn.textContent = optText;
      btn.addEventListener('click', () => handleAnswer(optText, correct, btn));
      optionsEl.appendChild(btn);
    });
  } else {
    optionsEl.style.display = 'none';
    typeinEl.style.display = 'flex';
    const input = document.getElementById('quizTypeinInput');
    input.value = '';
    input.disabled = false;
    input.focus();
  }
}

function handleAnswer(selected, correct, btnEl) {
  if (quizLocked) return;
  quizLocked = true;
  const isCorrect = normalize(selected) === normalize(correct);
  if (isCorrect) quizScore++;
  quizAnswers.push({
    prompt: document.getElementById('quizPromptText').textContent,
    userAnswer: selected,
    correctAnswer: correct,
    isCorrect
  });

  const feedback = document.getElementById('quizFeedback');
  feedback.textContent = isCorrect ? '✅ 答對了！' : `❌ 答錯了，正確答案：${correct}`;
  feedback.className = 'quiz-feedback ' + (isCorrect ? 'correct' : 'wrong');

  if (btnEl) {
    document.querySelectorAll('#quizOptions button').forEach(b => {
      b.disabled = true;
      if (normalize(b.textContent) === normalize(correct)) b.classList.add('correct');
      else if (b === btnEl) b.classList.add('wrong');
    });
  } else {
    document.getElementById('quizTypeinInput').disabled = true;
  }

  setTimeout(() => {
    quizIndex++;
    if (quizIndex >= quizQuestions.length) finishQuiz();
    else renderQuizQuestion();
  }, 1000);
}

function finishQuiz() {
  document.getElementById('quizPlayPanel').style.display = 'none';
  document.getElementById('quizResultPanel').style.display = 'block';
  const total = quizQuestions.length;
  const pct = total ? Math.round((quizScore / total) * 100) : 0;
  document.getElementById('quizScoreText').textContent = `${quizScore} / ${total}（${pct}%）`;

  const reviewEl = document.getElementById('quizReview');
  if (quizAnswers.every(a => a.isCorrect)) {
    reviewEl.innerHTML = '<p>🎉 全部答對，太棒了！</p>';
    return;
  }
  let html = '<h3>答錯的題目</h3><table><thead><tr><th>題目</th><th>你的答案</th><th>正確答案</th></tr></thead><tbody>';
  quizAnswers.filter(a => !a.isCorrect).forEach(a => {
    html += `<tr><td>${escapeHtml(a.prompt)}</td><td class="wrong-ans">${escapeHtml(a.userAnswer || '（未作答）')}</td><td class="correct-ans">${escapeHtml(a.correctAnswer)}</td></tr>`;
  });
  html += '</tbody></table>';
  reviewEl.innerHTML = html;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function initQuiz() {
  document.getElementById('quizDeckSelect').addEventListener('change', e => setCurrentDeck(e.target.value));
  document.getElementById('startQuizBtn').addEventListener('click', startQuiz);
  document.getElementById('quizRetryBtn').addEventListener('click', showQuizSetup);
  document.getElementById('quizBackBtn').addEventListener('click', showQuizSetup);
  document.getElementById('quizTypeinSubmit').addEventListener('click', () => {
    const q = quizQuestions[quizIndex];
    const answerField = currentAnswerField(q.dir);
    const input = document.getElementById('quizTypeinInput');
    handleAnswer(input.value.trim(), q.card[answerField], null);
  });
  document.getElementById('quizTypeinInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('quizTypeinSubmit').click();
  });
}

/* ---------------- Init ---------------- */
document.addEventListener('DOMContentLoaded', () => {
  loadDecks();
  initTabs();
  initManage();
  initStudy();
  initQuiz();
  renderManage();
  renderQuizDeckSelect();
});

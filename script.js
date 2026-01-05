
// 全域資料存儲
let state = {
    people: [],
    duties: []
};
let db = null; // Firestore instance
let useFirebase = false; // 模式旗標
let selectedPersonId = null; // 手機版點擊選擇狀態

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    try {
        initSystem();
        initTabs();
        setupEventListeners();
    } catch (e) {
        console.error("Init Error:", e);
        alert("系統初始化失敗: " + e.message);
    }
});

function initSystem() {
    // 檢查 Firebase 設定是否有效
    if (typeof firebase !== 'undefined' && typeof firebaseConfig !== 'undefined') {
        if (firebaseConfig.apiKey === "YOUR_API_KEY" || !firebaseConfig.apiKey) {
            console.warn("Firebase 未設定，切換至本地儲存模式。");
            useFirebase = false;
        } else {
            try {
                firebase.initializeApp(firebaseConfig);
                db = firebase.firestore();
                useFirebase = true;
                console.log("Firebase initialized");
            } catch (e) {
                console.error("Firebase init failed:", e);
                useFirebase = false;
            }
        }
    } else {
        useFirebase = false;
    }

    updateModeUI();

    if (useFirebase) {
        subscribeToData();
    } else {
        loadFromLocal();
    }
}

function updateModeUI() {
    const statusEl = document.getElementById('saveStatus');
    if (statusEl) {
        if (useFirebase) {
            statusEl.innerHTML = '<span style="color:#27ae60;">☁️ 雲端同步中</span>';
        } else {
            statusEl.innerHTML = '<span style="color:#f39c12;">📂 本地儲存模式</span>';
        }
    }
}

// ================= 資料同步與讀取 =================

function subscribeToData() {
    if (!db) return;

    db.collection("people").onSnapshot((snapshot) => {
        const remotePeople = [];
        snapshot.forEach((doc) => {
            remotePeople.push({ id: doc.id, ...doc.data() });
        });
        state.people = remotePeople;
        render();
    }, (error) => console.error("Error getting people:", error));

    db.collection("duties").onSnapshot((snapshot) => {
        state.duties = [];
        snapshot.forEach((doc) => {
            state.duties.push({ id: doc.id, ...doc.data() });
        });
        render();
    }, (error) => console.error("Error getting duties:", error));
}

function loadFromLocal() {
    const savedPeople = localStorage.getItem('rollcall_people');
    const savedDuties = localStorage.getItem('rollcall_duties');

    if (savedPeople) state.people = JSON.parse(savedPeople);
    if (savedDuties) state.duties = JSON.parse(savedDuties);

    // 預設公差 (如果完全是新的)
    if (state.duties.length === 0) {
        state.duties = [
            { id: 'duty_1', name: '公差' },
            { id: 'duty_2', name: '休假' },
            { id: 'duty_3', name: '衛哨' }
        ];
        saveToLocal();
    }

    render();
}

function saveToLocal() {
    localStorage.setItem('rollcall_people', JSON.stringify(state.people));
    localStorage.setItem('rollcall_duties', JSON.stringify(state.duties));
}

function render() {
    renderRollCall();
    renderSettings();
    renderReport();
}

// ================= 資料操作 (自動儲存版) =================

// 1. 新增人員
async function addPerson(name, unit) {
    if (!name.trim()) return;
    const finalUnit = unit.trim() || '預設建置班';
    const newPerson = {
        name: name.trim(),
        unit: finalUnit,
        dutyId: null,
        createdAt: new Date().toISOString()
    };

    if (useFirebase) {
        try {
            await db.collection("people").add({
                ...newPerson,
                createdAt: firebase.firestore.FieldValue.serverTimestamp()
            });
        } catch (e) { alert("新增失敗: " + e.message); }
    } else {
        newPerson.id = 'local_' + Date.now() + Math.random().toString(36).substr(2, 9);
        state.people.push(newPerson);
        saveToLocal();
        render();
    }
}

// 2. 新增公差
async function addDuty(name) {
    if (!name.trim()) return;
    if (useFirebase) {
        try {
            await db.collection("duties").add({
                name: name.trim(),
                createdAt: firebase.firestore.FieldValue.serverTimestamp()
            });
        } catch (e) { console.error(e); }
    } else {
        const newDuty = {
            id: 'duty_' + Date.now(),
            name: name.trim()
        };
        state.duties.push(newDuty);
        saveToLocal();
        render();
    }
}

// 3. 刪除人員
async function deletePerson(id) {
    if (!confirm('確定要刪除此人員嗎？')) return;

    if (useFirebase) {
        try { await db.collection("people").doc(id).delete(); } catch (e) { console.error(e); }
    } else {
        state.people = state.people.filter(p => p.id !== id);
        saveToLocal();
        render();
    }
}

// 4. 刪除公差
async function deleteDuty(id) {
    if (!confirm('確定要刪除此公差類別嗎？')) return;

    if (useFirebase) {
        try {
            await db.collection("duties").doc(id).delete();
            const batch = db.batch();
            let count = 0;
            state.people.filter(p => p.dutyId === id).forEach(p => {
                const ref = db.collection("people").doc(p.id);
                batch.update(ref, { dutyId: null });
                count++;
            });
            if (count > 0) await batch.commit();
        } catch (e) { console.error(e); }
    } else {
        state.duties = state.duties.filter(d => d.id !== id);
        state.people.forEach(p => {
            if (p.dutyId === id) p.dutyId = null;
        });
        saveToLocal();
        render();
    }
}

// 5. 移動人員
async function movePerson(personId, targetDutyId) {
    const finalDutyId = targetDutyId === 'unassigned' ? null : targetDutyId;
    const person = state.people.find(p => p.id === personId);

    if (person && person.dutyId !== finalDutyId) {
        person.dutyId = finalDutyId;

        // Optimistic UI Update
        render();

        if (useFirebase) {
            try {
                if (personId.startsWith('local_')) {
                    console.warn("Cannot sync local-only person to remote yet.");
                    return;
                }
                await db.collection("people").doc(personId).update({ dutyId: finalDutyId });
            } catch (e) {
                console.error("Auto-save failed:", e);
                // 實際應用可能需要 rollback
            }
        } else {
            saveToLocal();
        }
    }
}

// 6. 重置
async function resetData() {
    if (!confirm('確定清除所有資料？')) return;

    if (useFirebase) {
        const batch = db.batch();
        state.people.forEach(p => batch.delete(db.collection("people").doc(p.id)));
        state.duties.forEach(d => batch.delete(db.collection("duties").doc(d.id)));
        try {
            await batch.commit();
        } catch (e) {
            console.error("Reset failed", e);
        }
    } else {
        state.people = [];
        state.duties = [];
        saveToLocal();
        render();
    }

    // 如果有搜尋字串，重新觸發 input 事件以清除或更新
    const searchInput = document.getElementById('searchInput');
    if (searchInput && searchInput.value) {
        searchInput.value = '';
    }
}

// ================= UI 渲染邏輯 =================

function renderRollCall() {
    const container = document.getElementById('unassignedList');
    const unitFilter = document.getElementById('unitFilter');
    if (!container) return;

    // 更新篩選器選單
    if (unitFilter) {
        const allUnits = new Set(state.people.map(p => p.unit || '預設建置班'));
        const currentVal = unitFilter.value;
        const opts = Array.from(unitFilter.options).map(o => o.value);

        allUnits.forEach(u => {
            if (!opts.includes(u)) {
                const opt = document.createElement('option');
                opt.value = u;
                opt.innerText = u;
                unitFilter.appendChild(opt);
            }
        });
    }

    const filterValue = unitFilter ? unitFilter.value : 'all';
    // 篩選未分配且符合單位的人
    const unassignedPeople = state.people.filter(p => !p.dutyId && (filterValue === 'all' || (p.unit || '預設建置班') === filterValue));

    container.innerHTML = '';
    if (unassignedPeople.length === 0) {
        container.innerHTML = '<div class="empty-state">暫無未分配人員</div>';
    } else {
        unassignedPeople.forEach(person => {
            container.appendChild(createPersonCard(person));
        });
    }
    const unCount = document.getElementById('unassignedCount');
    if (unCount) unCount.innerText = unassignedPeople.length;

    const dutiesContainer = document.getElementById('dutiesContainer');
    if (dutiesContainer) {
        dutiesContainer.innerHTML = '';
        state.duties.forEach(duty => {
            const count = state.people.filter(p => p.dutyId === duty.id).length;
            const col = document.createElement('div');
            col.className = 'duty-column';
            col.innerHTML = `
            <div class="duty-header"><span>${duty.name} <span class="badge">(${count})</span></span></div>
            <div class="duty-content" id="${duty.id}"></div>
        `;
            const content = col.querySelector('.duty-content');
            const assigned = state.people.filter(p => p.dutyId === duty.id);
            if (assigned.length === 0) content.innerHTML = '<div class="empty-state" style="font-size:0.8em; margin-top:20px;">無人分配</div>';
            else assigned.forEach(p => content.appendChild(createPersonCard(p)));
            dutiesContainer.appendChild(col);
        });
    }
}

function createPersonCard(person) {
    const div = document.createElement('div');
    div.className = 'person-card';

    // Header row: Name and Unit
    const header = document.createElement('div');
    header.className = 'person-header';
    header.innerHTML = `
        <div class="person-name">${person.name}</div>
        <div class="person-unit">${person.unit || '預設'}</div>
    `;
    div.appendChild(header);

    // Dropdown row
    const select = document.createElement('select');
    select.className = 'person-duty-select';

    // Default option (Unassigned)
    const defaultOpt = document.createElement('option');
    defaultOpt.value = 'unassigned';
    defaultOpt.innerText = '未分配';
    if (!person.dutyId) defaultOpt.selected = true;
    select.appendChild(defaultOpt);

    // Duty options
    state.duties.forEach(duty => {
        const opt = document.createElement('option');
        opt.value = duty.id;
        opt.innerText = duty.name;
        if (person.dutyId === duty.id) opt.selected = true;
        select.appendChild(opt);
    });

    // Change event
    select.addEventListener('change', (e) => {
        const newDutyId = e.target.value === 'unassigned' ? null : e.target.value;
        movePerson(person.id, newDutyId);
    });

    div.appendChild(select);
    return div;
}

// Remove old handlePersonClick and handleTargetClick as they are replaced by dropdown logic

function renderSettings() {
    const peopleList = document.getElementById('settingsPeopleList');
    if (peopleList) {
        peopleList.innerHTML = '';
        state.people.forEach(p => {
            const item = document.createElement('div');
            item.className = 'settings-item';
            // 注意：這裡使用 onclick 屬性直接呼叫 global function
            // 為了避免作用域問題，deletePerson 必須是 Global 的
            item.innerHTML = `<span>${p.name}</span><span>${p.unit || ''}</span><button class="btn btn-danger" onclick="deletePerson('${p.id}')">刪除</button>`;
            peopleList.appendChild(item);
        });
    }
    const dutyList = document.getElementById('settingsDutyList');
    if (dutyList) {
        dutyList.innerHTML = '';
        state.duties.forEach(d => {
            const item = document.createElement('div');
            item.className = 'settings-item';
            item.innerHTML = `<span>${d.name}</span><span></span><button class="btn btn-danger" onclick="deleteDuty('${d.id}')">刪除</button>`;
            dutyList.appendChild(item);
        });
    }
}

function renderReport() {
    const reportContainer = document.getElementById('reportContent');
    if (!reportContainer) return;

    // Title Update
    const sessionSelect = document.getElementById('sessionSelect');
    const sessionName = sessionSelect ? sessionSelect.value : '';
    const reportTitle = document.querySelector('#tab-report h2');
    if (reportTitle) {
        reportTitle.innerText = `${sessionName ? '[' + sessionName + '] ' : ''}建置班統計報表`;
    }

    const totalCountEl = document.getElementById('totalPeopleCount');
    const totalDutyEl = document.getElementById('totalDutyCount');
    if (totalCountEl) totalCountEl.innerText = state.people.length;

    let dutiesCount = 0;
    const dutyStats = {};

    state.people.forEach(p => {
        if (p.dutyId) {
            dutiesCount++;
            const dName = getDutyName(p.dutyId);
            dutyStats[dName] = (dutyStats[dName] || 0) + 1;
        }
    });
    if (totalDutyEl) totalDutyEl.innerText = dutiesCount;

    // Global Stats Bar
    const globalStatsContainer = document.getElementById('globalDutyStats');
    if (globalStatsContainer) {
        globalStatsContainer.innerHTML = '';
        if (dutiesCount === 0) {
            globalStatsContainer.innerHTML = '<span style="color:#888;">無公差人員</span>';
        } else {
            Object.entries(dutyStats).forEach(([key, val]) => {
                const item = document.createElement('div');
                item.className = 'duty-stat-item';
                item.innerHTML = `<strong>${key}:</strong><span>${val}</span>`;
                globalStatsContainer.appendChild(item);
            });
        }
    }

    // Units
    reportContainer.innerHTML = '';
    const units = {};
    state.people.forEach(p => {
        const u = p.unit || '預設建置班';
        if (!units[u]) units[u] = [];
        units[u].push(p);
    });

    for (const [unitName, people] of Object.entries(units)) {
        const uDutyStats = {};
        people.forEach(p => {
            const d = getDutyName(p.dutyId);
            uDutyStats[d] = (uDutyStats[d] || 0) + 1;
        });
        const statsStr = Object.entries(uDutyStats).map(([k, v]) => `${k}:${v}`).join(' | ');

        const card = document.createElement('details');
        card.className = 'unit-card';
        card.open = true;
        let html = `
        <summary class="unit-header"><span>${unitName}</span><span>${people.length} 人</span></summary>
        <div class="unit-stats" style="padding: 0 10px 10px;">${statsStr}</div>
    `;
        people.forEach(p => {
            const dName = getDutyName(p.dutyId);
            const statusClass = p.dutyId ? 'active-duty' : 'unassigned';
            html += `<div class="unit-person-row"><span>${p.name}</span><span class="status-tag ${statusClass}">${dName}</span></div>`;
        });
        card.innerHTML = html;
        reportContainer.appendChild(card);
    }
}


function getDutyName(id) {
    const d = state.duties.find(x => x.id === id);
    return d ? d.name : '未知';
}

function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => {
                c.classList.remove('active');
                c.style.display = 'none';
            });

            tab.classList.add('active');
            const tabId = tab.dataset.tab;
            const content = document.getElementById(`tab-${tabId}`);
            if (content) {
                content.classList.add('active');
                if (tabId === 'rollcall') {
                    content.style.display = 'flex';
                } else {
                    content.style.display = 'block';
                }
            }
            if (tabId === 'report') renderReport();
        });
    });
}

function setupEventListeners() {
    // 移除舊的點擊監聽器，只保留功能性按鈕

    const addP = document.getElementById('addPersonBtn');
    if (addP) {
        addP.addEventListener('click', () => {
            const nameEl = document.getElementById('newPersonName');
            const unitEl = document.getElementById('newPersonUnit');
            if (nameEl.value) {
                addPerson(nameEl.value, unitEl.value);
                nameEl.value = '';
                // unitEl.value = ''; // 通常建置班會連續輸入，保留比較方便，或者清空也可
            }
        });
    }



    const addD = document.getElementById('addDutyBtn');
    if (addD) addD.addEventListener('click', () => {
        const dEl = document.getElementById('newDutyInput');
        if (dEl.value) {
            addDuty(dEl.value);
            dEl.value = '';
        }
    });

    const reset = document.getElementById('resetDataBtn');
    if (reset) reset.addEventListener('click', resetData);

    const copyRep = document.getElementById('copyReportBtn');
    if (copyRep) copyRep.addEventListener('click', () => {
        const container = document.getElementById('reportContent');
        if (container) {
            navigator.clipboard.writeText(container.innerText).then(() => alert('報表已複製'));
        }
    });

    const exportBtn = document.getElementById('exportJSONBtn'); // 注意 ID 大小寫修正 (原 HTML 是 exportJSONBtn)
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const dataStr = JSON.stringify(state, null, 2);
            const blob = new Blob([dataStr], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `rollcall_backup_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    const search = document.getElementById('searchInput'); // 雖然 HTML 裡沒有這個 ID，但保留邏輯
    if (search) search.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase().trim();
        document.querySelectorAll('.person-card, .settings-item').forEach(el => {
            // 排除設定頁的表頭
            if (el.classList.contains('settings-item') && !el.parentElement.id.includes('List')) return;

            el.classList.toggle('hidden', !el.innerText.toLowerCase().includes(q));
        });
    });

    const unitFilter = document.getElementById('unitFilter');
    if (unitFilter) unitFilter.addEventListener('change', renderRollCall);

    // Session Selector Listener
    const sessionSelect = document.getElementById('sessionSelect');
    if (sessionSelect) {
        sessionSelect.addEventListener('change', () => {
            renderReport(); // Re-render report to update title
        });
    }
}

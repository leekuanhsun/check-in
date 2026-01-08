
// 全域資料存儲
let state = {
    people: [],
    duties: [],
    currentSession: '早點名' // 預設時段
};

// Custom Sort Orders
const UNIT_ORDER = [
    '一班', '二班', '三班', '四班', '五班', '六班',
    '七班', '八班', '九班', '十班', '十一班', '十二班',
    '中隊部', '參謀區隊部'
];

const GROUP_ORDER = [
    '115一般', '115結構', '115發修', '115航設',
    '116一般', '116結構', '116發修', '116航設',
    '專軍'
];

function getCustomSortValue(val, orderArray) {
    const index = orderArray.indexOf(val);
    if (index !== -1) return index;
    // If not in list, put at the end, sorted alphabetically
    return orderArray.length + val.charCodeAt(0);
}

function compareCustomOrder(a, b, orderArray) {
    const valA = getCustomSortValue(a, orderArray);
    const valB = getCustomSortValue(b, orderArray);
    return valA - valB;
}
let db = null; // Firestore instance
let useFirebase = false; // 模式旗標
let selectedPersonId = null; // 手機版點擊選擇狀態

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    try {
        initSystem();
        initTabs();
        setupEventListeners();

        // 初始化時段選擇器狀態
        const sessionStore = document.getElementById('sessionSelect');
        if (sessionStore) {
            state.currentSession = sessionStore.value;
        }
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

    if (savedPeople) {
        state.people = JSON.parse(savedPeople);
        // 資料遷移: 舊版 dutyId 轉為 assignments
        state.people.forEach(p => {
            if (!p.assignments) {
                p.assignments = {};
                if (p.dutyId) {
                    p.assignments['早點名'] = p.dutyId; // 假設舊資料屬於早點名，或可選擇丟棄
                    delete p.dutyId;
                }
            }
        });
    }
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
    renderGroupReport();
}

// ================= 資料操作 (自動儲存版) =================

// 1. 新增人員
async function addPerson(name, unit, group) {
    if (!name.trim()) return;
    const finalUnit = unit.trim() || '預設建置班';
    const finalGroup = group.trim() || '';
    const newPerson = {
        name: name.trim(),
        unit: finalUnit,
        group: finalGroup,
        assignments: {}, // 初始化空的分配表
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

async function handleBatchAdd() {
    const input = document.getElementById('batchInput');
    if (!input) return;

    const text = input.value.trim();
    if (!text) {
        alert('請輸入資料');
        return;
    }

    const lines = text.split('\n');
    let successCount = 0;

    if (!confirm(`即將匯入 ${lines.length} 筆資料，確定嗎？`)) return;

    for (const line of lines) {
        const parts = line.trim().split(/\s+/); // Split by whitespace
        if (parts.length >= 1) {
            const name = parts[0];
            const unit = parts[1] || '';
            const group = parts[2] || '';

            if (name) {
                await addPerson(name, unit, group);
                successCount++;
            }
        }
    }

    alert(`已完成匯入 ${successCount} 筆資料`);
    input.value = '';
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
            // 這裡簡化處理：實際上若要從 map 中刪除特定 value 比較複雜
            // 建議在前端 render 時若 dutyId 不存在就視為未分配
            // 但為了數據一致性，這裡可以做一個遍歷清除
            console.warn("Firestore delete duty: assignments cleanup skipped for simplicity.");
        } catch (e) { console.error(e); }
    } else {
        state.duties = state.duties.filter(d => d.id !== id);
        state.people.forEach(p => {
            if (p.assignments) {
                Object.keys(p.assignments).forEach(session => {
                    if (p.assignments[session] === id) {
                        p.assignments[session] = null;
                    }
                });
            }
        });
        saveToLocal();
        render();
    }
}

// 5. 移動人員
// 5. 移動人員
async function movePerson(personId, targetDutyId) {
    const finalDutyId = targetDutyId === 'unassigned' ? null : targetDutyId;
    const person = state.people.find(p => p.id === personId);
    const session = state.currentSession;

    if (person) {
        if (!person.assignments) person.assignments = {};

        // 檢查是否真的變更
        if (person.assignments[session] !== finalDutyId) {
            person.assignments[session] = finalDutyId;

            // Optimistic UI Update
            render();

            if (useFirebase) {
                try {
                    if (personId.startsWith('local_')) {
                        console.warn("Cannot sync local-only person to remote yet.");
                        return;
                    }
                    // 更新 Firestore: 使用點符號語法更新特定 key，例如 "assignments.早點名"
                    // 注意：key 包含空格或特殊字元可能需要處理，這裡先假設簡單字串
                    await db.collection("people").doc(personId).update({
                        [`assignments.${session}`]: finalDutyId
                    });
                } catch (e) {
                    console.error("Auto-save failed:", e);
                }
            } else {
                saveToLocal();
            }
        }
    }
}

// 6. 重置
async function resetData() {
    if (!confirm('【警告 1/3】確定要清除所有資料嗎？此動作無法復原。')) return;
    if (!confirm('【警告 2/3】您真的確定嗎？清除後所有人員與公差設定都會消失。')) return;
    if (!confirm('【警告 3/3】這是最後一次確認。按下「確定」將立即刪除所有資料！')) return;

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
    const groupFilter = document.getElementById('groupFilter');
    if (!container) return;

    // 更新篩選器選單
    if (unitFilter) {
        // ... (Unit filter population logic remains the same, but let's optimize to not clear every time if possible, or just keep it simple)
        // Ideally we should separate option population from render loop to avoid re-rendering options constantly, 
        // but for now let's keep the pattern but add group logic. 
        // Actually, re-populating on every render might be annoying if selection is lost, 
        // but renderRollCall is called on filter change. 
        // Let's protect the selection.

        const populateOptions = (selectEl, options, defaultLabel) => {
            const currentVal = selectEl.value;
            // distinct values
            const existingOpts = Array.from(selectEl.options).map(o => o.value);
            options.forEach(opt => {
                if (!existingOpts.includes(opt)) {
                    const el = document.createElement('option');
                    el.value = opt;
                    el.innerText = opt;
                    selectEl.appendChild(el);
                }
            });
            // Restore selection if it still exists (it should)
            selectEl.value = currentVal;
        };

        const allUnits = new Set(state.people.map(p => p.unit || '預設建置班'));
        populateOptions(unitFilter, allUnits, '所有建置班');
    }

    if (groupFilter) {
        const populateOptions = (selectEl, options, defaultLabel) => {
            const currentVal = selectEl.value;
            const existingOpts = Array.from(selectEl.options).map(o => o.value);
            options.forEach(opt => {
                if (!existingOpts.includes(opt)) {
                    const el = document.createElement('option');
                    el.value = opt;
                    el.innerText = opt;
                    selectEl.appendChild(el);
                }
            });
            selectEl.value = currentVal;
        };

        const allGroups = new Set(state.people.map(p => p.group || '未分組'));
        populateOptions(groupFilter, allGroups, '所有組別');
    }

    const unitVal = unitFilter ? unitFilter.value : 'all';
    const groupVal = groupFilter ? groupFilter.value : 'all';

    // 篩選未分配且符合單位的人 (依據當前時段)
    const currentSession = state.currentSession;

    const unassignedPeople = state.people.filter(p => {
        const dutyId = p.assignments ? p.assignments[currentSession] : null;
        const matchUnit = unitVal === 'all' || (p.unit || '預設建置班') === unitVal;
        const matchGroup = groupVal === 'all' || (p.group || '未分組') === groupVal;

        return !dutyId && matchUnit && matchGroup;
    });

    container.innerHTML = '';
    if (unassignedPeople.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.innerText = '暫無人員';
        container.appendChild(empty);
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
            // 統計該時段分配到此公差的人數
            const count = state.people.filter(p => p.assignments && p.assignments[currentSession] === duty.id).length;
            const col = document.createElement('div');
            col.className = 'duty-column';
            col.innerHTML = `
            <div class="duty-header"><span>${duty.name} <span class="badge">(${count})</span></span></div>
            <div class="duty-content" id="${duty.id}"></div>
        `;
            const content = col.querySelector('.duty-content');
            const assigned = state.people.filter(p => p.assignments && p.assignments[currentSession] === duty.id);
            if (assigned.length === 0) content.innerHTML = '<div class="empty-state" style="font-size:0.8em; margin-top:20px;">無人分配</div>';
            else assigned.forEach(p => content.appendChild(createPersonCard(p)));
            dutiesContainer.appendChild(col);
        });
    }
}

function createPersonCard(person) {
    const div = document.createElement('div');
    div.className = 'person-card';

    // Header row: Name and Unit/Group
    const header = document.createElement('div');
    header.className = 'person-header';
    const groupText = person.group ? ` | ${person.group}` : '';
    header.innerHTML = `
        <div class="person-name">${person.name}</div>
        <div class="person-unit">${person.unit || '預設'}${groupText}</div>
    `;
    div.appendChild(header);

    // Dropdown row
    const select = document.createElement('select');
    select.className = 'person-duty-select';

    // 取得當前時段的分配
    const currentSession = state.currentSession;
    const currentDutyId = person.assignments ? person.assignments[currentSession] : null;

    // Default option (Unassigned)
    const defaultOpt = document.createElement('option');
    defaultOpt.value = 'unassigned';
    defaultOpt.innerText = '無公差';
    if (!currentDutyId) defaultOpt.selected = true;
    select.appendChild(defaultOpt);

    // Duty options
    state.duties.forEach(duty => {
        const opt = document.createElement('option');
        opt.value = duty.id;
        opt.innerText = duty.name;
        if (currentDutyId === duty.id) opt.selected = true;
        select.appendChild(opt);
    });

    // Change event
    select.addEventListener('change', (e) => {
        const newDutyId = e.target.value === 'unassigned' ? null : e.target.value;
        movePerson(person.id, newDutyId); // movePerson 已改為讀取 state.currentSession
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
            // 為了避免作用域問題，deletePerson 必須是 Global 的
            item.innerHTML = `<span>${p.name}</span><span>${p.unit || ''}</span><span>${p.group || ''}</span><button class="btn btn-danger" onclick="deletePerson('${p.id}')">刪除</button>`;
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

    // Update Advanced Export Unit Select
    updateExportUnitSelect();

    // 5. title update ...

    const totalCountEl = document.getElementById('totalPeopleCount');
    const actualCountEl = document.getElementById('actualPeopleCount');
    const totalDutyEl = document.getElementById('totalDutyCount');

    if (totalCountEl) totalCountEl.innerText = state.people.length;

    // Fix: Define totalPeople
    const totalPeople = state.people ? state.people.length : 0;
    const currentSession = state.currentSession || '早點名'; // Fallback

    let dutiesCount = 0;
    const dutyStats = {};

    try {
        if (state.people) {
            state.people.forEach(p => {
                const dId = p.assignments ? p.assignments[currentSession] : null;
                if (dId) {
                    dutiesCount++;
                    const dName = getDutyName(dId);
                    dutyStats[dName] = (dutyStats[dName] || 0) + 1;
                }
            });
        }
    } catch (e) {
        console.error("Error calculating duties:", e);
    }

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

    // Update Actual Count (Total - Duty)
    if (actualCountEl) actualCountEl.innerText = totalPeople - dutiesCount;

    // Units
    reportContainer.innerHTML = '';
    const units = {};
    if (state.people) {
        state.people.forEach(p => {
            const u = p.unit || '預設建置班';
            if (!units[u]) units[u] = [];
            units[u].push(p);
        });
    }

    try {
        // Sort Units by Custom Order
        const sortedUnits = Object.keys(units).sort((a, b) => compareCustomOrder(a, b, UNIT_ORDER));

        for (const unitName of sortedUnits) {
            const people = units[unitName];
            const uDutyStats = {};
            people.forEach(p => {
                const dId = p.assignments ? p.assignments[currentSession] : null;
                const d = getDutyName(dId);
                uDutyStats[d] = (uDutyStats[d] || 0) + 1;
            });
            const statsStr = Object.entries(uDutyStats).map(([k, v]) => `${k}:${v}`).join(' | ');

            const card = document.createElement('div');
            card.className = 'unit-card';
            let html = `
            <div class="unit-header"><span>${unitName}</span><span>${people.length} 人</span></div>
            <div class="unit-stats" style="padding: 0 0 10px;">${statsStr}</div>
        `;
            people.forEach(p => {
                const dId = p.assignments ? p.assignments[currentSession] : null;
                const dName = getDutyName(dId);
                const statusClass = dId ? 'active-duty' : 'unassigned';
                html += `<div class="unit-person-row"><span>${p.name}</span><span class="status-tag ${statusClass}">${dName}</span></div>`;
            });
            card.innerHTML = html;
            reportContainer.appendChild(card);
        }
    } catch (e) {
        console.error("Error rendering unit cards:", e);
        reportContainer.innerHTML += `<div style="color:red">Rendering Error: ${e.message}</div>`;
    }
}

function renderGroupReport() {
    const reportContainer = document.getElementById('groupReportContent');
    if (!reportContainer) return;

    // Title Update
    const sessionSelect = document.getElementById('sessionSelect');
    const sessionName = sessionSelect ? sessionSelect.value : '';
    const reportTitle = document.querySelector('#tab-group-report h2');
    if (reportTitle) {
        reportTitle.innerText = `${sessionName ? '[' + sessionName + '] ' : ''}組別統計報表`;
    }

    const totalCountEl = document.getElementById('groupTotalPeopleCount');
    const actualCountEl = document.getElementById('groupActualPeopleCount');
    const totalDutyCountEl = document.getElementById('groupTotalDutyCount');

    if (totalCountEl) totalCountEl.innerText = state.people.length;

    // Calculate Global Actual Count for Group Report
    let totalDutyCount = 0;
    state.people.forEach(p => {
        if (p.assignments && p.assignments[state.currentSession]) {
            totalDutyCount++;
        }
    });
    if (actualCountEl) actualCountEl.innerText = state.people.length - totalDutyCount;
    if (totalDutyCountEl) totalDutyCountEl.innerText = totalDutyCount;

    const currentSession = state.currentSession;

    // Groups
    reportContainer.innerHTML = '';
    const groups = {};
    const unassignedGroup = '未分組';

    state.people.forEach(p => {
        const g = p.group || unassignedGroup;
        if (!groups[g]) groups[g] = [];
        groups[g].push(p);
    });

    // Sort keys to make output stable
    const sortedKeys = Object.keys(groups).sort((a, b) => compareCustomOrder(a, b, GROUP_ORDER));

    if (sortedKeys.length === 0) {
        reportContainer.innerHTML = '<div class="empty-state">暫無人員資料</div>';
        return;
    }

    // 1. Generate Summary Table
    const tableContainer = document.createElement('div');
    tableContainer.className = 'report-table-container';

    const table = document.createElement('table');
    table.className = 'report-table';

    // Collect all duty IDs present (or all duties from state)
    // using state.duties ensures consistent column order
    const dutyColumns = state.duties;

    // Header
    const thead = document.createElement('thead');
    let headerHtml = '<tr><th style="text-align:left;">組別</th><th>應到</th><th>實到</th>';
    dutyColumns.forEach(d => {
        headerHtml += `<th>${d.name}</th>`;
    });
    headerHtml += '</tr>';
    thead.innerHTML = headerHtml;
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    for (const groupName of sortedKeys) {
        const people = groups[groupName];
        const gDutyCounts = {};

        let groupDutyCount = 0;
        people.forEach(p => {
            const dId = p.assignments ? p.assignments[currentSession] : null;
            if (dId) {
                gDutyCounts[dId] = (gDutyCounts[dId] || 0) + 1;
                groupDutyCount++;
            }
        });

        const tr = document.createElement('tr');
        const shouldAttend = people.length;
        const actualAttend = shouldAttend - groupDutyCount;
        let rowHtml = `<td class="group-name">${groupName}</td><td><strong>${shouldAttend}</strong></td><td class="has-count">${actualAttend}</td>`;

        dutyColumns.forEach(d => {
            const count = gDutyCounts[d.id] || 0;
            const classStr = count > 0 ? 'has-count' : 'zero-count';
            const displayCount = count > 0 ? count : '-';
            rowHtml += `<td class="${classStr}">${displayCount}</td>`;
        });

        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    tableContainer.appendChild(table);
    reportContainer.appendChild(tableContainer);

    // 2. Generate Detail Cards (Original Logic)
    for (const groupName of sortedKeys) {
        const people = groups[groupName];
        const gDutyStats = {};
        people.forEach(p => {
            const dId = p.assignments ? p.assignments[currentSession] : null;
            const d = getDutyName(dId);
            gDutyStats[d] = (gDutyStats[d] || 0) + 1;
        });
        const statsStr = Object.entries(gDutyStats).map(([k, v]) => `${k}:${v}`).join(' | ');

        const card = document.createElement('details');
        card.className = 'unit-card'; // Reuse unit-card style
        card.open = true;
        let html = `
        <summary class="unit-header"><span>${groupName}</span><span>${people.length} 人</span></summary>
        <div class="unit-stats" style="padding: 0 10px 10px;">${statsStr}</div>
    `;
        people.forEach(p => {
            const dId = p.assignments ? p.assignments[currentSession] : null;
            const dName = getDutyName(dId);
            const statusClass = dId ? 'active-duty' : 'unassigned';
            html += `<div class="unit-person-row"><span>${p.name} <span style="font-size:0.8em; color:#666;">(${p.unit || '-'})</span></span><span class="status-tag ${statusClass}">${dName}</span></div>`;
        });
        card.innerHTML = html;
        reportContainer.appendChild(card);
    }
}


function generateCopyText(mode) {
    const currentSession = state.currentSession;
    const groups = {};
    const unassignedLabel = '未分配';

    // Global Stats Variables
    let globalShouldAttend = 0;
    let globalDutyCount = 0;
    const globalDutyMap = {}; // name -> array of person names

    // Grouping
    state.people.forEach(p => {
        let key = '';
        if (mode === 'unit') key = p.unit || '預設建置班';
        else key = p.group || '未分組';

        if (!groups[key]) groups[key] = [];
        groups[key].push(p);

        // Global Calc
        globalShouldAttend++;
        const dId = p.assignments ? p.assignments[currentSession] : null;
        if (dId) {
            globalDutyCount++;
            const dName = getDutyName(dId);
            if (!globalDutyMap[dName]) globalDutyMap[dName] = [];
            globalDutyMap[dName].push(p.name);
        }
    });

    const sortedKeys = Object.keys(groups).sort((a, b) =>
        compareCustomOrder(a, b, mode === 'unit' ? UNIT_ORDER : GROUP_ORDER)
    );
    let output = '';

    // Add Session Title
    const sessionSelect = document.getElementById('sessionSelect');
    const sessionName = sessionSelect ? sessionSelect.value : '';
    output += `[${sessionName}] ${mode === 'unit' ? '建置班' : '組別'}統計報表\n\n`;

    sortedKeys.forEach(key => {
        const people = groups[key];
        let dutyCount = 0;
        const localDutyMap = {};

        people.forEach(p => {
            const dId = p.assignments ? p.assignments[currentSession] : null;
            if (dId) {
                dutyCount++;
                const dName = getDutyName(dId);

                if (!localDutyMap[dName]) localDutyMap[dName] = [];
                localDutyMap[dName].push(p.name);
            }
        });

        const shouldAttend = people.length;
        const actualAttend = shouldAttend - dutyCount;

        output += `${key}\n`;
        output += `應到：${shouldAttend}\n`;
        output += `公差：${dutyCount}\n`;

        // 格式: 伙委2:李冠勳 李柏鍵
        if (dutyCount > 0) {
            Object.entries(localDutyMap).forEach(([dName, pNames]) => {
                output += `${dName}${pNames.length}:${pNames.join(' ')}\n`;
            });
        }
        output += `實到：${actualAttend}\n`;
        output += `----------------\n`;
    });

    // Append Global Summary
    output += `統計總數\n`;
    output += `應到：${globalShouldAttend}\n`;
    output += `實到：${globalShouldAttend - globalDutyCount}\n`;
    output += `公差\n`;

    Object.keys(globalDutyMap).forEach(dName => {
        const names = globalDutyMap[dName];
        output += `${dName}${names.length}：${names.join(' ')}\n`;
    });

    return output;
}

function getDutyName(id) {
    if (!id) return '無';
    const d = state.duties.find(x => x.id === id);
    return d ? d.name : '無';
}

function updateExportUnitSelect() {
    const select = document.getElementById('exportUnitSelect');
    if (!select) return;

    // Check if distinct from last render to avoid flickering/resetting selection? 
    // For simplicity, re-populate if filtering changes, or just populate once.
    // Let's populate every time but keep selection if possible.
    const currentVal = select.value;
    select.innerHTML = '<option value="">選擇建置班...</option>';

    const units = [...new Set(state.people.map(p => p.unit || '預設建置班'))].sort((a, b) => compareCustomOrder(a, b, UNIT_ORDER));
    units.forEach(u => {
        const opt = document.createElement('option');
        opt.value = u;
        opt.innerText = u;
        if (u === currentVal) opt.selected = true;
        select.appendChild(opt);
    });
}



function generateUnitAllSessionReport(unitName) {
    if (!unitName) return '請先選擇建置班';

    const sessionSelect = document.getElementById('sessionSelect');
    const allSessions = Array.from(sessionSelect.options).map(o => o.value);

    // Filter people in this unit
    const unitPeople = state.people.filter(p => (p.unit || '預設建置班') === unitName);
    const shouldAttend = unitPeople.length;

    let output = `[${unitName}] 全時段公差彙整\n\n`;
    output += `${unitName}\n\n`;

    allSessions.forEach(sess => {
        output += `${sess}\n`;
        output += `應到${shouldAttend}\n`;

        // Calculate duties for this session
        const dutyMap = {}; // DutyName -> [PersonName]
        let totalDutyCount = 0;

        unitPeople.forEach(p => {
            const dId = p.assignments ? p.assignments[sess] : null;
            if (dId) {
                const dName = getDutyName(dId);
                if (!dutyMap[dName]) dutyMap[dName] = [];
                dutyMap[dName].push(p.name);
                totalDutyCount++;
            }
        });

        // Print Duty Lines (Sorted by system duty order)
        if (state.duties) {
            state.duties.forEach(d => {
                const dName = d.name;
                if (dutyMap[dName]) {
                    const names = dutyMap[dName];
                    output += `${dName}${names.length} ${names.join(' ')}\n`;
                }
            });
        }

        output += `實到：${shouldAttend - totalDutyCount}\n`;
        output += `_________________\n\n`;
    });

    return output;
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
            if (tabId === 'group-report') renderGroupReport();
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
            const groupEl = document.getElementById('newPersonGroup');
            if (nameEl.value) {
                addPerson(nameEl.value, unitEl.value, groupEl ? groupEl.value : '');
                nameEl.value = '';
                // unitEl.value = ''; 
                // groupEl.value = '';
            }
        });
    }

    const batchAdd = document.getElementById('batchAddBtn');
    if (batchAdd) {
        batchAdd.addEventListener('click', handleBatchAdd);
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
        const text = generateCopyText('unit');
        navigator.clipboard.writeText(text).then(() => alert('建置班報表已複製'));
    });

    const copyGroupRep = document.getElementById('copyGroupReportBtn');
    if (copyGroupRep) copyGroupRep.addEventListener('click', () => {
        const text = generateCopyText('group');
        navigator.clipboard.writeText(text).then(() => alert('組別報表已複製'));
    });

    const copyUnitAll = document.getElementById('copyUnitAllSessionBtn');
    if (copyUnitAll) copyUnitAll.addEventListener('click', () => {
        const unit = document.getElementById('exportUnitSelect').value;
        if (!unit) { alert('請選擇建置班'); return; }
        const text = generateUnitAllSessionReport(unit);
        navigator.clipboard.writeText(text).then(() => alert(`${unit} 全時段報表已複製`));
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

    const groupFilter = document.getElementById('groupFilter');
    if (groupFilter) groupFilter.addEventListener('change', renderRollCall);

    // Session Selector Listener
    const sessionSelect = document.getElementById('sessionSelect');
    if (sessionSelect) {
        sessionSelect.addEventListener('change', (e) => {
            state.currentSession = e.target.value;
            render(); // Re-render everything (RollCall + Report + Settings)
        });
    }
}

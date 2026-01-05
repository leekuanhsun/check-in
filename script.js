
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
        initTabs(); // 確保此函數存在且被呼叫
        setupEventListeners();
    } catch (e) {
        console.error("Init Error:", e);
        alert("系統初始化失敗: " + e.message);

        // 1. Remove active from all tabs
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

        // 2. Hide all contents
        document.querySelectorAll('.tab-content').forEach(c => {
            c.classList.remove('active');
            c.style.display = 'none'; // Ensure hidden
        });

        // 3. Activate clicked tab
        tab.classList.add('active');

        // 4. Show target content
        const tabId = tab.dataset.tab; // e.g., 'rank' -> 'tab-rank'
        const content = document.getElementById(`tab-${tabId}`);
        if (content) {
            content.classList.add('active');
            content.style.display = 'flex'; // Ensure visible (override CSS if needed)
        } else {
            console.error(`Tab content not found: tab-${tabId}`);
        }

        // 5. Render specific views if needed
        if (tabId === 'report') renderReport();
    });
    });
}

function render() {
    renderRollCall();
    renderSettings();
    renderReport();

    const searchInput = document.getElementById('searchInput');
    if (searchInput && searchInput.value) searchInput.dispatchEvent(new Event('input'));
}

function renderRollCall() {
    const container = document.getElementById('unassignedList');
    const unitFilter = document.getElementById('unitFilter');
    if (!container) return;

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
    const unassignedPeople = state.people.filter(p => !p.dutyId && (filterValue === 'all' || (p.unit || '預設建置班') === filterValue));

    container.innerHTML = '';
    if (unassignedPeople.length === 0) {
        container.innerHTML = '<div class="empty-state">暫無未分配人員</div>';
    } else {
        unassignedPeople.forEach(person => {
            container.appendChild(createPersonCard(person));
        });
    }
    document.getElementById('unassignedCount').innerText = unassignedPeople.length;

    const dutiesContainer = document.getElementById('dutiesContainer');
    if (dutiesContainer) {
        dutiesContainer.innerHTML = '';
        state.duties.forEach(duty => {
            const count = state.people.filter(p => p.dutyId === duty.id).length;
            const col = document.createElement('div');
            col.className = 'duty-column';
            col.innerHTML = `
                <div class="duty-header"><span>${duty.name} <span class="badge">(${count})</span></span></div>
                <div class="duty-content" id="${duty.id}" ondrop="drop(event, '${duty.id}')" ondragover="allowDrop(event)"></div>
            `;
            const content = col.querySelector('.duty-content');
            const assigned = state.people.filter(p => p.dutyId === duty.id);
            if (assigned.length === 0) content.innerHTML = '<div class="empty-state" style="font-size:0.8em; margin-top:20px;">拖曳至此</div>';
            else assigned.forEach(p => content.appendChild(createPersonCard(p)));
            dutiesContainer.appendChild(col);
        });
    }
}

function createPersonCard(person) {
    const div = document.createElement('div');
    div.className = 'person-card';
    if (selectedPersonId === person.id) div.classList.add('selected'); // Highlight if selected
    div.draggable = true;
    div.id = person.id;
    div.innerHTML = `<span>${person.name} <small style="color:#888;">(${person.unit || '預設'})</small></span>`;

    // Drag Events
    div.addEventListener('dragstart', drag);

    // Check Events (for Mobile/Click interaction)
    div.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent bubbling
        handlePersonClick(person.id);
    });

    return div;
}

function renderSettings() {
    const peopleList = document.getElementById('settingsPeopleList');
    if (peopleList) {
        peopleList.innerHTML = '';
        state.people.forEach(p => {
            const item = document.createElement('div');
            item.className = 'settings-item';
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

    // Stats
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

        const card = document.createElement('details'); // Use details for expand/collapse
        card.className = 'unit-card';
        card.open = true; // Default expanded as requested
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
    if (!id) return '未分配';
    const d = state.duties.find(x => x.id === id);
    return d ? d.name : '未知';
}

function allowDrop(ev) {
    ev.preventDefault();
    const t = ev.target.closest('.duty-content') || ev.target.closest('.people-list-container');
    if (t) t.classList.add('drag-over');
}
function drag(ev) { ev.dataTransfer.setData("text", ev.target.id); }
function drop(ev, targetId) {
    ev.preventDefault();
    const pid = ev.dataTransfer.getData("text");
    document.querySelectorAll('.drag-over').forEach(e => e.classList.remove('drag-over'));
    movePerson(pid, targetId);
}

// === Click/Tap Interaction Handler ===
function handlePersonClick(pid) {
    if (selectedPersonId === pid) {
        // Deselect
        selectedPersonId = null;
    } else {
        // Select
        selectedPersonId = pid;
    }
    render(); // Re-render to show selection highlight
    updateTargetHints();
}

function handleTargetClick(targetDutyId) {
    if (selectedPersonId) {
        movePerson(selectedPersonId, targetDutyId);
        selectedPersonId = null; // Clear selection after move
        render();
    }
}

function updateTargetHints() {
    // Optional: Visual cue for where to click
    const targets = document.querySelectorAll('.duty-content, .people-list-container');
    targets.forEach(t => {
        if (selectedPersonId) t.classList.add('selectable-target');
        else t.classList.remove('selectable-target');
    });
}
// =====================================

function setupEventListeners() {
    // Add click listeners to Duty Containers for tap-to-move
    const unList = document.getElementById('unassignedList');
    // Using delegation on unList parent? No, unList IS the container.
    // But clicking a person card inside unList bubbles up. We stopped propagation in createPersonCard, so it's fine.
    if (unList) {
        unList.addEventListener('click', () => {
            if (selectedPersonId) handleTargetClick('unassigned');
        });
    }

    // Since duty columns are dynamic, we delegate or add listeners in render, 
    // BUT we can also use event delegation on the container parent if possible, 
    // or just rely on the onclick attributes we might add, OR add listener in render.
    // Let's add delegation on dutiesContainer.
    const dCont = document.getElementById('dutiesContainer');
    if (dCont) {
        dCont.addEventListener('click', (e) => {
            const dutyContent = e.target.closest('.duty-content');
            if (dutyContent && selectedPersonId) {
                handleTargetClick(dutyContent.id);
            }
        });
    }

    const addP = document.getElementById('addPersonBtn');
    if (addP) {
        addP.addEventListener('click', () => {
            const nameEl = document.getElementById('newPersonName');
            const unitEl = document.getElementById('newPersonUnit');
            if (nameEl.value) {
                addPerson(nameEl.value, unitEl.value);
                nameEl.value = '';
                unitEl.value = '';
            }
        });
    }

    const impP = document.getElementById('importPeopleBtn');
    if (impP) impP.addEventListener('click', () => {
        const txt = document.getElementById('importPeopleInput').value;
        if (txt) {
            txt.split('\n').forEach(l => {
                const [n, u] = l.split(/[,\t]/);
                if (n) addPerson(n, u);
            });
            document.getElementById('importPeopleInput').value = '';
        }
    });

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

    const exportBtn = document.getElementById('exportJsonBtn');
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

    const search = document.getElementById('searchInput');
    if (search) search.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase().trim();
        document.querySelectorAll('.person-card, .settings-item').forEach(el => {
            if (!el.classList.contains('settings-item') || el.closest('#settingsPeopleList') || el.closest('#settingsDutyList')) {
                el.classList.toggle('hidden', !el.innerText.toLowerCase().includes(q));
            }
        });
        document.querySelectorAll('.unit-person-row').forEach(r => {
            r.style.display = r.innerText.toLowerCase().includes(q) ? 'flex' : 'none';
        });
    });

    document.addEventListener('dragleave', (e) => {
        if (e.target.classList?.contains('drag-over')) e.target.classList.remove('drag-over');
    });

    // Session Selector Listener
    const sessionSelect = document.getElementById('sessionSelect');
    if (sessionSelect) {
        sessionSelect.addEventListener('change', () => {
            renderReport(); // Re-render report to update title
        });
    }
} // End setupEventListeners
        } // End else (valid config)
    } else {
    useFirebase = false;
    // Fallback or Alert?
    // Actually initSystem logic above covered this.
    // But wait, the nesting is messy.
    // The previous view showed initSystem definition is okay but might handle nesting wrong.
}
} // End initSystem

const API_BASE = '/api';

let authToken = localStorage.getItem('authToken');
let currentUser = null;

const STATUS_ORDER = ['待开样', '打样中', '待测试', '待确认', '修改中', '已封样', '已取消'];
const STATUS_COLORS = {
    '待开样': '#94a3b8',
    '打样中': '#3b82f6',
    '待测试': '#f59e0b',
    '待确认': '#8b5cf6',
    '修改中': '#ec4899',
    '已封样': '#10b981',
    '已取消': '#cbd5e1'
};

const STATUS_CLASS_MAP = {
    '待开样': 'pending-open',
    '打样中': 'sampling',
    '待测试': 'pending-test',
    '待确认': 'pending-confirm',
    '修改中': 'modifying',
    '已封样': 'sealed',
    '已取消': 'cancelled'
};

const RISK_FLAG_CLASS_MAP = {
    '已超期': 'overdue',
    '临近截止': 'near-deadline',
    '反复修改': 'repeated-modification',
    '多次测试未通过': 'multiple-test-failure'
};

function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateOnly(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function getInitials(name) {
    if (!name) return '?';
    return name.charAt(0).toUpperCase();
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    str = String(str);
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDieVersion(version) {
    if (!version) return '';
    const v = String(version).trim();
    if (v.toUpperCase().startsWith('V')) {
        return v;
    }
    return 'v' + v;
}

async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers
    };
    
    if (authToken && !endpoint.includes('/auth/login')) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        localStorage.removeItem('authToken');
        authToken = null;
        showLogin();
        throw new Error('未授权，请重新登录');
    }
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return response.json();
}

async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: formData
    });
    
    authToken = data.access_token;
    localStorage.setItem('authToken', authToken);
    
    currentUser = await apiRequest('/auth/me');
    showApp();
    showToast('登录成功', 'success');
}

function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showLogin();
    showToast('已退出登录', 'warning');
}

function showLogin() {
    document.getElementById('login-modal').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
}

function showApp() {
    document.getElementById('login-modal').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    
    if (currentUser) {
        document.getElementById('user-avatar').textContent = getInitials(currentUser.username);
        document.getElementById('user-name').textContent = currentUser.full_name || currentUser.username;
        document.getElementById('user-role').textContent = currentUser.role || '用户';
    }
    
    loadData();
}

function getFilterParams() {
    return {
        customer_name: document.getElementById('filter-customer').value || null,
        project_name: document.getElementById('filter-project').value || null,
        die_number: document.getElementById('filter-die').value || null,
        status: document.getElementById('filter-status').value || null,
        owner: document.getElementById('filter-owner').value || null,
        priority: document.getElementById('filter-priority').value || null,
        date_from: document.getElementById('filter-date-from').value || null,
        date_to: document.getElementById('filter-date-to').value || null,
        risk_type: document.getElementById('filter-risk-type').value || null,
        urge_status: document.getElementById('filter-urge-status').value || null
    };
}

function buildQueryString(params) {
    return Object.entries(params)
        .filter(([_, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
}

async function loadData() {
    const filters = getFilterParams();
    const queryParams = { ...filters };
    
    if (filters.urge_status === 'pending') {
        queryParams.has_pending_urge = true;
        delete queryParams.urge_status;
    } else if (filters.urge_status === 'resolved') {
        queryParams.has_pending_urge = false;
        delete queryParams.urge_status;
    }
    
    const queryString = buildQueryString(queryParams);
    
    try {
        const [samples, summary] = await Promise.all([
            apiRequest(`/kanban/samples?${queryString}`),
            apiRequest(`/kanban/summary?${queryString}`)
        ]);
        
        renderStats(summary);
        renderStatusBar(summary.status_summary);
        renderKanban(samples);
        renderSummaryTables(summary);
    } catch (error) {
        showToast(error.message, 'error');
        console.error('加载数据失败:', error);
    }
}

function renderStats(summary) {
    document.getElementById('stat-total').textContent = summary.total_samples;
    document.getElementById('stat-high-risk').textContent = summary.high_risk_count;
    document.getElementById('stat-overdue').textContent = summary.overdue_count;
    document.getElementById('stat-near-deadline').textContent = summary.near_deadline_count;
    document.getElementById('stat-pending-urge').textContent = summary.pending_urge_count;
    document.getElementById('stat-high-risk-unclosed').textContent = summary.high_risk_unclosed_urge_count;
}

function renderStatusBar(statusSummary) {
    const container = document.getElementById('status-bar-container');
    const total = statusSummary.reduce((sum, s) => sum + s.count, 0);
    
    container.innerHTML = STATUS_ORDER.map(status => {
        const item = statusSummary.find(s => s.status === status) || { count: 0, percentage: 0 };
        const percentage = total > 0 ? (item.count / total * 100).toFixed(1) : 0;
        const color = STATUS_COLORS[status];
        
        return `
            <div class="status-bar-item">
                <span class="status-bar-label">${status}</span>
                <div class="status-bar-track">
                    <div class="status-bar-fill" style="width: ${percentage}%; background: ${color};"></div>
                </div>
                <span class="status-bar-count">${item.count}</span>
            </div>
        `;
    }).join('');
}

function renderKanban(samples) {
    const board = document.getElementById('kanban-board');
    
    const columns = STATUS_ORDER.map(status => {
        const columnSamples = samples.filter(s => s.status === status);
        const statusClass = STATUS_CLASS_MAP[status];
        
        return `
            <div class="kanban-column">
                <div class="kanban-column-header">
                    <span class="kanban-column-title">
                        <span class="status-dot ${statusClass}"></span>
                        ${status}
                    </span>
                    <span class="kanban-column-count">${columnSamples.length}</span>
                </div>
                <div class="kanban-cards">
                    ${columnSamples.length === 0 ? `
                        <div class="empty-state" style="padding: 20px;">
                            <div class="empty-state-text">暂无任务</div>
                        </div>
                    ` : columnSamples.map(sample => renderKanbanCard(sample)).join('')}
                </div>
            </div>
        `;
    }).join('');
    
    board.innerHTML = columns;
    
    document.querySelectorAll('.kanban-card').forEach(card => {
        card.addEventListener('click', () => {
            const sampleId = card.dataset.sampleId;
            showSampleDetail(sampleId);
        });
    });
}

function renderKanbanCard(sample) {
    const riskFlags = sample.risk_flags.filter(f => f !== '正常');
    const hasOverdue = riskFlags.includes('已超期');
    const hasNearDeadline = riskFlags.includes('临近截止');
    const hasPendingUrge = sample.pending_urge_count > 0;
    
    let cardClass = 'normal';
    if (hasOverdue) cardClass = 'overdue';
    else if (hasNearDeadline) cardClass = 'near-deadline';
    else if (hasPendingUrge) cardClass = 'pending-urge';
    else if (sample.priority === '紧急') cardClass = 'urgent-priority';
    else if (sample.priority === '高') cardClass = 'high-priority';
    
    let deadlineClass = '';
    let deadlineText = formatDateOnly(sample.deadline);
    if (sample.days_remaining !== null) {
        if (sample.days_remaining < 0) {
            deadlineClass = 'deadline-overdue';
            deadlineText = `已超期 ${Math.abs(sample.days_remaining)} 天`;
        } else if (sample.days_remaining <= 3) {
            deadlineClass = 'deadline-near';
            deadlineText = `剩余 ${sample.days_remaining} 天`;
        }
    }
    
    return `
        <div class="kanban-card ${cardClass}" data-sample-id="${escapeHtml(sample.id)}">
            <div class="kanban-card-header">
                <span class="kanban-card-project" title="${escapeHtml(sample.project_name)}">${escapeHtml(sample.project_name)}</span>
                <span class="kanban-card-priority priority-${escapeHtml(sample.priority)}">${escapeHtml(sample.priority)}</span>
            </div>
            <div class="kanban-card-meta">
                <div class="kanban-card-meta-row">
                    <svg viewBox="0 0 16 16" fill="none">
                        <path d="M8 14s-6-4.5-6-9a6 6 0 0 1 12 0c0 4.5-6 9-6 9z" stroke="currentColor" stroke-width="1.5"/>
                        <circle cx="8" cy="5" r="2" stroke="currentColor" stroke-width="1.5"/>
                    </svg>
                    <span class="kanban-card-customer">${escapeHtml(sample.customer_name)}</span>
                </div>
                <div class="kanban-card-meta-row">
                    <svg viewBox="0 0 16 16" fill="none">
                        <rect x="2" y="3" width="12" height="10" rx="1" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M2 7h12M5 3v10" stroke="currentColor" stroke-width="1.5"/>
                    </svg>
                    <span class="kanban-card-die">${escapeHtml(sample.die_number)} ${formatDieVersion(sample.die_version)}</span>
                </div>
                <div class="kanban-card-meta-row">
                    <svg viewBox="0 0 16 16" fill="none">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M8 4v4l3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span class="kanban-card-owner">
                        <span class="owner-avatar-small">${escapeHtml(getInitials(sample.owner))}</span>
                        ${escapeHtml(sample.owner)}
                    </span>
                </div>
                <div class="kanban-card-meta-row">
                    <svg viewBox="0 0 16 16" fill="none">
                        <rect x="3" y="4" width="10" height="10" rx="1" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M16 2v4h-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        <path d="M3 9h10" stroke="currentColor" stroke-width="1.5"/>
                    </svg>
                    <span class="kanban-card-deadline ${deadlineClass}">${escapeHtml(deadlineText)}</span>
                </div>
            </div>
            ${riskFlags.length > 0 || hasPendingUrge ? `
                <div class="kanban-card-risk-flags">
                    ${riskFlags.map(flag => `
                        <span class="risk-flag ${RISK_FLAG_CLASS_MAP[flag] || ''}">${escapeHtml(flag)}</span>
                    `).join('')}
                    ${hasPendingUrge ? `
                        <span class="risk-flag urge-pending">
                            <span class="urge-count-badge">${sample.pending_urge_count}</span>
                            待处理催办
                        </span>
                    ` : ''}
                </div>
            ` : ''}
            <div class="kanban-card-stats">
                <span class="kanban-card-stat">
                    <span class="kanban-card-stat-value">${escapeHtml(sample.modification_count)}</span>
                    修改
                </span>
                <span class="kanban-card-stat">
                    <span class="kanban-card-stat-value">${escapeHtml(sample.test_failure_count)}</span>
                    测试失败
                </span>
                <span class="kanban-card-stat">
                    <span class="kanban-card-stat-value">第${escapeHtml(sample.test_round)}轮</span>
                    测试
                </span>
            </div>
        </div>
    `;
}

function renderSummaryTables(summary) {
    renderCustomerTable(summary.customer_summary);
    renderSpecTable(summary.board_spec_summary);
    renderOwnerTable(summary.owner_summary);
}

function renderCustomerTable(data) {
    const tbody = document.getElementById('customer-table-body');
    tbody.innerHTML = data.map(item => `
        <tr>
            <td><strong>${escapeHtml(item.customer_name)}</strong></td>
            <td>${escapeHtml(item.total)}</td>
            <td>
                <div class="status-badges">
                    ${Object.entries(item.status_breakdown).map(([status, count]) => `
                        <span class="status-badge ${escapeHtml(status)}">${escapeHtml(status)} ${escapeHtml(count)}</span>
                    `).join('')}
                </div>
            </td>
            <td class="overdue-count">${escapeHtml(item.overdue_count > 0 ? item.overdue_count : '-')}</td>
        </tr>
    `).join('');
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 40px; color: var(--text-muted);">暂无数据</td>
            </tr>
        `;
    }
}

function renderSpecTable(data) {
    const tbody = document.getElementById('spec-table-body');
    tbody.innerHTML = data.map(item => `
        <tr>
            <td><strong>${escapeHtml(item.board_spec)}</strong></td>
            <td>${escapeHtml(item.total)}</td>
            <td>${escapeHtml(item.cracking_count > 0 ? item.cracking_count : '-')}</td>
            <td>${escapeHtml(item.reject_count > 0 ? item.reject_count : '-')}</td>
            <td>
                <span class="risk-level ${escapeHtml(item.risk_level)}">
                    ${item.risk_level === 'high' ? '高风险' : 
                      item.risk_level === 'medium' ? '中风险' : 
                      item.risk_level === 'low' ? '低风险' : '安全'}
                </span>
            </td>
        </tr>
    `).join('');
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: var(--text-muted);">暂无数据</td>
            </tr>
        `;
    }
}

function renderOwnerTable(data) {
    const tbody = document.getElementById('owner-table-body');
    tbody.innerHTML = data.map(item => `
        <tr>
            <td>
                <span style="display: flex; align-items: center; gap: 8px;">
                    <span class="owner-avatar-small">${escapeHtml(getInitials(item.owner))}</span>
                    <strong>${escapeHtml(item.owner)}</strong>
                </span>
            </td>
            <td>${escapeHtml(item.total)}</td>
            <td>
                <div class="status-badges">
                    ${Object.entries(item.status_breakdown).map(([status, count]) => `
                        <span class="status-badge ${escapeHtml(status)}">${escapeHtml(status)} ${escapeHtml(count)}</span>
                    `).join('')}
                </div>
            </td>
            <td class="overdue-count">${escapeHtml(item.overdue_count > 0 ? item.overdue_count : '-')}</td>
        </tr>
    `).join('');
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 40px; color: var(--text-muted);">暂无数据</td>
            </tr>
        `;
    }
}

async function showSampleDetail(sampleId) {
    try {
        const detail = await apiRequest(`/samples/${sampleId}`);
        renderSampleDetail(detail);
        document.getElementById('detail-modal').classList.remove('hidden');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function renderSampleDetail(detail) {
    const titleEl = document.getElementById('detail-title');
    titleEl.textContent = `${detail.project_name} - ${detail.die_number}`;
    
    const riskFlags = detail.risk_flags ? detail.risk_flags.filter(f => f !== '正常') : [];
    const urgeRecords = detail.urge_records || [];
    const pendingUrgeCount = urgeRecords.filter(u => u.status === '待处理' || u.status === '处理中').length;
    
    const html = `
        <div class="detail-section">
            <div class="urge-section-header">
                <h3 class="detail-section-title">基本信息</h3>
                <button class="btn-urge" id="btn-create-urge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <path d="M12 9v4M12 17h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                    </svg>
                    发起催办
                </button>
            </div>
            <div class="detail-info-grid">
                <div class="detail-info-item">
                    <span class="detail-info-label">项目名称</span>
                    <span class="detail-info-value">${escapeHtml(detail.project_name)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">客户名称</span>
                    <span class="detail-info-value">${escapeHtml(detail.customer_name)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">纸板规格</span>
                    <span class="detail-info-value">${escapeHtml(detail.board_spec)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">刀模编号</span>
                    <span class="detail-info-value">${escapeHtml(detail.die_number)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">刀模版本</span>
                    <span class="detail-info-value">${formatDieVersion(detail.die_version)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">当前状态</span>
                    <span class="detail-info-value status ${escapeHtml(detail.status)}">${escapeHtml(detail.status)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">责任人</span>
                    <span class="detail-info-value">${escapeHtml(detail.owner)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">优先级</span>
                    <span class="detail-info-value">${escapeHtml(detail.priority)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">截止日期</span>
                    <span class="detail-info-value">${escapeHtml(formatDateOnly(detail.deadline))}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">创建人</span>
                    <span class="detail-info-value">${escapeHtml(detail.created_by)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">创建时间</span>
                    <span class="detail-info-value">${escapeHtml(formatDate(detail.created_at))}</span>
                </div>
                <div class="detail-info-item">
                    <span class="detail-info-label">更新时间</span>
                    <span class="detail-info-value">${escapeHtml(formatDate(detail.updated_at))}</span>
                </div>
            </div>
            ${detail.notes ? `
                <div class="detail-info-item" style="margin-top: 16px;">
                    <span class="detail-info-label">备注</span>
                    <span class="detail-info-value">${escapeHtml(detail.notes)}</span>
                </div>
            ` : ''}
            ${riskFlags.length > 0 || pendingUrgeCount > 0 ? `
                <div class="detail-info-item" style="margin-top: 16px;">
                    <span class="detail-info-label">风险标识</span>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        ${riskFlags.map(flag => `
                            <span class="risk-flag ${RISK_FLAG_CLASS_MAP[flag] || ''}">${escapeHtml(flag)}</span>
                        `).join('')}
                        ${pendingUrgeCount > 0 ? `
                            <span class="risk-flag urge-pending">
                                <span class="urge-count-badge">${pendingUrgeCount}</span>
                                待处理催办
                            </span>
                        ` : ''}
                    </div>
                </div>
            ` : ''}
        </div>
        
        <div class="detail-section">
            <div class="urge-section-header">
                <h3 class="urge-section-title">催办记录</h3>
                <span class="urge-badge ${pendingUrgeCount > 0 ? 'pending' : 'resolved'}">
                    ${pendingUrgeCount > 0 ? `${pendingUrgeCount} 条待处理` : '全部已处理'}
                </span>
            </div>
            ${urgeRecords.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-text">暂无催办记录</div>
                </div>
            ` : urgeRecords.map(urge => renderUrgeRecordCard(urge)).join('')}
        </div>
        
        <div class="detail-section">
            <h3 class="detail-section-title">流转时间线</h3>
            <div class="timeline">
                ${detail.timeline.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-text">暂无时间线记录</div>
                    </div>
                ` : detail.timeline.map(log => renderTimelineItem(log)).join('')}
            </div>
        </div>
        
        <div class="detail-section">
            <h3 class="detail-section-title">测试记录</h3>
            ${detail.test_records.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-text">暂无测试记录</div>
                </div>
            ` : detail.test_records.slice().reverse().map(record => `
                <div class="record-card test">
                    <div class="record-header">
                        <span class="record-round">
                            <span class="record-round-badge">${escapeHtml(record.round)}</span>
                            第 ${escapeHtml(record.round)} 轮测试
                        </span>
                        <span class="record-date">${escapeHtml(formatDate(record.test_date))}</span>
                    </div>
                    <div class="record-grid">
                        <div class="record-item">
                            <span class="record-label">测试人员</span>
                            <span class="record-value">${escapeHtml(record.tester || '-')}</span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">测试结果</span>
                            <span class="record-value ${record.is_passed ? 'passed' : 'failed'}">
                                ${record.is_passed ? '✓ 通过' : '✗ 未通过'}
                            </span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">折合测试</span>
                            <span class="record-value">${escapeHtml(record.folding_result || '-')}</span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">压痕测试</span>
                            <span class="record-value">${escapeHtml(record.indentation_result || '-')}</span>
                        </div>
                        ${record.cracking_description ? `
                            <div class="record-item" style="grid-column: 1 / -1;">
                                <span class="record-label">开裂描述</span>
                                <span class="record-value" style="color: var(--danger);">${escapeHtml(record.cracking_description)}</span>
                            </div>
                        ` : ''}
                        ${record.notes ? `
                            <div class="record-item" style="grid-column: 1 / -1;">
                                <span class="record-label">备注</span>
                                <span class="record-value">${escapeHtml(record.notes)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="detail-section">
            <h3 class="detail-section-title">修改记录</h3>
            ${detail.modification_records.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-text">暂无修改记录</div>
                </div>
            ` : detail.modification_records.slice().reverse().map(record => `
                <div class="record-card modify">
                    <div class="record-header">
                        <span class="record-round">
                            <span class="record-round-badge">${escapeHtml(record.round)}</span>
                            第 ${escapeHtml(record.round)} 轮修改
                        </span>
                        <span class="record-date">${escapeHtml(formatDate(record.modify_date))}</span>
                    </div>
                    <div class="record-grid">
                        <div class="record-item">
                            <span class="record-label">修改人员</span>
                            <span class="record-value">${escapeHtml(record.modifier)}</span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">修改动作</span>
                            <span class="record-value">${escapeHtml(record.modification_action)}</span>
                        </div>
                        ${record.reason ? `
                            <div class="record-item" style="grid-column: 1 / -1;">
                                <span class="record-label">修改原因</span>
                                <span class="record-value">${escapeHtml(record.reason)}</span>
                            </div>
                        ` : ''}
                        ${record.notes ? `
                            <div class="record-item" style="grid-column: 1 / -1;">
                                <span class="record-label">备注</span>
                                <span class="record-value">${escapeHtml(record.notes)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="detail-section">
            <h3 class="detail-section-title">退回记录</h3>
            ${detail.reject_records.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-text">暂无退回记录</div>
                </div>
            ` : detail.reject_records.slice().reverse().map(record => `
                <div class="record-card reject">
                    <div class="record-header">
                        <span class="record-round">
                            <span class="record-round-badge">${escapeHtml(record.round)}</span>
                            第 ${escapeHtml(record.round)} 次退回
                        </span>
                        <span class="record-date">${escapeHtml(formatDate(record.reject_date))}</span>
                    </div>
                    <div class="record-grid">
                        <div class="record-item">
                            <span class="record-label">退回人员</span>
                            <span class="record-value">${escapeHtml(record.rejecter)}</span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">退回原因</span>
                            <span class="record-value" style="color: var(--danger);">${escapeHtml(record.reason)}</span>
                        </div>
                        ${record.description ? `
                            <div class="record-item" style="grid-column: 1 / -1;">
                                <span class="record-label">详细描述</span>
                                <span class="record-value">${escapeHtml(record.description)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
        
        ${detail.seal_record ? `
            <div class="detail-section">
                <h3 class="detail-section-title">封样信息</h3>
                <div class="seal-info">
                    <div class="seal-info-grid">
                        <div class="record-item">
                            <span class="record-label">封样人员</span>
                            <span class="record-value">${escapeHtml(detail.seal_record.sealer)}</span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">封样日期</span>
                            <span class="record-value">${escapeHtml(formatDate(detail.seal_record.seal_date))}</span>
                        </div>
                        <div class="record-item">
                            <span class="record-label">封样版本</span>
                            <span class="record-value">${formatDieVersion(detail.seal_record.version)}</span>
                        </div>
                        ${detail.seal_record.notes ? `
                            <div class="record-item" style="grid-column: 1 / -1;">
                                <span class="record-label">备注</span>
                                <span class="record-value">${escapeHtml(detail.seal_record.notes)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        ` : ''}
    `;
    
    document.getElementById('detail-body').innerHTML = html;
    
    const createUrgeBtn = document.getElementById('btn-create-urge');
    if (createUrgeBtn) {
        createUrgeBtn.addEventListener('click', () => openUrgeModal(detail.id));
    }
    
    document.querySelectorAll('.btn-handle-urge').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const urgeId = e.target.dataset.urgeId;
            openUrgeHandleModal(urgeId);
        });
    });
}

function renderUrgeRecordCard(urge) {
    const statusClass = {
        '待处理': 'pending',
        '处理中': 'processing',
        '已处理': 'resolved',
        '已关闭': 'closed'
    }[urge.status] || 'pending';
    
    const isPending = urge.status === '待处理' || urge.status === '处理中';
    
    return `
        <div class="urge-record-card ${statusClass}">
            <div class="urge-record-header">
                <div class="urge-record-title">
                    <span class="urge-badge ${statusClass}">${escapeHtml(urge.status)}</span>
                    <span>${escapeHtml(urge.urge_type)}</span>
                </div>
                <span class="record-date">${escapeHtml(formatDate(urge.urge_time))}</span>
            </div>
            <div class="urge-record-meta">
                <div class="urge-record-item">
                    <span class="urge-record-label">催办原因</span>
                    <span class="urge-record-value">${escapeHtml(urge.urge_reason)}</span>
                </div>
                <div class="urge-record-item">
                    <span class="urge-record-label">催办人</span>
                    <span class="urge-record-value">${escapeHtml(urge.urge_by)}</span>
                </div>
                <div class="urge-record-item">
                    <span class="urge-record-label">优先级</span>
                    <span class="urge-record-value">${escapeHtml(urge.priority)}</span>
                </div>
                ${urge.deadline ? `
                    <div class="urge-record-item">
                        <span class="urge-record-label">要求处理时间</span>
                        <span class="urge-record-value">${escapeHtml(formatDate(urge.deadline))}</span>
                    </div>
                ` : ''}
            </div>
            ${urge.description ? `
                <div class="urge-record-description">
                    <strong>催办说明：</strong>${escapeHtml(urge.description)}
                </div>
            ` : ''}
            ${urge.handle_result ? `
                <div class="urge-record-handle">
                    <div class="urge-record-handle-title">
                        处理结果 · ${escapeHtml(urge.handler || '-')} · ${escapeHtml(formatDate(urge.handle_time))}
                    </div>
                    <div class="urge-record-handle-result">${escapeHtml(urge.handle_result)}</div>
                </div>
            ` : ''}
            ${isPending ? `
                <div class="urge-record-actions">
                    <button class="btn-urge btn-urge-sm btn-handle-urge" data-urge-id="${escapeHtml(urge.id)}">
                        处理催办
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

function renderTimelineItem(log) {
    let itemClass = '';
    if (log.operation_type === '测试提交') itemClass = 'test';
    else if (log.operation_type === '修改') itemClass = 'modify';
    else if (log.operation_type === '退回') itemClass = 'reject';
    else if (log.operation_type === '封样确认') itemClass = 'confirm';
    else if (log.operation_type === '开样') itemClass = 'open';
    else if (log.operation_type === '发起催办') itemClass = 'urge';
    else if (log.operation_type === '处理催办') itemClass = 'urge-handle';
    
    let contentHtml = '';
    if (log.business_result) {
        const result = log.business_result;
        const fields = [];
        
        if (result.test_round !== undefined) fields.push(['测试轮次', `第 ${result.test_round} 轮`]);
        if (result.is_passed !== undefined) fields.push(['测试结果', result.is_passed ? '通过' : '未通过']);
        if (result.folding_result) fields.push(['折合测试', result.folding_result]);
        if (result.indentation_result) fields.push(['压痕测试', result.indentation_result]);
        if (result.cracking_description) fields.push(['开裂描述', result.cracking_description]);
        if (result.modification_action) fields.push(['修改动作', result.modification_action]);
        if (result.reason) fields.push(['原因', result.reason]);
        if (result.reject_reason) fields.push(['退回原因', result.reject_reason]);
        if (result.seal_version) fields.push(['封样版本', formatDieVersion(result.seal_version)]);
        if (result.from_status) fields.push(['状态变更', `${result.from_status} → ${result.to_status}`]);
        if (result.owner) fields.push(['责任人', result.owner]);
        if (result.priority) fields.push(['优先级', result.priority]);
        if (result.die_version) fields.push(['刀模版本', formatDieVersion(result.die_version)]);
        if (result.opener) fields.push(['开样人员', result.opener]);
        if (result.urge_type) fields.push(['催办类型', result.urge_type]);
        if (result.urge_reason) fields.push(['催办原因', result.urge_reason]);
        if (result.urge_priority) fields.push(['催办优先级', result.urge_priority]);
        if (result.urge_status) fields.push(['催办状态', result.urge_status]);
        if (result.handle_result) fields.push(['处理结果', result.handle_result]);
        if (result.handler) fields.push(['处理人', result.handler]);
        
        if (fields.length > 0) {
            contentHtml = `
                <div class="timeline-content">
                    ${fields.map(([label, value]) => `
                        <div class="timeline-content-row">
                            <span class="timeline-content-label">${escapeHtml(label)}</span>
                            <span class="timeline-content-value">${escapeHtml(value)}</span>
                        </div>
                    `).join('')}
                    ${log.notes ? `
                        <div class="timeline-content-row">
                            <span class="timeline-content-label">备注</span>
                            <span class="timeline-content-value">${escapeHtml(log.notes)}</span>
                        </div>
                    ` : ''}
                </div>
            `;
        } else if (log.notes) {
            contentHtml = `
                <div class="timeline-content">
                    <div class="timeline-content-row">
                        <span class="timeline-content-label">备注</span>
                        <span class="timeline-content-value">${escapeHtml(log.notes)}</span>
                    </div>
                </div>
            `;
        }
    } else if (log.notes) {
        contentHtml = `
            <div class="timeline-content">
                <div class="timeline-content-row">
                    <span class="timeline-content-label">备注</span>
                    <span class="timeline-content-value">${escapeHtml(log.notes)}</span>
                </div>
            </div>
        `;
    }
    
    return `
        <div class="timeline-item ${itemClass}">
            <div class="timeline-header">
                <span class="timeline-type ${escapeHtml(log.operation_type)}">${escapeHtml(log.operation_type)}</span>
                <span class="timeline-operator">${escapeHtml(log.operator)}</span>
                <span class="timeline-time">${escapeHtml(formatDate(log.operation_time))}</span>
            </div>
            ${contentHtml}
        </div>
    `;
}

function closeDetailModal() {
    document.getElementById('detail-modal').classList.add('hidden');
}

let currentUrgeSampleId = null;
let currentHandleUrgeId = null;

function openUrgeModal(sampleId) {
    currentUrgeSampleId = sampleId;
    document.getElementById('urge-form').reset();
    document.getElementById('urge-sample-id').value = sampleId;
    document.getElementById('urge-modal').classList.remove('hidden');
}

function closeUrgeModal() {
    document.getElementById('urge-modal').classList.add('hidden');
    currentUrgeSampleId = null;
}

async function submitUrge(e) {
    e.preventDefault();
    
    const data = {
        sample_id: currentUrgeSampleId,
        urge_type: document.getElementById('urge-type').value,
        urge_reason: document.getElementById('urge-reason').value,
        priority: document.getElementById('urge-priority').value,
        description: document.getElementById('urge-description').value,
        deadline: document.getElementById('urge-deadline').value || null
    };
    
    try {
        await apiRequest('/urges', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('催办创建成功', 'success');
        closeUrgeModal();
        loadData();
        
        if (currentSampleDetail && currentSampleDetail.id === currentUrgeSampleId) {
            await loadSampleDetail(currentUrgeSampleId);
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function openUrgeHandleModal(urgeId) {
    currentHandleUrgeId = urgeId;
    document.getElementById('urge-handle-form').reset();
    document.getElementById('urge-handle-id').value = urgeId;
    document.getElementById('urge-handle-modal').classList.remove('hidden');
}

function closeUrgeHandleModal() {
    document.getElementById('urge-handle-modal').classList.add('hidden');
    currentHandleUrgeId = null;
}

async function submitUrgeHandle(e) {
    e.preventDefault();
    
    const data = {
        handle_result: document.getElementById('urge-handle-result').value,
        status: document.getElementById('urge-handle-status').value
    };
    
    try {
        const result = await apiRequest(`/urges/${currentHandleUrgeId}/handle`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('催办处理成功', 'success');
        closeUrgeHandleModal();
        loadData();
        
        if (currentSampleDetail && result.sample_id && currentSampleDetail.id === result.sample_id) {
            await loadSampleDetail(result.sample_id);
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function setupEventListeners() {
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            await login(username, password);
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
    
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    document.getElementById('btn-apply-filter').addEventListener('click', loadData);
    
    document.getElementById('btn-reset-filter').addEventListener('click', () => {
        document.getElementById('filter-customer').value = '';
        document.getElementById('filter-project').value = '';
        document.getElementById('filter-die').value = '';
        document.getElementById('filter-status').value = '';
        document.getElementById('filter-owner').value = '';
        document.getElementById('filter-priority').value = '';
        document.getElementById('filter-date-from').value = '';
        document.getElementById('filter-date-to').value = '';
        document.getElementById('filter-risk-type').value = '';
        document.getElementById('filter-urge-status').value = '';
        loadData();
    });
    
    document.getElementById('btn-refresh').addEventListener('click', () => {
        loadData();
        showToast('数据已刷新', 'success');
    });
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`tab-${tab}`).classList.add('active');
        });
    });
    
    document.getElementById('detail-close').addEventListener('click', closeDetailModal);
    
    document.getElementById('detail-modal').addEventListener('click', (e) => {
        if (e.target.id === 'detail-modal') {
            closeDetailModal();
        }
    });
    
    document.getElementById('urge-form').addEventListener('submit', submitUrge);
    
    document.getElementById('urge-close').addEventListener('click', closeUrgeModal);
    document.getElementById('urge-cancel').addEventListener('click', closeUrgeModal);
    
    document.getElementById('urge-modal').addEventListener('click', (e) => {
        if (e.target.id === 'urge-modal') {
            closeUrgeModal();
        }
    });
    
    document.getElementById('urge-handle-form').addEventListener('submit', submitUrgeHandle);
    
    document.getElementById('urge-handle-close').addEventListener('click', closeUrgeHandleModal);
    document.getElementById('urge-handle-cancel').addEventListener('click', closeUrgeHandleModal);
    
    document.getElementById('urge-handle-modal').addEventListener('click', (e) => {
        if (e.target.id === 'urge-handle-modal') {
            closeUrgeHandleModal();
        }
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeDetailModal();
            closeUrgeModal();
            closeUrgeHandleModal();
        }
    });
}

async function init() {
    setupEventListeners();
    
    if (authToken) {
        try {
            currentUser = await apiRequest('/auth/me');
            showApp();
        } catch (error) {
            localStorage.removeItem('authToken');
            authToken = null;
            showLogin();
        }
    } else {
        showLogin();
    }
}

document.addEventListener('DOMContentLoaded', init);

/**
 * 看板邮件系统模块
 * 集成邮件功能到看板2.4系统
 */

class KanbanEmail {
    constructor() {
        this.apiBase = 'http://47.93.184.128:8089';
        this.contacts = [];
        this.emails = [];
        this.init();
    }
    
    init() {
        // 检查是否在邮件页面
        if (document.getElementById('email-panel')) {
            this.loadData();
            this.bindEvents();
        }
    }
    
    async loadData() {
        try {
            // 加载邮件状态
            const statusRes = await fetch(`${this.apiBase}/api/email/status`);
            const status = await statusRes.json();
            this.updateStatus(status.data);
            
            // 加载联系人
            const contactsRes = await fetch(`${this.apiBase}/api/contacts`);
            const contactsData = await contactsRes.json();
            if (contactsData.success) {
                this.contacts = contactsData.data;
                this.renderContacts();
            }
            
            // 加载收件箱
            await this.loadInbox();
        } catch (error) {
            console.error('加载邮件数据失败:', error);
            this.showError('无法连接到邮件服务器');
        }
    }
    
    updateStatus(status) {
        const statusEl = document.getElementById('email-status');
        if (statusEl) {
            const isConfigured = status.configured;
            statusEl.innerHTML = `
                <div class="alert ${isConfigured ? 'alert-success' : 'alert-warning'}">
                    <i class="fas ${isConfigured ? 'fa-check-circle' : 'fa-exclamation-triangle'}"></i>
                    ${isConfigured ? '邮件系统已配置' : '邮件系统未配置'}
                    <br><small>账户: ${status.account || '未设置'}</small>
                    <br><small>联系人: ${status.contacts_count || 0}人</small>
                </div>
            `;
        }
    }
    
    renderContacts() {
        const container = document.getElementById('email-contacts-list');
        if (!container) return;
        
        if (this.contacts.length === 0) {
            container.innerHTML = '<div class="text-muted p-3">暂无联系人</div>';
            return;
        }
        
        container.innerHTML = this.contacts.map(c => `
            <div class="email-contact-item" data-email="${c.email}">
                <div class="d-flex justify-content-between align-items-center p-2 border-bottom">
                    <div>
                        <strong>${c.name}</strong>
                        <div class="small text-muted">${c.email}</div>
                        ${c.company ? `<div class="small text-info">${c.company}</div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="kanbanEmail.compose('${c.email}')">
                        <i class="fas fa-envelope"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    async loadInbox() {
        try {
            const res = await fetch(`${this.apiBase}/api/email/inbox?limit=10`);
            const data = await res.json();
            if (data.success) {
                this.emails = data.data;
                this.renderInbox();
            }
        } catch (error) {
            console.error('加载收件箱失败:', error);
        }
    }
    
    renderInbox() {
        const container = document.getElementById('email-inbox-list');
        if (!container) return;
        
        if (this.emails.length === 0 || (this.emails.length === 1 && this.emails[0].error)) {
            container.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>收件箱为空</p>
                    <button class="btn btn-primary btn-sm" onclick="kanbanEmail.syncEmail()">
                        <i class="fas fa-sync"></i> 同步邮件
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.emails.map((e, i) => `
            <div class="email-item ${e.is_read ? '' : 'unread'}" data-id="${e.id}">
                <div class="p-2 border-bottom cursor-pointer" onclick="kanbanEmail.viewEmail('${e.id}')">
                    <div class="d-flex justify-content-between">
                        <strong class="${e.is_read ? 'text-muted' : ''}">${e.from || '未知'}</strong>
                        <small class="text-muted">${e.date || ''}</small>
                    </div>
                    <div class="text-truncate ${e.is_read ? '' : 'font-weight-bold'}">${e.subject || '(无主题)'}</div>
                    <small class="text-muted text-truncate d-block">${e.body_preview || ''}</small>
                </div>
            </div>
        `).join('');
    }
    
    compose(to = '') {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.cssText = 'display: block; background: rgba(0,0,0,0.5); z-index: 9999;';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-envelope"></i> 写邮件</h5>
                        <button type="button" class="close" onclick="this.closest('.modal').remove()">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form id="compose-form">
                            <div class="form-group">
                                <label>收件人</label>
                                <input type="email" class="form-control" id="compose-to" value="${to}" required>
                            </div>
                            <div class="form-group">
                                <label>抄送</label>
                                <input type="email" class="form-control" id="compose-cc">
                            </div>
                            <div class="form-group">
                                <label>主题</label>
                                <input type="text" class="form-control" id="compose-subject" required>
                            </div>
                            <div class="form-group">
                                <label>正文</label>
                                <textarea class="form-control" id="compose-body" rows="8" required></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">取消</button>
                        <button type="button" class="btn btn-primary" onclick="kanbanEmail.sendEmail()">
                            <i class="fas fa-paper-plane"></i> 发送
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    async sendEmail() {
        const to = document.getElementById('compose-to').value;
        const cc = document.getElementById('compose-cc').value;
        const subject = document.getElementById('compose-subject').value;
        const body = document.getElementById('compose-body').value;
        
        if (!to || !subject || !body) {
            alert('请填写完整信息');
            return;
        }
        
        try {
            const res = await fetch(`${this.apiBase}/api/email/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ to, cc, subject, body })
            });
            
            const data = await res.json();
            if (data.success) {
                alert('邮件发送成功！');
                document.querySelector('.modal.show').remove();
            } else {
                alert('发送失败: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            alert('发送失败: ' + error.message);
        }
    }
    
    addContact() {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.cssText = 'display: block; background: rgba(0,0,0,0.5); z-index: 9999;';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-user-plus"></i> 添加联系人</h5>
                        <button type="button" class="close" onclick="this.closest('.modal').remove()">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form id="contact-form">
                            <div class="form-group">
                                <label>姓名 *</label>
                                <input type="text" class="form-control" id="contact-name" required>
                            </div>
                            <div class="form-group">
                                <label>邮箱 *</label>
                                <input type="email" class="form-control" id="contact-email" required>
                            </div>
                            <div class="form-group">
                                <label>电话</label>
                                <input type="text" class="form-control" id="contact-phone">
                            </div>
                            <div class="form-group">
                                <label>公司</label>
                                <input type="text" class="form-control" id="contact-company">
                            </div>
                            <div class="form-group">
                                <label>标签</label>
                                <input type="text" class="form-control" id="contact-tags" placeholder="用逗号分隔,如: 客户,重要">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">取消</button>
                        <button type="button" class="btn btn-primary" onclick="kanbanEmail.saveContact()">保存</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    async saveContact() {
        const name = document.getElementById('contact-name').value;
        const email = document.getElementById('contact-email').value;
        const phone = document.getElementById('contact-phone').value;
        const company = document.getElementById('contact-company').value;
        const tags = document.getElementById('contact-tags').value.split(',').map(t => t.trim()).filter(t => t);
        
        if (!name || !email) {
            alert('请填写姓名和邮箱');
            return;
        }
        
        try {
            const res = await fetch(`${this.apiBase}/api/contacts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, phone, company, tags })
            });
            
            const data = await res.json();
            if (data.success) {
                alert('联系人添加成功！');
                document.querySelector('.modal.show').remove();
                this.loadData(); // 刷新列表
            } else {
                alert('添加失败: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            alert('添加失败: ' + error.message);
        }
    }
    
    async syncEmail() {
        try {
            const res = await fetch(`${this.apiBase}/api/email/sync`, {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                alert('邮件同步成功！');
                this.loadInbox();
            } else {
                alert('同步失败: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            alert('同步失败: ' + error.message);
        }
    }
    
    viewEmail(id) {
        const email = this.emails.find(e => e.id === id);
        if (!email) return;
        
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.cssText = 'display: block; background: rgba(0,0,0,0.5); z-index: 9999;';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${email.subject || '(无主题)'}</h5>
                        <button type="button" class="close" onclick="this.closest('.modal').remove()">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <strong>发件人:</strong> ${email.from || '未知'}<br>
                            <strong>时间:</strong> ${email.date || ''}
                        </div>
                        <hr>
                        <div style="white-space: pre-wrap;">${email.body_preview || ''}</div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">关闭</button>
                        <button type="button" class="btn btn-primary" onclick="kanbanEmail.compose('${email.from}'); this.closest('.modal').remove();">
                            <i class="fas fa-reply"></i> 回复
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    showError(msg) {
        const container = document.getElementById('email-panel');
        if (container) {
            container.innerHTML = `<div class="alert alert-danger">${msg}</div>`;
        }
    }
    
    bindEvents() {
        // 搜索联系人
        const searchInput = document.getElementById('contact-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                const items = document.querySelectorAll('.email-contact-item');
                items.forEach(item => {
                    const text = item.textContent.toLowerCase();
                    item.style.display = text.includes(query) ? '' : 'none';
                });
            });
        }
    }
}

// 初始化
window.kanbanEmail = new KanbanEmail();

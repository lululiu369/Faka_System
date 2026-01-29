/**
 * Project Nexus - 前端交互
 */

// TOTP 相关函数
function base32Decode(base32) {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    let bits = '';
    let result = [];

    // 移除空格和转大写
    base32 = base32.replace(/\s/g, '').toUpperCase();

    for (let char of base32) {
        if (char === '=') continue;
        const val = alphabet.indexOf(char);
        if (val === -1) continue;
        bits += val.toString(2).padStart(5, '0');
    }

    for (let i = 0; i + 8 <= bits.length; i += 8) {
        result.push(parseInt(bits.substr(i, 8), 2));
    }

    return new Uint8Array(result);
}

async function generateTOTP(secret) {
    try {
        // 解码 Base32 密钥
        const key = base32Decode(secret);

        // 获取当前时间步长 (30秒)
        const epoch = Math.floor(Date.now() / 1000);
        const timeStep = Math.floor(epoch / 30);

        // 将时间步长转为8字节大端序
        const timeBytes = new Uint8Array(8);
        let tmp = timeStep;
        for (let i = 7; i >= 0; i--) {
            timeBytes[i] = tmp & 0xff;
            tmp = Math.floor(tmp / 256);
        }

        // 使用 HMAC-SHA1
        const cryptoKey = await crypto.subtle.importKey(
            'raw', key, { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']
        );
        const signature = await crypto.subtle.sign('HMAC', cryptoKey, timeBytes);
        const hash = new Uint8Array(signature);

        // 动态截断
        const offset = hash[hash.length - 1] & 0x0f;
        const code = (
            ((hash[offset] & 0x7f) << 24) |
            ((hash[offset + 1] & 0xff) << 16) |
            ((hash[offset + 2] & 0xff) << 8) |
            (hash[offset + 3] & 0xff)
        ) % 1000000;

        return code.toString().padStart(6, '0');
    } catch (e) {
        console.error('TOTP generation error:', e);
        return null;
    }
}

function getRemainingSeconds() {
    return 30 - (Math.floor(Date.now() / 1000) % 30);
}

let totpInterval = null;

async function updateTOTP(secret) {
    const codeEl = document.getElementById('totpCode');
    const progressEl = document.getElementById('timerProgress');
    const textEl = document.getElementById('timerText');

    if (!codeEl || !secret) return;

    const code = await generateTOTP(secret);
    if (code) {
        codeEl.textContent = code.substr(0, 3) + ' ' + code.substr(3, 3);
    }

    const remaining = getRemainingSeconds();
    const percent = (remaining / 30) * 100;

    progressEl.style.width = percent + '%';
    progressEl.classList.remove('warning', 'danger');
    if (remaining <= 5) {
        progressEl.classList.add('danger');
    } else if (remaining <= 10) {
        progressEl.classList.add('warning');
    }

    textEl.textContent = remaining + 's';
}

function startTOTPTimer(secret) {
    if (totpInterval) clearInterval(totpInterval);

    updateTOTP(secret);
    totpInterval = setInterval(() => updateTOTP(secret), 1000);
}

// 复制到剪贴板
async function copyToClipboard(text, btn) {
    try {
        await navigator.clipboard.writeText(text);

        // 显示复制成功状态
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓';
        btn.classList.add('copied');

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);

        btn.innerHTML = '✓';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = '📋';
            btn.classList.remove('copied');
        }, 2000);
    }
}

// 兑换表单处理
function initRedeemForm() {
    const form = document.getElementById('redeemForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const codeInput = document.getElementById('code');
        const submitBtn = document.getElementById('submitBtn');
        const errorDiv = document.getElementById('errorMessage');

        const code = codeInput.value.trim();
        if (!code) {
            showError('请输入兑换码');
            return;
        }

        // 禁用按钮
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading"></span>兑换中...';
        errorDiv.classList.remove('show');

        try {
            const response = await fetch('/api/redeem', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code })
            });

            const data = await response.json();

            if (data.success) {
                // 显示结果
                showResult(data);
            } else {
                showError(data.error || '兑换失败');
            }
        } catch (err) {
            showError('网络错误，请稍后重试');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '立即兑换';
        }
    });

    // 自动转大写
    const codeInput = document.getElementById('code');
    if (codeInput) {
        codeInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase();
        });
    }
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');
    }
}

function showResult(data) {
    const container = document.querySelector('.redeem-container');

    // 构建 TOTP 显示区域
    let totpHtml = '';
    if (data.totp_secret) {
        totpHtml = `
            <div class="totp-container">
                <div class="totp-label">2FA 动态验证码</div>
                <div class="totp-code" id="totpCode">--- ---</div>
                <div class="totp-timer">
                    <div class="timer-bar">
                        <div class="timer-progress" id="timerProgress"></div>
                    </div>
                    <span class="timer-text" id="timerText">30s</span>
                </div>
                <button class="copy-btn" style="margin-top: 12px; padding: 8px 16px; background: var(--bg-input); border-radius: var(--radius-sm);" 
                        onclick="copyToClipboard(document.getElementById('totpCode').textContent.replace(' ', ''), this)">
                    📋 复制验证码
                </button>
            </div>
        `;
    }

    // 构建额外信息
    let extraHtml = '';
    if (data.extra_info) {
        try {
            // 尝试解析 JSON
            const extra = typeof data.extra_info === 'string'
                ? (data.extra_info.startsWith('{') ? JSON.parse(data.extra_info) : { info: data.extra_info })
                : data.extra_info;

            for (const [key, value] of Object.entries(extra)) {
                if (value) {
                    extraHtml += `
                        <div class="info-item">
                            <span class="label">${key}</span>
                            <span class="value">${value}</span>
                            <button class="copy-btn" onclick="copyToClipboard('${value}', this)">📋</button>
                        </div>
                    `;
                }
            }
        } catch (e) {
            // 纯文本格式
            extraHtml = `
                <div class="info-item">
                    <span class="label">其他信息</span>
                    <span class="value">${data.extra_info}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${data.extra_info}', this)">📋</button>
                </div>
            `;
        }
    }

    // 查看次数提示
    let viewCountHtml = '';
    if (data.view_count) {
        viewCountHtml = `
            <div class="view-count">
                这是您第 <strong>${data.view_count}</strong> 次查看此账号信息
            </div>
        `;
    }

    container.innerHTML = `
        <div class="result-card" style="max-width: 560px;">
            <div class="result-header">
                <div class="icon">✓</div>
                <h2>兑换成功</h2>
                <p>${data.group_name || '您的账号信息如下'}</p>
            </div>
            
            <div class="info-item">
                <span class="label">账号</span>
                <span class="value">${data.account}</span>
                <button class="copy-btn" onclick="copyToClipboard('${data.account}', this)">📋</button>
            </div>
            
            <div class="info-item">
                <span class="label">密码</span>
                <span class="value">${data.password}</span>
                <button class="copy-btn" onclick="copyToClipboard('${data.password}', this)">📋</button>
            </div>
            
            ${totpHtml}
            
            ${extraHtml}
            
            ${viewCountHtml}
            
            <div class="mt-4 text-center">
                <a href="/" class="btn btn-secondary">返回首页</a>
            </div>
        </div>
    `;

    // 如果有 TOTP，启动计时器
    if (data.totp_secret) {
        startTOTPTimer(data.totp_secret);
    }
}

// Flash 消息自动关闭
function initFlashMessages() {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(100%)';
            setTimeout(() => flash.remove(), 300);
        }, 3000);
    });
}

// 确认删除
function confirmDelete(message) {
    return confirm(message || '确定要删除吗？此操作不可撤销。');
}

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    initRedeemForm();
    initFlashMessages();
});

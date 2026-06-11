// Application State
let sessions = [];
let activeSessionId = null;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const historyList = document.getElementById('history-list');
const newChatBtn = document.getElementById('new-chat-btn');
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const themeText = document.getElementById('theme-text');
const menuToggle = document.getElementById('menu-toggle');
const clearCurrentChat = document.getElementById('clear-current-chat');
const chatFeed = document.getElementById('chat-feed');
const welcomeContainer = document.getElementById('welcome-container');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');

// Configure Marked.js
marked.use({
    gfm: true,
    breaks: true,
    highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
    }
});

// Init Application
document.addEventListener('DOMContentLoaded', () => {
    loadSessionsFromStorage();
    initTheme();
    setupEventListeners();
    renderHistory();
    lucide.createIcons();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('agentic_rag_theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        themeText.textContent = 'Modo Oscuro';
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        themeText.textContent = 'Modo Claro';
    }
}

function toggleTheme() {
    if (document.body.classList.contains('dark-theme')) {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        themeText.textContent = 'Modo Oscuro';
        localStorage.setItem('agentic_rag_theme', 'light');
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        themeText.textContent = 'Modo Claro';
        localStorage.setItem('agentic_rag_theme', 'dark');
    }
    lucide.createIcons();
}

// Session Management
function loadSessionsFromStorage() {
    const stored = localStorage.getItem('agentic_rag_sessions');
    if (stored) {
        try {
            sessions = JSON.parse(stored);
        } catch (e) {
            sessions = [];
        }
    }
    if (sessions.length === 0) {
        createNewSession();
    } else {
        activeSessionId = sessions[0].id;
        loadSession(activeSessionId);
    }
}

function saveSessionsToStorage() {
    localStorage.setItem('agentic_rag_sessions', JSON.stringify(sessions));
}

function createNewSession() {
    const newSession = {
        id: generateUUID(),
        title: 'Nueva conversación',
        messages: [],
        createdAt: new Date().toISOString()
    };
    sessions.unshift(newSession);
    saveSessionsToStorage();
    activeSessionId = newSession.id;
    
    renderHistory();
    loadSession(activeSessionId);
}

function loadSession(id) {
    activeSessionId = id;
    const session = sessions.find(s => s.id === id);
    if (!session) return;
    
    // Update active state in sidebar
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id === id);
    });
    
    // Clear feed
    chatFeed.innerHTML = '';
    
    if (session.messages.length === 0) {
        chatFeed.appendChild(welcomeContainer);
        welcomeContainer.style.display = 'flex';
    } else {
        welcomeContainer.style.display = 'none';
        session.messages.forEach((msg, idx) => {
            appendMessage(msg.role, msg.content, false, msg.sources || [], msg.timestamp, idx);
        });
    }
    
    scrollToBottom();
}

function deleteSession(id, event) {
    if (event) event.stopPropagation();
    
    const index = sessions.findIndex(s => s.id === id);
    if (index === -1) return;
    
    sessions.splice(index, 1);
    saveSessionsToStorage();
    
    if (sessions.length === 0) {
        createNewSession();
    } else if (activeSessionId === id) {
        activeSessionId = sessions[0].id;
        loadSession(activeSessionId);
    } else {
        renderHistory();
    }
}

function renameSession(id, event) {
    if (event) event.stopPropagation();
    const session = sessions.find(s => s.id === id);
    if (!session) return;
    
    const newTitle = prompt('Renombrar conversación:', session.title);
    if (newTitle && newTitle.trim()) {
        session.title = newTitle.trim();
        saveSessionsToStorage();
        renderHistory();
    }
}

// Sidebar Rendering
function renderHistory() {
    historyList.innerHTML = '';
    
    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `history-item ${session.id === activeSessionId ? 'active' : ''}`;
        item.dataset.id = session.id;
        
        item.innerHTML = `
            <i data-lucide="message-square"></i>
            <span class="chat-title" title="${session.title}">${session.title}</span>
            <div class="history-actions">
                <button class="rename-btn" title="Renombrar"><i data-lucide="edit-2"></i></button>
                <button class="delete-btn" title="Borrar"><i data-lucide="trash-2"></i></button>
            </div>
        `;
        
        item.querySelector('.rename-btn').addEventListener('click', (e) => renameSession(session.id, e));
        item.querySelector('.delete-btn').addEventListener('click', (e) => deleteSession(session.id, e));
        item.addEventListener('click', () => loadSession(session.id));
        
        historyList.appendChild(item);
    });
    lucide.createIcons();
}

// Event Listeners setup
function setupEventListeners() {
    newChatBtn.addEventListener('click', createNewSession);
    themeToggleBtn.addEventListener('click', toggleTheme);
    
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
    
    // Close sidebar on click outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && 
            !sidebar.contains(e.target) && 
            !menuToggle.contains(e.target) && 
            sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    });

    clearCurrentChat.addEventListener('click', () => {
        if (confirm('¿Estás seguro de que deseas borrar los mensajes de este chat?')) {
            const session = sessions.find(s => s.id === activeSessionId);
            if (session) {
                session.messages = [];
                session.title = 'Nueva conversación';
                saveSessionsToStorage();
                renderHistory();
                loadSession(activeSessionId);
            }
        }
    });
    
    // Input key behaviors
    chatInput.addEventListener('input', () => {
        // Auto-resize textarea
        chatInput.style.height = 'auto';
        chatInput.style.height = (chatInput.scrollHeight) + 'px';
        
        sendBtn.disabled = !chatInput.value.trim();
    });
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    sendBtn.addEventListener('click', sendMessage);
    
    // Suggestions Click
    document.querySelectorAll('.suggestion-card').forEach(card => {
        card.addEventListener('click', () => {
            const query = card.dataset.query;
            chatInput.value = query;
            chatInput.dispatchEvent(new Event('input'));
            sendMessage();
        });
    });
}

// Sending Messages & Streaming
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;
    
    // Hide welcome container if present
    if (welcomeContainer.parentNode) {
        welcomeContainer.style.display = 'none';
    }
    
    // Update active session messages
    const session = sessions.find(s => s.id === activeSessionId);
    if (!session) return;
    
    // Set title if it is the first message
    if (session.messages.length === 0) {
        session.title = text.length > 30 ? text.substring(0, 30) + '...' : text;
        renderHistory();
    }
    
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = { 
        role: 'user', 
        content: text,
        timestamp: timeNow
    };
    session.messages.push(userMsg);
    saveSessionsToStorage();
    
    // Render user message bubble
    appendMessage('user', text, false, [], timeNow, session.messages.length - 1);
    
    // Render empty assistant block and progress steps block
    const stepsBlock = createAgentStepsBlock();
    const assistantBubble = appendMessage('assistant', '', true, [], null, session.messages.length); // starts as empty, placeholder
    
    let currentSources = [];
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ messages: session.messages })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let assistantReply = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep partial line in buffer
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const rawData = line.slice(6).trim();
                    if (!rawData || rawData === '[DONE]') continue;
                    
                    try {
                        const data = JSON.parse(rawData);
                        if (data.type === 'token') {
                            assistantReply += data.token;
                            updateMessageText(assistantBubble, assistantReply, currentSources);
                        } else if (data.type === 'sources') {
                            currentSources = data.sources;
                        } else if (data.type === 'status') {
                            updateAgentStep(stepsBlock, data.node, data.status);
                        } else if (data.type === 'error') {
                            console.error("Server error:", data.message);
                            assistantReply += `\n\n*Error: ${data.message}*`;
                            updateMessageText(assistantBubble, assistantReply, currentSources);
                        }
                    } catch (err) {
                        console.error('Failed to parse SSE JSON:', err, line);
                    }
                }
            }
        }
        
        // Finalize reply in storage
        if (assistantReply.trim()) {
            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            session.messages.push({ 
                role: 'assistant', 
                content: assistantReply, 
                sources: currentSources,
                timestamp: timeStr
            });
            saveSessionsToStorage();
        }
        
        // Mark all steps as complete
        finalizeAgentSteps(stepsBlock);
        
    } catch (error) {
        console.error('Error sending message:', error);
        updateMessageText(assistantBubble, `*Lo siento, ocurrió un error al procesar tu solicitud: ${error.message}*`);
        finalizeAgentSteps(stepsBlock, true);
    } finally {
        sendBtn.disabled = !chatInput.value.trim();
    }
}

// UI Helpers
function appendMessage(role, content, isPlaceholder = false, sources = [], timestamp = null, msgIndex = null) {
    const row = document.createElement('div');
    row.className = `message-row ${role}-msg`;
    
    let avatarHtml = '';
    if (role === 'assistant') {
        avatarHtml = `<div class="message-avatar"><i data-lucide="bot"></i></div>`;
    }
    
    const timeStr = timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    const metaHtml = `
        <div class="message-meta">
            <span class="message-time">${timeStr}</span>
            <button class="msg-meta-btn copy-msg-btn" title="Copiar mensaje"><i data-lucide="copy"></i></button>
            ${role === 'user' && msgIndex !== null ? `<button class="msg-meta-btn rollback-msg-btn" title="Volver a este mensaje"><i data-lucide="corner-up-left"></i></button>` : ''}
        </div>
    `;
    
    row.innerHTML = `
        <div class="message-container">
            ${avatarHtml}
            <div class="message-bubble">
                <div class="message-bubble-content">
                    ${isPlaceholder ? '<span class="typing-cursor">|</span>' : formatMarkdown(content, sources)}
                </div>
                ${metaHtml}
            </div>
        </div>
    `;
    
    chatFeed.appendChild(row);
    scrollToBottom();
    lucide.createIcons();
    
    const bubbleContent = row.querySelector('.message-bubble-content');
    
    // Copy message click handler
    row.querySelector('.copy-msg-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        const plainText = bubbleContent.innerText.trim();
        const cleanText = plainText.endsWith('|') ? plainText.slice(0, -1).trim() : plainText;
        navigator.clipboard.writeText(cleanText).then(() => {
            const btn = row.querySelector('.copy-msg-btn');
            btn.innerHTML = `<i data-lucide="check" style="color:var(--status-success)"></i>`;
            lucide.createIcons();
            setTimeout(() => {
                btn.innerHTML = `<i data-lucide="copy"></i>`;
                lucide.createIcons();
            }, 1500);
        });
    });
    
    // Rollback click handler
    if (role === 'user' && msgIndex !== null) {
        row.querySelector('.rollback-msg-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            rollbackToMessage(msgIndex);
        });
    }
    
    return bubbleContent;
}

function updateMessageText(contentElement, rawContent, sources = []) {
    contentElement.innerHTML = formatMarkdown(rawContent, sources) + '<span class="typing-cursor">|</span>';
    
    // Trigger highlight.js for any code block inside the update
    contentElement.querySelectorAll('pre code').forEach((block) => {
        if (!block.dataset.highlighted) {
            hljs.highlightElement(block);
            block.dataset.highlighted = 'true';
        }
    });
    
    // Add copy button listeners
    contentElement.querySelectorAll('.copy-code-btn').forEach(btn => {
        btn.addEventListener('click', () => copyCodeBlock(btn));
    });
    
    // Scroll occasionally during stream
    scrollToBottom();
}

function formatMarkdown(text, sources = []) {
    // Basic formatting using Marked.js
    let html = marked.parse(text);
    
    // Customize code blocks to add header wrapper with title and copy button
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    tempDiv.querySelectorAll('pre').forEach(pre => {
        const code = pre.querySelector('code');
        const langClass = code ? Array.from(code.classList).find(c => c.startsWith('language-')) : '';
        const langName = langClass ? langClass.replace('language-', '') : 'code';
        
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        
        const header = document.createElement('div');
        header.className = 'code-block-header';
        header.innerHTML = `
            <span>${langName}</span>
            <button class="copy-code-btn"><i data-lucide="clipboard" style="width:13px;height:13px"></i> Copiar</button>
        `;
        
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(header);
        wrapper.appendChild(pre);
    });
    
    // Replace citations in the DOM structure safely
    replaceCitationsInDOM(tempDiv, sources);
    
    return tempDiv.innerHTML;
}

// Agent Steps UI handling
function createAgentStepsBlock() {
    const container = document.createElement('div');
    container.className = 'agent-status-container';
    
    container.innerHTML = `
        <div class="agent-steps">
            <div class="agent-steps-header">
                <div class="header-left">
                    <i data-lucide="activity" style="width:16px;height:16px;color:var(--accent-color)"></i>
                    <span>Analizando con RAG Agéntico...</span>
                </div>
                <i data-lucide="chevron-down" class="chevron"></i>
            </div>
            <div class="agent-steps-content">
                <div class="agent-step-item" id="step-generate_query_or_respond">
                    <div class="step-spinner"></div>
                    <span>Evaluando pregunta del usuario</span>
                </div>
                <div class="agent-step-item" id="step-retrieve" style="display:none">
                    <div class="step-spinner"></div>
                    <span>Buscando documentos en el índice híbrido (Chroma + BM25)</span>
                </div>
                <div class="agent-step-item" id="step-rewrite_question" style="display:none">
                    <div class="step-spinner"></div>
                    <span>Optimizando términos de búsqueda</span>
                </div>
                <div class="agent-step-item" id="step-generate_answer" style="display:none">
                    <div class="step-spinner"></div>
                    <span>Redactando respuesta en español</span>
                </div>
            </div>
        </div>
    `;
    
    chatFeed.appendChild(container);
    scrollToBottom();
    lucide.createIcons();
    
    // Toggle accordion
    const stepsDiv = container.querySelector('.agent-steps');
    container.querySelector('.agent-steps-header').addEventListener('click', () => {
        stepsDiv.classList.toggle('collapsed');
    });
    
    return container;
}

function updateAgentStep(container, node, status) {
    const stepEl = container.querySelector(`#step-${node}`);
    if (!stepEl) return;
    
    if (status === 'start') {
        // Show this step
        stepEl.style.display = 'flex';
        stepEl.className = 'agent-step-item active';
        // Mark previous active step as completed
        container.querySelectorAll('.agent-step-item.active').forEach(el => {
            if (el.id !== `step-${node}`) {
                el.className = 'agent-step-item completed';
                el.querySelector('.step-spinner').outerHTML = '<i data-lucide="check-circle-2" style="color:var(--status-success)"></i>';
            }
        });
    } else if (status === 'end') {
        stepEl.className = 'agent-step-item completed';
        const spinner = stepEl.querySelector('.step-spinner');
        if (spinner) {
            spinner.outerHTML = '<i data-lucide="check-circle-2" style="color:var(--status-success)"></i>';
        }
    }
    lucide.createIcons();
    scrollToBottom();
}

function finalizeAgentSteps(container, isError = false) {
    // Remove typing cursors from bubbles
    document.querySelectorAll('.typing-cursor').forEach(el => el.remove());
    
    // Mark all remaining spinners as completed
    container.querySelectorAll('.step-spinner').forEach(spinner => {
        if (isError) {
            spinner.outerHTML = '<i data-lucide="alert-circle" style="color:var(--status-pending)"></i>';
        } else {
            spinner.outerHTML = '<i data-lucide="check-circle-2" style="color:var(--status-success)"></i>';
        }
    });
    
    // Ensure all displayed items are completed
    container.querySelectorAll('.agent-step-item.active').forEach(el => {
        el.className = 'agent-step-item completed';
    });
    
    // Change top header title
    const headerTitle = container.querySelector('.agent-steps-header .header-left span');
    headerTitle.textContent = isError ? 'Error en análisis agéntico' : 'Análisis agéntico completado';
    
    // Collapse the accordion automatically to clean up space
    setTimeout(() => {
        container.querySelector('.agent-steps').classList.add('collapsed');
    }, 1500);
    
    lucide.createIcons();
    scrollToBottom();
}

// Utility Helpers
function scrollToBottom() {
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function copyCodeBlock(btn) {
    const code = btn.closest('.code-block-wrapper').querySelector('code').textContent;
    navigator.clipboard.writeText(code).then(() => {
        btn.innerHTML = `<i data-lucide="check" style="width:13px;height:13px;color:var(--status-success)"></i> Copiado!`;
        lucide.createIcons();
        setTimeout(() => {
            btn.innerHTML = `<i data-lucide="clipboard" style="width:13px;height:13px"></i> Copiar`;
            lucide.createIcons();
        }, 2000);
    });
}

// Citation parsing helper to safely replace [1], [2] with hover tooltips
function replaceCitationsInDOM(node, sources) {
    if (node.nodeType === Node.TEXT_NODE) {
        const text = node.nodeValue;
        const regex = /\[(\d+)\]/g;
        if (regex.test(text)) {
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;
            regex.lastIndex = 0; // reset
            let match;
            while ((match = regex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)));
                }
                
                const indexStr = match[1];
                const src = sources.find(s => s.index === indexStr);
                
                if (src) {
                    const badge = document.createElement('span');
                    badge.className = 'citation-badge';
                    badge.textContent = `[${indexStr}]`;
                    badge.dataset.index = indexStr;
                    
                    const tooltip = document.createElement('span');
                    tooltip.className = 'citation-tooltip';
                    
                    const filename = src.source.split(/[/\\]/).pop();
                    
                    // Clean text (removing HTML tags, tables, images, etc.)
                    const cleanedSnippet = cleanTooltipText(src.content);
                    const previewText = cleanedSnippet.length > 250 
                        ? cleanedSnippet.substring(0, 250) + '...' 
                        : cleanedSnippet;
                    
                    // Render inline markdown elements beautifully (bold, italics, inline code)
                    const parsedHtml = marked.parseInline(previewText);
                        
                    tooltip.innerHTML = `<strong>${filename}</strong><span>${parsedHtml}</span>`;
                    badge.appendChild(tooltip);
                    
                    // Mobile tap toggler
                    badge.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const isActive = badge.classList.contains('active');
                        document.querySelectorAll('.citation-badge').forEach(b => b.classList.remove('active'));
                        if (!isActive) {
                            badge.classList.add('active');
                        }
                    });
                    
                    fragment.appendChild(badge);
                } else {
                    fragment.appendChild(document.createTextNode(match[0]));
                }
                lastIndex = regex.lastIndex;
            }
            if (lastIndex < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
            }
            node.parentNode.replaceChild(fragment, node);
        }
    } else if (node.nodeType === Node.ELEMENT_NODE && node.nodeName !== 'CODE' && node.nodeName !== 'PRE' && node.nodeName !== 'A') {
        const children = Array.from(node.childNodes);
        for (const child of children) {
            replaceCitationsInDOM(child, sources);
        }
    }
}

function cleanTooltipText(text) {
    let clean = text;
    // 1. Remove markdown images: ![](images/...)
    clean = clean.replace(/!\[.*?\]\(.*?\)/g, '');
    // 2. Remove HTML tags like table, tr, td, img
    clean = clean.replace(/<\/?[a-z][a-z0-9]*\b[^>]*>/gi, ' ');
    // 3. Remove Markdown header markers (e.g. ###, ##, #)
    clean = clean.replace(/#+\s+/g, '');
    // 4. Collapse multiple spaces and newlines
    clean = clean.replace(/\s+/g, ' ').trim();
    return clean;
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Dismiss active tooltips when clicking outside
document.addEventListener('click', () => {
    document.querySelectorAll('.citation-badge').forEach(b => b.classList.remove('active'));
});

function rollbackToMessage(msgIndex) {
    const session = sessions.find(s => s.id === activeSessionId);
    if (!session) return;
    
    const text = session.messages[msgIndex].content;
    
    if (!confirm(`¿Deseas volver a la pregunta "${text.length > 40 ? text.substring(0, 40) + '...' : text}"? Se borrarán todos los mensajes posteriores.`)) {
        return;
    }
    
    // Remove all messages starting from msgIndex
    session.messages.splice(msgIndex);
    saveSessionsToStorage();
    
    // Place this message's text back into the chat input
    chatInput.value = text;
    chatInput.dispatchEvent(new Event('input')); // trigger auto-resize
    
    // Load session again to refresh the feed
    loadSession(activeSessionId);
    
    // Focus textarea
    chatInput.focus();
}

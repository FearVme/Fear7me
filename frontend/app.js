/**
 * 主要作用：运行工程设计变更智能问答前端交互。
 * 纯对话模式：首页选择 A/B/C 角色，提供问答、复制、重新回答和请求暂停交互。
 */

(function () {
  // 当前角色状态与权限定义
  let currentRole = 'A';
  let activeIndex = 0;
  let bgSlideIndex = 0;
  let bgTimer = null;
  let locationWeatherLoaded = false;
  let requestPending = false;
  let requestToken = 0;
  let lastUserQuestion = '';

  const ROLE_CONFIG = {
    A: {
      code: 'A',
      name: '角色 A · 项目经理',
      duty: '单项目查看权限',
      avatar: '🛡️',
      desc: '合规审查 · 违规穿透 · 纪检问责',
      welcome: '你好，当前是**角色 A · 项目经理**，可查看南区水厂二期 EPC 项目。\n\n你可以询问制度要求、项目与变更数据，或发起合规审计。'
    },
    B: {
      code: 'B',
      name: '角色 B · 区域管理',
      duty: '区域三项目查看权限',
      avatar: '📐',
      desc: '分级审批 · 专家论证 · 单据闭环',
      welcome: '你好，当前是**角色 B · 区域管理**，可查看区域内 3 个项目。\n\n你可以询问制度要求、项目与变更数据，或发起合规审计。'
    },
    C: {
      code: 'C',
      name: '角色 C · 全部项目',
      duty: '全部项目查看权限',
      avatar: '🏛️',
      desc: '投资控制 · 阳光公示 · 宏观决策',
      welcome: '你好，当前是**角色 C · 全部项目**，可查看全部 8 个项目。\n\n你可以询问制度要求、项目与变更数据，或发起合规审计。'
    }
  };

  // DOM 元素引用
  const refFilesBtn = document.getElementById('refFilesBtn');
  const refFilesModal = document.getElementById('refFilesModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const referenceFilesBody = document.getElementById('referenceFilesBody');
  const weatherWidgets = document.querySelectorAll('.weather-widget');
  const geminiChatModal = document.getElementById('geminiChatModal');
  const closeChatModalBtn = document.getElementById('closeChatModalBtn');
  const chatScrollArea = document.getElementById('chatScrollArea');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const bottomLeftBadge = document.getElementById('bottomLeftRoleBadge');
  const roleBadgeCircle = document.getElementById('roleBadgeCircle');
  const rolePopupStack = document.getElementById('rolePopupStack');
  const feedbackBtn = document.getElementById('feedbackBtn');
  const versionBtn = document.getElementById('versionBtn');
  const feedbackModal = document.getElementById('feedbackModal');
  const versionModal = document.getElementById('versionModal');
  const closeFeedbackBtn = document.getElementById('closeFeedbackBtn');
  const closeVersionBtn = document.getElementById('closeVersionBtn');
  const feedbackInput = document.getElementById('feedbackInput');
  const submitFeedbackBtn = document.getElementById('submitFeedbackBtn');
  const feedbackStatus = document.getElementById('feedbackStatus');
  const feedbackList = document.getElementById('feedbackList');
  const versionList = document.getElementById('versionList');

  // 初始化绑定
  function init() {
    // 1. 初始化全屏三图平滑轮播
    initBackgroundCarousel();

    // 2. 首页角色权限卡片点击与滑过联动
    const roleCols = document.querySelectorAll('.role-slide-col, .role-slide-card');
    roleCols.forEach(card => {
      const idx = parseInt(card.getAttribute('data-index'), 10);
      const role = card.getAttribute('data-role');

      card.addEventListener('mouseenter', () => {
        updateSlidingIndicator(idx);
      });

      card.addEventListener('click', () => {
        openGeminiChat(role);
      });
    });

    // 3. 点击右上角感叹号：弹窗展示全部参考文件
    refFilesBtn.addEventListener('click', () => {
      refFilesModal.classList.add('open');
    });

    closeModalBtn.addEventListener('click', () => {
      refFilesModal.classList.remove('open');
    });

    refFilesModal.addEventListener('click', (e) => {
      if (e.target === refFilesModal) {
        refFilesModal.classList.remove('open');
      }
    });

    // 4. 关闭 Gemini 提问居中弹出框
    closeChatModalBtn.addEventListener('click', () => {
      geminiChatModal.classList.remove('open');
      closeRolePopupStack();
    });

    geminiChatModal.addEventListener('click', (e) => {
      if (e.target === geminiChatModal) {
        geminiChatModal.classList.remove('open');
        closeRolePopupStack();
      }
    });

    // 5. 左下角角色圆圈点击：向上弹出 ABC 三个角色的按钮（不覆盖页面）
    if (roleBadgeCircle && rolePopupStack) {
      roleBadgeCircle.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = rolePopupStack.classList.contains('open');
        if (isOpen) {
          closeRolePopupStack();
        } else {
          openRolePopupStack();
        }
      });
    }

    // 点击向上弹出的 A / B / C 按钮进行角色切换
    document.querySelectorAll('.role-pop-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const role = btn.getAttribute('data-role');
        switchRoleInChat(role);
        closeRolePopupStack();
      });
    });

    // 点击对话框任意其他位置时自动收回三个按钮
    document.addEventListener('click', (e) => {
      if (bottomLeftBadge && !bottomLeftBadge.contains(e.target)) {
        closeRolePopupStack();
      }
    });

    // 6. 输入框与发送消息
    sendBtn.addEventListener('click', () => {
      if (requestPending) {
        pauseRequest();
        return;
      }
      handleSend();
    });
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        handleSend();
      }
    });

    feedbackBtn.addEventListener('click', () => feedbackModal.classList.add('open'));
    versionBtn.addEventListener('click', () => versionModal.classList.add('open'));
    closeFeedbackBtn.addEventListener('click', () => feedbackModal.classList.remove('open'));
    closeVersionBtn.addEventListener('click', () => versionModal.classList.remove('open'));

    feedbackModal.addEventListener('click', (event) => {
      if (event.target === feedbackModal) feedbackModal.classList.remove('open');
    });

    versionModal.addEventListener('click', (event) => {
      if (event.target === versionModal) versionModal.classList.remove('open');
    });

    submitFeedbackBtn.addEventListener('click', () => {
      const content = feedbackInput.value.trim();
      if (!content) return;
      sendInteractionToStreamlit('submit_feedback', content);
      feedbackInput.value = '';
    });

    // 7. 三类核心能力快捷入口
    document.querySelectorAll('.capability-card').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-action');
        triggerAction(action);
      });
    });

  }

  // ================= 全屏三张大图自动轮播 =================
  function initBackgroundCarousel() {
    const slides = document.querySelectorAll('.bg-carousel-slide');
    const dots = document.querySelectorAll('.bg-dot');
    if (!slides.length) return;

    function goToSlide(idx) {
      bgSlideIndex = idx;
      slides.forEach((s, i) => s.classList.toggle('active', i === idx));
      dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    }

    dots.forEach((dot, idx) => {
      dot.addEventListener('click', () => {
        goToSlide(idx);
        restartCarouselTimer();
      });
    });

    function startCarouselTimer() {
      bgTimer = setInterval(() => {
        const next = (bgSlideIndex + 1) % slides.length;
        goToSlide(next);
      }, 5500);
    }

    function restartCarouselTimer() {
      if (bgTimer) clearInterval(bgTimer);
      startCarouselTimer();
    }

    startCarouselTimer();
  }

  // 更新首页角色卡片的悬停状态。
  function updateSlidingIndicator(index) {
    activeIndex = index;
    const roleCols = document.querySelectorAll('.role-slide-col, .role-slide-card');
    roleCols.forEach((card, i) => card.classList.toggle('active', i === index));
  }

  // 选中角色权限后居中弹出 Gemini 对话框
  function openGeminiChat(role) {
    currentRole = role;
    const config = ROLE_CONFIG[role] || ROLE_CONFIG.A;

    geminiChatModal.classList.add('open');
    updateRoleBadgeUI(role);

    if (chatScrollArea.children.length === 0) {
      appendAIMessage(config.welcome);
    }
  }

  // 主要作用：切换 A、B、C 角色，并清空当前角色的聊天显示。
  function switchRoleInChat(role) {
  pauseRequest();
  currentRole = role;
  updateRoleBadgeUI(role);

  hideTyping();
  chatScrollArea.replaceChildren();

  const config = ROLE_CONFIG[role] || ROLE_CONFIG.A;
  appendAIMessage(config.welcome);

  sendRoleSwitchToStreamlit(role);
}

  function openRolePopupStack() {
    if (rolePopupStack && bottomLeftBadge) {
      rolePopupStack.classList.add('open');
      bottomLeftBadge.classList.add('stack-open');
    }
  }

  function closeRolePopupStack() {
    if (rolePopupStack && bottomLeftBadge) {
      rolePopupStack.classList.remove('open');
      bottomLeftBadge.classList.remove('stack-open');
    }
  }

  function updateRoleBadgeUI(role) {
    const badge = document.getElementById('roleBadgeCircle');
    const letter = document.getElementById('roleLetterDisplay');
    if (badge && letter) {
      letter.textContent = role;
      badge.className = `role-badge-circle role-${role.toLowerCase()}`;
    }

    document.querySelectorAll('.role-pop-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-role') === role);
    });
  }

  // 发送消息处理
  function handleSend() {
    if (requestPending) return;
    const text = chatInput.value.trim();
    if (!text) return;
    appendUserMessage(text);
    lastUserQuestion = text;
    chatInput.value = '';

    requestToken += 1;
    requestPending = true;
    setRequestState(true);
    showTyping(getServiceName(text));
    sendToStreamlit(text, requestToken);
  }

  // 主要作用：将当前角色的问题发送给 Streamlit 后端。
function sendToStreamlit(text, token) {
  window.parent.postMessage({
    isStreamlitMessage: true,
    type: 'streamlit:setComponentValue',
    value: {
      action: 'ask',
      role: currentRole,
      message: text,
      request_token: token
    }
  }, '*');
}

// 主要作用：用同一问题重新生成回答，不重复添加用户消息。
function regenerateAnswer(question) {
  if (requestPending || !question) return;
  requestToken += 1;
  requestPending = true;
  lastUserQuestion = question;
  setRequestState(true);
  showTyping(getServiceName(question));
  sendInteractionToStreamlit(
    'regenerate',
    question,
    { request_token: requestToken }
  );
}
// 主要作用：通知后端用户刚刚切换了 A、B、C 角色。
function sendRoleSwitchToStreamlit(role) {
  window.parent.postMessage({
    isStreamlitMessage: true,
    type: 'streamlit:setComponentValue',
    value: {
      action: 'switch_role',
      role: role,
      message: role
    }
  }, '*');
}

  // 主要作用：暂停当前请求，允许用户重新发起问题。
  function pauseRequest() {
    if (!requestPending) return;
    requestToken += 1;
    requestPending = false;
    hideTyping();
    setRequestState(false);
  }

  // 主要作用：锁定或恢复输入控件。
  function setRequestState(pending) {
    chatInput.disabled = pending;
    document.querySelectorAll('.capability-card').forEach(btn => {
      btn.disabled = pending;
    });
    sendBtn.classList.toggle('pause-active', pending);
    sendBtn.title = pending ? '暂停查询' : '发送';
    sendBtn.innerHTML = pending ? '<span>■</span>' : '<span>➤</span>';
  }

  function sendInteractionToStreamlit(action, message, extra = {}) {
    window.parent.postMessage({
      isStreamlitMessage: true,
      type: 'streamlit:setComponentValue',
      value: {
        action,
        role: currentRole,
        message,
        ...extra
      }
    }, '*');
  }

  // 主要作用：根据问题内容显示当前正在运行的能力名称。
  function getServiceName(text) {
    const query = text.toLowerCase();

    if (
      query.includes('审计') || query.includes('核查') ||
      query.includes('检查') || query.includes('审批') ||
      query.includes('公示') || query.includes('未批先建') ||
      query.includes('退回后施工')
    ) {
      return '正在运行：审计分析';
    }

    if (
      query.includes('查询') || query.includes('查看') ||
      query.includes('变更记录') || query.includes('评审记录') ||
      query.includes('基本信息')
    ) {
      return '正在运行：数据库查询';
    }

    return '正在运行：制度检索';
  }

  function receiveFromStreamlit(event) {
    if (!event.data || event.data.type !== 'streamlit:render') return;
    const args = event.data.args || {};
    if (args.weather && !locationWeatherLoaded) {
      updateWeather(args.weather);
    }
    if (Array.isArray(args.reference_files)) {
      renderReferenceFiles(args.reference_files);
    }
    if (Array.isArray(args.versions)) {
      renderVersions(args.versions);
    }
    if (Array.isArray(args.feedback)) {
      renderFeedback(args.feedback);
    }
    if (args.feedback_status) {
      feedbackStatus.textContent = args.feedback_status;
    }
    if (args.role && args.role !== currentRole) {
      currentRole = args.role;
      updateRoleBadgeUI(currentRole);
    }
    if (
      args.response && requestPending &&
      Number(args.response_token) === requestToken
    ) {
      requestPending = false;
      setRequestState(false);
      hideTyping();
      appendAIMessage(args.response, lastUserQuestion);
    }
    window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: document.body.scrollHeight }, '*');
  }

  function weatherPresentation(weather) {
    const code = Number(weather.weather_code);
    if ([95, 96, 99].includes(code)) return { condition: 'storm', icon: '⛈️', label: '雷雨' };
    if ([71, 73, 75, 77, 85, 86].includes(code)) return { condition: 'snow', icon: '❄️', label: '降雪' };
    if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { condition: 'rain', icon: '🌧️', label: '降雨' };
    if ([1, 2, 3, 45, 48].includes(code)) return { condition: 'cloudy', icon: '⛅', label: '多云' };
    return { condition: 'clear', icon: Number(weather.is_day) === 0 ? '🌙' : '☀️', label: '晴朗' };
  }

  function updateWeather(weather) {
    const presentation = weatherPresentation(weather || {});
    const city = weather.city || '深圳';
    const temperature = Number.isFinite(Number(weather.temperature)) ? `${Math.round(Number(weather.temperature))}°` : '--°';
    weatherWidgets.forEach(widget => {
      widget.dataset.condition = presentation.condition;
      const icon = widget.querySelector('.weather-icon');
      const temp = widget.querySelector('.weather-temp');
      const label = widget.querySelector('.weather-label');
      if (icon) icon.textContent = presentation.icon;
      if (temp) temp.textContent = temperature;
      if (label) label.textContent = `${city} · ${presentation.label}`;
    });
  }

  // 主要作用：根据访问者公网 IP 获取所在城市天气。
  async function loadLocationWeather() {
    const locationResponse = await fetch('https://ipwho.is/');
    const location = await locationResponse.json();
    const weatherResponse = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${location.latitude}&longitude=${location.longitude}&current=temperature_2m,weather_code,is_day&timezone=auto`
    );
    const weather = await weatherResponse.json();
    locationWeatherLoaded = true;
    updateWeather({
      city: location.city,
      temperature: weather.current.temperature_2m,
      weather_code: weather.current.weather_code,
      is_day: weather.current.is_day
    });
  }

  function formatFileSize(bytes) {
    const size = Number(bytes) || 0;
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  function renderReferenceFiles(files) {
    if (!referenceFilesBody) return;
    referenceFilesBody.replaceChildren();

    if (!files.length) {
      const empty = document.createElement('div');
      empty.className = 'reference-files-empty';
      empty.innerHTML = '<strong>暂无参考文件</strong><span>请将文件放入 GitHub 仓库的 reference_files/ 文件夹后重新部署。</span>';
      referenceFilesBody.appendChild(empty);
      return;
    }

    const groups = new Map();
    files.forEach(file => {
      const category = file.category || '参考文件';
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push(file);
    });

    groups.forEach((groupFiles, category) => {
      const section = document.createElement('section');
      section.className = 'file-sec';
      const heading = document.createElement('h4');
      heading.textContent = category;
      section.appendChild(heading);

      const list = document.createElement('div');
      list.className = 'file-list';
      groupFiles.forEach(file => {
        const row = document.createElement('div');
        row.className = 'file-row';
        const left = document.createElement('div');
        left.className = 'file-row-left';
        const badge = document.createElement('span');
        badge.className = `badge-tag badge-${String(file.extension || 'file').toLowerCase()}`;
        badge.textContent = file.extension || 'FILE';
        const name = document.createElement('span');
        name.className = 'file-desc';
        name.textContent = file.name || file.path || '未命名文件';
        left.append(badge, name);
        const actions = document.createElement('div');
        actions.className = 'file-actions';
        const meta = document.createElement('span');
        meta.className = 'file-size';
        meta.textContent = formatFileSize(file.size);
        actions.appendChild(meta);

        const dataUrl = `data:${file.mime_type};base64,${file.data}`;
        if (file.mime_type === 'application/pdf') {
          const preview = document.createElement('button');
          preview.className = 'file-action-btn';
          preview.textContent = '预览';
          preview.addEventListener('click', () => window.open(dataUrl, '_blank'));
          actions.appendChild(preview);
        }

        const download = document.createElement('a');
        download.className = 'file-action-btn';
        download.textContent = '下载';
        download.href = dataUrl;
        download.download = file.name;
        actions.appendChild(download);
        row.append(left, actions);
        list.appendChild(row);
      });
      section.appendChild(list);
      referenceFilesBody.appendChild(section);
    });
  }

  function renderVersions(versions) {
    versionList.replaceChildren();
    if (versions.length) {
      versionBtn.textContent = versions[versions.length - 1].version;
    }

    [...versions].reverse().forEach(item => {
      const row = document.createElement('div');
      row.className = 'version-row';
      row.innerHTML = `<strong>${escapeHtml(item.version)}</strong><span>${escapeHtml(item.description)}</span>`;
      versionList.appendChild(row);
    });
  }

  function renderFeedback(items) {
    feedbackList.replaceChildren();
    [...items].reverse().forEach(item => {
      const row = document.createElement('div');
      row.className = 'feedback-row';
      row.innerHTML = `
        <div><strong>${escapeHtml(item.role)}角色</strong> · ${escapeHtml(String(item.submitted_at))}</div>
        <p>${escapeHtml(item.content)}</p>
        <div class="feedback-reply-text">${item.reply ? `回复：${escapeHtml(item.reply)}` : '暂未回复'}</div>
      `;

      const replyInput = document.createElement('input');
      replyInput.className = 'feedback-reply-input';
      replyInput.placeholder = '输入回复内容';
      const replyButton = document.createElement('button');
      replyButton.className = 'file-action-btn';
      replyButton.textContent = '保存回复';
      replyButton.addEventListener('click', () => {
        const reply = replyInput.value.trim();
        if (!reply) return;
        sendInteractionToStreamlit(
          'reply_feedback',
          reply,
          { feedback_id: item.feedback_id }
        );
      });
      row.append(replyInput, replyButton);
      feedbackList.appendChild(row);
    });
  }

  // 主要作用：点击能力入口后，发起对应类型的示例问题。
  function triggerAction(action) {
    if (requestPending) return;
    const questions = {
      policy: '工程设计变更有哪些主要制度要求？',
      database: '我可以查看哪些项目？',
      audit: '请审查当前权限范围内的设计变更是否合规。'
    };
    const question = questions[action];
    if (!question) return;
    appendUserMessage(question);
    lastUserQuestion = question;
    requestToken += 1;
    requestPending = true;
    setRequestState(true);
    showTyping(getServiceName(question));
    sendToStreamlit(question, requestToken);
  }

  // 追加用户消息
  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'chat-bubble-row user';
    row.innerHTML = `
      <div class="msg-bubble">
        <p>${escapeHtml(text)}</p>
      </div>
    `;
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  // 追加 AI 消息
  function appendAIMessage(markdownText, sourceQuestion = '') {
    const row = document.createElement('div');
    row.className = 'chat-bubble-row ai';
    row.innerHTML = `
      <div class="msg-bubble">
        ${formatMarkdown(markdownText)}
      </div>
    `;
    if (!sourceQuestion) {
      chatScrollArea.appendChild(row);
      scrollToBottom();
      return;
    }

    chatScrollArea.querySelectorAll('.regenerate-message-btn').forEach(button => {
      button.remove();
    });

    const actions = document.createElement('div');
    actions.className = 'message-actions';
    const copyButton = document.createElement('button');
    copyButton.className = 'message-action-btn copy-message-btn';
    copyButton.title = '复制回答';
    copyButton.setAttribute('aria-label', '复制回答');
    copyButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="12" rx="2"></rect><path d="M5 16V5a2 2 0 0 1 2-2h8"></path></svg>';
    copyButton.addEventListener('click', async () => {
      await navigator.clipboard.writeText(markdownText);
      copyButton.classList.add('copied');
      copyButton.title = '已复制';
      setTimeout(() => {
        copyButton.classList.remove('copied');
        copyButton.title = '复制回答';
      }, 1200);
    });
    const regenerateButton = document.createElement('button');
    regenerateButton.className = 'message-action-btn regenerate-message-btn';
    regenerateButton.title = '重新回答';
    regenerateButton.setAttribute('aria-label', '重新回答');
    regenerateButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.34 5.66"></path><path d="M20 4v7h-7"></path></svg>';
    regenerateButton.addEventListener('click', () => {
      row.remove();
      regenerateAnswer(sourceQuestion);
    });
    actions.append(copyButton, regenerateButton);
    row.appendChild(actions);
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  // 打字中动效
  // 主要作用：显示回答生成期间的查询状态。
  function showTyping(serviceName) {
    hideTyping();
    const row = document.createElement('div');
    row.id = 'typingRow';
    row.className = 'chat-bubble-row ai';
    row.innerHTML = `
      <div class="msg-bubble typing-bubble">
        <div class="typing-text">正在查询中，请稍等……</div>
        <div class="typing-service">
          <span>${serviceName}</span>
          <span class="typing-dots" aria-label="处理中">
            <i></i><i></i><i></i>
          </span>
        </div>
      </div>
    `;
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  function hideTyping() {
    const el = document.getElementById('typingRow');
    if (el) el.remove();
  }

  function scrollToBottom() {
    chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
  }

  // 简易 Markdown 转化
  function formatMarkdown(text) {
    const normalized = String(text)
      .replace(/\\n/g, '\n')
      .replace(/\\\|/g, '|');
    const lines = normalized.split('\n');
    const output = [];
    let index = 0;

    while (index < lines.length) {
      const header = lines[index].trim();
      const separator = lines[index + 1] ? lines[index + 1].trim() : '';
      if (header.startsWith('|') && separator.startsWith('|') && /^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(separator)) {
        const parseRow = value => value.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
        const headers = parseRow(header);
        const rows = [];
        index += 2;
        while (index < lines.length && lines[index].trim().startsWith('|')) {
          rows.push(parseRow(lines[index]));
          index += 1;
        }
        output.push(`<table><thead><tr>${headers.map(cell => `<th>${cell}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${headers.map((_, cellIndex) => `<td>${row[cellIndex] || ''}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
        continue;
      }
      output.push(lines[index]);
      index += 1;
    }

    return output.join('\n')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\n\n/gim, '<br><br>');
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  window.addEventListener('message', receiveFromStreamlit);
  window.addEventListener('DOMContentLoaded', () => {
    init();
    renderReferenceFiles([]);
    updateWeather({ city: '深圳', temperature: 26, weather_code: 1, is_day: 1 });
    loadLocationWeather();
    window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:componentReady', apiVersion: 1 }, '*');
    window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: window.innerHeight }, '*');
  });
})();

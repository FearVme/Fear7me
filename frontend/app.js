/**
 * 工程设计变更智能问答 (app.js)
 * 纯对话模式：首页 A/B/C 三种角色权限选择，进入后全部以对话交互完成，无需写入修改文件
 */

(function () {
  // 当前角色状态与权限定义
  let currentRole = 'A';
  let activeIndex = 0;
  let bgSlideIndex = 0;
  let bgTimer = null;

  const ROLE_CONFIG = {
    A: {
      code: 'A',
      name: '角色 A · 审计监察',
      duty: '穿透核查权限',
      avatar: '🛡️',
      desc: '合规审查 · 违规穿透 · 纪检问责',
      welcome: '您好！已为您开启**角色 A · 审计监察（穿透核查权限）**问答对话。\n\n重点针对全盘在建工程项目的变更金额加总一致性、超400万单项与超5%累计公示合规性、非应急“未批先建”及违规拆分规避审批等风险提供穿透式审查。请点击上方指令或直接提问。'
    },
    B: {
      code: 'B',
      name: '角色 B · 工程管理',
      duty: '分级审批与方案合规权限',
      avatar: '📐',
      desc: '分级审批 · 专家论证 · 单据闭环',
      welcome: '您好！已为您开启**角色 B · 项目工程主管（分级审批与方案合规权限）**问答对话。\n\n重点协助把关单项超200万元专家论证组织闭环、现场工程量确认时效（14天内办理）及工程技术委员会报审流程。请点击上方指令或直接提问。'
    },
    C: {
      code: 'C',
      name: '角色 C · 集团决策',
      duty: '投资宏观监管权限',
      avatar: '🏛️',
      desc: '投资控制 · 阳光公示 · 宏观决策',
      welcome: '您好！已为您开启**角色 C · 集团决策层（投资宏观监管权限）**问答对话。\n\n重点针对8大在建工程项目累计变更率监控、超合同额5%阳光采购平台对外公示督办及重大投资风险提供宏观决策分析。'
    }
  };

  // DOM 元素引用
  const refFilesBtn = document.getElementById('refFilesBtn');
  const refFilesModal = document.getElementById('refFilesModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const referenceFilesBody = document.getElementById('referenceFilesBody');
  const weatherWidgets = document.querySelectorAll('.weather-widget');
  const weatherEffects = document.querySelectorAll('.weather-atmosphere');
  const geminiChatModal = document.getElementById('geminiChatModal');
  const closeChatModalBtn = document.getElementById('closeChatModalBtn');
  const chatScrollArea = document.getElementById('chatScrollArea');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const slidingIndicator = document.getElementById('slidingIndicator');
  const slidingNavTrack = document.getElementById('slidingNavTrack');
  const bottomLeftBadge = document.getElementById('bottomLeftRoleBadge');
  const roleBadgeCircle = document.getElementById('roleBadgeCircle');
  const rolePopupStack = document.getElementById('rolePopupStack');

  // 初始化绑定
  function init() {
    // 1. 初始化全屏三图平滑轮播
    initBackgroundCarousel();

    // 2. 初始化磁吸滑轨位置
    setTimeout(() => {
      updateSlidingIndicator(0);
    }, 100);

    window.addEventListener('resize', () => {
      updateSlidingIndicator(activeIndex);
    });

    // 3. 磁吸导轨项点击与滑过联动
    const navItems = document.querySelectorAll('.sliding-nav-item');
    navItems.forEach(item => {
      const idx = parseInt(item.getAttribute('data-index'), 10);
      const role = item.getAttribute('data-role');

      item.addEventListener('mouseenter', () => {
        updateSlidingIndicator(idx);
      });

      item.addEventListener('click', () => {
        openGeminiChat(role);
      });
    });

    // 4. 首页角色权限卡片点击与滑过联动
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

    // 5. 点击右上角感叹号：弹窗展示全部参考文件
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

    // 6. 关闭 Gemini 提问居中弹出框
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

    // 7. 左下角角色圆圈点击：向上弹出 ABC 三个角色的按钮（不覆盖页面）
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

    // 8. 输入框与发送消息
    sendBtn.addEventListener('click', handleSend);
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        handleSend();
      }
    });

    // 9. 5大核心审计快捷操作按钮 + 知识问答
    document.querySelectorAll('.g-pill').forEach(btn => {
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

  // 更新磁吸滑动条与联动卡片
  function updateSlidingIndicator(index) {
    activeIndex = index;
    const navItems = document.querySelectorAll('.sliding-nav-item');
    const targetItem = navItems[index];
    if (!targetItem || !slidingIndicator || !slidingNavTrack) return;

    const trackRect = slidingNavTrack.getBoundingClientRect();
    const itemRect = targetItem.getBoundingClientRect();
    const leftOffset = itemRect.left - trackRect.left;

    slidingIndicator.style.transform = `translateX(${leftOffset}px)`;
    slidingIndicator.style.width = `${itemRect.width}px`;

    navItems.forEach((it, i) => it.classList.toggle('active', i === index));

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

  // 在对话框内部切换角色权限视角
  function switchRoleInChat(role) {
    currentRole = role;
    const config = ROLE_CONFIG[role] || ROLE_CONFIG.A;

    updateRoleBadgeUI(role);
    sendToStreamlit(role);
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
    const text = chatInput.value.trim();
    if (!text) return;
    appendUserMessage(text);
    chatInput.value = '';

    sendToStreamlit(text);
  }

  function sendToStreamlit(text) {
    window.parent.postMessage({
      isStreamlitMessage: true,
      type: 'streamlit:setComponentValue',
      value: { role: currentRole, message: text }
    }, '*');
  }

  function receiveFromStreamlit(event) {
    if (!event.data || event.data.type !== 'streamlit:render') return;
    const args = event.data.args || {};
    if (args.weather) {
      updateWeather(args.weather);
    }
    if (Array.isArray(args.reference_files)) {
      renderReferenceFiles(args.reference_files);
    }
    if (args.role && args.role !== currentRole) {
      currentRole = args.role;
      updateRoleBadgeUI(currentRole);
    }
    if (args.response) {
      hideTyping();
      appendAIMessage(args.response);
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
    weatherEffects.forEach(effect => {
      effect.dataset.condition = presentation.condition;
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
        const meta = document.createElement('span');
        meta.className = 'file-size';
        meta.textContent = `${formatFileSize(file.size)} · 仓库文件`;
        row.append(left, meta);
        list.appendChild(row);
      });
      section.appendChild(list);
      referenceFilesBody.appendChild(section);
    });
  }

  // 路由用户问题
  function routeQuery(text) {
    const q = text.toLowerCase();

    if (q.includes('1') || q.includes('累计') || q.includes('金额') || q.includes('错误') || q.includes('算错')) {
      auditQuestion1();
    } else if (q.includes('2') || q.includes('阳光') || q.includes('公示') || q.includes('公开')) {
      auditQuestion2();
    } else if (q.includes('3') || q.includes('技术委员会') || q.includes('委员会') || q.includes('评审') || q.includes('退回')) {
      auditQuestion3();
    } else if (q.includes('4') || q.includes('审批流程') || q.includes('分级') || q.includes('权限') || q.includes('拆分') || q.includes('400万')) {
      auditQuestion4();
    } else if (q.includes('5') || q.includes('冲突') || q.includes('未批先建') || q.includes('专家论证') || q.includes('违规')) {
      auditQuestion5();
    } else {
      knowledgeQA(text);
    }
  }

  // 快捷操作指令触发 (纯对话模式)
  function triggerAction(action) {
    const questions = {
      '1': '变更金额累计是否错误？',
      '2': '是否按照要求在阳光平台公示？',
      '3': '是否走了工程技术委员会审批？',
      '4': '审批流程是否正确？',
      '5': '其他和制度冲突的部分有哪些？',
      'qa': '请说明重大设计变更的划分标准与审批要求是什么？'
    };
    const question = questions[action];
    if (!question) return;
    appendUserMessage(question);
    sendToStreamlit(question);
  }

  // ================= 5 大审计功能 (全部以对话形式输出结论) =================

  // 1、变更金额累计是否错误
  function auditQuestion1() {
    const reply = `
### 审计结论 1：变更金额累计是否错误

根据《管理办法》第七条及附图《审批流程图》，对 8 个工程项目共 80 笔台账逐笔验算：

* **加总核算结论**：**无计算错误（0 处误差）**，累计公式完全吻合。
* **超 5% 重点预警项目（3 个）**：

<table>
  <thead>
    <tr>
      <th>项目名称</th>
      <th>合同总额</th>
      <th>累计变更</th>
      <th>预警占比</th>
      <th>状态</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>临港能源站项目</strong></td>
      <td>27,400 万元</td>
      <td>2,255.00 万元</td>
      <td>8.23% <span class="audit-progress-bar"><span class="audit-progress-fill fill-red" style="width:82%;"></span></span></td>
      <td><span class="tag-risk red">严重超标</span></td>
    </tr>
    <tr>
      <td><strong>东部污水处理厂提标</strong></td>
      <td>32,800 万元</td>
      <td>1,925.00 万元</td>
      <td>5.87% <span class="audit-progress-bar"><span class="audit-progress-fill fill-red" style="width:58%;"></span></span></td>
      <td><span class="tag-risk red">已超5%</span></td>
    </tr>
    <tr>
      <td><strong>北部快速路改造项目</strong></td>
      <td>43,200 万元</td>
      <td>2,390.00 万元</td>
      <td>5.53% <span class="audit-progress-bar"><span class="audit-progress-fill fill-red" style="width:55%;"></span></span></td>
      <td><span class="tag-risk red">已超5%</span></td>
    </tr>
    <tr>
      <td>城市更新安置房项目</td>
      <td>68,900 万元</td>
      <td>2,423.00 万元</td>
      <td>3.52% <span class="audit-progress-bar"><span class="audit-progress-fill fill-green" style="width:35%;"></span></span></td>
      <td><span class="tag-risk green">在控</span></td>
    </tr>
    <tr>
      <td>西江综合管廊项目</td>
      <td>61,200 万元</td>
      <td>2,079.00 万元</td>
      <td>3.40% <span class="audit-progress-bar"><span class="audit-progress-fill fill-green" style="width:34%;"></span></span></td>
      <td><span class="tag-risk green">在控</span></td>
    </tr>
  </tbody>
</table>
    `;
    appendAIMessage(reply);
  }

  // 2、是否按照要求在阳光平台公示
  function auditQuestion2() {
    const reply = `
### 审计结论 2：是否按照要求在阳光平台公示

依据《管理办法》**第十六条【信息公示】**：
> *单项变更超 400 万元及累计超合同额 5% 以上的设计变更须在阳光采购平台对外公示（2024年6月24日起）。*

**数据表关联核查结果**：
1. **单项超 400 万元公示**：80 笔变更单项最高为 385 万元，**全部压在 400 万元以下**（存在故意避开单项公示倾向）；
2. **累计超 5% 公示核对**：超 5% 的 6 笔记录在台账中均填报为**“是”**；
3. **审计核查重点**：应查验平台公开挂牌凭证与发布时间戳，核实是否存在“事后突击补登”。
    `;
    appendAIMessage(reply);
  }

  // 3、是否走了工程技术委员会审批
  function auditQuestion3() {
    const reply = `
### 审计结论 3：是否走了工程技术委员会审批

依据《管理办法》第九条及《工作规则》第二条：
> *A类（≥1000万）、B类（400~1000万）重大变更决策前必须报工程技术委员会技术评审，监督委员会全程列席。*

**穿透发现（严重违规事实）**：
1. **申报情况**：8 个在建工程项目均有向委员会申报的记录；
2. **重大违规（被退回仍擅自施工）**：
   * ❌ **南区水厂二期 EPC 项目**（申报议题《机电预留预埋调整》，77万元）：在工程技术委员会评审中被明确决议 **【退回】**；
   * 🚨 **违规事实**：变更台账明确注明*“施工单位已先行实施，变更审批后补（现场已于 2026-01-22 开工）”*，属于未获批准擅自施工的顶风违规行为！
    `;
    appendAIMessage(reply);
  }

  // 4、审批流程是否正确
  function auditQuestion4() {
    const reply = `
### 审计结论 4：审批流程是否正确

依据《管理办法》第十条分级审批矩阵：
* **A 类（≥1000万）**：技术委员会 → 分管领导 → 党委会 → 总裁办公会
* **B 类（400~1000万）**：技术委员会 → 分管领导 → 总裁审批
* **C 类（200~400万）**：集团分管领导审批（必须附专家论证）
* **D 类（50~200万）**：集团分管领导审批
* **E 类（5~50万）**：部门主要负责人审批

**数据表穿透发现（疑似化整为零规避审批）**：
* 80 笔变更中，C 类共 43 笔，D 类共 37 笔，**无一笔超 400 万元**；
* 最高单项金额精准卡在 **385万、378万、371万**，疑似故意拆分单项金额以规避上报总裁审批及委员会强审（触犯制度第四条与第二十条追责红线）。
    `;
    appendAIMessage(reply);
  }

  // 5、其他和制度冲突的部分
  function auditQuestion5() {
    const reply = `
### 审计结论 5：其他和制度冲突的部分

对比制度切片与数据表明细，还排查出两项严重违规冲突：

#### 冲突一：严重违反“先批后建”原则（33 笔）
* **制度红线**：第四条规定严禁未批先建，仅在抢险特殊情况下允许口头报告并在 10 日内补办手续。
* **数据核查**：共有 **33 笔变更** 明确标注为“非应急”，但现场已实际开工施工，属于违规未批先建！

#### 冲突二：超200万专家论证大面积缺失（37 笔）
* **制度红线**：第七条、第十条明确规定超 200 万元变更必须组织专家论证并出具附件6咨询意见表。
* **数据核查**：43 笔超 200 万元变更中，有 **37 笔记录为“未组织专家论证”**，技术论证程序大面积落空。
    `;
    appendAIMessage(reply);
  }

  // 制度切片知识问答
  function knowledgeQA(query) {
    let answer = `### 制度依据解答\n\n针对您咨询的问题，为您检索到以下制度条款核心依据：\n\n`;
    answer += `#### 《K公司工程设计变更管理办法》第七条（重大设计变更划分）\n`;
    answer += `> 单项或一次性变更造价在 200 万元以上的设计变更属于重大设计变更。划分为 A 类（1000万元以上）、B 类（400~1000万元）、C 类（200~400万元）。\n\n`;
    answer += `#### 《K公司工程设计变更管理办法》第十六条（阳光采购平台公示）\n`;
    answer += `> 变更金额 400 万元以上的重大设计变更和累计变更金额超合同价 5% 以上的设计变更须在阳光采购平台对外公示（2024年6月24日起）。\n\n`;
    answer += `您可以直接点击上方指令按钮对数据表进行对应维度的穿透核验。`;
    appendAIMessage(answer);
  }

  // 追加用户消息
  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'chat-bubble-row user';
    row.innerHTML = `
      <div class="msg-avatar">👤</div>
      <div class="msg-bubble">
        <p>${escapeHtml(text)}</p>
      </div>
    `;
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  // 追加 AI 消息
  function appendAIMessage(markdownText) {
    const row = document.createElement('div');
    row.className = 'chat-bubble-row ai';
    row.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-bubble">
        ${formatMarkdown(markdownText)}
      </div>
    `;
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  // 打字中动效
  function showTyping() {
    const row = document.createElement('div');
    row.id = 'typingRow';
    row.className = 'chat-bubble-row ai';
    row.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-bubble typing-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
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
    return text
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
    window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:componentReady', apiVersion: 1 }, '*');
    window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: window.innerHeight }, '*');
  });
})();

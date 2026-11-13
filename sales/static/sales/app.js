const profiles = {
  funcionario: { name: "Bianca Rocha", first: "Bianca", initials: "BR", role: "Funcionária" },
  supervisor: { name: "Patrícia Lemos", first: "Patrícia", initials: "PL", role: "Gerente regional" },
  gerente: { name: "Diego Furtado", first: "Diego", initials: "DF", role: "Gerente de loja" },
  administrador: { name: "Marcos Albuquerque", first: "Marcos", initials: "MA", role: "Diretoria" },
};

const stages = [
  { id: "observe", title: "Observar e preparar", summary: "Leia o contexto disponível sem tirar conclusões precipitadas.", prompt: "Como posso me preparar e iniciar essa conversa sem presumir o que o cliente precisa?" },
  { id: "investigate", title: "Investigar com SPIN", summary: "Explore situação, problema, implicações e necessidade de solução.", prompt: "Sugira perguntas abertas SPIN para entender melhor a necessidade deste cliente." },
  { id: "classify", title: "Classificar o momento", summary: "Use sinais observáveis como hipóteses, não como rótulos fixos.", prompt: "Que sinais podem indicar o momento de compra do cliente e como confirmar minhas hipóteses?" },
  { id: "personalize", title: "Personalizar a abordagem", summary: "Adapte opções, ritmo e evidências às prioridades que o cliente confirmou.", prompt: "Como posso adaptar minha abordagem às prioridades que o cliente mencionou?" },
  { id: "value", title: "Construir valor", summary: "Conecte benefícios à necessidade real sem promessas exageradas.", prompt: "Como apresentar o valor desta solução de forma clara e sem pressionar?" },
  { id: "decision", title: "Conduzir a decisão", summary: "Investigue objeções e combine próximos passos com transparência.", prompt: "Como posso responder a uma objeção de preço sem pressionar o cliente?" },
  { id: "learn", title: "Aprender e acompanhar", summary: "Registre o resultado e planeje um pós-venda útil.", prompt: "Que acompanhamento pós-venda seria útil neste caso?" },
];

const state = {
  role: "funcionario",
  page: "inicio",
  conversations: [],
  activeConversationId: null,
  activeSaleId: null,
  activeStage: "general",
  messages: [],
  sales: [],
  alerts: [],
  people: [],
  selectedEmployee: null,
  products: [],
  specializations: [],
  webAvailable: false,
  sending: false,
};

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const roleSelect = document.getElementById("roleSelect");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

async function api(path, options = {}) {
  const headers = { "X-Demo-Role": state.role, ...options.headers };
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;
  const body = await response.text();
  let data;
  try {
    data = body ? JSON.parse(body) : {};
  } catch {
    const title = body.match(/<title[^>]*>(.*?)<\/title>/i)?.[1]?.trim();
    const detail = response.status >= 500
      ? "O Django retornou um erro interno. Consulte o traceback no terminal onde o servidor está rodando."
      : response.status === 404
        ? "A rota da API não foi encontrada. Reinicie o servidor Django para carregar as rotas atuais."
        : "O servidor respondeu com uma página HTML em vez de JSON.";
    throw new Error(`${detail} (HTTP ${response.status}${title ? ` · ${title}` : ""})`);
  }
  if (!response.ok) throw new Error(data.detail || "Não foi possível concluir a solicitação.");
  return data;
}

function notify(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function updateAlertBadge() {
  const unread = state.alerts.filter((alert) => !alert.read_at).length;
  const count = document.getElementById("alertCount");
  const dot = document.getElementById("alertDot");
  count.textContent = unread > 9 ? "9+" : String(unread);
  count.classList.toggle("hidden", unread === 0);
  dot.classList.toggle("hidden", unread > 0);
}

function setProfile() {
  const profile = profiles[state.role];
  document.getElementById("topAvatar").textContent = profile.initials;
  document.getElementById("welcomeTitle").innerHTML = `Bom dia, ${escapeHtml(profile.first)}.<br />O que você quer <span class="welcome-accent">descobrir?</span>`;
  document.querySelector(".manager-only").classList.toggle("hidden", state.role !== "gerente" || Boolean(state.selectedEmployee));
  if (state.role === "gerente" && state.page === "especializacao") renderPage("especializacao");
  if (state.role !== "gerente" && state.page === "especializacao") navigate("inicio");
}

function updateChatContext() {
  const context = document.getElementById("chatContext");
  const stage = stages.find((item) => item.id === state.activeStage);
  const chat = state.conversations.find((item) => item.id === state.activeConversationId);
  const title = chat?.sale_label || (state.activeSaleId ? `Venda #${state.activeSaleId}` : "Conversa geral");
  document.getElementById("contextTitle").textContent = title;
  document.getElementById("stageSelect").value = state.activeStage;
  context.classList.toggle("hidden", !state.activeConversationId && !state.activeSaleId);
  document.getElementById("floatingTitle").textContent = title;
  document.getElementById("floatingStage").textContent = stage?.title || chat?.stage_label || "Conversa em andamento";
}

function renderConversationHistory() {
  const list = document.getElementById("conversationList");
  if (!state.conversations.length) {
    list.innerHTML = '<p class="quiet">Ainda não há conversas. Faça uma pergunta para começar.</p>';
    return;
  }
  const groups = new Map();
  state.conversations.forEach((chat) => {
    const key = chat.sale_id ? `sale-${chat.sale_id}` : "general";
    if (!groups.has(key)) groups.set(key, { label: chat.sale_label, chats: [] });
    groups.get(key).chats.push(chat);
  });
  list.innerHTML = [...groups.values()].map((group) => `
    <div class="conversation-group"><p class="conversation-group-label">${escapeHtml(group.label)}</p>
      ${group.chats.map((chat, index) => `
        <button class="conversation-item ${chat.id === state.activeConversationId ? "active" : ""}" data-conversation-id="${chat.id}">
          <span class="conversation-icon" aria-hidden="true">${chat.sale_id ? "▥" : ["✦", "▥", "◆", "♟", "▤"][index % 5]}</span>
          <span class="conversation-copy"><strong>${escapeHtml(chat.title)}</strong>
          <small>${escapeHtml(chat.stage_label)}</small></span>
          <span class="conversation-chevron" aria-hidden="true">›</span>
        </button>`).join("")}
    </div>`).join("");
}

function renderMessage(message, appendTo) {
  const row = document.createElement("article");
  row.className = `message-row ${message.role === "user" ? "user" : "assistant"}`;
  if (message.role !== "user") {
    const avatar = document.createElement("span");
    avatar.className = "message-avatar";
    avatar.textContent = "✦";
    row.append(avatar);
  }
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = message.content;
  row.append(bubble);
  appendTo.append(row);

  if (message.role !== "user" && message.evidence?.items?.length) {
    const card = document.createElement("section");
    card.className = "message-evidence";
    const heading = document.createElement("div");
    heading.className = "message-evidence-heading";
    const title = document.createElement("strong");
    title.textContent = message.evidence.title || "Indicadores relacionados";
    const period = document.createElement("span");
    period.textContent = message.evidence.period || "";
    heading.append(title, period);
    const grid = document.createElement("div");
    grid.className = "message-evidence-grid";
    message.evidence.items.forEach((item) => {
      const metric = document.createElement("div");
      metric.className = "message-evidence-metric";
      const label = document.createElement("span");
      label.textContent = item.label;
      const value = document.createElement("strong");
      value.textContent = item.value;
      metric.append(label, value);
      if (item.detail) {
        const detail = document.createElement("small");
        detail.textContent = item.detail;
        metric.append(detail);
      }
      grid.append(metric);
    });
    card.append(heading, grid);
    if (message.evidence.people?.length) {
      const peopleHeading = document.createElement("strong");
      peopleHeading.className = "message-evidence-people-title";
      peopleHeading.textContent = message.evidence.people_title || "Pessoas no recorte";
      card.append(peopleHeading);
      message.evidence.people.forEach((person) => {
        const personRow = document.createElement("div");
        personRow.className = "message-evidence-person";
        const description = document.createElement("span");
        const goalLabel = person.goal_progress === "Sem meta" ? "sem meta individual" : `${person.goal_progress} da meta`;
        description.textContent = `${person.name} · ${person.team} · ${person.revenue} · ${goalLabel} · ${person.conversion} (${person.orders}/${person.attendances} atendimentos)`;
        const open = document.createElement("button");
        open.type = "button";
        open.textContent = "Abrir painel";
        open.addEventListener("click", async () => {
          const employee = state.people.find((candidate) => candidate.id === person.id) || person;
          selectEmployee(employee);
          navigate("indicadores");
          await refreshData();
          if (state.activeConversationId) openFloating(true);
        });
        personRow.append(description, open);
        card.append(personRow);
      });
    }
    if (message.evidence.signal) {
      const signal = document.createElement("p");
      signal.className = "message-evidence-signal";
      signal.textContent = message.evidence.signal;
      card.append(signal);
    }
    appendTo.append(card);
  }

  if (message.role !== "user" && message.sources?.length) {
    const sources = document.createElement("div");
    sources.className = "message-sources";
    message.sources.forEach((source) => {
      try {
        const url = new URL(source.url);
        if (url.protocol !== "https:") return;
        const link = document.createElement("a");
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = `Fonte · ${source.title || url.hostname}`;
        sources.append(link);
      } catch { /* Ignore malformed external citations. */ }
    });
    if (sources.childElementCount) appendTo.append(sources);
  }
  if (message.role !== "user" && message.links?.length) {
    const links = document.createElement("div");
    links.className = "message-sources app-links";
    message.links.forEach((destination) => {
      const button = document.createElement("button");
      button.className = "app-link-button";
      button.textContent = `↗ ${destination.label}`;
      button.addEventListener("click", async () => {
        if (destination.employee_id) {
          selectEmployee(state.people.find((person) => person.id === destination.employee_id) || { id: destination.employee_id, name: destination.label.replace("Ver desempenho de ", "") });
        }
        navigate(destination.page);
        if (destination.employee_id) await refreshData();
        if (state.activeConversationId) openFloating(true);
        if (destination.sale_id) {
          window.setTimeout(() => {
            const target = document.getElementById(`sale-row-${destination.sale_id}`);
            target?.scrollIntoView({ behavior: "smooth", block: "center" });
            target?.classList.add("highlight-row");
            window.setTimeout(() => target?.classList.remove("highlight-row"), 1800);
          }, 120);
        }
      });
      links.append(button);
    });
    if (links.childElementCount) appendTo.append(links);
  }
  if (message.role !== "user" && message.source) {
    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = `Resposta baseada em: ${message.source}`;
    appendTo.append(meta);
  }
  if (message.role !== "user" && message.id) {
    const feedback = document.createElement("div");
    feedback.className = "assistant-feedback";
    if (message.feedback?.rating) {
      feedback.textContent = message.feedback.rating === "helpful" ? "Obrigado pela avaliação." : "Obrigado. Vamos revisar esta resposta.";
    } else {
      feedback.innerHTML = '<span>Esta resposta ajudou?</span><button type="button" aria-label="Ajudou" title="Ajudou">👍</button><button type="button" aria-label="Não ajudou" title="Não ajudou">👎</button>';
      feedback.querySelectorAll("button").forEach((button) => button.addEventListener("click", async () => {
        const rating = button.getAttribute("aria-label") === "Ajudou" ? "helpful" : "not_helpful";
        let reason = "";
        if (rating === "not_helpful") reason = window.prompt("O que faltou ou ficou incorreto? (opcional)") || "";
        try {
          await api(`/api/assistant/messages/${message.id}/feedback/`, {
            method: "POST", body: JSON.stringify({ rating, reason }),
          });
          message.feedback = { rating, reason };
          renderMessages();
        } catch (error) { notify(error.message); }
      }));
    }
    appendTo.append(feedback);
  }
}

function renderMessages() {
  const homeList = document.getElementById("messageList");
  homeList.replaceChildren();
  if (!state.messages.length) {
    homeList.innerHTML = `
      <div class="welcome-chat" id="welcomeChat">
        <span class="assistant-orb">✦</span>
        <h2>Assistente comercial</h2>
        <p>Pergunte sobre suas metas, uma venda ou como adaptar sua abordagem ao cliente.</p>
        <div class="suggestion-list">
          <button data-prompt="Quanto falta para eu alcançar minha meta?"><span>↗</span>Quanto falta para minha meta?</button>
          <button data-prompt="Sugira perguntas SPIN para entender a necessidade do cliente."><span>⌕</span>Me ajude a entender o cliente</button>
          <button data-prompt="Como apresentar valor sem pressionar o cliente?"><span>✦</span>Como conduzir uma venda?</button>
        </div>
      </div>`;
  } else {
    state.messages.forEach((message) => renderMessage(message, homeList));
    homeList.scrollTop = homeList.scrollHeight;
  }

  const floatingMessages = document.getElementById("floatingMessages");
  floatingMessages.replaceChildren();
  state.messages.forEach((message) => renderMessage(message, floatingMessages));
  floatingMessages.scrollTop = floatingMessages.scrollHeight;
  updateChatContext();
}

async function loadHistory() {
  try {
    state.conversations = await api("/api/conversations/");
    renderConversationHistory();
  } catch (error) {
    notify(error.message);
  }
}

async function loadConversation(conversationId) {
  try {
    const chat = await api(`/api/conversations/${conversationId}/`);
    state.activeConversationId = chat.id;
    state.activeSaleId = chat.sale_id;
    state.activeStage = chat.stage;
    state.messages = chat.messages;
    renderConversationHistory();
    renderMessages();
  } catch (error) {
    notify(error.message);
  }
}

async function newConversation({ saleId = null, stage = "general", title = "Nova conversa" } = {}) {
  try {
    const chat = await api("/api/conversations/", {
      method: "POST",
      body: JSON.stringify({ sale_id: saleId, stage, title }),
    });
    state.activeConversationId = chat.id;
    state.activeSaleId = chat.sale_id;
    state.activeStage = chat.stage;
    state.messages = [];
    await loadHistory();
    renderMessages();
    return chat;
  } catch (error) {
    notify(error.message);
    return null;
  }
}

async function startSaleChat(saleId, stage = "observe") {
  const sale = state.sales.find((item) => item.id === Number(saleId));
  const chat = await newConversation({
    saleId: Number(saleId),
    stage,
    title: sale ? `Resumo diário · ${sale.sold_at}` : `Resumo diário #${saleId}`,
  });
  if (chat) {
    navigate("inicio");
    openFloating(false);
    const suggestion = stages.find((item) => item.id === stage);
    if (suggestion) document.getElementById("assistantQuestion").placeholder = `Converse sobre ${suggestion.title.toLowerCase()}…`;
  }
}

function selectConversationFromHistory(event) {
  const button = event.target.closest("[data-conversation-id]");
  if (button) loadConversation(Number(button.dataset.conversationId));
}

async function sendQuestion(question, fromFloating = false) {
  const text = question.trim();
  if (!text || state.sending) return;
  if (!state.activeConversationId) {
    const created = await newConversation({ saleId: state.activeSaleId, stage: state.activeStage });
    if (!created) return;
  }
  state.messages.push({ role: "user", content: text });
  renderMessages();
  const input = document.getElementById(fromFloating ? "floatingQuestion" : "assistantQuestion");
  input.value = "";
  state.sending = true;
  const sendButtons = document.querySelectorAll(".send-button, .floating-composer button");
  sendButtons.forEach((button) => { button.disabled = true; });
  try {
    const response = await api("/api/assistant/", {
      method: "POST",
      body: JSON.stringify({
        question: text,
        conversation_id: state.activeConversationId,
        sale_id: state.activeSaleId,
        employee_id: state.selectedEmployee?.id || null,
        stage: state.activeStage,
      }),
    });
    state.activeConversationId = response.conversation_id;
    state.activeSaleId = response.sale_id ?? null;
    state.activeStage = response.stage;
    state.messages.push({
      id: response.message_id,
      role: "assistant",
      content: response.answer,
      sources: response.sources || [],
      evidence: response.evidence || null,
      source: response.source,
      links: response.links || [],
      used_web_search: response.used_web_search,
    });
    await loadHistory();
  } catch (error) {
    state.messages.push({ role: "assistant", content: error.message });
  } finally {
    state.sending = false;
    sendButtons.forEach((button) => { button.disabled = false; });
    renderMessages();
    if (fromFloating) openFloating(true);
  }
}

function navigate(page) {
  if (page === "especializacao" && (state.role !== "gerente" || state.selectedEmployee)) {
    notify("A especialização de produtos está disponível no perfil gerente.");
    return;
  }
  state.page = page;
  const onHome = page === "inicio";
  document.getElementById("homeView").classList.toggle("hidden", !onHome);
  document.getElementById("pageView").classList.toggle("hidden", onHome);
  document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.page === page));
  if (!onHome) {
    renderPage(page);
    document.getElementById("floatingChatTrigger").classList.toggle("hidden", !state.activeConversationId);
    if (!document.getElementById("floatingChat").classList.contains("hidden")) renderMessages();
  } else {
    document.getElementById("floatingChat").classList.add("hidden");
    document.getElementById("floatingChatTrigger").classList.add("hidden");
    renderMessages();
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function pageHeader(title, description) {
  const personView = state.selectedEmployee && ["gerente", "administrador"].includes(state.role)
    ? `<div class="viewing-person"><span>VISÃO INDIVIDUAL</span><strong>${escapeHtml(state.selectedEmployee.name)}</strong><button type="button" data-clear-employee>Voltar para equipe</button></div>`
    : "";
  return `<header class="page-heading"><div><p class="eyebrow">DASHALISE · ESPAÇO COMERCIAL</p><h1 class="page-title">${escapeHtml(title)}</h1><p class="page-description">${escapeHtml(description)}</p></div>${personView}</header>`;
}

function renderSalesPage() {
  const rows = state.sales.map((sale) => `
    <tr id="sale-row-${sale.id}">
      <td><strong>${escapeHtml(sale.seller_name)}</strong><small class="cell-subtitle">${escapeHtml(sale.team_name || "Equipe")}</small></td>
      <td>Resumo diário agregado</td>
      <td><strong>${money.format(Number(sale.amount))}</strong></td>
      <td>${new Date(`${sale.sold_at}T12:00:00`).toLocaleDateString("pt-BR")}</td>
      <td>${sale.sales_count} vendas · ${sale.pieces} peças · ${sale.attendances} atendimentos</td>
      <td><button class="table-action" data-sale-chat="${sale.id}">Consultar este resumo ↗</button></td>
      <td><div class="reflection-cell">${sale.reflections?.length ? `<strong>${escapeHtml(sale.reflections[0].stage_label)}</strong><small>${escapeHtml(sale.reflections[0].challenge)}</small>` : '<small>Nenhum relato registrado</small>'}<button class="table-action" data-reflection-sale="${sale.id}">${sale.reflections?.length ? "Adicionar aprendizado" : "Registrar dificuldade"}</button></div></td>
    </tr>`).join("");
  return `${pageHeader("Vendas", state.selectedEmployee ? `Vendas individuais de ${state.selectedEmployee.name}. Abra um resumo diário para consultar o contexto disponível.` : "Consulte os resumos diários de receita, vendas, peças e atendimentos. O detalhe de cada transação não está disponível.")}
    <div class="metric-grid">
      <article class="metric-card"><span>Dias de trabalho exibidos</span><strong>${state.sales.length}</strong></article>
      <article class="metric-card"><span>Receita válida</span><strong>${money.format(Number(state.summary?.revenue || 0))}</strong></article>
      <article class="metric-card"><span>Meta do período</span><strong>${money.format(Number(state.summary?.goal || 0))}</strong></article>
      <article class="metric-card"><span>Comissão calculada</span><strong>${money.format(Number(state.summary?.commission || 0))}</strong></article>
    </div>
    <section class="panel"><header class="panel-heading"><div><h2>Resumos diários recentes</h2><p>Cada linha representa um vendedor em um dia de trabalho, como fornecido pelo desafio.</p></div><button class="button" id="salesExport">↓ Exportar CSV</button></header>
      <div class="table-scroll"><table><thead><tr><th>Vendedor / loja</th><th>Detalhe de produto</th><th>Receita no dia</th><th>Data</th><th>Atividade</th><th>Conversa</th><th>Aprendizado</th></tr></thead><tbody>${rows || '<tr><td colspan="7" class="empty-state">Não há vendas neste período.</td></tr>'}</tbody></table></div>
    </section>`;
}

function renderMetricsPage() {
  const summary = state.summary || {};
  return `${pageHeader("Metas e resultados", "Indicadores calculados no servidor a partir das vendas válidas.")}
    ${renderGoalProgress(summary)}
    <section class="panel"><header class="panel-heading"><div><h2>Comissões e critérios</h2><p>3% do valor vendido e prêmio de R$ 300 quando a meta mensal individual é atingida, conforme o briefing.</p></div></header>
      <div class="panel-body metric-grid metric-grid-three"><article class="metric-card"><span>Comissão acumulada</span><strong>${money.format(Number(summary.commission || 0))}</strong></article><article class="metric-card"><span>Pedidos válidos</span><strong>${summary.orders || 0}</strong></article><article class="metric-card"><span>Ticket médio</span><strong>${money.format(Number(summary.average_order_value || 0))}</strong></article></div>
    </section>`;
}

function renderGoalProgress(summary) {
  const goal = Number(summary.goal || 0);
  const revenue = Number(summary.revenue || 0);
  const remaining = Math.max(0, goal - revenue);
  const progress = goal > 0 ? Math.min(100, Math.max(0, revenue / goal * 100)) : 0;
  const reached = goal > 0 && revenue >= goal;
  const goalTitle = state.selectedEmployee ? `Meta de ${escapeHtml(state.selectedEmployee.name)}` : "Complete sua meta";
  return `<section class="goal-game panel ${reached ? "goal-complete" : ""}">
    <div class="goal-game-heading"><div><span class="goal-kicker">DESAFIO DO PERÍODO</span><h2>${reached ? "Meta concluída! 🎉" : goalTitle}</h2><p>${goal ? `${money.format(revenue)} de ${money.format(goal)} alcançados` : "Ainda não há uma meta cadastrada para este perfil."}</p></div><strong class="goal-percent">${percent.format(progress)}%</strong></div>
    <div class="goal-track" role="progressbar" aria-label="Progresso da meta de vendas" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress.toFixed(1)}"><span style="width:${progress}%"></span><i></i></div>
    <div class="goal-game-footer"><span>${goal ? (reached ? "🏆 Objetivo alcançado" : `Faltam <strong>${money.format(remaining)}</strong> para completar`) : "Adicione uma meta para acompanhar seu progresso"}</span><span>${goal ? `${money.format(goal)} · meta` : "—"}</span></div>
  </section>`;
}

function renderTrendChart(rows) {
  if (!rows?.length) return '<div class="chart-empty">Ainda não há vendas válidas neste período para desenhar o gráfico.</div>';
  const values = rows.map((row) => Number(row.amount || 0));
  const max = Math.max(...values, 1);
  const left = 42;
  const right = 690;
  const top = 18;
  const bottom = 175;
  const points = values.map((value, index) => {
    const x = values.length < 2 ? (left + right) / 2 : left + index * (right - left) / (values.length - 1);
    const y = bottom - (value / max) * (bottom - top);
    return { x, y, row: rows[index], value };
  });
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
  const grid = [0, .5, 1].map((ratio) => {
    const y = bottom - ratio * (bottom - top);
    return `<line class="chart-gridline" x1="${left}" y1="${y}" x2="${right}" y2="${y}"/><text class="chart-axis-label" x="0" y="${y + 4}">${money.format(max * ratio)}</text>`;
  }).join("");
  const labels = [0, Math.floor((points.length - 1) / 2), points.length - 1]
    .filter((index, position, all) => all.indexOf(index) === position)
    .map((index) => `<text class="chart-axis-label" x="${points[index].x}" y="198" text-anchor="middle">${new Date(`${points[index].row.sold_at}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}</text>`)
    .join("");
  return `<svg class="analytics-chart" viewBox="0 0 710 215" role="img" aria-label="Vendas diárias no período">${grid}<path class="chart-area" d="${path} L${points.at(-1).x} ${bottom} L${points[0].x} ${bottom} Z"/><path class="chart-line" d="${path}"/>${points.map((point) => `<circle class="chart-point" cx="${point.x}" cy="${point.y}" r="3.5"><title>${new Date(`${point.row.sold_at}T12:00:00`).toLocaleDateString("pt-BR")}: ${money.format(point.value)}</title></circle>`).join("")}${labels}</svg>`;
}

function renderIndicatorsPage() {
  const summary = state.summary || {};
  const topProducts = summary.top_products || [];
  const previousYear = summary.previous_year;
  const yearComparison = previousYear
    ? `<p>Na loja/região/rede visível, a receita foi ${money.format(Number(summary.revenue || 0))}; no período equivalente do ano anterior (mesmo dia da semana) foi ${money.format(Number(previousYear.revenue || 0))}${previousYear.change_percent === null ? ". Não há base anterior suficiente para calcular a variação." : `, variação de ${percent.format(Number(previousYear.change_percent))}%.`}</p>`
    : "";
  const maxProductRevenue = Math.max(...topProducts.map((product) => Number(product.amount || 0)), 1);
  const products = topProducts.map((product) => `<div class="product-bar-row"><div class="product-bar-label"><strong>${escapeHtml(product.product__name)}</strong><span>${money.format(Number(product.amount || 0))} · ${product.orders} pedidos</span></div><div class="product-bar-track"><i style="width:${Math.max(4, Number(product.amount || 0) / maxProductRevenue * 100)}%"></i></div></div>`).join("");
  const roleLabel = state.selectedEmployee ? "Funcionário" : profiles[state.role].role;
  return `${pageHeader("Indicadores comerciais", `Painel personalizado para ${roleLabel.toLowerCase()}, com dados limitados ao seu escopo.`)}
    ${renderGoalProgress(summary)}
    <div class="metric-grid">
      <article class="metric-card"><span>Vendas válidas</span><strong>${money.format(Number(summary.revenue || 0))}</strong></article>
      <article class="metric-card"><span>Comissão acumulada</span><strong>${money.format(Number(summary.commission || 0))}</strong></article>
      <article class="metric-card"><span>Pedidos válidos</span><strong>${Number(summary.orders || 0).toLocaleString("pt-BR")}</strong></article>
      <article class="metric-card"><span>Ticket médio</span><strong>${money.format(Number(summary.average_order_value || 0))}</strong></article>
    </div>
    <details class="secondary-metrics"><summary>Ver outros indicadores</summary><div class="metric-grid"><article class="metric-card"><span>Conversão (vendas ÷ atendimentos)</span><strong>${percent.format(Number(summary.conversion_rate_percent || 0))}%</strong></article><article class="metric-card"><span>Peças por venda (P.A.)</span><strong>${percent.format(Number(summary.pieces_per_sale || 0))}</strong></article><article class="metric-card"><span>Preço médio por peça</span><strong>${money.format(Number(summary.average_item_price || 0))}</strong></article><article class="metric-card"><span>Cancelamentos</span><strong>Sem registro no período</strong></article><article class="metric-card"><span>Projeção de fechamento</span><strong>${summary.closing_projection ? money.format(Number(summary.closing_projection)) : "—"}</strong></article><article class="metric-card"><span>Média diária no período</span><strong>${money.format(Number(summary.daily_average || 0))}</strong></article></div></details>
    <div class="analytics-grid">
    <section class="panel"><header class="panel-heading"><div><h2>Evolução das vendas</h2><p>Receita diária válida no período selecionado</p></div></header><div class="panel-body">${renderTrendChart(summary.sales_by_day || [])}</div></section>
      <section class="panel"><header class="panel-heading"><div><h2>Produtos por receita</h2><p>Vendas vinculadas a produtos, quando disponíveis.</p></div></header><div class="panel-body product-bars">${products || '<p class="empty-state">Ainda não há vendas vinculadas a produtos neste perfil. Consulte o cenário de apresentação na aba Produtos; ele fica separado destes indicadores.</p>'}</div></section>
    </div>
    <section class="panel insight-summary"><header class="panel-heading"><div><h2>Leitura dos indicadores</h2><p>Resumo objetivo para orientar a próxima consulta</p></div><button class="button" data-go="alertas">Ver alertas (${state.alerts.filter((alert) => !alert.read_at).length})</button></header><div class="panel-body"><p>${Number(summary.goal || 0) ? `${state.selectedEmployee ? `${escapeHtml(state.selectedEmployee.name)} está` : "O perfil selecionado está"} em <strong>${percent.format(Number(summary.goal_progress_percent || 0))}%</strong> da meta. ${Number(summary.remaining || 0) ? `Faltam <strong>${money.format(Number(summary.remaining))}</strong> para atingir o objetivo.` : "A meta foi alcançada no período."}` : "Ainda não há meta cadastrada para este perfil e período."} ${summary.daily_goal_pace ? `O ritmo médio necessário é <strong>${money.format(Number(summary.daily_goal_pace))} por dia</strong>.` : ""}</p>${yearComparison}</div></section>`;
}

async function renderTeamsPage() {
  const page = document.getElementById("pageView");
  const managerView = ["gerente", "administrador"].includes(state.role);
  page.innerHTML = `${pageHeader(managerView ? "Desempenho da equipe" : "Equipe", managerView ? "Visão geral resumida. Abra uma pessoa para consultar o mesmo painel individual do vendedor." : "Acompanhe as pessoas e os resultados dentro do seu escopo de visualização.")}<section class="panel"><header class="panel-heading"><div><h2>${managerView ? "Pessoas" : "Equipes visíveis"}</h2><p>${managerView ? "Os detalhes individuais aparecem ao abrir um perfil." : "Os resultados respeitam o papel de demonstração."}</p></div>${managerView ? '<label class="people-search"><span>⌕</span><input id="peopleSearch" type="search" placeholder="Buscar pessoa ou equipe" aria-label="Buscar pessoa ou equipe" /></label>' : ""}</header><div class="panel-body" id="teamsContent"><p class="quiet">Carregando dados da equipe…</p></div></section>`;
  try {
    const teams = managerView ? null : await api("/api/teams/");
    const target = document.getElementById("teamsContent");
    if (!target) return;
    if (managerView) {
      state.people = await api("/api/people/");
      const teamRevenue = state.people.reduce((total, person) => total + Number(person.revenue || 0), 0);
      const teamGoal = state.people.reduce((total, person) => total + Number(person.goal || 0), 0);
      const teamOrders = state.people.reduce((total, person) => total + Number(person.orders || 0), 0);
      const teamProgress = teamGoal ? teamRevenue / teamGoal * 100 : 0;
      target.innerHTML = `<div class="people-overview"><article><span>Receita válida no período</span><strong>${money.format(teamRevenue)}</strong></article><article><span>Meta individual somada</span><strong>${money.format(teamGoal)}</strong></article><article><span>Avanço agregado</span><strong>${percent.format(teamProgress)}%</strong></article><article><span>Vendas válidas</span><strong>${teamOrders}</strong></article></div><div class="people-list" id="peopleList"></div>`;
      const peopleList = document.getElementById("peopleList");
      const renderPeople = (term = "") => {
        const normalized = term.trim().toLocaleLowerCase("pt-BR");
        const teams = new Map();
        state.people.forEach((person) => {
          if (!teams.has(person.team)) teams.set(person.team, []);
          teams.get(person.team).push(person);
        });
        const groups = [...teams.entries()].map(([teamName, members]) => {
          const teamMatches = !normalized || teamName.toLocaleLowerCase("pt-BR").includes(normalized);
          const visible = teamMatches ? members : members.filter((person) => person.name.toLocaleLowerCase("pt-BR").includes(normalized));
          if (!visible.length) return "";
          const revenue = members.reduce((sum, person) => sum + Number(person.revenue || 0), 0);
          const goal = members.reduce((sum, person) => sum + Number(person.goal || 0), 0);
          const orders = members.reduce((sum, person) => sum + Number(person.orders || 0), 0);
          const progress = goal ? revenue / goal * 100 : 0;
          const cards = visible.map((person) => `<button class="person-card" type="button" data-open-employee="${person.id}"><span class="person-avatar">${escapeHtml(person.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join(""))}</span><span class="person-info"><strong>${escapeHtml(person.name)}</strong><small>${person.orders} vendas ÷ ${person.attendances} atendimentos · conversão ${percent.format(Number(person.conversion_rate_percent || 0))}%</small><span class="person-progress"><i style="width:${Math.min(100, Number(person.goal_progress_percent || 0))}%"></i></span></span><span class="person-result"><strong>${money.format(Number(person.revenue || 0))}</strong><small>${person.goal ? `${percent.format(Number(person.goal_progress_percent || 0))}% da meta` : "Sem meta individual"}</small></span><span class="person-open">Ver painel ↗</span></button>`).join("");
          return `<section class="team-performance-group"><header><div><strong>${escapeHtml(teamName)}</strong><small>${members.length} ${members.length === 1 ? "vendedor" : "vendedores"} · ${orders} vendas válidas</small></div><div class="team-performance-total"><strong>${money.format(revenue)}</strong><small>${goal ? `${percent.format(progress)}% da meta somada` : "Sem metas individuais"}</small></div></header>${cards}</section>`;
        }).join("");
        peopleList.innerHTML = groups || '<p class="empty-state">Nenhuma pessoa ou equipe corresponde à busca.</p>';
      };
      renderPeople();
      document.getElementById("peopleSearch").addEventListener("input", (event) => renderPeople(event.target.value));
      peopleList.addEventListener("click", (event) => {
        const button = event.target.closest("[data-open-employee]");
        if (button) openEmployeeDashboard(Number(button.dataset.openEmployee));
      });
    } else {
      target.innerHTML = teams.map((team) => `<article class="team-card"><div><strong>${escapeHtml(team.external_id ? `${team.external_id} · ${team.name}` : team.name)}</strong><p>${escapeHtml([team.city, team.state, team.region, team.store_type].filter(Boolean).join(" · "))}</p><small>${team.members.length} integrantes · gerente ${escapeHtml(team.manager || "não informado")} · supervisão ${escapeHtml(team.supervisor || "não informada")}</small></div></article>`).join("") || '<p class="empty-state">Nenhuma equipe disponível neste perfil.</p>';
    }
  } catch (error) { notify(error.message); }
}

async function openEmployeeDashboard(employeeId) {
  const employee = state.people.find((person) => person.id === employeeId);
  if (!employee) return;
  selectEmployee(employee);
  navigate("indicadores");
  await refreshData();
}

function selectEmployee(employee) {
  state.selectedEmployee = employee;
  setProfile();
  state.summary = null;
  state.sales = [];
  state.alerts = [];
  updateAlertBadge();
}

async function renderProductsPage() {
  const page = document.getElementById("pageView");
  const isManager = state.role === "gerente" && !state.selectedEmployee;
  page.innerHTML = `${pageHeader("Produtos", "Catálogo para especializar a IA e um cenário de produtos fictício para demonstração, separado dos resultados da equipe.")}
    <section class="panel demo-product-prompts"><header class="panel-heading"><div><h2>Experimente o assistente</h2><p>Use os exemplos fictícios para demonstrar consulta e orientação de produtos.</p></div></header><div class="panel-body suggestion-list"><button type="button" data-demo-product-prompt="No cenário simulado de outubro, qual produto teve maior receita e qual vendeu mais unidades?"><span>↗</span>Compare receita e unidades vendidas</button><button type="button" data-demo-product-prompt="Compare a Camiseta Essencial e a Calça Jeans Reta para ajudar um cliente que busca uma peça para o dia a dia."><span>✦</span>Peça uma recomendação com base no catálogo</button></div></section>
    ${isManager ? `<section class="panel"><header class="panel-heading"><div><h2>Novo produto</h2><p>Cadastre produtos para associá-los às especializações da IA.</p></div></header><form class="panel-body form-grid" id="productForm"><div class="form-field"><label>Nome do produto</label><input name="name" required /></div><div class="form-field"><label>SKU ou código</label><input name="sku" required /></div><div class="form-field"><label>Categoria</label><input name="category" /></div><div class="form-field"><label>Descrição</label><input name="description" /></div><div class="form-field full"><button class="button primary" type="submit">Cadastrar produto</button></div></form></section>` : ""}
    <section class="panel"><header class="panel-heading"><div><h2>Catálogo e dados de demonstração</h2><p>Os resultados simulados aparecem em coluna própria e nunca entram nas metas, comissões ou indicadores dos funcionários.</p></div></header><div class="table-scroll"><table><thead><tr><th>Produto</th><th>SKU</th><th>Vendas vinculadas no sistema</th><th>Cenário simulado de outubro</th></tr></thead><tbody id="productsBody"><tr><td colspan="4" class="empty-state">Carregando produtos…</td></tr></tbody></table></div></section>`;
  if (isManager) document.getElementById("productForm").addEventListener("submit", createProduct);
  try {
    const targetQuery = state.selectedEmployee ? `?employee_id=${state.selectedEmployee.id}` : "";
    const products = await api(`/api/products/${targetQuery}`);
    state.products = products;
    const body = document.getElementById("productsBody");
    if (body) body.innerHTML = products.map((product) => {
      const sample = product.demo_performance;
      const linkedSales = product.real_performance_available
        ? `${money.format(Number(product.amount || 0))} · ${Number(product.orders || 0)} vendas`
        : "Sem vendas vinculadas";
      const demoSales = sample
        ? `<strong>${money.format(Number(sample.revenue))}</strong><small class="cell-subtitle">${sample.orders} vendas · ${sample.units_sold} unidades</small><small class="cell-subtitle">${escapeHtml(sample.scenario_label)} · ${new Date(`${sample.period_start}T12:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</small>`
        : "Sem cenário simulado";
      return `<tr><td><strong>${escapeHtml(product.name)}</strong><small class="cell-subtitle">${escapeHtml(product.category || "Sem categoria")}</small><small class="cell-subtitle">${escapeHtml(product.description || "")}</small></td><td>${escapeHtml(product.sku)}</td><td>${linkedSales}</td><td>${demoSales}</td></tr>`;
    }).join("") || '<tr><td colspan="4" class="empty-state">Nenhum produto cadastrado.</td></tr>';
  } catch (error) { notify(error.message); }
}

function renderTrainingPage() {
  const cards = stages.map((stage, index) => `<article class="stage-card"><span class="stage-number">${index + 1}</span><div><strong>${escapeHtml(stage.title)}</strong><p>${escapeHtml(stage.summary)}</p><button class="table-action" data-stage-chat="${stage.id}">Conversar nesta etapa ↗</button></div></article>`).join("");
  return `${pageHeader("Método de venda adaptativa", "Um guia flexível inspirado em SPIN, Challenger e atendimento consultivo.")}
    <section class="panel"><div class="training-copy">Use as etapas como apoio à conversa. Elas podem acontecer em outra ordem; adapte à situação e às respostas do cliente. O assistente não avalia automaticamente o funcionário.</div><div class="stage-grid">${cards}</div></section>
    <section class="panel"><header class="panel-heading"><div><h2>Princípios de atendimento</h2><p>Conhecimento de referência usado para formular respostas.</p></div></header><div class="panel-body"><ul class="principle-list"><li>Entenda a necessidade antes de recomendar.</li><li>Trate perfis de cliente como situações temporárias, não como rótulos.</li><li>Conecte características a benefícios confirmados pelo cliente.</li><li>Explique limites, condições e incertezas; não crie urgência falsa.</li><li>Considere satisfação e adequação junto com conversão.</li></ul></div></section>`;
}

async function renderSpecializationPage() {
  if (state.role !== "gerente") {
    notify("Esta área está disponível apenas para a gerência.");
    return navigate("inicio");
  }
  const page = document.getElementById("pageView");
  page.innerHTML = `${pageHeader("Especialização da IA", "Organize os produtos da empresa e documente orientações úteis para todos os perfis.")}
    <section class="panel"><header class="panel-heading"><div><h2>Produtos e categorias</h2><p>Um perfil pode abranger um ou vários produtos da empresa.</p></div></header>
      <form class="panel-body form-grid" id="specializationForm">
        <div class="form-field"><label>Nome da especialização</label><input name="title" placeholder="Ex.: Planos digitais" required /></div>
        <div class="form-field"><label>Categoria comercial</label><input name="category" placeholder="Ex.: Assinaturas e serviços" required /></div>
        <div class="form-field full"><label>Produtos associados</label><div class="checkbox-list" id="productChoices"><span class="quiet">Carregando catálogo…</span></div></div>
        <div class="form-field"><label>Clientes e necessidades atendidas</label><textarea name="audience" placeholder="Quais perfis de clientes e necessidades são relevantes?"></textarea></div>
        <div class="form-field"><label>Diferenciais documentados</label><textarea name="differentiators" placeholder="Benefícios verificáveis e características confirmadas."></textarea></div>
        <div class="form-field"><label>Limitações e cuidados</label><textarea name="limitations" placeholder="O que o assistente não deve prometer ou presumir."></textarea></div>
        <div class="form-field"><label>Perguntas recomendadas</label><textarea name="recommended_questions" placeholder="Perguntas de descoberta úteis para estes produtos."></textarea></div>
        <div class="form-field full"><label>Orientação comercial</label><textarea name="sales_guidance" placeholder="Como apresentar valor, tratar dúvidas e explicar próximos passos."></textarea></div>
        <div class="form-field full"><button type="submit" class="button primary">Salvar especialização</button></div>
      </form>
    </section>
    <section class="panel"><header class="panel-heading"><div><h2>Especializações ativas</h2><p>A base contextual da IA usa esses dados e as etapas de venda adaptativa.</p></div></header><div class="panel-body"><div class="specialization-grid" id="specializationCards"><p class="quiet">Carregando especializações…</p></div></div></section>`;
  document.getElementById("specializationForm").addEventListener("submit", createSpecialization);
  try {
    const [products, profilesList] = await Promise.all([api("/api/products/"), api("/api/specializations/")]);
    state.products = products;
    state.specializations = profilesList;
    renderProductChoices();
    renderSpecializationCards();
  } catch (error) { notify(error.message); }
}

function renderProductChoices(selectedIds = []) {
  const target = document.getElementById("productChoices");
  if (!target) return;
  target.innerHTML = state.products.map((product) => `<label class="checkbox-pill"><input type="checkbox" name="product_ids" value="${product.id}" ${selectedIds.includes(product.id) ? "checked" : ""}/>${escapeHtml(product.name)}</label>`).join("") || '<span class="quiet">Cadastre produtos na aba Produtos primeiro.</span>';
}

function renderSpecializationCards() {
  const target = document.getElementById("specializationCards");
  if (!target) return;
  target.innerHTML = state.specializations.map((item) => `<article class="specialization-card">
    <div class="specialization-top"><div><h3>${escapeHtml(item.title)}</h3><span class="category-label">${escapeHtml(item.category)}</span></div><span class="status ${item.active ? "valid" : "cancelled"}">${item.active ? "Ativa" : "Pausada"}</span></div>
    <p><strong>Produtos:</strong> ${escapeHtml(item.products.map((product) => product.name).join(", ") || "Todos os produtos")}</p>
    <p><strong>Clientes:</strong> ${escapeHtml(item.audience || "Não definido")}</p>
    <p><strong>Cuidados:</strong> ${escapeHtml(item.limitations || "Não definido")}</p>
    <div class="card-actions"><button class="button" data-edit-specialization="${item.id}">Editar</button><button class="button danger" data-delete-specialization="${item.id}">Excluir</button></div>
    <form class="edit-specialization hidden" data-edit-form="${item.id}">
      <div class="form-grid">
        <div class="form-field"><label>Nome</label><input name="title" value="${escapeHtml(item.title)}" required /></div>
        <div class="form-field"><label>Categoria</label><input name="category" value="${escapeHtml(item.category)}" required /></div>
        <div class="form-field full"><label>Produtos associados</label><div class="checkbox-list" data-edit-products="${item.id}"></div></div>
        <div class="form-field"><label>Público e necessidades</label><textarea name="audience">${escapeHtml(item.audience)}</textarea></div>
        <div class="form-field"><label>Diferenciais</label><textarea name="differentiators">${escapeHtml(item.differentiators)}</textarea></div>
        <div class="form-field"><label>Limitações</label><textarea name="limitations">${escapeHtml(item.limitations)}</textarea></div>
        <div class="form-field"><label>Perguntas sugeridas</label><textarea name="recommended_questions">${escapeHtml(item.recommended_questions)}</textarea></div>
        <div class="form-field full"><label>Orientação de venda</label><textarea name="sales_guidance">${escapeHtml(item.sales_guidance)}</textarea></div>
        <div class="form-field full"><label class="checkbox-pill"><input type="checkbox" name="active" ${item.active ? "checked" : ""}/> Especialização ativa para o assistente</label></div>
        <div class="form-field full"><button class="button primary" type="submit">Salvar alterações</button></div>
      </div>
    </form>
  </article>`).join("") || '<p class="empty-state">Ainda não há especializações. Cadastre a primeira acima.</p>';
  target.querySelectorAll("[data-edit-specialization]").forEach((button) => button.addEventListener("click", () => toggleEditSpecialization(Number(button.dataset.editSpecialization))));
  target.querySelectorAll("[data-delete-specialization]").forEach((button) => button.addEventListener("click", () => deleteSpecialization(Number(button.dataset.deleteSpecialization))));
  target.querySelectorAll("[data-edit-form]").forEach((form) => form.addEventListener("submit", saveSpecializationEdit));
}

function toggleEditSpecialization(id) {
  const item = state.specializations.find((profile) => profile.id === id);
  const form = document.querySelector(`[data-edit-form="${id}"]`);
  if (!item || !form) return;
  form.classList.toggle("hidden");
  const choices = form.querySelector(`[data-edit-products="${id}"]`);
  choices.innerHTML = state.products.map((product) => `<label class="checkbox-pill"><input type="checkbox" name="product_ids" value="${product.id}" ${item.product_ids.includes(product.id) ? "checked" : ""}/>${escapeHtml(product.name)}</label>`).join("");
}

async function createProduct(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    await api("/api/products/", { method: "POST", body: JSON.stringify(data) });
    notify("Produto cadastrado.");
    renderProductsPage();
  } catch (error) { notify(error.message); }
}

async function createSpecialization(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submitButton = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.product_ids = formData.getAll("product_ids").map(Number);
  submitButton.disabled = true;
  try {
    const profile = await api("/api/specializations/", { method: "POST", body: JSON.stringify(data) });
    state.specializations.unshift(profile);
    form.reset();
    renderSpecializationCards();
    renderProductChoices();
    notify("Especialização adicionada à base de conhecimento da IA.");
  } catch (error) { notify(error.message); }
  finally { submitButton.disabled = false; }
}

async function saveSpecializationEdit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const id = Number(form.dataset.editForm);
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.product_ids = formData.getAll("product_ids").map(Number);
  data.active = form.querySelector('[name="active"]').checked;
  try {
    const updated = await api(`/api/specializations/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
    state.specializations = state.specializations.map((item) => item.id === id ? updated : item);
    renderSpecializationCards();
    notify("Especialização atualizada.");
  } catch (error) { notify(error.message); }
}

async function deleteSpecialization(id) {
  try {
    await api(`/api/specializations/${id}/`, { method: "DELETE" });
    state.specializations = state.specializations.filter((item) => item.id !== id);
    renderSpecializationCards();
    notify("Especialização removida.");
  } catch (error) { notify(error.message); }
}

function exportSales() {
  const columns = ["vendedor", "produto", "valor", "data", "status"];
  const rows = state.sales.map((sale) => [sale.seller_name, sale.product_name, sale.amount, sale.sold_at, sale.status]);
  const csv = [columns, ...rows].map((row) => row.map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`).join(";")).join("\r\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
  link.download = "vendas-dashalise-demo.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

function openReflectionDialog(saleId) {
  const sale = state.sales.find((item) => item.id === saleId);
  if (!sale) return;
  state.reflectionSaleId = saleId;
  document.getElementById("reflectionForm").reset();
  document.getElementById("reflectionContext").textContent = `Resumo diário #${saleId} · ${sale.seller_name} · ${sale.sold_at}. Registre uma dificuldade ou algo que queira praticar.`;
  document.getElementById("reflectionDialog").showModal();
  document.getElementById("reflectionStage").focus();
}

async function submitSaleReflection(event) {
  event.preventDefault();
  if (!state.reflectionSaleId) return;
  const form = event.currentTarget;
  const button = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  button.disabled = true;
  try {
    await api(`/api/sales/${state.reflectionSaleId}/reflections/`, {
      method: "POST",
      body: JSON.stringify({ stage: formData.get("stage"), challenge: formData.get("challenge") }),
    });
    document.getElementById("reflectionDialog").close();
    notify("Aprendizado salvo. A IA já pode usar essa etapa para sugerir uma prática.");
    await refreshData();
  } catch (error) {
    notify(error.message);
  } finally {
    button.disabled = false;
  }
}

async function renderPage(pageName) {
  const page = document.getElementById("pageView");
  if (pageName === "indicadores") {
    page.innerHTML = renderIndicatorsPage();
  } else if (pageName === "vendas") {
    page.innerHTML = renderSalesPage();
    page.querySelectorAll("[data-sale-chat]").forEach((button) => button.addEventListener("click", () => startSaleChat(Number(button.dataset.saleChat), "observe")));
    page.querySelectorAll("[data-reflection-sale]").forEach((button) => button.addEventListener("click", () => openReflectionDialog(Number(button.dataset.reflectionSale))));
    document.getElementById("salesExport").addEventListener("click", exportSales);
  } else if (pageName === "metas") {
    page.innerHTML = renderMetricsPage();
  } else if (pageName === "equipe") {
    await renderTeamsPage();
  } else if (pageName === "produtos") {
    await renderProductsPage();
  } else if (pageName === "treinamento") {
    page.innerHTML = renderTrainingPage();
    page.querySelectorAll("[data-stage-chat]").forEach((button) => button.addEventListener("click", async () => {
      const stage = stages.find((item) => item.id === button.dataset.stageChat);
      const chat = await newConversation({ saleId: state.activeSaleId, stage: stage.id, title: stage.title });
      if (chat) {
        navigate("inicio");
        document.getElementById("assistantQuestion").value = stage.prompt;
        document.getElementById("assistantQuestion").focus();
      }
    }));
  } else if (pageName === "especializacao") {
    await renderSpecializationPage();
  } else if (pageName === "alertas") {
    page.innerHTML = renderAlertsPage();
    page.querySelectorAll("[data-read-alert]").forEach((button) => button.addEventListener("click", () => markAlertRead(button.dataset.readAlert)));
    page.querySelectorAll("[data-alert-person]").forEach((button) => button.addEventListener("click", () => openEmployeeDashboard(Number(button.dataset.alertPerson))));
    page.querySelectorAll("[data-alert-coach]").forEach((button) => button.addEventListener("click", () => askAboutAlert(Number(button.dataset.alertCoach))));
    document.getElementById("readAllAlerts").addEventListener("click", markAllAlertsRead);
  }
}

function renderAlertsPage() {
  const managerView = ["gerente", "administrador"].includes(state.role);
  const unread = state.alerts.filter((alert) => !alert.read_at).length;
  const cards = state.alerts.map((alert) => {
    const canOpenPerson = managerView && alert.user_id;
    const personLabel = alert.team_name ? `${alert.user_name} · ${alert.team_name}` : alert.user_name;
    const coaching = alert.title.includes("Desenvolvimento") || alert.title.includes("Meta em risco") || alert.title.includes("Cancelamentos");
    return `<article class="alert-item ${alert.read_at ? "read" : ""}"><span class="status ${alert.severity === "warning" || alert.severity === "critical" ? "pending" : "valid"}">${alert.severity === "critical" ? "Crítico" : alert.severity === "warning" ? "Atenção" : "Informativo"}</span><div class="alert-message"><strong>${escapeHtml(alert.title)}</strong>${canOpenPerson ? `<button class="alert-person-link" data-alert-person="${alert.user_id}">${escapeHtml(personLabel)}</button>` : ""}<p>${escapeHtml(alert.message)}</p><small>${new Date(alert.created_at).toLocaleString("pt-BR")}</small><div class="alert-actions">${coaching ? `<button class="table-action" data-alert-coach="${alert.id}">Pedir exemplo à IA ↗</button>` : ""}${canOpenPerson ? `<button class="table-action" data-alert-person="${alert.user_id}">Abrir painel individual ↗</button>` : ""}</div></div>${alert.read_at ? '<span class="read-label">Lido</span>' : `<button class="table-action" data-read-alert="${alert.id}">Marcar como lido</button>`}</article>`;
  }).join("");
  return `${pageHeader("Alertas e próximos passos", managerView ? "Sinais dos resultados e sugestões de conversa para acompanhamento individual." : "Avisos de metas e resultados, com uma sugestão prática para o próximo atendimento.")}<section class="panel"><header class="panel-heading"><div><h2>Central de acompanhamento</h2><p>${unread} não lidos · recomendações derivadas dos dados disponíveis</p></div><button class="button" id="readAllAlerts">Marcar todos como lidos</button></header>${cards || '<p class="empty-state">Nenhum alerta disponível para este perfil.</p>'}</section>`;
}

async function askAboutAlert(alertId) {
  const alert = state.alerts.find((item) => item.id === alertId);
  if (!alert) return;
  if (alert.user_id && ["gerente", "administrador"].includes(state.role)) {
    selectEmployee(state.people.find((person) => person.id === alert.user_id) || { id: alert.user_id, name: alert.user_name });
  }
  const title = alert.title.toLocaleLowerCase("pt-BR");
  const stage = title.includes("obje") || title.includes("cancel") ? "decision"
    : title.includes("valor") ? "value"
      : title.includes("personal") ? "personalize"
        : title.includes("compra") ? "classify"
          : title.includes("acompanh") || title.includes("pós") ? "learn"
            : title.includes("prepara") ? "observe" : "investigate";
  const stageInfo = stages.find((item) => item.id === stage);
  const personName = state.selectedEmployee?.name;
  const prompt = personName
    ? `Considerando este indicador de ${personName}: ${alert.message} Como eu conduziria uma conversa de desenvolvimento com essa pessoa e qual exemplo prático posso dar usando ${stageInfo.title}?`
    : `Considerando este alerta: ${alert.message} Como posso aplicar ${stageInfo.title} no próximo atendimento? Dê um exemplo de fala e um passo prático.`;
  const conversation = await newConversation({ stage, title: `Dica rápida · ${stageInfo.title}` });
  if (!conversation) return;
  navigate("inicio");
  await sendQuestion(prompt);
}

async function markAlertRead(alertId) {
  try {
    await api(`/api/alerts/${alertId}/read/`, { method: "POST", body: "{}" });
    await refreshData();
    if (state.page === "alertas") renderPage("alertas");
  } catch (error) { notify(error.message); }
}

async function markAllAlertsRead() {
  const unreadIds = state.alerts.filter((alert) => !alert.read_at).map((alert) => alert.id);
  await Promise.all(unreadIds.map((id) => api(`/api/alerts/${id}/read/`, { method: "POST", body: "{}" }).catch(() => null)));
  await refreshData();
  if (state.page === "alertas") renderPage("alertas");
}

function openFloating(open) {
  const panel = document.getElementById("floatingChat");
  panel.classList.toggle("hidden", !open);
  if (open) {
    renderMessages();
    document.getElementById("floatingQuestion").focus();
  }
}

async function refreshData() {
  setProfile();
  try {
    const targetQuery = state.selectedEmployee && ["gerente", "administrador"].includes(state.role) ? `?employee_id=${state.selectedEmployee.id}` : "";
    const [summary, sales, alerts] = await Promise.all([api(`/api/dashboard/${targetQuery}`), api(`/api/sales/${targetQuery}`), api(`/api/alerts/${targetQuery}`)]);
    state.summary = summary;
    state.sales = sales;
    state.alerts = alerts;
    updateAlertBadge();
  } catch (error) { notify(error.message); }
  await loadHistory();
  if (state.page !== "inicio") renderPage(state.page);
}

async function updateWebAvailability() {
  try {
    const status = await api("/api/assistant/status/");
    state.webAvailable = status.web_search_enabled;
  } catch { state.webAvailable = false; }
  const label = document.getElementById("webAvailability");
  label.closest(".web-status").classList.toggle("disabled", !state.webAvailable);
  label.textContent = state.webAvailable
    ? "Gemini"
    : "configure API";
}

document.getElementById("navigation").addEventListener("click", (event) => {
  const button = event.target.closest("[data-page]");
  if (button) navigate(button.dataset.page);
});
document.getElementById("pageView").addEventListener("click", async (event) => {
  if (event.target.closest("[data-clear-employee]")) {
    state.selectedEmployee = null;
    setProfile();
    state.summary = null;
    state.sales = [];
    state.alerts = [];
    navigate("equipe");
    await refreshData();
    return;
  }
  if (event.target.closest('[data-go="alertas"]')) navigate("alertas");
});
document.querySelector(".brand").addEventListener("click", (event) => {
  event.preventDefault();
  navigate("inicio");
});
document.getElementById("roleSelect").addEventListener("change", async (event) => {
  state.role = event.target.value;
  state.selectedEmployee = null;
  state.summary = null;
  state.sales = [];
  state.alerts = [];
  state.activeConversationId = null;
  state.activeSaleId = null;
  state.activeStage = "general";
  state.messages = [];
  state.conversations = [];
  renderMessages();
  await refreshData();
  if (state.page === "especializacao" && state.role !== "gerente") navigate("inicio");
  notify(`Visão alterada para ${profiles[state.role].role}.`);
});
document.getElementById("conversationList").addEventListener("click", selectConversationFromHistory);
document.getElementById("newConversation").addEventListener("click", () => newConversation());
document.getElementById("stageSelect").addEventListener("change", async (event) => {
  const nextStage = event.target.value;
  if (nextStage === state.activeStage) return;
  const chat = await newConversation({ saleId: state.activeSaleId, stage: nextStage, title: stages.find((stage) => stage.id === nextStage)?.title || "Nova conversa" });
  if (chat) renderMessages();
});
document.getElementById("assistantForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("assistantQuestion");
  await sendQuestion(input.value, false);
});
document.getElementById("assistantQuestion").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    document.getElementById("assistantForm").requestSubmit();
  }
});
document.getElementById("floatingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendQuestion(document.getElementById("floatingQuestion").value, true);
});
document.getElementById("messageList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button) sendQuestion(button.dataset.prompt, false);
});
document.getElementById("pageView").addEventListener("click", (event) => {
  const button = event.target.closest("[data-demo-product-prompt]");
  if (!button) return;
  const prompt = button.dataset.demoProductPrompt;
  navigate("inicio");
  document.getElementById("assistantQuestion").value = prompt;
  sendQuestion(prompt);
});
document.getElementById("floatingChatTrigger").addEventListener("click", () => openFloating(true));
document.getElementById("closeFloatingChat").addEventListener("click", () => openFloating(false));
document.getElementById("expandChat").addEventListener("click", () => navigate("inicio"));
document.getElementById("notificationButton").addEventListener("click", () => navigate("alertas"));
document.getElementById("reflectionForm").addEventListener("submit", submitSaleReflection);
document.getElementById("closeReflectionDialog").addEventListener("click", () => document.getElementById("reflectionDialog").close());
document.getElementById("cancelReflection").addEventListener("click", () => document.getElementById("reflectionDialog").close());

setProfile();
renderMessages();
refreshData();
updateWebAvailability();

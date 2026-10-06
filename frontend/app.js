const state = {
  page: "dashboard",
  domains: [],
  dashboard: {},
  urlPage: 1,
  urlSize: 50,
  urlTotal: 0,
};

const $ = (selector) => document.querySelector(selector);

async function api(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {}

    throw new Error(message);
  }

  return response.json();
}

function toast(message) {
  $("#toast").innerHTML = `
    <div class="toast">${escapeHtml(message)}</div>
  `;

  setTimeout(() => {
    $("#toast").innerHTML = "";
  }, 3000);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString();
}

function statusBadge(status) {
  const safe = escapeHtml(status || "unknown");

  return `
    <span class="status status-${safe}">
      ${safe}
    </span>
  `;
}

/* NAVIGATION */

function navigate(page) {
  state.page = page;

  document.querySelectorAll(".page").forEach((element) => {
    element.classList.remove("active");
  });

  const target = $(`#${page}Page`);

  if (target) {
    target.classList.add("active");
  }

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle(
      "active",
      item.dataset.page === page
    );
  });

  const titles = {
    dashboard: "Dashboard",
    domains: "Websites",
    urls: "URL Repository",
    crawls: "Crawl History",
    submissions: "Archive History",
  };

  $("#pageTitle").textContent = titles[page] || "Dashboard";

  if (page === "dashboard") {
    loadDashboard();
  }

  if (page === "domains") {
    loadDomains();
  }

  if (page === "urls") {
    loadUrlDomains();
    loadUrls();
  }

  if (page === "crawls") {
    loadCrawls();
  }

  if (page === "submissions") {
    loadSubmissions();
  }

  $("#sidebar").classList.remove("open");
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    navigate(item.dataset.page);
  });
});

$("#menuButton").addEventListener("click", () => {
  $("#sidebar").classList.toggle("open");
});

/* DASHBOARD */

async function loadDashboard() {
  try {
    const data = await api("/api/dashboard");
    state.dashboard = data;

    renderStats(data);
    renderHealth(data);
    drawActivityChart(data);

    await loadRecentDomains();
  } catch (error) {
    toast(error.message);
  }
}

function renderStats(data) {
  const cards = [
    ["domains", "Websites", "◎", "i-pink"],
    ["urls", "Discovered URLs", "↗", "i-purple"],
    ["queued", "In pipeline", "◷", "i-blue"],
    ["submitted", "Archived", "✓", "i-green"],
  ];

  $("#stats").innerHTML = cards.map(
    ([key, label, icon, color]) => `
      <div class="stat">
        <div class="stat-icon ${color}">${icon}</div>
        <div class="stat-label">${label}</div>
        <div class="stat-value">${Number(data[key] || 0).toLocaleString()}</div>
      </div>
    `
  ).join("");
}

function renderHealth(data) {
  const success = Number(data.success || 0);
  const failed = Number(data.failed || 0);
  const pending = Number(data.pending || 0);
  const manual = Number(data.manual || 0);

  const total = success + failed + pending + manual;

  const successPercent =
    total === 0
      ? 0
      : Math.round((success / total) * 100);

  const failedPercent =
    total === 0
      ? 0
      : Math.round((failed / total) * 100);

  const pendingPercent =
    total === 0
      ? 0
      : Math.round((pending / total) * 100);

  const gradient = total
    ? `conic-gradient(
        #19a974 0 ${successPercent}%,
        #e5484d ${successPercent}% ${successPercent + failedPercent}%,
        #d99400 ${successPercent + failedPercent}%
      )`
    : "#eeeeF5";

  $("#healthChart").innerHTML = `
    <div>
      <div class="donut" style="background:${gradient}">
        <div class="donut-center">
          <strong>${successPercent}%</strong>
          <span>successful</span>
        </div>
      </div>

      <div style="
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:8px;
        margin-top:15px;
        font-size:11px;
        color:#777789;
      ">
        <span>● Success ${success}</span>
        <span>● Failed ${failed}</span>
        <span>● Pending ${pending}</span>
        <span>● Manual ${manual}</span>
      </div>
    </div>
  `;
}

function drawActivityChart(data) {
  const canvas = $("#activityChart");

  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;

  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;

  const ctx = canvas.getContext("2d");

  ctx.scale(ratio, ratio);

  const width = rect.width;
  const height = rect.height;

  ctx.clearRect(0, 0, width, height);

  const values = [
    Number(data.domains || 0),
    Number(data.urls || 0),
    Number(data.queued || 0),
    Number(data.submitted || 0),
  ];

  const max = Math.max(...values, 1);

  const padding = {
    top: 20,
    right: 20,
    bottom: 35,
    left: 35,
  };

  const chartWidth =
    width - padding.left - padding.right;

  const chartHeight =
    height - padding.top - padding.bottom;

  ctx.strokeStyle = "#eeeeF4";
  ctx.lineWidth = 1;

  for (let i = 0; i <= 4; i++) {
    const y =
      padding.top +
      (chartHeight / 4) * i;

    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  const points = values.map((value, index) => ({
    x:
      padding.left +
      (chartWidth / (values.length - 1)) * index,
    y:
      padding.top +
      chartHeight -
      (value / max) * chartHeight,
  }));

  const gradient = ctx.createLinearGradient(
    0,
    0,
    width,
    0
  );

  gradient.addColorStop(0, "#ff3f87");
  gradient.addColorStop(1, "#7257ff");

  ctx.strokeStyle = gradient;
  ctx.lineWidth = 4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  ctx.beginPath();

  points.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });

  ctx.stroke();

  points.forEach((point, index) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#ff3f87";
    ctx.fill();

    const labels = [
      "Websites",
      "URLs",
      "Queued",
      "Archived",
    ];

    ctx.fillStyle = "#777789";
    ctx.font = "10px system-ui";
    ctx.textAlign = "center";
    ctx.fillText(
      labels[index],
      point.x,
      height - 10
    );
  });
}

async function loadRecentDomains() {
  const domains = await api("/api/domains");

  state.domains = domains;

  const recent = domains.slice(0, 5);

  if (!recent.length) {
    $("#recentDomains").innerHTML = emptyState(
      "◎",
      "No websites yet",
      "Add your first website to start building the archive."
    );

    return;
  }

  $("#recentDomains").innerHTML = recent.map(
    (domain) => `
      <div style="
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:15px;
        padding:15px 20px;
        border-top:1px solid var(--line);
      ">
        <div>
          <strong>${escapeHtml(domain.name)}</strong>
          <div style="color:#777789;font-size:11px;margin-top:3px">
            ${escapeHtml(domain.base_url)}
          </div>
        </div>

        <button
          class="small-button"
          onclick="scanDomain(${domain.id})"
        >
          Scan
        </button>
      </div>
    `
  ).join("");
}

/* DOMAINS */

async function loadDomains() {
  try {
    const domains = await api("/api/domains");

    state.domains = domains;

    if (!domains.length) {
      $("#domainsList").innerHTML = emptyState(
        "◎",
        "Your repository is empty",
        "Add a website above and start your first crawl."
      );

      return;
    }

    $("#domainsList").innerHTML = domains.map(
      (domain) => `
        <div class="domain-card">
          <div class="domain-top">
            <div>
              <div class="domain-name">
                ${escapeHtml(domain.name)}
              </div>

              <div class="domain-url">
                ${escapeHtml(domain.base_url)}
              </div>
            </div>

            ${domain.active
              ? '<span class="status status-success">ACTIVE</span>'
              : '<span class="status status-failed">INACTIVE</span>'}
          </div>

          <div class="domain-actions">
            <button
              class="small-button"
              onclick="scanDomain(${domain.id})"
            >
              ↻ Scan website
            </button>

            <button
              class="small-button"
              onclick="queueArchive(${domain.id}, 'wayback')"
            >
              Archive with Wayback
            </button>

            <button
              class="small-button"
              onclick="queueArchive(${domain.id}, 'archive_today')"
            >
              Archive.today
            </button>

            <button
              class="small-button"
              onclick="viewDomainUrls(${domain.id})"
            >
              View URLs
            </button>
          </div>
        </div>
      `
    ).join("");
  } catch (error) {
    toast(error.message);
  }
}

async function addDomain() {
  const input = $("#site");
  const url = input.value.trim();

  if (!url) {
    toast("Enter a website URL first.");
    return;
  }

  try {
    await api("/api/domains", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    });

    input.value = "";

    toast("Website added successfully.");

    await loadDomains();
    await loadDashboard();
  } catch (error) {
    toast(error.message);
  }
}

async function scanDomain(id) {
  try {
    await api(`/api/domains/${id}/scan`, {
      method: "POST",
    });

    toast("Crawl started.");

    setTimeout(() => {
      loadDashboard();
    }, 500);

    if (state.page === "domains") {
      await loadDomains();
    }
  } catch (error) {
    toast(error.message);
  }
}

async function queueArchive(id, service) {
  try {
    const result = await api(
      `/api/submissions/queue/${id}?service=${encodeURIComponent(service)}`,
      {
        method: "POST",
      }
    );

    toast(
      `${result.queued} URL(s) queued for ${service}.`
    );

    await loadDashboard();
  } catch (error) {
    toast(error.message);
  }
}

function viewDomainUrls(id) {
  $("#urlDomain").value = String(id);
  navigate("urls");
}

/* URLS */

async function loadUrlDomains() {
  const domains = await api("/api/domains");

  $("#urlDomain").innerHTML = `
    <option value="">All websites</option>
    ${domains.map(
      (domain) => `
        <option value="${domain.id}">
          ${escapeHtml(domain.name)}
        </option>
      `
    ).join("")}
  `;
}

async function loadUrls() {
  try {
    const query = $("#urlSearch")?.value.trim() || "";
    const domain = $("#urlDomain")?.value || "";

    const params = new URLSearchParams({
      q: query,
      page: state.urlPage,
      size: state.urlSize,
    });

    if (domain) {
      params.set("domain", domain);
    }

    const result = await api(
      `/api/urls?${params.toString()}`
    );

    /*
      The API supports both the older array response and
      the newer paginated object response.
    */
    const rows = Array.isArray(result)
      ? result
      : result.items || [];

    state.urlTotal = Array.isArray(result)
      ? rows.length
      : Number(result.total || rows.length);

    if (!rows.length) {
      $("#urls").innerHTML = `
        <tr>
          <td colspan="5">
            ${emptyState(
              "↗",
              "No URLs found",
              "Crawl a website to discover URLs."
            )}
          </td>
        </tr>
      `;
    } else {
      $("#urls").innerHTML = rows.map(
        (url) => `
          <tr>
            <td>
              <a
                href="${escapeHtml(url.url)}"
                target="_blank"
                rel="noopener"
                style="color:#e91e63;text-decoration:none"
              >
                ${escapeHtml(url.url)}
              </a>
            </td>

            <td>
              ${statusBadge(url.status)}
            </td>

            <td>
              ${url.http_status ?? "—"}
            </td>

            <td>
              ${escapeHtml(url.source || "—")}
            </td>

            <td>
              ${formatDate(url.crawled_at)}
            </td>
          </tr>
        `
      ).join("");
    }

    const totalPages =
      Math.max(
        1,
        Math.ceil(state.urlTotal / state.urlSize)
      );

    $("#urlPageInfo").textContent =
      `Page ${state.urlPage} / ${totalPages}`;
  } catch (error) {
    toast(error.message);
  }
}

function changeUrlPage(delta) {
  const totalPages =
    Math.max(
      1,
      Math.ceil(state.urlTotal / state.urlSize)
    );

  state.urlPage = Math.min(
    totalPages,
    Math.max(1, state.urlPage + delta)
  );

  loadUrls();
}

$("#urlSearch")?.addEventListener(
  "input",
  debounce(() => {
    state.urlPage = 1;
    loadUrls();
  }, 300)
);

$("#urlDomain")?.addEventListener(
  "change",
  () => {
    state.urlPage = 1;
    loadUrls();
  }
);

/* CRAWLS */

async function loadCrawls() {
  try {
    const result = await api("/api/crawls?page=1&size=50");

    const rows = Array.isArray(result)
      ? result
      : result.items || [];

    if (!rows.length) {
      $("#crawlHistory").innerHTML = emptyState(
        "◷",
        "No crawl history",
        "Start a website scan to create your first crawl."
      );
      return;
    }

    $("#crawlHistory").innerHTML = `
      <div class="panel table-panel">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Website</th>
                <th>Status</th>
                <th>Total</th>
                <th>Done</th>
                <th>Failed</th>
                <th>Started</th>
                <th>Finished</th>
              </tr>
            </thead>

            <tbody>
              ${rows.map((crawl) => `
                <tr>
                  <td>#${Number(crawl.id)}</td>

                  <td>
                    ${escapeHtml(
                      domainName(crawl.domain_id)
                    )}
                  </td>

                  <td>
                    ${statusBadge(crawl.status)}
                  </td>

                  <td>${Number(crawl.total || 0).toLocaleString()}</td>
                  <td>${Number(crawl.done || 0).toLocaleString()}</td>
                  <td>${Number(crawl.failed || 0).toLocaleString()}</td>

                  <td>${formatDate(crawl.started_at)}</td>
                  <td>${formatDate(crawl.finished_at)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (error) {
    toast(error.message);
  }
}

function domainName(id) {
  const domain = state.domains.find(
    (item) => Number(item.id) === Number(id)
  );

  return domain
    ? domain.name
    : `Domain #${id}`;
}

/* SUBMISSIONS */

async function loadSubmissions() {
  try {
    const params = new URLSearchParams();

    const status = $("#submissionStatus").value;
    const service = $("#submissionService").value;

    if (status) {
      params.set("status", status);
    }

    if (service) {
      params.set("service", service);
    }

    params.set("page", "1");
    params.set("size", "50");

    const result = await api(
      `/api/submissions?${params.toString()}`
    );

    const rows = Array.isArray(result)
      ? result
      : result.items || [];

    if (!rows.length) {
      $("#submissions").innerHTML = `
        <tr>
          <td colspan="6">
            ${emptyState(
              "▣",
              "No archive submissions",
              "Queue a website for archiving to see submission history here."
            )}
          </td>
        </tr>
      `;

      return;
    }

    $("#submissions").innerHTML = rows.map(
      (row) => `
        <tr>
          <td>
            ${escapeHtml(row.url)}
          </td>

          <td>
            ${escapeHtml(row.service)}
          </td>

          <td>
            ${statusBadge(row.status)}
          </td>

          <td>
            ${Number(row.tries || 0)}
          </td>

          <td>
            ${
              row.archive_url
                ? `
                  <a
                    class="archive-link"
                    href="${escapeHtml(row.archive_url)}"
                    target="_blank"
                    rel="noopener"
                  >
                    Open ↗
                  </a>
                `
                : "—"
            }
          </td>

          <td style="color:#e5484d">
            ${escapeHtml(row.error || "—")}
          </td>
        </tr>
      `
    ).join("");
  } catch (error) {
    toast(error.message);
  }
}

$("#submissionStatus")?.addEventListener(
  "change",
  loadSubmissions
);

$("#submissionService")?.addEventListener(
  "change",
  loadSubmissions
);

/* HELPERS */

function emptyState(icon, title, description) {
  return `
    <div class="empty">
      <div class="empty-icon">${icon}</div>
      <strong style="display:block;color:#33333d">
        ${escapeHtml(title)}
      </strong>

      <div style="margin-top:5px">
        ${escapeHtml(description)}
      </div>
    </div>
  `;
}

function debounce(fn, delay) {
  let timer;

  return (...args) => {
    clearTimeout(timer);

    timer = setTimeout(
      () => fn(...args),
      delay
    );
  };
}

async function refreshAll() {
  if (state.page === "dashboard") {
    await loadDashboard();
  }

  if (state.page === "domains") {
    await loadDomains();
  }

  if (state.page === "urls") {
    await loadUrls();
  }

  if (state.page === "submissions") {
    await loadSubmissions();
  }

  toast("Refreshed.");
}

window.addDomain = addDomain;
window.scanDomain = scanDomain;
window.queueArchive = queueArchive;
window.viewDomainUrls = viewDomainUrls;
window.navigate = navigate;
window.changeUrlPage = changeUrlPage;
window.refreshAll = refreshAll;

/* INITIAL */

loadDashboard();

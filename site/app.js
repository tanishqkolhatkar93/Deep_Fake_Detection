const API_BASE = "https://tanishq93-deepfake-detection.hf.space";

const healthPill = document.getElementById("health-pill");
const limitPill = document.getElementById("limit-pill");
const apiBase = document.getElementById("api-base");
const resultCard = document.getElementById("result-card");
const resultSummary = document.getElementById("result-summary");
const resultGrid = document.getElementById("result-grid");
const evidenceTable = document.getElementById("evidence-table");

apiBase.textContent = API_BASE;

function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function setResultState(title, summary, tone) {
  const heading = resultCard.querySelector("h3");
  heading.textContent = title;
  resultSummary.textContent = summary;
  resultCard.dataset.tone = tone;
}

function renderTiles(items) {
  resultGrid.innerHTML = items
    .map(
      (item) => `
        <article class="result-tile ${item.highlight ? "result-highlight" : ""}">
          <span>${item.label}</span>
          <strong>${item.value}</strong>
        </article>
      `
    )
    .join("");
}

function renderEvidence(evidence = {}) {
  const entries = Object.entries(evidence).sort((a, b) => Number(b[1]) - Number(a[1]));
  if (!entries.length) {
    evidenceTable.innerHTML = "";
    return;
  }

  evidenceTable.innerHTML = `
    <p class="eyebrow">Evidence</p>
    ${entries
      .map(
        ([label, score]) => `
          <div class="evidence-row">
            <span>${label.replaceAll("_", " ")}</span>
            <strong>${Number(score).toFixed(3)}</strong>
          </div>
        `
      )
      .join("")}
  `;
}

async function refreshMetadata() {
  try {
    const [healthResponse, metadataResponse] = await Promise.all([
      fetch(`${API_BASE}/health`),
      fetch(`${API_BASE}/metadata`)
    ]);

    if (!healthResponse.ok || !metadataResponse.ok) {
      throw new Error("API metadata unavailable");
    }

    const health = await healthResponse.json();
    const metadata = await metadataResponse.json();

    healthPill.textContent = health.status === "ok" ? "API online" : "API degraded";
    limitPill.textContent = `${Math.round(metadata.limits.max_image_bytes / (1024 * 1024))} MB image / ${Math.round(metadata.limits.max_video_duration_seconds)}s video`;
  } catch (error) {
    healthPill.textContent = "API unreachable";
    limitPill.textContent = "Check backend status";
  }
}

async function submitMedia(form, mediaType) {
  const fileInput = form.querySelector('input[type="file"]');
  const file = fileInput.files?.[0];
  if (!file) {
    setResultState("Missing file", "Choose a file before submitting.", "error");
    return;
  }

  const endpoint = mediaType === "video" ? "/detect/video" : "/detect/image";
  const formData = new FormData();
  formData.append("file", file);

  setResultState("Analyzing…", `Uploading ${file.name} to the live API.`, "loading");
  renderTiles([
    { label: "File", value: file.name },
    { label: "Size", value: `${(file.size / (1024 * 1024)).toFixed(2)} MB` }
  ]);
  renderEvidence();

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      body: formData
    });

    const raw = await response.text();
    let payload = {};
    try {
      payload = JSON.parse(raw);
    } catch (error) {
      payload = { detail: raw || "Unexpected non-JSON response from API" };
    }
    if (!response.ok) {
      throw new Error(payload.detail || "Scan failed");
    }

    const report = payload.report;
    const verdictTone = report.verdict === "Yes" ? "warn" : "ok";
    setResultState(
      report.verdict === "Yes" ? "Potentially synthetic" : "No synthetic flag",
      report.summary,
      verdictTone
    );

    renderTiles([
      { label: "Verdict", value: report.verdict, highlight: true },
      { label: "Fake probability", value: formatPercent(report.fake_probability) },
      { label: "Processing time", value: `${payload.processing_ms} ms` },
      { label: "Model", value: payload.model },
      {
        label: "Request ID",
        value: payload.request_id ? payload.request_id.slice(0, 12) : "Unavailable"
      },
      {
        label: mediaType === "video" ? "Frames sampled" : "Media type",
        value: mediaType === "video" ? report.frames_sampled : payload.media_type
      }
    ]);
    renderEvidence(report.evidence);
  } catch (error) {
    setResultState("Scan failed", error.message, "error");
    renderTiles([
      { label: "Status", value: "Request rejected", highlight: true },
      { label: "Reason", value: error.message }
    ]);
    renderEvidence();
  }
}

function wireTabs() {
  const buttons = document.querySelectorAll(".tab-button");
  const panels = document.querySelectorAll(".tab-panel");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => item.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`[data-panel="${button.dataset.tab}"]`)?.classList.add("active");
    });
  });
}

function wireForms() {
  document.querySelectorAll(".upload-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitMedia(form, form.dataset.mediaType);
    });
  });
}

wireTabs();
wireForms();
refreshMetadata();

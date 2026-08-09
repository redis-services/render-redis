/* Central — shared client helpers. No framework, no build step. */

(function () {
  "use strict";

  const Central = {};

  // ── HTTP ─────────────────────────────────────────────────────────────────

  Central.api = async function (path, options) {
    options = options || {};
    const init = {
      method: options.method || "GET",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
    };
    if (options.body !== undefined) init.body = JSON.stringify(options.body);

    const response = await fetch(path, init);
    let payload = null;
    try {
      payload = await response.json();
    } catch (err) {
      payload = null;
    }
    if (!response.ok) {
      const detail = payload && payload.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail) && detail.length
          ? detail[0].msg || "Request failed"
          : "Request failed (" + response.status + ")";
      const error = new Error(message);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  };

  // ── Toasts ───────────────────────────────────────────────────────────────

  Central.toast = function (message, kind) {
    let host = document.querySelector(".toasts");
    if (!host) {
      host = document.createElement("div");
      host.className = "toasts";
      document.body.appendChild(host);
    }
    const node = document.createElement("div");
    node.className = "toast" + (kind === "err" ? " err" : "");
    node.textContent = message;
    host.appendChild(node);
    setTimeout(function () {
      node.style.opacity = "0";
      setTimeout(function () { node.remove(); }, 200);
    }, kind === "err" ? 5000 : 2800);
  };

  // ── Clipboard ────────────────────────────────────────────────────────────

  Central.copy = async function (text, label) {
    try {
      await navigator.clipboard.writeText(text);
      Central.toast((label || "Copied") + " to clipboard");
    } catch (err) {
      // Clipboard API needs a secure context; fall back to a hidden textarea.
      const scratch = document.createElement("textarea");
      scratch.value = text;
      scratch.style.position = "fixed";
      scratch.style.opacity = "0";
      document.body.appendChild(scratch);
      scratch.select();
      try {
        document.execCommand("copy");
        Central.toast((label || "Copied") + " to clipboard");
      } catch (err2) {
        Central.toast("Could not copy — select and copy manually", "err");
      }
      scratch.remove();
    }
  };

  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-copy]");
    if (!trigger) return;
    event.preventDefault();
    Central.copy(trigger.getAttribute("data-copy"), trigger.getAttribute("data-copy-label"));
  });

  // ── Escaping and formatting ──────────────────────────────────────────────

  Central.escape = function (value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  };

  Central.formatBytes = function (value) {
    if (!value) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = Number(value);
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
      size /= 1024;
      index += 1;
    }
    return (index === 0 ? size.toFixed(0) : size.toFixed(1)) + " " + units[index];
  };

  Central.formatCount = function (value) {
    const number = Number(value || 0);
    if (number < 1000) return String(number);
    if (number < 1000000) return (number / 1000).toFixed(1).replace(".0", "") + "k";
    return (number / 1000000).toFixed(1).replace(".0", "") + "M";
  };

  Central.formatTtl = function (seconds) {
    if (seconds == null) return "∞";
    if (seconds < 60) return seconds + "s";
    if (seconds < 3600) return Math.floor(seconds / 60) + "m";
    if (seconds < 86400) return Math.floor(seconds / 3600) + "h";
    return Math.floor(seconds / 86400) + "d";
  };

  Central.formatTime = function (millis) {
    const when = new Date(millis);
    return when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  // ── JSON rendering ───────────────────────────────────────────────────────

  Central.highlightJson = function (value) {
    const text = JSON.stringify(value, null, 2);
    if (text === undefined) return "";
    return Central.escape(text).replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      function (match) {
        let cls = "json-num";
        if (/^"/.test(match)) {
          cls = /:$/.test(match) ? "json-key" : "json-str";
        } else if (/true|false/.test(match)) {
          cls = "json-bool";
        } else if (/null/.test(match)) {
          cls = "json-null";
        }
        return '<span class="' + cls + '">' + match + "</span>";
      }
    );
  };

  Central.typeClass = function (type) {
    const known = ["string", "list", "hash", "set", "zset"];
    return "type-" + (known.indexOf(type) >= 0 ? type : "none");
  };

  // ── Modals ───────────────────────────────────────────────────────────────

  Central.openModal = function (id) {
    const node = document.getElementById(id);
    if (node) {
      node.classList.remove("hidden");
      const focusable = node.querySelector("input:not([disabled]), textarea, select");
      if (focusable) setTimeout(function () { focusable.focus(); }, 40);
    }
  };

  Central.closeModal = function (id) {
    const node = document.getElementById(id);
    if (node) node.classList.add("hidden");
  };

  document.addEventListener("click", function (event) {
    const opener = event.target.closest("[data-modal-open]");
    if (opener) {
      event.preventDefault();
      Central.openModal(opener.getAttribute("data-modal-open"));
      return;
    }
    const closer = event.target.closest("[data-modal-close]");
    if (closer) {
      event.preventDefault();
      Central.closeModal(closer.getAttribute("data-modal-close"));
      return;
    }
    if (event.target.classList && event.target.classList.contains("overlay")) {
      event.target.classList.add("hidden");
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    document.querySelectorAll(".overlay:not(.hidden)").forEach(function (node) {
      node.classList.add("hidden");
    });
  });

  // ── Tabs ─────────────────────────────────────────────────────────────────

  document.addEventListener("click", function (event) {
    const tab = event.target.closest("[data-tab]");
    if (!tab) return;
    const group = tab.getAttribute("data-tab-group");
    const name = tab.getAttribute("data-tab");
    document.querySelectorAll('[data-tab-group="' + group + '"]').forEach(function (node) {
      node.classList.toggle("active", node === tab);
    });
    document.querySelectorAll('[data-tab-panel-group="' + group + '"]').forEach(function (node) {
      node.classList.toggle("hidden", node.getAttribute("data-tab-panel") !== name);
    });
  });

  // ── Charts (inline SVG, no dependencies) ─────────────────────────────────

  function buildPath(points, width, height, maxValue, pad) {
    if (!points.length) return { line: "", area: "" };
    const stepX = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
    const usableHeight = height - pad * 2;
    const coords = points.map(function (value, index) {
      const x = pad + index * stepX;
      const y = pad + usableHeight - (maxValue ? (value / maxValue) * usableHeight : 0);
      return [x, y];
    });
    const line = coords
      .map(function (point, index) { return (index ? "L" : "M") + point[0].toFixed(1) + " " + point[1].toFixed(1); })
      .join(" ");
    const area =
      line +
      " L" + coords[coords.length - 1][0].toFixed(1) + " " + (height - pad) +
      " L" + coords[0][0].toFixed(1) + " " + (height - pad) + " Z";
    return { line: line, area: area };
  }

  /**
   * Render a filled area chart into a container element.
   * series: [{ values: [], color: string, fill: bool }]
   */
  Central.areaChart = function (container, series, labels) {
    if (!container) return;
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 200;
    const pad = 12;
    const maxValue = Math.max(
      1,
      ...series.map(function (item) { return Math.max.apply(null, item.values.concat([0])); })
    );

    let gridLines = "";
    for (let index = 1; index <= 3; index += 1) {
      const y = pad + ((height - pad * 2) / 4) * index;
      gridLines +=
        '<line class="chart-grid" x1="' + pad + '" y1="' + y + '" x2="' + (width - pad) + '" y2="' + y + '" />';
    }

    let body = "";
    let defs = "";
    series.forEach(function (item, index) {
      const path = buildPath(item.values, width, height, maxValue, pad);
      if (!path.line) return;
      const gradientId = "grad-" + index + "-" + Math.random().toString(36).slice(2, 7);
      if (item.fill !== false) {
        defs +=
          '<linearGradient id="' + gradientId + '" x1="0" y1="0" x2="0" y2="1">' +
          '<stop offset="0%" stop-color="' + item.color + '" stop-opacity="0.28"/>' +
          '<stop offset="100%" stop-color="' + item.color + '" stop-opacity="0"/>' +
          "</linearGradient>";
        body += '<path d="' + path.area + '" fill="url(#' + gradientId + ')" />';
      }
      body += '<path d="' + path.line + '" fill="none" stroke="' + item.color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />';
    });

    let axis = "";
    if (labels && labels.length) {
      const first = labels[0];
      const middle = labels[Math.floor(labels.length / 2)];
      const last = labels[labels.length - 1];
      axis =
        '<text class="chart-axis" x="' + pad + '" y="' + (height - 1) + '">' + Central.escape(first) + "</text>" +
        '<text class="chart-axis" x="' + width / 2 + '" y="' + (height - 1) + '" text-anchor="middle">' + Central.escape(middle) + "</text>" +
        '<text class="chart-axis" x="' + (width - pad) + '" y="' + (height - 1) + '" text-anchor="end">' + Central.escape(last) + "</text>";
    }

    container.innerHTML =
      '<svg class="chart" viewBox="0 0 ' + width + " " + height + '" preserveAspectRatio="none">' +
      "<defs>" + defs + "</defs>" + gridLines + body + axis + "</svg>";
  };

  Central.sparkline = function (container, values, color) {
    if (!container) return;
    const width = container.clientWidth || 200;
    const height = container.clientHeight || 40;
    const maxValue = Math.max(1, Math.max.apply(null, values.concat([0])));
    const path = buildPath(values, width, height, maxValue, 3);
    container.innerHTML =
      '<svg class="chart" viewBox="0 0 ' + width + " " + height + '" preserveAspectRatio="none">' +
      '<path d="' + path.line + '" fill="none" stroke="' + (color || "#DC382D") + '" stroke-width="1.6" />' +
      "</svg>";
  };

  // ── Password strength (signals effort, not a security control) ───────────

  Central.passwordStrength = function (value) {
    if (!value) return 0;
    let score = 0;
    if (value.length >= 10) score += 1;
    if (value.length >= 14) score += 1;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
    if (/\d/.test(value)) score += 1;
    if (/[^A-Za-z0-9]/.test(value)) score += 1;
    return Math.min(3, Math.max(1, Math.round((score / 5) * 3)));
  };

  Central.bindStrengthMeter = function (input, meter) {
    if (!input || !meter) return;
    const bars = meter.querySelectorAll("i");
    input.addEventListener("input", function () {
      const score = Central.passwordStrength(input.value);
      const classes = ["", "on-weak", "on-fair", "on-good"];
      bars.forEach(function (bar, index) {
        bar.className = index < score ? classes[score] : "";
      });
    });
  };

  Central.togglePassword = function (button) {
    const input = button.parentElement.querySelector("input");
    if (!input) return;
    const revealed = input.type === "text";
    input.type = revealed ? "password" : "text";
    button.textContent = revealed ? "Show" : "Hide";
  };

  window.Central = Central;
})();

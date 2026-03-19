/**
 * apply.js — SSE streaming frontend for AgentHire
 *
 * Real TinyFish event types (confirmed via API test):
 *   STARTED, STREAMING_URL, HEARTBEAT, PROGRESS, COMPLETED, ERROR
 */

document.addEventListener('DOMContentLoaded', function () {

  var urlInputsContainer = document.getElementById('url-inputs');
  var addUrlBtn          = document.getElementById('add-url-btn');
  var urlLimitMsg        = document.getElementById('url-limit-msg');
  var launchBtn          = document.getElementById('launch-btn');
  var launchText         = document.getElementById('launch-text');
  var launchIcon         = document.getElementById('launch-icon');
  var progressSection    = document.getElementById('progress-section');
  var jobCardsContainer  = document.getElementById('job-cards');
  var overallStatus      = document.getElementById('overall-status');
  var completionSummary  = document.getElementById('completion-summary');
  var summaryText        = document.getElementById('summary-text');
  var cardTemplate       = document.getElementById('job-card-template');

  var MAX_URLS = 5;
  var urlCount = 1;

  // ── Dynamic URL rows ───────────────────────────────────────────────────────

  function addUrlRow() {
    if (urlCount >= MAX_URLS) return;
    urlCount++;

    var row = document.createElement('div');
    row.className = 'url-row flex items-center gap-3';
    row.innerHTML =
      '<div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;font-size:0.72rem;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">' + urlCount + '</div>'
      + '<input type="url"'
      + ' class="job-url-input form-input flex-1"'
      + ' placeholder="https://boards.greenhouse.io/company/jobs/..."'
      + ' id="url-input-' + urlCount + '">'
      + '<button type="button" onclick="removeUrlRow(this)"'
      + ' class="clear-url-btn w-7 h-7 flex-shrink-0 flex items-center justify-center rounded-full text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all text-sm">✕</button>';

    urlInputsContainer.appendChild(row);
    // animate in
    row.style.opacity = '0'; row.style.transform = 'translateY(8px)';
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        row.style.transition = 'opacity 0.25s,transform 0.25s';
        row.style.opacity = '1'; row.style.transform = '';
      });
    });
    row.querySelector('input').focus();

    if (urlCount >= MAX_URLS) {
      addUrlBtn.disabled = true;
      urlLimitMsg.classList.remove('hidden');
    }
  }

  window.removeUrlRow = function (btn) {
    btn.closest('.url-row').remove();
    urlCount--;
    addUrlBtn.disabled = false;
    urlLimitMsg.classList.add('hidden');
    // renumber badges
    document.querySelectorAll('.url-row').forEach(function (row, i) {
      var badge = row.querySelector('div[style*="border-radius:50%"]');
      if (badge) badge.textContent = i + 1;
    });
  };

  addUrlBtn.addEventListener('click', addUrlRow);

  // ── Launch Agent ───────────────────────────────────────────────────────────

  launchBtn.addEventListener('click', function () {
    var inputs  = document.querySelectorAll('.job-url-input');
    var jobUrls = Array.from(inputs).map(function (i) { return i.value.trim(); }).filter(function (v) { return v.length > 0; });

    if (jobUrls.length === 0) {
      showToast('Please enter at least one job URL.', 'error'); return;
    }
    for (var u = 0; u < jobUrls.length; u++) {
      try { new URL(jobUrls[u]); } catch (e) {
        showToast('Invalid URL: ' + jobUrls[u], 'error'); return;
      }
    }

    launchBtn.disabled = true;
    launchText.textContent = 'Launching...';
    launchIcon.innerHTML = '<span class="spinner" style="width:18px;height:18px"></span>';
    launchBtn.style.opacity = '0.8';

    fetch('/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_urls: jobUrls }),
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { showToast(data.error, 'error'); resetLaunchBtn(); return; }

      var ids = data.application_ids || [];

      progressSection.classList.remove('hidden');
      progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

      // Build cards
      var cardRefs = ids.map(function (id, idx) {
        return createJobCard(id, jobUrls[idx] || '...');
      });

      // Stream sequentially
      var submitted = 0;
      var failed    = 0;
      var idx       = 0;

      function runNext() {
        if (idx >= cardRefs.length) {
          overallStatus.textContent = 'Complete — ' + submitted + ' submitted, ' + failed + ' failed';
          summaryText.textContent = submitted + ' application' + (submitted !== 1 ? 's' : '') + ' submitted · ' + failed + ' failed';
          completionSummary.classList.remove('hidden');
          completionSummary.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          launchText.textContent = 'Launch Another Run';
          launchIcon.textContent = '🔄';
          launchBtn.disabled = false;
          launchBtn.classList.remove('opacity-75');
          return;
        }
        overallStatus.textContent = 'Applying ' + (idx + 1) + ' of ' + cardRefs.length + '...';
        streamApplication(cardRefs[idx], function (status) {
          if (status === 'submitted') submitted++;
          else failed++;
          idx++;
          runNext();
        });
      }
      runNext();
    })
    .catch(function (err) {
      console.error(err);
      // Show network error UI banner
      var errBanner = document.getElementById('network-error-banner');
      if (!errBanner) {
        errBanner = document.createElement('div');
        errBanner.id = 'network-error-banner';
        errBanner.style.cssText = 'display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:14px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);color:#f87171;font-size:0.85rem;margin-top:12px';
        errBanner.innerHTML = '<span style="font-size:1.2rem">😵</span><div><strong>Connection error</strong> — Could not reach the server. Check your connection and try again.</div>'
          + '<button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;color:#94a3b8;cursor:pointer;font-size:1.1rem">✕</button>';
        launchBtn.parentElement.appendChild(errBanner);
      }
      if (typeof showToast !== 'undefined') showToast('Network error. Please try again.', 'error');
      resetLaunchBtn();
    });
  });

  // ── Create job card ────────────────────────────────────────────────────────

  function createJobCard(appId, jobUrl) {
    var clone       = cardTemplate.content.cloneNode(true);
    var card        = clone.querySelector('.job-card');
    var urlDisplay  = card.querySelector('.job-url-display');
    var logArea     = card.querySelector('.log-area');
    var statusBadge = card.querySelector('.status-badge');
    var statusDot   = card.querySelector('.status-dot');
    var browserContainer = card.querySelector('.browser-container');
    var iframe           = card.querySelector('.browser-iframe');
    var iframeFallback   = card.querySelector('.iframe-fallback');
    var liveViewLink     = card.querySelector('.live-view-link');

    urlDisplay.textContent = jobUrl.length > 70 ? jobUrl.substring(0, 70) + '…' : jobUrl;
    urlDisplay.title = jobUrl;

    jobCardsContainer.appendChild(card);
    return {
      card: card,
      logArea: logArea,
      statusBadge: statusBadge,
      statusDot: statusDot,
      companyRole: card.querySelector('.company-role'),
      appId: appId,
      browserContainer: browserContainer,
      iframe: iframe,
      iframeFallback: iframeFallback,
      liveViewLink: liveViewLink
    };
  }

  // ── Stream one application ─────────────────────────────────────────────────

  function streamApplication(ref, onDone) {
    var logArea     = ref.logArea;
    var statusBadge = ref.statusBadge;
    var statusDot   = ref.statusDot;
    var companyRole = ref.companyRole;
    var appId       = ref.appId;

    logArea.classList.remove('hidden');
    setStatus(statusBadge, statusDot, 'in_progress');

    var done        = false;
    var eventSource = null;
    var timeoutId   = null;

    function finish(status) {
      if (done) return;
      done = true;
      clearTimeout(timeoutId);
      if (eventSource) eventSource.close();
      onDone(status);
    }

    function resetTimeout() {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(function () {
        appendLog(logArea, '⚠️ No events for 90s — agent may be on a slow page...', 'warn');
      }, 90000);
    }

    try {
      eventSource = new EventSource('/apply/stream/' + appId);
      resetTimeout();

      eventSource.onmessage = function (e) {
        resetTimeout();
        var event;
        try { event = JSON.parse(e.data); } catch (err) {
          appendLog(logArea, 'Raw: ' + e.data, 'info'); return;
        }

        handleEvent(event, ref);

        var t = (event.type || '').toUpperCase();
        if (t === 'COMPLETED' || t === 'COMPLETE') {
          var finalStatus = statusBadge.textContent.includes('Submitted') ? 'submitted' : 'failed';
          setTimeout(function () { finish(finalStatus); }, 500);
        }
        if (t === 'ERROR') {
          setTimeout(function () { finish('failed'); }, 500);
        }
      };

      eventSource.onerror = function () {
        // EventSource fires onerror when the stream naturally closes after COMPLETED
        var cur = statusBadge.textContent;
        if (!cur.includes('Submitted') && !cur.includes('Failed')) {
          setStatus(statusBadge, statusDot, 'failed');
          appendLog(logArea, '❌ Connection lost.', 'error');
          finish('failed');
        } else {
          finish(cur.includes('Submitted') ? 'submitted' : 'failed');
        }
      };

    } catch (err) {
      appendLog(logArea, '❌ Cannot connect: ' + err.message, 'error');
      setStatus(statusBadge, statusDot, 'failed');
      finish('failed');
    }
  }

  // ── Handle individual SSE event ────────────────────────────────────────────

  function handleEvent(event, ref) {
    var logArea     = ref.logArea;
    var statusBadge = ref.statusBadge;
    var statusDot   = ref.statusDot;
    var companyRole = ref.companyRole;
    var type        = (event.type || 'LOG').toUpperCase();

    switch (type) {

      case 'STARTED':
        appendLog(logArea, '🚀 Agent started. Run: ' + (event.runId || '...'), 'action');
        break;

      case 'STREAMING_URL': {
        var sUrl = event.streamingUrl || event.streaming_url || event.url;
        if (sUrl) {
          if (ref.browserContainer && ref.iframe) {
            ref.browserContainer.classList.remove('hidden');

            // Update the fallback link regardless
            if (ref.liveViewLink) ref.liveViewLink.href = sUrl;

            // Try embedding in iframe; after 5s check if it actually loaded anything
            ref.iframe.src = sUrl;
            setTimeout(function() {
              try {
                // If we can read contentDocument, it's same-origin — check if empty
                var doc = ref.iframe.contentDocument || (ref.iframe.contentWindow && ref.iframe.contentWindow.document);
                if (!doc || !doc.body || doc.body.innerHTML.trim() === '') {
                  if (ref.iframeFallback) ref.iframeFallback.classList.remove('hidden');
                }
                // else: same-origin content loaded fine — no fallback needed
              } catch (e) {
                // SecurityError = cross-origin iframe loaded successfully (content is there)
                // Do NOT show fallback — the live view is rendering
              }
            }, 5000);

            appendLog(logArea, '📺 Live browser view loading...', 'success');
          }
        }
        break;
      }

      case 'HEARTBEAT':
        appendLog(logArea, '· agent heartbeat', 'info');
        break;

      case 'PROGRESS':
        appendLog(logArea, '▶ ' + (event.purpose || event.message || 'Working...'), 'action');
        break;

      case 'COMPLETED':
      case 'COMPLETE': {
        var raw = event.resultJson || event.result || event.output || {};
        var result;
        if (typeof raw === 'string') {
          try { result = JSON.parse(raw); } catch (e) { result = {}; }
        } else {
          result = raw;
        }
        handleComplete(result, event, logArea, statusBadge, statusDot, companyRole);
        break;
      }

      case 'ERROR':
        appendLog(logArea, '❌ Error: ' + (event.error || event.message || JSON.stringify(event)), 'error');
        setStatus(statusBadge, statusDot, 'failed');
        break;

      case 'ACTION':
        appendLog(logArea, '▶ ' + (event.description || event.message || JSON.stringify(event)), 'action');
        break;

      case 'NAVIGATION':
        appendLog(logArea, '→ ' + (event.url || event.message || '...'), 'nav');
        break;

      case 'SCREENSHOT':
        appendLog(logArea, '📸 Screenshot captured', 'info');
        break;

      case 'THINKING':
        appendLog(logArea, '💭 ' + (event.message || 'Thinking...'), 'info');
        break;

      default:
        var msg = event.purpose || event.message || event.description;
        if (msg) {
          appendLog(logArea, '· ' + msg, 'info');
        } else if (Object.keys(event).length > 1) {
          appendLog(logArea, '[' + type + '] ' + JSON.stringify(event).substring(0, 120), 'info');
        }
        break;
    }
  }

  // ── Handle COMPLETED result ────────────────────────────────────────────────

  function handleComplete(result, rawEvent, logArea, statusBadge, statusDot, companyRole) {
    // TinyFish COMPLETED: result may be { status, output, blockers, ... }
    // or the whole resultJson may contain application outcome info
    var agentStatus = (result.status || rawEvent.status || 'submitted').toLowerCase();

    if (agentStatus === 'submitted' || agentStatus === 'completed' || agentStatus === 'success') {
      setStatus(statusBadge, statusDot, 'submitted');
      appendLog(logArea, '✅ Application submitted successfully!', 'success');
      if (result.confirmation) appendLog(logArea, '📧 Confirmation: ' + result.confirmation, 'success');
    } else if (agentStatus === 'blocked' || agentStatus === 'captcha') {
      setStatus(statusBadge, statusDot, 'failed');
      appendLog(logArea, '🚫 Blocked: ' + (result.blockers || result.reason || 'CAPTCHA or auth required'), 'error');
    } else if (agentStatus === 'failed' || agentStatus === 'error') {
      setStatus(statusBadge, statusDot, 'failed');
      appendLog(logArea, '❌ Failed: ' + (result.reason || result.blockers || 'Unknown reason'), 'error');
    } else {
      // Unknown status — treat as submitted (agent completed the task)
      setStatus(statusBadge, statusDot, 'submitted');
      appendLog(logArea, '✅ Agent completed the task.', 'success');
      if (result.output) appendLog(logArea, '📋 Output: ' + String(result.output).substring(0, 200), 'info');
    }

    if (result.company || result.role) {
      companyRole.textContent = (result.company || '') + (result.role ? ' · ' + result.role : '');
    }

    if (result.steps_completed && result.steps_completed.length) {
      appendLog(logArea, '📋 Steps: ' + result.steps_completed.join(' → '), 'info');
    }
  }

  // ── UI helpers ─────────────────────────────────────────────────────────────

  function appendLog(container, text, type) {
    var colors = {
      action:  '#60a5fa',
      nav:     '#c084fc',
      success: '#34d399',
      error:   '#f87171',
      warn:    '#fbbf24',
      info:    '#94a3b8',
    };
    var line = document.createElement('div');
    line.style.cssText = 'display:flex;align-items:flex-start;gap:6px;font-family:monospace;font-size:0.72rem;color:' + (colors[type] || colors.info);
    line.innerHTML = '<span style="opacity:0.4;color:#475569;flex-shrink:0">' + ts() + '</span>'
      + '<span style="word-break:break-all">' + esc(text) + '</span>';
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  }

  function setStatus(badge, dot, status) {
    var classes = {
      pending:     'background:rgba(71,85,105,0.4);color:#94a3b8',
      in_progress: 'background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3)',
      submitted:   'background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.3)',
      failed:      'background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.3)',
    };
    var labels = {
      pending:     '⏸ Pending',
      in_progress: '⏳ In Progress',
      submitted:   '✅ Submitted',
      failed:      '❌ Failed',
    };
    badge.style.cssText = 'margin-left:0.75rem;flex-shrink:0;padding:0.2rem 0.6rem;font-size:0.72rem;font-weight:700;border-radius:9999px;' + (classes[status] || classes.pending);
    badge.textContent = labels[status] || '⏸ Pending';

    dot.className = 'status-dot w-2.5 h-2.5 rounded-full shrink-0 ' + status;
    dot.style.animation = status === 'in_progress' ? 'pulse 1s ease-in-out infinite' : 'none';
  }

  function showToast(message, type) {
    // Prefer global toast from base.html, fall back to own implementation
    if (window.showToast && window.showToast !== showToast) {
      window.showToast(message, type); return;
    }
    var toast = document.createElement('div');
    var bg = type==='error'?'rgba(239,68,68,0.9)':type==='success'?'rgba(16,185,129,0.9)':'rgba(59,130,246,0.9)';
    toast.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:50;padding:0.75rem 1.25rem;border-radius:0.75rem;color:white;font-size:0.875rem;font-weight:500;box-shadow:0 25px 50px rgba(0,0,0,0.3);background:'+bg;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function(){ toast.style.opacity='0'; toast.style.transition='opacity 0.5s'; setTimeout(function(){ toast.remove(); },500); }, 4500);
  }

  function resetLaunchBtn() {
    launchBtn.disabled = false;
    launchText.textContent = 'Launch Agent';
    launchIcon.innerHTML = '🤖';
    launchBtn.style.opacity = '1';
  }

  function ts() {
    return new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function esc(str) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(String(str)));
    return d.innerHTML;
  }

});

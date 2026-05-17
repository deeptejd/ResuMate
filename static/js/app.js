function getCsrfToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(name + '=')) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }
  return '';
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(function(t) {
    t.classList.remove('tab-active');
  });
  document.querySelectorAll('.tab-panel').forEach(function(p) {
    p.classList.remove('tab-panel-active');
  });
  var btn = document.getElementById('tab-btn-' + name);
  if (btn) btn.classList.add('tab-active');
  var panel = document.getElementById('panel-' + name);
  if (panel) panel.classList.add('tab-panel-active');
}

function copyText(elementId) {
  var el = document.getElementById(elementId);
  if (!el) return;
  var text = el.innerText || el.textContent;
  navigator.clipboard.writeText(text).then(function() {
    var buttons = document.querySelectorAll('[onclick="copyText(\'' + elementId + '\')"]');
    buttons.forEach(function(btn) {
      var original = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(function() { btn.textContent = original; }, 2000);
    });
  });
}

function toggleUpdateJd() {
  var panel = document.getElementById('updateJdPanel');
  if (!panel) return;
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

var tabProgress = {
  match:  { pct: 0,  label: 'Analysing keyword match...'    },
  cover:  { pct: 20, label: 'Writing cover letter...'       },
  decode: { pct: 40, label: 'Decoding job description...'   },
  flags:  { pct: 60, label: 'Scanning for red flags...'     },
  prep:   { pct: 80, label: 'Building interview prep...'    },
};

var tabFieldMap = {
  match:  'content-match',
  cover:  'content-cover',
  decode: 'content-decode',
  flags:  'content-flags',
  prep:   'content-prep',
};

function setDot(tabKey, state) {
  var dot = document.getElementById('dot-' + tabKey);
  if (!dot) return;
  dot.className = 'tab-dot';
  if (state === 'streaming') dot.classList.add('dot-streaming');
  if (state === 'done') dot.classList.add('dot-active');
}

function startAnalysisStream(jobId) {
  var progressBar = document.getElementById('progressBar');
  var progressFill = document.getElementById('progressFill');
  var progressLabel = document.getElementById('progressLabel');
  if (progressBar) progressBar.style.display = 'block';

  var source = new EventSource('/jobs/' + jobId + '/stream/');
  var currentTab = null;

  source.addEventListener('tab_start', function(e) {
    var data = JSON.parse(e.data);
    currentTab = data.tab;
    var info = tabProgress[currentTab];
    if (info) {
      if (progressFill) progressFill.style.width = info.pct + '%';
      if (progressLabel) progressLabel.textContent = info.label;
    }
    setDot(currentTab, 'streaming');
    switchTab(currentTab);
    var loading = document.getElementById('loading-' + currentTab);
    if (loading) loading.style.display = 'none';
    var content = document.getElementById('content-' + currentTab);
    if (content) content.innerHTML = '<pre class="analysis-text" id="stream-' + currentTab + '"></pre>';
  });

  source.addEventListener('token', function(e) {
    var data = JSON.parse(e.data);
    var el = document.getElementById('stream-' + data.tab);
    if (el) el.textContent += data.chunk;
  });

  source.addEventListener('tab_complete', function(e) {
    var data = JSON.parse(e.data);
    setDot(data.tab, 'done');
  });

  source.addEventListener('analysis_complete', function(e) {
    source.close();
    if (progressFill) progressFill.style.width = '100%';
    if (progressLabel) progressLabel.textContent = 'Analysis complete.';
    setTimeout(function() {
      if (progressBar) progressBar.style.display = 'none';
    }, 2000);

    var notGenerated = document.getElementById('resumeNotGenerated');
    if (notGenerated) {
      notGenerated.innerHTML = '<p class="tailored-intro">Analysis complete. Generate a rewritten version of your resume tailored specifically for this role.</p><button class="btn btn-primary" onclick="startResumeGeneration()">Generate tailored resume</button>';
    }

    window.location.reload();
  });

  source.addEventListener('error', function(e) {
    console.error('SSE error', e);
  });

  source.onerror = function() {
    source.close();
    if (progressLabel) progressLabel.textContent = 'Connection error. Please refresh.';
  };
}

function startResumeGeneration() {
  var jobIdEl = document.getElementById('jobId');
  if (!jobIdEl) return;
  var jobId = jobIdEl.dataset.id;

  var generating = document.getElementById('resumeGenerating');
  var notGenerated = document.getElementById('resumeNotGenerated');
  var preview = document.getElementById('resumePreview');
  var approved = document.getElementById('resumeApproved');

  if (notGenerated) notGenerated.style.display = 'none';
  if (preview) preview.style.display = 'none';
  if (approved) approved.style.display = 'none';
  if (generating) generating.style.display = 'block';

  var streamText = document.getElementById('resumeStreamText');
  if (streamText) streamText.textContent = '';

  var source = new EventSource('/jobs/' + jobId + '/resume/stream/');

  source.addEventListener('token', function(e) {
    var data = JSON.parse(e.data);
    if (streamText) streamText.textContent += data.chunk;
  });

  source.addEventListener('complete', function(e) {
    source.close();
    window.location.reload();
  });

  source.addEventListener('error', function(e) {
    source.close();
    if (generating) generating.style.display = 'none';
    if (notGenerated) {
      notGenerated.style.display = 'block';
      notGenerated.innerHTML += '<p style="color:var(--red);font-size:13px;margin-top:8px;">Generation failed. Please try again.</p>';
    }
  });

  source.onerror = function() {
    source.close();
  };
}

function approveResume(jobId) {
  fetch('/jobs/' + jobId + '/resume/approve/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json',
    },
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.ok) {
      window.location.reload();
    }
  })
  .catch(function(err) {
    console.error('Approve failed', err);
  });
}

function initJobDetail() {
  var needsEl = document.getElementById('needsAnalysis');
  var jobIdEl = document.getElementById('jobId');
  if (!needsEl || !jobIdEl) return;

  var needsAnalysis = needsEl.dataset.value === 'true';
  var jobId = jobIdEl.dataset.id;

  if (needsAnalysis) {
    startAnalysisStream(jobId);
  }
}
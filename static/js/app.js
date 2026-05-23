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
    if (content) content.innerHTML = '<div class="analysis-streaming" id="stream-' + currentTab + '"></div>';
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

function formatAnalysisHtml(tabKey) {
  var contentDiv = document.getElementById('content-' + tabKey);
  if (!contentDiv) return;

  var rendered = contentDiv.querySelector('.analysis-rendered');
  if (!rendered) return;

  if (rendered.dataset.formatted === 'true') return;

  if (tabKey === 'match') {
    var headings = Array.from(rendered.querySelectorAll('h2, h3'));
    headings.forEach(function(heading) {
      var text = heading.textContent.toLowerCase();
      var isFound = text.indexOf('found') !== -1 || text.indexOf('✓') !== -1;
      var isMissing = text.indexOf('missing') !== -1 || text.indexOf('✗') !== -1;

      if (isFound || isMissing) {
        var nextUl = heading.nextElementSibling;
        if (nextUl && nextUl.tagName === 'UL') {
          nextUl.classList.add('chips-list');
          var lis = Array.from(nextUl.querySelectorAll('li'));
          lis.forEach(function(li) {
            var strong = li.querySelector('strong');
            if (strong) {
              var term = strong.textContent.trim();
              var restText = li.innerHTML.replace(strong.outerHTML, '').replace(/^[\s—\-–:]+/, '');
              
              var chipSpan = document.createElement('span');
              chipSpan.className = 'keyword-chip ' + (isFound ? 'keyword-chip-found' : 'keyword-chip-missing');
              chipSpan.textContent = term;

              var contextSpan = document.createElement('span');
              contextSpan.className = 'keyword-context';
              contextSpan.innerHTML = restText;

              li.innerHTML = '';
              li.appendChild(chipSpan);
              if (restText.trim()) {
                li.appendChild(contextSpan);
              }
            }
          });
        }
      }
    });
  } else if (tabKey === 'decode') {
    var headings = Array.from(rendered.querySelectorAll('h2, h3'));
    headings.forEach(function(heading) {
      var text = heading.textContent.toLowerCase();
      if (text.indexOf('decoded') !== -1) {
        var nextUl = heading.nextElementSibling;
        if (nextUl && nextUl.tagName === 'UL') {
          var lis = Array.from(nextUl.querySelectorAll('li'));
          nextUl.style.listStyleType = 'none';
          nextUl.style.padding = '0';
          nextUl.style.margin = '1rem 0';
          
          lis.forEach(function(li) {
            li.className = 'phrase-card';
            var strong = li.querySelector('strong');
            if (strong) {
              var phrase = strong.textContent.trim();
              var html = li.innerHTML;
              var rest = html.replace(strong.outerHTML, '');
              var cleanRest = rest.replace(/^[\s&rarr;→\-–—]+/, '').trim();
              
              var phraseSpan = document.createElement('span');
              phraseSpan.className = 'phrase-term';
              phraseSpan.textContent = phrase;
              
              var arrowSpan = document.createElement('span');
              arrowSpan.className = 'phrase-arrow';
              arrowSpan.innerHTML = ' &rarr; ';
              
              var meaningSpan = document.createElement('span');
              meaningSpan.className = 'phrase-meaning';
              meaningSpan.innerHTML = cleanRest;
              
              li.innerHTML = '';
              li.appendChild(phraseSpan);
              li.appendChild(arrowSpan);
              li.appendChild(meaningSpan);
            }
          });
        }
      }
    });
  } else if (tabKey === 'prep') {
    var elements = Array.from(rendered.children);
    var accordionContainer = document.createElement('div');
    accordionContainer.className = 'accordions-container';

    var currentItem = null;
    var currentHeader = null;
    var currentBody = null;
    
    var studyTopicsHeading = null;
    var studyTopicsList = null;

    elements.forEach(function(el) {
      var text = el.textContent.toLowerCase();
      var isStudyTopics = text.indexOf('topics to study') !== -1;
      
      if (isStudyTopics) {
        studyTopicsHeading = el;
        var next = el.nextElementSibling;
        if (next && next.tagName === 'UL') {
          studyTopicsList = next;
        }
      }
    });

    if (studyTopicsList) {
      studyTopicsList.classList.add('chips-list');
      var studyLis = Array.from(studyTopicsList.querySelectorAll('li'));
      studyLis.forEach(function(li) {
        var strong = li.querySelector('strong');
        if (strong) {
          var term = strong.textContent.trim();
          var restText = li.innerHTML.replace(strong.outerHTML, '').replace(/^[\s—\-–:]+/, '');
          
          var chipSpan = document.createElement('span');
          chipSpan.className = 'keyword-chip keyword-chip-found';
          chipSpan.style.borderColor = 'var(--accent-strong)';
          chipSpan.style.color = 'var(--accent)';
          chipSpan.style.backgroundColor = 'var(--accent-dim)';
          chipSpan.textContent = term;

          var contextSpan = document.createElement('span');
          contextSpan.className = 'keyword-context';
          contextSpan.innerHTML = restText;

          li.innerHTML = '';
          li.appendChild(chipSpan);
          if (restText.trim()) {
            li.appendChild(contextSpan);
          }
        }
      });
    }

    var elementsToGroup = [];
    var grouping = false;

    elements.forEach(function(el) {
      var tagName = el.tagName;
      var text = el.textContent.toLowerCase();
      var isQuestionHeader = tagName === 'H2' && (text.indexOf('question') !== -1 || text.indexOf('wildcard') !== -1);
      
      if (isQuestionHeader) {
        grouping = true;
        if (currentItem) {
          currentItem.appendChild(currentBody);
          accordionContainer.appendChild(currentItem);
        }
        
        currentItem = document.createElement('div');
        currentItem.className = 'accordion-item';
        
        currentHeader = document.createElement('div');
        currentHeader.className = 'accordion-header';
        
        var titleSpan = document.createElement('span');
        titleSpan.textContent = el.textContent.replace('⚡', '').trim();
        if (text.indexOf('wildcard') !== -1) {
          titleSpan.innerHTML = '⚡ ' + titleSpan.textContent;
        }
        currentHeader.appendChild(titleSpan);
        
        var arrowSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        arrowSvg.setAttribute('class', 'accordion-trigger-icon');
        arrowSvg.setAttribute('viewBox', '0 0 24 24');
        arrowSvg.setAttribute('fill', 'none');
        arrowSvg.setAttribute('stroke', 'currentColor');
        arrowSvg.setAttribute('stroke-width', '2');
        arrowSvg.setAttribute('stroke-linecap', 'round');
        arrowSvg.setAttribute('stroke-linejoin', 'round');
        arrowSvg.innerHTML = '<polyline points="6 9 12 15 18 9"></polyline>';
        currentHeader.appendChild(arrowSvg);
        
        currentItem.appendChild(currentHeader);
        
        currentBody = document.createElement('div');
        currentBody.className = 'accordion-content';
        
        (function(item, header) {
          header.addEventListener('click', function() {
            var isActive = item.classList.contains('active');
            accordionContainer.querySelectorAll('.accordion-item').forEach(function(it) {
              it.classList.remove('active');
            });
            if (!isActive) {
              item.classList.add('active');
            }
          });
        })(currentItem, currentHeader);

        elementsToGroup.push(el);
      } else if (grouping) {
        if (el.tagName === 'HR') {
          elementsToGroup.push(el);
        } else {
          currentBody.appendChild(el.cloneNode(true));
          elementsToGroup.push(el);
        }
      }
    });

    if (currentItem) {
      currentItem.appendChild(currentBody);
      accordionContainer.appendChild(currentItem);
    }

    if (grouping) {
      elementsToGroup.forEach(function(el) {
        if (el.parentNode) {
          el.parentNode.removeChild(el);
        }
      });
      rendered.appendChild(accordionContainer);
    }
  }

  rendered.dataset.formatted = 'true';
}

function initJobDetail() {
  var needsEl = document.getElementById('needsAnalysis');
  var jobIdEl = document.getElementById('jobId');
  if (!needsEl || !jobIdEl) return;

  var needsAnalysis = needsEl.dataset.value === 'true';
  var jobId = jobIdEl.dataset.id;

  if (!needsAnalysis) {
    switchTab('match');
    document.querySelectorAll('.tab-dot').forEach(function(dot) {
      var id = dot.id.replace('dot-', '');
      var content = document.getElementById('content-' + id);
      if (content && content.querySelector('.analysis-rendered')) {
        dot.classList.add('dot-active');
        formatAnalysisHtml(id);
      }
    });
  }

  if (needsAnalysis) {
    startAnalysisStream(jobId);
  }
}

function initDashboardFilters() {
  var searchInput = document.getElementById('jobSearch');
  var clearSearchBtn = document.getElementById('clearSearch');
  var companySelect = document.getElementById('filterCompany');
  var scoreSelect = document.getElementById('filterScore');
  var statusSelect = document.getElementById('filterStatus');
  var sortSelect = document.getElementById('sortJobs');
  var resetBtn = document.getElementById('btnResetFilters');
  var resetLnk = document.getElementById('lnkResetFilters');
  var jobsGrid = document.getElementById('jobsGrid');
  var noJobsFallback = document.getElementById('noMatchingJobs');

  if (!jobsGrid) return;

  var jobCards = Array.from(document.querySelectorAll('.job-card-wrap'));
  if (jobCards.length === 0) return;

  // Populate company options
  var companies = new Set();
  jobCards.forEach(function(card) {
    var comp = card.dataset.company;
    if (comp) {
      companies.add(comp.trim());
    }
  });

  var sortedCompanies = Array.from(companies).sort(function(a, b) {
    return a.localeCompare(b, undefined, { sensitivity: 'base' });
  });

  sortedCompanies.forEach(function(comp) {
    var opt = document.createElement('option');
    opt.value = comp;
    opt.textContent = comp;
    companySelect.appendChild(opt);
  });

  function applyFiltersAndSort() {
    var query = searchInput.value.trim().toLowerCase();
    var selectedCompany = companySelect.value;
    var selectedScore = scoreSelect.value;
    var selectedStatus = statusSelect.value;
    var sortBy = sortSelect.value;

    // Search bar clear button
    if (clearSearchBtn) {
      clearSearchBtn.style.display = query ? 'block' : 'none';
    }

    // Reset button visibility
    var isFiltered = query || selectedCompany || selectedScore || selectedStatus;
    if (resetBtn) {
      resetBtn.style.display = isFiltered ? 'inline-flex' : 'none';
    }

    // Filter job cards
    jobCards.forEach(function(card) {
      var title = (card.dataset.title || '').toLowerCase();
      var company = (card.dataset.company || '').toLowerCase();
      var jd = (card.dataset.jd || '').toLowerCase();
      var score = parseInt(card.dataset.score || '-1', 10);
      var isReady = card.dataset.ready === 'true';
      var isComplete = card.dataset.complete === 'true';

      var matchesSearch = !query || title.indexOf(query) !== -1 || company.indexOf(query) !== -1 || jd.indexOf(query) !== -1;
      var matchesCompany = !selectedCompany || card.dataset.company === selectedCompany;

      var matchesScore = true;
      if (selectedScore === 'high') {
        matchesScore = score >= 70;
      } else if (selectedScore === 'mid') {
        matchesScore = score >= 45 && score < 70;
      } else if (selectedScore === 'low') {
        matchesScore = score >= 0 && score < 45;
      } else if (selectedScore === 'pending') {
        matchesScore = score === -1;
      }

      var matchesStatus = true;
      if (selectedStatus === 'ready') {
        matchesStatus = isReady;
      } else if (selectedStatus === 'complete') {
        matchesStatus = isComplete;
      } else if (selectedStatus === 'pending') {
        matchesStatus = !isComplete && !isReady;
      }

      var isVisible = matchesSearch && matchesCompany && matchesScore && matchesStatus;

      if (isVisible) {
        if (card.style.display === 'none') {
          card.style.display = '';
          // Trigger CSS reflow to restart the animation
          card.classList.remove('fade-in');
          void card.offsetWidth;
          card.classList.add('fade-in');
        } else if (!card.classList.contains('fade-in')) {
          card.classList.add('fade-in');
        }
      } else {
        card.style.display = 'none';
        card.classList.remove('fade-in');
      }
    });

    // Sort job cards
    var sortedCards = jobCards.slice().sort(function(a, b) {
      if (sortBy === 'date-desc') {
        return parseFloat(b.dataset.created) - parseFloat(a.dataset.created);
      } else if (sortBy === 'date-asc') {
        return parseFloat(a.dataset.created) - parseFloat(b.dataset.created);
      } else if (sortBy === 'score-desc') {
        var scoreA = parseInt(a.dataset.score || '-1', 10);
        var scoreB = parseInt(b.dataset.score || '-1', 10);
        return scoreB - scoreA;
      } else if (sortBy === 'score-asc') {
        var scoreA = parseInt(a.dataset.score || '-1', 10);
        var scoreB = parseInt(b.dataset.score || '-1', 10);
        // Put pending scores (-1) at the end
        var valA = scoreA === -1 ? 999999 : scoreA;
        var valB = scoreB === -1 ? 999999 : scoreB;
        return valA - valB;
      } else if (sortBy === 'company-asc') {
        var compA = a.dataset.company || '';
        var compB = b.dataset.company || '';
        return compA.localeCompare(compB, undefined, { sensitivity: 'base' });
      } else if (sortBy === 'title-asc') {
        var titleA = a.dataset.title || '';
        var titleB = b.dataset.title || '';
        return titleA.localeCompare(titleB, undefined, { sensitivity: 'base' });
      }
      return 0;
    });

    sortedCards.forEach(function(card) {
      jobsGrid.appendChild(card);
    });

    // Show fallback if no visible results
    var visibleCards = jobCards.filter(function(card) {
      return card.style.display !== 'none';
    });

    if (noJobsFallback) {
      noJobsFallback.style.display = visibleCards.length === 0 ? 'block' : 'none';
    }
  }

  function resetAll() {
    searchInput.value = '';
    companySelect.value = '';
    scoreSelect.value = '';
    statusSelect.value = '';
    sortSelect.value = 'date-desc';
    applyFiltersAndSort();
  }

  // Event Listeners
  searchInput.addEventListener('input', applyFiltersAndSort);
  companySelect.addEventListener('change', applyFiltersAndSort);
  scoreSelect.addEventListener('change', applyFiltersAndSort);
  statusSelect.addEventListener('change', applyFiltersAndSort);
  sortSelect.addEventListener('change', applyFiltersAndSort);

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', function() {
      searchInput.value = '';
      applyFiltersAndSort();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', resetAll);
  }

  if (resetLnk) {
    resetLnk.addEventListener('click', function(e) {
      e.preventDefault();
      resetAll();
    });
  }

  // Initial call to sort cards and establish state
  applyFiltersAndSort();
}

// Initialize filters
initDashboardFilters();
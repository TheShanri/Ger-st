document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const uploadForm = document.getElementById('upload-form');
  const helperText = document.getElementById('file-helper');
  const loadingOverlay = document.getElementById('loading-overlay');
  const statusText = document.getElementById('status-text');
  const progressFill = document.getElementById('progress-fill');
  const tabButtons = document.querySelectorAll('.tab-button');
  const uploadPanel = document.getElementById('upload-panel');
  const textPanel = document.getElementById('text-panel');
  const textInput = document.getElementById('text-input');
  const themeTemplate = document.getElementById('theme-switcher-template');
  const viewSettingsTemplate = document.getElementById('view-settings-template');

  const funStatuses = [
    'Loading the German brain...',
    'Untangling the sentence bracket...',
    'Searching for the verb at the end...',
    'Consulting Kafka...',
    'Polishing the Umlauts...',
    'Calculating declensions...',
  ];

  let statusInterval;
  let currentMode = 'upload';
  let themeSelect;
  let allowThemeStorage = true;

  const startLoadingFeedback = () => {
    if (!loadingOverlay) return;

    loadingOverlay.classList.add('visible');

    if (statusInterval) {
      clearInterval(statusInterval);
    }

    if (statusText) {
      let statusIndex = 0;
      statusText.innerText = funStatuses[statusIndex];
      statusInterval = setInterval(() => {
        statusIndex = (statusIndex + 1) % funStatuses.length;
        statusText.innerText = funStatuses[statusIndex];
      }, 1500);
    }

    if (progressFill) {
      progressFill.style.transition = 'none';
      progressFill.style.width = '0%';
      requestAnimationFrame(() => {
        progressFill.style.transition = 'width 15s linear';
        progressFill.style.width = '90%';
        const wrapper = progressFill.parentElement;
        if (wrapper?.setAttribute) {
          wrapper.setAttribute('aria-valuenow', '90');
        }
      });
    }
  };

  const setMode = (mode) => {
    currentMode = mode;

    tabButtons.forEach((button) => {
      const isActive = button.dataset.mode === mode;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-selected', String(isActive));
    });

    if (uploadPanel) uploadPanel.hidden = mode !== 'upload';
    if (textPanel) textPanel.hidden = mode !== 'paste';

    if (fileInput) {
      fileInput.required = mode === 'upload';
      fileInput.disabled = mode !== 'upload';
    }

    if (textInput) {
      textInput.required = mode === 'paste';
      textInput.disabled = mode !== 'paste';
    }
  };

  if (tabButtons.length) {
    tabButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const nextMode = button.dataset.mode || 'upload';
        setMode(nextMode);
      });
    });
  }

  setMode('upload');

  const applyTheme = (theme) => {
    const nextTheme = theme || 'light';
    document.body.setAttribute('data-theme', nextTheme);

    if (themeSelect && themeSelect.value !== nextTheme) {
      themeSelect.value = nextTheme;
    }

    if (allowThemeStorage) {
      try {
        localStorage.setItem('gerust-theme', nextTheme);
      } catch (error) {
        allowThemeStorage = false;
        console.warn('Unable to persist theme preference', error);
      }
    }
  };

  const setupThemeSwitcher = () => {
    const themeContainer = document.getElementById('theme-switcher-container');
    if (themeContainer && themeTemplate) {
      const clone = themeTemplate.content.cloneNode(true);
      themeContainer.replaceWith(clone);
      themeSelect = document.getElementById('theme-select');

      if (themeSelect) {
        themeSelect.addEventListener('change', (event) => {
          applyTheme(event.target.value);
        });
      }
    }

    let savedTheme = null;

    if (allowThemeStorage) {
      try {
        savedTheme = localStorage.getItem('gerust-theme');
      } catch (error) {
        allowThemeStorage = false;
        console.warn('Unable to read saved theme', error);
      }
    }

    applyTheme(savedTheme || document.body.getAttribute('data-theme'));
  };

  const mountViewSettings = () => {
    const viewSettingsContainer = document.getElementById('view-settings-container');
    if (viewSettingsContainer && viewSettingsTemplate) {
      const clone = viewSettingsTemplate.content.cloneNode(true);
      viewSettingsContainer.replaceWith(clone);
    }
  };

  if (dropZone && fileInput && uploadForm) {
    const setHelper = (message) => {
      if (helperText) helperText.innerText = message;
    };

    dropZone.addEventListener('click', () => {
      if (currentMode !== 'upload') return;
      fileInput.click();
    });

    dropZone.addEventListener('dragover', (event) => {
      if (currentMode !== 'upload') return;
      event.preventDefault();
      dropZone.classList.add('dragover');
      setHelper('Drop your PDF to start analyzing');
    });

    dropZone.addEventListener('dragleave', () => {
      if (currentMode !== 'upload') return;
      dropZone.classList.remove('dragover');
      setHelper('Drag & drop a PDF or click to browse');
    });

    dropZone.addEventListener('drop', (event) => {
      if (currentMode !== 'upload') return;
      event.preventDefault();
      dropZone.classList.remove('dragover');
      if (event.dataTransfer?.files?.length) {
        fileInput.files = event.dataTransfer.files;
        setHelper(event.dataTransfer.files[0].name);
        startLoadingFeedback();
        uploadForm.submit();
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files?.length) {
        setHelper(fileInput.files[0].name);
        startLoadingFeedback();
        uploadForm.submit();
      }
    });

    uploadForm.addEventListener('submit', () => {
      startLoadingFeedback();
    });
  }

  const setupHighlightToggles = () => {
    const toggles = [
      { id: 'toggle-masc', className: 'show-masc' },
      { id: 'toggle-fem', className: 'show-fem' },
      { id: 'toggle-neut', className: 'show-neut' },
      { id: 'toggle-verbs', className: 'show-verbs' },
      { id: 'toggle-nom', className: 'show-nom' },
      { id: 'toggle-acc', className: 'show-acc' },
      { id: 'toggle-dat', className: 'show-dat' },
      { id: 'toggle-gen', className: 'show-gen' },
      { id: 'toggle-adj', className: 'show-adj' },
      { id: 'toggle-plur', className: 'show-plur' },
    ];

    toggles.forEach(({ id, className }) => {
      const checkbox = document.getElementById(id);
      if (!checkbox) return;

      const updateClass = () => {
        document.body.classList.toggle(className, checkbox.checked);
      };

      checkbox.addEventListener('change', updateClass);
      updateClass();
    });
  };

  setupThemeSwitcher();
  mountViewSettings();
  setupHighlightToggles();
});

function updateSidebar(element) {
  const tokens = document.querySelectorAll('.token');
  tokens.forEach((t) => t.classList.remove('active'));
  element.classList.add('active');

  const text = element.innerText;
  const lemma = element.getAttribute('data-lemma');
  const trans = element.getAttribute('data-trans');
  const grammar = element.getAttribute('data-grammar');

  const wordEl = document.getElementById('sb-word');
  const lemmaEl = document.getElementById('sb-lemma');
  const meaningEl = document.getElementById('sb-meaning');
  const grammarEl = document.getElementById('sb-grammar');
  const reasonBox = document.getElementById('sb-reason-box');

  if (wordEl) wordEl.innerText = text;
  if (lemmaEl) lemmaEl.innerText = `Base: ${lemma}`;
  if (meaningEl) meaningEl.innerText = trans;
  if (grammarEl) grammarEl.innerHTML = grammar;

  if (reasonBox) {
    const reason = element.getAttribute('data-reason');
    if (reason) {
      reasonBox.hidden = false;
      reasonBox.innerText = reason;
    } else {
      reasonBox.hidden = true;
      reasonBox.innerText = '';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const uploadForm = document.getElementById('upload-form');
  const helperText = document.getElementById('file-helper');
  const loadingOverlay = document.getElementById('loading-overlay');
  const statusText = document.getElementById('status-text');
  const progressFill = document.getElementById('progress-fill');

  const funStatuses = [
    'Loading the German brain...',
    'Untangling the sentence bracket...',
    'Searching for the verb at the end...',
    'Consulting Kafka...',
    'Polishing the Umlauts...',
    'Calculating declensions...',
  ];

  let statusInterval;

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

  if (dropZone && fileInput && uploadForm) {
    const setHelper = (message) => {
      if (helperText) helperText.innerText = message;
    };

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (event) => {
      event.preventDefault();
      dropZone.classList.add('dragover');
      setHelper('Drop your PDF to start analyzing');
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('dragover');
      setHelper('Drag & drop a PDF or click to browse');
    });

    dropZone.addEventListener('drop', (event) => {
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
  const dudenBtn = document.getElementById('btn-duden');

  if (wordEl) wordEl.innerText = text;
  if (lemmaEl) lemmaEl.innerText = `Base: ${lemma}`;
  if (meaningEl) meaningEl.innerText = trans;
  if (grammarEl) grammarEl.innerHTML = grammar;

  if (dudenBtn) {
    const cleanLemma = (lemma || '').replace(/[^\wäöüÄÖÜß]/g, '');
    dudenBtn.href = `https://www.duden.de/suchen/dudenonline/${cleanLemma}`;
  }
}

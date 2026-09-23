document.addEventListener('DOMContentLoaded', function () {
  const dialog = document.getElementById('modal-dialog');
  const modalBody = document.getElementById('modal-body');

  function openModal(url) {
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.text())
      .then(html => {
        modalBody.innerHTML = html;
        dialog.showModal();
        attachFormHandler();
      });
  }

  function attachFormHandler() {
    const form = modalBody.querySelector('form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: new FormData(form),
      }).then(async (r) => {
        const contentType = r.headers.get('Content-Type') || '';
        if (contentType.includes('application/json')) {
          window.location.reload();
        } else {
          modalBody.innerHTML = await r.text();
          attachFormHandler();
        }
      });
    });
  }

  document.querySelectorAll('.modal-trigger').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      openModal(el.getAttribute('href'));
    });
  });

  document.getElementById('modal-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', function (e) {
    if (e.target === dialog) dialog.close();
  });
});
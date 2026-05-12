/* =================================================================
 * Suministros CNCV — UI helpers (modal, toast, navbar, delegation)
 *
 * Se carga con <script src="…/ui.js" defer> en base.html. Todo lo que
 * antes vivía como <script> inline al final del <body> ahora vive aquí.
 *
 * APIs públicas:
 *   window.confirmDialog({title, message, confirmText, cancelText, variant})
 *     -> Promise<boolean>   (true si el usuario confirma)
 *   window.showToast(message, variant)
 *     -> void               variant: 'success'|'danger'|'warning'|'info'
 *
 * Comportamiento declarativo (sin JS por página):
 *   <form data-confirm="¿Eliminar?" data-confirm-variant="danger">
 *   <a    data-confirm="¿Continuar?" data-confirm-variant="warning">
 *   <button data-set-theme="elegant">               // theme switcher
 *   <button data-flash-close>                       // cierra el snackbar padre
 *   <button data-remove-closest="tr">               // elimina el ancestor más cercano que matchee
 *   <select data-auto-submit>                        // submitea el form al cambiar
 * ================================================================= */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    /* ----- Auto-hide flash messages ----- */
    setTimeout(function () {
      document.querySelectorAll('.alert-dismissible').forEach(function (a) {
        a.style.opacity = '0';
        setTimeout(function () { a.remove(); }, 500);
      });
    }, 6000);

    /* ----- Mobile nav toggle ----- */
    var navToggle = document.getElementById('nav-toggle');
    var navContent = document.getElementById('nav-content');
    if (navToggle && navContent) {
      navToggle.addEventListener('click', function () {
        navContent.classList.toggle('hidden');
      });
    }

    /* ----- Theme switcher (delegated) ----- */
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-set-theme]');
      if (!btn) return;
      if (typeof window.setTheme === 'function') {
        window.setTheme(btn.getAttribute('data-set-theme'));
      }
    });

    /* ----- Flash close button (delegated) ----- */
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-flash-close]');
      if (!btn) return;
      var alertEl = btn.closest('.alert-dismissible') || btn.parentElement;
      if (!alertEl) return;
      alertEl.style.opacity = '0';
      setTimeout(function () { alertEl.remove(); }, 300);
    });

    /* ----- Remove closest ancestor (delegated)
            Used by row-builder UIs that let the user discard a row. ----- */
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-remove-closest]');
      if (!btn) return;
      var sel = btn.getAttribute('data-remove-closest');
      var target = sel ? btn.closest(sel) : btn.parentElement;
      if (target) target.remove();
    });

    /* ----- Auto-submit on change (delegated) ----- */
    document.addEventListener('change', function (e) {
      var el = e.target.closest('[data-auto-submit]');
      if (!el) return;
      if (el.form) el.form.submit();
    });

    /* ===================================================
     * Confirmation modal (window.confirmDialog)
     * =================================================== */
    var modal           = document.getElementById('confirm-modal');
    var modalPanel      = document.getElementById('confirm-modal-panel');
    var modalTitle      = document.getElementById('confirm-modal-title');
    var modalMessage    = document.getElementById('confirm-modal-message');
    var modalIcon       = document.getElementById('confirm-modal-icon');
    var modalIconWrap   = document.getElementById('confirm-modal-icon-wrap');
    var modalCancel     = document.getElementById('confirm-modal-cancel');
    var modalConfirm    = document.getElementById('confirm-modal-confirm');

    var VARIANT_CONFIG = {
      danger:  { icon: 'warning',       iconColor: 'text-danger-400',  wrap: 'bg-danger-500/10 border-danger-500/30',
                 btnClasses: 'bg-danger-600 hover:bg-danger-500 text-white border-transparent' },
      warning: { icon: 'priority_high', iconColor: 'text-warning-400', wrap: 'bg-warning-500/10 border-warning-500/30',
                 btnClasses: 'bg-warning-600 hover:bg-warning-500 text-white border-transparent' },
      primary: { icon: 'help',          iconColor: 'text-primary-400', wrap: 'bg-primary-500/10 border-primary-500/30',
                 btnClasses: '' },
    };

    var modalResolver = null;
    var modalLastFocused = null;

    function openModal(opts) {
      var variant = (opts && opts.variant) || 'danger';
      var cfg = VARIANT_CONFIG[variant] || VARIANT_CONFIG.danger;

      modalTitle.textContent   = (opts && opts.title)   || 'Confirmar acción';
      modalMessage.textContent = (opts && opts.message) || '¿Estás seguro?';
      modalCancel.textContent  = (opts && opts.cancelText)  || 'Cancelar';
      modalConfirm.textContent = (opts && opts.confirmText) || 'Confirmar';

      modalIcon.textContent = cfg.icon;
      modalIcon.className   = 'material-symbols-outlined text-xl ' + cfg.iconColor;
      modalIconWrap.className = 'shrink-0 w-12 h-12 rounded-full flex items-center justify-center border ' + cfg.wrap;
      modalConfirm.className = 'btn-elegant btn-primary ' + cfg.btnClasses;

      modalLastFocused = document.activeElement;
      modal.classList.remove('hidden');
      modal.classList.add('flex');
      requestAnimationFrame(function () {
        modalPanel.classList.remove('scale-95', 'opacity-0');
        modalPanel.classList.add('scale-100', 'opacity-100');
      });
      modalConfirm.focus();
    }

    function closeModal(result) {
      modalPanel.classList.add('scale-95', 'opacity-0');
      modalPanel.classList.remove('scale-100', 'opacity-100');
      setTimeout(function () {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        if (modalLastFocused && typeof modalLastFocused.focus === 'function') {
          modalLastFocused.focus();
        }
      }, 180);
      if (modalResolver) {
        var r = modalResolver;
        modalResolver = null;
        r(result);
      }
    }

    if (modal) {
      modalCancel.addEventListener('click', function () { closeModal(false); });
      modalConfirm.addEventListener('click', function () { closeModal(true); });
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal(false);
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeModal(false);
      });

      window.confirmDialog = function (opts) {
        return new Promise(function (resolve) {
          modalResolver = resolve;
          openModal(opts || {});
        });
      };
    }

    /* ===================================================
     * Toast (window.showToast)
     * =================================================== */
    var toastContainer = document.getElementById('toast-container');
    var TOAST_VARIANTS = {
      success: { border: 'border-success-500', text: 'text-success-100', shadow: 'shadow-success-900/20', icon: 'check_circle' },
      danger:  { border: 'border-danger-500',  text: 'text-danger-100',  shadow: 'shadow-danger-900/20',  icon: 'error' },
      warning: { border: 'border-warning-500', text: 'text-warning-100', shadow: 'shadow-warning-900/20', icon: 'warning' },
      info:    { border: 'border-info-500',    text: 'text-info-100',    shadow: 'shadow-info-900/20',    icon: 'info' },
    };

    window.showToast = function (message, variant) {
      variant = variant || 'info';
      var cfg = TOAST_VARIANTS[variant] || TOAST_VARIANTS.info;
      if (!toastContainer) return;

      var el = document.createElement('div');
      el.className = 'pointer-events-auto transform transition-all duration-500 p-4 rounded-r-xl rounded-l-sm shadow-2xl border-l-4 backdrop-blur-md flex justify-between items-start bg-canvas-800/90 '
        + cfg.border + ' ' + cfg.text + ' ' + cfg.shadow;
      el.setAttribute('role', 'status');

      // Build DOM without innerHTML so untrusted message strings can't inject markup.
      var leftWrap = document.createElement('div');
      leftWrap.className = 'flex items-center gap-4';
      var icon = document.createElement('span');
      icon.className = 'material-symbols-outlined text-3xl opacity-80';
      icon.textContent = cfg.icon;
      var p = document.createElement('p');
      p.className = 'font-light text-sm leading-snug';
      p.textContent = message;
      leftWrap.appendChild(icon);
      leftWrap.appendChild(p);

      var closeBtn = document.createElement('button');
      closeBtn.type = 'button';
      closeBtn.className = 'ml-4 opacity-50 hover:opacity-100 transition-opacity p-1';
      closeBtn.setAttribute('aria-label', 'Cerrar');
      var closeIcon = document.createElement('span');
      closeIcon.className = 'material-symbols-outlined text-xl';
      closeIcon.textContent = 'close';
      closeBtn.appendChild(closeIcon);

      el.appendChild(leftWrap);
      el.appendChild(closeBtn);

      var dismiss = function () {
        el.style.opacity = '0';
        setTimeout(function () { el.remove(); }, 300);
      };
      closeBtn.addEventListener('click', dismiss);
      toastContainer.appendChild(el);
      setTimeout(dismiss, 5000);
    };

    /* ===================================================
     * data-confirm interceptor (forms + links + buttons)
     * =================================================== */
    document.addEventListener('submit', function (e) {
      var form = e.target.closest('form[data-confirm]');
      if (!form || form.dataset.confirmed === '1') return;
      e.preventDefault();
      if (typeof window.confirmDialog !== 'function') {
        // Fallback in case the modal failed to mount (e.g. base template missing).
        if (window.confirm(form.dataset.confirm || '¿Continuar?')) {
          form.dataset.confirmed = '1';
          form.submit();
        }
        return;
      }
      window.confirmDialog({
        title:       form.dataset.confirmTitle,
        message:     form.dataset.confirm,
        confirmText: form.dataset.confirmText,
        variant:     form.dataset.confirmVariant,
      }).then(function (ok) {
        if (ok) {
          form.dataset.confirmed = '1';
          form.submit();
        }
      });
    }, true);

    document.addEventListener('click', function (e) {
      var link = e.target.closest('a[data-confirm], button[data-confirm]:not([type="submit"])');
      if (!link || link.dataset.confirmed === '1') return;
      e.preventDefault();
      if (typeof window.confirmDialog !== 'function') {
        if (window.confirm(link.dataset.confirm || '¿Continuar?')) {
          if (link.tagName === 'A') window.location.href = link.href;
          else { link.dataset.confirmed = '1'; link.click(); }
        }
        return;
      }
      window.confirmDialog({
        title:       link.dataset.confirmTitle,
        message:     link.dataset.confirm,
        confirmText: link.dataset.confirmText,
        variant:     link.dataset.confirmVariant,
      }).then(function (ok) {
        if (!ok) return;
        if (link.tagName === 'A') {
          window.location.href = link.href;
        } else {
          link.dataset.confirmed = '1';
          link.click();
        }
      });
    }, true);
  });
})();

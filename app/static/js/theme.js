/* =================================================================
 * Suministros CNCV — Theme bootstrap
 *
 * Este archivo se carga en <head> antes del primer paint para evitar
 * "flash of wrong theme" cuando el usuario tenía un tema guardado en
 * localStorage diferente al default.
 *
 * Expone:
 *   window.setTheme(name)  — cambia el tema y lo persiste
 *
 * Los botones del navbar que cambian de tema usan
 *   <button data-set-theme="elegant">…</button>
 * y un listener delegado registrado en ui.js (después de DOMContentLoaded).
 * Aquí sólo definimos setTheme y aplicamos el tema guardado.
 * ================================================================= */
(function () {
  'use strict';

  function setTheme(themeName) {
    try {
      localStorage.setItem('theme', themeName);
    } catch (_) {
      /* localStorage puede estar bloqueado; ignoramos. */
    }
    document.documentElement.setAttribute('data-theme', themeName);
  }

  // Apply saved theme immediately (before first paint).
  var saved = 'elegant';
  try {
    saved = localStorage.getItem('theme') || 'elegant';
  } catch (_) { /* noop */ }
  document.documentElement.setAttribute('data-theme', saved);

  window.setTheme = setTheme;
})();

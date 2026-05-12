/* =================================================================
 * Suministros CNCV — Theme bootstrap
 *
 * Se carga en <head> antes del primer paint para evitar flash of wrong
 * theme cuando el usuario tenía un tema guardado en localStorage.
 *
 * Temas válidos (rediseño 2026-05-12): slate, graphite, obsidian, sapphire.
 * Los temas antiguos (elegant/cyberpunk/corporate/emerald) se remapean al
 * equivalente más cercano para no romper localStorage de usuarios existentes.
 *
 * Expone:
 *   window.setTheme(name)  — cambia el tema y lo persiste
 *
 * El cambio de tema vive sólo en la pantalla de perfil (sección "Apariencia"),
 * usando <button data-set-theme="…"> + delegated listener en ui.js.
 * ================================================================= */
(function () {
  'use strict';

  var VALID = ['slate', 'graphite', 'obsidian', 'sapphire'];
  var LEGACY_MAP = {
    elegant:   'slate',     // antes default morado → ahora default azul slate
    corporate: 'slate',     // ya era slate-like
    cyberpunk: 'sapphire',  // saturado oscuro → tech serio
    emerald:   'obsidian',  // único con acento cálido → premium dorado
  };

  function normalize(name) {
    if (!name) return 'slate';
    if (VALID.indexOf(name) !== -1) return name;
    if (LEGACY_MAP[name]) return LEGACY_MAP[name];
    return 'slate';
  }

  function setTheme(themeName) {
    var resolved = normalize(themeName);
    try {
      localStorage.setItem('theme', resolved);
    } catch (_) { /* localStorage bloqueado, ignoramos */ }
    document.documentElement.setAttribute('data-theme', resolved);
  }

  var saved = 'slate';
  try {
    saved = normalize(localStorage.getItem('theme'));
  } catch (_) { /* noop */ }
  document.documentElement.setAttribute('data-theme', saved);

  window.setTheme = setTheme;
})();

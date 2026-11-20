/* Utilidades de interfaz: DOM seguro (nada de innerHTML con datos), formato, avisos, modales, animaciones. */
'use strict';
const SVGNS = 'http://www.w3.org/2000/svg';

function h(tag, attrs, ...hijos) {
  const svg = ['svg', 'g', 'path', 'circle', 'rect', 'line', 'text', 'polygon', 'polyline', 'defs', 'linearGradient', 'stop', 'title'].includes(tag) && (tag !== 'title');
  const el = svg ? document.createElementNS(SVGNS, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.setAttribute('class', v);
    else if (k === 'style' && typeof v === 'object') { for (const [p, x] of Object.entries(v)) { if (p.startsWith('--')) el.style.setProperty(p, x); else el.style[p] = x; } }
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'value') el.value = v;
    else if (k === 'checked' || k === 'disabled' || k === 'selected') { el[k] = !!v; }
    else el.setAttribute(k, v === true ? '' : v);
  }
  anexar(el, hijos);
  return el;
}
function anexar(el, hijos) {
  for (const c of hijos.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
function vaciar(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
function icono(d, extra) { return h('svg', Object.assign({ viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.9, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, extra || {}), h('path', { d })); }

/* ---- formato ---- */
const fm = (x) => '$' + Number(x || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fm0 = (x) => '$' + Math.round(Number(x || 0)).toLocaleString('en-US');
const pct0 = (v, b) => (b && b > 0 ? Math.round(v / b * 100) + '%' : '—');
const pct1 = (v, b) => (b && b > 0 ? (v / b * 100).toFixed(1) + '%' : '—');
const lerp = (a, b, t) => a + (b - a) * t;
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const animar = (ms, f, fin) => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { f(1); if (fin) fin(); return () => {}; }
  let cancelado = false; const t0 = performance.now();
  const paso = (t) => { if (cancelado) return; const p = Math.min(1, (t - t0) / ms); f(easeOut(p)); if (p < 1) requestAnimationFrame(paso); else if (fin) fin(); };
  requestAnimationFrame(paso);
  return () => { cancelado = true; };
};
/* contador que sube suavemente hasta el valor (y recuerda el anterior para no empezar siempre de cero) */
function contar(el, hasta, fmt = fm0, ms = 460) {
  const desde = el._n || 0;
  if (el._stop) el._stop();
  el._stop = animar(ms, (p) => { el.textContent = fmt(lerp(desde, hasta, p)); }, () => { el.textContent = fmt(hasta); });
  el._n = hasta;
}

/* ---- tema y colores ---- */
const Tema = { paletas: null, nombre: 'claro', P: null };
function aplicarTema(nombre) {
  Tema.nombre = nombre === 'oscuro' ? 'oscuro' : 'claro';
  Tema.P = Tema.paletas[Tema.nombre];
  const r = document.documentElement.style;
  for (const [k, v] of Object.entries(Tema.P)) r.setProperty('--' + k.toLowerCase().replace(/_/g, '-'), v);
  r.setProperty('--sombra', Tema.nombre === 'oscuro' ? '0 1px 2px rgba(0,0,0,.35), 0 6px 18px rgba(0,0,0,.25)' : '0 1px 2px rgba(16,40,64,.06), 0 6px 18px rgba(16,40,64,.06)');
  document.documentElement.dataset.tema = Tema.nombre;
  const b = $('#btnTema'); if (b) b.setAttribute('aria-checked', Tema.nombre === 'oscuro');
}
function colorVend(ci) {
  if (ci === null || ci === undefined) return { t: Tema.P.GT, s: Tema.P.GS };
  const i = ((ci % 8) + 8) % 8; return { t: Tema.P['PT' + i], s: Tema.P['PS' + i] };
}
const V = (nombre) => `var(--${nombre})`;

/* ---- avisos ---- */
function toast(msg, opc = {}) {
  const t = h('div', { class: 'toast' + (opc.err ? ' err' : ''), role: 'status' }, msg,
    opc.accion ? h('button', { onclick: () => { opc.accion.fn(); quitar(); } }, opc.accion.texto) : null);
  const quitar = () => { t.classList.add('sale'); setTimeout(() => t.remove(), 220); };
  $('#toasts').appendChild(t);
  setTimeout(quitar, opc.ms || (opc.err ? 6000 : 3600));
}
/* ---- modales ---- */
function modal({ titulo, cuerpo, botones, ancho = 460, cerrarConFondo = true, alMostrar }) {
  return new Promise((res) => {
    const previo = document.activeElement;
    let cerrado = false;
    const cerrar = (v) => {
      if (cerrado) return; cerrado = true;
      document.removeEventListener('keydown', tecla, true);
      fondo.classList.add('sale'); setTimeout(() => { fondo.remove(); if (previo && previo.focus) previo.focus(); }, 150); res(v);
    };
    const tecla = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); cerrar(undefined); }
      if (e.key === 'Enter' && !e.shiftKey && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'SELECT') {
        const p = botones.find((b) => !(b instanceof Node) && (b.tipo === 'primario' || b.tipo === 'peligro')); if (p) { e.preventDefault(); p.fn ? p.fn(cerrar) : cerrar(p.valor); }
      }
    };
    const btns = (botones || []).map((b) => b instanceof Node ? b : h('button', { class: 'btn ' + (b.tipo || ''), onclick: () => (b.fn ? b.fn(cerrar) : cerrar(b.valor)), 'data-valor': String(b.valor) }, b.texto));
    const modalEl = h('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true', style: { '--ancho': ancho + 'px' } },
      titulo ? h('div', { class: 'modal-cab' }, h('h3', null, titulo)) : null,
      h('div', { class: 'modal-cuerpo' }, cuerpo),
      btns.length ? h('div', { class: 'modal-pie' }, btns) : null);
    const fondo = h('div', { class: 'fondo', onmousedown: (e) => { if (cerrarConFondo && e.target === fondo) cerrar(undefined); } }, modalEl);
    $('#modales').appendChild(fondo);
    document.addEventListener('keydown', tecla, true);
    const foco = modalEl.querySelector('input,select,textarea') || btns.find((b) => b.classList.contains('primario') || b.classList.contains('peligro')) || btns[0];
    setTimeout(() => foco && foco.focus(), 30);
    if (alMostrar) alMostrar(modalEl, cerrar);
  });
}
const parrafos = (txt) => String(txt).split('\n\n').map((p) => h('p', null, p));
const avisar = (txt, titulo = 'Proyecciones') => modal({ titulo, cuerpo: parrafos(txt), botones: [{ texto: 'Entendido', tipo: 'primario', valor: true }] });
const confirmar = (txt, o = {}) => modal({ titulo: o.titulo || 'Confirmar', cuerpo: parrafos(txt), botones: [
  { texto: o.no || 'Cancelar', valor: false }, { texto: o.si || 'Aceptar', tipo: o.peligro ? 'peligro' : 'primario', valor: true }] }).then((v) => v === true);
const pedirTexto = (titulo, etiqueta, valor = '') => {
  const inp = h('input', { type: 'text', value: valor, 'aria-label': etiqueta, autocomplete: 'off' });
  return modal({ titulo, cuerpo: [h('label', { class: 'et' }, etiqueta), inp], botones: [
    { texto: 'Cancelar', valor: null }, { texto: 'Aceptar', tipo: 'primario', fn: (c) => c(inp.value) }] });
};

/* ---- tooltip ---- */
let _tt;
function tip(el, texto) {
  el.addEventListener('mousemove', (e) => {
    if (!_tt) { _tt = h('div', { class: 'tooltip' }); document.body.appendChild(_tt); }
    _tt.textContent = typeof texto === 'function' ? texto() : texto; _tt.classList.add('v');
    _tt.style.left = Math.min(e.clientX + 14, innerWidth - 230) + 'px'; _tt.style.top = (e.clientY + 16) + 'px';
  });
  el.addEventListener('mouseleave', () => _tt && _tt.classList.remove('v'));
}

/* ---- controles ---- */
function selectEl(opciones, valor, onchange, attrs = {}) {
  const s = h('select', attrs, opciones.map((o) => { const v = typeof o === 'object' ? o.id : o; const t = typeof o === 'object' ? o.label : o;
    return h('option', { value: v, selected: v === valor }, t); }));
  s.value = valor; if (onchange) s.addEventListener('change', () => onchange(s.value)); return s;
}
function segmentado(opciones, valor, onchange) {
  const cont = h('div', { class: 'seg', role: 'tablist' });
  const pastilla = h('i', { class: 'pastilla' });
  cont.appendChild(pastilla);
  const botones = opciones.map((o) => { const id = typeof o === 'object' ? o.id : o, tx = typeof o === 'object' ? o.label : o;
    const b = h('button', { role: 'tab', class: id === valor ? 'on' : '', onclick: () => { valor = id; botones.forEach((x) => x.classList.toggle('on', x === b)); mover(); onchange(id); } }, tx);
    b._id = id; cont.appendChild(b); return b; });
  const mover = () => { const b = botones.find((x) => x.classList.contains('on')); if (b && b.offsetWidth) { pastilla.style.left = b.offsetLeft + 'px'; pastilla.style.width = b.offsetWidth + 'px'; } };
  cont._mover = mover; requestAnimationFrame(() => requestAnimationFrame(mover)); cont.fijar = (v) => { valor = v; botones.forEach((x) => x.classList.toggle('on', x._id === v)); mover(); };
  return cont;
}
function boton(texto, onclick, tipo = '', extra = {}) { return h('button', Object.assign({ class: 'btn ' + tipo, onclick }, extra), texto); }
/* boton que muestra un girito mientras trabaja la llamada */
function enCurso(btn, promesaFn) {
  return async (...a) => {
    if (btn.disabled) return; btn.disabled = true; const t = btn.textContent; vaciar(btn).appendChild(h('span', { class: 'giro' })); btn.appendChild(document.createTextNode(' ' + t));
    try { return await promesaFn(...a); } finally { btn.disabled = false; btn.textContent = t; }
  };
}
/* skeletons */
const sk = (cl, st) => h('div', { class: 'sk ' + cl, style: st });
function skCab() { return h('div', { class: 'cab' }, h('div', null, sk('titulo'), sk('subt'))); }
function skKpis(n = 5) { return h('div', { class: 'kpis' }, Array.from({ length: n }, () => h('div', { class: 'card kpi' }, sk('l1'), sk('l2'), sk('l3')))); }
function skTarjetas(n = 3, alto = 300) { return h('div', { class: 'rejilla', style: { gridTemplateColumns: 'repeat(auto-fit,minmax(340px,1fr))' } },
  Array.from({ length: n }, () => h('div', { class: 'sk-card' }, h('div', { class: 'sk-fila' }, sk('l1', { width: '30%' })), h('div', { class: 'sk-fila', style: { marginTop: '16px' } }, sk('redondo', { width: '92px', height: '92px' }),
    h('div', { style: { flex: 1 } }, sk('l1', { width: '60%' }), sk('l2'), sk('l3'))), sk('bloque', { height: (alto - 190) + 'px', marginTop: '14px' })))); }
function skTabla(filas = 8) { return h('div', { class: 'card' }, Array.from({ length: filas }, () => h('div', { class: 'sk-fila', style: { margin: '11px 0' } }, sk('l1', { width: '8%' }), sk('l1', { width: '14%' }), sk('l1', { width: '34%' }), sk('l1', { width: '16%' }), sk('l1', { width: '10%' })))); }
function skPagina(tipo) {
  const t = { panel: [skCab(), skKpis(), h('div', { class: 'dos-col' }, h('div', { class: 'sk-card' }, sk('bloque', { height: '130px' })), h('div', { class: 'sk-card' }, sk('bloque', { height: '130px' }))), h('div', { style: { height: '14px' } }), skTarjetas(3)],
    tabla: [skCab(), skTabla(10)], tarjetas: [skCab(), skTarjetas(4, 280)], form: [skCab(), h('div', { class: 'ingreso' }, h('div', { class: 'sk-card' }, sk('bloque', { height: '320px' })), h('div', { class: 'sk-card' }, sk('bloque', { height: '320px' })))] };
  return h('div', { class: 'pag' }, t[tipo] || t.tabla);
}

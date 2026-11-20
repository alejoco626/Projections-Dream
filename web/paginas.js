/* Paginas de la app. Cada pagina es un objeto { id, titulo, montar(), actualizar(), skeleton } que app.js maneja:
   montar() dibuja el marco una vez; actualizar() vuelve a pedir los datos al programa y actualiza solo lo que cambio. */
'use strict';
const S = { estado: null };       // estado general (lo llena app.js)

/* ------------------------------------------------------------- piezas comunes */
function cab(titulo, sub, acciones) {
  const s = h('div', { class: 'sub' }, sub || '');
  return { el: h('div', { class: 'cab' }, h('div', null, h('h1', null, titulo), s), h('div', { class: 'acciones' }, acciones || [])), sub: s };
}
async function refrescarEstado() { S.estado = await API.estado(); window.dispatchEvent(new Event('estado')); }
const refrescarVista = () => window.app.actualizarPagina();
async function cambio() { await refrescarEstado(); await window.app.actualizarPagina(); }
function errorDe(r, campo) { if (r && r.error) { toast(r.error.split('\n')[0], { err: true }); if (campo && r.campo) { const e = campo[r.campo]; if (e) { e.classList.add('malo'); e.focus(); setTimeout(() => e.classList.remove('malo'), 1400); } } return true; } return false; }
const seguro = async (p) => { const r = await p; if (r && r.error) { await avisar(r.error); return null; } return r; };

/* Mes | Semana + semana (se desactiva si hay varios meses) */
function filtroTiempo(onchange) {
  const v = S.estado.vista; const cont = h('div', { class: 'hl' });
  if (v.multi) { cont.appendChild(h('span', { class: 'muted' }, 'Meses combinados')); return cont; }
  const sem = selectEl(v.semanas.map((t, i) => ({ id: String(i + 1), label: t })), String(v.semana), async (x) => { await API.fijar_vista(null, null, 'Semana', +x); await refrescarEstado(); onchange(); }, { 'aria-label': 'Semana', style: { width: '170px', display: v.modo === 'Semana' ? '' : 'none' } });
  const seg = segmentado(['Mes', 'Semana'], v.modo, async (m) => { sem.style.display = m === 'Semana' ? '' : 'none'; await API.fijar_vista(null, null, m); await refrescarEstado(); onchange(); });
  cont.append(seg, sem); return cont;
}

/* Tabla con filas seleccionables (clic, Ctrl, Mayus), orden por columna y "mostrar mas" */
function Tabla({ cols, id = (f) => f.id, multi = true, alto = 460, vacio = 'Sin resultados', onDbl, onSel, ordenar, clase, filaClase, limite = 400 }) {
  const thead = h('tr'), tbody = h('tbody'), tabla = h('table', { class: 't' }, h('thead', null, thead), tbody);
  const el = h('div', { class: 'tabla-scroll', style: { '--alto': alto + 'px' } }, tabla);
  let filas = [], sel = new Set(), ultima = null, mostrados = limite, orden = { col: null, inv: false };
  const T = { el, get sel() { return [...sel]; }, get filas() { return filas; } };
  function cabeceras() {
    vaciar(thead);
    cols.forEach((c) => { const fl = orden.col === c.id ? h('span', { class: 'fl' }, orden.inv ? '▼' : '▲') : null;
      thead.appendChild(h('th', { class: (c.cls || '') + (c.ord ? ' ord' : ''), style: c.w ? { width: c.w } : null, onclick: c.ord && ordenar ? () => ordenar(c.id) : null }, c.t, fl)); });
  }
  function pintarSel() { [...tbody.children].forEach((tr) => tr.classList.toggle('sel', sel.has(tr.dataset.id))); onSel && onSel(T.sel); }
  function fila(f) {
    const tr = h('tr', { dataset: { id: String(id(f)) }, class: filaClase ? filaClase(f) : '' }, cols.map((c) => { const v = c.render ? c.render(f) : f[c.id]; return h('td', { class: c.cls || '' }, v); }));
    tr.addEventListener('mousedown', (e) => { if (e.button !== 0 || e.target.closest('a.enlace:not(.sin)') && !(e.ctrlKey || e.shiftKey || e.metaKey)) return; clicFila(e, f); });
    if (onDbl) tr.addEventListener('dblclick', (e) => { if (!e.target.closest('a.enlace:not(.sin)')) onDbl(f); });
    return tr;
  }
  function clicFila(e, f) {
    const k = String(id(f));
    if (!multi) sel = new Set([k]);
    else if (e.shiftKey && ultima) { const ids = filas.map((x) => String(id(x))); let a = ids.indexOf(ultima), b = ids.indexOf(k); if (a > b) [a, b] = [b, a]; sel = new Set(ids.slice(a, b + 1)); e.preventDefault(); }
    else if (e.ctrlKey || e.metaKey) { sel.has(k) ? sel.delete(k) : sel.add(k); ultima = k; }
    else { sel = new Set([k]); ultima = k; }
    pintarSel();
  }
  T.set = (nuevas, o = {}) => {
    filas = nuevas; if (o.orden) orden = o.orden; mostrados = limite; const previa = sel; sel = new Set([...previa].filter((k) => filas.some((f) => String(id(f)) === k))); cabeceras(); dibujar();
  };
  function dibujar() {
    vaciar(tbody);
    if (!filas.length) { tbody.appendChild(h('tr', null, h('td', { colspan: cols.length, class: 'vacio' }, vacio))); onSel && onSel([]); return; }
    const lote = document.createDocumentFragment(); filas.slice(0, mostrados).forEach((f) => lote.appendChild(fila(f))); tbody.appendChild(lote);
    if (filas.length > mostrados) tbody.appendChild(h('tr', null, h('td', { colspan: cols.length, class: 'c' }, h('button', { class: 'btn chico', onclick: () => { mostrados += 600; dibujar(); } }, `Mostrar más (${filas.length - mostrados} restantes)`))));
    pintarSel();
  }
  T.limpiar = () => { sel = new Set(); pintarSel(); };
  T.seleccionar = (ids) => { sel = new Set(ids.map(String)); pintarSel(); };
  cabeceras(); return T;
}
const celdaEnlace = (txt, url, aviso) => {
  if (!txt) return '';
  if (!url) return h('a', { class: 'enlace sin', title: 'Este lead solo tiene el ID (sin enlace)' }, txt);
  return h('a', { class: 'enlace', href: '#', title: 'Abrir en el navegador (Ctrl o Mayús + clic solo selecciona)', onclick: async (e) => { e.preventDefault(); if (e.ctrlKey || e.shiftKey || e.metaKey) return; const r = await API.abrir_url(url); if (r.error) toast(r.error, { err: true }); } }, txt);
};
const etqTipo = (t) => h('span', { class: 'etq ' + t }, { activa: 'Activa', perdida: 'Perdida', exitosa: 'Exitosa' }[t]);
const vendPunto = (f) => h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '7px' } }, h('i', { class: 'punto', style: { background: colorVend(f.ci).s } }), f.vendedor);
function pie(txt) { return h('div', { class: 'pie-tabla' }, txt); }

/* ============================================================= PANEL */
const PanelPag = {
  id: 'panel', titulo: 'Panel principal', skeleton: 'panel',
  montar() {
    this.kpis = Array.from({ length: 5 }, () => ({ t: h('div', { class: 't' }), v: h('div', { class: 'v' }), s: h('div', { class: 's' }) }));
    this.k = this.kpis.map((k, i) => h('div', { class: 'card kpi', style: { '--i': i } }, k.t, k.v, k.s));
    this.ritmo = h('div', { class: 'card', style: { minHeight: '150px' } }); this.nec = h('div', { class: 'card' }); this.cards = h('div', { class: 'vend-cards' });
    const c = cab('Panel principal', '', []); this.c = c; this.acc = c.el.querySelector('.acciones');
    return h('div', { class: 'pag' }, c.el, h('div', { class: 'kpis' }, this.k), h('div', { class: 'dos-col' }, this.ritmo, this.nec), this.cards);
  },
  async actualizar() {
    const r = await API.panel(); if (r.error) return avisar(r.error);
    const m = r.modelo, e = m.equipo, modo = S.estado.vista.modo; this.c.sub.textContent = m.titulo;
    vaciar(this.acc).append(filtroTiempo(refrescarVista), boton('Guardar reporte', () => this.guardarReporte(), 'primario'), boton('Descargar PDF', () => this.pdf()));
    const top = r.top, arr = e.arrastre || 0, multi = !!m.multi;
    let subMeta = multi ? 'de los meses elegidos' : modo === 'Mes' ? 'mensual' : 'semanal'; if (Math.abs(arr) >= 0.5) subMeta += ` · ${arr > 0 ? '+' : '−'}${fm0(Math.abs(arr))} de semanas anteriores`;
    const set = (i, t, v, s, color, kc, sc) => { const k = this.kpis[i]; k.t.textContent = t; k.s.textContent = s || ''; k.s.style.color = sc || ''; k.v.style.color = color || ''; k.v.parentElement.style.setProperty('--kc', kc || 'var(--azul-claro)');
      if (typeof v === 'number') contar(k.v, v); else { if (k.v._stop) k.v._stop(); k.v._n = 0; k.v.textContent = v; } };
    set(0, 'Meta del equipo', e.meta > 0 ? e.meta : 'Sin meta', subMeta, null, 'var(--azul-claro)');
    set(1, 'Recibido', e.neto, e.meta > 0 ? pct0(e.neto, e.meta) + ' de la meta' : '', 'var(--azul)', 'var(--azul)');
    set(2, 'Proyectado', e.proy, `${e.n_proy} activas`, null, 'var(--azul-claro)');
    if (e.meta <= 0) set(3, 'Falta', '—', '', null, 'var(--track)'); else if (e.falta_neto > 0) set(3, 'Falta', e.falta_neto, 'para la meta', 'var(--corinto)', 'var(--corinto)'); else set(3, 'Superó por', -e.falta_neto, 'la meta', 'var(--azul-med)', 'var(--azul-med)');
    set(4, 'Campaña líder', top ? top.campana : '—', top ? `${fm0(top.neto)} · ${top.n_neto} ventas` : 'sin ventas', top ? 'var(--corinto)' : 'var(--muted)', 'var(--corinto-med)');
    this.kpis[4].v.title = top ? top.campana : '';
    // ritmo del equipo
    vaciar(this.ritmo).append(h('h2', null, 'Ritmo del equipo'), e.meta > 0 && m.esp != null ? bloqueRitmo(m.esp, e.neto, e.esp_monto, e.meta, true) : h('div', { class: 'muted', style: { marginTop: '8px' } }, 'Define la meta para ver el ritmo'));
    // proyeccion necesaria
    const filas = m.filas.concat([Object.assign({}, e, { nombre: 'Equipo', _total: true })]);
    vaciar(this.nec).append(h('h2', null, 'Proyección necesaria para la meta'), h('p', { class: 'ayuda' }, 'Con la tasa de cierre actual: vendido ÷ proyectado.'),
      h('table', { class: 'tabla-nec' }, h('thead', null, h('tr', null, ['Vendedor', 'Tasa de cierre', 'Proyectado', 'Necesaria', '% faltante', 'Falta proyectar'].map((t) => h('th', null, t)))),
        h('tbody', null, filas.map((f) => { const tr = h('tr', { class: f._total ? 'total' : '' }, h('td', null, f.nombre));
          if (f.meta <= 0) { tr.append(h('td', { colspan: 5, class: 'muted' }, 'Sin meta')); return tr; }
          tr.append(h('td', null, f.tasa != null ? pct0(f.tasa, 1) : '—'), h('td', null, fm0(f.ingresado)));
          if (f.neto >= f.meta) tr.append(h('td', { colspan: 3, class: 'azulmed-t', style: { fontWeight: 700 } }, 'Meta lograda'));
          else if (f.nec_total == null) tr.append(h('td', { colspan: 3, class: 'muted' }, 'Sin ventas aún'));
          else tr.append(h('td', null, fm0(f.nec_total)), h('td', null, pct0(f.pct_falta, 1)), h('td', { class: 'rojo-t', style: { fontWeight: 700 } }, fm0(f.nec_falta)));
          return tr; }))));
    // tarjetas
    const n = m.filas.length, cols = n <= 3 ? Math.max(n, 1) : n === 4 ? 2 : 3;
    this.cards.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
    vaciar(this.cards);
    if (!n) this.cards.appendChild(h('div', { class: 'card vacio', style: { gridColumn: '1/-1' } }, 'Aún no hay vendedores. Agrégalos en «Vendedores y metas».'));
    m.filas.forEach((f, i) => this.cards.appendChild(tarjetaVendedor(f, r.semanas_vend[f.id], { tipo: r.tipo_grafica, esp: m.esp, destacada: m.semana, etq: r.etq_semanas, metaMes: f.meta_mes }, i)));
  },
  async guardarReporte(reemplazar = false) {
    const r = await API.guardar_reporte(reemplazar); if (r.error) return avisar(r.error);
    if (r.pregunta) { if (await confirmar(r.pregunta, { titulo: r.titulo, si: 'Reemplazar' })) return this.guardarReporte(true); return; }
    await avisar(`Reporte guardado: ${r.titulo}\n(con la meta mensual y semanal de cada vendedor).\n\nLo encuentras en «Reportes guardados».`, 'Reporte guardado'); await cambio();
  },
  async pdf(rid) { const r = await API.descargar_pdf(rid || null); if (r.error) return avisar(r.error); if (r.cancelado) return;
    if (await confirmar(`PDF creado (${r.laminas} láminas).\n¿Abrirlo ahora?`, { titulo: 'PDF listo', si: 'Abrir', no: 'Cerrar' })) API.abrir_ruta(r.ruta); },
};

/* ============================================================= INGRESAR */
const IngresoPag = {
  id: 'ingreso', titulo: 'Ingresar reporte', skeleton: 'form',
  montar() {
    this.editando = null; this.auto = {}; this.autoId = null;
    const campo = (et, input, extra) => h('div', { class: 'campo' + (extra ? ' ' + extra : '') }, h('label', { class: 'et' }, et), input);
    this.fecha = h('input', { type: 'text', inputmode: 'numeric', placeholder: 'dd/mm/aaaa', 'aria-label': 'Fecha' });
    this.asesor = h('select', { 'aria-label': 'Asesor' });
    this.lead = h('input', { type: 'text', placeholder: 'Pega el enlace de Bitrix24 o el ID', autocomplete: 'off', 'aria-label': 'Enlace o ID del lead' });
    this.campana = h('input', { type: 'text', list: 'lista-campanas', autocomplete: 'off', 'aria-label': 'Campaña' }); this.listaCamp = h('datalist', { id: 'lista-campanas' });
    this.monto = h('input', { type: 'text', inputmode: 'decimal', placeholder: '0.00', autocomplete: 'off', 'aria-label': 'Monto' });
    this.avisoMonto = h('div', { class: 'aviso-campo' }); this.avisoCamp = h('div', { class: 'aviso-campo' }); this.autoMsg = h('div', { class: 'auto' });
    this.tipos = h('div', { class: 'tipos' }, [['activa', 'Activa'], ['perdida', 'Perdida'], ['exitosa', 'Exitosa']].map(([v, t]) => h('label', { class: 'tipo-op' }, h('input', { type: 'radio', name: 'tipo', value: v, checked: v === 'activa' }), h('span', null, t))));
    this.btnGuardar = boton('Agregar', () => this.guardar(), 'primario'); this.btnCancelar = boton('Cancelar edición', () => this.cancelar(), ''); this.btnCancelar.style.display = 'none';
    this.btnLimpiar = boton('Limpiar', () => this.limpiar());
    const btnLeer = boton('Leer de Bitrix24', () => this.leer(true), 'chico'); this.btnLeer = btnLeer;
    this.campos = { fecha: this.fecha, asesor: this.asesor, lead: this.lead, campana: this.campana, monto: this.monto };
    const form = h('div', { class: 'card' }, h('h2', null, 'Nueva proyección'), (this.subForm = h('p', { class: 'ayuda' })),
      h('div', { class: 'form-grid' }, campo('Fecha', this.fecha), campo('Asesor (vendedor)', this.asesor),
        h('div', { class: 'ancho campo' }, h('label', { class: 'et' }, 'Enlace o ID del lead'), h('div', { class: 'hl', style: { flexWrap: 'nowrap' } }, this.lead, btnLeer), this.autoMsg),
        h('div', { class: 'campo' }, h('label', { class: 'et' }, 'Campaña'), this.campana, this.listaCamp, this.avisoCamp),
        h('div', { class: 'campo' }, h('label', { class: 'et' }, 'Monto ($)'), this.monto, this.avisoMonto),
        h('div', { class: 'ancho campo' }, h('label', { class: 'et' }, 'Estado'), this.tipos)),
      h('div', { class: 'botones-form' }, this.btnGuardar, this.btnCancelar, this.btnLimpiar));
    this.tabla = Tabla({ cols: [{ id: 'fecha', t: 'Fecha', cls: 'c' }, { id: 'vendedor', t: 'Vendedor', render: vendPunto }, { id: 'etq_id', t: 'ID ↗', cls: 'c', render: (f) => celdaEnlace(f.etq_id, f.url) },
      { id: 'campana', t: 'Campaña', cls: 'corto', render: (f) => f.campana || '—' }, { id: 'monto', t: 'Monto', cls: 'd', render: (f) => fm(f.monto) }, { id: 'tipo', t: 'Estado', render: (f) => etqTipo(f.tipo) }],
      alto: 330, vacio: 'Aún no hay proyecciones en este periodo', onDbl: (f) => this.editar(f.id), onSel: (s) => { this.btnEd.disabled = s.length !== 1; this.btnEl.disabled = !s.length; } });
    this.btnEd = boton('Editar', () => this.tabla.sel[0] && this.editar(this.tabla.sel[0]), 'chico'); this.btnEl = boton('Eliminar', () => this.eliminar(), 'chico rojo'); this.btnEd.disabled = this.btnEl.disabled = true;
    this.total = h('div', { class: 'pie-tabla' });
    const lista = h('div', { class: 'card' }, h('div', { class: 'hl', style: { justifyContent: 'space-between', marginBottom: '8px' } }, h('div', null, h('h2', null, 'Últimas proyecciones'), h('div', { class: 'ayuda', style: { margin: 0 } }, 'Las 10 más recientes del periodo')), h('div', { class: 'hl' }, this.btnEd, this.btnEl)), this.tabla.el, this.total);
    // eventos
    this.lead.addEventListener('input', () => this.programarLectura()); this.lead.addEventListener('paste', () => setTimeout(() => this.programarLectura(), 0));
    [this.fecha, this.asesor, this.lead, this.campana, this.monto].forEach((e) => e.addEventListener('input', () => this.borrador()));
    this.tipos.addEventListener('change', () => this.borrador());
    this.lead.addEventListener('keydown', (e) => e.key === 'Enter' && this.guardar()); this.monto.addEventListener('keydown', (e) => e.key === 'Enter' && this.guardar()); this.campana.addEventListener('keydown', (e) => e.key === 'Enter' && this.guardar());
    const c = cab('Ingresar reporte', '', []); this.c = c; return h('div', { class: 'pag' }, c.el, h('div', { class: 'ingreso' }, form, lista));
  },
  tipoSel() { return $('input[name=tipo]:checked', this.tipos).value; },
  ponerTipo(t) { const r = $(`input[name=tipo][value=${t}]`, this.tipos); if (r) r.checked = true; },
  async actualizar() {
    const r = await API.ingreso(); if (r.error) return avisar(r.error);
    this.c.sub.textContent = 'Se guarda en ' + r.titulo_periodo; this.subForm.textContent = 'Se guarda en ' + r.titulo_periodo;
    this.bitrix = r.bitrix;
    const cur = this.asesor.value; vaciar(this.asesor).append(...r.asesores.map((n) => h('option', { value: n }, n))); this.asesor.value = r.asesores.includes(cur) ? cur : (r.asesores[0] || '');
    vaciar(this.listaCamp).append(...r.campanas.map((c) => h('option', { value: c })));
    if (!this.fecha.value) this.fecha.value = r.hoy;
    if (!this._borradorCargado) { this._borradorCargado = true; const b = r.borrador; if (b) { this.fecha.value = b.fecha || r.hoy; if (r.asesores.includes(b.asesor)) this.asesor.value = b.asesor; this.campana.value = b.campana || ''; this.monto.value = b.monto || ''; this.lead.value = b.lead || ''; const t = { Activa: 'activa', Perdida: 'perdida', Exitosa: 'exitosa' }[b.tipo]; if (t) this.ponerTipo(t); } }
    this.tabla.set(r.ultimas);
    const etiquetas = { activa: 'Activa', perdida: 'Perdida', exitosa: 'Exitosa' };
    this.total.textContent = `Total del periodo (${r.n} proyecciones): ${fm(r.total)}   ·   ` + ['activa', 'perdida', 'exitosa'].map((t) => `${etiquetas[t]}: ${fm(r.por[t])}`).join('   ·   ');
    this.btnLeer.style.display = r.bitrix ? '' : 'none';
  },
  borrador() { clearTimeout(this._bj); if (this.editando) return; this._bj = setTimeout(() => API.guardar_borrador({ fecha: this.fecha.value, asesor: this.asesor.value, campana: this.campana.value, monto: this.monto.value, tipo: { activa: 'Activa', perdida: 'Perdida', exitosa: 'Exitosa' }[this.tipoSel()], lead: this.lead.value }), 600); },
  programarLectura() {
    clearTimeout(this._lj); const did = (this.lead.value.match(/\/deal\/details\/(\d+)/i) || [null, /^\s*\d+\s*$/.test(this.lead.value) ? this.lead.value.trim() : ''])[1];
    if (did !== this.autoId) this.avisos(false);
    if (!did || this.editando || !this.bitrix) return; this._lj = setTimeout(() => this.leer(false), 500);
  },
  avisos(vacio, campana = '') { this.avisoMonto.textContent = vacio ? 'El vendedor no colocó el monto en la negociación' : ''; this.avisoCamp.textContent = campana || ''; },
  async leer(manual) {
    const lead = this.lead.value; if (!lead.trim()) { if (manual) { this.autoMsg.className = 'auto'; this.autoMsg.textContent = 'Pega primero el enlace o el ID del lead.'; } return; }
    if (!this.bitrix) { if (manual) avisar('Configura el webhook en ⚙ Configuración → Conexión con Bitrix24.'); return; }
    this.autoMsg.className = 'auto cargando'; vaciar(this.autoMsg).append(h('span', { class: 'giro' }), `Leyendo el lead en Bitrix24…`);
    const r = await API.leer_bitrix(lead);
    if (this.lead.value !== lead) return;        // cambio de lead mientras leia
    if (r.error) { this.autoMsg.className = 'auto err'; this.autoMsg.textContent = r.error.replace(/\n/g, ' '); return; }
    const nuevos = { asesor: r.asesor, campana: r.campana, monto: r.monto }, el = { asesor: this.asesor, campana: this.campana, monto: this.monto };
    for (const k of Object.keys(nuevos)) { const actual = (el[k].value || '').trim();
      if (!actual || actual === this.auto[k] || (k === 'asesor' && r.vendedor_conocido)) { if (k === 'asesor' && !nuevos[k]) continue; el[k].value = nuevos[k]; } }
    this.auto = nuevos; this.autoId = r.id; this.avisos(r.monto_vacio, r.aviso_campana);
    let msg = 'Leído de Bitrix24 · puedes editar los datos'; if (r.vendedor_bitrix && !r.vendedor_conocido) msg += ` · «${r.vendedor_bitrix}» no está en tu lista de vendedores`;
    if (r.duplicado) msg = `Este lead ya está registrado en ${r.duplicado}.`;
    this.autoMsg.className = 'auto' + (r.duplicado ? ' err' : ''); this.autoMsg.textContent = msg; this.borrador();
  },
  formulario(extra) { return Object.assign({ fecha: this.fecha.value, asesor: this.asesor.value, lead: this.lead.value, campana: this.campana.value, monto: this.monto.value, tipo: { activa: 'Activa', perdida: 'Perdida', exitosa: 'Exitosa' }[this.tipoSel()], editando: this.editando }, extra || {}); },
  async guardar(confirmarNombre = false) {
    const r = await API.guardar_proyeccion(this.formulario({ confirmar_nombre: confirmarNombre }));
    if (r.pregunta) { if (await confirmar(r.pregunta, { titulo: r.titulo, si: 'Guardar' })) return this.guardar(true); return; }
    if (r.error) { if (r.titulo) await avisar(r.error, r.titulo); else toast(r.error, { err: true }); const e = this.campos[r.campo]; if (e) { e.classList.add('malo'); e.focus(); setTimeout(() => e.classList.remove('malo'), 1400); } return; }
    const fueEdicion = !!this.editando; this.cancelar(true); this.lead.value = ''; this.monto.value = ''; this.auto = {}; this.autoId = null; this.avisos(false); this.autoMsg.textContent = '';
    toast(fueEdicion ? 'Cambios guardados' : 'Proyección agregada'); await cambio(); this.lead.focus();
  },
  async editar(id) {
    const r = await API.editar_registro(id); if (r.error) return avisar(r.error);
    await refrescarEstado(); window.dispatchEvent(new Event('vista')); await this.actualizar();
    this.editando = r.reg.id; const g = r.reg; this.fecha.value = g.fecha; this.asesor.value = g.asesor; this.campana.value = g.campana; this.monto.value = g.monto; this.lead.value = g.lead;
    this.ponerTipo({ Activa: 'activa', Perdida: 'perdida', Exitosa: 'exitosa' }[g.tipo]); this.btnGuardar.textContent = 'Guardar cambios'; this.btnCancelar.style.display = ''; this.autoMsg.textContent = 'Editando una proyección existente'; this.autoMsg.className = 'auto';
    if (window.app.actual !== 'ingreso') window.app.ir('ingreso'); this.lead.focus();
  },
  cancelar(silencio) { this.editando = null; this.btnGuardar.textContent = 'Agregar'; this.btnCancelar.style.display = 'none'; if (!silencio) { this.autoMsg.textContent = ''; } },
  limpiar() { this.cancelar(); this.lead.value = ''; this.monto.value = ''; this.auto = {}; this.autoId = null; this.avisos(false); this.autoMsg.textContent = ''; this.borrador(); this.lead.focus(); },
  async eliminar() {
    const ids = this.tabla.sel; if (!ids.length) return;
    if (!(await confirmar(`¿Eliminar ${ids.length} proyección(es) seleccionada(s)?\n(Podrás deshacerlo.)`, { titulo: 'Eliminar', si: 'Eliminar', peligro: true }))) return;
    if (ids.includes(this.editando)) this.cancelar(); await eliminarConAviso(ids);
  },
};
async function eliminarConAviso(ids) {
  const r = await API.eliminar(ids); if (r.error) return avisar(r.error);
  await cambio(); toast(`${r.n} proyección(es) eliminada(s)`, { accion: { texto: 'Deshacer', fn: deshacer } });
}
async function deshacer() {
  const r = await API.deshacer(); if (r.error) return avisar(r.error);
  await cambio(); toast(`Se restauró ${r.vendedor ? 'al vendedor y sus ' : ''}${r.n} proyección(es).`);
}

/* ============================================================= HISTORIAL */
const HistorialPag = {
  id: 'historial', titulo: 'Historial', skeleton: 'tabla',
  montar() {
    this.f = { texto: '', vendedor: '(Todos)', campana: '(Todas)', tipo: '(Todos)' }; this.ord = { col: 'n', inv: false };
    this.busca = h('input', { type: 'search', placeholder: 'Buscar por referencia, ID, campaña, asesor, monto…', 'aria-label': 'Buscar' }); this.busca.addEventListener('input', () => { clearTimeout(this._b); this._b = setTimeout(() => { this.f.texto = this.busca.value; this.actualizar(); }, 140); });
    this.selV = h('select', { 'aria-label': 'Vendedor' }); this.selC = h('select', { 'aria-label': 'Campaña' }); this.chips = h('div', { class: 'chips' });
    this.selV.addEventListener('change', () => { this.f.vendedor = this.selV.value; this.actualizar(); }); this.selC.addEventListener('change', () => { this.f.campana = this.selC.value; this.actualizar(); });
    this.tabla = Tabla({ alto: 430, vacio: 'No hay proyecciones con estos filtros', onDbl: (f) => IngresoPag.editar(f.id), onSel: (s) => this.alSeleccionar(s), ordenar: (c) => this.ordenar(c),
      cols: [{ id: 'n', t: '#', cls: 'c', ord: true, w: '48px' }, { id: 'fecha', t: 'Fecha', cls: 'c', ord: true }, { id: 'vend', t: 'Vendedor', ord: true, render: vendPunto }, { id: 'id', t: 'ID ↗', cls: 'c', ord: true, render: (f) => celdaEnlace(f.etq_id, f.url) },
        { id: 'lead', t: 'Lead', ord: true, cls: 'corto', render: (f) => celdaEnlace(f.lead, f.url) }, { id: 'campana', t: 'Campaña', ord: true, cls: 'corto', render: (f) => f.campana || '—' },
        { id: 'monto', t: 'Monto', cls: 'd', ord: true, render: (f) => fm(f.monto) }, { id: 'tipo', t: 'Tipo', ord: true, render: (f) => etqTipo(f.tipo) }] });
    this.estado = h('span', { class: 'muted', style: { marginLeft: 'auto', fontSize: '12.5px' } });
    this.b = { perdida: boton('Marcar Perdida', () => this.marcar('perdida'), 'chico'), exitosa: boton('Marcar Exitosa', () => this.marcar('exitosa'), 'chico'), editar: boton('Editar', () => this.editar(), 'chico'),
      regresar: boton('Regresar a Seguimiento', () => this.regresar(), 'chico'), eliminar: boton('Eliminar', () => this.eliminar(), 'chico rojo'), deshacer: boton('Deshacer eliminación', () => deshacer().then(() => cambio()), 'chico') };
    this.resumen = h('div', { class: 'card tabla-caja', style: { marginTop: '12px' } });
    this.alSeleccionar([]);
    const c = cab('Historial', '', [boton('Exportar datos', () => Dialogos.exportar())]); this.c = c;
    this.teclas = (e) => { if (window.app.actual !== 'historial') return; if (e.key === 'Delete' && !/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) this.eliminar(); if (e.key === 'f' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this.busca.focus(); this.busca.select(); } };
    document.addEventListener('keydown', this.teclas);
    return h('div', { class: 'pag' }, c.el,
      h('div', { class: 'card', style: { padding: '14px', marginBottom: '12px' } }, h('div', { class: 'hl', style: { flexWrap: 'nowrap' } }, h('div', { style: { flex: 1, minWidth: '180px' } }, this.busca), h('div', { style: { width: '170px' } }, this.selV), h('div', { style: { width: '200px' } }, this.selC), boton('Limpiar filtros', () => this.limpiar())), h('div', { style: { marginTop: '10px' } }, this.chips)),
      h('div', { class: 'card tabla-caja' }, this.tabla.el, this.pieTabla = pie('')),
      h('div', { class: 'hl', style: { margin: '12px 2px 0' } }, this.b.perdida, this.b.exitosa, h('span', { style: { width: '8px' } }), this.b.editar, this.b.regresar, this.b.eliminar, h('span', { style: { width: '8px' } }), this.b.deshacer, this.estado), this.resumen);
  },
  alSeleccionar(s) { if (!this.b) return; const n = s.length; ['perdida', 'exitosa', 'regresar', 'eliminar'].forEach((k) => (this.b[k].disabled = !n)); this.b.editar.disabled = n !== 1; },
  async actualizar() {
    const r = await API.historial(this.f.texto, this.f.vendedor, this.f.campana, this.f.tipo, this.ord.col, this.ord.inv); if (r.error) return avisar(r.error);
    this.c.sub.textContent = r.periodo;
    const llenar = (sel, op, valor) => { vaciar(sel).append(...op.map((o) => h('option', { value: o }, o))); sel.value = op.includes(valor) ? valor : op[0]; return sel.value; };
    this.f.vendedor = llenar(this.selV, ['(Todos)'].concat(r.vendedores), this.f.vendedor); this.f.campana = llenar(this.selC, ['(Todas)'].concat(r.campanas), this.f.campana);
    const tot = r.conteo.activa + r.conteo.perdida + r.conteo.exitosa;
    vaciar(this.chips).append(...[['(Todos)', 'Todas', tot], ['activa', 'Activas', r.conteo.activa], ['perdida', 'Perdidas', r.conteo.perdida], ['exitosa', 'Exitosas', r.conteo.exitosa]].map(([v, t, n]) =>
      h('button', { class: 'chip' + (this.f.tipo === v ? ' on' : ''), onclick: () => { this.f.tipo = v; this.actualizar(); } }, `${t} (`, h('b', null, n), ')')));
    this.tabla.set(r.filas, { orden: this.ord });
    const et = { activa: 'Activa', perdida: 'Perdida', exitosa: 'Exitosa' };
    this.pieTabla.textContent = `Mostrando ${r.filas.length} de ${r.total_vista}  ·  Total ${fm(r.total)}  (${['activa', 'perdida', 'exitosa'].map((t) => `${et[t]} ${fm(r.suma[t])}`).join(' · ')})`;
    this.estado.textContent = ''; this.b.deshacer.disabled = !r.hay_papelera;
    vaciar(this.resumen).append(h('div', { class: 'tabla-scroll', style: { '--alto': '260px' } }, h('table', { class: 't' }, h('thead', null, h('tr', null, [['Vendedor', ''], ['Activas', 'c'], ['Monto activas', 'd'], ['Perdidas', 'c'], ['Monto perdidas', 'd'], ['Exitosas', 'c'], ['Monto exitosas', 'd'], ['Total', 'c'], ['Monto total', 'd'], ['% perdido', 'd']].map(([t, c]) => h('th', { class: c }, t)))),
      h('tbody', null, r.resumen.map((x) => h('tr', { class: x.id === 'TOTAL' ? 'total' : '' }, h('td', null, x.nombre), h('td', { class: 'c' }, x.d.activa[0]), h('td', { class: 'd' }, fm(x.d.activa[1])), h('td', { class: 'c' }, x.d.perdida[0]), h('td', { class: 'd' }, fm(x.d.perdida[1])),
        h('td', { class: 'c' }, x.d.exitosa[0]), h('td', { class: 'd' }, fm(x.d.exitosa[1])), h('td', { class: 'c' }, x.n), h('td', { class: 'd' }, fm(x.m)), h('td', { class: 'd' }, x.pp)))))));
  },
  ordenar(col) { if (this.ord.col === col) this.ord.inv = !this.ord.inv; else this.ord = { col, inv: false }; this.actualizar(); },
  limpiar() { this.f = { texto: '', vendedor: '(Todos)', campana: '(Todas)', tipo: '(Todos)' }; this.busca.value = ''; this.actualizar(); },
  async marcar(t) { const ids = this.tabla.sel; if (!ids.length) return; await API.marcar(ids, t); await cambio(); toast(`Marcadas como ${t === 'perdida' ? 'perdidas' : 'exitosas'}: ${ids.length}`); },
  editar() { const id = this.tabla.sel[0]; if (id) IngresoPag.editar(id); },
  async eliminar() { const ids = this.tabla.sel; if (!ids.length) return; if (await confirmar(`¿Eliminar ${ids.length} proyección(es) seleccionada(s)?\n(Podrás deshacerlo.)`, { titulo: 'Eliminar', si: 'Eliminar', peligro: true })) eliminarConAviso(ids); },
  async regresar() {
    const ids = this.tabla.sel; if (!ids.length) return;
    if (!(await confirmar(`¿Regresar ${ids.length} lead(s) a Seguimiento?\n\nDesaparecen de esta tabla y de todos los totales. Quedan anotados en Configuración → Historial de regresos, desde donde se pueden restaurar.`, { titulo: 'Regresar a Seguimiento', si: 'Regresar' }))) return;
    const r = await API.regresar(ids); if (r.error) return avisar(r.error); await cambio(); toast(`${r.n} lead(s) regresado(s) a Seguimiento`);
  },
};

/* ============================================================= CAMPAÑAS */
const CampanasPag = {
  id: 'campanas', titulo: 'Campañas', skeleton: 'tarjetas',
  montar() {
    this.vend = '(Todos)'; this.selV = h('select', { 'aria-label': 'Vendedor', style: { width: '180px' } }); this.selV.addEventListener('change', () => { this.vend = this.selV.value; this.actualizar(); });
    this.lider = h('div', { class: 'card lider-card' }); this.rank = h('div', { class: 'card' }); this.part = h('div', { class: 'card' });
    const c = cab('Campañas', '', []); this.c = c; this.acc = c.el.querySelector('.acciones');
    return h('div', { class: 'pag' }, c.el, this.lider, h('div', { class: 'cuerpo-camp' }, this.rank, this.part));
  },
  async actualizar() {
    const r = await API.campanas(this.vend); if (r.error) return avisar(r.error);
    this.c.sub.textContent = r.cuando + (this.vend === '(Todos)' ? '' : ' · ' + this.vend);
    const sv = this.selV; vaciar(sv).append(...r.vendedores.map((o) => h('option', { value: o }, o))); sv.value = r.vendedor;
    vaciar(this.acc).append(filtroTiempo(refrescarVista), h('span', { class: 'muted' }, 'Vendedor'), sv);
    const t = r.top; vaciar(this.lider).append(h('div', null, h('div', { class: 'et' }, 'Campaña más solicitada'), h('div', { class: 'nom' }, t ? t.campana : '—')),
      h('div', null, h('div', { class: 'val num' }, t ? fm0(t.neto) : ''), h('div', { class: 'muted', style: { textAlign: 'right' } }, t ? `recaudado en ${t.leads} leads · ${t.n_neto} ventas` : 'sin proyecciones en esta vista')));
    vaciar(this.rank).append(h('h2', null, 'Ranking de campañas'), h('div', { style: { marginTop: '8px' } }, r.tipo_rank === 'pareto' ? rankingPareto(r.rank, r.total) : rankingBarras(r.rank)));
    vaciar(this.part).append(h('h2', null, 'Participación'), donaCampanas(r.rank, r.total, r.tipo_dona));
  },
};

/* ============================================================= EMBUDOS */
const EmbudosPag = {
  id: 'embudos', titulo: 'Embudos', skeleton: 'tarjetas',
  montar() { this.grid = h('div', { class: 'embudos stagger' }); const c = cab('Embudos', '', []); this.c = c; this.acc = c.el.querySelector('.acciones'); return h('div', { class: 'pag' }, c.el, this.grid); },
  async actualizar() {
    const r = await API.embudos(); if (r.error) return avisar(r.error);
    this.c.sub.textContent = r.cuando;
    const med = selectEl(S.estado.medidas, r.medida, async (m) => { await API.fijar_vista(null, null, null, null, m); await refrescarEstado(); this.actualizar(); }, { 'aria-label': 'Medir por', style: { width: '140px' } });
    vaciar(this.acc).append(filtroTiempo(refrescarVista), h('span', { class: 'muted' }, 'Medir por'), med);
    vaciar(this.grid).append(...r.items.map((it, i) => h('div', { class: 'card alza', style: { '--i': i } }, h('div', { class: 'hl', style: { marginBottom: '4px', flexWrap: 'nowrap' } }, h('i', { class: 'punto', style: { background: colorVend(it.ci).s, width: '11px', height: '11px' } }), h('h2', { style: { margin: 0 } }, it.nombre)), graficoEmbudo(it.embudo, r.medida === S.estado.medidas[0], r.tipo))));
  },
};

/* ============================================================= REPORTES GUARDADOS */
const ReportesPag = {
  id: 'reportes', titulo: 'Reportes guardados', skeleton: 'tabla',
  montar() {
    this.tabla = Tabla({ multi: false, alto: 460, vacio: 'Todavía no hay reportes guardados. Se crean desde Panel principal → Guardar reporte.', onDbl: (f) => this.ver(f.id), onSel: (s) => this.sel(s),
      cols: [{ id: 'periodo', t: 'Periodo' }, { id: 'vista', t: 'Vista' }, { id: 'meta', t: 'Meta equipo', cls: 'd', render: (f) => fm(f.meta) }, { id: 'neto', t: 'Recibido', cls: 'd', render: (f) => fm(f.neto) }, { id: 'proy', t: 'Proyectado', cls: 'd', render: (f) => fm(f.proy) },
        { id: 'pc', t: '% meta', cls: 'd', render: (f) => pct1(f.neto, f.meta) }, { id: 'falta', t: 'Falta / Superó', cls: 'd', render: (f) => (f.meta <= 0 ? '—' : f.falta > 0 ? 'Falta ' + fm(f.falta) : 'Superó ' + fm(-f.falta)) }, { id: 'creado', t: 'Guardado', cls: 'c' }] });
    this.bs = { ver: boton('Ver detalle', () => this.ver(), ''), pdf: boton('Descargar PDF', () => this.pdf(), 'primario'), del: boton('Eliminar', () => this.eliminar(), 'rojo') };
    const c = cab('Reportes guardados', '', [this.bs.ver, this.bs.pdf, this.bs.del]); this.c = c; this.sel([]);
    return h('div', { class: 'pag' }, c.el, h('div', { class: 'card tabla-caja' }, this.tabla.el), h('p', { class: 'muted', style: { margin: '12px 4px' } }, 'Cada reporte guarda la vista (semana o mes) con la meta mensual y semanal de cada vendedor en ese momento. Se crean desde Panel principal → Guardar reporte.'));
  },
  sel(s) { if (this.bs) Object.values(this.bs).forEach((b) => (b.disabled = !s.length)); },
  async actualizar() { const r = await API.reportes(); this.c.sub.textContent = `${r.filas.length} reporte(s) guardado(s)`; this.tabla.set(r.filas); },
  ver(id) { id = id || this.tabla.sel[0]; if (id) Dialogos.verReporte(id); },
  pdf() { const id = this.tabla.sel[0]; if (id) PanelPag.pdf.call(PanelPag, id); },
  async eliminar() { const id = this.tabla.sel[0]; const f = this.tabla.filas.find((x) => x.id === id); if (!f) return; if (await confirmar(`¿Eliminar el reporte «${f.titulo}»?\nEsta acción no se puede deshacer.`, { titulo: 'Eliminar reporte', si: 'Eliminar', peligro: true })) { await API.eliminar_reporte(id); await cambio(); } },
};

/* ============================================================= VENDEDORES Y METAS */
const AjustesPag = {
  id: 'ajustes', titulo: 'Vendedores y metas', skeleton: 'tabla',
  montar() {
    this.tabla = Tabla({ multi: false, alto: 440, vacio: 'Aún no hay vendedores. Pulsa «Agregar vendedor».', onDbl: (f) => this.editar(f.id), onSel: (s) => this.sel(s), id: (f) => f.id,
      cols: [{ id: 'nombre', t: 'Vendedor', render: (f) => (f.total ? 'TOTAL' : vendPunto({ vendedor: f.nombre, ci: f.ci })) }, { id: 'mes', t: 'Meta mensual', cls: 'd', render: (f) => fm(f.mes) },
        { id: 'sem', t: 'Meta semanal', cls: 'd', render: (f) => (f.sem ? fm(f.sem) : `auto (${fm(f.sem_auto)})`) }, { id: 'n', t: 'Proyecciones', cls: 'c' }], filaClase: (f) => (f.total ? 'total' : '') });
    this.bs = { ed: boton('Editar', () => this.editar(), ''), del: boton('Eliminar', () => this.eliminar(), 'rojo') };
    const c = cab('Vendedores y metas', '', [boton('Agregar vendedor', () => this.agregar(), 'primario'), this.bs.ed, this.bs.del, boton('Deshacer eliminación', () => deshacer().then(() => cambio()))]); this.c = c; this.sel([]);
    return h('div', { class: 'pag' }, c.el, h('div', { class: 'card tabla-caja' }, this.tabla.el), h('p', { class: 'muted', style: { margin: '12px 4px' } }, 'La meta de cada vendedor vale desde el mes elegido en adelante. Si dejas la meta semanal vacía se usa la mensual ÷ 4.'));
  },
  sel(s) { if (this.bs) { const hay = s.length && s[0] !== '__total__'; this.bs.ed.disabled = !hay; this.bs.del.disabled = !hay; } },
  async actualizar() {
    const r = await API.vendedores_metas(); this.c.sub.textContent = 'Metas de ' + r.titulo_periodo;
    this.tabla.set(r.filas.concat(r.filas.length ? [{ id: '__total__', total: true, mes: r.total.mes, sem: r.total.sem, sem_auto: 0, n: r.total.n, nombre: 'TOTAL' }] : []));
  },
  agregar() { Dialogos.vendedor(null); }, editar(id) { id = id || this.tabla.sel[0]; if (id && id !== '__total__') Dialogos.vendedor(id); },
  async eliminar() { const id = this.tabla.sel[0]; const f = this.tabla.filas.find((x) => x.id === id); if (!f || f.total) return;
    if (await confirmar(`¿Eliminar a ${f.nombre}?\n\nTambién se eliminarán sus ${f.n} proyección(es) y sus metas.\n(Podrás deshacerlo.)`, { titulo: 'Eliminar vendedor', si: 'Eliminar', peligro: true })) { const r = await API.eliminar_vendedor(id); if (r.error) return avisar(r.error); await cambio(); toast('Vendedor eliminado', { accion: { texto: 'Deshacer', fn: deshacer } }); } },
};

/* ============================================================= CONFIGURACION */
const ConfigPag = {
  id: 'config', titulo: 'Configuración', skeleton: 'form',
  montar() { this.cont = h('div', { class: 'stagger' }); const c = cab('Configuración', 'Conexión, gráficas y datos', []); return h('div', { class: 'pag' }, c.el, this.cont); },
  async actualizar() {
    const r = await API.config(); const sec = (t, ay, ...c) => h('div', { class: 'card seccion' }, h('h2', null, t), h('p', { class: 'ayuda' }, ay), h('div', { class: 'cuerpo' }, c));
    const hook = h('input', { type: 'text', value: r.webhook, placeholder: 'https://tuempresa.bitrix24.es/rest/1/clave/', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Webhook' });
    const campo = h('input', { type: 'text', value: r.campo, style: { maxWidth: '260px' }, 'aria-label': 'Campo de campaña' });
    const graficas = S.estado.areas_graficas.map((a) => h('div', { class: 'hl', style: { justifyContent: 'space-between', flexWrap: 'nowrap', margin: '6px 0' } }, h('span', null, a.label),
      h('div', { style: { width: '340px', maxWidth: '55%' } }, selectEl(S.estado.opciones_graficas[a.id], r.graficas[a.id], async (v) => { const x = await API.cambiar_grafica(a.id, v); if (x.error) return avisar(x.error); await refrescarEstado(); toast('Gráfica cambiada'); }, { 'aria-label': a.label }))));
    const estadoAct = h('span', { class: 'muted' });
    vaciar(this.cont).append(
      sec('Conexión con Bitrix24', 'Con el webhook, al pegar un lead se llenan solos el monto, la campaña y el vendedor.',
        h('label', { class: 'et' }, 'Webhook de entrada'), hook, h('div', { style: { height: '10px' } }), h('label', { class: 'et' }, 'Campo de Bitrix24 con la campaña'), campo,
        h('p', { class: 'ayuda', style: { margin: '6px 0 12px' } }, 'Déjalo en «auto» para usar «Seleccione Campaña» y, si está vacío, «Campaña». Si no la encuentra, usa «Probar con un lead».'),
        h('div', { class: 'hl' }, boton('Guardar', async () => { const x = await API.guardar_conexion(hook.value, campo.value); if (x.error) { hook.classList.add('malo'); setTimeout(() => hook.classList.remove('malo'), 1400); return avisar(x.error); } hook.value = x.webhook; await refrescarEstado(); await avisar(x.webhook ? 'Conexión guardada.' : 'Conexión desactivada (webhook vacío).'); }, 'primario'),
          boton('Probar con un lead', () => this.probar(hook.value)))),
      sec('Gráficas', 'Elige cómo se dibuja cada sección.', graficas),
      sec('Mis datos', 'Todo se guarda solo en tu computadora, en esta carpeta:', h('div', { class: 'leer-pre', style: { padding: '8px 12px', marginBottom: '12px', whiteSpace: 'normal', wordBreak: 'break-all' } }, r.ruta),
        h('div', { class: 'hl' }, boton('Importar datos', () => Dialogos.importar()), boton('Exportar datos', () => Dialogos.exportar()), boton('Abrir carpeta de datos', () => API.abrir_carpeta())),
        h('p', { class: 'muted', style: { margin: '16px 0 8px', fontSize: '12.5px' } }, 'Zona de borrado (se hace una copia de seguridad antes de borrar todo)'),
        h('div', { class: 'hl' }, boton('Vaciar este periodo', () => this.vaciar(), 'rojo'), boton('Borrar TODAS las proyecciones…', () => this.borrarTodo(), 'rojo'))),
      sec('Historial de regresos a Seguimiento', 'Leads que regresaron a Seguimiento: salieron de la tabla y de los totales.', h('p', { style: { margin: '0 0 10px' } }, r.n_regresos ? `${r.n_regresos} lead(s) regresado(s)` : 'Todavía no hay regresos.'), boton('Ver historial', () => Dialogos.regresos())),
      sec('Versión', `Versión ${r.version}. Cuando se publica una nueva, el programa instalado te avisa al abrirlo.`, h('div', { class: 'hl' }, boton('Buscar actualización', () => app.buscarActualizacion(true)), estadoAct)));
  },
  async probar(webhook) {
    const lead = await pedirTexto('Probar conexión', 'Enlace o ID de un lead para probar:'); if (!lead) return;
    const r = await API.probar_conexion(webhook, lead); if (r.error) return avisar(r.error, 'No se pudo probar');
    modal({ titulo: 'Conexión correcta', ancho: 560, cuerpo: [h('p', null, `Campos con valor en el lead ${r.id}:`), h('div', { class: 'leer-pre' }, r.campos.join('\n')), h('p', { class: 'muted' }, 'Escribe en «Campo de la campaña» el nombre del que trae la campaña.')], botones: [{ texto: 'Cerrar', tipo: 'primario', valor: true }] });
  },
  async vaciar() { const r = await API.cuenta_periodo(); if (!r.n) return avisar('Este periodo no tiene proyecciones.'); if (await confirmar(`Se eliminarán las ${r.n} proyecciones de ${r.titulo_periodo}.\n(Podrás deshacerlo con «Deshacer eliminación».)\n\n¿Continuar?`, { titulo: 'Vaciar periodo', si: 'Vaciar', peligro: true })) { await API.vaciar_periodo(); await cambio(); toast('Periodo vaciado', { accion: { texto: 'Deshacer', fn: deshacer } }); } },
  async borrarTodo() { const r = await API.cuenta_periodo(); if (!r.total) return avisar('No hay proyecciones guardadas.');
    if (!(await confirmar(`Se borrarán las ${r.total} proyecciones de TODOS los periodos.\n\nSe conservan vendedores, metas, reportes guardados y la conexión con Bitrix24.\nAntes se hace una copia de seguridad en la carpeta «copias».\n\n¿Continuar?`, { titulo: 'Borrar todo', si: 'Borrar todo', peligro: true }))) return;
    const x = await API.borrar_todo(); if (x.error) return avisar(x.error); await cambio(); await avisar(`Listo: se borraron ${x.n} proyecciones.` + (x.copia ? `\n\nCopia de seguridad:\n${x.copia}` : ''), 'Datos borrados'); },
};

const PAGINAS = { panel: PanelPag, ingreso: IngresoPag, historial: HistorialPag, campanas: CampanasPag, embudos: EmbudosPag, reportes: ReportesPag, ajustes: AjustesPag, config: ConfigPag };

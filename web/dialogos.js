/* Ventanas emergentes: vendedor, regresos, reporte guardado, importar, exportar, ejemplo, actualizaciones, novedades. */
'use strict';
const Dialogos = {
  /* ---------- agregar / editar vendedor ---------- */
  async vendedor(vid) {
    let d = { nombre: '', mes: '', sem: '', titulo_periodo: S.estado.vista.titulo_periodo };
    if (vid) { d = await API.datos_vendedor(vid); if (d.error) return avisar(d.error); }
    const nom = h('input', { type: 'text', value: d.nombre, autocomplete: 'off', 'aria-label': 'Nombre' }), mes = h('input', { type: 'text', value: d.mes, inputmode: 'decimal', autocomplete: 'off', 'aria-label': 'Meta mensual' }), sem = h('input', { type: 'text', value: d.sem, inputmode: 'decimal', autocomplete: 'off', 'aria-label': 'Meta semanal' });
    const campos = { nombre: nom, mes, sem };
    const cuerpo = h('div', { class: 'fila-campos' }, h('div', null, h('label', { class: 'et' }, 'Nombre del vendedor'), nom), h('div', null, h('label', { class: 'et' }, 'Meta mensual ($)'), mes),
      h('div', null, h('label', { class: 'et' }, 'Meta semanal ($)  ·  vacío = mensual ÷ 4'), sem), h('p', { class: 'muted', style: { margin: '2px 2px 0', fontSize: '12.5px' } }, `La meta vale desde ${d.titulo_periodo} en adelante.`));
    modal({ titulo: vid ? 'Editar vendedor' : 'Agregar vendedor', cuerpo, botones: [{ texto: 'Cancelar', valor: false },
      { texto: 'Guardar', tipo: 'primario', fn: async (cerrar) => { const r = await API.guardar_vendedor(vid, nom.value, mes.value, sem.value);
        if (r.error) { const e = campos[r.campo]; if (e) { e.classList.add('malo'); e.focus(); setTimeout(() => e.classList.remove('malo'), 1400); } return toast(r.error, { err: true }); } cerrar(true); await cambio(); toast(vid ? 'Vendedor actualizado' : 'Vendedor agregado'); } }] });
  },

  /* ---------- historial de regresos a Seguimiento ---------- */
  async regresos() {
    const r = await API.regresos(); const info = h('p', { class: 'muted', style: { margin: '2px 0 10px' } });
    const btn = boton('Restaurar seleccionados', null, 'primario'); btn.disabled = true;
    const t = Tabla({ alto: 380, vacio: 'Todavía no hay leads regresados a Seguimiento.', onSel: (s) => (btn.disabled = !s.length),
      cols: [{ id: 'regreso', t: 'Regresó el', cls: 'c' }, { id: 'vendedor', t: 'Vendedor', render: vendPunto }, { id: 'etq_id', t: 'ID ↗', cls: 'c', render: (f) => celdaEnlace(f.etq_id, f.url) }, { id: 'campana', t: 'Campaña', cls: 'corto', render: (f) => f.campana || '—' },
        { id: 'monto', t: 'Monto', cls: 'd', render: (f) => fm(f.monto) }, { id: 'tipo', t: 'Estaba', render: (f) => etqTipo(f.tipo) }, { id: 'periodo', t: 'Periodo' }] });
    const pintar = (filas) => { t.set(filas); info.textContent = filas.length ? `${filas.length} regreso(s). Para devolver uno a las tablas, selecciónalo y pulsa «Restaurar».` : 'Todavía no hay leads regresados a Seguimiento.'; };
    pintar(r.filas);
    btn.onclick = async () => { const ids = t.sel; const x = await API.restaurar_regresos(ids); if (x.error) return avisar(x.error); const n = await API.regresos(); pintar(n.filas); await cambio(); toast(`Se restauraron ${x.n} lead(s) a su periodo.`); };
    modal({ titulo: 'Historial de regresos a Seguimiento', ancho: 940, cuerpo: [info, h('div', { class: 'card tabla-caja', style: { padding: '4px' } }, t.el)], botones: [btn, { texto: 'Cerrar', valor: true }] });
  },

  /* ---------- detalle de un reporte guardado ---------- */
  async verReporte(rid) {
    const r = await API.reporte_guardado(rid); if (r.error) return avisar(r.error); const m = r.modelo, top = m.campanas[0];
    const filas = m.filas.concat([Object.assign({}, m.equipo, { nombre: 'Equipo', meta_mes: r.mes_total, meta_sem: r.sem_total, _t: true })]);
    const tabla = h('div', { class: 'tabla-scroll', style: { '--alto': '340px' } }, h('table', { class: 't' }, h('thead', null, h('tr', null, [['Vendedor', ''], ['Meta mensual', 'd'], ['Meta semanal', 'd'], ['Meta aplicada', 'd'], ['Recibido', 'd'], ['Proyectado', 'd'], ['% meta', 'd'], ['Falta / Superó', 'd']].map(([t, c]) => h('th', { class: c }, t)))),
      h('tbody', null, filas.map((f) => h('tr', { class: f._t ? 'total' : '' }, h('td', null, f.nombre), h('td', { class: 'd' }, fm(f.meta_mes)), h('td', { class: 'd' }, fm(f.meta_sem)), h('td', { class: 'd' }, fm(f.meta)), h('td', { class: 'd' }, fm(f.neto)), h('td', { class: 'd' }, fm(f.proy)),
        h('td', { class: 'd' }, pct1(f.neto, f.meta)), h('td', { class: 'd' }, f.meta > 0 ? (f.falta_neto > 0 ? 'Falta ' + fm(f.falta_neto) : 'Superó ' + fm(-f.falta_neto)) : '—'))))));
    modal({ titulo: m.titulo, ancho: 960, cuerpo: [h('p', { class: 'muted', style: { marginTop: 0 } }, `Guardado el ${r.creado} · las metas son las que estaban asignadas en ese momento`), tabla,
      h('p', { class: 'rojo-t', style: { fontWeight: 650 } }, top && top.neto > 0 ? `Campaña más vendida: ${top.campana}  ·  ${fm(top.neto)} en ${top.n_neto} ventas` : 'Sin ventas exitosas')],
      botones: [{ texto: 'Descargar PDF', fn: () => PanelPag.pdf(rid) }, { texto: 'Cerrar', tipo: 'primario', valor: true }] });
  },

  /* ---------- ejemplo de archivo para importar ---------- */
  ejemplo() {
    const enc = ['Fecha', 'Asesor', 'Enlace', 'Campaña', 'Monto', 'Estado'];
    const filas = [['06/11/2026', 'Lesly', 'https://dreamtravel.bitrix24.es/crm/deal/details/472763/', 'Personalizado boston', '1,323.80', 'Exitosa'], ['06/11/2026', 'Susana', '474865', 'Madrid', '18,810.00', 'Activa'], ['03/11/2026', 'Debi', 'https://dreamtravel.bitrix24.es/crm/deal/details/471002/', 'Cancún', '2,500.00', 'Perdida']];
    const letras = 'ABCDEF'.split('');
    modal({ titulo: 'Así debe verse tu archivo', ancho: 860, cuerpo: [h('p', { class: 'muted', style: { marginTop: 0 } }, 'Primera hoja de Excel (o una tabla CSV). Los encabezados pueden llamarse distinto: luego eliges qué columna es cuál.'),
      h('div', { class: 'tabla-scroll' }, h('table', { class: 't' }, h('thead', null, h('tr', null, h('th', null, ''), letras.map((l) => h('th', { class: 'c' }, l)))), h('tbody', null,
        h('tr', null, h('td', { class: 'muted c' }, '1'), enc.map((e) => h('td', { style: { background: 'var(--btn)', color: '#fff', fontWeight: 650 } }, e))),
        filas.map((f, i) => h('tr', null, h('td', { class: 'muted c' }, i + 2), f.map((v) => h('td', { class: 'corto' }, v))))))),
      h('ul', { class: 'ayuda-lista', style: { paddingLeft: '18px' } }, h('li', null, 'Fecha como dd/mm/aaaa.  ·  Enlace de Bitrix24 o solo el ID.  ·  Monto como número.'), h('li', null, 'Estado: Activa, Perdida (o Baja) o Exitosa.  ·  El asesor debe ser uno de tus vendedores.'),
        h('li', null, 'JSON: una lista de objetos con esos mismos nombres, o un archivo exportado desde esta app.'))],
      botones: [{ texto: 'Cerrar', tipo: 'primario', valor: true }] });
  },

  /* ---------- importar ---------- */
  importar() {
    let enc = [], campos = [], hay = false;
    const NINGUNA = '(no importar)', selects = {}, mapaDiv = h('div', { class: 'mapa-col' }), vista = h('div', { class: 'leer-pre', style: { minHeight: '260px' } }, 'Elige un archivo para ver la vista previa.');
    const lbl = h('span', { class: 'muted' }, 'Aún no has elegido un archivo.'), arch = h('span', { class: 'muted' }), btnImp = boton('Importar', null, 'primario'); btnImp.disabled = true;
    const mapa = () => { const m = {}; for (const [k, s] of Object.entries(selects)) if (s.value !== '') m[k] = +s.value; return m; };
    const pintarVista = (v) => {
      const L = []; if (v.vista.length) { L.push(['Fecha', 'Asesor', 'ID', 'Campaña', 'Monto', 'Estado'].join(' | ')); v.vista.forEach((f) => L.push(f.join(' | ').slice(0, 150))); if (v.nuevos > v.vista.length) L.push('…'); }
      if (v.repetidos) L.push('', `${v.repetidos} repetidas (ya registradas; se omiten).`);
      if (v.n_errores) { L.push('', `${v.n_errores} filas con problemas (no se importan):`); v.errores.slice(0, 8).forEach(([n, m]) => L.push(`  Fila ${n}: ${m}`)); if (v.n_errores > 8) L.push(`  … y ${v.n_errores - 8} más`); }
      vista.textContent = L.join('\n') || 'No hay filas nuevas para importar.';
      const per = Object.entries(v.periodos).map(([k, n]) => `${k}: ${n}`).join(', ');
      lbl.textContent = `${v.nuevos} nuevas · total ${fm(v.total)}${per ? ' · ' + per : ''}`; btnImp.textContent = v.nuevos ? `Importar ${v.nuevos}` : 'Importar'; btnImp.disabled = !v.nuevos;
    };
    const recalcular = async () => { if (!hay) return; const v = await API.imp_vista(mapa()); if (v.error) return toast(v.error, { err: true }); pintarVista(v); };
    const cargarResultado = (r) => {
      enc = r.encabezados; campos = r.campos; hay = true; arch.textContent = r.archivo; vaciar(mapaDiv);
      campos.forEach((c) => { const s = h('select', { 'aria-label': c.label }, h('option', { value: '' }, NINGUNA), enc.map((e, i) => h('option', { value: i }, e))); s.value = r.mapa[c.id] !== undefined ? String(r.mapa[c.id]) : ''; s.addEventListener('change', recalcular); selects[c.id] = s;
        mapaDiv.appendChild(h('div', null, h('label', { class: 'et' }, c.label + (c.req ? ' *' : '')), s)); });
      mapaDiv.appendChild(h('div', { class: 'muted', style: { fontSize: '12px' } }, '* obligatorias')); pintarVista(r.vista);
    };
    const elegir = async () => { const r = await API.imp_elegir(); if (r.cancelado) return; if (r.error) return avisar(r.error); cargarResultado(r); };
    let cerrarImp = null;
    btnImp.onclick = async () => { const r = await API.imp_aplicar(mapa()); if (r.error) return avisar(r.error); cerrarImp && cerrarImp(true); await cambio(); await avisar(`Se importaron ${r.nuevos} proyecciones (${fm(r.total)}).`, 'Importación lista'); };
    const cuerpo = h('div', null, h('p', { class: 'muted', style: { marginTop: 0 } }, 'Excel (.xlsx), CSV o JSON. Elige el archivo, revisa la vista previa y confirma las columnas.'),
      h('div', { class: 'hl', style: { marginBottom: '12px' } }, boton('Elegir archivo…', elegir, 'primario'), boton('Descargar plantilla', async () => { const r = await API.imp_plantilla(); if (r.error) return avisar(r.error); if (!r.cancelado) lbl.textContent = 'Plantilla guardada. Llénala y luego elige el archivo.'; }), boton('Ver ejemplo', () => Dialogos.ejemplo()), arch),
      h('div', { class: 'cols-2', style: { gridTemplateColumns: '270px 1fr' } }, h('div', null, h('div', { class: 'muted', style: { marginBottom: '6px' } }, 'Qué columna es cuál'), mapaDiv), h('div', null, h('div', { class: 'muted', style: { marginBottom: '6px' } }, 'Vista previa de lo que se importaría'), vista)));
    modal({ titulo: 'Importar datos', ancho: 1000, cuerpo: [cuerpo, h('div', { style: { marginTop: '12px' } }, lbl)], botones: [btnImp, { texto: 'Cerrar', valor: true }], alMostrar: (m, c) => (cerrarImp = c) });
  },

  /* ---------- exportar ---------- */
  async exportar() {
    const info = await API.exp_info(); const o = { formato: 0, alcance: 'elegidos', tipos: ['activa', 'perdida', 'exitosa'], preset: 0, columnas: info.columnas.filter((c) => c.defecto).map((c) => c.id), nombres: {}, extras: [] };
    info.columnas.forEach((c) => (o.nombres[c.id] = c.nombre));
    const vista = h('div', { class: 'leer-pre', style: { minHeight: '280px' } }), lbl = h('span', { class: 'muted' });
    const refrescar = async () => { const r = await API.exp_vista(o); if (r.error) return; vista.textContent = r.texto; lbl.textContent = `${r.n} filas · ${r.columnas} columnas · total ${fm(r.total)}`; };
    const chk = (txt, activo, fn) => h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: activo, onchange: (e) => fn(e.target.checked) }), txt);
    const colsDiv = h('div', { style: { display: 'none', marginTop: '8px' } }, h('div', { class: 'muted', style: { fontSize: '12px', marginBottom: '4px' } }, 'En el programa  →  Nombre en el archivo'),
      info.columnas.map((c) => h('div', { class: 'hl', style: { flexWrap: 'nowrap', margin: '4px 0' } }, h('div', { style: { width: '150px', flex: 'none' } }, chk(c.prog, o.columnas.includes(c.id), (v) => { o.columnas = v ? [...new Set([...o.columnas, c.id])] : o.columnas.filter((x) => x !== c.id); refrescar(); })), h('span', { class: 'muted' }, '→'),
        h('input', { type: 'text', value: c.nombre, oninput: (e) => { o.nombres[c.id] = e.target.value; clearTimeout(colsDiv._t); colsDiv._t = setTimeout(refrescar, 200); }, 'aria-label': 'Nombre de ' + c.prog }))));
    const extrasDiv = h('div', { style: { display: 'none', marginTop: '10px' } }, h('div', { class: 'muted', style: { fontSize: '12px', marginBottom: '4px' } }, 'Además, en el JSON'),
      [['vendedores', 'Vendedores y sus metas'], ['reportes', 'Reportes guardados'], ['completo', 'Copia completa de la app (respaldo, sin el webhook)']].map(([k, t]) => h('div', { style: { margin: '5px 0' } }, chk(t, false, (v) => { o.extras = v ? [...o.extras, k] : o.extras.filter((x) => x !== k); refrescar(); }))));
    const form = h('div', null,
      h('label', { class: 'et' }, 'Formato'), selectEl(info.formatos.map((f, i) => ({ id: String(i), label: f })), '0', (v) => { o.formato = +v; extrasDiv.style.display = o.formato === 2 ? '' : 'none'; refrescar(); }),
      h('label', { class: 'et', style: { marginTop: '12px' } }, 'Periodos'), selectEl([{ id: 'elegidos', label: `Periodos elegidos (${info.periodo})` }, { id: 'todos', label: 'Todos los periodos' }], 'elegidos', (v) => { o.alcance = v; refrescar(); }),
      h('label', { class: 'et', style: { marginTop: '12px' } }, 'Estados'), h('div', { class: 'hl' }, [['activa', 'Activa'], ['perdida', 'Perdida'], ['exitosa', 'Exitosa']].map(([k, t]) => chk(t, true, (v) => { o.tipos = v ? [...o.tipos, k] : o.tipos.filter((x) => x !== k); refrescar(); }))),
      h('label', { class: 'et', style: { marginTop: '12px' } }, 'Columnas'), selectEl(info.presets.map((f, i) => ({ id: String(i), label: f })), '0', (v) => { o.preset = +v; colsDiv.style.display = o.preset === 2 ? '' : 'none'; refrescar(); }), colsDiv, extrasDiv);
    const btn = boton('Exportar', null, 'primario');
    btn.onclick = async () => { const r = await API.exp_exportar(o); if (r.error) return avisar(r.error); if (r.cancelado) return; toast(`Exportado: ${r.n} filas`, { accion: { texto: 'Abrir carpeta', fn: () => API.abrir_ruta(r.ruta.replace(/[^\\/]*$/, '')) } }); };
    modal({ titulo: 'Exportar datos', ancho: 1040, cuerpo: [h('p', { class: 'muted', style: { marginTop: 0 } }, 'Elige formato y periodos; abajo ves cómo quedará el archivo.'), h('div', { class: 'cols-2', style: { gridTemplateColumns: '400px 1fr' } }, h('div', { style: { maxHeight: '480px', overflow: 'auto', paddingRight: '6px' } }, form), h('div', null, h('div', { class: 'muted', style: { marginBottom: '6px' } }, 'Vista previa'), vista)), h('div', { style: { marginTop: '10px' } }, lbl)], botones: [btn, { texto: 'Cerrar', valor: true }] });
    refrescar();
  },

  /* ---------- novedades tras actualizar ---------- */
  novedades(r) {
    const cuerpo = r.notas.map((s) => [h('h4', { style: { margin: '14px 0 6px', fontSize: '14.5px' } }, s.titulo), h('ul', { class: 'lista-mod', style: { margin: 0, paddingLeft: '18px' } }, s.items.map((i) => h('li', null, i)))]);
    modal({ titulo: 'Actualización v' + r.version, cuerpo, ancho: 520, botones: [{ texto: 'Entendido', tipo: 'primario', valor: true }] });
  },

  /* ---------- descarga de actualizacion ---------- */
  async descargarActualizacion(version) {
    const r0 = await API.descargar_actualizacion(); if (r0.error) return avisar(r0.error);
    const barra = h('i'), txt = h('div', { class: 'muted' }, 'Descargando…');
    modal({ titulo: `Descargando la versión ${version}…`, cuerpo: [h('div', { class: 'progreso' }, barra), txt], botones: [], cerrarConFondo: false });
    for (;;) { await new Promise((ok) => setTimeout(ok, 250)); const p = await API.progreso_actualizacion(); barra.style.width = (p.pct || 0) + '%'; txt.textContent = Math.round(p.pct || 0) + '%';
      if (p.fin) { $$('#modales .fondo').forEach((f) => f.remove());
        if (p.error) return avisar('No se pudo descargar la actualización.\n' + p.error, 'Error de actualización'); await API.instalar_actualizacion(); return; } }
  },
};

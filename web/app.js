/* Arranque, menu lateral, selector de periodo y navegacion. */
'use strict';
const NAV = [
  ['panel', 'Panel principal', 'M3 13h7V4H3v9zm0 7h7v-5H3v5zm11 0h7V11h-7v9zm0-16v5h7V4h-7z'],
  ['ingreso', 'Ingresar reporte', 'M12 5v14M5 12h14'],
  ['historial', 'Historial', 'M12 8v5l3 2M3 12a9 9 0 1 0 3-6.7M3 4v5h5'],
  ['campanas', 'Campañas', 'M4 20V10M10 20V4M16 20v-8M22 20H2'],
  ['embudos', 'Embudos', 'M3 4h18l-7 8v6l-4 2v-8L3 4z'],
  ['reportes', 'Reportes guardados', 'M6 3h9l4 4v14H6V3zm9 0v4h4M9 12h7M9 16h7'],
  ['ajustes', 'Vendedores y metas', 'M16 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM21 20v-2a4 4 0 0 0-3-3.9M16 3.1a3.5 3.5 0 0 1 0 6.8'],
  ['config', 'Configuración', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z'],
];

const app = window.app = {
  actual: null, pag: null, _tok: 0,
  async ir(id, { animar = true } = {}) {
    const P = PAGINAS[id]; if (!P) return;
    if (this.pag && this.pag.alSalir) this.pag.alSalir();
    this.actual = id; this.pag = P; const tok = ++this._tok;
    $$('.nav').forEach((b) => { const on = b.dataset.id === id; b.classList.toggle('on', on); b.setAttribute('aria-current', on ? 'page' : 'false'); });
    const vista = $('#vista'); const sk = skPagina(P.skeleton); vaciar(vista).appendChild(sk); vista.scrollTop = 0;
    if (!P._marco) P._marco = P.montar();                                  // el marco se arma una sola vez
    await P.actualizar();
    if (tok !== this._tok) return;                                         // el usuario ya cambio de pagina
    vaciar(vista).appendChild(P._marco); vista.classList.remove('entra'); void vista.offsetWidth; if (animar) vista.classList.add('entra');
    if (P._marco._seg) P._marco._seg.forEach((s) => s._mover());
    $$('.seg', P._marco).forEach((s) => s._mover && s._mover());
  },
  async actualizarPagina() { if (this.pag) { const y = $('#vista').scrollTop; await this.pag.actualizar(); $$('.seg', this.pag._marco).forEach((s) => s._mover && s._mover()); $('#vista').scrollTop = y; } this.sello(); },
  sello() { const g = $('#guardado'); g.textContent = 'Guardado a las ' + new Date().toTimeString().slice(0, 5); g.classList.add('ok'); clearTimeout(this._sg); this._sg = setTimeout(() => g.classList.remove('ok'), 1600); },

  /* ---------- barra lateral ---------- */
  menu() { const m = vaciar($('#menu')); NAV.forEach(([id, t, d]) => m.appendChild(h('button', { class: 'nav', dataset: { id }, onclick: () => this.ir(id) }, icono(d), t))); },
  /* El selector se arma una sola vez; periodo() solo actualiza su texto, el año y los meses marcados
     (asi el panel de meses no se cierra mientras se eligen varios). */
  periodo() {
    const meses = S.estado.meses, hoy = new Date(), cont = $('#selMeses'), sa = $('#selAnio');
    const sel = () => S.estado.vista.meses;
    const resumen = () => { const s = sel(); if (s.length === 12) return 'Todos los meses'; const n = s.map((i) => (s.length === 1 ? meses[i] : S.estado.meses_abr[i])); return n.length <= 3 ? n.join(', ') : n.length + ' meses'; };
    if (!this._pp) {
      const btn = h('button', { class: 'sel-btn', 'aria-haspopup': 'true', 'aria-expanded': 'false' }, h('span', { id: 'resMeses' }), icono('M6 9l6 6 6-6', { class: 'flecha', width: 16, height: 16 }));
      const P = this._pp = { btn, pop: null, botones: [] };
      const cerrar = () => { if (P.pop) { P.pop.remove(); P.pop = null; P.botones = []; btn.setAttribute('aria-expanded', 'false'); document.removeEventListener('mousedown', fuera, true); document.removeEventListener('keydown', tecla, true); } };
      const fuera = (e) => { if (P.pop && !P.pop.contains(e.target) && !btn.contains(e.target)) cerrar(); };
      const tecla = (e) => { if (e.key === 'Escape') cerrar(); };
      const aplicar = async (s) => { if (!s.length) return; await API.fijar_vista(s); await refrescarEstado(); await this.actualizarPagina(); };
      const click = (i, e) => { let s = new Set(sel());
        if (e.ctrlKey || e.metaKey) { if (s.has(i)) { if (s.size > 1) s.delete(i); } else s.add(i); }
        else if (e.shiftKey && s.size) { const a = Math.min(...s); s = new Set(Array.from({ length: Math.abs(i - a) + 1 }, (_, k) => Math.min(a, i) + k)); } else s = new Set([i]);
        return aplicar([...s].sort((x, y) => x - y)); };
      btn.onclick = () => {
        if (P.pop) return cerrar();
        P.pop = h('div', { class: 'pop', role: 'dialog' },
          h('div', { class: 'pop-cab' }, h('button', { onclick: () => aplicar(Array.from({ length: 12 }, (_, i) => i)) }, 'Todos'), h('button', { onclick: () => aplicar([hoy.getMonth()]) }, 'Este mes')),
          h('div', { class: 'meses-grid' }, meses.map((nom, i) => { const b = h('button', { class: 'mes', onclick: (e) => click(i, e) }, S.estado.meses_abr[i]); P.botones.push(b); return b; })),
          h('div', { class: 'muted', style: { fontSize: '11.5px', margin: '9px 2px 0' } }, 'Ctrl: sumar meses · Mayús: rango'));
        cont.appendChild(P.pop); btn.setAttribute('aria-expanded', 'true'); this.periodo(); setTimeout(() => { document.addEventListener('mousedown', fuera, true); document.addEventListener('keydown', tecla, true); }, 0);
      };
      cont.appendChild(btn);
      sa.addEventListener('change', async () => { await API.fijar_vista(null, +sa.value); await refrescarEstado(); await this.actualizarPagina(); });
    }
    const P = this._pp; $('#resMeses').textContent = resumen();
    P.botones.forEach((b, i) => { b.classList.toggle('on', sel().includes(i)); b.classList.toggle('hoy', i === hoy.getMonth() && S.estado.vista.anio === hoy.getFullYear()); });
    const anios = S.estado.anios.map(String); if (sa.options.length !== anios.length || [...sa.options].some((o, i) => o.value !== anios[i])) vaciar(sa).append(...anios.map((a) => h('option', { value: a }, a)));
    sa.value = String(S.estado.vista.anio);
  },
};

async function arrancar() {
  S.estado = await API.estado(); Tema.paletas = S.estado.paletas; aplicarTema(S.estado.tema);
  app.menu(); app.periodo();
  window.addEventListener('estado', () => { app.periodo(); });
  $('#btnTema').onclick = async () => { const nuevo = Tema.nombre === 'oscuro' ? 'claro' : 'oscuro'; aplicarTema(nuevo); await API.fijar_tema(nuevo); S.estado.tema = nuevo; app.actualizarPagina(); };
  await app.ir('panel', { animar: false });
  if (S.estado.aviso) avisar(S.estado.aviso, 'Aviso');
  setTimeout(async () => { const n = await API.novedades_pendientes(); if (n && n.notas) Dialogos.novedades(n); }, 500);
  setTimeout(() => app.buscarActualizacion(false), 4000);
}
app.buscarActualizacion = async function (manual) {
  const r = await API.buscar_actualizacion(manual); if (r.error) return manual && avisar(r.error);
  if (r.estado === 'fuente') return avisar('Estás usando el código fuente; solo el programa instalado se actualiza solo.');
  if (r.estado === 'nueva') { if (await confirmar(`Hay una versión nueva (${r.version}).\nTu versión es la ${r.actual}.\n\nTus datos no se tocan. ¿Actualizar ahora?`, { titulo: 'Actualización disponible', si: 'Actualizar' })) Dialogos.descargarActualizacion(r.version); }
  else if (manual) avisar(r.estado === 'actual' ? `Ya tienes la última versión (${r.actual}).` : 'No se pudo consultar las versiones (revisa tu conexión).');
};
window.addEventListener('DOMContentLoaded', arrancar);
document.addEventListener('keydown', (e) => { if (e.ctrlKey && e.key === 'f' && app.actual !== 'historial') { e.preventDefault(); app.ir('historial').then(() => { const b = $('input[type=search]'); b && b.focus(); }); } });

/* Graficas en SVG/HTML. Los colores son variables CSS, asi que cambiar de tema las recolorea sin volver a dibujar.
   Las animaciones son transiciones CSS (rapidas, ~500 ms) que arrancan un fotograma despues de dibujar. */
'use strict';

const sigFrame = (f) => requestAnimationFrame(() => requestAnimationFrame(f));
const rad = (g) => g * Math.PI / 180;

/* ---- anillos y donas: circulos con stroke-dasharray (animables con CSS) ---- */
function circulo(cx, cy, r, ancho, color, frac, desdeFrac = 0, opc = {}) {
  const C = 2 * Math.PI * r;
  const c = h('circle', { cx, cy, r, fill: 'none', stroke: color, 'stroke-width': ancho, transform: `rotate(-90 ${cx} ${cy})`,
    'stroke-linecap': opc.redondo ? 'round' : 'butt', style: { transition: `stroke-dasharray 620ms cubic-bezier(.22,.7,.2,1) ${opc.retraso || 0}ms` } });
  const largo = Math.max(0, Math.min(1, frac)) * C;
  const dash = (l) => `${l} ${C - l}`;
  c.setAttribute('stroke-dasharray', dash(0));
  c.setAttribute('stroke-dashoffset', -desdeFrac * C);
  if (largo > 0.5) sigFrame(() => c.setAttribute('stroke-dasharray', dash(opc.redondo ? Math.max(largo, 0.01) : Math.max(largo - (opc.hueco || 0), 0.01))));
  return c;
}
function pista(cx, cy, r, ancho) { return h('circle', { cx, cy, r, fill: 'none', stroke: V('track'), 'stroke-width': ancho }); }
function marcaEsperado(cx, cy, r, ancho, esp, color) {
  const a = rad(360 * esp - 90), r1 = r - ancho / 2 - 3, r2 = r + ancho / 2 + 3;
  return h('line', { x1: cx + r1 * Math.cos(a), y1: cy + r1 * Math.sin(a), x2: cx + r2 * Math.cos(a), y2: cy + r2 * Math.sin(a), stroke: color, 'stroke-width': 3, 'stroke-linecap': 'round' });
}
/* partes = [[fraccion, 'var(--color)'], ...] */
function dona(partes, { cx, cy, r, ancho, hueco = 2 }) {
  const g = h('g'); g.appendChild(pista(cx, cy, r, ancho));
  const C = 2 * Math.PI * r; let acum = 0;
  partes.forEach(([f, col], i) => { if (f > 0.003) { g.appendChild(circulo(cx, cy, r, ancho, col, f, acum, { hueco: partes.length > 1 ? hueco : 0, retraso: i * 60 })); } acum += f; });
  return g;
}
/* pastel: sectores que "se abren" (JS) */
function sectorPath(cx, cy, r, a0, a1) {
  if (a1 - a0 >= 359.9) return `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`;
  const p = (a) => [cx + r * Math.sin(rad(a)), cy - r * Math.cos(rad(a))]; const [x0, y0] = p(a0), [x1, y1] = p(a1);
  return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1} Z`;
}
function pastel(partes, { cx, cy, r }) {
  const g = h('g'); const paths = partes.map(([f, col]) => { const p = h('path', { fill: col, stroke: V('card'), 'stroke-width': 2, d: '' }); g.appendChild(p); return [p, f]; });
  animar(620, (k) => { let a = 0; for (const [p, f] of paths) { const a1 = a + 360 * f * k; p.setAttribute('d', f * k > 0.003 ? sectorPath(cx, cy, r, a, Math.min(a1, a + 359.9)) : ''); a += 360 * f * k; } });
  return g;
}
function svgBase(w, hh, ...hijos) { return h('svg', { viewBox: `0 0 ${w} ${hh}`, role: 'img' }, hijos); }
/* Grafica a tamaño real: se dibuja con el ancho que tiene su contenedor (texto nítido, sin escalar) y se redibuja si cambia. */
function adaptable(dibujar, W0 = 340) {
  const cont = h('div', { class: 'grafico' }); let ultimo = 0, primera = true;
  const pintar = (w) => { w = Math.round(w); if (w < 80 || Math.abs(w - ultimo) < 8) return; ultimo = w; vaciar(cont).appendChild(dibujar(w)); };
  if (typeof ResizeObserver === 'function') new ResizeObserver((es) => pintar(es[0].contentRect.width)).observe(cont); else pintar(W0);
  return cont;
}

/* ---- partes de la meta: recibido / proyectado / falta ---- */
function partesMeta(neto, proy, meta) {
  if (!(meta > 0)) return null;
  const rec = Math.min(neto, meta), pro = Math.max(Math.min(proy, meta - rec), 0);
  return [[rec / meta, V('azul')], [pro / meta, V('azul-claro')], [Math.max(meta - rec - pro, 0) / meta, V('corinto')]];
}

/* ---- columnas por semana ---- */
function graficoSemanas(sem, destacada, metaSem, etq) { return adaptable((W) => semanasSvg(W, sem, destacada, metaSem, etq)); }
function semanasSvg(W, sem, destacada, metaSem, etq) {
  const n = sem.length; if (!n) return h('svg');
  const Hh = 84, zona = 62, base = 66;
  const mx = Math.max(...sem.map((s) => s[0] + s[1]), metaSem, 1) * 1.12, cw = W / n, bw = Math.min(cw * 0.46, 30);
  const g = h('g');
  sem.forEach(([neto, proy], i) => {
    const gx = i * cw, bx = gx + (cw - bw) / 2, th = zona * (neto + proy) / mx, nh = zona * neto / mx;
    if (destacada === i + 1) g.appendChild(h('rect', { x: gx + 3, y: 0, width: cw - 6, height: Hh - 2, rx: 10, fill: V('azul-palido') }));
    const rect = (alto, col, rx) => { const r = h('rect', { x: bx, y: base, width: bw, height: 0, rx: Math.min(rx, bw / 2), fill: col, style: { transition: `y 520ms cubic-bezier(.22,.7,.2,1) ${i * 40}ms, height 520ms cubic-bezier(.22,.7,.2,1) ${i * 40}ms` } });
      if (alto > 1) sigFrame(() => { r.setAttribute('y', base - alto); r.setAttribute('height', alto); }); return r; };
    const total = rect(th, V('azul-claro'), 5), neta = rect(nh, V('azul'), 5);
    g.append(total, neta);
    const t = h('text', { x: gx + cw / 2, y: base + 15, 'text-anchor': 'middle', style: { fontSize: '10.5px', fill: destacada === i + 1 ? 'var(--azul)' : 'var(--muted)', fontWeight: destacada === i + 1 ? 700 : 400 } }, etq ? etq[i] : 'S' + (i + 1));
    g.appendChild(t);
    const area = h('rect', { x: gx, y: 0, width: cw, height: Hh, fill: 'transparent' });
    tip(area, () => `${etq ? etq[i] : 'Semana ' + (i + 1)} · Recibido ${fm0(neto)} · Proyectado ${fm0(proy)}`); g.appendChild(area);
  });
  if (metaSem > 0) g.appendChild(h('line', { x1: 0, x2: W, y1: base - zona * metaSem / mx, y2: base - zona * metaSem / mx, stroke: V('ink'), 'stroke-dasharray': '4 3', 'stroke-width': 1, opacity: .7 }));
  return svgBase(W, Hh, g);
}

/* ---- acumulada por semana ---- */
function graficoAcumulada(sem, meta, destacada, etq) { return adaptable((W) => acumuladaSvg(W, sem, meta, destacada, etq)); }
function acumuladaSvg(W, sem, meta, destacada, etq) {
  const n = sem.length; if (!n) return h('svg');
  const Hh = 118, base = 96, alto = 78, x0 = 10, ancho = W - 20;
  const cn = [0], ct = [0]; sem.forEach(([a, b]) => { cn.push(cn.at(-1) + a); ct.push(ct.at(-1) + a + b); });
  const ultima = Math.max(0, ...sem.map(([a, b], i) => (a + b > 0 ? i + 1 : 0)));
  const mx = Math.max(meta, ct[ultima], 1) * 1.12, px = (k) => x0 + ancho * k / n, py = (v) => base - alto * v / mx;
  const g = h('g');
  g.appendChild(h('line', { x1: 0, x2: W, y1: base, y2: base, stroke: V('borde') }));
  for (let k = 1; k <= n; k++) g.appendChild(h('text', { x: px(k), y: base + 14, 'text-anchor': 'middle', style: { fontSize: '10.5px', fill: destacada === k ? 'var(--azul)' : 'var(--muted)' } }, etq ? etq[k - 1] : 'S' + k));
  if (meta > 0) { g.appendChild(h('line', { x1: px(0), y1: base, x2: px(n), y2: py(meta), stroke: V('corinto'), 'stroke-width': 2, 'stroke-dasharray': '4 3' }));
    g.appendChild(h('text', { x: px(n), y: py(meta) - 6, 'text-anchor': 'end', style: { fill: 'var(--corinto)', fontSize: '10.5px' } }, 'Meta ' + fm0(meta))); }
  const linea = (vals, col) => { const pts = Array.from({ length: ultima + 1 }, (_, k) => `${px(k)},${py(vals[k])}`).join(' ');
    const p = h('polyline', { points: pts, fill: 'none', stroke: col, 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 1, style: { transition: 'stroke-dashoffset 700ms cubic-bezier(.22,.7,.2,1)' } });
    sigFrame(() => p.setAttribute('stroke-dashoffset', 0)); return p; };
  if (ultima >= 1) {
    g.append(linea(ct, V('azul-claro')), linea(cn, V('azul')));
    for (let k = 1; k <= ultima; k++) { const c = h('circle', { cx: px(k), cy: py(cn[k]), r: 3.6, fill: V('card'), stroke: V('azul'), 'stroke-width': 2 }); tip(c, () => `${etq ? etq[k - 1] : 'Semana ' + k} · acumulado ${fm0(cn[k])}`); g.appendChild(c); }
    g.appendChild(h('text', { x: Math.min(Math.max(px(ultima), 30), W - 30), y: Math.min(py(cn[ultima]) + 17, base - 6), 'text-anchor': 'middle', style: { fill: 'var(--azul)', fontWeight: 700, fontSize: '11.5px', paintOrder: 'stroke', stroke: 'var(--card)', strokeWidth: '3px' } }, fm0(cn[ultima])));
  }
  return svgBase(W, Hh, g);
}

/* ---- bloque de ritmo: estimado / real / faltante o de mas ---- */
function bloqueRitmo(esp, neto, espMonto, meta, grande) {
  const real = meta > 0 ? neto / meta : 0, pe = esp * 100, pr = real * 100, atras = pr < pe - 1e-9, dif = Math.abs(pr - pe);
  const col = (l, v, c, m) => h('div', null, h('div', { class: 'l' }, l), h('div', { class: 'n', style: { color: c } }, v), h('div', { class: 'm' }, m));
  const barra = h('div', { class: 'barra-ritmo' }); const relleno = [];
  if (atras) { const f = h('i', { style: { background: V('corinto-med') } }); barra.appendChild(f); relleno.push([f, Math.min(esp, 1)]); }
  const fr = h('i', { style: { background: V('azul') } }); barra.appendChild(fr); relleno.push([fr, Math.min(real, 1)]);
  const marca = h('div', { class: 'marca-r', style: { left: '0%' } }); if (esp > 0 && esp < 1) barra.appendChild(marca);
  sigFrame(() => { relleno.forEach(([e, f]) => (e.style.width = (f * 100) + '%')); marca.style.left = `calc(${esp * 100}% - 1.5px)`; });
  return h('div', null, h('div', { class: 'ritmo' + (grande ? ' grande' : '') },
    col('Estimado', Math.round(pe) + '%', V('ink'), fm0(espMonto)), col('Real', Math.round(pr) + '%', V('azul'), fm0(neto)),
    col(atras ? 'Faltante' : 'De más', Math.round(dif) + '%', atras ? V('corinto') : V('azul-med'), fm0(Math.abs(neto - espMonto)))), barra);
}

/* ---- tarjeta de vendedor ---- */
function statItem(lab, val, marca, color) {
  return h('div', { class: 'stat' }, h('i', { class: 'punto', style: { background: marca } }), h('span', { class: 'l' }, lab), h('div', { class: 'n', style: { color: color || 'inherit' } }, val));
}
function statsVendedor(c, meta) {
  const falta = meta - c.neto;
  const tercera = meta <= 0 ? ['Falta', '—', V('track'), V('muted')] : falta > 0 ? ['Falta', fm0(falta), V('corinto'), V('corinto')] : ['Superó por', fm0(-falta), V('azul-med'), V('azul-med')];
  return [['Recibido', fm0(c.neto), V('azul'), V('ink')], ['Proyectado', fm0(c.proy), V('azul-claro'), V('ink')], tercera];
}
function tarjetaVendedor(f, semanas, o, i) {
  const col = colorVend(f.ci), meta = f.meta, tipo = o.tipo;
  const fn = meta > 0 ? Math.min(f.neto / meta, 1) : 0, fp = meta > 0 ? Math.min((f.neto + f.proy) / meta, 1) : 0, esp = meta > 0 ? o.esp : null;
  const arr = f.arrastre || 0;
  const cab = h('div', { class: 'cab-v' }, h('i', { class: 'punto', style: { background: col.s, width: '11px', height: '11px' } }), h('b', null, f.nombre),
    h('span', { class: 'muted num' }, meta > 0 ? 'Meta ' + fm0(meta) + (Math.abs(arr) >= 0.5 ? ` (${arr > 0 ? '+' : '−'}${fm0(Math.abs(arr))})` : '') : 'Sin meta'));
  const stats = statsVendedor(f, meta), partes = partesMeta(f.neto, f.proy, meta);
  let cuerpo;
  if (['anillo', 'dona', 'pastel'].includes(tipo)) {
    const cx = 62, cy = 62, r = 46, gw = 13; const g = h('g');
    if (tipo === 'anillo') { g.append(pista(cx, cy, r, gw)); if (fp > 0.003) g.append(circulo(cx, cy, r, gw, V('azul-claro'), fp, 0, { redondo: true })); if (fn > 0.003) g.append(circulo(cx, cy, r, gw, V('azul'), fn, 0, { redondo: true, retraso: 80 })); if (esp && esp > 0 && esp < 1) g.append(marcaEsperado(cx, cy, r, gw, esp, V('corinto'))); }
    else if (tipo === 'dona') { if (partes) { g.append(dona(partes, { cx, cy, r, ancho: gw, hueco: 2 })); if (esp && esp > 0 && esp < 1) g.append(marcaEsperado(cx, cy, r, gw, esp, V('ink'))); } else g.append(pista(cx, cy, r, gw)); }
    else { if (partes) g.append(pastel(partes, { cx, cy, r: r + 6 })); else g.append(h('circle', { cx, cy, r, fill: V('track') })); }
    const centro = tipo === 'pastel' ? null : [h('text', { x: cx, y: cy + 2, 'text-anchor': 'middle', style: { fontSize: '19px', fontWeight: 700, fill: 'var(--azul)' } }, pct0(f.neto, meta)), h('text', { x: cx, y: cy + 18, 'text-anchor': 'middle', style: { fontSize: '10px' } }, 'de la meta')];
    cuerpo = h('div', { class: 'vcuerpo' }, h('div', { class: 'grafico', style: { width: '124px', flex: 'none' } }, svgBase(124, 124, g, centro)),
      h('div', { class: 'stats' }, stats.map(([l, v, m, c]) => statItem(l, v, m, c))));
  } else {
    let sup;
    if (tipo === 'barra') {
      const fila = h('div', { class: 'barra-ritmo', style: { height: '16px', margin: '8px 0 10px' } }); const a = h('i', { style: { background: V('azul-claro') } }), b = h('i', { style: { background: V('azul') } }); fila.append(a, b);
      const m = h('div', { class: 'marca-r', style: { left: '0%', height: '26px', top: '-5px', background: V('corinto') } }); if (esp && esp > 0 && esp < 1) fila.append(m);
      sigFrame(() => { a.style.width = fp * 100 + '%'; b.style.width = fn * 100 + '%'; m.style.left = `calc(${(esp || 0) * 100}% - 1.5px)`; });
      sup = h('div', null, h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' } }, h('b', { class: 'azul-t', style: { fontSize: '26px', letterSpacing: '-.02em' } }, pct0(f.neto, meta)), h('span', { class: 'muted' }, 'de la meta')), fila);
    } else sup = graficoAcumulada(semanas, o.metaMes ?? meta, o.destacada, o.etq);
    cuerpo = h('div', null, sup, h('div', { class: 'stats-fila' }, stats.map(([l, v, m, c]) => statItem(l, v, m, c))));
  }
  return h('div', { class: 'card alza vcard', style: { '--i': i } }, cab, cuerpo,
    meta > 0 && esp !== null && esp !== undefined ? bloqueRitmo(esp, f.neto, f.esp_monto || 0, meta, false) : null,
    h('div', { class: 'semanas' }, h('div', { class: 't' }, 'Por semana'), graficoSemanas(semanas, o.destacada, f.meta_sem, o.etq)));
}

/* ---- embudo ---- */
function filaEmbudo(lab, cant, monto, col, ancho, centrar, texto, extra) {
  const b = h('div', { class: 'emb-barra' + (centrar ? '' : ' izq'), style: { background: col, color: texto, width: Math.max(ancho, 0) + '%', minWidth: ancho > 0 ? '118px' : '0' } }, ancho > 0 ? `${cant} · ${fm0(monto)}` : '');
  return h('div', { class: 'emb-fila' }, h('div', { class: 'l' }, h('span', null, lab), extra || null), ancho > 0 ? b : h('div', { class: 'muted', style: { marginTop: '4px' } }, '—'));
}
function graficoEmbudo(e, porMonto, tipo) {
  const idx = porMonto ? 1 : 0;
  const etapas = [['Ingresadas', e.ingresadas, 'var(--azul)', '#fff'], ['En juego (activas + exitosas)', e.en_juego, 'var(--azul-med)', '#fff'], ['Exitosas', e.exitosas, 'var(--azul-claro)', 'var(--ink)']];
  const perd = e.perdidas;
  if (tipo === 'dona' || tipo === 'pastel') {
    const exi = e.exitosas, act = [e.en_juego[0] - exi[0], e.en_juego[1] - exi[1]];
    const est = [['Exitosas', exi, V('azul')], ['Activas', act, V('azul-claro')], ['Perdidas', perd, V('corinto')]];
    const total = est.reduce((s, x) => s + x[1][idx], 0);
    if (total <= 0) return h('div', { class: 'vacio' }, 'Sin datos');
    const partes = est.map((x) => [x[1][idx] / total, x[2]]);
    const g = h('g'); if (tipo === 'pastel') g.append(pastel(partes, { cx: 84, cy: 84, r: 72 })); else g.append(dona(partes, { cx: 84, cy: 84, r: 62, ancho: 24 }));
    const centro = tipo === 'pastel' ? null : [h('text', { x: 84, y: 84, 'text-anchor': 'middle', style: { fontWeight: 700, fontSize: '17px', fill: 'var(--ink)' } }, porMonto ? fm0(total) : String(total)), h('text', { x: 84, y: 101, 'text-anchor': 'middle', style: { fontSize: '10.5px' } }, 'ingresadas')];
    return h('div', { class: 'vcuerpo', style: { alignItems: 'center' } }, h('div', { class: 'grafico', style: { width: '168px', flex: 'none' } }, svgBase(168, 168, g, centro)),
      h('div', { class: 'stats', style: { gap: '14px' } }, est.map(([n, [c, m], col]) => h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px' } },
        h('i', { style: { width: '6px', height: '40px', borderRadius: '3px', background: col } }), h('div', { style: { flex: 1 } }, h('div', { class: 'muted', style: { fontSize: '12.5px' } }, n), h('b', null, `${c} · ${fm0(m)}`)),
        h('b', { style: { color: col, fontSize: '17px' } }, pct0(porMonto ? m : c, total))))));
  }
  const vmax = Math.max(...etapas.map((x) => x[1][idx]), perd[idx], 1);
  if (tipo === 'barras') {
    return h('div', null, [...etapas, ['Perdidas', perd, 'var(--corinto)', '#fff']].map(([n, [c, m], col, tx]) => filaEmbudo(n, c, m, col, (porMonto ? m : c) / vmax * 100, false, tx)));
  }
  const v0 = Math.max(etapas[0][1][idx], 1);
  return h('div', null, etapas.map(([n, [c, m], col, tx], i) => { const v = porMonto ? m : c; const ant = i > 0 ? (porMonto ? etapas[i - 1][1][1] : etapas[i - 1][1][0]) : 0;
    return filaEmbudo(n, c, m, col, v > 0 ? Math.max(v / v0 * 100, 0) : 0, true, tx, i > 0 && ant > 0 ? h('b', { class: 'azulmed-t' }, '▼ ' + pct0(v, ant)) : null); }),
    filaEmbudo('Perdidas', perd[0], perd[1], 'var(--corinto)', perd[idx] > 0 ? perd[idx] / vmax * 100 : 0, false, '#fff'));
}

/* ---- campañas ---- */
const colorDona = (i) => ['var(--corinto)', 'var(--azul)', 'var(--azul-med)', 'var(--azul-claro)', 'var(--corinto-med)', 'var(--muted)'][Math.min(i, 5)];
function rankingBarras(rank) {
  rank = rank.slice(0, 10);
  if (!rank.length) return h('div', { class: 'vacio' }, 'Sin proyecciones en esta vista');
  const vmax = Math.max(...rank.map((e) => e.neto + e.proy), 1);
  return h('div', null, rank.map((e, i) => { const lider = i === 0 && e.neto > 0;
    return h('div', { class: 'rank-fila', style: { animation: 'entra 280ms both', animationDelay: i * 30 + 'ms' } }, h('div', { class: 'rank-n' + (lider ? ' l' : '') }, i + 1),
      h('div', { class: 'rank-nom', style: { fontWeight: lider ? 700 : 400 }, title: e.campana }, e.campana),
      h('div', { class: 'pista' }, h('i', { style: { width: (e.neto + e.proy) / vmax * 100 + '%', background: V('azul-claro'), animationDelay: i * 30 + 'ms' } }), h('b', { style: { width: e.neto / vmax * 100 + '%', background: lider ? V('corinto') : V('azul'), animationDelay: i * 30 + 'ms' } })),
      h('div', { style: { textAlign: 'right' } }, h('b', { style: { color: lider ? 'var(--corinto)' : 'var(--azul)' }, class: 'num' }, fm0(e.neto)), h('div', { class: 'muted', style: { fontSize: '11.5px' } }, e.n_neto + ' ventas'))); }));
}
function rankingPareto(rank, totalNeto) {
  rank = rank.slice(0, 8);
  if (!rank.length) return h('div', { class: 'vacio' }, 'Sin proyecciones en esta vista');
  return adaptable((W) => paretoSvg(W, rank, totalNeto), 640);
}
function paretoSvg(W, rank, totalNeto) {
  const n = rank.length, Hh = 330, base = 270, alto = 230, x0 = 10, ancho = W - 56, vmax = Math.max(...rank.map((e) => e.neto + e.proy), 1);
  const ref = rank.map((e) => (totalNeto > 0 ? e.neto : e.proy)), refT = ref.reduce((a, b) => a + b, 0) || 1, bw = Math.min(ancho / n * 0.56, 62);
  const g = h('g'); g.appendChild(h('line', { x1: 0, x2: W, y1: base, y2: base, stroke: V('borde') }));
  const pts = []; let cum = 0;
  rank.forEach((e, i) => { const cx = x0 + ancho * (i + .5) / n, lider = i === 0 && e.neto > 0;
    const col = (alto2, c) => { const r = h('rect', { x: cx - bw / 2, y: base, width: bw, height: 0, rx: 7, fill: c, style: { transition: `y 560ms cubic-bezier(.22,.7,.2,1) ${i * 40}ms, height 560ms cubic-bezier(.22,.7,.2,1) ${i * 40}ms` } }); if (alto2 > 1) sigFrame(() => { r.setAttribute('y', base - alto2); r.setAttribute('height', alto2); }); return r; };
    g.append(col(alto * (e.neto + e.proy) / vmax, V('azul-claro')), col(alto * e.neto / vmax, lider ? V('corinto') : V('azul')));
    const maxc = Math.max(6, Math.floor(ancho / n / 7)); const nom = e.campana.length > maxc ? e.campana.slice(0, maxc - 1) + '…' : e.campana;
    g.append(h('text', { x: cx, y: base + 17, 'text-anchor': 'middle', style: { fill: 'var(--ink)', fontSize: '11px' } }, nom), h('text', { x: cx, y: base + 32, 'text-anchor': 'middle', style: { fill: lider ? 'var(--corinto)' : 'var(--azul)', fontSize: '11px', fontWeight: 600 } }, fm0(e.neto)));
    cum += ref[i]; pts.push([cx, base - alto * cum / refT]); });
  if (n >= 2) { const p = h('polyline', { points: pts.map((p) => p.join(',')).join(' '), fill: 'none', stroke: V('corinto-med'), 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 1, style: { transition: 'stroke-dashoffset 700ms cubic-bezier(.22,.7,.2,1) 200ms' } }); g.appendChild(p); sigFrame(() => p.setAttribute('stroke-dashoffset', 0)); }
  let acu = 0; pts.forEach(([x, y], i) => { acu += ref[i]; g.append(h('circle', { cx: x, cy: y, r: 4.5, fill: V('card'), stroke: V('corinto-med'), 'stroke-width': 2 }), h('text', { x, y: y - 11, 'text-anchor': 'middle', style: { fill: 'var(--corinto)', fontSize: '10.5px', fontWeight: 600, paintOrder: 'stroke', stroke: 'var(--card)', strokeWidth: '3px' } }, pct0(acu, refT))); });
  g.append(h('text', { x: W - 2, y: base - alto, 'text-anchor': 'end', style: { fill: 'var(--corinto)', fontSize: '10.5px' } }, '100%'), h('text', { x: W - 2, y: base, 'text-anchor': 'end', style: { fill: 'var(--corinto)', fontSize: '10.5px' } }, '0%'));
  return svgBase(W, Hh, g);
}
function donaCampanas(rank, totalNeto, tipo) {
  if (totalNeto <= 0) return h('div', { class: 'vacio' }, 'Sin ventas');
  let partes = rank.slice(0, 5).map((e) => [e.campana, e.neto]); if (rank.length > 5) partes.push(['Otras', rank.slice(5).reduce((s, e) => s + e.neto, 0)]);
  partes = partes.filter((p) => p[1] > 0);
  const g = h('g'), seg = partes.map(([, v], i) => [v / totalNeto, colorDona(i)]);
  if (tipo === 'pastel') g.append(pastel(seg, { cx: 100, cy: 100, r: 88 })); else g.append(dona(seg, { cx: 100, cy: 100, r: 76, ancho: 24 }));
  const centro = tipo === 'pastel' ? null : [h('text', { x: 100, y: 100, 'text-anchor': 'middle', style: { fontWeight: 700, fontSize: '18px', fill: 'var(--ink)' } }, fm0(totalNeto)), h('text', { x: 100, y: 118, 'text-anchor': 'middle', style: { fontSize: '10.5px' } }, 'recibido')];
  return h('div', null, h('div', { class: 'grafico', style: { width: '200px', margin: '4px auto 0' } }, svgBase(200, 200, g, centro)),
    h('div', { class: 'leyenda' }, partes.map(([n, v], i) => h('div', null, h('i', { class: 'punto', style: { background: colorDona(i) } }), h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, title: n }, n), h('b', null, pct0(v, totalNeto))))));
}

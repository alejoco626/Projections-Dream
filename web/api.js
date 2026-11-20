/* Llamadas al programa (Python). En la ventana real usa pywebview; en el servidor de pruebas, fetch. */
const API = (() => {
  let lista = null;
  function esperar() {
    if (lista) return lista;
    lista = new Promise(async (ok) => {
      // Servidor de desarrollo: responde en /__dev. En la ventana real (pywebview) no existe.
      try { const r = await fetch('/__dev', { cache: 'no-store' }); if (r.ok && (await r.text()) === 'dev') return ok(false); } catch (e) {}
      const listo = () => window.pywebview && window.pywebview.api && Object.keys(window.pywebview.api).length > 0;
      if (listo()) return ok(true);
      window.addEventListener('pywebviewready', () => ok(true), { once: true });
      const t0 = Date.now();
      const iv = setInterval(() => { if (listo()) { clearInterval(iv); ok(true); } else if (Date.now() - t0 > 15000) { clearInterval(iv); ok(true); } }, 40);
    });
    return lista;
  }
  async function llamar(metodo, args) {
    const real = await esperar();
    try {
      if (real) return await window.pywebview.api[metodo](...args);
      const r = await fetch('/__api/' + metodo, { method: 'POST', body: JSON.stringify(args) });
      return await r.json();
    } catch (e) {
      return { error: 'No se pudo comunicar con el programa: ' + e };
    }
  }
  return new Proxy({}, { get: (_, m) => (...a) => llamar(m, a) });
})();

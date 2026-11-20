/* Llamadas al programa (Python). En la ventana real usa pywebview; en el servidor de pruebas, fetch. */
const API = (() => {
  let lista = null;
  function esperar() {
    if (lista) return lista;
    lista = new Promise((ok) => {
      if (window.pywebview && window.pywebview.api) return ok(true);
      if (location.protocol === 'file:' || window.pywebview) {
        window.addEventListener('pywebviewready', () => ok(true), { once: true });
        return;
      }
      ok(false);
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

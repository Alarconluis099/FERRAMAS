// Catalog & filters JS extracted from template
(function () {
    function $(sel, root = document) { return root.querySelector(sel); }
    function $all(sel, root = document) { return [...root.querySelectorAll(sel)]; }
    function formatCL(v) { return '$' + Number(v).toLocaleString('es-CL'); }
    const catalogRoot = $('#catalog-root');
    if (!catalogRoot) return;
    const API_TOOLS = catalogRoot.dataset.apiTools;
    const API_ADD = catalogRoot.dataset.apiAdd;
    const grid = $('#productos-grid');
    let total = parseInt(grid?.dataset.total || '0', 10);
    let perPage = parseInt(grid?.dataset.perPage || '12', 10);
    let page = 1;
    const perPageSelect = $('#per-page-select');
    const btnPrev = $('#btn-prev');
    const btnNext = $('#btn-next');
    const pageIndicator = $('#page-indicator');
    const rangeInfo = $('#range-info');
    const activeFiltersBox = $('#active-filters');
    // Filtros
    const fQ = $('#f-q');
    const fPMin = $('#f-precio-min');
    const fPMax = $('#f-precio-max');
    const fOrder = $('#f-order');
    let currentFilters = { q: null, precio_min: null, precio_max: null, order: null };
    // Slider
    const priceRangeContainer = $('#price-range-container');
    const rMin = $('#price-min-range');
    const rMax = $('#price-max-range');
    const bubbleMin = $('#price-bubble-min');
    const bubbleMax = $('#price-bubble-max');
    function updateDual() {
        if (+rMin.value > +rMax.value) { const t = rMin.value; rMin.value = rMax.value; rMax.value = t; }
        const min = parseInt(rMin.min, 10), max = parseInt(rMin.max, 10);
        const a = ((rMin.value - min) / (max - min)) * 100; const b = ((rMax.value - min) / (max - min)) * 100;
        priceRangeContainer.style.setProperty('--a', a + '%'); priceRangeContainer.style.setProperty('--b', b + '%');
        bubbleMin.textContent = formatCL(rMin.value); bubbleMax.textContent = formatCL(rMax.value);
        bubbleMin.style.left = `calc(6px + ${a}% * (100% - 12px))`; bubbleMax.style.left = `calc(6px + ${b}% * (100% - 12px))`;
        fPMin.value = rMin.value; fPMax.value = rMax.value;
        bubbleMin.setAttribute('aria-valuenow', rMin.value); bubbleMax.setAttribute('aria-valuenow', rMax.value);
    }
    function showBubble(b) { b.classList.add('show'); clearTimeout(b._t); b._t = setTimeout(() => b.classList.remove('show'), 1000); }
    function bindSlider() { ['input', 'change'].forEach(ev => { rMin.addEventListener(ev, () => { updateDual(); showBubble(bubbleMin); triggerPriceDebounced(); }); rMax.addEventListener(ev, () => { updateDual(); showBubble(bubbleMax); triggerPriceDebounced(); }); }); updateDual(); }

    function debounce(fn, delay = 400) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), delay); }; }
    const triggerFilterDebounced = debounce(() => { setFiltersFromInputs(); loadPage(1, perPage).catch(console.warn); }, 400);
    const triggerPriceDebounced = debounce(() => { setFiltersFromInputs(); loadPage(1, perPage).catch(console.warn); }, 300);

    function setFiltersFromInputs() { currentFilters.q = fQ.value.trim() || null; currentFilters.precio_min = fPMin.value ? parseInt(fPMin.value, 10) : null; currentFilters.precio_max = fPMax.value ? parseInt(fPMax.value, 10) : null; currentFilters.order = fOrder.value || null; renderFilterChips(); }

    function renderFilterChips() {
        if (!activeFiltersBox) return; const chips = []; if (currentFilters.q) chips.push({ k: 'q', label: `Texto: "${currentFilters.q}"` }); if (currentFilters.precio_min != null || currentFilters.precio_max != null) { chips.push({ k: 'precio', label: `Precio ${currentFilters.precio_min ? formatCL(currentFilters.precio_min) : formatCL(0)} – ${currentFilters.precio_max ? formatCL(currentFilters.precio_max) : formatCL(rMax.max)}` }); } if (currentFilters.order) chips.push({ k: 'order', label: `Orden: ${currentFilters.order.replace('_', ' ')}` }); activeFiltersBox.innerHTML = chips.map(c => `<button type="button" class="af-chip" data-k="${c.k}">${c.label}<span aria-hidden="true">×</span></button>`).join(''); if (!chips.length) { activeFiltersBox.innerHTML = ''; }
        activeFiltersBox.querySelectorAll('.af-chip').forEach(btn => btn.addEventListener('click', () => { const k = btn.dataset.k; if (k === 'q') { fQ.value = ''; } else if (k === 'precio') { rMin.value = rMin.min; rMax.value = rMax.max; updateDual(); } else if (k === 'order') { fOrder.value = ''; } setFiltersFromInputs(); loadPage(1, perPage).catch(console.warn); }));
    }

    async function loadPage(newPage, newPerPage) { const usp = new URLSearchParams(); const p = { page: newPage, per_page: newPerPage, ...currentFilters }; Object.entries(p).forEach(([k, v]) => { if (v !== null && v !== '' && v !== undefined) usp.append(k, v); }); const resp = await fetch(`${API_TOOLS}?${usp.toString()}`); const data = await resp.json(); if (!data.ok) throw new Error('API'); grid.innerHTML = ''; const STATIC_BASE = document.querySelector('link[rel="icon"]') ? '' : ''; data.items.forEach(tool => { const div = document.createElement('div'); div.className = 'producto'; div.setAttribute('data-tool-id', tool.id_tool); const fallback = 'Imagenes/Marcas/220px-Stanley_Hand_Tools_logo.png'; const lower = (tool.name || '').toLowerCase(); let inferred = fallback; if (/martillo/.test(lower)) inferred = 'Imagenes/Herramientas manuales/martillo.png'; else if (/destorn/.test(lower)) inferred = 'Imagenes/Herramientas manuales/destornillador.png'; else if (/taladro/.test(lower)) inferred = 'Imagenes/Herramientas manuales/taladro.png'; else if (/sierra/.test(lower)) inferred = 'Imagenes/Herramientas manuales/sierra.png'; else if (/nivel|laser/.test(lower)) inferred = 'Imagenes/Equipos de medicion/laser.png'; else if (/casco/.test(lower)) inferred = 'Imagenes/Equipos de seguridad/casco.png'; else if (/guante/.test(lower)) inferred = 'Imagenes/Equipos de seguridad/guantes.png'; else if (/lente/.test(lower)) inferred = 'Imagenes/Equipos de seguridad/lentes.png'; div.innerHTML = `<img src='/static/${inferred}' alt='${tool.name}' onerror="this.onerror=null;this.src='/static/${fallback}'"><h3 title='${tool.name}'>${tool.name}</h3><p>${tool.description || 'Sin descripción'}</p><div class='precio'>$ ${tool.precio}</div>${(tool.stock === null || tool.stock > 0) ? `<form method='POST' action='#' class='add-form'><input type='hidden' name='product_id' value='${tool.id_tool}'><input type='number' name='cantidad' value='1' min='1' class='form-control form-control-sm mb-1 qty-input'><button type='submit' class='btn-add'>Añadir al carrito</button></form>` : `<div class='agotado'>Agotado</div>`}`; grid.appendChild(div); }); bindAddToCart(grid); if (typeof data.total !== 'undefined') total = data.total; page = data.page; perPage = data.per_page; const startIdx = (page - 1) * perPage + 1; const endIdx = Math.min(page * perPage, total); pageIndicator.textContent = `${startIdx}–${endIdx} de ${total}`; rangeInfo.innerHTML = `Mostrando <strong>${data.items.length}</strong> de <strong>${total}</strong> productos`; const fpCount = $('#fp-results-count'); if (fpCount) fpCount.textContent = `${total} resultados`; btnPrev.disabled = page <= 1; btnNext.disabled = !data.has_more; }

    function bindAddToCart(root = document) { const cartCountEl = $('#cart-count'); $all('.add-form', root).forEach(form => { if (form._b) return; form._b = 1; form.addEventListener('submit', e => { e.preventDefault(); const fd = new FormData(form); const payload = { product_id: fd.get('product_id'), cantidad: fd.get('cantidad') }; fetch(API_ADD, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then(r => r.json()).then(data => { if (data.ok) { if (cartCountEl) cartCountEl.textContent = data.cart_count; const btn = form.querySelector('button'); const old = btn.textContent; btn.textContent = 'Añadido'; btn.disabled = true; setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 900); } }).catch(() => alert('Error de red')); }); }); }

    // Collapse groups
    $all('[data-toggle-group]').forEach(btn => btn.addEventListener('click', () => { const grp = btn.closest('[data-group]'); if (grp) grp.classList.toggle('open'); }));
    // Events
    perPageSelect?.addEventListener('change', () => { perPage = parseInt(perPageSelect.value, 10) || 12; loadPage(1, perPage).catch(console.warn); });
    fQ?.addEventListener('input', triggerFilterDebounced);
    fOrder?.addEventListener('change', () => { setFiltersFromInputs(); loadPage(1, perPage).catch(console.warn); });
    const clearTop = $('#fp-clear-top'); if (clearTop) { clearTop.addEventListener('click', () => { if (fQ) fQ.value = ''; rMin.value = rMin.min; rMax.value = rMax.max; updateDual(); if (fOrder) fOrder.value = ''; setFiltersFromInputs(); loadPage(1, perPage).catch(console.warn); }); }
    btnPrev?.addEventListener('click', () => { if (page > 1) loadPage(page - 1, perPage).catch(console.warn); });
    btnNext?.addEventListener('click', () => { loadPage(page + 1, perPage).catch(console.warn); });
    setFiltersFromInputs();
    bindSlider();
    bindAddToCart();
})();

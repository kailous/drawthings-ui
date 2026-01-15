(() => {
    // --- I18n Module (保持不变) ---
    const I18n = {
        data: {}, lang: 'zh',
        async loadLang(lang) {
            const res = await fetch(`lang/${lang}.json`);
            if (!res.ok) return null;
            return res.json();
        },
        async init() {
            try {
                const primary = await this.loadLang(this.lang);
                this.data = primary || await this.loadLang('zh') || {};
                this.updatePage();
            } catch (e) {}
        },
        t(key, p={}) { let s=this.data[key]||key; for(let k in p) s=s.replace(`{${k}}`,p[k]); return s; },
        updatePage() {
            document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=this.t(e.dataset.i18n));
            document.querySelectorAll('[data-i18n-placeholder]').forEach(e=>e.placeholder=this.t(e.dataset.i18nPlaceholder));
            document.querySelectorAll('[data-i18n-title]').forEach(e=>e.title=this.t(e.dataset.i18nTitle));
        }
    };

    const CONFIG = { BATCH_SIZE: 40, PRELOAD_COUNT: 12, LAZY_MARGIN: '600px' };
    
    const state = {
        historyData: [],
        renderedCount: 0,
        isGenerating: false,
        imageElements: [],
        preloadCursor: 0,
        preloadPrimed: false
    };

    const $ = (id) => document.getElementById(id);
    const els = {
        payload: $('payload'),
        btnFormat: $('btn-format'),
        submitBtn: $('submit-btn'),
        btnText: $('btn-text'),
        resultsArea: $('results-area'),
        resultsGrid: $('results-grid'),
        historyGrid: $('history-grid'),
        historyCount: $('history-count'),
        historyEmpty: $('history-empty'),
        loaderTrigger: $('infinite-scroll-trigger'),
        toastBox: $('toast-container')
    };

    const toast = (key, type='normal', params={}) => {
        const msg = I18n.t(key, params);
        const el = document.createElement('div');
        el.className = `toast ${type==='error'?'!bg-red-600 !text-white':''}`;
        el.textContent = msg;
        els.toastBox.appendChild(el);
        setTimeout(() => { el.style.opacity='0'; el.style.transform='translateY(20px)'; setTimeout(()=>el.remove(),300); }, 2000);
    };

    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const img = entry.target;
            const src = img.dataset.src;
            if (!src) {
                imageObserver.unobserve(img);
                return;
            }
            img.src = src;
            img.removeAttribute('data-src');
            imageObserver.unobserve(img);
        });
    }, { rootMargin: CONFIG.LAZY_MARGIN });

    const handleImageDone = (img) => {
        img.classList.add('loaded');
        const index = parseInt(img.dataset.index || '', 10);
        if (!Number.isNaN(index)) maybePreloadNextBatch(index);
    };

    const forceLoadImage = (img) => {
        const src = img.dataset.src;
        if (!src) return;
        img.loading = 'eager';
        img.src = src;
        img.removeAttribute('data-src');
        imageObserver.unobserve(img);
    };

    const preloadRange = (start, count) => {
        const end = Math.min(start + count, state.historyData.length);
        for (let i = start; i < end; i += 1) {
            const img = state.imageElements[i];
            if (img) forceLoadImage(img);
        }
    };

    const maybePreloadNextBatch = (index) => {
        if (!state.historyData.length) return;
        const triggerOffset = CONFIG.PRELOAD_COUNT - 1;
        while (
            state.preloadCursor < state.historyData.length &&
            index >= state.preloadCursor - triggerOffset
        ) {
            preloadRange(state.preloadCursor, CONFIG.PRELOAD_COUNT);
            state.preloadCursor += CONFIG.PRELOAD_COUNT;
        }
    };

    // --- 实例化查看器 ---
    // 这里是改动最大的地方：直接使用新类
    const viewer = new ImageViewer({
        elements: {
            modal: $('image-modal'),
            img: $('modal-img'),
            close: $('modal-close'),
            prev: $('modal-prev'),
            next: $('modal-next')
        },
        config: {
            // 当到达第一张或最后一张时的回调
            onReachEdge: (dir) => {
                toast(dir > 0 ? 'msg_nav_last' : 'msg_nav_first');
            }
        }
    });

    // --- 业务逻辑 ---

    els.submitBtn.onclick = async () => {
        if (state.isGenerating) return;
        let payload;
        try { payload = JSON.parse(els.payload.value); } catch { return toast('msg_json_invalid', 'error'); }

        state.isGenerating = true;
        els.submitBtn.disabled = true;
        els.btnText.textContent = I18n.t('btn_generating');
        els.submitBtn.querySelector('.spinner').classList.remove('hidden');
        els.resultsArea.classList.add('hidden');
        els.resultsGrid.innerHTML = '';

        try {
            const res = await fetch('/generate', { method: 'POST', body: JSON.stringify(payload) });
            if(!res.ok) throw new Error();
            const data = await res.json();
            
            if (data.images?.length) {
                els.resultsArea.classList.remove('hidden');
                // 这里的图片是单次生成的，我们构建一个临时数组给 Viewer
                const tempItems = data.images.map(img => img.startsWith('data:') ? img : `data:image/png;base64,${img}`);
                
                tempItems.forEach((url, idx) => {
                    createImageCard(url, els.resultsGrid, () => {
                        // 打开查看器，传入临时数组
                        viewer.open(tempItems, idx);
                    });
                });
                toast('msg_gen_success', 'normal', {n: data.images.length});
                loadHistory(); 
            } else { toast('msg_gen_empty'); }
        } catch(e) { toast('msg_server_err', 'error'); } 
        finally {
            state.isGenerating = false;
            els.submitBtn.disabled = false;
            els.btnText.textContent = I18n.t('btn_generate');
            els.submitBtn.querySelector('.spinner').classList.add('hidden');
        }
    };

    els.btnFormat.onclick = () => {
        try {
            if(!els.payload.value.trim()) return toast('msg_input_empty');
            els.payload.value = JSON.stringify(JSON.parse(els.payload.value), null, 2);
            toast('msg_format_ok');
        } catch { toast('msg_json_invalid', 'error'); }
    };

    const loadHistory = async () => {
        try {
            const res = await fetch('/history');
            const data = await res.json();
            if (!data.enabled) return;
            state.historyData = data.items || [];
            els.historyCount.textContent = state.historyData.length;
            els.historyGrid.innerHTML = '';
            state.renderedCount = 0;
            state.imageElements = [];
            state.preloadPrimed = false;
            state.preloadCursor = Math.min(CONFIG.PRELOAD_COUNT, state.historyData.length);
            els.loaderTrigger.style.display = 'flex';
            
            if (state.historyData.length === 0) {
                els.historyEmpty.style.display = 'block';
                els.loaderTrigger.style.display = 'none';
            } else {
                els.historyEmpty.style.display = 'none';
                renderBatch();
            }
        } catch { toast('msg_hist_fail', 'error'); }
    };
    $('btn-reload-history').onclick = loadHistory;

    const createImageCard = (url, container, onClick, options = {}) => {
        const card = document.createElement('div');
        card.className = 'img-card';
        const img = document.createElement('img');
        img.decoding = 'async';
        const forceLoad = options.forceLoad === true;
        const index = Number.isFinite(options.index) ? options.index : null;
        if (url.startsWith('data:')) {
            img.src = url;
            img.classList.add('loaded');
        } else {
            img.dataset.src = url;
            img.loading = forceLoad ? 'eager' : 'lazy';
            if (index !== null) {
                img.dataset.index = String(index);
                state.imageElements[index] = img;
            }
            img.onload = () => handleImageDone(img);
            img.onerror = () => handleImageDone(img);
            if (forceLoad || (index !== null && index < state.preloadCursor)) {
                forceLoadImage(img);
            } else {
                imageObserver.observe(img);
            }
        }
        card.appendChild(img);
        card.onclick = onClick;
        container.appendChild(card);
    };

    const renderBatch = () => {
        if (state.renderedCount >= state.historyData.length) {
            els.loaderTrigger.style.display = 'none'; return;
        }
        const fragment = document.createDocumentFragment();
        const nextBatch = state.historyData.slice(state.renderedCount, state.renderedCount + CONFIG.BATCH_SIZE);
        nextBatch.forEach((item, idx) => {
            const globalIndex = state.renderedCount + idx;
            // 点击历史记录时，把完整的历史数据传给 Viewer
            createImageCard(
                item.url,
                fragment,
                () => viewer.open(state.historyData, globalIndex),
                { forceLoad: globalIndex < CONFIG.PRELOAD_COUNT, index: globalIndex }
            );
        });
        els.historyGrid.appendChild(fragment);
        state.renderedCount += nextBatch.length;
        if (!state.preloadPrimed && state.historyData.length > CONFIG.PRELOAD_COUNT) {
            preloadRange(CONFIG.PRELOAD_COUNT, CONFIG.PRELOAD_COUNT);
            state.preloadCursor = Math.min(CONFIG.PRELOAD_COUNT * 2, state.historyData.length);
            state.preloadPrimed = true;
        }
    };

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            setTimeout(() => {
                renderBatch();
                if(state.renderedCount < state.historyData.length) els.loaderTrigger.style.opacity = '0';
            }, 300);
            els.loaderTrigger.style.opacity = '1';
        }
    }, { rootMargin: '200px' });
    observer.observe(els.loaderTrigger);

    els.payload.addEventListener('focus', () => { if(els.payload.value.trim().length) els.payload.value=''; });

    (async () => {
        await I18n.init();
        loadHistory();
        try { const r = await fetch('/payload'); if(r.ok) els.payload.value=JSON.stringify(await r.json(),null,2); } catch{}
    })();
})();

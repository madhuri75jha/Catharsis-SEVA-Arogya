(function () {
    const MODAL_ID = 'pdf-language-picker-modal';

    function ensureModal() {
        let modal = document.getElementById(MODAL_ID);
        if (modal) {
            return modal;
        }

        modal = document.createElement('div');
        modal.id = MODAL_ID;
        modal.className = 'hidden fixed inset-0 z-[120] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div data-role="backdrop" class="absolute inset-0 bg-black/50"></div>
            <div class="relative w-full max-w-lg rounded-xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
                <h3 class="text-base font-semibold text-slate-900 dark:text-white">Select Language</h3>
                <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">English is the default language.</p>
                <input
                    data-role="search"
                    type="text"
                    placeholder="Search language..."
                    class="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-primary dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
                <div class="mt-3 max-h-64 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700">
                    <div data-role="list" class="divide-y divide-slate-100 dark:divide-slate-800"></div>
                </div>
                <div class="mt-4 flex gap-2">
                    <button data-role="cancel" class="flex-1 rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600">Cancel</button>
                    <button data-role="confirm" class="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90">Continue</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        return modal;
    }

    function renderList(listEl, languages, selectedCode) {
        if (!languages.length) {
            listEl.innerHTML = '<p class="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">No languages available</p>';
            return;
        }

        listEl.innerHTML = languages.map((language) => {
            const code = String(language.code || '').toLowerCase();
            const name = String(language.name || code);
            const selected = code === selectedCode ? 'bg-primary/10 text-primary' : 'text-slate-700 dark:text-slate-200';
            return `
                <button
                    type="button"
                    data-code="${code}"
                    class="w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800 ${selected}"
                >
                    <span class="font-medium">${name}</span>
                    <span class="ml-2 text-xs text-slate-500 dark:text-slate-400">(${code})</span>
                </button>
            `;
        }).join('');
    }

    window.showPrescriptionLanguagePicker = function (languages, defaultCode) {
        const sourceLanguages = Array.isArray(languages) ? languages : [];
        const normalizedDefault = String(defaultCode || 'en').toLowerCase();
        const modal = ensureModal();
        const backdrop = modal.querySelector('[data-role="backdrop"]');
        const search = modal.querySelector('[data-role="search"]');
        const list = modal.querySelector('[data-role="list"]');
        const cancel = modal.querySelector('[data-role="cancel"]');
        const confirm = modal.querySelector('[data-role="confirm"]');

        let selectedCode = normalizedDefault;
        let filtered = [...sourceLanguages];

        const close = (result) => {
            modal.classList.add('hidden');
            search.value = '';
            search.oninput = null;
            list.onclick = null;
            cancel.onclick = null;
            confirm.onclick = null;
            backdrop.onclick = null;
            resolve(result);
        };

        let resolve;
        const promise = new Promise((res) => {
            resolve = res;
        });

        const applyFilter = () => {
            const query = search.value.trim().toLowerCase();
            filtered = sourceLanguages.filter((language) => {
                const code = String(language.code || '').toLowerCase();
                const name = String(language.name || '').toLowerCase();
                return !query || code.includes(query) || name.includes(query);
            });
            renderList(list, filtered, selectedCode);
        };

        search.oninput = applyFilter;
        list.onclick = (event) => {
            const button = event.target.closest('button[data-code]');
            if (!button) return;
            selectedCode = button.dataset.code || normalizedDefault;
            renderList(list, filtered, selectedCode);
        };
        cancel.onclick = () => close(null);
        backdrop.onclick = () => close(null);
        confirm.onclick = () => {
            const selected = sourceLanguages.find((language) => String(language.code || '').toLowerCase() === selectedCode)
                || sourceLanguages.find((language) => String(language.code || '').toLowerCase() === 'en')
                || { code: 'en', name: 'English' };
            close({ code: String(selected.code || 'en').toLowerCase(), name: String(selected.name || 'English') });
        };

        modal.classList.remove('hidden');
        renderList(list, sourceLanguages, selectedCode);
        search.focus();

        return promise;
    };
})();


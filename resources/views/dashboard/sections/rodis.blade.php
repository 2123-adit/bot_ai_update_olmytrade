<div id="view-rodis" class="fade-in hidden">

    {{-- ═══════════════════════════════════════════════════════════
         HERO HEADER
    ═══════════════════════════════════════════════════════════ --}}
    <div class="bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-900 rounded-3xl p-6 md:p-8 shadow-2xl border border-indigo-500/30 mb-6 relative overflow-hidden text-white">
        {{-- Background decoration --}}
        <div class="absolute top-0 right-0 w-72 h-72 bg-indigo-500/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl pointer-events-none"></div>
        <div class="absolute bottom-0 left-16 w-40 h-40 bg-purple-500/10 rounded-full translate-y-1/2 blur-2xl pointer-events-none"></div>

        <div class="relative z-10">
            <div class="flex items-center gap-3 mb-2">
                <div class="w-10 h-10 rounded-2xl bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center text-xl">🤖</div>
                <div>
                    <h2 class="text-2xl md:text-3xl font-extrabold text-white leading-none">RODIS <span class="text-indigo-400">Auto</span></h2>
                    <p class="text-xs text-indigo-300 font-medium">Martingale + Compound Engine</p>
                </div>
            </div>
            <p class="text-indigo-200 max-w-2xl text-sm leading-relaxed mt-3">
                Bot akan otomatis memantau semua market, masuk posisi saat FALSE mencapai target, dan menerapkan
                strategi <b>Martingale (×2.2)</b> dengan saldo yang <b>Compound</b> setiap kemenangan.
            </p>
        </div>
    </div>

    {{-- ═══════════════════════════════════════════════════════════
         KONFIGURASI
    ═══════════════════════════════════════════════════════════ --}}
    <div class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm p-5 md:p-6 mb-5">
        <h3 class="text-xs font-extrabold text-gray-400 uppercase tracking-widest mb-4">⚙️ Konfigurasi RODIS Auto</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {{-- Modal Investasi --}}
            <div>
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">💵 Modal Investasi ($)</label>
                <input type="number" id="rodis-modal" value="19" min="1" step="0.01"
                    class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl font-extrabold text-xl text-dark dark:text-white outline-none text-center focus:border-indigo-400 transition-colors">
            </div>
            {{-- Target FALSE --}}
            <div>
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">🎯 Masuk Saat FALSE ke-</label>
                <input type="number" id="rodis-target-loss" value="9" min="1"
                    class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl font-extrabold text-xl text-dark dark:text-white outline-none text-center focus:border-indigo-400 transition-colors">
            </div>
            {{-- Stop Loss Harian --}}
            <div>
                <label class="block text-[10px] font-bold text-red-500 uppercase tracking-wider mb-1.5">🛑 Stop Loss Harian ($)</label>
                <input type="number" id="rodis-stop-loss" value="0" min="0" step="0.5"
                    class="w-full px-4 py-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-700 rounded-xl font-extrabold text-xl text-red-700 dark:text-red-300 outline-none text-center focus:border-red-400 transition-colors">
                <p class="text-[10px] text-gray-400 mt-1">0 = tidak aktif</p>
            </div>
            {{-- Pilih Akun --}}
            <div>
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">👤 Pilih Akun Trading</label>
                <select id="rodis-account-id"
                    class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl font-bold text-sm text-dark dark:text-white outline-none focus:border-indigo-400 transition-colors appearance-none">
                    <option value="">-- Muat dari Pusat Kendali --</option>
                </select>
                <p class="text-[10px] text-gray-400 mt-1">Cek akun di <b>Pusat Kendali</b> terlebih dahulu.</p>
            </div>
            {{-- Durasi + Sound Toggle --}}
            <div>
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">⏱️ Durasi Trade</label>
                <div class="w-full px-4 py-3 bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-700 rounded-xl font-extrabold text-xl text-indigo-600 dark:text-indigo-300 text-center">
                    60 Detik
                </div>
                <label class="flex items-center gap-2 mt-2 cursor-pointer select-none">
                    <input type="checkbox" id="rodis-sound-enabled" checked class="w-4 h-4 accent-indigo-500">
                    <span class="text-[10px] text-gray-500 font-bold">🔊 Sound Alert aktif</span>
                </label>
            </div>
        </div>


        {{-- Tombol START / STOP --}}
        <div class="mt-6 flex flex-col sm:flex-row gap-3 border-t border-gray-100 dark:border-gray-700 pt-5">
            <button onclick="startRodisAuto()" id="btn-rodis-start"
                class="flex-1 sm:flex-none px-8 py-3.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-extrabold text-base rounded-xl shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-all flex items-center justify-center gap-2">
                ▶ NYALAKAN RODIS AUTO
            </button>
            <button onclick="stopRodisAuto()" id="btn-rodis-stop"
                class="flex-1 sm:flex-none px-8 py-3.5 bg-red-500/10 hover:bg-red-500 text-red-600 hover:text-white border border-red-200 hover:border-red-500 font-extrabold text-base rounded-xl transition-all flex items-center justify-center gap-2 opacity-50 cursor-not-allowed"
                disabled>
                ⏹ STOP
            </button>
            <button onclick="loadRodisAccounts()" id="btn-rodis-load-acc"
                class="flex-1 sm:flex-none px-5 py-3.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 font-bold text-sm rounded-xl transition-all flex items-center justify-center gap-2">
                🔄 Muat Akun
            </button>
        </div>
    </div>

    {{-- ═══════════════════════════════════════════════════════════
         STATUS PANEL — Real-time
    ═══════════════════════════════════════════════════════════ --}}
    <div id="rodis-status-panel" class="mb-5">
        {{-- Status Badges --}}
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
            {{-- Status --}}
            <div class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700 p-4 text-center shadow-sm">
                <p class="text-[9px] font-extrabold text-gray-400 uppercase tracking-widest mb-1">Status</p>
                <p id="rodis-state-badge" class="text-sm font-black text-gray-400">IDLE</p>
            </div>
            {{-- Market Aktif --}}
            <div class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700 p-4 text-center shadow-sm col-span-2 sm:col-span-1">
                <p class="text-[9px] font-extrabold text-gray-400 uppercase tracking-widest mb-1">Market</p>
                <p id="rodis-current-market" class="text-xs font-extrabold text-indigo-500 truncate">-</p>
            </div>
            {{-- Step --}}
            <div class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700 p-4 text-center shadow-sm">
                <p class="text-[9px] font-extrabold text-gray-400 uppercase tracking-widest mb-1">Step</p>
                <p id="rodis-step-label" class="text-xs font-extrabold text-gray-700 dark:text-white">-</p>
            </div>
            {{-- Modal Saat Ini --}}
            <div class="bg-white dark:bg-gray-900 rounded-2xl border border-green-100 dark:border-green-900 p-4 text-center shadow-sm">
                <p class="text-[9px] font-extrabold text-gray-400 uppercase tracking-widest mb-1">Modal</p>
                <p id="rodis-modal-now" class="text-base font-black text-green-600">$0</p>
            </div>
            {{-- Total Profit --}}
            <div class="bg-white dark:bg-gray-900 rounded-2xl border border-blue-100 dark:border-blue-900 p-4 text-center shadow-sm">
                <p class="text-[9px] font-extrabold text-gray-400 uppercase tracking-widest mb-1">Total Profit</p>
                <p id="rodis-total-profit" class="text-base font-black text-blue-600">$0</p>
            </div>
            {{-- Win / Loss --}}
            <div class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700 p-4 text-center shadow-sm">
                <p class="text-[9px] font-extrabold text-gray-400 uppercase tracking-widest mb-1">W / L</p>
                <p class="text-base font-black">
                    <span id="rodis-total-win" class="text-green-600">0</span>
                    <span class="text-gray-300">/</span>
                    <span id="rodis-total-loss" class="text-red-500">0</span>
                </p>
            </div>
        </div>

        {{-- Bet Simulator Preview --}}
        <div id="rodis-bet-preview" class="bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-700 rounded-2xl p-4 mb-4 hidden">
            <p class="text-[10px] font-extrabold text-indigo-500 uppercase tracking-widest mb-2">🎲 Simulasi Bet (berdasarkan modal)</p>
            <div class="flex flex-wrap gap-2">
                <span class="bg-white dark:bg-indigo-950 px-3 py-1.5 rounded-lg text-xs font-bold text-dark dark:text-white border border-indigo-100 dark:border-indigo-700">Entry (F<span id="rodis-f-entry">10</span>): <span id="rodis-bet-s1" class="text-indigo-600">$-</span></span>
                <span class="bg-white dark:bg-indigo-950 px-3 py-1.5 rounded-lg text-xs font-bold text-dark dark:text-white border border-indigo-100 dark:border-indigo-700">Martingale F<span id="rodis-f-mg1">11</span>: <span id="rodis-bet-s2" class="text-orange-500">$-</span></span>
                <span class="bg-white dark:bg-indigo-950 px-3 py-1.5 rounded-lg text-xs font-bold text-dark dark:text-white border border-indigo-100 dark:border-indigo-700">Martingale F<span id="rodis-f-mg2">12</span>: <span id="rodis-bet-s3" class="text-orange-600">$-</span></span>
                <span class="bg-white dark:bg-indigo-950 px-3 py-1.5 rounded-lg text-xs font-bold text-dark dark:text-white border border-indigo-100 dark:border-indigo-700">Martingale F<span id="rodis-f-mg3">13</span>: <span id="rodis-bet-s4" class="text-red-600">$-</span></span>
            </div>
        </div>
    </div>

    {{-- ═══════════════════════════════════════════════════════════
         LOG TERMINAL
    ═══════════════════════════════════════════════════════════ --}}
    <div class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden">
        <div class="px-5 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
            <span class="text-xs font-extrabold text-gray-500 uppercase tracking-widest">Log Eksekusi RODIS Auto</span>
        </div>
        <div id="rodis-terminal"
            class="text-xs custom-scrollbar"
            style="font-family:'Courier New',Courier,monospace; background:#0f172a; color:#4ade80; height:260px; overflow-y:auto; padding:1rem;">
            <span class="text-indigo-400 opacity-60">Sistem siap. Atur form di atas lalu klik "Nyalakan RODIS Auto".</span>
        </div>
    </div>

</div>

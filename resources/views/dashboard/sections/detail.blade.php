<div id="view-detail" class="fade-in hidden">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div class="w-full md:w-auto">
            <button onclick="showView('dashboard')"
                class="flex items-center justify-center w-full sm:w-auto gap-2 text-sm font-bold text-gray-500 hover:text-dark transition-colors mb-2 bg-white px-4 py-2.5 rounded-xl shadow-sm border border-gray-200">
                ⬅ Kembali ke Dashboard
            </button>
            <h2 class="text-2xl sm:text-3xl font-extrabold text-dark mt-3 flex items-center gap-3">
                Analisis: <span id="detail-market-name" class="text-gojek">Market</span>
            </h2>
            <p id="detail-status" class="text-sm text-gray-500 font-medium mt-1">Menunggu instruksi...</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full md:w-auto">
            <button id="btn-start-bot" onclick="startCurrentMarketBot()"
                class="w-full px-6 py-3 bg-gojek text-white font-bold rounded-xl hover:bg-gojek-dark transition-colors shadow-sm text-sm">
                ▶ Hubungkan Bot
            </button>
            <button id="btn-stop-bot" onclick="stopCurrentMarketBot()"
                class="w-full px-6 py-3 bg-red-light text-red font-bold rounded-xl hover:bg-red-200 transition-colors shadow-sm text-sm hidden">
                ⏹ Hentikan Bot
            </button>
            <button id="btn-reset-data" onclick="resetCurrentMarket()"
                class="w-full px-6 py-3 bg-gray-100 text-gray-700 font-bold rounded-xl hover:bg-gray-300 transition-colors shadow-sm text-sm">
                🔄 Reset Data
            </button>
        </div>
    </div>

    <div
        class="bg-blue-50 rounded-2xl p-5 mb-6 shadow-sm border border-blue-100 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-5">
        <div class="w-full lg:w-auto">
            <h3 class="text-lg font-bold text-blue-900 mb-1">📲 Sinyal Telegram Otomatis</h3>
            <p class="text-xs text-blue-700 leading-relaxed">Berjalan 24 Jam Nonstop dari Server untuk market ini.</p>
            <p id="tg-status-text" class="text-sm font-bold text-gray-500 mt-2">Status: NONAKTIF</p>
        </div>
        <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end w-full lg:w-auto">
            <div class="w-full sm:w-auto">
                <label
                    class="block text-xs font-bold text-blue-800 uppercase mb-2 sm:mb-1 text-left sm:text-center">Kirim
                    Saat False Ke:</label>
                <input type="number" id="tg-target-loss" value="7"
                    class="w-full sm:w-32 px-4 py-3 bg-white border border-blue-200 rounded-xl font-bold text-xl outline-none text-center shadow-sm">
            </div>
            <button onclick="toggleTelegramServer()" id="btn-tg-toggle"
                class="w-full sm:w-auto px-6 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 shadow-md transition-colors">
                Aktifkan Telegram
            </button>
        </div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div
            class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm text-center bg-gradient-to-br from-indigo-50 to-white">
            <p class="text-[10px] font-bold text-indigo-500 uppercase tracking-widest mb-1">Target Open Posisi Ke</p>
            <p class="text-2xl font-extrabold text-indigo-900" id="val-target-op">0</p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm text-center">
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Total Analisis</p>
            <p class="text-2xl font-extrabold text-dark" id="val-total">0</p>
        </div>

        <div class="bg-green-50 p-5 rounded-2xl border border-green-200 shadow-sm text-center relative overflow-hidden">
            <div class="absolute bottom-0 left-0 w-full h-1 bg-green-500"></div>
            <p class="text-[10px] font-bold text-green-600 uppercase tracking-widest mb-1">Signal TRUE (Warna Sama)</p>
            <p class="text-2xl font-extrabold text-green-600" id="val-sig-win">0</p>
        </div>

        <div class="bg-red-50 p-5 rounded-2xl border border-red-200 shadow-sm text-center relative overflow-hidden">
            <div class="absolute bottom-0 left-0 w-full h-1 bg-red-500"></div>
            <p class="text-[10px] font-bold text-red-600 uppercase tracking-widest mb-1">Signal FALSE (Warna Beda)</p>
            <p class="text-2xl font-extrabold text-red-600" id="val-sig-loss">0</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-gojek/20 shadow-sm text-center relative overflow-hidden">
            <div class="absolute bottom-0 left-0 w-full h-1 bg-gojek"></div>
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Total Hijau</p>
            <p class="text-2xl font-extrabold text-gojek" id="val-hijau">0</p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-red/20 shadow-sm text-center relative overflow-hidden">
            <div class="absolute bottom-0 left-0 w-full h-1 bg-red"></div>
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Total Merah</p>
            <p class="text-2xl font-extrabold text-red" id="val-merah">0</p>
        </div>
    </div>

    {{-- Doji Analytics Section --}}
    <div id="detail-doji-section" class="bg-indigo-50 border border-indigo-100 rounded-2xl p-5 mb-6 shadow-sm hidden">
        <div class="flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="text-center md:text-left">
                <h3 class="text-sm font-extrabold text-indigo-900 flex items-center justify-center md:justify-start gap-2">
                    📊 Analisa Doji Khusus Market Ini
                </h3>
                <p class="text-xs text-indigo-700 mt-1">Dihitung otomatis ketika muncul Signal FALSE berdasarkan data 5x lipat dari jumlah FALSE aktif.</p>
            </div>
            <div class="flex flex-wrap justify-center gap-2 sm:gap-4 items-center">
                <div class="text-center bg-white px-3 sm:px-4 py-2 rounded-xl shadow-sm border border-indigo-50 w-24 sm:w-auto">
                    <p class="text-[9px] sm:text-[10px] uppercase font-bold text-gray-500 mb-0.5">Candle Dicek</p>
                    <p class="text-base sm:text-lg font-black text-dark" id="doji-detail-candles">0</p>
                </div>
                <div class="text-center bg-white px-3 sm:px-4 py-2 rounded-xl shadow-sm border border-indigo-50 w-24 sm:w-auto">
                    <p class="text-[9px] sm:text-[10px] uppercase font-bold text-gray-500 mb-0.5">Total Doji</p>
                    <p class="text-base sm:text-lg font-black text-indigo-600" id="doji-detail-count">0</p>
                </div>
                <div class="text-center bg-indigo-600 px-3 sm:px-4 py-2 rounded-xl shadow-sm w-24 sm:w-auto">
                    <p class="text-[9px] sm:text-[10px] uppercase font-bold text-indigo-200 mb-0.5">Winrate</p>
                    <p class="text-base sm:text-lg font-black text-white" id="doji-detail-winrate">0%</p>
                </div>
            </div>
        </div>
    </div>

    <div
        class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6 flex flex-col relative w-full">
        <div
            class="p-3 sm:p-4 border-b border-gray-100 flex flex-col sm:flex-row justify-between items-start sm:items-center bg-gray-50/50 gap-3 w-full">
            <div class="flex items-center gap-2">
                <h3 class="text-sm font-extrabold text-dark flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_#3b82f6]"></span>
                    Live Market Data
                </h3>
                <span
                    class="text-[9px] sm:text-[10px] font-bold text-gray-500 bg-white px-2 py-1 rounded border border-gray-200 shadow-sm"
                    id="local-chart-market">Memuat Market...</span>
            </div>

            <div
                class="flex bg-white rounded-lg p-0.5 border border-gray-200 shadow-sm w-full sm:w-auto justify-between">
                <button onclick="changeChartTimeframe('1M', this)"
                    class="tf-btn flex-1 sm:flex-none px-4 py-1.5 text-xs font-bold rounded bg-gray-100 text-gray-800 transition-colors">1M</button>
                <button onclick="changeChartTimeframe('5M', this)"
                    class="tf-btn flex-1 sm:flex-none px-4 py-1.5 text-xs font-bold rounded text-gray-500 hover:text-gray-800 transition-colors">5M</button>
                <button onclick="changeChartTimeframe('15M', this)"
                    class="tf-btn flex-1 sm:flex-none px-4 py-1.5 text-xs font-bold rounded text-gray-500 hover:text-gray-800 transition-colors">15M</button>
            </div>
        </div>
        <div class="p-1 sm:p-4 bg-white w-full overflow-hidden">
            <div id="local-chart-container" class="w-full min-h-[300px] sm:min-h-[380px]">
                <div class="flex h-full items-center justify-center text-gray-400 font-bold py-20 text-xs sm:text-base">
                    Menyiapkan Data...</div>
            </div>
        </div>
        <div
            class="px-3 sm:px-5 py-2 sm:py-3 bg-blue-50/50 text-[10px] sm:text-xs font-medium text-blue-800 border-t border-blue-100 flex items-start gap-2 sm:gap-3 w-full">
            <span class="text-sm sm:text-base">ℹ️</span>
            <p class="leading-relaxed">Data <b>Open, High, Low, Close</b> ini dikalkulasi secara simulasi akurat berdasarkan histori warna
                candle dari bot Anda. Warna Hijau menandakan candle naik, Warna Merah menandakan candle turun.
            </p>
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden min-h-[300px]">
        <div class="overflow-x-auto w-full custom-scrollbar">
            <table class="w-full text-left border-collapse" id="log-table">
                <thead>
                    <tr>
                        <th
                            class="py-4 px-4 sm:px-8 bg-gray-50 text-[10px] sm:text-xs font-bold text-gray-400 uppercase border-b border-gray-100 whitespace-nowrap">
                            Waktu Candle</th>
                        <th
                            class="py-4 px-4 sm:px-8 bg-gray-50 text-[10px] sm:text-xs font-bold text-gray-400 uppercase border-b border-gray-100 whitespace-nowrap">
                            Market</th>
                        <th
                            class="py-4 px-4 sm:px-8 bg-gray-50 text-[10px] sm:text-xs font-bold text-gray-400 uppercase border-b border-gray-100 whitespace-nowrap">
                            Arah / Warna</th>
                    </tr>
                </thead>
                <tbody id="table-body" class="divide-y divide-gray-100">
                    <tr>
                        <td colspan="3" class="py-20 text-center text-gray-500 text-xs sm:text-sm">Silakan klik
                            "Hubungkan Bot" terlebih dahulu.</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div id="detail-pagination-controls"
            class="flex justify-center items-center gap-1 sm:gap-2 p-3 sm:p-4 border-t border-gray-100 flex-wrap"></div>
    </div>
</div>

<style>
    .tf-btn.bg-gray-100 {
        background-color: #f1f5f9;
        color: #1e293b;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }

    /* Scrollbar minimalis khusus tabel detail agar rapi di HP */
    .custom-scrollbar::-webkit-scrollbar {
        height: 6px;
        width: 6px;
    }

    .custom-scrollbar::-webkit-scrollbar-track {
        background: #f8fafc;
    }

    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }
</style>

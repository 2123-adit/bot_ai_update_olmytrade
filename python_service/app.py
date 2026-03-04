from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
from datetime import datetime
import asyncio
import mysql.connector
from mysql.connector import pooling
import urllib.request
import urllib.parse

try:
    from olymptrade_ws import OlympTradeClient
except ImportError:
    OlympTradeClient = None

app = Flask(__name__)
# Izinkan CORS untuk semua origin dan semua metode
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# ==========================================
# KONFIGURASI TELEGRAM  ← GANTI DI SINI
# ==========================================
TELEGRAM_BOT_TOKEN = "8762488972:AAHzdICqLME-9MuMh1aZevOpc0TyNHceES8"
TELEGRAM_CHAT_ID   = "-5220906500"   # Grup: RODIS NOTIFIKASI
# Cara: 1) Buat bot di @BotFather → salin token
#        2) Buat grup, tambahkan bot, buka:
#           https://api.telegram.org/bot<TOKEN>/getUpdates
#        3) Kirim pesan di grup → ambil "id" dari "chat" (angka negatif)

# Variabel RAM (hanya untuk antrian manual trade)
markets_data = {}
global_demo_balance = 0.0

# ==========================================
# RODIS AUTO STATE (Martingale + Compound)
# ==========================================
rodis_auto_state = {
    "active": False,
    "state": "IDLE",          # IDLE | SCANNING | WAITING_ENTRY | TRADING | DONE_WIN | DONE_LOSS
    "modal": 0.0,
    "modal_awal": 0.0,
    "target_false": 9,
    "token": "",
    "account_id": "",
    "current_market": None,
    "false_detected_at": None,
    "step": 0,
    "current_bet": 0.0,
    "trade_result": None,
    "entry_direction": None,
    "entry_minute_key": None,
    "last_candle_checked": None,
    "log": [],
    "total_profit": 0.0,
    "total_win": 0,
    "total_loss": 0,
    "session_start": None,
    # Feature: Stop Loss Harian
    "stop_loss_daily": 0.0,    # 0 = tidak aktif
    "daily_loss_today": 0.0,   # akumulasi kerugian hari ini
}

def rodis_log(msg):
    """Tambah pesan ke log RODIS Auto, max 200 baris."""
    ts = datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{ts}] {msg}"
    rodis_auto_state["log"].append(full_msg)
    if len(rodis_auto_state["log"]) > 200:
        rodis_auto_state["log"] = rodis_auto_state["log"][-200:]
    print(f"[RODIS] {full_msg}")

def rodis_calc_bet(step, modal):
    """Hitung bet berdasarkan step martingale dan modal."""
    entry = round(modal * 0.0535, 2)
    if entry < 1.0: entry = 1.0
    bets = [entry, round(entry * 2.2, 2), round(entry * 2.2 * 2.2, 2), round(entry * 2.2 * 2.2 * 2.2, 2)]
    idx = max(0, min(step - 1, 3))
    return bets[idx]

def rodis_auto_worker():
    """Background thread: state machine RODIS Auto."""
    import asyncio

    BET_MULTIPLIER   = 2.2
    PROFIT_RATE      = 0.80   # 80% dari nilai bet saat menang (Olymp Trade 80%)
    MAX_STEP         = 4      # step 1 = entry, step 2-4 = martingale
    POLL_INTERVAL    = 3      # detik antar loop
    
    waiting_result   = False
    trade_expire_at  = None   # timestamp saat trade harus sudah selesai

    while rodis_auto_state["active"]:
        try:
            state = rodis_auto_state["state"]

            # ─── SCANNING: cari market dengan false = target ───────────────
            if state == "SCANNING":
                target = rodis_auto_state["target_false"]
                best_market = None
                best_time   = None

                for mkt, mdata in markets_data.items():
                    if not mdata.get("is_running"):
                        continue
                    hist = get_history_db(mkt, 200)
                    sig  = calc_sig_loss(hist)
                    if sig >= target:
                        # Temukan waktu candle pertama yang membuat false = target
                        # Ambil waktu candle terbaru sebagai proxy (lebih awal = lebih baik)
                        if hist:
                            mkt_time = hist[0].get("waktu", "99:99")
                            if best_time is None or mkt_time < best_time:
                                best_market = mkt
                                best_time   = mkt_time

                if best_market:
                    rodis_auto_state["current_market"] = best_market
                    rodis_auto_state["step"]           = 1
                    rodis_auto_state["state"]          = "WAITING_ENTRY"
                    rodis_auto_state["entry_minute_key"] = None
                    rodis_auto_state["last_candle_checked"] = None
                    rodis_log(f"🎯 Market ditemukan: {best_market} — FALSE ke-{target}. Menunggu candle menit-0 blok berikutnya...")

            # ─── WAITING_ENTRY: tunggu candle menit-0 blok ke-N ──────────
            elif state == "WAITING_ENTRY":
                market = rodis_auto_state["current_market"]
                if not market or not markets_data.get(market, {}).get("is_running"):
                    rodis_log("⚠️ Market tidak lagi aktif. Kembali SCANNING...")
                    rodis_auto_state["state"] = "SCANNING"
                    time.sleep(POLL_INTERVAL)
                    continue

                now = datetime.now()
                mm  = now.minute
                # Tunggu menit ke-0 dari blok 5 menit (xx:00, xx:05, xx:10, ...)
                if mm % 5 != 0:
                    time.sleep(1)
                    continue

                # Buat key unik untuk blok ini agar tidak dobel
                blk_key = f"{now.strftime('%Y-%m-%d %H')}:{(mm//5)*5:02d}"
                if blk_key == rodis_auto_state["entry_minute_key"]:
                    time.sleep(1)
                    continue

                # Baca histori: ambil warna candle menit ke-0 blok ini
                hist = get_history_db(market, 30)
                mm0_str = f"{now.strftime('%H')}:{mm:02d}"
                target_candle = None
                for h in hist:
                    if h.get("waktu", "") == mm0_str:
                        target_candle = h
                        break

                if not target_candle:
                    rodis_log(f"⏳ Menunggu candle {mm0_str} muncul di {market}...")
                    time.sleep(2)
                    continue

                # Tentukan arah bet: sama dengan warna candle menit-0
                raw_warna = target_candle.get("warna", "Merah")
                if "Hijau" in raw_warna:
                    direction = "Hijau"
                    olym_dir  = "call"   # BUY
                else:
                    direction = "Merah"
                    olym_dir  = "put"    # SELL

                bet_amount = rodis_calc_bet(rodis_auto_state["step"], rodis_auto_state["modal"])
                rodis_auto_state["current_bet"]      = bet_amount
                rodis_auto_state["entry_direction"]  = direction
                rodis_auto_state["entry_minute_key"] = blk_key

                rodis_log(f"📌 Step {rodis_auto_state['step']} | Candle {mm0_str}={raw_warna} | Arah: {direction.upper()} | Bet: ${bet_amount}")

                # Pasang trade ke OlympTrade via manual_queue (sama seperti tombol manual trade)
                if market in markets_data:
                    markets_data[market]["manual_queue"].append({
                        "direction": olym_dir,
                        "amount": bet_amount,
                        "duration": 60
                    })
                    rodis_auto_state["state"]       = "TRADING"
                    trade_expire_at = time.time() + 90   # tunggu max 90 detik
                    waiting_result  = True
                    rodis_log(f"🚀 Trade dikirim! Menunggu hasil 60 detik...")
                else:
                    rodis_log("❌ Market hilang dari daftar aktif. Kembali SCANNING...")
                    rodis_auto_state["state"] = "SCANNING"

            # ─── TRADING: tunggu hasil trade ─────────────────────────────
            elif state == "TRADING":
                if trade_expire_at and time.time() > trade_expire_at:
                    # Timeout — cek histori untuk tahu hasilnya
                    market    = rodis_auto_state["current_market"]
                    direction = rodis_auto_state["entry_direction"]
                    hist      = get_history_db(market, 10)
                    
                    # Cari candle hasil (menit ke-2 dari blok yang sama)
                    now      = datetime.now()
                    blk_key  = rodis_auto_state["entry_minute_key"]
                    blk_mm   = int(blk_key.split(":")[1])
                    result_mm = blk_mm + 2
                    if result_mm >= 60:
                        result_mm -= 60
                    result_str = f"{blk_key.split(' ')[1].split(':')[0]}:{result_mm:02d}"
                    
                    result_candle = None
                    for h in hist:
                        if h.get("waktu") == result_str:
                            result_candle = h
                            break

                    if result_candle:
                        raw_warna  = result_candle.get("warna", "Merah")
                        result_dir = "Hijau" if "Hijau" in raw_warna else "Merah"
                        is_win     = (result_dir == direction)
                    else:
                        # Tidak ketemu candle hasil, anggap false (konservatif)
                        is_win = False
                        rodis_log("⚠️ Candle hasil tidak ditemukan, dianggap LOSS")

                    waiting_result  = False
                    trade_expire_at = None

                    if is_win:
                        profit = round(rodis_auto_state["current_bet"] * PROFIT_RATE, 2)
                        rodis_auto_state["modal"]        += profit
                        rodis_auto_state["total_profit"] += profit
                        rodis_auto_state["total_win"]    += 1
                        modal_now = round(rodis_auto_state['modal'], 2)
                        rodis_log(f"✅ WIN! Profit +${profit} | Modal baru: ${modal_now}")
                        # ── Notifikasi Telegram WIN ─────────────────────────────
                        send_telegram_internal(
                            f"✅ *RODIS AUTO: WIN* ✅\n\n"
                            f"📈 *Market:* {market}\n"
                            f"🎯 Step: {rodis_auto_state['step']} | Arah: *{rodis_auto_state['entry_direction'].upper()}*\n"
                            f"💵 Bet: *${rodis_auto_state['current_bet']}* | Profit: *+${profit}*\n"
                            f"🏦 Modal sekarang: *${modal_now}*"
                        )
                        rodis_auto_state["state"]          = "SCANNING"
                        rodis_auto_state["current_market"] = None
                        rodis_auto_state["step"]           = 0
                    else:
                        step     = rodis_auto_state["step"]
                        bet_loss = rodis_auto_state["current_bet"]
                        rodis_auto_state["daily_loss_today"] += bet_loss

                        if step >= MAX_STEP:
                            rodis_auto_state["total_loss"] += 1
                            rodis_log(f"❌ LOSS di Step {step} (FALSE ke-{rodis_auto_state['target_false'] + step}). Bot berhenti di market ini.")
                            # ── Notifikasi Telegram LOSS ──────────────────────────
                            send_telegram_internal(
                                f"❌ *RODIS AUTO: LOSS MAX* ❌\n\n"
                                f"📈 *Market:* {market}\n"
                                f"🎯 Step: {step} (Step Maksimum Tercapai)\n"
                                f"💵 Total Loss Sesi Ini: ~${round(rodis_auto_state['daily_loss_today'],2)}\n"
                                f"🏦 Modal tersisa: *${round(rodis_auto_state['modal'],2)}*"
                            )
                            rodis_auto_state["state"]          = "SCANNING"
                            rodis_auto_state["current_market"] = None
                            rodis_auto_state["step"]           = 0

                            # ── Cek Stop Loss Harian ──────────────────────────────
                            sl = rodis_auto_state["stop_loss_daily"]
                            if sl > 0 and rodis_auto_state["daily_loss_today"] >= sl:
                                rodis_log(f"🛑 STOP LOSS HARIAN tercapai (${rodis_auto_state['daily_loss_today']:.2f} >= limit ${sl}). Bot dihentikan!")
                                send_telegram_internal(
                                    f"🛑 *RODIS AUTO: STOP LOSS HARIAN* 🛑\n\n"
                                    f"Total kerugian hari ini: *${rodis_auto_state['daily_loss_today']:.2f}*\n"
                                    f"Limit stop loss: *${sl}*\n"
                                    f"Bot RODIS Auto otomatis dihentikan untuk melindungi modal."
                                )
                                rodis_auto_state["active"] = False
                                rodis_auto_state["state"]  = "IDLE"
                        else:
                            rodis_auto_state["step"]  += 1
                            rodis_auto_state["state"]   = "WAITING_ENTRY"
                            rodis_auto_state["entry_minute_key"] = None
                            rodis_log(f"🔄 LOSS di Step {step}. Martingale ke Step {rodis_auto_state['step']}...")

            time.sleep(POLL_INTERVAL)
        except Exception as e:
            rodis_log(f"⚠️ Worker error: {e}")
            time.sleep(5)

    rodis_log("🛑 RODIS Auto dihentikan.")


# --- KONFIGURASI MYSQL ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'robot_trading'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Error Database: {err}")
        return None

# --- FUNGSI DATABASE HELPER ---
def save_settings(token, account_id):
    conn = get_db_connection()
    if not conn: return
    c = conn.cursor()
    c.execute("SELECT id FROM settings WHERE id = 1")
    if c.fetchone():
        c.execute("UPDATE settings SET token = %s, account_id = %s, updated_at = NOW() WHERE id = 1", (token, account_id))
    else:
        c.execute("INSERT INTO settings (id, token, account_id, created_at, updated_at) VALUES (1, %s, %s, NOW(), NOW())", (token, account_id))
    conn.commit()
    c.close()
    conn.close()

def get_settings():
    conn = get_db_connection()
    if not conn: return {"token": "", "account_id": ""}
    c = conn.cursor()
    c.execute("SELECT token, account_id FROM settings WHERE id = 1")
    res = c.fetchone()
    c.close()
    conn.close()
    return {"token": res[0], "account_id": res[1]} if res else {"token": "", "account_id": ""}

def init_market_state(market_name):
    if market_name not in markets_data: markets_data[market_name] = {"manual_queue": []}
    conn = get_db_connection()
    if not conn: return
    c = conn.cursor(dictionary=True)
    c.execute("SELECT is_running, tg_active, tg_target_loss, tg_phase, tg_trade_counter, tg_last_candle, tg_direction FROM market_states WHERE market = %s", (market_name,))
    row = c.fetchone()
    c.close()
    
    if not row:
        c = conn.cursor()
        c.execute("INSERT INTO market_states (market, created_at, updated_at) VALUES (%s, NOW(), NOW())", (market_name,))
        conn.commit(); c.close()
        row = {'is_running': 1, 'tg_active': 0, 'tg_target_loss': 7, 'tg_phase': 'IDLE', 'tg_trade_counter': 0, 'tg_last_candle': '', 'tg_direction': ''}
    else:
        c = conn.cursor()
        c.execute("UPDATE market_states SET is_running = 1, updated_at = NOW() WHERE market = %s", (market_name,))
        conn.commit(); c.close(); row['is_running'] = 1
        
    markets_data[market_name].update({
        'is_running': row.get('is_running', 1), 'tg_active': row.get('tg_active', 0),
        'tg_target_loss': row.get('tg_target_loss', 7), 'tg_phase': row.get('tg_phase', 'IDLE'),
        'tg_trade_counter': row.get('tg_trade_counter', 0), 'tg_last_candle': row.get('tg_last_candle', ''),
        'tg_direction': row.get('tg_direction', '')
    })
    conn.close()

# --- FUNGSI BARU LOGIKA WARNA & DOJI ---
def get_candle_color(o, h, l, c):
    """Logika sesuai dokumen: Menentukan warna berdasarkan OHLC dan deteksi Doji"""
    body = abs(c - o)
    total_range = h - l

    # 1. Deteksi Doji (Badan < 10% dari total range)
    is_doji = False
    if total_range > 0:
        is_doji = (body / total_range) < 0.10
    elif body == 0:
        is_doji = True

    # 2. Tentukan Warna Dasar
    if c > o:
        base_color = "Hijau"
    elif c < o:
        base_color = "Merah"
    else:
        # Open == Close (Doji murni) -> Lihat dominasi ekor
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        base_color = "Hijau" if upper_wick >= lower_wick else "Merah"

    return f"Doji/{base_color}" if is_doji else base_color

# --- UPDATE: FUNGSI SIMPAN ANALISIS DENGAN OHLC ---
def save_analysis_db(market, tanggal, waktu, warna, o=0.0, h=0.0, l=0.0, c_pr=0.0, vol=0):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    # Mencegah Race Condition (Dobel Data) dengan `INSERT IGNORE`
    # Database sudah diamankan dengan: ALTER TABLE market_histories ADD CONSTRAINT unique_market_time UNIQUE (market, tanggal, waktu);
    sql = """INSERT IGNORE INTO market_histories
             (market, tanggal, waktu, warna, open_price, high_price, low_price, close_price, tick_volume, created_at, updated_at)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"""
    cursor.execute(sql, (market, tanggal, waktu, warna, o, h, l, c_pr, vol))
    
    # Cek jika tidak ada baris yang disisipkan (artinya data sudah ada/dobel) maka jangan tambah total_trade
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return

    # Update state (tetap gunakan warna dasar untuk data statistik dashboard)
    base_color = "Hijau" if "Hijau" in warna else "Merah"
    if base_color == "Hijau":
        cursor.execute("UPDATE market_states SET total_trade = total_trade + 1, total_hijau = total_hijau + 1 WHERE market = %s", (market,))
    else:
        cursor.execute("UPDATE market_states SET total_trade = total_trade + 1, total_merah = total_merah + 1 WHERE market = %s", (market,))

    conn.commit()
    cursor.close()
    conn.close()

def get_history_db(market, limit=100):
    conn = get_db_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    c.execute("SELECT market, tanggal, waktu, warna, open_price, high_price, low_price, close_price FROM market_histories WHERE market = %s ORDER BY id DESC LIMIT %s", (market, limit))
    res = c.fetchall()
    c.close()
    conn.close()
    return res

def save_trade_db(tanggal, waktu, market, warna, amount):
    conn = get_db_connection()
    if not conn: return
    c = conn.cursor()
    c.execute("INSERT INTO trade_histories (tanggal, waktu, market, warna, amount, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
            (tanggal, waktu, market, warna, amount))
    conn.commit()
    c.close()
    conn.close()

ASSET_MAPPING = {
    "Asia Composite Index": "ASIA_X", "Europe Composite Index": "EUROPE_X",
    "Commodity Composite": "CMDTY_X", "Crypto Composite Index": "CRYPTO_X",
    "EUR/USD OTC": "EURUSD_OTC", "GBP/USD OTC": "GBPUSD_OTC", "USD/JPY OTC": "USDJPY_OTC",
    "AUD/USD OTC": "AUDUSD_OTC", "NZD/USD OTC": "NZDUSD_OTC", "USD/CAD OTC": "USDCAD_OTC",
    "USD/CHF OTC": "USDCHF_OTC", "EUR/JPY OTC": "EURJPY_OTC", "GBP/JPY OTC": "GBPJPY_OTC",
    "AUD/JPY OTC": "AUDJPY_OTC", "CAD/JPY OTC": "CADJPY_OTC", "NZD/JPY OTC": "NZDJPY_OTC",
    "CHF/JPY OTC": "CHFJPY_OTC", "EUR/GBP OTC": "EURGBP_OTC", "EUR/AUD OTC": "EURAUD_OTC",
    "EUR/CAD OTC": "EURCAD_OTC", "EUR/CHF OTC": "EURCHF_OTC", "GBP/AUD OTC": "GBPAUD_OTC",
    "GBP/CAD OTC": "GBPCAD_OTC", "GBP/CHF OTC": "GBPCHF_OTC", "AUD/CAD OTC": "AUDCAD_OTC",
    "AUD/CHF OTC": "AUDCHF_OTC", "CAD/CHF OTC": "CADCHF_OTC",
}

# --- UPDATE: TELEGRAM DENGAN USER AGENT UNTUK VPS ---
def send_telegram_internal(message):
    def send_task():
        bot_token = TELEGRAM_BOT_TOKEN
        chat_id   = TELEGRAM_CHAT_ID
        if not bot_token or "MASUKKAN" in bot_token:
            print("⚠️ Telegram belum dikonfigurasi. Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di app.py")
            return
        try:
            encoded_msg = urllib.parse.quote(message)
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={encoded_msg}&parse_mode=Markdown"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"❌ Gagal mengirim Telegram: {e}")

    threading.Thread(target=send_task, daemon=True).start()

def calc_sig_loss(history_list):
    sig_loss = 0
    blocks = {}
    for c in history_list:
        if c.get("waktu") and ":" in c["waktu"]:
            parts = c["waktu"].split(":")
            hh, mm = parts[0], int(parts[1])
            base_mm = (mm // 5) * 5
            key = f"{c['tanggal']}_{hh}:{base_mm:02d}"
            if key not in blocks: blocks[key] = {}
            if mm % 5 == 0: blocks[key]['c1'] = c['warna']
            if mm % 5 == 2: blocks[key]['c2'] = c['warna']

    # Diurutkan agar deteksi reset ke 0 dari candle terbaru berjalan akurat
    sorted_keys = sorted(blocks.keys(), reverse=True)
    for k in sorted_keys:
        b = blocks[k]
        if 'c1' in b and 'c2' in b:
            # Karena format warna sekarang bisa berisi Doji/Hijau, kita ambil base_color nya saja
            c1_base = "Hijau" if "Hijau" in b['c1'] else "Merah"
            c2_base = "Hijau" if "Hijau" in b['c2'] else "Merah"

            if c1_base != c2_base:
                sig_loss += 1
            else:
                break # Reset ke 0 jika mendeteksi ada 1 TRUE (Win)

    return sig_loss

async def fetch_accounts(token):
    accounts_info = []
    try:
        client = OlympTradeClient(access_token=token)
        await client.start()
        await asyncio.sleep(2)
        try:
            balance_data = await client.balance.get_balance()
            print(f"DEBUG fetch_accounts balance_data: {balance_data}")
            if isinstance(balance_data, dict) and 'd' in balance_data:
                for acc in balance_data['d']:
                    acc_id = str(acc.get('account_id') or acc.get('id'))
                    group = str(acc.get('group', 'unknown')).lower()
                    curr = str(acc.get('currency', 'unknown')).lower()
                    bal = float(acc.get('amount', 0))
                    is_demo = acc.get('is_demo', False)
                    tipe_akun = "Demo" if (is_demo or group == 'demo' or curr == 'demo') else "Real"
                    if not any(a['id'] == acc_id for a in accounts_info):
                        accounts_info.append({"id": acc_id, "type": tipe_akun, "balance": bal})
        except Exception as e:
            print(f"DEBUG fetch_accounts get_balance err: {e}")
        if hasattr(client, 'close'): await client.close()
        elif hasattr(client, 'disconnect'): await client.disconnect()
    except Exception as e:
        print(f"DEBUG fetch_accounts client.start err: {e}")
    return accounts_info

# --- FUNGSI BARU: UPDATE PROFITABILITAS KE DATABASE ---
async def update_profitability_db(client, account_id):
    """Mengambil data profit dari API dan simpan ke MySQL"""
    try:
        if not account_id: return
        profits = await client.market.get_profitability(account_id)
        if profits:
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            for item in profits:
                pair = item.get('pair')
                payout = item.get('payout', 0)
                if pair and payout:
                    cursor.execute("""
                        INSERT INTO asset_profitabilities (market, payout, updated_at)
                        VALUES (%s, %s, NOW())
                        ON DUPLICATE KEY UPDATE payout=%s, updated_at=NOW()
                    """, (pair, payout, payout))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error update profitability: {e}")

async def async_bot_task(market_name, token, user_account_id):
    global global_demo_balance
    actual_asset_id = ASSET_MAPPING.get(market_name, market_name)
    last_raw_candles = []

    try: target_account_id = int(str(user_account_id).strip()) if user_account_id else None
    except ValueError: target_account_id = None

    try:
        client = OlympTradeClient(access_token=token)
        original_dispatch = client._dispatch_message
        async def custom_dispatch(message):
            nonlocal last_raw_candles
            global global_demo_balance
            if isinstance(message, dict):
                msg_event = message.get('e')
                msg_data = message.get('d', [])
                if isinstance(msg_data, list):
                    for item in msg_data:
                        if isinstance(item, dict):
                            if 'amount' in item and ('id' in item or 'account_id' in item):
                                acc_id_loop = str(item.get('account_id') or item.get('id'))
                                if str(acc_id_loop) == str(target_account_id):
                                    global_demo_balance = float(item.get('amount', 0))
                            if msg_event == 10 and item.get('p') == actual_asset_id and 'candles' in item:
                                last_raw_candles = item.get('candles', [])
            if asyncio.iscoroutinefunction(original_dispatch): await original_dispatch(message)
            else: original_dispatch(message)

        client._dispatch_message = custom_dispatch
        await client.start()
        await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ Error start client {market_name}: {e}")
        # Jika gagal di awal, pastikan state is_running mati agar tidak looping kosong
        if market_name in markets_data:
            markets_data[market_name]['is_running'] = 0
        return

    last_minute_checked = -1

    while True:
        try:
            if market_name not in markets_data: break
            state = markets_data[market_name]
            if state.get('is_running', 0) == 0:
                if hasattr(client, 'close'): await client.close()
                elif hasattr(client, 'disconnect'): await client.disconnect()
                break
            now = datetime.now()

            # EKSEKUSI MANUAL TRADE
            if market_name in markets_data and len(markets_data[market_name]["manual_queue"]) > 0:
                cmd = markets_data[market_name]["manual_queue"].pop(0)
                try:
                    amount_int = int(float(cmd['amount']))
                    duration_raw = int(cmd['duration'])
                    direction_str = str(cmd['direction'])

                    try: await client.trade.place_order(actual_asset_id, amount_int, direction_str, duration_raw, target_account_id)
                    except TypeError: await client.trade.place_order(asset=actual_asset_id, amount=amount_int, dir=direction_str, duration=duration_raw, account_id=target_account_id)

                    save_trade_db(now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), market_name, f"MANUAL {direction_str.upper()}", amount_int)
                except Exception as e:
                    amt = locals().get('amount_int', 0)
                    save_trade_db(now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), market_name, f"GAGAL: Script Error", amt)

            # TRIGGER UPDATE PROFITABILITAS PER 5 MENIT
            if now.minute % 5 == 0 and now.second < 2:
                try:
                    await update_profitability_db(client, target_account_id)
                except Exception: pass

            # CEK KONEKSI & AUTO RECONNECT (Setiap 10 detik)
            if now.second % 10 == 0 and now.microsecond < 500000:
                if not client.connection.is_connected:
                    print(f"⚠️ [{market_name}] Koneksi terputus! Mencoba menyambung kembali...")
                    try:
                        await client.start()
                        await asyncio.sleep(2)
                        print(f"✅ [{market_name}] Berhasil terhubung kembali.")
                    except Exception as e:
                        print(f"❌ [{market_name}] Gagal Reconnect: {e}")
                        await asyncio.sleep(5)
                        continue

            # ANALISIS CANDLE PER 5 MENIT DENGAN TOLERANSI VPS LAG (2-15 Detik)
            if 2 <= now.second <= 15 and last_minute_checked != now.minute:
                prev_minute = (now.minute - 1) % 60

                if prev_minute % 5 == 0 or prev_minute % 5 == 2:
                    waktu_laporan = f"{now.hour if now.minute != 0 else (now.hour - 1) % 24:02d}:{prev_minute:02d}"
                    last_raw_candles = []
                    try:
                        await client.market.get_candles(actual_asset_id, 60, 2)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

                    if len(last_raw_candles) > 0:
                        last_minute_checked = now.minute
                        target_candle = last_raw_candles[1] if len(last_raw_candles) >= 2 else last_raw_candles[0]

                        # --- EKSTRAKSI DATA OHLC & VOL BARU ---
                        o_pr = float(target_candle.get('open', 0))
                        h_pr = float(target_candle.get('high', 0))
                        l_pr = float(target_candle.get('low', 0))
                        c_pr = float(target_candle.get('close', 0))
                        vol  = int(target_candle.get('vol', 0))

                        # --- TENTUKAN WARNA LOGIKA DOJI ---
                        warna_label = get_candle_color(o_pr, h_pr, l_pr, c_pr)
                        base_warna = "Hijau" if "Hijau" in warna_label else "Merah"

                        # Simpan data dengan lengkap
                        save_analysis_db(market_name, now.strftime("%Y-%m-%d"), waktu_laporan, warna_label, o_pr, h_pr, l_pr, c_pr, vol)

                        # LOGIKA TELEGRAM SERVER
                        if state['tg_active']:
                            hist = get_history_db(market_name, 100)
                            sig_loss = calc_sig_loss(hist)
                            mm = prev_minute
                            candle_id = f"{now.strftime('%Y-%m-%d')}_{waktu_laporan}"

                            if state["tg_last_candle"] != candle_id:
                                tg_phase = state['tg_phase']
                                tg_trade_counter = state['tg_trade_counter']
                                tg_direction = state['tg_direction']

                                if tg_phase == "IDLE" and (mm % 5 == 2):
                                    if state["tg_target_loss"] > 0:
                                        expected_trades = sig_loss // state["tg_target_loss"]

                                        # LOGIKA PINTAR AUTO-RESET SIKLUS
                                        if expected_trades < tg_trade_counter:
                                            tg_trade_counter = expected_trades
                                            state['tg_trade_counter'] = tg_trade_counter
                                            conn2 = get_db_connection()
                                            if conn2:
                                                conn2.cursor().execute("UPDATE market_states SET tg_trade_counter=%s WHERE market=%s", (tg_trade_counter, market_name))
                                                conn2.commit(); conn2.close()

                                        if expected_trades > tg_trade_counter and sig_loss > 0:
                                            tg_trade_counter += 1
                                            tg_phase = "WAIT_CONF"
                                            state['tg_trade_counter'] = tg_trade_counter; state['tg_phase'] = tg_phase; state['tg_last_candle'] = candle_id
                                            next_min = f"{(mm + 3) % 60:02d}"
                                            msg = f"⚠️ *SERVER: PERSIAPAN OP* ⚠️\n\n📈 *Market:* {market_name}\n🗓 *Waktu:* {waktu_laporan} WIB\n\nTarget *FALSE ke-{sig_loss}* tercapai.\nStandby arah menit ke-{next_min}.\n"
                                            send_telegram_internal(msg)
                                            conn2 = get_db_connection()
                                            if conn2:
                                                conn2.cursor().execute("UPDATE market_states SET tg_trade_counter=%s, tg_phase=%s, tg_last_candle=%s WHERE market=%s", (tg_trade_counter, tg_phase, candle_id, market_name))
                                                conn2.commit(); conn2.close()

                                elif tg_phase == "WAIT_CONF" and (mm % 5 == 0):
                                    tg_phase = "WAIT_RES"
                                    state['tg_phase'] = tg_phase
                                    state['tg_direction'] = "BUY 🟢" if base_warna == "Hijau" else "SELL 🔴"
                                    state['tg_last_candle'] = candle_id
                                    tg_direction = state['tg_direction']
                                    next_min = f"{(mm + 2) % 60:02d}"
                                    msg = f"🚀 *SERVER: SINYAL EKSEKUSI* 🚀\n\n📈 *Market:* {market_name}\n🗓 *Waktu:* {waktu_laporan} WIB\n\n🚨 Eksekusi Manual:\n👉 *{tg_direction}*\n🗓 *Hasil Menit {next_min}*\n"
                                    send_telegram_internal(msg)
                                    conn2 = get_db_connection()
                                    if conn2:
                                        conn2.cursor().execute("UPDATE market_states SET tg_phase=%s, tg_direction=%s, tg_last_candle=%s WHERE market=%s", (tg_phase, tg_direction, candle_id, market_name))
                                        conn2.commit(); conn2.close()

                                elif tg_phase == "WAIT_RES" and (mm % 5 == 2):
                                    tg_phase = "IDLE"
                                    state['tg_phase'] = tg_phase; state['tg_last_candle'] = candle_id
                                    required_color = "Hijau" if "BUY" in tg_direction else "Merah"
                                    is_win = (base_warna == required_color)
                                    status_emoji = "✅" if is_win else "❌"
                                    hasil_teks = "TRUE" if is_win else "FALSE"
                                    msg = f"{status_emoji} *SERVER: HASIL TRADE* {status_emoji}\n\n📈 *Market:* {market_name}\nArah Tadi: *{tg_direction}*\nCandle Hasil: *{warna_label.upper()}*\nHasil Akhir: *{hasil_teks}*\n"
                                    send_telegram_internal(msg)
                                    conn2 = get_db_connection()
                                    if conn2:
                                        conn2.cursor().execute("UPDATE market_states SET tg_phase=%s, tg_last_candle=%s WHERE market=%s", (tg_phase, candle_id, market_name))
                                        conn2.commit(); conn2.close()
                else:
                    last_minute_checked = now.minute

            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"⚠️ [{market_name}] Loop Error: {e}")
            await asyncio.sleep(2)


def run_trading_bot_thread(market_name, token, account_id):
    """Jalankan bot dengan auto-restart hingga 3x jika mati tidak sengaja."""
    MAX_RETRIES = 3
    RETRY_DELAY = 10   # detik antar retry

    for attempt in range(MAX_RETRIES + 1):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_bot_task(market_name, token, account_id))
            # Jika selesai normal (is_running == 0 = dihentikan user), keluar
            break
        except Exception as e:
            print(f"❌ [{market_name}] Bot crash (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        finally:
            loop.close()

        stopped_by_user = (markets_data.get(market_name, {}).get('is_running') == 0)
        if stopped_by_user:
            # Dihentikan oleh user — jangan retry
            break

        if attempt < MAX_RETRIES:
            # Auto-restart
            print(f"🔄 [{market_name}] Auto-restart {attempt+1}/{MAX_RETRIES} dalam {RETRY_DELAY} detik...")
            send_telegram_internal(
                f"🔄 *BOT AUTO-RESTART* ({attempt+1}/{MAX_RETRIES})\n\n"
                f"📈 *Market:* {market_name}\n"
                f"Bot mati tidak terduga dan sedang direstart otomatis..."
            )
            time.sleep(RETRY_DELAY)
            init_market_state(market_name)   # reset state sebelum retry
        else:
            # Semua retry habis — kirim notifikasi gagal
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"❌ [{market_name}] Semua {MAX_RETRIES} retry gagal. Bot menyerah.")
            try:
                conn = get_db_connection()
                if conn:
                    conn.cursor().execute("UPDATE market_states SET is_running = 0 WHERE market = %s", (market_name,))
                    conn.commit(); conn.close()
            except Exception:
                pass
            if market_name in markets_data:
                markets_data[market_name]['is_running'] = 0
            send_telegram_internal(
                f"❌ *BOT GAGAL RESTART* ❌\n\n"
                f"📈 *Market:* {market_name}\n"
                f"🕐 *Waktu:* {now_str}\n\n"
                f"Bot sudah mencoba restart {MAX_RETRIES}x namun terus gagal. "
                f"Silakan periksa koneksi / server dan nyalakan manual dari dashboard."
            )


# ==========================================
# ENDPOINT FLASK API
# ==========================================

@app.route('/api/get_settings', methods=['GET'])
def api_get_settings():
    return jsonify(get_settings())

@app.route('/api/save_token', methods=['POST', 'OPTIONS'])
def api_save_token():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json or {}
    token      = data.get('token', '')
    account_id = data.get('account_id', '')
    if not token:
        return jsonify({"status": "error", "message": "Token kosong"})
    save_settings(token, account_id)
    return jsonify({"status": "success"})

@app.route('/api/check_accounts', methods=['POST', 'OPTIONS'])
def api_check_accounts():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    token = request.json.get('token')
    if not token: return jsonify({"status": "error", "message": "Harap masukkan Access Token!"})
    try:
        accounts = asyncio.run(fetch_accounts(token))
        if accounts: return jsonify({"status": "success", "accounts": accounts})
        else: return jsonify({"status": "error", "message": "Gagal menarik data. Token salah / expired."})
    except Exception as e: return jsonify({"status": "error", "message": "Koneksi terputus dari server."})

@app.route('/api/start', methods=['POST', 'OPTIONS'])
def start_bot():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.json
    market = data.get('market')
    token = data.get('token')
    account_id = data.get('account_id')
    save_settings(token, account_id)

    if market not in markets_data: 
        markets_data[market] = {"manual_queue": []}
    elif markets_data[market].get('is_running') == 1:
        return jsonify({"status": "success", "message": f"{market} sudah berjalan!"})

    init_market_state(market)
    threading.Thread(target=run_trading_bot_thread, args=(market, token, account_id), daemon=True).start()
    return jsonify({"status": "success", "message": f"Koneksi {market} berhasil dibuka!"})

@app.route('/api/start_all', methods=['POST', 'OPTIONS'])
def start_all():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.json
    token = data.get('token')
    account_id = data.get('account_id')
    save_settings(token, account_id)

    def start_all_bg():
        for m in ASSET_MAPPING.keys():
            if m not in markets_data: 
                markets_data[m] = {"manual_queue": []}
            elif markets_data[m].get('is_running') == 1:
                continue # Skip if already running to prevent double threads
                
            init_market_state(m)
            threading.Thread(target=run_trading_bot_thread, args=(m, token, account_id), daemon=True).start()
            time.sleep(1.5)
            
    threading.Thread(target=start_all_bg, daemon=True).start()
    return jsonify({"status": "success", "message": f"Memulai {len(ASSET_MAPPING)} market secara bertahap!"})

@app.route('/api/stop', methods=['POST', 'OPTIONS'])
def stop_bot():
    if request.method == 'OPTIONS': return jsonify({}), 200
    market = request.json.get('market')
    if market in markets_data: markets_data[market]['is_running'] = 0
    conn = get_db_connection()
    if conn:
        conn.cursor().execute("UPDATE market_states SET is_running = 0 WHERE market = %s", (market,))
        conn.commit(); conn.close()
    return jsonify({"status": "success"})

@app.route('/api/stop_all', methods=['POST', 'OPTIONS'])
def stop_all():
    if request.method == 'OPTIONS': return jsonify({}), 200
    for m in markets_data.values(): m['is_running'] = 0
    conn = get_db_connection()
    if not conn: return jsonify({"status": "error"})
    conn.cursor().execute("UPDATE market_states SET is_running = 0")
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": "Semua bot market berhasil dihentikan!"})

@app.route('/api/reset_market', methods=['POST'])
def reset_market():
    market = request.json.get('market')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM market_histories WHERE market = %s", (market,))
    c.execute("UPDATE market_states SET total_trade=0, total_hijau=0, total_merah=0, tg_trade_counter=0, tg_phase='IDLE' WHERE market = %s", (market,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Data {market} berhasil direset."})

@app.route('/api/reset_all', methods=['POST'])
def reset_all():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("TRUNCATE TABLE market_histories")
    c.execute("UPDATE market_states SET total_trade=0, total_hijau=0, total_merah=0, tg_trade_counter=0, tg_phase='IDLE'")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Semua data berhasil direset!"})

@app.route('/api/toggle_telegram', methods=['POST'])
def toggle_telegram():
    data = request.json
    market = data.get('market')
    target_loss = int(data.get('target_loss', 7))

    if market in markets_data:
        new_active = 0 if markets_data[market]['tg_active'] else 1
        markets_data[market].update({'tg_active': new_active, 'tg_target_loss': target_loss, 'tg_phase': 'IDLE'})
        conn = get_db_connection()
        if conn:
            conn.cursor().execute("UPDATE market_states SET tg_active=%s, tg_target_loss=%s, tg_phase='IDLE' WHERE market=%s", (new_active, target_loss, market))
            conn.commit(); conn.close()
        return jsonify({"status": "success", "active": bool(new_active)})
    return jsonify({"status": "error", "message": "Market belum aktif!"})

@app.route('/api/toggle_telegram_all', methods=['POST'])
def toggle_telegram_all():
    data = request.json
    target_loss = int(data.get('target_loss', 7))
    active_count = 0
    conn = get_db_connection()
    c = conn.cursor()
    for m, state in markets_data.items():
        if state.get('is_running'):
            state.update({'tg_active': 1, 'tg_target_loss': target_loss, 'tg_phase': 'IDLE'})
            c.execute("UPDATE market_states SET tg_active=1, tg_target_loss=%s, tg_phase='IDLE' WHERE market=%s", (target_loss, m))
            active_count += 1
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": f"Sinyal Telegram DIAKTIFKAN di {active_count} market aktif!"})

@app.route('/api/stop_telegram_all', methods=['POST'])
def stop_telegram_all():
    for state in markets_data.values():
        state.update({'tg_active': 0, 'tg_phase': 'IDLE'})
    conn = get_db_connection()
    conn.cursor().execute("UPDATE market_states SET tg_active=0, tg_phase='IDLE'")
    conn.commit(); conn.close()
    return jsonify({"status": "success", "message": "Sinyal Telegram di SEMUA market berhasil dimatikan!"})

@app.route('/api/manual_trade', methods=['POST', 'OPTIONS'])
def manual_trade():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data = request.json
    market = data.get('market')
    if market in markets_data:
        markets_data[market]['manual_queue'].append({
            "direction": data.get('direction'), "amount": data.get('amount', 1), "duration": data.get('duration', 60)
        })
        return jsonify({"status": "success", "message": f"Sinyal dikirim!"})
    return jsonify({"status": "error", "message": "Bot belum jalan!"})

@app.route('/api/data', methods=['GET'])
def get_data():
    market = request.args.get('market')
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM market_states WHERE market = %s", (market,))
    state = c.fetchone()

    if state:
        histories = get_history_db(market, 500)
        
        # Calculate Doji Statistics for this specific market
        sig_loss = calc_sig_loss(histories)
        doji_count = 0
        winrate = 0.0
        candles_to_check = 0
        
        if sig_loss >= 1:
            candles_to_check = sig_loss * 5
            hist_target = histories[:candles_to_check]
            for item in hist_target:
                if item['warna'] and "Doji" in item['warna']:
                    doji_count += 1
            if candles_to_check > 0:
                winrate = (doji_count / float(candles_to_check)) * 100
                
        doji_analytics = {
            "consecutive_false": sig_loss,
            "doji_count": doji_count,
            "total_candles": candles_to_check,
            "winrate": round(winrate, 1)
        }

        conn.close()
        return jsonify({
            "is_running": bool(state['is_running']),
            "stats": {"total_trade": state['total_trade'], "total_hijau": state['total_hijau'], "total_merah": state['total_merah']},
            "history": histories,
            "doji_analytics": doji_analytics,
            "telegram": {"active": bool(state['tg_active']), "target_loss": state['tg_target_loss'], "trade_counter": state['tg_trade_counter']},
            "balance": global_demo_balance
        })
    conn.close()
    return jsonify({"is_running": False, "stats": {"total_trade": 0, "total_hijau": 0, "total_merah": 0}, "history": [], "doji_analytics": None, "balance": global_demo_balance})

@app.route('/api/status_all', methods=['GET'])
def status_all():
    conn = get_db_connection()
    if not conn: return jsonify({"active_markets": [], "market_streaks": {}, "balance": global_demo_balance, "tg_active_count": 0})

    c_dict = conn.cursor(dictionary=True)
    c_dict.execute("SELECT market, tg_active FROM market_states WHERE is_running = 1")
    running_data = c_dict.fetchall()

    active_markets = [row['market'] for row in running_data]
    tg_active_count = sum(1 for row in running_data if row['tg_active'] == 1)

    market_streaks = {}
    
    for mkt in active_markets:
        c_dict.execute("SELECT market, tanggal, waktu, warna FROM market_histories WHERE market = %s ORDER BY id DESC LIMIT 100", (mkt,))
        raw_hist = c_dict.fetchall()
        
        # Hitung sig_loss normal
        sig_loss = calc_sig_loss(raw_hist)
        market_streaks[mkt] = sig_loss

    c_dict.close()
    conn.close()
    return jsonify({
        "active_markets": active_markets,
        "market_streaks": market_streaks,
        "balance": global_demo_balance,
        "tg_active_count": tg_active_count
    })

@app.route('/api/trade_history', methods=['GET'])
def trade_history():
    conn = get_db_connection()
    if conn:
        c = conn.cursor(dictionary=True)
        c.execute("SELECT tanggal, waktu, market, warna, amount FROM trade_histories ORDER BY id DESC LIMIT 500")
        results = c.fetchall()
        conn.close()
        return jsonify({"trade_history": results})
    return jsonify({"trade_history": []})

@app.route('/api/send_wa', methods=['POST'])
def send_telegram():
    data = request.json
    send_telegram_internal(data.get('message', ''))
    return jsonify({"status": "success"})


# ==========================================
# RODIS AUTO API ENDPOINTS
# ==========================================

@app.route('/api/rodis_auto/start', methods=['POST', 'OPTIONS'])
def rodis_auto_start():
    if request.method == 'OPTIONS': return jsonify({}), 200
    data          = request.json or {}
    modal         = float(data.get('modal', 19))
    target        = int(data.get('target_false', 9))
    account_id    = data.get('account_id', '')
    token         = data.get('token', '')
    stop_loss_daily = float(data.get('stop_loss_daily', 0))

    if rodis_auto_state["active"]:
        return jsonify({"status": "error", "message": "RODIS Auto sudah berjalan!"})

    # Cek apakah ada minimal 1 market yang running
    running_count = sum(1 for m in markets_data.values() if m.get('is_running'))
    if running_count == 0:
        return jsonify({"status": "error", "message": "Belum ada market yang berjalan! Klik PLAY di Monitor terlebih dahulu."})

    sl_msg = f" | Stop Loss Harian: ${stop_loss_daily}" if stop_loss_daily > 0 else ""
    rodis_auto_state.update({
        "active": True,
        "state": "SCANNING",
        "modal": modal,
        "modal_awal": modal,
        "target_false": target,
        "token": token,
        "account_id": account_id,

        "current_market": None,
        "step": 0,
        "current_bet": 0.0,
        "entry_direction": None,
        "entry_minute_key": None,
        "last_candle_checked": None,
        "total_profit": 0.0,
        "total_win": 0,
        "total_loss": 0,
        "log": [],
        "session_start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stop_loss_daily": stop_loss_daily,
        "daily_loss_today": 0.0,
    })
    rodis_log(f"🚀 RODIS Auto DIMULAI | Modal: ${modal} | Target FALSE: {target}{sl_msg} | Akun: {account_id or 'default'}")
    threading.Thread(target=rodis_auto_worker, daemon=True).start()
    return jsonify({"status": "success", "message": "RODIS Auto berhasil dimulai!"})


@app.route('/api/rodis_auto/stop', methods=['POST', 'OPTIONS'])
def rodis_auto_stop():
    if request.method == 'OPTIONS': return jsonify({}), 200
    rodis_auto_state["active"] = False
    rodis_auto_state["state"]  = "IDLE"
    rodis_log("🛑 Perintah STOP diterima.")
    return jsonify({"status": "success", "message": "RODIS Auto dihentikan."})


@app.route('/api/rodis_auto/status', methods=['GET'])
def rodis_auto_status():
    s = rodis_auto_state
    step_labels = {0: "-", 1: "Entry (F"+str(s['target_false']+1)+")", 2: "Martingale 2", 3: "Martingale 3", 4: "Martingale 4"}
    return jsonify({
        "active":            s["active"],
        "state":             s["state"],
        "modal":             round(s["modal"], 2),
        "modal_awal":        round(s["modal_awal"], 2),
        "target_false":      s["target_false"],
        "current_market":    s["current_market"],
        "step":              s["step"],
        "step_label":        step_labels.get(s["step"], "-"),
        "current_bet":       round(s["current_bet"], 2),
        "entry_direction":   s["entry_direction"],
        "total_profit":      round(s["total_profit"], 2),
        "total_win":         s["total_win"],
        "total_loss":        s["total_loss"],
        "stop_loss_daily":   round(s["stop_loss_daily"], 2),
        "daily_loss_today":  round(s["daily_loss_today"], 2),
        "session_start":     s["session_start"],
        "log":               s["log"][-50:]
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')

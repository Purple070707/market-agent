"""
Market Intelligence Agent
Compatible Python 3.14 — utilise la bibliothèque 'ta'
"""

import time
import requests
import pandas as pd
import ta
from datetime import datetime
import yfinance as yf

# ──────────────────────────────────────────
# CONFIGURATION — À remplir
# ──────────────────────────────────────────

TELEGRAM_TOKEN = "TON_TOKEN_ICI"
TELEGRAM_CHAT_ID = "TON_CHAT_ID_ICI"

COINGECKO_API = "https://api.coingecko.com/api/v3"

# ──────────────────────────────────────────
# ACTIFS SURVEILLÉS
# ──────────────────────────────────────────

US_STOCKS_SMART = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "JPM", "META"]
FR_STOCKS_SMART = ["AI.PA", "TTE.PA", "SAN.PA", "OR.PA", "BNP.PA", "MC.PA"]
US_STOCKS_RISKY = ["GME", "AMC", "PLTR", "SOFI", "RIVN", "LCID", "SPCE"]
CRYPTO_IDS = [
    "bitcoin", "ethereum", "solana", "dogecoin",
    "shiba-inu", "pepe", "sui", "avalanche-2"
]

# ──────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[TELEGRAM] ✓ Envoyé")
    except Exception as e:
        print(f"[ERREUR TELEGRAM] {e}")

# ──────────────────────────────────────────
# ANALYSE ACTIONS
# ──────────────────────────────────────────

def analyze_stock(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d")

        if df.empty or len(df) < 30:
            return None

        close = df["Close"]
        volume = df["Volume"]

        rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
        macd_obj = ta.trend.MACD(close)
        macd = macd_obj.macd().iloc[-1]
        macd_signal = macd_obj.macd_signal().iloc[-1]
        macd_prev = macd_obj.macd().iloc[-2]
        macd_signal_prev = macd_obj.macd_signal().iloc[-2]
        sma20 = ta.trend.SMAIndicator(close, window=20).sma_indicator().iloc[-1]
        sma50 = ta.trend.SMAIndicator(close, window=50).sma_indicator().iloc[-1]

        price = close.iloc[-1]
        vol_today = volume.iloc[-1]
        vol_avg = volume.tail(20).mean()
        volume_ratio = vol_today / vol_avg if vol_avg > 0 else 1

        price_prev = close.iloc[-2]
        change_1d = ((price - price_prev) / price_prev) * 100

        smart_score = 0
        reasons_smart = []
        risk_score = 0
        reasons_risk = []

        if rsi < 30:
            smart_score += 3
            reasons_smart.append(f"RSI survendu : {rsi:.1f}")
        elif rsi < 40:
            smart_score += 1
            reasons_smart.append(f"RSI bas : {rsi:.1f}")
        elif rsi > 70:
            smart_score -= 2

        if macd > macd_signal and macd_prev <= macd_signal_prev:
            smart_score += 2
            reasons_smart.append("Croisement MACD haussier")

        if sma20 > sma50 and price > sma20:
            smart_score += 2
            reasons_smart.append("Prix au-dessus SMA20 et SMA50")

        if volume_ratio > 1.5:
            smart_score += 1
            reasons_smart.append(f"Volume élevé : x{volume_ratio:.1f}")

        if volume_ratio > 2.5:
            risk_score += 4
            reasons_risk.append(f"🔥 Volume x{volume_ratio:.1f} vs moyenne")

        if rsi > 68:
            risk_score += 2
            reasons_risk.append(f"RSI momentum fort : {rsi:.1f}")

        if abs(change_1d) > 5:
            risk_score += 3
            direction = "🚀" if change_1d > 0 else "💥"
            reasons_risk.append(f"{direction} Mouvement 1j : {change_1d:+.1f}%")

        return {
            "ticker": ticker,
            "price": price,
            "change_1d": change_1d,
            "smart_score": smart_score,
            "risk_score": risk_score,
            "reasons_smart": reasons_smart,
            "reasons_risk": reasons_risk,
        }

    except Exception as e:
        print(f"[ERREUR] {ticker}: {e}")
        return None

# ──────────────────────────────────────────
# ANALYSE CRYPTO
# ──────────────────────────────────────────

def analyze_crypto(coin_id: str):
    try:
        url = f"{COINGECKO_API}/coins/{coin_id}"
        r = requests.get(url, params={"localization": "false"}, timeout=15)
        data = r.json()

        market = data.get("market_data", {})
        price = market.get("current_price", {}).get("eur", 0)
        change_1h = market.get("price_change_percentage_1h_in_currency", {}).get("eur", 0) or 0
        change_24h = market.get("price_change_percentage_24h", 0) or 0
        change_7d = market.get("price_change_percentage_7d", 0) or 0
        volume_24h = market.get("total_volume", {}).get("eur", 0)
        market_cap = market.get("market_cap", {}).get("eur", 1)
        volume_ratio = volume_24h / market_cap if market_cap > 0 else 0
        symbol = data.get("symbol", "").upper()

        smart_score = 0
        reasons_smart = []
        risk_score = 0
        reasons_risk = []

        if change_24h < -10 and market_cap > 5_000_000_000:
            smart_score += 3
            reasons_smart.append(f"Correction forte sur large cap : {change_24h:.1f}%")
        if change_7d < -20 and market_cap > 1_000_000_000:
            smart_score += 2
            reasons_smart.append(f"Zone de rebond potentielle (7j : {change_7d:.1f}%)")

        if abs(change_1h) > 5:
            risk_score += 4
            reasons_risk.append(f"🔥 Mouvement 1h : {change_1h:+.1f}%")
        if volume_ratio > 0.5:
            risk_score += 3
            reasons_risk.append(f"Volume/Market cap élevé : {volume_ratio:.2f}")
        if abs(change_24h) > 15:
            risk_score += 3
            direction = "🚀" if change_24h > 0 else "💥"
            reasons_risk.append(f"{direction} Variation 24h : {change_24h:+.1f}%")

        return {
            "ticker": f"{symbol}/EUR",
            "price": price,
            "change_1d": change_24h,
            "smart_score": smart_score,
            "risk_score": risk_score,
            "reasons_smart": reasons_smart,
            "reasons_risk": reasons_risk,
        }

    except Exception as e:
        print(f"[ERREUR CRYPTO] {coin_id}: {e}")
        return None

# ──────────────────────────────────────────
# FORMATAGE ALERTES
# ──────────────────────────────────────────

def format_smart_alert(data: dict) -> str:
    score = data["smart_score"]
    price = data["price"]
    change = data.get("change_1d", 0)
    reasons = "\n".join([f"  • {r}" for r in data["reasons_smart"]])
    stars = "⭐" * min(int(score / 2), 5)
    return f"""🟢 <b>SMART MONEY — {data['ticker']}</b>
━━━━━━━━━━━━━━━━━━━━
Score : {score}/10  {stars}
Prix : {price:.4f} € | {change:+.2f}%

{reasons}

⏱️ Horizon : Moyen terme (1-4 semaines)
🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""


def format_risk_alert(data: dict) -> str:
    score = data["risk_score"]
    price = data["price"]
    change = data.get("change_1d", 0)
    reasons = "\n".join([f"  • {r}" for r in data["reasons_risk"]])
    fire = "🔥" * min(int(score / 2), 5)
    return f"""🔴 <b>HIGH RISK BET — {data['ticker']}</b>
━━━━━━━━━━━━━━━━━━━━
Score risque : {score}/10  {fire}
Prix : {price:.6f} € | {change:+.2f}%

{reasons}

⚡ Fenêtre : Court terme (heures / 1-2 jours)
💀 Joue uniquement ce que tu peux perdre
🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

# ──────────────────────────────────────────
# BOUCLE PRINCIPALE
# ──────────────────────────────────────────

def run_agent():
    print("=" * 50)
    print("  MARKET INTELLIGENCE AGENT — Démarré")
    print("=" * 50)

    send_telegram("🤖 <b>Agent démarré ✅</b>\nSurveillance : Actions US + FR + Crypto\n━━━━━━━━━━━━━━━━━━━━")

    smart_sent = set()
    risk_sent = set()

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scan en cours...")

        all_assets = []

        for ticker in US_STOCKS_SMART + FR_STOCKS_SMART + US_STOCKS_RISKY:
            result = analyze_stock(ticker)
            if result:
                all_assets.append(result)
            time.sleep(0.5)

        for coin in CRYPTO_IDS:
            result = analyze_crypto(coin)
            if result:
                all_assets.append(result)
            time.sleep(1.5)

        smart_candidates = sorted(
            [a for a in all_assets if a["smart_score"] >= 5 and a["reasons_smart"]],
            key=lambda x: x["smart_score"], reverse=True
        )
        for asset in smart_candidates[:3]:
            key = f"smart_{asset['ticker']}_{datetime.now().strftime('%Y%m%d')}"
            if key not in smart_sent:
                send_telegram(format_smart_alert(asset))
                smart_sent.add(key)

        risk_candidates = sorted(
            [a for a in all_assets if a["risk_score"] >= 6 and a["reasons_risk"]],
            key=lambda x: x["risk_score"], reverse=True
        )
        for asset in risk_candidates[:3]:
            key = f"risk_{asset['ticker']}_{datetime.now().strftime('%Y%m%d%H')}"
            if key not in risk_sent:
                send_telegram(format_risk_alert(asset))
                risk_sent.add(key)

        if not smart_candidates and not risk_candidates:
            print("[INFO] Aucun signal fort ce cycle.")

        if len(smart_sent) > 200:
            smart_sent.clear()
        if len(risk_sent) > 200:
            risk_sent.clear()

        print("[INFO] Prochain scan dans 1 heure...")
        time.sleep(3600)


if __name__ == "__main__":
    run_agent()

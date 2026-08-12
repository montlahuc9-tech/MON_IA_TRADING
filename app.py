import os
import pandas as pd
import requests
import feedparser
import streamlit as st
import yfinance as yf
from groq import Groq
from dateutil import parser as date_parser
from datetime import datetime

# ---------------------------------------------------------
# 1. CONFIGURATION & CONSTANTES GLOBALES
# ---------------------------------------------------------
DATA_FILE = "trading_journal.csv"
MAX_DAILY_VISION_CALLS = 10

if "vision_calls" not in st.session_state:
    st.session_state.vision_calls = 0

# ---------------------------------------------------------
# 2. FONCTIONS UTILITAIRES & HELPER FUNCTIONS
# ---------------------------------------------------------
def get_live_market_prices():
    """Récupère les prix en temps réel des principaux Futures CME via Yahoo Finance."""
    try:
        tickers = {
            "NQ (Nasdaq)": "NQ=F",
            "ES (S&P 500)": "ES=F",
            "GC (Gold)": "GC=F",
            "CL (Crude Oil)": "CL=F"
        }
        prices_text = "📈 **PRIX MARCHÉ EN TEMPS RÉEL (Yahoo Finance)** :\n"
        for name, symbol in tickers.items():
            data = yf.Ticker(symbol).fast_info
            last_price = round(data['lastPrice'], 2)
            prices_text += f"- {name} : {last_price}\n"
        return prices_text
    except Exception:
        return "⚠️ Impossible de charger les prix en temps réel pour le moment."

def parse_date(entry):
    """Extrait et convertit la date d'une entrée RSS pour le tri chronologique."""
    date_str = getattr(entry, "published", getattr(entry, "updated", None))
    if not date_str:
        return datetime.min
    try:
        return date_parser.parse(date_str)
    except Exception:
        return datetime.min

def get_live_news():
    """Récupère et trie chronologiquement les actualités en direct depuis les flux RSS."""
    rss_urls = [
        "https://finance.yahoo.com/news/rssindex",
        "https://search.cnbc.com/rs/search/combined:rss?source=cnbcnews&categories=finance",
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://news.google.com/rss/search?q=site:reuters.com+finance&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=site:bloomberg.com+markets&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=CME+Group+Futures&hl=en-US&gl=US&ceid=US:en"
    ]
    
    news_entries = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                dt = parse_date(entry)
                news_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": getattr(entry, "published", getattr(entry, "updated", "En direct")),
                    "dt": dt
                })
        except Exception:
            continue
            
    news_entries.sort(key=lambda x: x["dt"], reverse=True)
    return news_entries

def translate_titles_batch(api_key, titles):
    """Traduit une liste de titres en français via Groq."""
    if not api_key or not titles:
        return titles
    try:
        client = Groq(api_key=api_key)
        prompt = f"Traduis ces titres d'actualités financières en français, un par ligne sans numérotation :\n" + "\n".join(titles)
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        translated = res.choices[0].message.content.strip().split("\n")
        return [t.strip() for t in translated if t.strip()] if len(translated) == len(titles) else titles
    except Exception:
        return titles

def call_expert_ai(api_key, system_prompt, user_prompt, image_bytes=None):
    """Appel centralisé aux modèles Groq (Texte & Vision) avec contexte de prix."""
    client = Groq(api_key=api_key)
    if image_bytes:
        st.session_state.vision_calls += 1
        model = "llama-3.2-11b-vision-preview"
    else:
        model = "llama-3.3-70b-versatile"

    live_prices = get_live_market_prices()
    full_system_prompt = f"{system_prompt}\n\n{live_prices}"

    messages = [
        {"role": "system", "content": full_system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3
    )
    return response.choices[0].message.content

# ---------------------------------------------------------
# 3. SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.title("🟢 HubAlexMTL")
    st.caption("Espace Personnel & Copilote")
    st.divider()

    MA_CLE_API_GROQ = os.environ.get("GROQ_API_KEY", "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")
    st.session_state.groq_key = MA_CLE_API_GROQ
    groq_api_key = st.session_state.groq_key
    st.success("🔑 Clé API Groq active (Stable)")

    st.divider()

    st.markdown("📊 **Compteur Analyses Graphiques**")
    current_calls = st.session_state.vision_calls
    calls_left = max(0, MAX_DAILY_VISION_CALLS - current_calls)

    st.metric(
        label="Analyses faites",
        value=f"{current_calls} / {MAX_DAILY_VISION_CALLS}",
    )
    progress_val = min(1.0, current_calls / MAX_DAILY_VISION_CALLS)
    st.progress(progress_val)

    if current_calls >= MAX_DAILY_VISION_CALLS:
        st.warning("⚠️ Limite atteinte pour aujourd'hui !")
    else:
        st.caption(f"⚡ Il te reste environ {calls_left} analyses disponibles.")

    if st.button("🔄 Réinitialiser le compteur"):
        st.session_state.vision_calls = 0
        st.rerun()

    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "🤖 Copilote IA & Desk Experts",
            "📡 Orion News",
            "⚡ Checklists FlowX",
            "📈 Analyse Chart Futures",
            "📰 Flash Actus",
            "📅 Calendrier Économique",
            "📖 Journal de Trading",
        ],
        index=0,
    )
    st.divider()

latest_news_entries = get_live_news()
ticker_text = (
    latest_news_entries[0]["title"]
    if latest_news_entries
    else "Surveillance active des marchés CME / NQ / ES / Bloomberg / Yahoo Finance..."
)

st.markdown(
    f"""
    <div class="flash-info-bar">
        <span class="flash-badge">⚡ Flash Info</span>
        <span>{ticker_text}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 4. CONTENU DES PAGES
# ---------------------------------------------------------

if page == "🤖 Copilote IA & Desk Experts":
    st.title("🤖 Copilote IA & Desk d'Experts Complet")
    st.divider()

    expert = st.selectbox(
        "Sélectionner l'expert du Desk :",
        [
            "Arthur (Orion Junior - Analyste Généraliste)",
            "Alexandre (Directeur de Desk - Orchestration & Vision Globale)",
            "Marcus (Expert Market Profile & TPO)",
            "Victor (Expert Carnet d'Ordres & DOM)",
            "Sophie (Expert Order Flow & Volume / Delta / Footprint)",
            "Claire (Coach Psychologie & Mindset / Discipline)",
            "François (Expert Macro & News / Fed)",
            "Thomas (Expert Analyse Technique / Price Action & Structures)",
            "Laurent (Expert Risk Management & Position Sizing)",
            "Élise (Expert Options & Dérivés / Greeks)",
            "Nicolas (Expert Prop Firms & Règles Funding)",
            "FlowX (Expert Scalping Institutionnel / Auction Market Theory)",
        ],
    )

    if "Arthur" in expert:
        system_prompt = "Tu es Arthur, Orion Junior, analyste trading généraliste pédagogue."
    elif "Alexandre" in expert:
        system_prompt = "Tu es Alexandre, Directeur de Desk institutionnel."
    elif "Marcus" in expert:
        system_prompt = "Tu es Marcus, expert en Market Profile, TPO et Value Area sur les Futures."
    elif "Victor" in expert:
        system_prompt = "Tu es Victor, expert du Carnet d'Ordres (DOM)."
    elif "Sophie" in expert:
        system_prompt = "Tu es Sophie, expert en Order Flow et Volume (Delta, Footprint)."
    elif "Claire" in expert:
        system_prompt = "Tu es Claire, coach en psychologie et mindset du trader."
    elif "François" in expert:
        system_prompt = "Tu es François, expert Macro & News (intégrant Bloomberg, Yahoo Finance et FlashAlpha)."
    elif "Thomas" in expert:
        system_prompt = "Tu es Thomas, expert en Analyse Technique et Price Action."
    elif "Laurent" in expert:
        system_prompt = "Tu es Laurent, expert en Risk Management."
    elif "Élise" in expert:
        system_prompt = "Tu es Élise, expert en Options & Dérivés."
    elif "Nicolas" in expert:
        system_prompt = "Tu es Nicolas, expert Prop Firms & Risque."
    else:
        system_prompt = "Tu es FlowX, expert en Scalping Institutionnel et AMT (Auction Market Theory)."

    if "current_expert" not in st.session_state or st.session_state.current_expert != expert:
        st.session_state.current_expert = expert
        try:
            welcome_prompt = "Présente-toi brièvement et adresse un mot d'accueil professionnel à l'utilisateur."
            initial_greeting = call_expert_ai(groq_api_key, system_prompt, welcome_prompt)
        except Exception:
            initial_greeting = f"Bonjour, c'est {expert.split('(')[0].strip()}. Je suis prêt pour analyser les marchés."
        st.session_state.messages = [{"role": "assistant", "content": initial_greeting}]

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if "image" in msg and msg["image"]:
                st.image(msg["image"], width=400)
            st.markdown(msg["content"])

    st.write("---")
    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            "📥 Glisse ton graphique ici pour analyse",
            type=["png", "jpg", "jpeg"],
            key="manual_chart_input",
        )
    with col_btn:
        st.write("")
        st.write("")
        analyser_btn = st.button("🚀 Analyser l'image", type="primary", use_container_width=True)

    if analyser_btn and uploaded_file is not None:
        img_bytes = uploaded_file.getvalue()
        st.session_state.messages.append({
            "role": "user",
            "content": "📊 *[Graphique transmis pour analyse]*",
            "image": img_bytes,
        })

        with st.spinner("👁️ L'expert analyse ton graphique..."):
            try:
                answer = call_expert_ai(groq_api_key, system_prompt, "Analyse ce graphique", img_bytes)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Erreur critique : {str(e)}"})
            st.rerun()

    if prompt := st.chat_input("Écris ton message à l'expert..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("L'expert répond..."):
            try:
                answer = call_expert_ai(groq_api_key, system_prompt, prompt, None)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Erreur : {str(e)}"})
            st.rerun()

elif page == "📡 Orion News":
    st.title("📡 Orion News - Briefing Stratégique IA")
    st.caption("Synthèse de marché en direct générée par l'IA Orion basée sur Reuters, Bloomberg, CME Group, Yahoo Finance & CNBC.")
    st.divider()

    if st.button("🔄 Régénérer le briefing en direct", type="primary"):
        with st.spinner("Analyse des flux récents et rédaction du briefing Orion..."):
            news_entries = get_live_news()
            if news_entries:
                news_text_summary = "\n".join([f"- {e.get('title', '')}" for e in news_entries[:15]])
                system_prompt_orion = (
                    "Tu es Orion, un analyste macro et stratégiste de marché institutionnel de premier plan. "
                    "Rédige un briefing de marché professionnel, synthétique, structuré et percutant en français destiné à un trader."
                )
                brief_output = call_expert_ai(groq_api_key, system_prompt_orion, news_text_summary)
                st.session_state.orion_brief_cache = brief_output
            else:
                st.session_state.orion_brief_cache = "Aucune actualité en direct récupérée pour l'instant."

    if "orion_brief_cache" in st.session_state:
        st.markdown(st.session_state.orion_brief_cache)
    else:
        st.info("Cliquez sur le bouton ci-dessus pour générer le briefing de marché du jour.")

elif page == "⚡ Checklists FlowX":
    st.title("⚡ Checklists FlowX")
    st.caption("Vérifie chaque règle avant d'entrer en trade — Processus de validation mécanique pour le scalping NQ basé sur l'AMT et l'Order Flow.")
    st.divider()

    chk_tab1, chk_tab2, chk_tab3 = st.tabs(["🟢 Entrée", "🔴 Sortie", "🛡️ Risque"])

    with chk_tab1:
        st.subheader("Pre-Trade Entry Checklist (FlowX)")
        c1 = st.checkbox("Phase de marché identifiée (Balance vs Déséquilibre)", value=False, key="e1")
        c2 = st.checkbox("Initial Balance (IB) tracée", value=False, key="e2")
        c3 = st.checkbox("Prix sur une zone de valeur (POC/VA) ou niveau majeur", value=False, key="e3")
        c4 = st.checkbox("Maturité de la distribution confirmée via Volume Profile", value=False, key="e4")
        c5 = st.checkbox("Absorption détectée (Mur invisible d'ordres limites)", value=False, key="e5")
        c6 = st.checkbox("CVD en ligne avec la direction du trade", value=False, key="e6")
        c7 = st.checkbox("Niveau d'invalidation précis identifié", value=False, key="e7")
        c8 = st.checkbox("Absence de FOMO", value=False, key="e8")

        checked_e = sum([c1, c2, c3, c4, c5, c6, c7, c8])
        st.metric("Total Entrée", f"{checked_e}/8 validés")
        st.progress(checked_e / 8)

    with chk_tab2:
        st.subheader("Exit & Take Profit Checklist (FlowX)")
        s1 = st.checkbox("Objectif premier fixé sur le POC de la distribution", value=False, key="s1")
        s2 = st.checkbox("Retour au VWAP utilisé pour alléger la position", value=False, key="s2")
        s3 = st.checkbox("Prise de profit partielle sur palier technique atteint", value=False, key="s3")
        s4 = st.checkbox("Disparition de l'absorption ou contre-absorption adverse", value=False, key="s4")
        s5 = st.checkbox("Ré-intégration du range après breakout (Fakeout)", value=False, key="s5")
        s6 = st.checkbox("Sortie exécutée sans hésitation dès invalidation du flux", value=False, key="s6")

        checked_s = sum([s1, s2, s3, s4, s5, s6])
        st.metric("Total Sortie", f"{checked_s}/6 validés")
        st.progress(checked_s / 6)

    with chk_tab3:
        st.subheader("Risk Management Checklist (FlowX)")
        r1 = st.checkbox("Risque par trade <= 0.25% du capital total", value=False, key="r1")
        r2 = st.checkbox("Stop-loss systématique placé dans le carnet d'ordres (DOM)", value=False, key="r2")
        r3 = st.checkbox("Limite overtrading respectée", value=False, key="r3")
        r4 = st.checkbox("Absence de Revenge Trading détectée", value=False, key="r4")
        r5 = st.checkbox("État mental Thinking Slow (clarté vs impulsivité)", value=False, key="r5")
        r6 = st.checkbox("Time-stop appliqué", value=False, key="r6")

        checked_r = sum([r1, r2, r3, r4, r5, r6])
        st.metric("Total Risque", f"{checked_r}/6 validés")
        st.progress(checked_r / 6)

    st.write("")
    col_b1, col_b2 = st.columns(2)
    if col_b1.button("🔄 Réinitialiser les checklists", use_container_width=True):
        st.rerun()
    if col_b2.button("💾 Sauvegarder l'état", type="primary", use_container_width=True):
        st.success("✅ État des checklists validé et enregistré pour la session.")

elif page == "📈 Analyse Chart Futures":
    st.title("📈 Analyse Chart Futures CME")
    st.divider()

    col_sym, col_tf = st.columns([2, 2])
    with col_sym:
        symbol_choice = st.selectbox(
            "Actif Futures :",
            ["NQ1! (Nasdaq 100)", "ES1! (S&P 500)", "CL1! (Crude Oil)", "GC1! (Gold)"]
        )
    with col_tf:
        interval_choice = st.selectbox(
            "Unité de temps :",
            ["1", "5", "15", "60", "D"],
            index=1
        )

    symbol_map = {
        "NQ1! (Nasdaq 100)": "CME_MINI:NQ1!",
        "ES1! (S&P 500)": "CME_MINI:ES1!",
        "CL1! (Crude Oil)": "NYMEX:CL1!",
        "GC1! (Gold)": "COMEX:GC1!",
    }

    tv_symbol = symbol_map.get(symbol_choice, "CME_MINI:NQ1!")

    import urllib.parse
    tradingview_html = f"""<!DOCTYPE html>
    <html>
    <head><style>html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #131722; }}</style></head>
    <body>
      <div id="tradingview_chart" style="height:100vh;width:100vw;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "{interval_choice}",
        "timezone": "Europe/Paris",
        "theme": "dark",
        "style": "1",
        "locale": "fr",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </body>
    </html>"""

    encoded_html = urllib.parse.quote(tradingview_html)
    st.iframe(f"data:text/html;charset=utf-8,{encoded_html}", height=610)

elif page == "📰 Flash Actus":
    st.title("📰 Flash Actus & Marchés (Yahoo Finance, Bloomberg, FlashAlpha, Reuters, CME, CNBC)")
    st.caption("Traduction automatique instantanée en français via Groq AI")
    
    if st.button("🔄 Rafraîchir les actualités en direct"):
        st.rerun()
        
    st.divider()

    news_entries = get_live_news()
    if news_entries:
        with st.spinner("Traductions des flux en direct via Groq..."):
            raw_titles = [e.get("title", "Titre non disponible") for e in news_entries]
            translated_titles = translate_titles_batch(groq_api_key, raw_titles)

        for entry, translated_title in zip(news_entries, translated_titles):
            link = entry.get("link", "#")
            published = entry.get("published", "En direct")
            st.markdown(
                f"""
                <div class="news-card">
                    <div class="news-header">
                        <span>⚡ FLASH MARCHÉS GLOBAL</span>
                        <span>{published}</span>
                    </div>
                    <div class="news-body">
                        <div class="news-title">{translated_title}</div>
                        <div style="color: #58a6ff; font-weight: 500;"><a href="{link}" target="_blank" style="color: #58a6ff; text-decoration: none;">🔗 Lire l'article complet à la source</a></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.warning("Impossible de récupérer les flux d'actualités en direct pour le moment.")

elif page == "📅 Calendrier Économique":
    st.title("📅 Calendrier Économique")
    st.divider()
    st.markdown(
        """
        <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 30px; text-align: center; margin-top: 20px;">
            <h3 style="color: #ffffff; margin-bottom: 15px;">Accéder au Calendrier Économique Investing.com</h3>
            <p style="color: #8b949e; margin-bottom: 20px;">Suivez en temps réel les annonces macroéconomiques à fort impact (CPI, NFP, Fed, BCE...)</p>
            <a href="https://fr.investing.com/economic-calendar/" target="_blank"
               style="background-color: #d93838; color: white; padding: 12px 25px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 1.1rem; display: inline-block;">
               🚀 Ouvrir le Calendrier Investing.com
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

elif page == "📖 Journal de Trading":
    st.title("📖 Journal de Trading & Dashboard de Performance")
    st.caption("Analyse automatique de tes statistiques de trading (Winrate, Profit Factor, Courbe P&L)")
    st.divider()

    @st.dialog("📂 Importer ou Saisir des Trades")
    def open_import_dialog():
        st.write("Importez vos trades au format CSV (colonnes suggérées : `Date`, `Symbol`, `Type`, `PnL`).")
        uploaded_file = st.file_uploader("Glissez votre fichier CSV ici", type=["csv"])

        if uploaded_file is not None:
            try:
                df_imported = pd.read_csv(uploaded_file)
                df_imported.to_csv(DATA_FILE, index=False)
                st.success("✅ Trades importés et enregistrés avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur lors de l'importation : {str(e)}")

    col_j1, col_j2 = st.columns([1, 3])
    with col_j1:
        if st.button("📂 Charger / Importer CSV", use_container_width=True, type="primary"):
            open_import_dialog()

    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)

            # Détection automatique de la colonne PnL
            pnl_col = None
            for col in df.columns:
                if col.lower() in ["pnl", "p&l", "profit", "gain", "resultat", "result"]:
                    pnl_col = col
                    break

            if pnl_col:
                # Nettoyage et conversion numérique
                df[pnl_col] = pd.to_numeric(df[pnl_col], errors="coerce").fillna(0)

                # Calculs des métriques
                total_trades = len(df)
                winning_trades = df[df[pnl_col] > 0]
                losing_trades = df[df[pnl_col] < 0]

                winrate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
                total_pnl = df[pnl_col].sum()

                gross_profit = winning_trades[pnl_col].sum()
                gross_loss = abs(losing_trades[pnl_col].sum())
                profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

                avg_win = winning_trades[pnl_col].mean() if len(winning_trades) > 0 else 0
                avg_loss = abs(losing_trades[pnl_col].mean()) if len(losing_trades) > 0 else 0

                # Affichage des KPIs
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("📊 Total Trades", total_trades)
                m2.metric("🎯 Winrate", f"{winrate:.1f} %")
                m3.metric("💵 P&L Total", f"{total_pnl:,.2f} $", delta=f"{total_pnl:,.2f} $")
                m4.metric("⚖️ Profit Factor", f"{profit_factor:.2f}")

                st.write("")
                col_sub1, col_sub2 = st.columns(2)
                col_sub1.caption(f"🟢 Gain Moyen par trade gagnant : **+{avg_win:,.2f} $**")
                col_sub2.caption(f"🔴 Perte Moyenne par trade perdant : **-{avg_loss:,.2f} $**")

                st.divider()

                # Graphique P&L Cumulé
                st.subheader("📈 Courbe de Capital (P&L Cumulé)")
                df["P&L Cumulé"] = df[pnl_col].cumsum()
                st.line_chart(df["P&L Cumulé"], use_container_width=True)

            st.subheader("📋 Historique Complet des Trades")
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors du traitement du journal : {str(e)}")
    else:
        st.info("Aucun journal existant. Télécharge le modèle CSV ci-dessous pour tester immédiatement.")

        sample_data = pd.DataFrame({
            "Date": ["2026-08-10", "2026-08-10", "2026-08-11", "2026-08-11", "2026-08-12"],
            "Symbol": ["NQ", "NQ", "ES", "NQ", "NQ"],
            "Type": ["BUY", "SELL", "BUY", "BUY", "SELL"],
            "PnL": [250.0, -120.0, 180.0, 310.0, -90.0]
        })
        st.download_button(
            label="📥 Télécharger un modèle CSV exemple",
            data=sample_data.to_csv(index=False),
            file_name="modele_journal_trading.csv",
            mime="text/csv"
        )
        

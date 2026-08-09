import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser
from groq import Groq

# 1. Récupération des identifiants sécurisés
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def get_live_news():
    urls = [
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://search.cnbc.com/rs/search/combinedrender?source=yahoo&partner=0&output=rss"
    ]
    all_entries = []
    for url in urls:
        feed = feedparser.parse(url)
        all_entries.extend(feed.entries)
    return all_entries

def generate_brief():
    news_entries = get_live_news()
    summary_input = "\n".join([f"- {e.get('title', '')}" for e in news_entries[:12]])
    
    system_prompt = (
        "Tu es Orion, un analyste macro et stratégiste de marché institutionnel. "
        "Rédige un briefing de marché complet, percutant et professionnel en français pour la session du jour. "
        "Formate TOUT le contenu en HTML propre sans utiliser de syntaxe Markdown (pas de **, pas de #). "
        "Utilise uniquement des balises HTML : <h3> pour les titres de section, <p> pour le texte, "
        "<strong> pour mettre en valeur les mots importants, et <ul>/<li> pour les listes. "
        "N'inclus ni balise <html>, <body>, ni blocs de code ```html."
    )
    
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": summary_input}
        ],
        temperature=0.3,
        max_tokens=1024
    )
    return response.choices[0].message.content

def send_email(subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #e1e4e8;">
            <div style="background-color: #0f172a; color: #ffffff; padding: 20px 25px;">
                <h1 style="margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px;">⚡ BRIEFING STRATÉGIQUE ORION</h1>
            </div>
            <div style="padding: 25px; color: #334155; line-height: 1.6; font-size: 15px;">
                {html_content}
            </div>
            <div style="background-color: #f8fafc; padding: 15px 25px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; text-align: center;">
                Généré automatiquement par Orion AI • Macro Trading Brief
            </div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(full_html, 'html', 'utf-8'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    server.quit()

if __name__ == "__main__":
    print("Génération du brief Orion...")
    brief_content = generate_brief()
    print(f"Envoi du mail HTML à {RECIPIENT_EMAIL}...")
    send_email("⚡ Briefing Stratégique Orion News du Matin", brief_content)
    print("✅ E-mail envoyé avec succès !")

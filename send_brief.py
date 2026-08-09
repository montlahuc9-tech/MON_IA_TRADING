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
        "Rédige un briefing de marché complet, percutant et professionnel en français pour la session du jour."
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

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    server.quit()

if __name__ == "__main__":
    print("Génération du brief Orion...")
    brief_content = generate_brief()
    print(f"Envoi du mail à {RECIPIENT_EMAIL}...")
    send_email("⚡ Briefing Stratégique Orion News du Matin", brief_content)
    print("✅ E-mail envoyé avec succès !")

import os
import re
import glob
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from sentence_transformers import SentenceTransformer

# Zorg dat je de NLTK stopwoorden hebt gedownload
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# Laad een voorgetrainde SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')


def clean_text(text):
    """
    Verwijdert HTML-tags, speciale tekens en stopwoorden en zet de tekst om naar lowercase.
    """
    # Verwijder HTML tags
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(separator=' ')
    # Verwijder speciale tekens (laat alleen letters en spaties over)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    # Zet om naar lowercase
    text = text.lower()
    # Tokeniseer en filter stopwoorden
    words = text.split()
    words = [w for w in words if w not in stop_words]
    cleaned = ' '.join(words)
    return cleaned


def process_article_file(file_path, output_base):
    """
    Leest een artikelbestand, verwijdert de header (behalve de titel), controleert of de
    tekst beschikbaar is en schrijft de genormaliseerde tekst naar de output folder.
    Daarnaast wordt er een embedding vector berekend en opgeslagen.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Splits de header van de tekst; we gaan er vanuit dat de header en de tekst gescheiden zijn door een lege regel
    parts = content.split('\n\n', 1)
    if len(parts) < 2:
        return  # Geen duidelijke scheiding, overslaan

    header, body = parts
    # Als het artikel de placeholder bevat, dan overslaan
    if "No article text available." in body:
        return

    # Haal de titel op uit de header (alleen de regel die met "Title:" begint)
    title = ""
    for line in header.splitlines():
        if line.startswith("Title:"):
            title = line[len("Title:"):].strip()
            break

    # Combineer de titel met de rest van de tekst
    full_text = title + "\n" + body

    # Normaliseer de tekst
    cleaned_text = clean_text(full_text)

    # Bereken de embedding vector
    vector = model.encode(cleaned_text)

    # Bepaal de output pad, behoud de subdirectory-structuur
    relative_path = os.path.relpath(file_path, "data")
    output_path = os.path.join(output_base, relative_path)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Schrijf de genormaliseerde tekst weg
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)

    # Sla de vector op in een parallel bestand (bijvoorbeeld met dezelfde naam + .vec)
    vec_output_path = output_path + ".vec"
    vec_str = ",".join(map(str, vector))
    with open(vec_output_path, 'w', encoding='utf-8') as f:
        f.write(vec_str)


def process_all_articles(input_base="data", output_base="./articles_normalised"):
    """
    Loopt over alle bestanden in de input_base directory en verwerkt ze.
    """
    for root, dirs, files in os.walk(input_base):
        for file in files:
            # Veronderstel dat alle artikelbestanden .txt-extensie hebben
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                process_article_file(file_path, output_base)


if __name__ == "__main__":
    process_all_articles()


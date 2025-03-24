
# AI Trend Analyse en Topic Rapportage

  

Dit project voert een trendanalyse uit op AI-gerelateerde artikelen en genereert een rapport waarin per topic:

  

- Een titel wordt gegenereerd per topic.

- Belangrijke en trending termen worden weergegeven.

- De maandelijkse puntenverdeling per term én de daadwerkelijke groei (growth) per term worden getoond.

- Alle representatieve documenten (fragmenten) worden meegenomen.

- De artikeltitels worden geëxtraheerd door de eerste 150 karakters van elk artikel te lezen.

- Een kritische relevantie-analyse wordt gegeven, met aandacht voor technische kansen, risico’s voor burgers en mogelijke veranderingen in wet- en regelgeving.

  

## Inhoud

  

-  **trend_analysis.py**

Voert de initiële data‑invoer en clustering uit. De trendanalyse berekent per term de maandelijkse scores en de groei over de periode.

  

-  **llm_analysis.py**

Verwerkt de resultaten per topic en bouwt een uitgebreide prompt voor de LLM. De prompt bevat:

- De top 10 termen en de top 5 trending woorden.

- Alle representatieve fragmenten.

- De artikeltitels (eerste 150 karakters van elk artikel).

- De maandelijkse distributie en de groei per term (via de meegeleverde trend_info).

- Een instructie om een titel te genereren voor het topic en kritisch te analyseren.

  

-  **main.py**

Het hoofdscript dat:

- De argumenten leest (inclusief start- en einddatum).

- Éénmalig de trendanalyse uitvoert via `run_analysis` en de resultaten doorgeeft aan de LLM-analyse.

- Een HTML-rapport genereert en opslaat in een submap `output` met een bestandsnaam in de vorm `html_output_<start_date>_<end_date>.html`.

  

## Hoe te gebruiken

  

1.  **Voorbereiding:**

- Zorg dat je een `.env`-bestand hebt met je `OPENAI_API_KEY`.

- Zorg dat de mappen met artikelen (`vec_dir`) en de scraper CSV-bestanden (`scraper_dir`) beschikbaar zijn. Dit wordt duidelijk in de volgende stap.

  

2.  **Data ophalen:**

Je hebt twee opties om de benodigde data te verkrijgen:

-  **Optie 1:** Voer het shell-script `run_all.sh` uit. Dit script maakt automatisch de map `./data` aan (indien deze niet bestaat), haalt de artikelen op (via `pull_articles.py`), en normaliseert ze (via `normalize.py`). Hiervoor moet wel een Google Cloud account aangemaakt zijn om queries uit te kunnen voeren op de Google BigQuery dataset [Google BigQuery link](https://cloud.google.com/bigquery/public-data).

Zorg ervoor dat het script uitvoerbaar is (bijvoorbeeld met `chmod +x run_all.sh`), en run het met:

```

./run_all.sh

```

-  **Optie 2:** Download de data rechtstreeks vanaf deze [Google Drive link](https://drive.google.com/drive/folders/15yV3BI1rbiSRpj8W2CiTickdhF6WmmUy?usp=sharing) om tijd te besparen. Achter deze link zitten twee mappen die gewoon in de rootfolder geplaatst kunnen worden.

  

3.  **Uitvoeren:**

Run het hoofdscript met de benodigde argumenten, bijvoorbeeld:

```

python main.py --start_date 2023-01-01 --end_date 2023-01-31 --verbose

```

**Tip:** Als het script niet werkt, kun je altijd de `--help` flag gebruiken om de beschikbare opties te bekijken:

```

python main.py --help

```

  

Na uitvoering wordt een HTML-rapport gegenereerd in de submap `output` met een naam als `html_output_2023-01-01_2023-01-31.html`. Het rapport bevat voor elk topic:

  

- De door de LLM gegenereerde titel.

- Belangrijke en trending termen.

- Een trend samenvatting en een kritische relevantieverklaring.

- De artikeltitels (eerste 150 karakters per artikel).

- De maandelijkse puntenverdeling en de groei per term.

  

## Installatie

  

1.  **Externe dependencies installeren:**

Alle niet-standaard pakketten die dit project gebruikt, staan in het bestand `requirements.txt`. Installeer deze met:

```

pip install -r requirements.txt

```

  

2.  **NLTK-data downloaden:**

Het project maakt gebruik van NLTK. Zorg ervoor dat de benodigde NLTK-resources worden gedownload (dit gebeurt automatisch bij de eerste uitvoering of via een aparte downloadroutine).

  

## Opmerkingen

  

- Dit project ondersteunt de AI Lab activiteiten van de gemeente Amsterdam door opkomende trends in kaart te brengen.

- De LLM-analyse maakt gebruik van de GPT-4 API. Houd rekening met je API-credits en zorg voor een geldige `OPENAI_API_KEY`.

- Alle analyse-stappen worden slechts één keer uitgevoerd om redundantie te voorkomen.

- Twee voorbeeld analyses zitten in de output-map.

  

## Aannames

  

- Het hoofdscript gaat ervan uit dat de benodigde data reeds op de harde schijf aanwezig is. In een productieomgeving kan er een dagelijkse job ingericht worden die continu de nieuwste data ophaalt en bijwerkt.

- Het script moet altijd gerund worden met een gespecificeerde date range. Aangezien de opdracht per kwartaalrapporten verlangt, kan dit script gebruikt worden door per kwartaal de juiste start- en einddatum op te geven.

- Als het script niet direct werkt, is het altijd een goed idee om de `--help` flag te gebruiken voor meer informatie over de beschikbare opties.
- De punten overzicht is gebaseerd op het aantal punten wat per topic door gebruikers van hackernews aan artikelen wordt toegekend. Dit zou mooier zijn in een grafiek maar daar was geen tijd voor.
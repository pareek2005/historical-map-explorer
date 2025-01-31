from flask import Flask, render_template, jsonify, request
import requests
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def extract_year_mentions(text):
    # Match years like 500 BCE, 500 BC, 500CE, 500 CE, etc.
    year_pattern = r'\b(\d{1,4})\s*(BC|BCE|AD|CE)?\b'
    matches = re.finditer(year_pattern, text, re.IGNORECASE)
    years = []

    for match in matches:
        year_str = match.group()
        # Convert to negative years for BCE/BC
        if re.search(r'BC|BCE', year_str, re.IGNORECASE):
            year = -int(''.join(filter(str.isdigit, year_str)))
        else:
            year = int(''.join(filter(str.isdigit, year_str)))
        years.append(year)

    return sorted(years)

def get_article_views(pageid):
    endpoint = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{pageid}/daily/20220101/20221231"
    headers = {
        "User-Agent": "HistoricalMapExplorer/1.0 (challengepareek@gmail.com)"
    }
    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        views = sum(item['views'] for item in data.get('items', []))
        return views
    except requests.RequestException as e:
        logger.error(f"Error in fetching page views for article {pageid}: {e}")
        return 0

def get_wikipedia_articles(lat, lng, start_year, end_year, radius=10000, min_views=1000):
    endpoint = "https://en.wikipedia.org/w/api.php"
    headers = {
        "User-Agent": "HistoricalMapExplorer/1.0 (challengepareek@gmail.com)"
    }

    # Filter for specific historical events like battles or treaties
    params = {
        "action": "query",
        "format": "json",
        "list": "geosearch",
        "gscoord": f"{lat}|{lng}",
        "gsradius": radius,
        "gslimit": 50,
        "gsprop": "type|globe|name"
    }

    try:
        response = requests.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        articles = data.get("query", {}).get("geosearch", [])
        logger.debug(f"Found {len(articles)} nearby articles")

        if not articles:
            return []

        # Get full content and filter for historical events
        enriched_articles = []
        for article in articles:
            content_params = {
                "action": "query",
                "format": "json",
                "pageids": article["pageid"],
                "prop": "extracts|categories",
                "explaintext": True,
                "exintro": True,
                "cllimit": "max"
            }

            content_response = requests.get(endpoint, params=content_params, headers=headers)
            content_response.raise_for_status()
            content_data = content_response.json()

            if 'query' in content_data and 'pages' in content_data['query']:
                page_data = content_data['query']['pages'][str(article["pageid"])]
                if "extract" in page_data:
                    views = get_article_views(article["title"].replace(" ", "_"))
                    if views >= min_views:
                        extract = page_data["extract"]
                        years_mentioned = extract_year_mentions(extract)
                        relevant_years = [year for year in years_mentioned if start_year <= year <= end_year]

                        if relevant_years:
                            enriched_articles.append({
                                "title": article["title"],
                                "pageid": article["pageid"],
                                "lat": article["lat"],
                                "lon": article["lon"],
                                "distance": round(article["dist"], 2),
                                "extract": extract[:500] + "..." if len(extract) > 500 else extract,
                                "url": f"https://en.wikipedia.org/wiki?curid={article['pageid']}",
                                "years_mentioned": relevant_years,
                                "views": views
                            })
                            logger.debug(f"Article {article['title']} has {views} views and mentions years: {relevant_years}")

        logger.debug(f"Found {len(enriched_articles)} articles with relevant historical events and views >= {min_views}")
        enriched_articles.sort(key=lambda x: x["distance"])
        return enriched_articles[:25]

    except requests.RequestException as e:
        logger.error(f"Error in Wikipedia API request: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/articles')
def get_articles():
    try:
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))

        start_year = request.args.get('startYear', '3000 BCE')
        end_year = request.args.get('endYear', '2024 CE')

        # Convert BCE/CE years to numbers (BCE as negative)
        start_year = -int(start_year.replace(' BCE', '')) if 'BCE' in start_year else int(start_year.replace(' CE', ''))
        end_year = -int(end_year.replace(' BCE', '')) if 'BCE' in end_year else int(end_year.replace(' CE', ''))

        logger.debug(f"Searching for articles between years {start_year} and {end_year}")
        articles = get_wikipedia_articles(lat, lng, start_year, end_year)
        return jsonify(articles)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

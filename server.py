import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

desired_locations_set = {
    'albuquerque, new mexico',
    'carlsbad, california',
    'chula vista, california',
    'colorado springs, colorado',
    'denver, colorado',
    'el cajon, california',
    'el paso, texas',
    'escondido, california',
    'fresno, california',
    'la mesa, california',
    'las vegas, nevada',
    'los angeles, california',
    'oceanside, california',
    'phoenix, arizona',
    'sacramento, california',
    'salt lake city, utah',
    'san diego, california',
    'tucson, arizona'
}

date_format = "%Y-%m-%d"


class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass


    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores


    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")

            # Write your code here
            # The GET method should allow for two parameters Location and Timestamp
            # that filters the results when the parameters are included. GET should return a JSON object 

            # ex: location=Salt+Lake+City%2C+Utah&start_date=2021-01-01&end_date=2021-12-31
            url_query_string = environ['QUERY_STRING']
            
            if url_query_string:
                
                parsed_qs = parse_qs(url_query_string)
                query_location = parsed_qs.get('location', [None])[0]
                query_start_date = parsed_qs.get('start_date', [None])[0]
                query_end_date = parsed_qs.get('end_date', [None])[0]

                query_start_date_obj = datetime.strptime(query_start_date, date_format) if query_start_date else None
                query_end_date_obj = datetime.strptime(query_end_date, date_format) if query_end_date else None

                filtered_reviews = []
                for review in reviews:
                    review_date = datetime.strptime(review['Timestamp'], "%Y-%m-%d %H:%M:%S") # "Timestamp": "2021-10-21 6:09:40",
            
                    # filter on location
                    if query_location and query_location.strip().lower() != review['Location'].strip().lower():
                        continue
                    if query_location and query_location.strip().lower() not in desired_locations_set:
                        continue
                    if query_start_date_obj and review_date < query_start_date_obj:
                        continue
                    if query_end_date_obj and review_date > query_end_date_obj:
                        continue
                    review['sentiment'] = self.analyze_sentiment(review['ReviewBody'])
                    filtered_reviews.append(review)

                # now we sort the filtered reviews based on compound sentiment score
                filtered_reviews.sort(key=lambda x: x['sentiment']['compound'], reverse=True)

                response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here

            # Post should accept two parameters, ReviewBody and Location , both are text strings.
            # Each post should add a Timestamp for when the review was added using datetime and a
            # ReviewId using uuid which are already included in the import statements.
            
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            
            # Read the raw request body if content length is greter than 0
            raw_data = environ['wsgi.input'].read(content_length) if content_length > 0 else b''

            data_str = raw_data.decode('utf-8')
            data_parsed = parse_qs(data_str)

            location = data_parsed.get("Location", [None])[0]
            review_body = data_parsed.get("ReviewBody", [None])[0]

            if not location or not review_body:
                status = '400 Bad Request'
                start_response(status, [
                    ("Content-Type", "application/json"),
                    ])
                response_body = json.dumps({"error": "No location or body"}, indent=2).encode("utf-8")
                return [response_body]

            if location.lower().strip() not in desired_locations_set:
                status = '400 Bad Request'
                start_response(status, [
                    ("Content-Type", "application/json"),
                    ])
                response_body = json.dumps({"error": "Not a desired location"}, indent=2).encode("utf-8")
                return [response_body]

            # create a entry
            new_review = {
                "ReviewId": str(uuid.uuid4()),
                "ReviewBody": review_body,
                "Location": location,
                "Timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            response_body = json.dumps(new_review, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("201 Created", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()
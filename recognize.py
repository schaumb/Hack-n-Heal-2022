import os
import sys
import requests

if __name__ == '__main__':
    while True:
        line = sys.stdin.readline().strip().replace('ö', '0')

        import requests

        url = "https://google-search3.p.rapidapi.com/api/v1/search/q=site:https://pingvinpatika.hu%20" + line

        headers = {
            "X-User-Agent": "mobile",
            "X-Proxy-Location": "EU",
            "X-RapidAPI-Host": "google-search3.p.rapidapi.com",
            "X-RapidAPI-Key": os.environ['API_KEY']
        }

        response = requests.request("GET", url, headers=headers)

        print(response.json()['results'][0]['title'].split(' - ')[0].strip())

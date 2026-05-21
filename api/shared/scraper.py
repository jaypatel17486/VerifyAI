import requests
from bs4 import BeautifulSoup

def extract(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)

    soup = BeautifulSoup(res.text, "html.parser")

    for tag in soup(["script", "style"]):
        tag.extract()

    text = soup.get_text()
    return " ".join(text.split())[:3000]
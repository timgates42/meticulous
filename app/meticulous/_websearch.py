"""
Use the internet to determine if the provided word is a nonword or a typo
"""

from urllib.parse import quote

from bs4 import BeautifulSoup

import requests


def get_suggestion(word):
    """
    Use the internet to determine if the provided word is a nonword or a typo
    """
    search = f"https://www.google.com.au/search?q={quote(word)}"
    page = requests.get(search).text
    soup = BeautifulSoup(page)
    return "\n\n\n".join(elem.prettify() for elem in soup.find_all('div'))


if __name__ == "__main__":
    print(get_suggestion("catenate"))

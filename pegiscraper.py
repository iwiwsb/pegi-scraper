from argparse import ArgumentParser, Namespace
import math
import csv
import os
from typing import Dict
import requests
from bs4 import BeautifulSoup, Tag, ResultSet
from requests.sessions import Session


def main():
    delimiters: Dict[str, str] = {'comma': ",",
                                  'tab': "\t",
                                  'colon': ":",
                                  'semicolon': ";",
                                  'pipe': "|"}
    parser: ArgumentParser = ArgumentParser(description="Scrape videogame data from PEGI website")
    parser.add_argument("--delimiter",
                        default="comma",
                        type=str,
                        choices=delimiters.keys(),
                        required=False,
                        help="Delimiter will be used in csv file. The default is comma.")
    parser.add_argument("path", type=str, help="Path where to save file.")

    args: Namespace = parser.parse_args()
    s: Session = requests.Session()
    s.headers.update({
        "Referer": "https://pegi.info/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0"
    })

    url: str = ("https://pegi.info/search-pegi?q=&filter-age%%5B0%%5D=&filter-descriptor%%5B0%%5D=&filter-publisher="
                "&filter-platform%%5B0%%5D=&filter-release-year%%5B0%%5D=&page={}")

    first_page_html: str = get_page_html(s, url, 1)
    first_page_soup: BeautifulSoup = BeautifulSoup(first_page_html, features="lxml")
    pages_count: int = get_pages_count(first_page_soup)
    pages_range = range(1, pages_count + 1)

    with open(args.path, "w", encoding="utf8", newline="", buffering=1) as csvfile:
        fieldnames = ['"game_title"',
                      '"publisher"',
                      '"release_date"',
                      '"platforms"',
                      '"rating"',
                      '"descriptors"',
                      '"website"']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=delimiters[args.delimiter])
        writer.writeheader()
        for page in pages_range:
            if page == 1:
                soup = first_page_soup
            else:
                search_results = get_page_html(s, url, page)
                soup = BeautifulSoup(search_results, features="lxml")
            games_list = get_games_list(soup)
            for game in games_list:
                game_title = get_title(game)
                publisher = get_publisher(game)
                release_date = get_release_date(game)
                platforms = get_platforms(game)
                rating = get_rating(game)
                descriptors = get_descriptors(game)
                website = get_website(game)
                values = [game_title,
                          publisher,
                          release_date,
                          platforms,
                          rating,
                          descriptors,
                          website]
                entry = dict(zip(fieldnames, values))
                writer.writerow(entry)
            progress_percent = page / pages_count * 100
            print("\rParsed {}/{} pages ({:.2}%)".format(page, pages_count, progress_percent), end="")


def get_page_html(session: Session, url: str, page_number: int) -> str:
    """

    :rtype: str
    """
    return session.get(url.format(page_number)).text


def get_pages_count(soup: BeautifulSoup) -> int:
    """

    :rtype: object
    """
    results_count = int(soup.find("div", {"class": "results-count"}).find("strong").text.strip("results"))
    pages_count = math.floor(results_count / 10)
    return pages_count


def get_filename(path: str) -> str:
    return os.path.split(path)[1]


def get_games_list(soup: BeautifulSoup) -> ResultSet:
    return soup.find("div", {"class": "page-content"}).find_all("article", {"class": "game"})


def get_title(game: Tag) -> str:
    return game.find("div", {"class": "info"}).find("h3").text


def get_release_date(game: Tag) -> str:
    date = game.find("span", {"class": "release-date"}).text.lstrip("\nRelease Date:")
    day, month, year = date.split("/")
    return str(year + '-' + month + '-' + day)


def get_platforms(game: Tag):
    return game.find("span", {"class": "platform"}).text.split(":")[1]


def get_rating(game: Tag):
    pegi_ratings = {"pegi3": 3,
                    "pegi7": 7,
                    "pegi12": 12,
                    "pegi16": 16,
                    "pegi18": 18}
    filepath = game.find("div", {"class": "age-rating"}).find("img").get("src")
    key = get_filename(filepath).rstrip(".png")
    return pegi_ratings[key]


def get_descriptors(game: Tag) -> str:
    pegi_descriptors = {"bad_language": "Bad Language",
                        "discrimination": "Discrimination",
                        "drugs": "Drugs",
                        "fear": "Fear",
                        "horror": "Horror",
                        "gambling": "Gambling",
                        "in-game_purchases": "In-Game Purchases",
                        "sex": "Sex",
                        "violence": "Violence"}

    descriptors_list = []
    descriptors = game.find("div", {"class": "descriptors"}).find_all("img")

    for descriptor in descriptors:
        key = get_filename(descriptor.get("src")).split(".")[0]
        if key not in ("", None):
            descriptors_list.append(pegi_descriptors[key])
        else:
            descriptors_list.append("")
    return ", ".join(descriptors_list)


def get_publisher(game: Tag) -> str:
    return game.find("span", {"class": "publisher"}).text


def get_website(game: Tag) -> str:
    url = ""
    website = game.find("div", {"class": "info"}).find("span", {"class": "website-info"})
    if website is not None:
        url = website.find("a")["href"]
    return url


if __name__ == "__main__":
    main()

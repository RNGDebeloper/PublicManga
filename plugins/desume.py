import json
import re
from dataclasses import dataclass
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from aiohttp import ClientResponse
from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


@dataclass
class DesuMeMangaCard(MangaCard):
    read_url: str

    def get_url(self):
        return self.read_url


@dataclass
class DesuMeMangaChapter(MangaChapter):
    read_url: str

    def get_url(self):
        return self.read_url


class DesuMeClient(MangaClient):

    base_url = urlparse('https://desu.me/')
    search_url = urljoin(base_url.geturl(), 'manga/api/')
    search_param = 'search'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name='DesuMe', **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        dt = json.loads(page)
        mangas = dt['response']

        names = [manga.get('russian') for manga in mangas]
        url = [f"https://desu.me/manga/api/{manga.get('id')}" for manga in mangas]
        images = [manga.get('image').get('preview') for manga in mangas]
        read_url = [manga.get('url') for manga in mangas]

        mangas = [DesuMeMangaCard(self, *tup) for tup in zip(names, url, images, read_url)]

        return mangas

    def chapters_from_page(self, content: bytes, manga: DesuMeMangaCard = None):
        dt = json.loads(content)
        chapters = dt['response'].get('chapters').get('list')

        links = [f"{manga.url}/chapter/{chapter.get('id')}" for chapter in chapters]
        texts = [f"{chapter.get('vol')} - {chapter.get('ch')} {str(chapter.get('title') or '')}".strip() for chapter in chapters]
        read_url = [f"{manga.read_url}vol{chapter.get('vol')}/ch{chapter.get('ch')}/rus" for chapter in chapters]

        return list(map(lambda x: DesuMeMangaChapter(self, x[0], x[1], manga, [], x[2]), zip(texts, links, read_url)))

    def updates_from_page(self, page: bytes):
        raise NotImplementedError

    async def pictures_from_chapters(self, content: bytes, response: ClientResponse = None):
        dt = json.loads(content)
        pages = dt['response'].get('pages').get('list')

        images_url = [page.get('img') for page in pages]

        return images_url

    async def search(self, query: str = '', page: int = 1) -> List[DesuMeMangaCard]:
        request_url = self.search_url

        if query:
            request_url += f'?limit=20&page={page}&order=popular&{self.search_param}={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: DesuMeMangaCard, page: int = 1) -> List[DesuMeMangaChapter]:
        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[DesuMeMangaChapter]:
        manga_card = DesuMeMangaCard(self, manga_name, manga_url, '', '')

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        for ch in self.chapters_from_page(content, manga_card):
            yield ch

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):
        raise NotImplementedError

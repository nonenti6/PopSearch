"""Необязательные обложки альбомов из каталога iTunes; факты хранятся в PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import re
import requests


def normalize(value):
    return re.sub(r'[^\w]+', '', (value or '').casefold(), flags=re.UNICODE)


@lru_cache(maxsize=512)
def find_album_art(artist, album):
    try:
        response = requests.get(
            'https://itunes.apple.com/search',
            params={'term': f'{artist} {album}', 'media': 'music', 'entity': 'album', 'limit': 25, 'country': 'US'},
            timeout=3,
            headers={'User-Agent': 'PopSearchCourseProject/1.0'},
        )
        response.raise_for_status()
        for candidate in response.json().get('results', []):
            if (normalize(candidate.get('collectionName')) == normalize(album)
                and normalize(candidate.get('artistName')) == normalize(artist)):
                cover = candidate.get('artworkUrl100')
                source = candidate.get('collectionViewUrl')
                if cover and cover.startswith('https://') and source and source.startswith('https://'):
                    # 100 px достаточно для миниатюр; не подменяем размер URL произвольным образом.
                    return {'cover_url': cover, 'cover_source': source}
    except (requests.RequestException, ValueError, TypeError):
        pass
    return {'cover_url': None, 'cover_source': None}


def attach_album_art(albums):
    """Внешний сервис не влияет на доступность поиска по БЗ."""
    if not albums:
        return
    with ThreadPoolExecutor(max_workers=6) as executor:
        covers = list(executor.map(lambda a: find_album_art(a['stage_name'], a['title']), albums[:24]))
    for album, cover in zip(albums[:24], covers):
        album.update(cover)

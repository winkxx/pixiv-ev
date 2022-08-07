import os
import re

from .models import Artwork
from .. import util, settings
from ..exceptions import ReqException, ArtworkError
from ..texts import texts

__all__ = ['Illust']


class Illust(Artwork):
    """

    extra properties

    """

    _referer_url = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id='
    _details_url = 'https://www.pixiv.net/ajax/illust/'
    _headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/75.0.3770.100 Safari/537.36'
    }

    def __init__(self, illust_id):
        # properties, set after generate details is called
        self._views = None
        self._bookmarks = None
        self._title = None
        self._author = None
        self._likes = None
        self._tags = None
        self._id = None
        self._width = None
        self._height = None

        # iterator use, set after generate download data is called
        self.__download_urls = None

        # not used, set after generate details is called
        self.__original_url_template = None
        self.__comments = None

        # internal uses
        self.__page_count = None
        self._details_url = Illust._details_url + str(illust_id)
        self._headers = Illust._headers.copy()
        self._headers['referer'] = Illust._referer_url + str(illust_id)

        # this will call config
        super().__init__(illust_id)

    def config(self):
        try:
            illust_data = util.req(req_type='get', url=self._details_url, log_req=False).json()
            illust_data = illust_data['body']

            # properties
            # self._id = illust_data['id'] given, check? or overwrite? ... just ignore for now
            self._views = illust_data['viewCount']
            self._bookmarks = illust_data['bookmarkCount']
            self._likes = illust_data['likeCount']
            self._title = illust_data['illustTitle']
            self._author = illust_data['userName']
            self._height = illust_data['height']
            self._width = illust_data['width']
            self._tags = [item['tag'] for item in illust_data['tags']['tags']]

            self.__original_url_template = illust_data['urls']['original']
            self.__original_url_template = re.sub(r'(?<=_p)\d', '{page_num}', self.__original_url_template)
            self.__comments = illust_data['commentCount']
            self.__page_count = illust_data['pageCount']

            self.__generate_download_data()
        except (ReqException, KeyError) as e:
            raise ArtworkError(texts.ARTWORK_CONFIGURE_ERROR.format(id=self.id)) from e

    def _get_download_url(self, page_num):
        return self.__original_url_template.format(page_num=page_num)

    def _get_download_filename(self, download_url, folder=None):
        id_search = re.search(r'(\d{8}_p\d.*)', download_url)
        illust_signature = id_search.group(1) if id_search else download_url
        filename = str(self.author) + '_' + str(illust_signature)
        if folder is not None:
            filename = os.path.join(util.clean_filename(folder), filename)
        return util.clean_filename(filename)

    def __generate_download_data(self):
        self.__download_urls = []
        curr_page = 0

        while curr_page < self.__page_count:
            if self._reached_limit_in_settings(curr_page):
                break
            self.__download_urls.append(self._get_download_url(curr_page))
            curr_page += 1

    def __getitem__(self, index):
        download_url = self.__download_urls[index]
        filename = self._get_download_filename(download_url)

        return Artwork.DownloadStatus.OK, (download_url, self._headers), filename

    def __len__(self):
        return len(self.__download_urls)

    def __eq__(self, other):
        if isinstance(other, Illust):
            if other.id is not None:
                return self.id == other.id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()

    @property
    def tags(self):
        return self._tags

    @property
    def bookmarks(self):
        return self._bookmarks

    @property
    def views(self):
        return self._views

    @property
    def author(self):
        return self._author

    @property
    def title(self):
        return self._title

    @property
    def likes(self):
        return self._likes

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @staticmethod
    def _reached_limit_in_settings(current):
        if settings.MAX_PAGES_PER_ARTWORK:
            if current >= settings.MAX_PAGES_PER_ARTWORK:
                return True
        return False

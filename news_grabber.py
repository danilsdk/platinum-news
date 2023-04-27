from newsapi import NewsApiClient
from data.configuration import API_NEWS_TOKEN
from random import choice as rand
import datetime as dt

today = dt.date.today()
week_ago = today - dt.timedelta(days=7)

api = NewsApiClient(api_key=API_NEWS_TOKEN)


def get_news(request, lang):
    news_list = api.get_everything(q=request, language=lang, from_param=week_ago)

    if news_list['totalResults'] == 0:
        return '404'

    rand_news = rand(news_list['articles'])

    publ = rand_news['publishedAt'][:10].split('-')

    date = f"{publ[2]}.{publ[1]}.{publ[0]}"

    output = {
        "source": rand_news['source']['name'],
        "title": rand_news['title'],
        "date": date,
        "image": rand_news['urlToImage'],
        "url": rand_news['url']
    }

    return output

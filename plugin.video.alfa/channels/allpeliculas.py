# -*- coding: utf-8 -*-

from core import httptools
from core import jsontools
from core import scrapertools
from core import servertools
from core import tmdb
from core.item import Item
from channelselector import get_thumb
from platformcode import config, logger

__modo_grafico__ = config.get_setting('modo_grafico', "allpeliculas")
__perfil__ = int(config.get_setting('perfil', "allpeliculas"))

# Fijar perfil de color
perfil = [['0xFFFFE6CC', '0xFFFFCE9C', '0xFF994D00'],
          ['0xFFA5F6AF', '0xFF5FDA6D', '0xFF11811E'],
          ['0xFF58D3F7', '0xFF2E9AFE', '0xFF2E64FE']]
color1, color2, color3 = perfil[__perfil__]

IDIOMAS = {"Castellano": "CAST", "Latino": "LAT", "Subtitulado": "VOSE", "Ingles": "VO"}
SERVERS = {"26": "powvideo", "45": "okru", "75": "openload", "12": "netutv", "65": "thevideos",
           "67": "spruto", "71": "stormo", "73": "idowatch", "48": "okru", "55": "openload",
           "20": "nowvideo", "84": "fastplay", "96": "raptu", "94": "tusfiles"}

host = "http://allpeliculas.com/"

def mainlist(item):
    logger.info()
    itemlist = []
    item.text_color = color1

    itemlist.append(item.clone(title="Películas", action="lista", fanart="http://i.imgur.com/c3HS8kj.png",
                               url= host + "movies/newmovies?page=1", extra1 = 0,
                               thumbnail=get_thumb('movies', auto=True)))
    itemlist.append(item.clone(title="Por genero", action="generos", fanart="http://i.imgur.com/c3HS8kj.png",
                               url= host + "movies/getGanres", thumbnail=get_thumb('genres', auto=True)))
    itemlist.append(item.clone(title="Colecciones", action="colecciones", fanart="http://i.imgur.com/c3HS8kj.png",
                               url= host, thumbnail=get_thumb('colections', auto=True)))
    itemlist.append(item.clone(title="", action=""))
    itemlist.append(item.clone(title="Buscar...", action="search", thumbnail=get_thumb('search', auto=True)))

    return itemlist


def colecciones(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    patron  = 'href="(/peliculas[^"]+).*?'
    patron += 'title_geo"><span>([^<]+).*?'
    patron += 'title_eng"><span>([^<]+).*?'
    patron += 'src="([^"]+)'
    matches = scrapertools.find_multiple_matches(data, patron)
    for scrapedurl, scrapedtitle, scrapedcantidad, scrapedthumbnail in matches:
        if scrapedtitle == "LGTB" and config.get_setting("adult_mode") == 0:
            continue
        title = scrapedtitle.capitalize() + " (" + scrapedcantidad + ")"
        itemlist.append(Item(channel = item.channel,
                             action = "listado_colecciones",
                             page = 1,
                             thumbnail = host + scrapedthumbnail,
                             title = title,
                             url = host + scrapedurl
                             ))
    return itemlist


def listado_colecciones(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    data_url = scrapertools.find_single_match(data, "data_url: '([^']+)")
    post = "page=%s" %item.page
    data = httptools.downloadpage(host + data_url, post=post).data
    patron  = 'a href="(/peli[^"]+).*?'
    patron += 'src="([^"]+).*?'
    patron += 'class="c_fichas_title">([^<]+).*?'
    patron += 'Año:.*?href="">([^<]+)'
    matches = scrapertools.find_multiple_matches(data, patron)
    for scrapedurl, scrapedthumbnail, scrapedtitle, scrapedyear in matches:
        item.infoLabels['year'] = scrapedyear
        itemlist.append(item.clone(channel = item.channel,
                             action = "findvideos",
                             contentTitle = scrapedtitle,
                             thumbnail = scrapedthumbnail,
                             title = scrapedtitle,
                             url = host + scrapedurl
                             ))
    tmdb.set_infoLabels(itemlist)
    item.page += 1
    post = "page=%s" %item.page
    data = httptools.downloadpage(host + data_url, post=post).data
    if len(data) > 50:
        itemlist.append(Item(channel = item.channel,
                            action = "listado_colecciones",
                            title = "Pagina siguiente>>",
                            page = item.page,
                            url = item.url
                            ))
    return itemlist


def generos(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    dict_data = jsontools.load(data)
    for it in dict_data:
        itemlist.append(Item(
                             channel = item.channel,
                             action = "lista",
                             title = it['label'],
                             url = host + "movies/newmovies?page=1",
                             extra1 = it['id']
                             ))
    return itemlist
    

def findvideos(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    if "Próximamente" in data:
        itemlist.append(Item(channel = item.channel, title = "Próximamente"))
        return itemlist
    patron  = 'data-link="([^"]+).*?'
    patron += '>([^<]+)'
    matches = scrapertools.find_multiple_matches(data, patron)
    for url, calidad in matches:
        itemlist.append(item.clone(
                             channel = item.channel,
                             action = "play",
                             title = calidad,
                             fulltitle = item.title,
                             contentThumbnail = item.thumbnail,
                             url = url,
                             ))
    try:
        tmdb.set_infoLabels(itemlist, __modo_grafico__)
    except:
        pass
    itemlist = servertools.get_servers_itemlist(itemlist)
    itemlist.append(Item(channel=item.channel))
    if config.get_videolibrary_support():
        itemlist.append(Item(channel=item.channel, title="Añadir a la videoteca", text_color="green",
                             action="add_pelicula_to_library", url=item.url, thumbnail = item.thumbnail,
                             fulltitle = item.fulltitle
                             ))
    return itemlist


def play(item):
    logger.info()
    item.thumbnail = item.contentThumbnail
    return [item]


def lista(item):
    logger.info()
    itemlist = []
    dict_param = dict()
    item.infoLabels = {}
    item.text_color = color2

    params = '{}'
    if item.extra1 != 0:
        dict_param["genero"] = [item.extra1]
        params = jsontools.dump(dict_param)

    data = httptools.downloadpage(item.url, post=params).data
    data = data.replace("<mark>","").replace("<\/mark>","")
    dict_data = jsontools.load(data)

    for it in dict_data["items"]:
        title = it["title"]
        plot = it["slogan"]
        rating = it["imdb"]
        year = it["year"]
        url = host + "pelicula/" + it["slug"]
        thumb = host + it["image"]
        item.infoLabels['year'] = year
        itemlist.append(item.clone(action="findvideos", title=title, fulltitle=title, url=url, thumbnail=thumb,
                                   plot=plot, context=["buscar_trailer"], contentTitle=title, contentType="movie"))

    try:
        tmdb.set_infoLabels(itemlist, __modo_grafico__)
    except:
        pass
    pagina = scrapertools.find_single_match(item.url, 'page=([0-9]+)')
    item.url = item.url.replace(pagina, "")
    if pagina == "":
        pagina = "0"
    pagina = int(pagina) + 1
    item.url = item.url + "%s" %pagina
    if item.extra != "busqueda":
        itemlist.append(Item(channel = item.channel, action="lista", title="Pagina %s" %pagina, url=item.url, extra1 = item.extra1
                             ))
    return itemlist

def search(item, texto):
    logger.info()
    if texto != "":
        texto = texto.replace(" ", "%20")
    item.url = host + "/movies/search/" + texto
    item.extra = "busqueda"
    try:
        return lista(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def newest(categoria):
    logger.info()
    itemlist = []
    item = Item()
    try:
        if categoria in ['peliculas','latino']:
            item.url = host + "movies/newmovies?page=1"
            item.action = "lista"
            itemlist = lista(item)

            if itemlist[-1].action == "lista":
                itemlist.pop()

    # Se captura la excepción, para no interrumpir al canal novedades si un canal falla
    except:
        import sys
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        return []

    return itemlist

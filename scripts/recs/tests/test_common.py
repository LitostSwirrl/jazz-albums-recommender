from scripts.recs import common


def test_norm_basic():
    assert common.norm("The Jazz Messengers") == "jazz messengers"
    assert common.norm("Météo") == "meteo"


def test_norm_title_strips_editions():
    assert common.norm_title("Blue Train (Remastered 2003)") == "blue train"
    assert common.norm_title("Speak No Evil [RVG Edition]") == "speak no evil"


def test_norm_title_keeps_real_parens():
    assert common.norm_title("Money Jungle (Provocative in Blue)") != "money jungle"


def test_norm_key():
    assert (
        common.norm_key("The Bill Evans Trio", "Portrait in Jazz (OJC)")
        == "bill evans trio::portrait in jazz"
    )


def test_spotify_album_id():
    assert (
        common.spotify_album_id("https://open.spotify.com/album/2e2E6QiOO95idJELO2MnKb")
        == "2e2E6QiOO95idJELO2MnKb"
    )
    assert common.spotify_album_id("") is None

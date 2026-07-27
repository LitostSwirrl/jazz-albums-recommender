import scripts.fetch_rec_covers as rc


def test_core_title_strips_parenthetical_and_bracketed_suffixes():
    assert rc.core_title("Waltz for Debby (Original Jazz Classics)") == "waltzfordebby"
    assert rc.core_title("Dark Magus [Live]") == "darkmagus"
    assert rc.core_title("Mingus At Antibes (Live)") == "mingusatantibes"


def test_match_accepts_the_same_record_with_an_edition_suffix():
    assert rc.is_match(
        "Bill Evans",
        "Waltz for Debby",
        "Bill Evans Trio",
        "Waltz for Debby (Original Jazz Classics)",
    )


def test_match_rejects_a_different_album_by_the_same_artist():
    # Observed live: this is the false positive that makes strict title
    # matching load-bearing.
    assert not rc.is_match(
        "Theo Parrish",
        "Theo Parrish's Black Jazz Signature",
        "Theo Parrish",
        "First Floor",
    )


def test_match_rejects_a_different_artist():
    assert not rc.is_match("Chet Baker", "Chet", "Chet Atkins", "Chet")


def test_artwork_url_upgrades_the_size_segment():
    assert (
        rc.artwork_url("https://is1-ssl.mzstatic.com/image/thumb/a/b/100x100bb.jpg")
        == "https://is1-ssl.mzstatic.com/image/thumb/a/b/600x600bb.jpg"
    )


def test_should_cache_rejects_fetch_failed():
    # A transient network error must not become a permanent cache entry --
    # that would block every future retry for the album.
    assert not rc.should_cache("fetch_failed")


def test_should_cache_accepts_answers_about_the_album():
    assert rc.should_cache("ok")
    assert rc.should_cache("no_result")
    assert rc.should_cache("mismatch")

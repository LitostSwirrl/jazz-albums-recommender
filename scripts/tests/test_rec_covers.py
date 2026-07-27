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


def test_match_rejects_a_volume_marker_on_the_want_side():
    # Observed live and shipped a wrong cover: India Navigation issued Volumes
    # 1 and 2 with different sleeves. Stripping the parenthetical from OUR
    # title discards the only token that says which record we asked for.
    assert not rc.is_match(
        "David Murray",
        "Live At The Lower Manhattan Ocean Club (Volume 1)",
        "David Murray",
        "Live at the Lower Manhattan Ocean Club",
    )


def test_match_rejects_disagreeing_edition_markers():
    assert not rc.is_match("A", "Ellington (Volume 1)", "A", "Ellington (Volume 2)")
    assert not rc.is_match("A", "Live in Paris (1975)", "A", "Live in Paris (1976)")
    assert not rc.is_match("A", "Blue Train [Take 1]", "A", "Blue Train [Take 2]")


def test_match_accepts_a_parenthetical_that_is_part_of_the_name():
    # The parenthetical is the release title, not an edition suffix. Both sides
    # carry it, so it must still match.
    assert rc.is_match(
        "Darius Jones",
        "Raw Demoon Alchemy (A Lone Operation)",
        "Darius Jones",
        "Raw Demoon Alchemy (A Lone Operation)",
    )


def test_match_uses_the_bracketed_name_when_the_title_repeats_the_artist():
    # "Art Blakey and The Jazz Messengers [Moanin']" reduces to the bare artist
    # once the bracket is stripped, so it could never match anything. The
    # bracket holds the actual album name.
    assert rc.is_match(
        "Art Blakey and The Jazz Messengers",
        "Art Blakey and The Jazz Messengers [Moanin']",
        "Art Blakey",
        "Moanin' (Remastered)",
    )


def test_match_rejects_an_empty_artist_on_either_side():
    assert not rc.is_match("", "Kind of Blue", "Miles Davis", "Kind of Blue")
    assert not rc.is_match("Miles Davis", "Kind of Blue", "", "Kind of Blue")


def test_match_rejects_an_empty_title():
    assert not rc.is_match("Miles Davis", "", "Miles Davis", "")


def test_artwork_url_upgrades_the_size_segment():
    assert (
        rc.artwork_url("https://is1-ssl.mzstatic.com/image/thumb/a/b/100x100bb.jpg")
        == "https://is1-ssl.mzstatic.com/image/thumb/a/b/600x600bb.jpg"
    )


def test_artwork_url_leaves_a_url_without_the_size_segment_alone():
    # Not every artworkUrl100 carries the segment. Returning the URL unchanged
    # gives a smaller cover; inventing a substitution would give a broken one.
    plain = "https://is1-ssl.mzstatic.com/image/thumb/a/b/source/cover.jpg"
    assert rc.artwork_url(plain) == plain


def test_should_cache_rejects_fetch_failed():
    # A transient network error must not become a permanent cache entry --
    # that would block every future retry for the album.
    assert not rc.should_cache("fetch_failed")


def test_should_cache_accepts_answers_about_the_album():
    assert rc.should_cache("ok")
    assert rc.should_cache("no_result")
    assert rc.should_cache("mismatch")

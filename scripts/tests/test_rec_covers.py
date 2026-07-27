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

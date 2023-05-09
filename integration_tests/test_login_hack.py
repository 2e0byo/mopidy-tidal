import pytest


@pytest.mark.parametrize(
    "type",
    (
        "artist",
        "album",
        "Artist",
        "Album",
        "AlbumArtist",
        "Title",
        "Genre",
        "Date",
        "Composer",
        "Performer",
        "Comment",
    ),
)
def test_link_on_mpc_list_with_hack_login(type, spawn, config_dir):
    config = config_dir / "lazy_hack.conf"
    with spawn(f"mopidy --config {config.resolve()}") as child:
        child.expect("Connecting to TIDAL... Quality = LOSSLESS")
        child.expect("Starting GLib mainloop")
        with spawn(f"mpc list {type}") as mpc:
            mpc.expect("Please visit .*link.tidal.com/.* to log in")

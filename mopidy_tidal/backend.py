from __future__ import unicode_literals

import json
import logging
import os

from mopidy import backend
from pykka import ThreadingActor
from tidalapi import Config, Quality, Session

from mopidy_tidal import Extension, context, library, playback, playlists

logger = logging.getLogger(__name__)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(TidalBackend, self).__init__()
        self._current_session = None
        self._logged_in = False
        self._config = config
        context.set_config(self._config)
        self.playback = playback.TidalPlaybackProvider(audio=audio, backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)
        self.uri_schemes = ["tidal"]

    def oauth_login_new_session(self):
        logger.info("Creating new OAuth session...")
        # create a new session
        self._current_session.login_oauth_simple(function=logger.info)
        if self._current_session.check_login():
            # store current OAuth session
            data = {}
            data["token_type"] = {"data": self._current_session.token_type}
            data["session_id"] = {"data": self._current_session.session_id}
            data["access_token"] = {"data": self._current_session.access_token}
            data["refresh_token"] = {"data": self._current_session.refresh_token}
            with open(self._oauth_file, "w") as outfile:
                json.dump(data, outfile)

    def _login(self):
        if not self._current_session.check_login():
            self._login_oauth()

        if not self._current_session.check_login():
            self.oauth_login_new_session()

        if self._current_session.check_login():
            logger.info("TIDAL Login OK")
        else:
            logger.info("TIDAL Login KO")
            raise Exception("Failed to log in.")

    @property
    def _session(self):
        if not self._logged_in:
            self._login()
        self._logged_in = True
        return self._current_session

    @property
    def _oauth_file(self):
        # Always store tidal-oauth cache in mopidy core config data_dir
        data_dir = Extension.get_data_dir(self._config)
        return os.path.join(data_dir, "tidal-oauth.json")

    def _login_oauth(self):
        try:
            # attempt to reload existing session from file
            with open(self._oauth_file) as f:
                logger.info("Loading OAuth session from %s..." % self._oauth_file)
                data = json.load(f)
                self._current_session.load_oauth_session(
                    data["session_id"]["data"],
                    data["token_type"]["data"],
                    data["access_token"]["data"],
                    data["refresh_token"]["data"],
                )
        except Exception:
            logger.info("Could not load OAuth session from %s" % self._oauth_file)

    def on_start(self):
        quality = self._config["tidal"]["quality"]
        logger.info("Quality = %s" % quality)
        config = Config(quality=Quality(quality))
        client_id = self._config["tidal"]["client_id"]
        client_secret = self._config["tidal"]["client_secret"]

        if (client_id and not client_secret) or (client_secret and not client_id):
            logger.warn("always provide client_id and client_secret together")
            logger.info("Using default client id & client secret from python-tidal")

        if client_id and client_secret:
            logger.info("Client id & client secret from config section are used")
            config.client_id = client_id
            config.api_token = client_id
            config.client_secret = client_secret

        if not client_id and not client_secret:
            logger.info("Using default client id & client secret from python-tidal")

        self._current_session = Session(config)
        if not self._config["tidal"]["lazy"]:
            try:
                self._login()
            except Exception:
                pass

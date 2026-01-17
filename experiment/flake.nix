{
  description = "Mopidy Tidal";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem
    (
      system: let
        libsoup-overlay = final: prev: {
          libsoup_3 = prev.libsoup_3.overrideAttrs (_: {
            src = pkgs.fetchgit {
              url = "https://gitlab.gnome.org/GNOME/libsoup.git";
              rev = "e9b681a5";
              hash = "sha256-r+i1gGJHcXJW20W9PNz1Z108tkPhiqh9ytkrHKbWW58=";
            };
            version = "3.6.5-5";
          });
        };

        pkgs = import nixpkgs {
          inherit system;
          overlays = [libsoup-overlay];
        };
        python = pkgs.python313;
        buildInputs =
          (with pkgs; [
            (python.withPackages (ps:
              with ps; [
                gst-python
                pygobject3
              ]))
            uv
            pre-commit
            ruff
            mopidy # for its build inputs: it would be nice to do this properly, but I can't seem to get network playing to work
            gobject-introspection
            mpc # integration tests
          ])
          ++ (with pkgs.gst_all_1; [
            pkgs.glib-networking
            gst-plugins-bad
            gst-plugins-base
            gst-plugins-good
            gst-plugins-ugly
            gst-plugins-rs
          ]);
        env = {
          UV_PROJECT_ENVIRONMENT = ".direnv/venv";
        };

        tidalapi = pkgs.python3Packages.buildPythonPackage rec {
          pname = "tidalapi";
          version = "0.8.10";
          pyproject = true;

          src = pkgs.fetchFromGitHub {
            owner = "EbbLabs";
            repo = "python-tidal";
            tag = "v${version}";
            hash = "sha256-hqtTe/KIGds01udMKoH5xXnoEe17FuOXLvWtp1yvJ2c=";
          };

          build-system = [
            pkgs.python3Packages.poetry-core
          ];

          dependencies = with pkgs.python3Packages; [
            requests
            python-dateutil
            mpegdash
            isodate
            ratelimit
            typing-extensions
            pyaes
          ];

          doCheck = false; # tests require internet access

          pythonImportsCheck = [
            "tidalapi"
          ];
        };

        local-mopidy-tidal = pkgs.python3Packages.buildPythonApplication rec {
          pname = "latest-mopidy-tidal";
          version = "0.3.12";
          pyproject = true;

          src = pkgs.fetchFromGitHub {
            owner = "2e0byo";
            repo = "mopidy-tidal";
            rev = "feat/proxy";
            hash = "sha256-06UilqKFP8Oygl9H4E/9e4mMiA7qncuq2IsLev/EY9k="; #BAD
          };

          # used even though we're not using poetry
          build-system = [pkgs.python3Packages.poetry-core];

          nativeCheckInputs = with pkgs.python3Packages; [
            pytestCheckHook
            pytest-asyncio
            pytest-cov # since default pytest invocation includes --cov
            pytest-mock
            pytest-httpserver
            pytest-cases
            trustme
            httpx
          ];
          doCheck = false; # currently hangs

          dependencies = [
            pkgs.mopidy
            # pkgs.python3Packages.tidalapi
            tidalapi
          ];
        };
      in
        with pkgs; {
          inherit libsoup3;
          devShells.default = mkShell {
            # this also works, if you don't use the overlay above
            # env = { GST_PLUGIN_FEATURE_RANK="curlhttpsrc:MAX";};
            buildInputs =
              (with pkgs; [
                mopidy
                mopidy-local
                mopidy-iris
                mopidy-mpd
              ])
              ++ [
                # uncomment to use the code with the proxy
                # local-mopidy-tidal
                pkgs.mopidy-tidal
              ];
          };
        }
    );
}

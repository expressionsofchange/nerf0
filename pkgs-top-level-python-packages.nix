  kivy = buildPythonPackage rec {
    name = "Kivy-1.10.0";

    src = pkgs.fetchurl {
      url = "mirror://pypi/k/kivy/${name}.tar.gz";
      # sha256 = "0zk3g1j1z0lzcm9d0k1lprrs95zr8n8k5pdg3p5qlsn26jz4bg19"; 1.9.1
      sha256 = "1394zh6kvf7k5d8vlzxcsfcailr3q59xwg9b1n7qaf25bvyq1h98";
    };

    # setup.py invokes git on build but we're fetching a tarball, so
    # can't retrieve git version. We remove the git-invocation from setup.py
    patches = [
      ../development/python-modules/kivy/setup.py.patch
    ];

    buildInputs = with self; [ 
      pkgconfig
      cython
      kivygarden
      requests2
      docutils
      pygments
      nose

      pkgs.SDL2
      pkgs.SDL2_image
      pkgs.SDL2_ttf
      pkgs.SDL2_mixer

      pkgs.mesa  # is GL, AFAIU
      pkgs.gst_all_1.gstreamer
      # pyopengl

      ];
    propagatedBuildInputs = with self; [
      nose  # to facilitate the construction of the runner.
      pillow
      ] ; 

    doCheck = false;

    checkPhase = ''
      export KIVY_NO_CONFIG=1
      nosetests
    '';

    meta = {
      description = "A software library for rapid development of hardware-accelerated multitouch applications.";
      homepage    = "https://pypi.python.org/pypi/kivy";
      license     = licenses.mit;
      maintainers = with maintainers; [ vanschelven ];
      platforms   = platforms.unix;  # Can only test linux; in principle other platforms are supported
    };
  };

  kivygarden = buildPythonPackage rec {
    # NOTE HOW THIS THING IS THE WORK OF THE DEVIL
    # NOTE HOW THE ONLY REASON I DID THIS IS.. TO GET KIVY TO WORK
    name = "kivy-garden-0.1.4";

    src = pkgs.fetchurl {
      url = "mirror://pypi/k/kivy-garden/${name}.tar.gz";
      sha256 = "0wkcpr2zc1q5jb0bi7v2dgc0vs5h1y7j42mviyh764j2i0kz8mn2";
    };

    buildInputs = with self; [ requests2 ];

    meta = {
      description = "The kivy garden installation script, split into its own package for convenient use in buildozer.";

      homepage    = "https://pypi.python.org/pypi/kivy-garden";
      license     = licenses.mit;
      maintainers = with maintainers; [ vanschelven ];
      platforms   = platforms.unix;  # Can only test linux; in principle other platforms are supported
    };
  };



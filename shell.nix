let
	pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  name = "MusicAnalyser-shell";

	packages = [
		(pkgs.python314.withPackages (ps: with ps; [
			pandas
			numpy
			seaborn
			matplotlib
		]))
	];

  shellHook = ''
    echo " -- Music Analyser Environment -- "
    echo "Python: $(python --version)"
  '';
}

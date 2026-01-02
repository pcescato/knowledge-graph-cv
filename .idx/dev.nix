{ pkgs, ... }: {
  channel = "stable-24.11"; # Version stable actuelle
  
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.uv # Je vois que tu as mis uv, c'est un excellent choix pour la rapidité
  ];

  idx = {
    extensions = [
      "google.gemini-cli-vscode-ide-companion"
      "ms-python.python"
    ];

    # C'est ici que la magie opère pour Streamlit
    previews = {
      enable = true;
      previews = {
        web = {
          # On active l'environnement virtuel et on lance Streamlit
          command = [
            "bash" 
            "-c" 
            "source .venv/bin/activate && streamlit run app.py --server.port $PORT --server.address 0.0.0.0"
          ];
          manager = "web";
        };
      };
    };

    workspace = {
      # Se lance à la création du projet
      onCreate = {
        setup-venv = "python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt";
      };
      # Se lance à chaque démarrage
      onStart = {
        install-deps = "source .venv/bin/activate && pip install -r requirements.txt";
      };
    };
  };
}
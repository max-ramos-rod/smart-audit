"""Exporta o contrato OpenAPI do Smart Audit sem subir o servidor.

O FastAPI gera o schema a partir dos routers/schemas em runtime; este script
importa o app e serializa `app.openapi()`, util para agentes/integracoes obterem
o contrato de forma deterministica e offline (nao gera snapshot versionado, que
envelheceria).

Pre-requisito: virtualenv ativo + `.env` na raiz (mesmas variaveis do app:
DATABASE_URL, JWT_SECRET_KEY). Nao acessa o banco.

Uso (repo root):
    python backend/scripts/export_openapi.py                # imprime no stdout
    python backend/scripts/export_openapi.py -o openapi.json # grava em arquivo
"""

import argparse
import json

from app.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o schema OpenAPI do Smart Audit.")
    parser.add_argument("-o", "--output", help="Arquivo de saida (default: stdout)")
    args = parser.parse_args()

    schema = json.dumps(app.openapi(), ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(schema + "\n")
        print(f"OpenAPI exportado para {args.output}")
    else:
        print(schema)


if __name__ == "__main__":
    main()

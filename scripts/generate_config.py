#!/usr/bin/env python3
"""
Script pour générer un fichier de configuration par défaut.
Permet de créer config.yaml ou config.json avec les valeurs par défaut.
"""

import argparse
from config.settings import Config
from logger_settings import logger


def main():
    parser = argparse.ArgumentParser(
        description="Générer un fichier de configuration par défaut pour Crypto Bot"
    )
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Format du fichier de configuration (yaml ou json)",
    )
    parser.add_argument(
        "--output",
        default="config.yaml",
        help="Chemin du fichier de sortie",
    )

    args = parser.parse_args()

    # Créer une instance de configuration avec les valeurs par défaut
    config = Config()

    # Déterminer le format de sortie
    if args.format == "json":
        output_file = args.output if args.output.endswith(".json") else "config/config.json"
    else:
        output_file = args.output if args.output.endswith(".yaml") else "config/config.yaml"

    # Sauvegarder la configuration
    success = config.save_to_file(output_file)

    if success:
        logger.info(f"✅ Configuration par défaut générée dans {output_file}")
        logger.info("Vous pouvez maintenant modifier ce fichier selon vos besoins.")
    else:
        logger.error(f"❌ Échec de la génération du fichier {output_file}")


if __name__ == "__main__":
    main()
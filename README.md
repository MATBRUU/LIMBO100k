# LIMBO100k

Agent de simulation fictive pour un jeu de type Limbo.

## Objectif

Ce projet sert à entraîner et comparer des stratégies de gestion de bankroll dans un environnement simulé :

- capital initial : 50 € ;
- objectif théorique : 100 000 € ;
- moteur probabiliste de type Limbo ;
- mesure du risque de ruine, du drawdown, de la volatilité et du taux de survie ;
- comparaison de plusieurs agents.

## Limite importante

Ce dépôt est conçu uniquement pour la simulation, la recherche statistique et l'entraînement algorithmique.
Il ne contient pas et ne doit pas contenir de connexion à un casino réel, d'automatisation de mises réelles, ni de mécanisme destiné à contourner l'aléa d'un jeu d'argent.

## Structure

```text
limbo100k/
  engine/        Moteur du jeu fictif
  agents/        Stratégies de mise
  risk/          Règles de gestion du risque
  analytics/     Métriques de performance
  simulation.py  Orchestration des simulations
scripts/
  run_simulation.py
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .
```

## Lancer une simulation

```bash
python scripts/run_simulation.py --sessions 1000 --agent fixed --initial-bankroll 50 --target-bankroll 100000
```

## Prochaine étape

Créer un dashboard de suivi avec courbe de bankroll, distribution des résultats et comparaison des agents.

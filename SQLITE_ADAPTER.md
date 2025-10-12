# FlexmodelSQLite - SQLite3 Adapter for Flex-Schema

## Vue d'ensemble

FlexmodelSQLite est un adapteur SQLite3 pour Flex-Schema qui offre les mêmes fonctionnalités que Flexmodel mais utilise SQLite au lieu de MongoDB.

## Caractéristiques principales

### 1. Structure de la table SQLite

Chaque modèle est stocké dans une table SQLite avec la structure suivante:
- **_id** (TEXT PRIMARY KEY): Identifiant UUID unique
- **_updated_at** (TEXT): Horodatage au format ISO
- **document** (TEXT): Représentation JSON complète du document

### 2. Méthodes disponibles

FlexmodelSQLite fournit exactement les mêmes méthodes que Flexmodel:

#### Méthodes d'instance:
- `commit(commit_all=True)`: Sauvegarde dans la base de données
- `delete()`: Supprime de la base de données
- `id`: Obtient l'ID du document
- `updated_at`: Obtient l'horodatage de la dernière mise à jour

#### Méthodes de classe:
- `attach(database, table_name=None)`: Se connecte à la base de données SQLite
- `detach()`: Se déconnecte de la base de données
- `load(_id)`: Charge un document par ID
- `fetch(queries)`: Trouve un document correspondant aux requêtes
- `fetch_all(queries={}, position=1, position_limit=10)`: Obtient des résultats paginés
- `count()`: Compte les documents dans la table
- `truncate()`: Supprime tous les enregistrements de la table

### 3. Exemple d'utilisation

```python
import sqlite3
from flexschema import Schema, FlexmodelSQLite, field, field_constraint

# Définir un modèle
class User(FlexmodelSQLite):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        email=field(
            str,
            nullable=False,
            constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
        ),
        age=field(int, default=0),
    )

# Se connecter à SQLite
conn = sqlite3.connect("database.sqlite")
User.attach(conn, "users")

# Créer et sauvegarder
user = User(name="Jean Dupont", email="jean@example.com", age=30)
user.commit()

# Charger par ID
loaded_user = User.load(user.id)

# Rechercher
found_user = User.fetch({"email": "jean@example.com"})

# Pagination
results = User.fetch_all({}, position=1, position_limit=10)
for user in results:
    print(user.to_json())
```

### 4. Fonctionnalités avancées

#### Modèles imbriqués
FlexmodelSQLite supporte les modèles imbriqués comme Flexmodel:

```python
class Address(Flex):
    schema = Schema(
        street=field(str, nullable=False),
        city=field(str, nullable=False),
    )

class Person(FlexmodelSQLite):
    schema = Schema.ident(
        name=field(str, nullable=False),
        address=field(Address, nullable=False, default=Address()),
    )
```

#### Validation de schéma
Toutes les validations de schéma fonctionnent exactement comme avec Flexmodel:

```python
class Product(FlexmodelSQLite):
    schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(
            float,
            nullable=False,
            constraint=field_constraint(min_length=0),
        ),
    )

product = Product(name="Laptop", price=999.99)
if product.commit():
    print("Produit sauvegardé!")
else:
    print("Erreurs:", product.evaluate())
```

## Tests

Des tests complets sont disponibles dans `tests/test_sqlite.py`:
- Tests CRUD basiques
- Tests de modèles imbriqués
- Tests de validation de schéma
- Tests de structure de table
- Tests de pagination

Pour exécuter les tests:
```bash
python tests/test_sqlite.py
```

## Différences avec Flexmodel

La seule différence majeure est le stockage sous-jacent:
- **Flexmodel**: Utilise MongoDB (collections, documents)
- **FlexmodelSQLite**: Utilise SQLite (tables, JSON)

L'API reste identique pour faciliter la migration entre les deux backends.

## Avantages de SQLite

- Pas de serveur requis (base de données fichier)
- Parfait pour les applications embarquées
- Excellent pour le développement et les tests
- Portable et simple à déployer
- Transactions ACID complètes

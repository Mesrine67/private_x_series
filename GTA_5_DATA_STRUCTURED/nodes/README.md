# Système de découpage des nodes GPS

Ce dossier contient les fichiers de zones découpés à partir de `lib/nodes.json`.

## Pourquoi découper nodes.json ?

Le fichier `nodes.json` est très volumineux (~142 MB) et contient plus de 4 millions de lignes de données routières pour GTA V. Le charger entièrement en mémoire peut causer des problèmes de performance.

Le système de découpage divise ce fichier en plusieurs petits fichiers par zone (AreaId), permettant de :
- Charger uniquement les zones visibles dans le viewport
- Réduire l'utilisation de la mémoire
- Accélérer le chargement initial
- Améliorer les performances du pathfinding GPS

## Comment découper nodes.json

Si ce dossier est vide ou si vous avez mis à jour `nodes.json`, exécutez :

```bash
pnpm split-nodes
```

Cela va :
1. Lire le fichier `lib/nodes.json`
2. Créer un fichier `area_X.json` pour chaque zone
3. Générer un fichier `index.json` contenant les métadonnées de toutes les zones

## Structure des fichiers

```
lib/nodes/
├── README.md           # Ce fichier
├── index.json          # Index des zones (coordonnées, nombre de nœuds)
├── area_489.json       # Zone 489
├── area_490.json       # Zone 490
└── ...                 # Autres zones
```

## Utilisation dans le code

L'API `/api/roads` détecte automatiquement si le système de découpage est disponible :

```typescript
import { loadAreaIndex, loadArea, findVisibleAreas } from '@/lib/load-area-nodes'

// Charger l'index
const index = loadAreaIndex()

// Charger une zone spécifique
const area = loadArea(489)

// Trouver les zones visibles dans un viewport
const visibleAreaIds = findVisibleAreas(minX, minY, maxX, maxY)
```

## Fallback

Si les fichiers découpés n'existent pas, l'API utilisera automatiquement le fichier `nodes.json` complet (plus lent mais fonctionnel).

## Performance

Avec le système de découpage :
- Chargement initial : ~200ms (au lieu de ~5s)
- Utilisation mémoire : ~50MB (au lieu de ~200MB)
- Pathfinding GPS : ~20-50ms (inchangé)

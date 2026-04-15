# Guide Complet d'Organisation des Tiles Maps

## Structure Existante

Notre projet utilise un système de cartographie tuilée (slippy maps) suivant le standard XYZ où:

- **Z** = Niveau de zoom (0-5)
- **X** = Coordonnée horizontale (colonne)
- **Y** = Coordonnée verticale (ligne)

## Styles de Cartes

Le projet comprend trois styles de rendu distincts, chacun avec ses propres caractéristiques:

```
tiles_maps/
├── styleAtlas/     # Style atlas cartographique standard (JPG)
├── styleGrid/      # Style avec grille (PNG)
└── styleSatelite/  # Imagerie satellite (JPG)
```

### Caractéristiques Spécifiques des Styles

#### styleAtlas
- **Format**: JPG
- **Taille moyenne**: 10-33 KB par tuile
- **Caractéristiques**: Compression variable selon le contenu
- **Fichiers globaux**: `empty.jpg` (10.8 KB), `map.png` (22.5 MB)

#### styleGrid
- **Format**: PNG
- **Taille constante**: 199.6 KB par tuile
- **Caractéristiques**: Qualité constante, préservation de la transparence
- **Fichiers globaux**: `empty.png` (199.6 KB), `map.png` (19.5 MB)

#### styleSatelite
- **Format**: JPG
- **Taille variable**: 9-70 KB par tuile
- **Caractéristiques**: Compression forte pour zones uniformes, moindre pour zones détaillées
- **Fichiers globaux**: `empty.jpg` (10.0 KB), `satellite.jpg` (10.6 MB), `satellite.png` (71.3 MB)

## Organisation Hiérarchique

Chaque style suit la même structure hiérarchique précise:

```
styleXXX/
├── 0/              # Zoom niveau 0 (1x1 tuiles)
│   └── 0/          # Coordonnée X=0
│       └── 0.jpg   # Coordonnée Y=0
├── 1/              # Zoom niveau 1 (2x2 tuiles)
│   ├── 0/          # Coordonnées X=0
│   │   ├── 0.jpg   # Y=0
│   │   └── 1.jpg   # Y=1
│   └── 1/          # Coordonnées X=1
│       ├── 0.jpg   # Y=0
│       └── 1.jpg   # Y=1
├── 2/              # Zoom niveau 2 (4x4 tuiles)
...
└── 5/              # Zoom niveau 5 (32x32 tuiles)
    ├── 0/
    │   ├── 0.jpg
    │   ├── 1.jpg
    │   └── ... jusqu'à 31.jpg
    ├── 1/
    │   └── ...
    └── ... jusqu'à 31/
        └── 0.jpg jusqu'à 31.jpg
```

### Croissance Exponentielle des Tuiles

- **Niveau 0**: 2^0 × 2^0 = 1 tuile au total (1×1)
- **Niveau 1**: 2^1 × 2^1 = 4 tuiles au total (2×2)
- **Niveau 2**: 2^2 × 2^2 = 16 tuiles au total (4×4)
- **Niveau 3**: 2^3 × 2^3 = 64 tuiles au total (8×8)
- **Niveau 4**: 2^4 × 2^4 = 256 tuiles au total (16×16)
- **Niveau 5**: 2^5 × 2^5 = 1,024 tuiles au total (32×32)

## Fichiers Globaux et leur Utilisation

Chaque style contient des fichiers globaux avec des fonctions spécifiques:

### styleAtlas
- `empty.jpg`: Image de substitution affichée pour les tuiles manquantes ou en cours de chargement
- `map.png`: Version complète de la carte à basse résolution, utilisée pour les aperçus ou le préchargement

### styleGrid
- `empty.png`: Image de substitution avec transparence pour les tuiles manquantes
- `map.png`: Version complète de la carte avec le système de grille visible

### styleSatelite
- `empty.jpg`: Image de substitution pour les tuiles satellites manquantes
- `satellite.jpg`: Version compressée de la carte satellite complète (meilleure performance)
- `satellite.png`: Version haute qualité de la carte satellite (plus lourd mais plus détaillé)

## Spécificités Techniques des Tuiles

### Dimensions et Résolution
- **Taille standard**: 256×256 pixels par tuile
- **Format styleAtlas**: JPG sans canal alpha (RGB)
- **Format styleGrid**: PNG avec canal alpha (RGBA)
- **Format styleSatelite**: JPG avec compression optimisée

### Niveaux de Compression
- **styleAtlas**: Compression JPG moyenne (~75-85%)
- **styleGrid**: PNG sans perte
- **styleSatelite**: Compression JPG variable (60-90% selon le contenu)

### Système de Coordonnées
Le système suit le standard Web Mercator (EPSG:3857) avec:
- L'origine (0,0) située au coin supérieur gauche
- L'axe X augmentant vers l'est
- L'axe Y augmentant vers le sud

## Bonnes Pratiques pour l'Extension du Système

### Ajout de Nouvelles Tuiles

1. **Respecter la convention de nommage**:
   - Les dossiers Z doivent être numérotés de 0 à N
   - Les dossiers X sont numérotés de 0 à (2^Z)-1
   - Les fichiers Y sont numérotés de 0.jpg/png à (2^Z)-1.jpg/png

2. **Maintenir la cohérence des formats**:
   - `styleAtlas`: Utiliser des JPG avec compression adaptative
   - `styleGrid`: Utiliser des PNG sans perte
   - `styleSatelite`: Utiliser des JPG avec compression selon le contenu

3. **Préserver les dimensions**:
   - Maintenir la taille de 256×256 pixels pour toutes les tuiles
   - Pour les tuiles partielles (bords de carte), compléter avec de la transparence ou la couleur de fond

### Ajout d'un Nouveau Style

Pour ajouter un nouveau style de carte (par exemple, `styleNight`):

1. Créer un nouveau dossier à la racine de `tiles_maps/`
2. Reproduire la structure complète de niveaux de zoom (0-5)
3. Pour chaque niveau, créer la structure X/Y appropriée
4. Ajouter les fichiers complémentaires:
   - `empty.jpg` ou `empty.png` pour les tuiles manquantes
   - Fichier de carte complète avec le format approprié

### Extension des Niveaux de Zoom

Pour ajouter un niveau de zoom supplémentaire (niveau 6):

1. Dans chaque style, créer un dossier `6/`
2. Créer 64 sous-dossiers (0-63) pour les coordonnées X
3. Dans chaque dossier X, créer 64 fichiers (0.jpg à 63.jpg) pour les coordonnées Y
4. S'assurer que chaque nouvelle tuile couvre précisément 1/4 de la tuile parente du niveau 5

## Optimisation des Ressources

### Techniques de Compression
- **JPG**: Utiliser une compression adaptative basée sur le contenu
  - Zones uniformes: compression plus forte (90-95%)
  - Zones détaillées: compression plus légère (75-85%)
- **PNG**: Utiliser une compression sans perte avec optimisation
  - Réduire la palette de couleurs si possible
  - Utiliser des outils comme OptiPNG ou PNGQuant

### Stratégies de Chargement
- Mettre en cache les tuiles fréquemment utilisées
- Implémenter un chargement progressif (basse résolution → haute résolution)
- Précharger les tuiles adjacentes lors de la navigation

## Intégration avec les Systèmes de Navigation

### Conversion de Coordonnées
Pour convertir des coordonnées géographiques en indices de tuiles:

```javascript
function geoToTile(lat, lon, zoom) {
    const x = Math.floor((lon + 180) / 360 * Math.pow(2, zoom));
    const y = Math.floor((1 - Math.log(Math.tan(lat * Math.PI/180) + 1 / Math.cos(lat * Math.PI/180)) / Math.PI) / 2 * Math.pow(2, zoom));
    return { x, y, z: zoom };
}
```

### Bibliothèques Compatibles
Cette structure est compatible avec les bibliothèques cartographiques comme:
- Leaflet.js
- OpenLayers
- Mapbox GL
- Google Maps API (avec adaptation)

## Maintenance et Dépannage

### Vérification d'Intégrité
Script de vérification pour:
- Identifier les tuiles manquantes
- Repérer les tuiles corrompues
- Valider la cohérence des formats

```bash
#!/bin/bash
# Script de vérification des tiles
for style in styleAtlas styleGrid styleSatelite; do
  for z in {0..5}; do
    for x in $(seq 0 $((2**$z-1))); do
      for y in $(seq 0 $((2**$z-1))); do
        if [ "$style" == "styleGrid" ]; then
          ext="png"
        else
          ext="jpg"
        fi
        if [ ! -f "$style/$z/$x/$y.$ext" ]; then
          echo "Tuile manquante: $style/$z/$x/$y.$ext"
        fi
      done
    done
  done
done
```

### Régénération de Tuiles Manquantes
Procédure pour générer les tuiles manquantes:
1. Identifier la tuile manquante par son chemin Z/X/Y
2. Utiliser l'image source à haute résolution pour générer la tuile
3. Appliquer les transformations spécifiques au style (grille, effets, etc.)
4. Sauvegarder avec le format et niveau de compression appropriés

## Évolution Future du Système

### Niveaux de Détail Adaptatifs
- Implémentation de tuiles vectorielles pour une meilleure mise à l'échelle
- Stratégie de génération à la demande pour les niveaux de zoom élevés

### Styles Additionnels Potentiels
- `styleNight`: Rendu nocturne avec éclairage
- `styleThematic`: Visualisations thématiques (densité, température, etc.)
- `style3D`: Rendu isométrique ou 3D des éléments

### Migration vers Formats Avancés
- WebP pour remplacer JPG avec une meilleure compression
- AVIF pour une compression encore plus efficace
- SVG pour les éléments vectoriels (légendes, symboles)

## Conclusion

Cette organisation structurée des tiles maps offre une base solide pour l'affichage de cartes interactives avec différents styles visuels. Le système de coordonnées Z/X/Y facilite l'implémentation du zoom et de la navigation, tandis que la séparation en styles distincts permet une grande flexibilité visuelle.

Pour maintenir l'efficacité du système, respectez rigoureusement les conventions de nommage et d'organisation, et assurez-vous que toutes les nouvelles tuiles correspondent aux spécifications techniques établies pour chaque style.
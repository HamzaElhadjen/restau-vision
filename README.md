# RESTO-VISION — MVP Vision

Prototype web de surveillance d'occupation des tables à partir d'une webcam.

## Fonctionnalités
- Capture webcam (index 0 par défaut).
- Détection des personnes avec YOLO (`yolo11n.pt` par défaut).
- Suivi temporaire avec ByteTrack via `model.track(..., persist=True)`.
- Zones polygonales configurables pour chaque table.
- Estimation du nombre de personnes par table.
- Confirmation temporelle de l'occupation et de la libération pour limiter les faux changements.
- Chronomètre d'occupation et tableau de bord web.
- Flux vidéo annoté (personnes, zones, états).

> Limite importante : ce MVP détecte l'occupation visuelle. Il ne sait pas encore si un serveur a pris une commande, ni quels plats ont été commandés. Ces événements devront être confirmés via une interface serveur ou reliés à un logiciel de caisse dans une version ultérieure.

## Prérequis
- Python 3.10 ou supérieur (3.11 recommandé).
- Webcam accessible par l'ordinateur.
- Connexion Internet au premier lancement pour télécharger le modèle YOLO.
- Windows, Linux ou macOS.

## Installation — Windows (PowerShell)
```powershell
cd RESTO-VISION
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Si PowerShell bloque l'activation, utilisez l'invite de commandes :
```cmd
.venv\Scripts\activate.bat
```

## Installation — Linux / macOS
```bash
cd RESTO-VISION
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Ouvrir ensuite : http://127.0.0.1:8000

Le premier démarrage peut prendre plus de temps car YOLO télécharge le modèle `yolo11n.pt`.

## Configuration des tables
Modifier `config/tables.json`.

Les coordonnées sont normalisées entre 0 et 1 :
- x = position horizontale / largeur de l'image
- y = position verticale / hauteur de l'image

Exemple : `[0.05, 0.10]` correspond à 5 % depuis la gauche et 10 % depuis le haut.

Chaque table est un polygone. Dessinez-le autour de la zone où les clients sont assis, sans inclure inutilement les allées. Le point utilisé pour associer une personne à une table est le centre inférieur de sa boîte de détection (près des pieds).

Après modification, redémarrer le serveur.

## Webcam
L'index de caméra par défaut est `0`. Pour changer :
```powershell
$env:RESTO_CAMERA_INDEX="1"
uvicorn backend.main:app --reload
```

Linux/macOS :
```bash
export RESTO_CAMERA_INDEX=1
uvicorn backend.main:app --reload
```

Autres variables :
- `RESTO_MODEL` : modèle Ultralytics, défaut `yolo11n.pt`
- `RESTO_CONFIDENCE` : seuil de confiance, défaut `0.35`
- `RESTO_OCCUPY_SECONDS` : confirmation occupation, défaut `2`
- `RESTO_VACATE_SECONDS` : confirmation libération, défaut `5`
- `RESTO_CAMERA_WIDTH` : largeur demandée, défaut `1280`
- `RESTO_CAMERA_HEIGHT` : hauteur demandée, défaut `720`

## Dépannage
- **Caméra indisponible** : fermer les applications qui utilisent déjà la webcam ; essayer l'index 1 ; vérifier les autorisations caméra du système.
- **Écran vidéo noir** : vérifier la webcam et les journaux du terminal.
- **Performances faibles** : réduire `RESTO_CAMERA_WIDTH` et `RESTO_CAMERA_HEIGHT`, ou utiliser un modèle plus léger compatible avec Ultralytics.
- **Tables toujours libres** : les polygones de `tables.json` sont des exemples. Il faut les adapter à l'angle réel de la caméra.
- **YOLO ne se télécharge pas** : vérifier la connexion Internet puis relancer.

## Sécurité et vie privée
Cette version traite le flux localement et ne sauvegarde pas les vidéos. Les identifiants de suivi sont temporaires et ne constituent pas une identification personnelle. Pour un déploiement réel, informer les personnes concernées, limiter l'accès, définir une durée de conservation et vérifier les règles locales applicables à la vidéosurveillance.

## Prochaines étapes
1. Ajouter un assistant de calibration des zones directement dans l'interface.
2. Ajouter les actions serveur : « prise en charge », « commande prise », « commande servie », « paiement ».
3. Ajouter l'historique en base de données.
4. Ajouter les statistiques par créneau et par taille de groupe.
5. Connecter des caméras RTSP et gérer plusieurs flux.

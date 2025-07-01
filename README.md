# Solara Imagery Labeling Interface

## Purpose
Label geospatial imagery collaboratively with a lightweight, customizable platform for multiple simultaneous users.

## Running the Interface
The intended way to run this interface is using docker compose with the compose.yml. After cloning this repository, navigate to the repository and run the command:
```docker compose up -d```
To build the docker image and run the interface.

Settings for running the interface can be modified by editing the file ```solara-labeler/src/settings.yml```.

In order to run this interface with the original MA Orthophoto dataset it was designed for, clone the repository github.com/ClarkCGA/solara-labeler-datagen. Modify the ```compose.yml``` files in each repository to specify your data directory and run the dataset generation script. Then, modify the ```compose.yml``` file in this repository to mount the same data directory to the public directory within the container - for example:

```
    volumes:
      - /path/to/workspace/solara-labeler/:/home/jovyan/solara-labeler
      - /path/to/workspace/data/:/home/jovyan/solara-labeler/src/public/
```

## Architecture

### Core Components
1. **Frontend Interface**
   - Solara for reactive UI components
   - Leafmap for interactive mapping capabilities
   - Progress tracking and navigation controls

2. **Data Management**
   - LocalTileServer for serving local imagery
   - CSV tracking system for label boundaries and completion status
   - GeoJSON export functionality for annotated regions

3. **Application Flow**
   - Load imagery from local files using LocalTileServer or from pre-rendered tiles
   - Display imagery in Leafmap with AOI boundary boxes
   - Capture user-drawn ROIs and save to GeoJSON
   - Update tracking CSV to mark completed labels
   - Pre-load next images for seamless transition

### Directory Structure
```
/
├── Dockerfile
├── LICENSE
├── README.md
├── compose.yml
└── src
    ├── pages
    │   ├── 00_home.py
    │   └── 01_interface.py
    ├── public
    └── settings.yml
```

### Data Structures

#### Labels CSV Format
```
id,boundary,status,timestamp,username
1,data/imagery/chip1.tif,"[x1,y1,x2,y2]",pending,null
2,data/imagery/chip2.tif,"[x1,y1,x2,y2]",complete,2025-05-20T14:30:00Z
```

#### GeoJSON Annotation Format
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "id": 1,
        "label_class": "building",
        "timestamp": "2025-05-20T14:30:00Z"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[x1, y1], [x2, y2], ...]]
      }
    }
  ]
}
```

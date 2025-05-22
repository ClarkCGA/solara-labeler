# Solara Imagery Labeling Interface

## Purpose
Create an interactive web application using Solara that enables users to efficiently label imagery by drawing regions of interest (ROIs) on geospatial data. The application will track labeling progress and save user annotations in standardized formats.

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
   - Load imagery from local files using LocalTileServer
   - Display imagery in Leafmap with existing boundary boxes
   - Capture user-drawn ROIs and save to GeoJSON
   - Update tracking CSV to mark completed labels
   - Pre-load next images for seamless transition

### Directory Structure
```
/
├── compose.yml           # Docker compose configuration
├── Dockerfile            # Docker configuration
├── README.md             # Project documentation
└── pages/                # Solara pages
    └── interface.py     # Map interface
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
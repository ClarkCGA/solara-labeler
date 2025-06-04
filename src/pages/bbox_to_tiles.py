import math

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def bbox_to_tiles(bbox, zoom):
    # bbox = (min_lon, min_lat, max_lon, max_lat)
    min_x, max_y = deg2num(bbox[1], bbox[0], zoom)  # north-west corner
    max_x, min_y = deg2num(bbox[3], bbox[2], zoom)  # south-east corner
    tiles = []
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            tiles.append((zoom, x, y))
    return tiles

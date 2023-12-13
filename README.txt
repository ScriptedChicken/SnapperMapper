#Get Snapper Balance#

Ever forgotten where you've been on the bus? Worry no further with Get Snapper Balance!

update_snapper_data.py
- Pulls Snapper card data from their API
- Stores the data as GeoJSON for later

generate_snapper_map.py
- Gets stored GeoJSON data, creates a map per unique card stored in ./data/cards.json
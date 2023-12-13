# Snapper Mapper #

Ever forgotten where you've been on the bus? Worry no further with Snapper Mapper! And all this without entering a password. Just enter a card number and a CSV.

See the presentation here --> https://docs.google.com/presentation/d/1T8KictZybdOLU_0ER96j4-8EdvlBmGsOVw8Zse55lcM/edit?usp=sharing

update_snapper_data.py
- Pulls Snapper card data from Snapper's API
- Stores the data as GeoJSON for later
- Add card details in .data/cards.json with the following format:
{
    "card_number":123456789012345,
    "cvv":123
}

generate_snapper_map.py
- Gets stored GeoJSON data, creates a map per unique card stored in ./data/cards.json

Uses:
* Python
* QGIS
* API queries and network troubleshooting
* JSON
* ...and more

![Example map](./maps/1010000011267390.png) 
*Figure 1: Example map of one snapper card*

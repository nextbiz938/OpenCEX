# Pipe into `python manage.py shell`. Switches a pair to a manual ("Custom") reference price.
# Needed offline: wizard.py sets price_source=External, and order validation (Order.check_for_deviation)
# rejects every limit order with "no last price and no custom price" until an external feed
# (cryptocompare/binance) has answered or a first trade has set a last price.
import os
from core.models import PairSettings
from core.models.inouts.pair import Pair

pair = Pair.get(os.environ.get('PAIR', 'BTC-USDT'))
ps = PairSettings.objects.get(pair=pair)
ps.price_source = PairSettings.PRICE_SOURCE_CUSTOM
ps.custom_price = os.environ.get('CUSTOM_PRICE', '30000')
ps.save()
PairSettings._cache_data(set_cache=True)
print(f'{pair.code}: price_source=Custom custom_price={ps.custom_price} deviation={ps.deviation}')

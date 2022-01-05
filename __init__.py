import os
import sys

from flask import Blueprint
import entsoe


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

__version__ = "0.4"

entsoe_data_bp = Blueprint("entsoe", __name__)

DEFAULT_COUNTRY_CODE = "NL"
DEFAULT_COUNTRY_TIMEZONE = "Europe/Amsterdam"  # This is what we receive, even if ENTSO-E documents Europe/Brussels
DEFAULT_DERIVED_DATA_SOURCE = "FlexMeasures ENTSO-E"


entsoe_data_bp.cli.help = "ENTSO-E Data commands"


from .generation import day_ahead as day_ahead_generation  # noqa: E402,F401
from .prices import day_ahead as day_ahead_prices  # noqa: E402,F401
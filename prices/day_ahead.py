from typing import Optional
from datetime import datetime

import click
from flask.cli import with_appcontext
from flask import current_app
import pandas as pd

import entsoe
from entsoe import EntsoePandasClient
from flexmeasures.data.transactional import task_with_status_report

from . import pricing_sensors
from .. import (
    entsoe_data_bp,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_COUNTRY_TIMEZONE,
)  # noqa: E402
from ..utils import (
    create_entsoe_client,
    ensure_country_code_and_timezone,
    ensure_data_source,
    parse_from_and_to_dates_default_today_and_tomorrow,
    ensure_sensors,
    save_entsoe_series,
    get_auth_token_from_config_and_set_server_url,
    abort_if_data_empty,
    start_import_log,
)


@entsoe_data_bp.cli.command("import-day-ahead-prices")
@click.option(
    "--from-date",
    required=False,
    type=click.DateTime(["%Y-%m-%d"]),
    help="Query data from this date onwards. If not specified, defaults to today",
)
@click.option(
    "--to-date",
    required=False,
    type=click.DateTime(["%Y-%m-%d"]),
    help="Query data until this date (inclusive). If not specified, defaults to tomorrow.",
)
@click.option(
    "--dryrun/--no-dryrun",
    default=False,
    help="In dry run mode, do not save the data to the db.",
)
@click.option(
    "--country",
    "country_code",
    required=False,
    help="ENTSO-E country code (such as BE, DE, FR or NL).",
)
@click.option(
    "--timezone",
    "country_timezone",
    required=False,
    help="Timezone for the country (such as 'Europe/Amsterdam').",
)
@with_appcontext
@task_with_status_report("entsoe-import-day-ahead-prices")
def import_day_ahead_prices(
    dryrun: bool = False,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    country_code: Optional[str] = None,
    country_timezone: Optional[str] = None,
):
    """
    Import forecasted prices for any date range, defaulting to today and tomorrow.
    Possibly best to run this script somewhere around or maybe two or three hours after 13:00,
    when tomorrow's prices are announced.
    """
    # Set up FlexMeasures data structure
    country_code, country_timezone = ensure_country_code_and_timezone(country_code, country_timezone)
    sensors = ensure_sensors(pricing_sensors, country_code, country_timezone)
    entsoe_data_source = ensure_data_source()
    # For now, we only have one pricing sensor ...
    pricing_sensor = sensors["Day-ahead prices"]
    assert pricing_sensor.name == "Day-ahead prices"

    # Parse CLI options (or set defaults)
    from_time, until_time = parse_from_and_to_dates_default_today_and_tomorrow(
        from_date, to_date, country_timezone
    )

    # Start import
    client = create_entsoe_client()
    log, now = start_import_log("day-ahead price", from_time, until_time, country_code, country_timezone)

    log.info("Getting prices ...")
    prices: pd.Series = client.query_day_ahead_prices(
        country_code, start=from_time, end=until_time
    )
    abort_if_data_empty(prices)
    log.debug("Prices: \n%s" % prices)

    if not dryrun:
        log.info(f"Saving {len(prices)} beliefs for Sensor {pricing_sensor.name} ...")
        prices.name = "event_value"  # required by timely_beliefs, TODO: check if that still is the case, see https://github.com/SeitaBV/timely-beliefs/issues/64
        save_entsoe_series(prices, pricing_sensor, entsoe_data_source, country_timezone, now)

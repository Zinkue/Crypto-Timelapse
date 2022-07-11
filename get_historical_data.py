import requests
import json
import pandas as pd
import sys
import datetime
import time
import argparse


def ping_server():
    """
    Checks the connection with the CoinGecko API

    Returns the status code of the request
    """

    r = requests.get("https://api.coingecko.com/api/v3/ping")
    if r.status_code != 200:
        print("The API is not available at this moment. Try it later")
        sys.exit()


def get_crypto_id(**kwargs):
    """
    Sends a GET request to CoinGecko API /coins/markets

    Returns a pandas DataFrame with the id, name, symbol and the current market cap rank

    Keyword Args:
        vs_currency (str): The target currency of market data.
            Complete list in https://api.coingecko.com/api/v3/simple/supported_vs_currencies Default usd
        order (str): sort results by field. Default market_cap_desc
            Valid values: market_cap_desc, gecko_desc, gecko_asc, market_cap_asc, market_cap_desc,
            volume_asc, volume_desc, id_asc, id_desc
        per_page (int): Total results per page. Default 100 Valid values: 1-250
    """

    # Default args
    args = {"vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100}

    # Valid keyword args
    supported_vs_currencies = requests.get("https://api.coingecko.com/api/v3/simple/supported_vs_currencies")
    supported_vs_currencies = supported_vs_currencies.content.decode("utf-8")[1:-1].replace("\"", "").split(",")
    valid_keyword_args = {"vs_currency": supported_vs_currencies,
                          "order": ["market_cap_desc", "gecko_desc", "gecko_asc", "market_cap_asc",
                                    "volume_asc", "volume_desc", "id_asc", "id_desc"],
                          "per_page": range(1, 251)}

    # Check and update the args
    if len(kwargs) > 0:
        for key, value in kwargs.items():
            if key not in valid_keyword_args.keys():
                print(f"{key} is not a valid argument")
                sys.exit()
            elif value not in valid_keyword_args[key]:
                print(f"{value} it not a valid value for {key}")
                sys.exit()

        args = {**args, **kwargs}

    # Send a request and get the data
    url = "https://api.coingecko.com/api/v3/coins/markets?" \
          f"vs_currency={str(args['vs_currency'])}&" \
          f"order={str(args['order'])}&" \
          f"per_page={str(args['per_page'])}&" \
          f"page=1&sparkline=false"
    r = requests.get(url)
    response = json.loads(r.content.decode("utf-8"))
    data = pd.DataFrame(response)
    data = data[["id", "name", "symbol", "market_cap_rank"]]

    return data, args["vs_currency"]


def get_historical_data(data, vs_currency, from_date, to_date=None):
    """
    Sends a GET request to CoinGecko API /coins/{id}/market_chart/range

    Data granularity is automatic (cannot be adjusted)
    1 day from current time = 5 minute interval data
    1 - 90 days from current time = hourly data
    above 90 days from current time = daily data (00:00 UTC)

    Returns a csv with the id, name, symbol ,current market cap rank_today, time, price, market cap and 24h volume

    Args:
        data (pandas.DataFrame): data returned by get_crypto_id()
        vs_currency (str): vs_currency returned by get_crypto_id()
        from_date (str): Date in string format yyyy-MM-dd or yyyy-MM-dd hh:mm:ss
        to_date (str): Date in string format yyyy-MM-dd or yyyy-MM-dd hh:mm:ss Default datetime.datetime.today()
    """
    # Initialize the elements
    data_end = pd.DataFrame([])
    wait_time = 2.2

    # Default to_date and check
    if to_date is None:
        to_date = int(datetime.datetime.timestamp(datetime.datetime.today()))
    else:
        try:
            to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                print(f"{to_date} is not in format yyyy-MM-dd or yyyy-MM-dd hh:mm:ss")
                sys.exit()
        to_date = int(datetime.datetime.timestamp(to_date))

    # Default from_date and check
    try:
        from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
        from_date = int(datetime.datetime.timestamp(from_date))
    except ValueError:
        try:
            from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d")
            from_date = int(datetime.datetime.timestamp(from_date))
        except ValueError:
            print(f"{from_date} is not in format yyyy-MM-dd or yyyy-MM-dd hh:mm:ss")
            sys.exit()

    # Obtain the data_id for each id
    pos = 1
    for ID in data["id"].unique():
        print(f"{pos}/{data['id'].unique().size}", end=" ")
        print("Downloading the historical data for:", ID)
        url = f"https://api.coingecko.com/api/v3/coins/{ID}/market_chart/range?" \
              f"vs_currency={vs_currency}&" \
              f"from={from_date}&to={to_date}"
        r = requests.get(url)
        while r.status_code != 200:
            print("Exceeded API calls. Wait time 30s")
            time.sleep(30)
            wait_time += 0.1
            r = requests.get(url)
        response = json.loads(r.content.decode("utf-8"))

        # Data analyze for different length
        size = {"prices": len(response["prices"]),
                "market_caps": len(response["market_caps"]),
                "total_volumes": len(response["total_volumes"])}
        min_size_key = min(size, key=size.get)
        times = pd.DataFrame(response[min_size_key])[0]
        data_prices = pd.DataFrame(response["prices"])
        data_prices = data_prices[data_prices[0].isin(times.values)][1]
        data_market_caps = pd.DataFrame(response["market_caps"])
        data_market_caps = data_market_caps[data_market_caps[0].isin(times.values)][1]
        data_total_volumes = pd.DataFrame(response["total_volumes"])
        data_total_volumes = data_total_volumes[data_total_volumes[0].isin(times.values)][1]
        times = times.map(lambda x: datetime.datetime.fromtimestamp(x // 1000))

        # Create dataframe structure
        data_id = pd.concat([times, data_prices, data_market_caps, data_total_volumes], axis=1)
        data_id.columns = ["timestamp", "prices", "market_caps", "total_volumes"]
        data_id["name"] = data[data.id == ID]["name"].iloc[0]
        data_id["symbol"] = data[data.id == ID]["symbol"].iloc[0]
        data_id["market_cap_rank_today"] = data[data.id == ID]["market_cap_rank"].iloc[0]

        # Concatenate all data_id
        data_end = pd.concat([data_end, data_id])

        # Wait time for not exceeded API calls
        time.sleep(wait_time)

        pos += 1

    # Save date_end into csv file
    start_time = data_end["timestamp"].min().strftime("%Y%m%d%H%M%S")
    end_time = data_end["timestamp"].max().strftime("%Y%m%d%H%M%S")
    file_name = f"CryptoData_{start_time}_{end_time}.csv"
    data_end.to_csv(file_name, index=False)


def main():
    # Parses the arguments from the terminal
    parser = argparse.ArgumentParser()
    parser.add_argument("from_date", type=str, help="Date in string format yyyy-MM-dd or yyyy-MM-dd hh:mm:ss")
    parser.add_argument("--to_date", type=str,
                        help="Date in string format yyyy-MM-dd or yyyy-MM-dd hh:mm:ss "
                             "Default datetime.datetime.today()")
    parser.add_argument("--vs_currency", type=str,
                        help="The target currency of market data. "
                             "Complete list in https://api.coingecko.com/api/v3/simple/supported_vs_currencies "
                             "Default usd")
    parser.add_argument("--order", type=str,
                        help="sort results by field. Default market_cap_desc "
                             "Valid values: market_cap_desc, gecko_desc, gecko_asc, market_cap_asc, "
                             "market_cap_desc, volume_asc, volume_desc, id_asc, id_desc")
    parser.add_argument("--per_page", type=int,
                        help="Total results per page. Default 100 Valid values: 1-250")
    args = vars(parser.parse_args())

    # Remove None values
    for key, value in args.copy().items():
        if value is None:
            del args[key]

    # Create the dict for the functions
    get_historical_data_args = {"from_date": args["from_date"]}
    del args["from_date"]
    get_crypto_id_args = args

    # Run the functions
    ping_server()
    id_data, currency = get_crypto_id(**get_crypto_id_args)
    get_historical_data_args = {**{"data": id_data, "vs_currency": currency},
                                **get_historical_data_args}
    get_historical_data(**get_historical_data_args)


if __name__ == "__main__":
    main()

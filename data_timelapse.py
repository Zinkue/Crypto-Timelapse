import pandas as pd
import plotly.graph_objects as go
import sys
import argparse


def group_market_cap_rank(x):
    group = "101-"
    for i in range(0, 91, 10):
        if x in range(1 + i, 11 + i):
            group = f"{1 + i}-{11 + i - 1}"
            break

    return group


def data_timelapse(data_path, type_data="all_data"):
    """
    Create a Plotly animation from data obtained by get_historical_data.py

    Args:
        data_path (str): Path to data obtained from get_historical_data.py
        type_data (str): Select the quantity of data to plot
            Valid values: all_data, symbols_all_date_range, symbols_with_common_date_range
            Default all_data
    """
    # Check type_data
    if type_data not in ["all_data", "symbols_all_date_range", "symbols_with_common_date_range"]:
        print(f"{type_data} is not a valid type")
        sys.exit()

    # Read data and filter it
    data = pd.read_csv(data_path)
    if type_data == "symbols_all_date_range":
        count = data.groupby(by="symbol").count()["name"].max()
        symbols = data.groupby(by="symbol").count()["name"][data.groupby(by="symbol").count()["name"] == count].index
        data = data[data["symbol"].isin(symbols)]
    elif type_data == "symbols_with_common_date_range":
        num_symbols = len(data["symbol"].unique())
        min_date = (data.groupby(by="Timestamp").count()["symbol"]
                    [data.groupby(by="Timestamp").count()["symbol"] == num_symbols].idxmin())
        data = data[data["Timestamp"] >= min_date]

    # Add columns to data
    data["group_market_cap_rank"] = data["market_cap_rank"].map(lambda x: group_market_cap_rank(x))
    data["percentage_change_from_start"] = 0
    for name in data["name"].unique():
        start_price = data[data["name"] == name]["prices"].iloc[0]
        data.loc[data["name"] == name, ["percentage_change_from_start"]] = \
            (data[data["name"] == name]["prices"] / start_price - 1) * 100
    print("Filtered data an added columns")

    # Create the frames and slider
    fig = go.Figure(frames=[go.Frame(data=[
        go.Scatter(
            x=data[(data["Timestamp"] == year) & (data["group_market_cap_rank"] == group)]["group_market_cap_rank"],
            y=data[(data["Timestamp"] == year) & (data["group_market_cap_rank"] == group)]
            ["percentage_change_from_start"],
            mode="markers",
            name=str(group),
            customdata=data[(data["Timestamp"] == year) & (data["group_market_cap_rank"] == group)].values,
            hovertemplate="<b>%{customdata[4]}</b><br>" +
            "Price: %{customdata[0]:.5f}<br>" +
            "Percentage change from start: %{y:.2f}%<br>" +
            "Market cap rank : %{customdata[6]}" +
            "<extra></extra>"
        ) for group in data["group_market_cap_rank"].unique()] +
        [
        go.Scatter(
            x=[data["group_market_cap_rank"].unique()[0], data["group_market_cap_rank"].unique()[-1]],
            y=[data[data["Timestamp"] == year]["percentage_change_from_start"].mean(),
               data[data["Timestamp"] == year]["percentage_change_from_start"].mean()],
            mode="lines+text",
            text=[round(data[data["Timestamp"] == year]["percentage_change_from_start"].mean(), 2),
                  round(data[data["Timestamp"] == year]["percentage_change_from_start"].mean(), 2)],
            textposition="bottom right",
            name='Mean')
        ],
        name=str(year))
        for year in data["Timestamp"].unique()])

    sliders = [
        {
            "pad": {"b": 10, "t": 30},
            "len": 0.9,
            "x": 0.1,
            "y": 0,
            "steps": [
                {
                    "args": [[f.name], {"frame": {"duration": 250, "redraw": False},
                                        "mode": "immediate",
                                        "fromcurrent": True,
                                        "transition": {"duration": 250, "easing": "quadratic-in-out"}}],
                    "label": f.name,
                    "method": "animate"
                }
                for f in fig.frames
            ]
        }
    ]
    print("Created the frames and slider")

    # Initialize the data before animation
    start_year = data["Timestamp"].unique()[0]
    fig.add_traces([
        go.Scatter(
            x=data[(data["Timestamp"] == start_year) & (data["group_market_cap_rank"] == group)]
            ["group_market_cap_rank"],
            y=data[(data["Timestamp"] == start_year) & (data["group_market_cap_rank"] == group)]
            ["percentage_change_from_start"],
            mode="markers",
            name=str(group),
            customdata=data[(data["Timestamp"] == start_year) & (data["group_market_cap_rank"] == group)].values,
            hovertemplate="<b>%{customdata[4]}</b><br>" +
            "Price: %{customdata[0]:.5f}<br>" +
            "Percentage change from start: %{y:.2f}%<br>" +
            "Market cap rank : %{customdata[6]}" +
            "<extra></extra>",
        ) for group in data["group_market_cap_rank"].unique()] + [
        go.Scatter(
            x=[data["group_market_cap_rank"].unique()[0], data["group_market_cap_rank"].unique()[-1]],
            y=[data[data["Timestamp"] == start_year]["percentage_change_from_start"].mean(),
               data[data["Timestamp"] == start_year]["percentage_change_from_start"].mean()],
            mode="lines+text",
            text=[round(data[data["Timestamp"] == start_year]["percentage_change_from_start"].mean(), 2),
                  round(data[data["Timestamp"] == start_year]["percentage_change_from_start"].mean(), 2)],
            textposition="bottom right",
            name='Mean')
    ])
    print("Initialized the data before animation")

    # Layout
    fig.update_layout(
        title="Crypto timelapse",
        yaxis=dict(range=[-200, data["percentage_change_from_start"].max()*1.1],
                   autorange=False, ticksuffix=" %"),
        updatemenus=[
            {
                "buttons": [
                    {
                        "args": [None, {"frame": {"duration": 250, "redraw": False},
                                        "mode": "immediate",
                                        "fromcurrent": True,
                                        "transition": {"duration": 250, "easing": "quadratic-in-out"}}],
                        "label": "Play",
                        "method": "animate"
                    },
                    {
                        "args": [[None], {"frame": {"duration": 0, "redraw": False},
                                          "mode": "immediate",
                                          "fromcurrent": True,
                                          "transition": {"duration": 0}}],
                        "label": "Pause",
                        "method": "animate"
                    }
                ],
                "direction": "left",
                "pad": {"r": 10, "t": 45},
                "type": "buttons",
                "x": 0.1,
                "y": 0
            }
        ],
        sliders=sliders
    )
    print("Created the layout")

    # Save the figure into html
    fig.write_html("data_timelapse.html", auto_open=True)


def main():
    # Parses the arguments from the terminal
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path", type=str, help="Path to data")
    parser.add_argument("--type_data", type=str,
                        help="Select the quantity of data to plot "
                             "Valid values: all_data, symbols_all_date_range, symbols_with_common_date_range "
                             "Default all_data")
    args = vars(parser.parse_args())

    # Run the function
    if args["type_data"] is None:
        data_timelapse(args["data_path"])
    else:
        data_timelapse(args["data_path"], args["type_data"])


if __name__ == "__main__":
    main()

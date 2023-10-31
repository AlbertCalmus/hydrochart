import flet as ft
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from flet.matplotlib_chart import MatplotlibChart
from matplotlib import use
from pathlib import Path

from utils.data import fetch_data_from_api, get_sorted_spaced_maxes, generate_daily_params, generate_hourly_params
from utils.store import Store

use("svg")

def main(page: ft.Page):
    page.title = "HydroChart v1.0.0"
    page.window_height, page.window_min_height= 800, 800
    page.window_width, page.window_min_width = 1200, 1200

    store = Store()

    station_code_input = ft.TextField(
        label="Station code",
        capitalization=ft.TextCapitalization.CHARACTERS,
        value="K4470010",
        width=160
    )

    start_date_input = ft.TextField(
        label="Start date (YYYY-MM-DD)",
        value="1900-01-01",
        width=200
    )

    end_date_input = ft.TextField(
        label="End date (YYYY-MM-DD)",
        value="2023-10-31",
        width=200
    )

    time_delta_input = ft.TextField(
        label="Time delta (in days)",
        value=10,
        width=160
    )

    nb_floods_input = ft.TextField(
        label="Number of floods",
        value=5,
        width=160
    )

    list_view = ft.ListView(controls=[], expand=True)

    chart = MatplotlibChart(expand=True, visible=False)

    def list_view_item(date: str, color: str):
        return ft.Row(controls=[
                    ft.Container(
                        ft.Text(value=date),
                            alignment=ft.alignment.center,
                            bgcolor=f"#26{color[1:]}",
                            padding=10,
                            margin=5,
                            border_radius=ft.border_radius.all(5),
                            expand=True
                    ),
                    ft.Container(
                        ft.IconButton(
                            data=date,
                            icon=ft.icons.DELETE_SHARP,
                            icon_size=25,
                            on_click=delete_chro,
                            icon_color="#285F9F"
                        ),
                        margin=ft.margin.only(right=15)
                    )])

    def notify(page: ft.Page, text: str, color: str):
        page.snack_bar = ft.SnackBar(ft.Text(text), padding=10)
        page.snack_bar.bgcolor = color
        page.snack_bar.open = True
        page.update()
    
    def refresh_list_view():
        list_view.controls = [ list_view_item(date, item['color']) for date, item in store.data.items() ]
        list_view.update()

    def delete_chro(e):
        if len(store.data) > 1:
            del store.data[e.control.data]
            refresh_list_view()
            refresh_store_and_chart(chart)
        else:
            notify(page, "You must keep at least one peak", ft.colors.ERROR)

    def export_to_svg(e):
        try:
            plt.savefig(str(Path.home() / "Downloads" / f"{station_code_input.value}_{start_date_input.value}_{end_date_input.value}.svg"))
            notify(page, "Successfully saved, check your Downloads folder.", ft.colors.GREEN_ACCENT_700)
        except:
            notify(page, "Something wrong happened while exporting your graph to SVG.", ft.colors.ERROR)
    
    def export_to_excel(e):
        try:
            filepath = str(Path.home() / "Downloads" / f"{station_code_input.value}_{start_date_input.value}_{end_date_input.value}.xlsx")
            with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
                store.normalized.to_excel(writer, sheet_name="normalized", index=False)
                for k, item in store.data.items():
                    item["df"].to_excel(writer, sheet_name=k, index=False)
            notify(page, "Successfully saved, check your Downloads folder.", ft.colors.GREEN_ACCENT_700)
        except:
            notify(page, "Something wrong happened while exporting your data to Excel.", ft.colors.ERROR)

    def refresh_store_and_chart(chart: MatplotlibChart):
        delta = int(time_delta_input.value)
        x = np.arange(-delta, delta, 0.025)

        fig, ax = plt.subplots()
        fig.tight_layout()

        for _, item in store.data.items():
            ax.plot(item["x"], item["y"], color=item["color"], alpha=0.15)

        store.normalized = pd.DataFrame({
            "t": x,
            "v": np.mean([ item["y"] for _, item in store.data.items() ], axis=0)
        })

        ax.plot(store.normalized["t"], store.normalized["v"], color="#285F9F")
        chart.figure = fig
        chart.update()


    export_to_excel_button = ft.FilledButton("Export data to Excel", icon="table_chart", height=30, on_click=export_to_excel, disabled=True)
    export_to_svg_button = ft.FilledButton("Export graph to SVG", icon="image", height=30, on_click=export_to_svg, disabled=True)

    actions_container = ft.Container(
        content=ft.Row(controls=[
            export_to_excel_button,
            export_to_svg_button
        ], alignment=ft.MainAxisAlignment.CENTER),
        height=100,
        border_radius=ft.border_radius.all(5),
        padding=10,
        margin=10
    )

    def search(e):
        store.clear()
        chart.visible = False
        list_view.controls = []
        export_to_excel_button.disabled = True
        export_to_svg_button.disabled = True

        list_view.update()
        actions_container.update()
        chart.update()

        delta = int(time_delta_input.value)

        data, err = fetch_data_from_api(station_code_input.value, generate_daily_params(pd.Timestamp(start_date_input.value), pd.Timestamp(end_date_input.value)))
        if err != None:
            notify(page, "Something wrong happened while fetching the data from the API.", ft.colors.ERROR)
            return
        
        sorted_spaced_maxes = get_sorted_spaced_maxes(data, int(nb_floods_input.value), delta)

        x = np.arange(-delta, delta, 0.025)
        ys = []

        fig, ax = plt.subplots()
        fig.tight_layout()
        
        chart.visible = True
        for _, row in sorted_spaced_maxes.iterrows():
            peak_date = row["t"]
            start_date, end_date = peak_date - pd.Timedelta(days=delta), peak_date + pd.Timedelta(days=delta)
            data, err = fetch_data_from_api(station_code_input.value, generate_hourly_params(start_date, end_date))
            if err != None:
                notify(page, f"Could not fetch hourly data for flood {peak_date}", ft.colors.ORANGE_ACCENT)
                continue
            
            chro_df = pd.DataFrame(data)[["t", "v"]]
            chro_df["t"] = pd.to_datetime(chro_df["t"], format='%Y-%m-%dT%H:%M:%SZ')
            chro_df["t_norm"] = (chro_df["t"] - chro_df.loc[chro_df["v"].idxmax()]["t"]).dt.total_seconds() / (24 * 3600)
            chro_df["v_norm"] = chro_df["v"] / max(chro_df["v"])
            
            y = np.interp(x, chro_df["t_norm"], chro_df["v_norm"])
            ys.append(y)

            row_plot, = ax.plot(x, y, alpha=0.15)

            store.data[peak_date.strftime('%Y-%m-%d')] = {
                "df": chro_df[["t", "v"]],
                "x": x,
                "y": y,
                "color": row_plot.get_color()
            }

            refresh_list_view()
            chart.figure = fig
            chart.update()

        mean_y = np.mean(ys, axis=0)
        store.normalized = pd.DataFrame({"t": x, "v": mean_y})
        ax.plot(x, mean_y, color="#285F9F")

        export_to_excel_button.disabled = False
        export_to_svg_button.disabled = False
        page.update()

    LAYOUT = ft.Column(controls=[
            ft.Container(
                content=ft.Row(controls=[
                    station_code_input,
                    start_date_input,
                    end_date_input,
                    time_delta_input,
                    nb_floods_input,
                    ft.FilledButton("Search", icon="search", height=50, on_click=search)
                ], alignment=ft.MainAxisAlignment.CENTER),
                height=100,
                border_radius=ft.border_radius.all(5),
                padding=10
            ),
            ft.Row(controls=[
                ft.Container(
                    content=list_view,
                    alignment=ft.alignment.center,
                    width=300,
                    border_radius=ft.border_radius.all(5),
                    margin=ft.margin.only(left=50)
                ),
                ft.Container(
                    content=chart,
                    alignment=ft.alignment.center,
                    expand=True,
                    border_radius=ft.border_radius.all(5)
                )
            ], expand=True),
            actions_container,
    ], expand=True)
    page.add(LAYOUT)

ft.app(target=main)
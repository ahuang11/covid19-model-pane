import panel as pn
import numpy as np
import pandas as pd
import hvplot.pandas
import holoviews as hv
from bokeh.models import HoverTool

hv.renderer('bokeh').theme = 'caliber'
pn.extension(backend='bokeh')

WORLD_DATA_URL = 'https://covid.ourworldindata.org/data/ecdc/full_data.csv'
US_CASES_DATA_URL = (
    'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/'
    'csse_covid_19_data/csse_covid_19_time_series/'
    'time_series_19-covid-Confirmed.csv'
)
US_DEATHS_DATA_URL = (
    'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/'
    'csse_covid_19_data/csse_covid_19_time_series/'
    'time_series_19-covid-Deaths.csv'
)
DATA_TAG = (f'<a href="{WORLD_DATA_URL}">world full data</a>, '
            f'<a href="{US_CASES_DATA_URL}">US cases data</a>, '
            f'<a href="{US_DEATHS_DATA_URL}">US deaths data</a>')

YOUTUBE_TAG = '<a href="https://youtube.com/watch?v=Kas0tIxDvrg">video</a>'
WORLD_POPULATION = 7794798739
HVPLOT_KWDS = dict(
    responsive=True, ylim=(1, None), grid=True,
)
FOOTER = (
    f'Thanks to Our World in Data and Johns Hopkins University Center for '
    f'Systems Science and Engineering for providing the {DATA_TAG} and '
    f'3Blue1Brown\'s "Exponential growth and epidemics" {YOUTUBE_TAG} for the '
    f'inspiration & formula. Created primarily with numpy, pandas, panel, '
    f'holoviews, and bokeh in Python.')

def process_us_df(kind):
    if kind == 'total_cases':
        url = US_CASES_DATA_URL
    else:
        url = US_DEATHS_DATA_URL
    us_df = pd.read_csv(url)
    us_df = us_df.loc[us_df['Country/Region'] == 'US'].drop(
        columns=['Country/Region', 'Lat', 'Long']
    ).melt(
        'Province/State', var_name='date', value_name=kind
    ).rename(columns={
        'Province/State': 'location'
    })
    us_df['date'] = pd.to_datetime(us_df['date'])
    return us_df


### Preprocess data

worldwide_df = pd.read_csv(WORLD_DATA_URL)
worldwide_df['location'] = worldwide_df['location'].str.replace("'", '`')
num_days = int(worldwide_df['location'].value_counts().max())
start_date = pd.to_datetime(worldwide_df['date'].min())
worldwide_df['date'] = pd.to_datetime(worldwide_df['date'])

us_df = pd.merge(
    process_us_df('total_cases'),
    process_us_df('total_deaths'),
    on=['location', 'date'],
).sort_values(['location', 'date'])

us_df = us_df.join(
    us_df.groupby('location')[['total_cases', 'total_deaths']].diff().rename(
    columns={'total_cases': 'new_cases', 'total_deaths': 'new_deaths'}).fillna(0)
)

full_df = pd.concat([worldwide_df, us_df], sort=False)

locations_list = (
    sorted(worldwide_df['location'].unique().tolist()) +
    sorted(us_df['location'].unique().tolist())
)
locations_list.remove('World')

### Define widgets

data_options = pn.widgets.RadioButtonGroup(
    options=['Total cases', 'Total deaths', 'New deaths', 'New cases'],
    value='Total cases', sizing_mode='stretch_width',
)
time_options = pn.widgets.RadioButtonGroup(
    options=['By date', 'By days'],
    value='By date', sizing_mode='stretch_width',
)
location_options = pn.widgets.MultiSelect(
    options=locations_list,
    value=['United States', 'South Korea', 'Italy', 'Illinois'],
    sizing_mode='stretch_height'
)
log_toggle = pn.widgets.Toggle(name='Logarithmic Scale', value=True)
world_toggle = pn.widgets.Toggle(name='Show World Total', value=True)

### Define function

@pn.interact(average_number_of_people_exposed_daily=(0, 1000., 1, 5),
             probability_of_infection=(0, 0.1, 0.001, 0.03),
             number_of_days=(0, 720., 1, num_days),
             number_of_cases=(0, 1e5, 1., 1),
             report_threshold=(0, 1000, 1, 1),
             data_column=data_options,
             time_column=time_options,
             log_scale=log_toggle,
             show_world=world_toggle,
             locations=location_options)
def layout(average_number_of_people_exposed_daily, probability_of_infection,
           number_of_days, number_of_cases, report_threshold,
           data_column, time_column, log_scale, show_world, locations):
    if time_column == 'By date':
        time_col = 'date'
        hover_cols = ['days']
        xlabel = 'Date'
    else:
        time_col = 'days'
        hover_cols = ['date']
        xlabel = f'Days since {report_threshold} reports'

    data_col = data_column.lower().replace(' ', '_')
    columns = ['days', 'date', 'location', data_col]

    days_df = full_df.fillna(0)
    days_df = days_df.loc[days_df[data_col] >= report_threshold]

    days_df['days'] = 1
    days_df = (
        days_df
        .drop(columns='days')
        .set_index(['location', 'date'])
        .join(
            days_df.groupby(['location', 'date']).sum()
            .groupby('location')['days'].cumsum()
        )
    ).reset_index()
    days_df['days'] -= 1

    observed_df = days_df.loc[
        days_df['location'] != 'World', columns
    ]

    location_df = observed_df.loc[observed_df['location'].isin(locations)]
    location_line = location_df.hvplot.line(
        time_col, data_col, by='location',
        hover_cols=hover_cols, **HVPLOT_KWDS)

    days = np.arange(number_of_days)
    Nd = (1 + average_number_of_people_exposed_daily *
          probability_of_infection) ** days * number_of_cases
    model_df = pd.DataFrame({data_col: Nd}, index=days).rename_axis('days')
    model_df['date'] = start_date + pd.to_timedelta(days, unit='D')
    exceed_case = model_df[data_col] > WORLD_POPULATION
    model_df.loc[exceed_case, data_col] = WORLD_POPULATION
    model_line = model_df.hvplot.line(
        time_col, data_col, label='Model', logy=log_scale,
        hover_cols=hover_cols, **HVPLOT_KWDS
    ).opts(line_dash='dashed', line_width=5,
           xlabel=xlabel,
           ylabel='Reports by ECDC & JHU CSSE')

    overlay_lines = (model_line * location_line).opts(
        'Curve', toolbar='above')

    if show_world:
        world_df = days_df.loc[
            days_df['location'] == 'World', columns
        ]
        world_line = world_df.hvplot.line(
            time_col, data_col, label='World',
            hover_cols=hover_cols,
            color='black', **HVPLOT_KWDS)
        overlay_lines *= world_line

    pane = pn.pane.HoloViews(overlay_lines, sizing_mode='stretch_both',
                             min_height=500)
    return overlay_lines

widgets = pn.WidgetBox(layout[0], sizing_mode='stretch_height')
plot = layout[1]
for widget in widgets[0]:
    widget.name = widget.name.replace('_', ' ').capitalize()
plot.set_param(sizing_mode='stretch_both')
view = pn.Row(widgets, plot, sizing_mode='stretch_both')
footer_md = pn.pane.Markdown(
    object=FOOTER, sizing_mode='stretch_width', height=20)
dashboard = pn.Column(view, footer_md, sizing_mode='stretch_both')
dashboard.servable(title='COVID19 Model Pane')

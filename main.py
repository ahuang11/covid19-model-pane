import panel as pn
import numpy as np
import pandas as pd
import hvplot.pandas
import holoviews as hv
from bokeh.models import HoverTool

hv.renderer('bokeh').theme = 'caliber'
pn.extension(backend='bokeh')

DATA_URL = 'https://covid.ourworldindata.org/data/who/full_data.csv'
DATA_TAG = f'<a href="{DATA_URL}">data</a>'
YOUTUBE_TAG = '<a href="https://youtube.com/watch?v=Kas0tIxDvrg">video</a>'
WORLD_POPULATION = 7794798739
HVPLOT_KWDS = dict(
    responsive=True, ylim=(1, None), grid=True,
)
FOOTER = (
    f'Thanks to Our World in Data for providing the {DATA_TAG} and '
    f'3Blue1Brown\'s "Exponential growth and epidemics" {YOUTUBE_TAG} for the '
    f'inspiration & formula. Created primarily with numpy, pandas, panel, '
    f'holoviews, and bokeh in Python.')

### Preprocess data

full_df = pd.read_csv(DATA_URL)
full_df['location'] = full_df['location'].str.replace("'", '`')
num_days = int(full_df['location'].value_counts().max())
locations_list = sorted(full_df['location'].unique().tolist())
locations_list.remove('World')
start_date = pd.to_datetime(full_df['date'].min())
full_df['date'] = pd.to_datetime(full_df['date'])

### Define widgets

data_options = pn.widgets.RadioButtonGroup(
    options=['Total cases', 'Total deaths', 'New deaths', 'New cases'],
    value='Total cases', sizing_mode='stretch_width',
)
time_options = pn.widgets.RadioButtonGroup(
    options=['By date', 'By days since first report'],
    value='By date', sizing_mode='stretch_width',
)
location_options = pn.widgets.MultiSelect(
    options=locations_list,
    value=['United States', 'South Korea', 'Italy', 'Singapore'],
    sizing_mode='stretch_height'
)
log_toggle = pn.widgets.Toggle(name='Logarithmic Scale', value=True)
world_toggle = pn.widgets.Toggle(name='Show World Total', value=True)

### Define function

@pn.interact(average_number_of_people_exposed_daily=(0, 1000., 1, 5),
             probability_of_infection=(0, 0.1, 0.001, 0.03),
             number_of_days=(0, 720., 1, num_days),
             number_of_cases=(0, 1e5, 1., 1),
             data_column=data_options,
             time_column=time_options,
             log_scale=log_toggle,
             show_world=world_toggle,
             locations=location_options)
def layout(average_number_of_people_exposed_daily, probability_of_infection,
           number_of_days, number_of_cases, data_column, time_column,
           log_scale, show_world, locations):
    if time_column == 'By date':
        time_col = 'date'
        hover_cols = ['days']
        xlabel = 'Date'
    else:
        time_col = 'days'
        hover_cols = ['date']
        xlabel = f'Days since first report'

    data_col = data_column.lower().replace(' ', '_')
    columns = ['days', 'date', 'location', data_col]

    days_df = full_df.fillna(0).reset_index()
    days_df = days_df.loc[days_df[data_col] != 0]
    days_df['days'] = 1
    days_df['days'] = (
        days_df.groupby(['index', 'location'])
        .sum().groupby('location')['days'].cumsum()
    ).values - 1

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
           ylabel='Reports by WHO')

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

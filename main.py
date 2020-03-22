import panel as pn
import numpy as np
import pandas as pd
import hvplot.pandas
import holoviews as hv
from bokeh.models import HoverTool

hv.renderer('bokeh').theme = 'caliber'
pn.extension(backend='bokeh')

DATA_URL = 'https://covid.ourworldindata.org/data/ecdc/total_cases.csv'
DATA_TAG = f'<a href="{DATA_URL}">data</a>'
YOUTUBE_TAG = '<a href="https://youtube.com/watch?v=Kas0tIxDvrg">video</a>'
START_DATE = pd.to_datetime('2020-01-21')
WORLD_POPULATION = 7794798739
XLABEL = f'Days from {START_DATE:%Y-%m-%d}'
YLABEL = 'Cases'
HVPLOT_KWDS = dict(
    xlabel=XLABEL, ylabel=YLABEL, hover_cols=['date'], responsive=True,
    logy=True, xlim=(0, None), ylim=(1, None), grid=True,
)
FOOTER = (
    f'Thanks to Our World in Data for providing the {DATA_TAG} and '
    f'3Blue1Brown\'s "Exponential growth and epidemics" {YOUTUBE_TAG} for the '
    f'inspiration & formula. Created primarily with numpy, pandas, panel, '
    f'holoviews, and bokeh in Python.')

observed_df = pd.read_csv(DATA_URL)
print(observed_df)
num_days = len(observed_df)
observed_df = (
    observed_df
    .reset_index()
    .rename(columns={'index': 'days'})
    .melt(['date', 'days'], var_name='location', value_name='cases')
    .dropna()
)
observed_df['location'] = observed_df['location'].str.replace("'", '`')
worldwide_df = observed_df.query("location == 'Worldwide'")
observed_df = observed_df.query("location != 'Worldwide'")
location_options = pn.widgets.MultiSelect(
    options=observed_df['location'].unique().tolist(),
    value=['United States', 'South Korea', 'China', 'Italy', 'Singapore'],
    sizing_mode='stretch_height'
)
worldwide_line = worldwide_df.hvplot.line(
    'days', 'cases', label='Worldwide',
    color='black', **HVPLOT_KWDS)

@pn.interact(Average_number_of_people_exposed_daily=(0, 1000., 1, 5),
             Probability_of_infection=(0, 0.1, 0.01, 0.03),
             Number_of_days=(0, 720., 1, num_days),
             Number_of_cases=(0, 1e5, 1., 1),
             Locations=location_options)
def layout(Average_number_of_people_exposed_daily, Probability_of_infection,
           Number_of_days, Number_of_cases, Locations):
    """
    Average_number_of_people_exposed_daily
    Probability_of_infection
    Number_of_days
    Number_of_cases
    """
    days = np.arange(Number_of_days)
    Nd = (1 + Average_number_of_people_exposed_daily *
          Probability_of_infection) ** days * Number_of_cases
    model_df = pd.DataFrame({'cases': Nd}, index=days).rename_axis('days')
    model_df['date'] = START_DATE - pd.to_timedelta(days, unit='D')
    exceed_case = model_df['cases'] > WORLD_POPULATION
    model_df.loc[exceed_case, 'cases'] = WORLD_POPULATION
    model_line = model_df.hvplot.line(
        'days', 'cases', label='Model', **HVPLOT_KWDS
    ).opts(line_dash='dashed', line_width=5)

    location_df = observed_df.loc[observed_df['location'].isin(Locations)]
    location_line = location_df.hvplot.line(
        'days', 'cases', by='location', **HVPLOT_KWDS)

    overlay_lines = (model_line * location_line * worldwide_line).opts(
        'Curve', toolbar='above')
    pane = pn.pane.HoloViews(overlay_lines, sizing_mode='stretch_both',
                             min_height=500)
    return overlay_lines

widgets = pn.WidgetBox(layout[0], sizing_mode='stretch_height')
plot = layout[1]
for widget in widgets[0]:
    widget.name = widget.name.replace('_', ' ')
plot.set_param(sizing_mode='stretch_both')
view = pn.Row(widgets, plot, sizing_mode='stretch_both')
footer_md = pn.pane.Markdown(
    object=FOOTER, sizing_mode='stretch_width', height=20)
dashboard = pn.Column(view, footer_md, sizing_mode='stretch_both')
dashboard.servable(title='COVID19 Model Pane')

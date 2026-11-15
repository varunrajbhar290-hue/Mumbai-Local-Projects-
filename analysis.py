"""SIMULATED Mumbai suburban crowding portfolio. Run: python analysis.py"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs'; OUT.mkdir(exist_ok=True)
CHARTS = ROOT / 'charts'; CHARTS.mkdir(exist_ok=True)
rng = np.random.default_rng(42)
stations = {'Western':['Borivali','Andheri','Dadar'],
            'Central':['Thane','Ghatkopar','Dadar'],
            'Harbour':['Vashi','Chembur','Wadala Road']}
rows = []
# Entire timetable, station selection, demand and service intervals are invented.
for date in ['2026-11-09','2026-11-14']:
    day = 'weekday' if pd.Timestamp(date).dayofweek < 5 else 'weekend'
    for line, stops in stations.items():
        for direction in ['towards_terminus','away_from_terminus']:
            order = stops if direction == 'towards_terminus' else stops[::-1]
            types = ['slow'] if line == 'Harbour' else ['slow','fast']
            for typ in types:
                interval = 10 if typ == 'slow' else 20
                for start in range(300, 1410, interval):
                    service = f'{date}_{line}_{direction}_{typ}_{start}'
                    for pos, station in enumerate(order):
                        minute = start + pos * (9 if typ == 'slow' else 6)
                        hour = minute / 60
                        morning = np.exp(-0.5*((hour-9.3)/1.15)**2)
                        evening = np.exp(-0.5*((hour-18.8)/1.5)**2)
                        directional = (65*morning+20*evening if direction == 'towards_terminus'
                                       else 18*morning+68*evening)
                        load = (29 + directional*(1 if day=='weekday' else .48)
                                + {'Western':4,'Central':9,'Harbour':-5}[line]
                                + (5 if typ=='fast' else 0) + pos*2
                                + rng.normal(0,7))
                        rows.append([service,line,station,direction,
                                     pd.Timestamp(date)+pd.Timedelta(minutes=minute),typ,day,
                                     round(float(np.clip(load,5,145)),2)])
cols = ['service_id','line','station','direction','departure_time','train_type','day_type','estimated_passenger_load']
pristine = pd.DataFrame(rows,columns=cols)
raw = pristine.copy()
# Deliberate, reproducible quality defects; never silently replace missing loads with truth.
ix = rng.choice(raw.index,90,replace=False)
raw.loc[ix[:30],'estimated_passenger_load'] = np.nan
raw.loc[ix[30:60],'station'] = raw.loc[ix[30:60],'station'].str.upper().map(lambda s:' '+s+' ')
raw.loc[ix[60:],'train_type'] = raw.loc[ix[60:],'train_type'].str.upper()
raw = pd.concat([raw,raw.iloc[:25]],ignore_index=True)
raw.to_csv(ROOT/'simulated_raw.csv',index=False)
print('1. DATA SETUP: SIMULATED rows:',len(raw))
print('Dates: one weekday and one weekend; not an actual operating timetable.')
print('\n2. CLEANING\nMissing before:\n',raw.isna().sum().to_string())
print('Exact duplicates:',raw.duplicated().sum())
df = raw.drop_duplicates().copy()
canonical = {s.upper():s for stops in stations.values() for s in stops}
station_fixes = (df.station != df.station.str.strip().str.upper().map(canonical)).sum()
df['station'] = df.station.str.strip().str.upper().map(canonical)
type_fixes = (df.train_type != df.train_type.str.lower()).sum()
df['train_type'] = df.train_type.str.lower()
df['departure_time'] = pd.to_datetime(df.departure_time,errors='coerce')
df['estimated_passenger_load'] = pd.to_numeric(df.estimated_passenger_load,errors='coerce')
df['load_imputed'] = df.estimated_passenger_load.isna()
df['hour'] = df.departure_time.dt.hour
groups = ['line','station','direction','day_type','train_type','hour']
med = df.groupby(groups).estimated_passenger_load.transform('median')
df['estimated_passenger_load'] = df.estimated_passenger_load.fillna(med)
assert df[cols].notna().all().all()
assert df.estimated_passenger_load.between(0,150).all()
assert not df.duplicated(['service_id','station']).any()
df['time_band'] = pd.cut(df.hour,bins=[-1,7,10,16,20,23],
    labels=['early morning','morning peak','midday','evening peak','night']).astype(str)
df['is_peak'] = df.hour.between(8,10) | df.hour.between(17,20)
print(f'Fixed {station_fixes} station labels, {type_fixes} train-type labels; imputed {df.load_imputed.sum()} loads with same-segment hourly medians.')
print('Converted timestamps and numeric loads; added hour, time_band, is_peak. Remaining nulls:',df.isna().sum().sum())

# Frequency is the previous departure gap for the same station, direction and type,
# separately for each service date; no overnight gaps or cross-direction mixing.
df['service_date'] = df.departure_time.dt.strftime('%Y-%m-%d')
keys = ['service_date','line','station','direction','train_type']
df = df.sort_values(keys+['departure_time'])
df['gap_minutes'] = df.groupby(keys).departure_time.diff().dt.total_seconds()/60
df['gap_imputed'] = df.gap_minutes.isna()
df['gap_minutes'] = df.gap_minutes.fillna(df.groupby(keys).gap_minutes.transform('median'))
load_score = (df.estimated_passenger_load/120*100).clip(0,100)
gap_score = (df.gap_minutes/20*100).clip(0,100)
df['crowding_index'] = (0.8*load_score+0.2*gap_score).round(2)
df['crowding_category'] = pd.cut(df.crowding_index,[-.001,25,50,75,100],
    labels=['Low','Moderate','High','Very High']).astype(str)
df.to_csv(ROOT/'simulated_clean.csv',index=False)
summary = {}
print('\n3. ESTIMATED CROWDING PATTERNS')
for col in ['hour','line','day_type','train_type']:
    table = df.groupby(col).agg(mean_estimated_load=('estimated_passenger_load','mean'),
                              mean_index=('crowding_index','mean'),departures=('service_id','size')).round(2)
    summary[col] = table
    table.to_csv(OUT/f'average_by_{col}.csv')
    print('\nBy',col,'\n',table.to_string())
combo_cols = ['line','station','direction','day_type','hour','train_type']
combo = df.groupby(combo_cols).agg(mean_estimated_load=('estimated_passenger_load','mean'),
    departures=('service_id','size')).reset_index()
most = combo.nlargest(10,'mean_estimated_load'); least = combo.nsmallest(10,'mean_estimated_load')
most.to_csv(OUT/'top10_highest.csv',index=False); least.to_csv(OUT/'top10_lowest.csv',index=False)
print('\nTop 10 highest station-hour segments:\n',most.to_string(index=False))
print('\nTop 10 lowest station-hour segments:\n',least.to_string(index=False))
plt.style.use('seaborn-v0_8-whitegrid')
fig,axes = plt.subplots(2,2,figsize=(13,8))
for ax,col in zip(axes.flat,['hour','line','day_type','train_type']):
    s = summary[col].mean_estimated_load
    if col=='hour': ax.plot(s.index,s.values,marker='o',color='#007f86')
    else: ax.bar(s.index,s.values,color=['#007f86','#de9151','#5968a5'][:len(s)])
    ax.set(title=f'Mean estimated load by {col.replace("_"," ")}',ylabel='Estimated load (% capacity)',xlabel=col.replace('_',' ').title())
fig.suptitle('SIMULATED — estimated crowding patterns',fontsize=16)
fig.tight_layout(); fig.savefig(CHARTS/'overview.png',dpi=160); plt.close(fig)
heat = df.pivot_table(index='line',columns='hour',values='crowding_index',aggfunc='mean')
fig,ax=plt.subplots(figsize=(13,3.6))
im=ax.imshow(heat.values,aspect='auto',cmap='YlOrRd',vmin=0,vmax=100)
ax.set_xticks(range(len(heat.columns)),heat.columns); ax.set_yticks(range(len(heat.index)),heat.index)
ax.set(xlabel='Departure hour',ylabel='Line',title='SIMULATED — mean estimated Crowding Index (0–100)')
fig.colorbar(im,ax=ax,label='Crowding Index'); fig.tight_layout(); fig.savefig(CHARTS/'heatmap.png',dpi=160); plt.close(fig)
labels = lambda t: t.apply(lambda r:f'{r.station} | {r.direction.replace("_from_"," ← ").replace("_"," ")} | {r.day_type} {r.hour:02d}:00 | {r.train_type}',axis=1)
fig,axes=plt.subplots(1,2,figsize=(17,7))
for ax,t,title,color in [(axes[0],most,'Highest','#b65341'),(axes[1],least,'Lowest','#007f86')]:
    ax.barh(range(len(t)),t.mean_estimated_load,color=color); ax.set_yticks(range(len(t)),labels(t),fontsize=8)
    ax.invert_yaxis(); ax.set(xlabel='Mean estimated load (% capacity)',title=f'{title} 10 station-hour segments')
fig.suptitle('SIMULATED — estimated crowding patterns'); fig.tight_layout(); fig.savefig(CHARTS/'station_segments.png',dpi=160); plt.close(fig)

def best_departures(station,direction,preferred_time,line=None):
    """Up to three scheduled stops within inclusive ±30 min; full date required."""
    station = canonical.get(str(station).strip().upper())
    if station is None: raise ValueError('Unknown station')
    if direction not in ['towards_terminus','away_from_terminus']: raise ValueError('Invalid direction')
    t=pd.Timestamp(preferred_time)
    candidates=df[(df.station==station)&(df.direction==direction)&
        (df.departure_time.between(t-pd.Timedelta(minutes=30),t+pd.Timedelta(minutes=30)))].copy()
    if line is not None: candidates=candidates[candidates.line==line]
    candidates['minutes_from_preference']=(candidates.departure_time-t).dt.total_seconds().abs()/60
    return candidates.sort_values(['crowding_index','estimated_passenger_load','minutes_from_preference','departure_time','service_id']).head(3)[
        ['line','station','direction','departure_time','train_type','estimated_passenger_load','gap_minutes','crowding_index','crowding_category']]

recommendations=best_departures('Andheri','towards_terminus','2026-11-09 09:00',line='Western')
recommendations.to_csv(OUT/'example_best_departures.csv',index=False)
print('\n4. INDEX: 80% normalized load + 20% normalized service gap.\n',df.crowding_category.value_counts().to_string())
print('\n5. BEST DEPARTURES, Andheri towards terminus, 9 Nov 09:00 ±30 minutes:\n',recommendations.to_string(index=False))
metrics={'rows_raw':len(raw),'rows_clean':len(df),'avg_index':round(df.crowding_index.mean(),2),
         'busiest_hour':int(summary['hour'].mean_estimated_load.idxmax()),
         'least_crowded_line':summary['line'].mean_index.idxmin(),
         'weekday_load':float(summary['day_type'].loc['weekday','mean_estimated_load']),
         'weekend_load':float(summary['day_type'].loc['weekend','mean_estimated_load']),
         'peak_load':round(df.loc[df.is_peak,'estimated_passenger_load'].mean(),2),
         'nonpeak_load':round(df.loc[~df.is_peak,'estimated_passenger_load'].mean(),2)}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
with pd.ExcelWriter(ROOT/'crowding_analysis.xlsx',engine='openpyxl') as writer:
    df.to_excel(writer,sheet_name='Simulated data',index=False)
    for col,table in summary.items(): table.to_excel(writer,sheet_name=f'By {col}')
    most.to_excel(writer,sheet_name='Highest 10',index=False)
    least.to_excel(writer,sheet_name='Lowest 10',index=False)
    recommendations.to_excel(writer,sheet_name='Example departures',index=False)
    pd.DataFrame([metrics]).to_excel(writer,sheet_name='KPIs',index=False)
    from openpyxl.styles import Font,PatternFill
    from openpyxl.chart import BarChart,Reference
    for ws in writer.book.worksheets:
        ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]: cell.font=Font(color='FFFFFF',bold=True); cell.fill=PatternFill('solid',fgColor='007F86')
        for column in ws.columns:
            letter=column[0].column_letter
            ws.column_dimensions[letter].width=min(32,max(14,max(len(str(c.value)) for c in list(column)[:100])+2))
    ws=writer.book['By hour']; chart=BarChart(); chart.title='SIMULATED hourly estimated load'
    chart.y_axis.title='Estimated load (% capacity)'; chart.x_axis.title='Hour'
    chart.add_data(Reference(ws,min_col=2,max_col=2,min_row=1,max_row=ws.max_row),titles_from_data=True)
    chart.set_categories(Reference(ws,min_col=1,min_row=2,max_row=ws.max_row)); ws.add_chart(chart,'F2')
print('\nMETRICS\n',json.dumps(metrics,indent=2))

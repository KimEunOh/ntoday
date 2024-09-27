import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from data_processing import load_data

# 페이지 등록
dash.register_page(__name__, path="/schedule_dashboard", name="Schedule Dashboard")

# 색상 혼합 함수 (두 색상 혼합)
def mix_colors(color1, color2):
    c1 = np.array([int(color1[i:i+2], 16) for i in (1, 3, 5)])
    c2 = np.array([int(color2[i:i+2], 16) for i in (1, 3, 5)])
    mixed = (c1 + c2) // 2
    return f'#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}'

# 다중 색상 혼합 함수 
def mix_multiple_colors(colors):
    rgb_values = [np.array([int(color[i:i+2], 16) for i in (1, 3, 5)]) for color in colors]
    # 색상값 평균 사용
    mixed_rgb = np.mean(rgb_values, axis=0).astype(int)
    return f'#{mixed_rgb[0]:02x}{mixed_rgb[1]:02x}{mixed_rgb[2]:02x}'

# 데이터 로드
df = load_data()  # 전처리 함수 호출

# 근무 상태 컬럼 추가
df['근무상태'] = df['근무_여부'].apply(lambda x: 
    '근무' if x == '근무' else 
    '휴식중' if x == '휴식중' else 
    '대기중' if x == '대기중' else 
    'NONE'
)

# 피드백 점수 그룹화
df['피드백_점수_그룹'] = pd.cut(
    df['피드백_점수'],
    bins=[-1.0, -0.6, -0.2, 0.2, 0.6, 1.0],
    labels=['강하게 부정적', '부정적', '중립적', '긍정적', '강하게 긍정적'],
    right=False,
    include_lowest=True
)

# 파견 횟수를 그룹화
df['파견횟수_그룹'] = (df['파견횟수'] // 5) * 5

# 카드 스타일 정의
FILTER_CARD_STYLE = {
    'box-shadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
    'border': 'none',
    'border-radius': '16px',  
    'padding': '15px',
    'background-color': '#FFFFFF', 
}

GRAPH_CARD_STYLE = {
    'box-shadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
    'border': 'none',
    'border-radius': '16px',  
    'padding': '15px',
    'background-color': '#FFFFFF',  
}

# 색상 맵 정의 (파스텔 톤)
COLOR_MAP = {
    '근무': '#AEC6CF',      
    '휴식중': '#FFD1DC',    
    '대기중': '#FFB347',     
    'NONE': '#CFCFC4'        
}

# 페이지 레이아웃 정의
layout = dbc.Container(
    [
        # 페이지 제목
        html.H1(
            "Schedule Dashboard",
            className="text-center my-4",
            style={
                'font-weight': 'bold',
                'font-size': '2.5em',
                'color': '#333'
            }
        ),
        
        # 필터 섹션
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Label(
                                    "매장 선택",
                                    style={
                                        'font-weight': 'bold',
                                        'font-size': '16px',
                                        'margin-bottom': '5px',
                                        'color': '#007BFF'
                                    }
                                ),
                                dcc.Dropdown(
                                    id='store-selector',
                                    options=[
                                        {'label': store, 'value': store} 
                                        for store in sorted(df['매장_ID'].dropna().unique())
                                    ],
                                    placeholder="매장 선택",
                                    style={
                                        'width': '100%',
                                        'border': '1px solid #007BFF',
                                        'border-radius': '5px',
                                        'padding': '10px',
                                        'font-size': '14px',
                                        'color': '#333'
                                    }
                                )
                            ],
                            style={
                                'display': 'flex',
                                'flex-direction': 'column',
                                'justify-content': 'center',
                                'height': '100px'  
                            }
                        ),
                        style=FILTER_CARD_STYLE
                    ),
                    width=6
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Label(
                                    "날짜 선택",
                                    style={
                                        'font-weight': 'bold',
                                        'font-size': '16px',
                                        'margin-bottom': '5px',
                                        'color': '#007BFF'
                                    }
                                ),
                                html.Div(style={'height': '10px'}),  
                                dcc.DatePickerSingle(
                                    id='date-picker',
                                    placeholder='날짜 선택',
                                    style={
                                        'width': '100%',
                                        'border': '1px solid #007BFF',
                                        'border-radius': '5px',
                                        'padding': '10px',
                                        'font-size': '14px',
                                        'color': '#333'
                                    }
                                )
                            ],
                            style={
                                'display': 'flex',
                                'flex-direction': 'column',
                                'justify-content': 'center',
                                'height': '100px'  
                            }
                        ),
                        style=FILTER_CARD_STYLE
                    ),
                    width=6
                )
            ],
            className="mb-4"
        ),
        
        # 그래프 섹션
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Graph(
                                id='schedule-plot',
                                config={'displayModeBar': False},
                                style={'height': '600px'}  
                            ),
                        ),
                        style=GRAPH_CARD_STYLE
                    ),
                    width=12
                )
            ],
            className="mb-4"
        )
    ],
    fluid=True,
    style={
        'background-color': '#E0F7FA',  
        'padding': '20px'
    }
)

# 데이터 필터링 함수 정의
def filter_data(selected_store, selected_date):
    filtered_df = df.copy()
    if selected_store:
        filtered_df = filtered_df[filtered_df['매장_ID'] == selected_store]
    if selected_date:
        selected_date = pd.to_datetime(selected_date).date()
        filtered_df = filtered_df[
            (filtered_df['기록_날짜'].dt.date == selected_date) & 
            (filtered_df['근무_여부'] == '근무')
        ]
    return filtered_df

# 매장 선택 시 근무 날짜 표시 콜백
@dash.callback(
    [Output('date-picker', 'disabled_days'),
     Output('date-picker', 'date')],
    Input('store-selector', 'value')
)
def update_calendar(selected_store):
    if not selected_store:
        # 매장 선택이 없을 경우 모든 날짜를 비활성화하지 않음
        return [], None

    # 매장에 해당하는 근무 날짜 가져오기
    store_dates = df[df['매장_ID'] == selected_store]['기록_날짜'].dt.date.unique()
    all_dates = pd.date_range(df['기록_날짜'].min(), df['기록_날짜'].max()).date
    disabled_dates = [date.strftime('%Y-%m-%d') for date in all_dates if date not in store_dates]

    return disabled_dates, None

# 선택한 날짜의 근무 시간표 출력 콜백
@dash.callback(
    Output('schedule-plot', 'figure'),
    [Input('date-picker', 'date'),
     Input('store-selector', 'value')]
)
def update_schedule(selected_date, selected_store):
    if not selected_date or not selected_store:
        return go.Figure()

    selected_date = pd.to_datetime(selected_date).date()
    filtered_df = df[
        (df['기록_날짜'].dt.date == selected_date) & 
        (df['매장_ID'] == selected_store) & 
        (df['근무_여부'] == '근무')
    ]

    if filtered_df.empty:
        return go.Figure()

    # 근무 시간 데이터
    employee_ids = filtered_df['직원_ID'].unique()
    colors = ['#%06x' % np.random.randint(0, 0xFFFFFF) for _ in range(len(employee_ids))]

    # 직원별 색상 매핑
    employee_color_map = dict(zip(employee_ids, colors))

    # 시간대별 근무 직원 정보 저장
    time_slots_am = [[] for _ in range(12)]
    time_slots_pm = [[] for _ in range(12)]

    for emp_id in employee_ids:
        emp_data = filtered_df[filtered_df['직원_ID'] == emp_id]
        for _, row in emp_data.iterrows():
            start_hour = int(row['근무_시작'].split(':')[0])
            end_hour = int(row['근무_종료'].split(':')[0])
            for hour in range(start_hour, end_hour):
                hour_mod = hour % 24
                if hour_mod < 12:
                    time_slots_am[hour_mod].append(emp_id)
                else:
                    time_slots_pm[hour_mod - 12].append(emp_id)

    # 혼합 색상 및 텍스트 레이블 적용
    slot_colors_am = ['white'] * 12
    slot_colors_pm = ['white'] * 12
    text_labels_am = [''] * 12
    text_labels_pm = [''] * 12

    for i in range(12):
        # 오전 시간대 텍스트 설정
        if len(time_slots_am[i]) == 1:
            slot_colors_am[i] = employee_color_map[time_slots_am[i][0]]
            text_labels_am[i] = f'{i}시 - ' + ', '.join(time_slots_am[i])
        elif len(time_slots_am[i]) > 1:
            mixed_color = mix_multiple_colors([employee_color_map[emp_id] for emp_id in time_slots_am[i]])
            slot_colors_am[i] = mixed_color
            text_labels_am[i] = f'{i}시 - ' + ', '.join(time_slots_am[i])

        # 오후 시간대 텍스트 설정
        if len(time_slots_pm[i]) == 1:
            slot_colors_pm[i] = employee_color_map[time_slots_pm[i][0]]
            text_labels_pm[i] = f'{i + 12}시 - ' + ', '.join(time_slots_pm[i])
        elif len(time_slots_pm[i]) > 1:
            mixed_color = mix_multiple_colors([employee_color_map[emp_id] for emp_id in time_slots_pm[i]])
            slot_colors_pm[i] = mixed_color
            text_labels_pm[i] = f'{i + 12}시 - ' + ', '.join(time_slots_pm[i])

    # Plotly 파이 차트 생성
    fig = go.Figure()

    # 직원별 색상 Legend 추가
    for emp_id, color in employee_color_map.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],  # 빈 좌표, 표시되지 않음
            mode='markers',
            marker=dict(size=10, color=color),
            name=f'{emp_id}'  # 직원 ID를 Legend에 표시
        ))

    # 오전 시간대 파이 차트
    fig.add_trace(go.Pie(
        values=[1] * 12,
        marker=dict(colors=slot_colors_am, line=dict(color='black', width=1)),
        domain=dict(x=[0, 0.5]),
        hoverinfo='label+text',
        text=text_labels_am,
        textinfo='none',
        title='오전 (00:00 - 11:59)',
        hole=0.7,
        direction='clockwise',  # 시계 방향으로 설정
        sort=False,
        showlegend=False
    ))

    # 오후 시간대 파이 차트
    fig.add_trace(go.Pie(
        values=[1] * 12,
        marker=dict(colors=slot_colors_pm, line=dict(color='black', width=1)),
        domain=dict(x=[0.5, 1]),
        hoverinfo='label+text',
        text=text_labels_pm,
        textinfo='none',
        title='오후 (12:00 - 23:59)',
        hole=0.7,
        direction='clockwise', 
        sort=False,
        showlegend=False
    ))

    # 레이아웃 설정
    fig.update_layout(
        title=f'{selected_date} {selected_store} 근무 시간표',
        showlegend=True,
        legend=dict(
            title='직원 ID',
            orientation='v',
            x=1.05,
            y=1
        ),
        margin=dict(l=50, r=200, t=100, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=17,
            family='Arial',
            color='#000000',
            weight='bold'
        )
    )

    return fig

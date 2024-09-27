import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_processing import load_data

# 페이지 등록
dash.register_page(__name__, path="/score_dashboard", name="Score Dashboard")

# 데이터 불러오기 및 전처리
df = load_data()  # 데이터 불러오기 및 기본 전처리 함수 호출
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

#  카드 스타일 정의
FILTER_CARD_STYLE = {
    'box-shadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
    'border': 'none',
    'border-radius': '16px',  # 모서리 둥글게 설정
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
    '근무': '#AEC6CF',       # 파스텔 블루
    '휴식중': '#FFD1DC',     # 파스텔 핑크
    '대기중': '#FFB347',     # 파스텔 오렌지
    'NONE': '#CFCFC4'        # 파스텔 그레이
}

# 페이지 레이아웃 정의
layout = dbc.Container(
    [
        # 필터 섹션 추가
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("매장 카테고리", style={'font-weight': 'bold'}),  
                                            dcc.Dropdown(
                                                options=[
                                                    {'label': cat, 'value': cat} for cat in sorted(df['매장_카테고리'].dropna().unique())
                                                ],
                                                value=None,
                                                multi=True,
                                                placeholder="카테고리 선택",
                                                id='category-filter',
                                                style={'font-weight': 'bold'}  
                                            )
                                        ],
                                        md=4
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("연도", style={'font-weight': 'bold'}),  
                                            dcc.Dropdown(
                                                options=[
                                                    {'label': year, 'value': year} for year in sorted(df['연도'].unique())
                                                ],
                                                value=sorted(df['연도'].unique()),
                                                multi=True,
                                                placeholder="연도 선택",
                                                id='year-filter',
                                                style={'font-weight': 'bold'}  
                                            )
                                        ],
                                        md=4
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("월", style={'font-weight': 'bold'}),  
                                            dcc.Dropdown(
                                                options=[
                                                    {'label': month, 'value': month} for month in range(1, 13)
                                                ],
                                                value=sorted(df['월'].unique()),
                                                multi=True,
                                                placeholder="월 선택",
                                                id='month-filter',
                                                style={'font-weight': 'bold'}  
                                            )
                                        ],
                                        md=4
                                    ),
                                ]
                            )
                        ]
                    ),
                    style=FILTER_CARD_STYLE
                ),
                width=12,
                className="mb-4"
            )
        ),
        
        # 그래프 1행 (피드백 vs 판매량, 파견 vs 판매량, 근무 상태 추세)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Graph(id='feedback-vs-sales', config={'displayModeBar': False})
                        ),
                        style=GRAPH_CARD_STYLE  
                    ),
                    width=12,
                    lg=4,
                    className="mb-4"
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Graph(id='dispatch-vs-sales', config={'displayModeBar': False})
                        ),
                        style=GRAPH_CARD_STYLE  
                    ),
                    width=12,
                    lg=4,
                    className="mb-4"
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Graph(id='work-status-trend', config={'displayModeBar': False})
                        ),
                        style=GRAPH_CARD_STYLE  
                    ),
                    width=12,
                    lg=4,
                    className="mb-4"
                ),
            ],
            className="mb-4"
        ),
        
        # 그래프 2행 (근무 상태 이동 평균, 피드백-파견 히트맵)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Graph(id='work-status-moving-average', style={'height': '500px'}, config={'displayModeBar': False})
                        ),
                        style=GRAPH_CARD_STYLE  
                    ),
                    width=12,
                    lg=6,
                    className="mb-4"
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Graph(id='feedback-dispatch-heatmap', style={'height': '500px'}, config={'displayModeBar': False})
                        ),
                        style=GRAPH_CARD_STYLE  
                    ),
                    width=12,
                    lg=6,
                    className="mb-4"
                ),
            ],
            className="mb-4"
        ),
    ],
    fluid=True,
    style={'background-color': '#E0F7FA', 'padding': '20px'}  # 전체 배경색을 연한 청록색으로 설정
)


# 데이터 필터링 함수 정의
def filter_data(selected_categories, selected_years, selected_months):
    filtered_df = df.copy()
    if selected_categories:
        filtered_df = filtered_df[filtered_df['매장_카테고리'].isin(selected_categories)]
    if selected_years:
        filtered_df = filtered_df[filtered_df['연도'].isin(selected_years)]
    if selected_months:
        filtered_df = filtered_df[filtered_df['월'].isin(selected_months)]
    return filtered_df

# 피드백 점수별 판매량 추세 그래프 콜백
@dash.callback(
    Output('feedback-vs-sales', 'figure'),
    [
        Input('category-filter', 'value'),
        Input('year-filter', 'value'),
        Input('month-filter', 'value')
    ]
)
def update_feedback_vs_sales(selected_categories, selected_years, selected_months):
    filtered_df = filter_data(selected_categories, selected_years, selected_months)
    
    # 데이터 필터링 및 정제
    cat_data = filtered_df[filtered_df['매장_카테고리'].notna()]
    cat_data = cat_data[['피드백_점수', '판매량']].dropna()  
    cat_data['피드백_점수'] = pd.to_numeric(cat_data['피드백_점수'], errors='coerce')  
    cat_data['판매량'] = pd.to_numeric(cat_data['판매량'], errors='coerce')  
    cat_data = cat_data.dropna()  

    # 데이터프레임이 비어있을 경우 빈 Figure 반환
    if cat_data.empty:
        return go.Figure()

    # 직선 추세선 (OLS)
    fig_ols = px.scatter(
        cat_data, 
        x='피드백_점수', 
        y='판매량',
        trendline='ols',
        title='피드백 점수별 판매량 추세',
        labels={'피드백_점수': '피드백 점수', '판매량': '판매량'},
        template='plotly_white'
    )

    # 곡선 추세선 (LOWESS)
    fig_lowess = px.scatter(
        cat_data, 
        x='피드백_점수', 
        y='판매량',
        trendline='lowess',
        title='피드백 점수별 판매량 추세',
        labels={'피드백_점수': '피드백 점수', '판매량': '판매량'},
        template='plotly_white'
    )

    # 새로운 Figure 생성
    fig = go.Figure()

    # 산점도 추가
    fig.add_traces([trace for trace in fig_ols.data if trace.mode == 'markers'])  

    # 직선 추세선 추가
    fig.add_traces([trace for trace in fig_ols.data if trace.mode == 'lines'])
    fig.data[-1].update(line=dict(color='#FF6961', dash='dash', width=2), name='직선 추세선')  

    # 곡선 추세선 추가
    fig.add_traces([trace for trace in fig_lowess.data if trace.mode == 'lines'])
    fig.data[-1].update(line=dict(color='#77DD77', width=3), name='곡선 추세선')  

    # 레이아웃 설정
    fig.update_layout(
        title={'text': '피드백 점수별 판매량 추세', 'x': 0.5, 'xanchor': 'center'},
        font=dict(size=14, family='Arial', color='#000000', weight='bold'),  
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(title='추세선', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    return fig

# 파견횟수별 판매량 추세 그래프 콜백
@dash.callback(
    Output('dispatch-vs-sales', 'figure'),
    [
        Input('category-filter', 'value'),
        Input('year-filter', 'value'),
        Input('month-filter', 'value')
    ]
)
def update_dispatch_vs_sales(selected_categories, selected_years, selected_months):
    filtered_df = filter_data(selected_categories, selected_years, selected_months)
    
    # 데이터 필터링 및 정제
    cat_data = filtered_df[filtered_df['매장_카테고리'].notna()]
    cat_data = cat_data[['파견횟수', '판매량']].dropna()
    cat_data['파견횟수'] = pd.to_numeric(cat_data['파견횟수'], errors='coerce')
    cat_data['판매량'] = pd.to_numeric(cat_data['판매량'], errors='coerce')
    cat_data = cat_data.dropna()

    # 데이터프레임이 비어있을 경우 빈 Figure 반환
    if cat_data.empty:
        return go.Figure()

    # 직선 추세선 (OLS)
    fig_ols = px.scatter(
        cat_data, 
        x='파견횟수', 
        y='판매량', 
        trendline='ols',
        title='파견횟수별 판매량 추세',
        labels={'파견횟수': '파견횟수', '판매량': '판매량'},
        template='plotly_white'
    )

    # 곡선 추세선 (LOWESS)
    fig_lowess = px.scatter(
        cat_data, 
        x='파견횟수', 
        y='판매량', 
        trendline='lowess',
        title='파견횟수별 판매량 추세',
        labels={'파견횟수': '파견횟수', '판매량': '판매량'},
        template='plotly_white'
    )

    # 새로운 Figure 생성
    fig = go.Figure()

    # 산점도 추가
    fig.add_traces([trace for trace in fig_ols.data if trace.mode == 'markers'])

    # 직선 추세선 추가
    fig.add_traces([trace for trace in fig_ols.data if trace.mode == 'lines'])
    fig.data[-1].update(line=dict(color='#FF6961', dash='dash', width=2), name='직선 추세선')  

    # 곡선 추세선 추가
    fig.add_traces([trace for trace in fig_lowess.data if trace.mode == 'lines'])
    fig.data[-1].update(line=dict(color='#77DD77', width=3), name='곡선 추세선')  

    # 레이아웃 설정
    fig.update_layout(
        title={'text': '파견횟수별 판매량 추세', 'x': 0.5, 'xanchor': 'center'},
        font=dict(size=14, family='Arial', color='#000000', weight='bold'),  
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(title='추세선', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    return fig

# 근무 상태별 인원 변화 시각화 그래프 콜백
@dash.callback(
    Output('work-status-trend', 'figure'),
    [
        Input('category-filter', 'value'),
        Input('year-filter', 'value'),
        Input('month-filter', 'value')
    ]
)
def work_status_trend(selected_categories, selected_years, selected_months):
    filtered_df = filter_data(selected_categories, selected_years, selected_months)
    
    filtered_df['연도_월'] = filtered_df['연도'].astype(str) + '-' + filtered_df['월'].astype(str).str.zfill(2)  # 연도-월 형식으로 변환

    # 월별로 근무 상태별 일수를 집계
    monthly_counts = filtered_df.groupby(['연도_월', '근무상태']).size().reset_index(name='일수')

    # 누적 막대 그래프 생성
    fig = px.bar(
        monthly_counts, 
        x='연도_월', 
        y='일수', 
        color='근무상태', 
        title='월별 근무 상태별 인원 변화',
        labels={'일수': '총 일수', '연도_월': '연도-월'},
        color_discrete_map=COLOR_MAP,
        template='plotly_white'
    )

    fig.update_layout(
        barmode='stack',  # 누적 막대 그래프로 설정
        xaxis_tickangle=-45,  # X축 라벨 각도
        title={'text': '월별 근무 상태별 인원 변화', 'x': 0.5, 'xanchor': 'center'},
        font=dict(size=14, family='Arial', color='#000000', weight='bold'), 
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(title='근무 상태', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    return fig

# 근무 상태별 인원 변화 (7일 이동 평균) 그래프 콜백
@dash.callback(
    Output('work-status-moving-average', 'figure'),
    [
        Input('category-filter', 'value'),
        Input('year-filter', 'value'),
        Input('month-filter', 'value')
    ]
)
def update_work_status_moving_average(selected_categories, selected_years, selected_months):
    filtered_df = filter_data(selected_categories, selected_years, selected_months)
    
    # 날짜별로 근무 상태별 직원 수 집계
    daily_status_pivot = filtered_df.groupby(['기록_날짜', '근무상태']).agg({'직원_ID': 'nunique'}).reset_index()
    daily_status_pivot = daily_status_pivot.pivot(index='기록_날짜', columns='근무상태', values='직원_ID').fillna(0)
    rolling_avg = daily_status_pivot.rolling(window=7).mean().reset_index()

    # 선 그래프 생성
    fig = go.Figure()

    # 각 근무 상태별로 선 추가
    for status in rolling_avg.columns[1:]:  # '기록_날짜' 제외
        if status in COLOR_MAP:
            fig.add_trace(go.Scatter(
                x=rolling_avg['기록_날짜'],
                y=rolling_avg[status],
                mode='lines',
                name=status,
                line=dict(color=COLOR_MAP.get(status, '#BDBDBD')),
                line_width=2
            ))
        else:
            fig.add_trace(go.Scatter(
                x=rolling_avg['기록_날짜'],
                y=rolling_avg[status],
                mode='lines',
                name=status,
                line=dict(color=COLOR_MAP.get('NONE', '#BDBDBD')),
                line_width=2
            ))

    # 레이아웃 설정
    fig.update_layout(
        title={'text': '근무 상태별 인원 변화 (7일 이동 평균)', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='기록 날짜',
        yaxis_title='평균 인원수',
        xaxis_tickangle=-45,
        font=dict(size=14, family='Arial', color='#000000', weight='bold'), 
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(title='근무 상태', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig

# 피드백 점수와 파견 횟수의 빈도 히트맵 그래프 콜백
@dash.callback(
    Output('feedback-dispatch-heatmap', 'figure'),
    [
        Input('category-filter', 'value'),
        Input('year-filter', 'value'),
        Input('month-filter', 'value')
    ]
)
def update_feedback_dispatch_heatmap(selected_categories, selected_years, selected_months):
    filtered_df = filter_data(selected_categories, selected_years, selected_months)
    
    # 피벗 테이블 생성 (빈 값 채우기)
    heatmap_data = filtered_df.pivot_table(
        index='피드백_점수_그룹',
        columns='파견횟수_그룹',
        values='기록_ID',
        aggfunc='count',
        fill_value=0
    )

    # 모든 피드백 그룹이 표시되도록 y축 라벨을 강제 설정
    y_labels = ['강하게 부정적', '부정적', '중립적', '긍정적', '강하게 긍정적']
    heatmap_data = heatmap_data.reindex(y_labels).fillna(0)

    # 히트맵 생성
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=y_labels,
        colorscale='Viridis',
        colorbar=dict(title='빈도'),
        hoverongaps=False
        # text 및 texttemplate 제거하여 값 표시 없음
    ))

    # 레이아웃 설정
    fig.update_layout(
        title={'text': '그룹화된 파견빈도에 따른 피드백 점수 빈도', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='파견빈도 (그룹)',
        yaxis_title='피드백 점수 (그룹)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        margin=dict(l=80, r=20, t=80, b=80),
        font=dict(size=14, family='Arial', color='#000000', weight='bold'), 
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig

# prophet_forecast.py
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from prophet import Prophet
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
from data_processing import load_data

# 페이지 등록
dash.register_page(__name__, path="/prophet_forecast", name="Prophet Forecast")

# 데이터 로드 및 전처리
df = load_data()
df_working = df[df['근무_여부'] == '근무']

# 색상 맵 정의 (파스텔 톤)
COLOR_MAP = {
    '근무': '#AEC6CF',       # 파스텔 블루
    '휴식중': '#FFD1DC',     # 파스텔 핑크
    '대기중': '#FFB347',     # 파스텔 오렌지
    'NONE': '#CFCFC4'        # 파스텔 그레이
}

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

# 고유 카테고리 리스트 추출
unique_categories = sorted(df_working['매장_카테고리'].dropna().unique())

# 페이지 레이아웃 정의
layout = dbc.Container(
    [
        # 페이지 제목
        dbc.Row(
            dbc.Col(
                html.H1(
                    [
                        html.I(className="fas fa-chart-line mr-3"),  # FontAwesome 아이콘 추가
                        "Sales Forecast Dashboard"
                    ],
                    style={
                        'text-align': 'center',
                        'margin-bottom': '20px',
                        'color': '#004d40', 
                        'font-family': 'Arial, sans-serif',
                        'font-weight': 'bold'
                    }
                ),
                width=12
            )
        ),
        
        # 필터 섹션 추가: 카테고리 선택을 위한 라디오 버튼
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Label("매장 카테고리 선택", style={'font-weight': 'bold', 'font-size': '1.1em'}),
                            dbc.RadioItems(
                                options=[
                                    {'label': category, 'value': category} for category in unique_categories
                                ],
                                value=unique_categories[0] if unique_categories else None,  # 기본 선택값 설정
                                id='category-radio',
                                inline=True,
                                className="mt-2"
                            )
                        ]
                    ),
                    style=FILTER_CARD_STYLE
                ),
                width=12,
                className="mb-4"
            )
        ),
        
        # 그래프 섹션
        dbc.Spinner(  # 로딩 스피너 추가
            children=dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-chart-area mr-2"),
                                        "실제 매출액 및 예측 매출액"
                                    ],
                                    className="bg-primary text-white"
                                ),
                                dbc.CardBody(
                                    dcc.Graph(id='sales-forecast-plot', config={'displayModeBar': False})
                                )
                            ],
                            style=GRAPH_CARD_STYLE
                        ),
                        width=12,
                        lg=6,
                        className="mb-4"
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-trend-up mr-2"),
                                        "예측 트렌드"
                                    ],
                                    className="bg-success text-white"
                                ),
                                dbc.CardBody(
                                    dcc.Graph(id='forecast-trend-plot', config={'displayModeBar': False})
                                )
                            ],
                            style=GRAPH_CARD_STYLE
                        ),
                        width=12,
                        lg=6,
                        className="mb-4"
                    ),
                ],
                className="mb-4"
            )
        ),
        
        dbc.Spinner(
            children=dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-seasonal-weather mr-2"),
                                        "연간 주기성"
                                    ],
                                    className="bg-warning text-white"
                                ),
                                dbc.CardBody(
                                    dcc.Graph(id='forecast-seasonality-plot', config={'displayModeBar': False})
                                )
                            ],
                            style=GRAPH_CARD_STYLE
                        ),
                        width=12,
                        lg=6,
                        className="mb-4"
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-calendar-week mr-2"),
                                        "요일별 주기성"
                                    ],
                                    className="bg-danger text-white"
                                ),
                                dbc.CardBody(
                                    dcc.Graph(id='forecast-weekly-plot', config={'displayModeBar': False})
                                )
                            ],
                            style=GRAPH_CARD_STYLE
                        ),
                        width=12,
                        lg=6,
                        className="mb-4"
                    ),
                ],
                className="mb-4"
            )
        ),
    ],
    fluid=True,
    style={'background-color': '#004d40', 'padding': '20px', 'border-radius': '10px'},  
    className="bg-light" 
)

# 데이터 필터링 함수 정의
def filter_data_by_category(selected_category):
    if selected_category:
        filtered_df = df_working[df_working['매장_카테고리'] == selected_category]
    else:
        filtered_df = df_working.copy()
    return filtered_df

# 콜백 함수 정의
@dash.callback(
    [
        Output('sales-forecast-plot', 'figure'),
        Output('forecast-trend-plot', 'figure'),
        Output('forecast-seasonality-plot', 'figure'),
        Output('forecast-weekly-plot', 'figure')
    ],
    Input('category-radio', 'value')  # 카테고리 선택을 Input으로 사용
)
def update_forecast_graph(selected_category):
    filtered_df = filter_data_by_category(selected_category)
    
    # 근무 중인 데이터만 사용하여 일별 매출액 집계
    daily_sales = filtered_df.groupby('기록_날짜')['매출액'].sum().reset_index()
    daily_sales.columns = ['ds', 'y']
    
    # Prophet 모델 생성 및 훈련
    if daily_sales.empty:
        # 데이터가 없을 경우 빈 Figure 반환
        return go.Figure(), go.Figure(), go.Figure(), go.Figure()
    
    model = Prophet()
    model.fit(daily_sales)
    
    # 미래 예측 (180일)
    future = model.make_future_dataframe(periods=180)
    forecast = model.predict(future)
    
    # 실제 매출액 및 예측 매출액 시각화
    fig1 = go.Figure()
    
    # 실제 매출액을 산점도로 표현
    fig1.add_trace(go.Scatter(
        x=daily_sales['ds'], y=daily_sales['y'], 
        mode='markers',  # Scatter plot with markers
        name='실제 매출액', 
        marker=dict(color='blue', size=6, symbol='circle')
    ))
    
    # 예측 매출액을 선으로 표현
    fig1.add_trace(go.Scatter(
        x=forecast['ds'], y=forecast['yhat'], 
        mode='lines', 
        name='예측 매출액', 
        line=dict(color='red', width=2)
    ))
    
    # 예측 매출액의 최대값(상한) 범위
    fig1.add_trace(go.Scatter(
        x=forecast['ds'], y=forecast['yhat_upper'],
        mode='lines',
        line=dict(width=0),  # 선을 보이지 않게 설정
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # 예측 매출액의 최소값(하한) 범위
    fig1.add_trace(go.Scatter(
        x=forecast['ds'], y=forecast['yhat_lower'],
        mode='lines',
        fill='tonexty',  # 이전 trace와 영역을 채움
        fillcolor='rgba(255, 99, 132, 0.2)',  # 반투명한 붉은색으로 범위를 나타냄
        line=dict(width=0),  # 선을 보이지 않게 설정
        name='예측 범위'
    ))
    
    # 레이아웃 설정
    fig1.update_layout(
        title={'text': f'{selected_category} - 일 단위 매출액 예측' if selected_category else '일 단위 매출액 예측', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='날짜', 
        yaxis_title='매출액',
        template='plotly_white',
        font=dict(family='Arial, sans-serif', size=12, color='#333', weight='bold'),
        plot_bgcolor='#ffffff',
        margin=dict(t=50, b=40, l=40, r=20)
    )
    
    # 트렌드 플롯
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=forecast['ds'], y=forecast['trend'], 
        mode='lines', 
        name='트렌드', 
        line=dict(color='green')
    ))
    fig2.update_layout(
        title={'text': f'{selected_category} - 예측 트렌드' if selected_category else '예측 트렌드', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='날짜', 
        yaxis_title='트렌드',
        template='plotly_white',
        font=dict(family='Arial, sans-serif', size=12, color='#333', weight='bold'),
        plot_bgcolor='#ffffff',
        margin=dict(t=50, b=40, l=40, r=20)
    )
    
    # 주기성 플롯
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=forecast['ds'], y=forecast['yearly'], 
        mode='lines', 
        name='연간 주기성', 
        line=dict(color='purple')
    ))
    fig3.update_layout(
        title={'text': f'{selected_category} - 연간 주기성' if selected_category else '연간 주기성', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='날짜', 
        yaxis_title='주기성',
        template='plotly_white',
        font=dict(family='Arial, sans-serif', size=12, color='#333', weight='bold'),
        plot_bgcolor='#ffffff',
        margin=dict(t=50, b=40, l=40, r=20)
    )
    
    # 주간 주기성 플롯
    # 요일 이름을 생성 (월요일부터 일요일까지)
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Prophet에서 주간 주기성을 추출하여 요일별 평균으로 재구성
    # 요일에 따른 주기성을 추출 (주기를 맞추기 위해 modulo 연산 사용)
    forecast['day_of_week'] = forecast['ds'].dt.dayofweek  # 요일을 숫자로 변환 (0: Monday, ..., 6: Sunday)
    weekly_means = forecast.groupby('day_of_week')['weekly'].mean().reindex(range(7))  # 요일 순서대로 정렬
    
    # 주간 주기성 플롯 생성
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=weekdays, y=weekly_means, 
        mode='lines+markers', 
        name='요일별 주기성',
        line=dict(color='#ff7f0e', width=2),
        marker=dict(size=8, color='#ff7f0e', symbol='circle')
    ))
    fig4.update_layout(
        title={'text': f'{selected_category} - 요일별 주기성' if selected_category else '요일별 주기성', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='요일', 
        yaxis_title='주기성',
        template='plotly_white',
        font=dict(family='Arial, sans-serif', size=12, color='#333', weight='bold'),
        plot_bgcolor='#ffffff',
        xaxis=dict(tickmode='array', tickvals=np.arange(7), ticktext=weekdays),
        margin=dict(t=50, b=40, l=40, r=20)
    )
    
    return fig1, fig2, fig3, fig4

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from dash.exceptions import PreventUpdate
from data_processing import load_data

# 페이지 등록
dash.register_page(__name__, path="/sales-dashboard", name="Sales Dashboard")

# 데이터 전처리
df = load_data()  # 전처리 함수 호출
df_working = df[df['근무_여부'] == '근무']

# 색상 맵 정의 (파스텔 톤)
COLOR_MAP = {
    '근무': '#AEC6CF',       
    '휴식중': '#FFD1DC',     
    '대기중': '#FFB347',     
    'NONE': '#CFCFC4'     
}

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

# 그래프를 위한 카드 컴포넌트 생성
def create_card(title, graph_id):
    return dbc.Card(
        [
            dbc.CardHeader(
                title, 
                className="card-header", 
                style={
                    'background-color': '#F8F9FA', 
                    'border-bottom': '1px solid #E9ECEF', 
                    'font-weight': 'bold', 
                    'font-size': '18px',
                    'color': '#333'
                }
            ),
            dbc.CardBody(
                [
                    dcc.Graph(id=graph_id, config={'displayModeBar': False}, style={'height': '400px'}),
                ],
                className="card-body",
                style={'padding': '20px'}
            )
        ],
        className="h-100",
        style={
            'border': 'none', 
            'box-shadow': '0 4px 8px rgba(0, 0, 0, 0.1)', 
            'border-radius': '16px'
        }
    )

# 중앙 연도 선택 체크박스 컴포넌트 생성
year_checkbox = dbc.Card(
    dbc.CardBody(
        [
            html.Label(
                "연도 선택",
                style={
                    'font-weight': 'bold',
                    'font-size': '16px',
                    'margin-bottom': '10px',
                    'color': '#007BFF'
                }
            ),
            dbc.Checklist(
                options=[{'label': str(year), 'value': year} for year in sorted(df['연도'].unique())],
                value=sorted(df['연도'].unique()),  # 기본적으로 모든 연도가 선택됨
                id="year-checkbox",
                inline=True,
                switch=True,
                style={
                    'display': 'flex', 
                    'flex-wrap': 'wrap', 
                    'gap': '10px', 
                    'padding': '10px 0', 
                    'background-color': '#F0F2F5',
                    'border-radius': '8px'
                }
            ),
        ],
        style={'padding': '20px'}
    ),
    style=FILTER_CARD_STYLE,
    className="mb-4"
)



# 로딩 스피너 컴포넌트
loading_spinner = dbc.Spinner(
    children=[
        dbc.Row(
            [
                dbc.Col(create_card("연도별 월별 총 판매량 변화", "monthly-sales"), width=4, id="monthly-sales-col"),
                dbc.Col(create_card("카테고리별 월별 총 판매량 변화", "category-sales"), width=4, id="category-sales-col"),
                dbc.Col(create_card("연도별 월별 평균 판매량 (근무당)", "average-sales-per-shift"), width=4, id="average-sales-per-shift-col")
            ],
            className="mb-4"
        ),
        dbc.Row(
            [
                dbc.Col(create_card("연도별 월별 총 매출액 변화", "monthly-revenue"), width=4, id="monthly-revenue-col"),
                dbc.Col(create_card("카테고리별 월별 총 매출액 변화", "category-revenue"), width=4, id="category-revenue-col"),
                dbc.Col(create_card("연도별 월별 평균 매출액 (근무당)", "average-revenue-per-shift"), width=4, id="average-revenue-per-shift-col")
            ],
            className="mb-4"
        ),
    ],
    color="primary",
    fullscreen=False,
    spinner_style={"width": "3rem", "height": "3rem"}
)

# 페이지 레이아웃 정의
layout = dbc.Container(
    [
        html.Div(
            [
                year_checkbox,  # 중앙 연도 선택 체크박스
                loading_spinner,  # 그래프 섹션 (로딩 스피너 포함)
            ],
            style={
                "padding": "20px"
            }
        )
    ],
    fluid=True,
    style={
        'background-color': '#E0F7FA', 
        'padding-top': '70px'  # 네비게이션 바 높이만큼 패딩 추가
    }
)

# 그래프 보이기/숨기기 콜백 함수
@dash.callback(
    [
        Output('monthly-sales-col', 'style'),
        Output('monthly-revenue-col', 'style'),
        Output('category-sales-col', 'style'),
        Output('category-revenue-col', 'style'),
        Output('average-sales-per-shift-col', 'style'),
        Output('average-revenue-per-shift-col', 'style')
    ],
    [Input('graph-toggle', 'value')]
)
def toggle_graphs(selected_graphs):
    return [
        {'display': 'block'} if 'monthly-sales-col' in selected_graphs else {'display': 'none'},
        {'display': 'block'} if 'monthly-revenue-col' in selected_graphs else {'display': 'none'},
        {'display': 'block'} if 'category-sales-col' in selected_graphs else {'display': 'none'},
        {'display': 'block'} if 'category-revenue-col' in selected_graphs else {'display': 'none'},
        {'display': 'block'} if 'average-sales-per-shift-col' in selected_graphs else {'display': 'none'},
        {'display': 'block'} if 'average-revenue-per-shift-col' in selected_graphs else {'display': 'none'},
    ]

# 콜백 함수: 그래프 업데이트 (연도 선택 체크박스 기반)
@dash.callback(
    [
        Output('monthly-sales', 'figure'),
        Output('monthly-revenue', 'figure'),
        Output('category-sales', 'figure'),
        Output('category-revenue', 'figure'),
        Output('average-sales-per-shift', 'figure'),
        Output('average-revenue-per-shift', 'figure'),
    ],
    [Input('year-checkbox', 'value')]
)
def update_graphs(selected_years):
    if not selected_years:
        return [go.Figure()] * 6

    # 연도별 월별 총 판매량 변화
    filtered_df = df_working[df_working['연도'].isin(selected_years)]
    monthly_total_sales = filtered_df.groupby(['연도', '월'])['판매량'].sum().reset_index()
    fig_sales = px.line(
        monthly_total_sales,
        x='월', y='판매량', color='연도',
        markers=True,
        title='연도별 월별 총 판매량 변화',
        labels={'판매량': '총 판매량', '월': '월'}
    )
    fig_sales.update_layout(
        xaxis_title='월',
        yaxis_title='총 판매량',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 연도별 월별 총 매출액 변화
    monthly_total_revenue = filtered_df.groupby(['연도', '월'])['매출액'].sum().reset_index()
    fig_revenue = px.line(
        monthly_total_revenue,
        x='월', y='매출액', color='연도',
        markers=True,
        title='연도별 월별 총 매출액 변화',
        labels={'매출액': '총 매출액', '월': '월'}
    )
    fig_revenue.update_layout(
        xaxis_title='월',
        yaxis_title='총 매출액',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 카테고리별 월별 총 판매량 변화
    monthly_sales = filtered_df.groupby(['연도', '월', '매장_카테고리'])['판매량'].sum().reset_index()
    fig_category_sales = px.area(
        monthly_sales,
        x='월', y='판매량', color='매장_카테고리', line_group='연도',
        markers=True,
        title='카테고리별 월별 총 판매량 변화',
        labels={'판매량': '총 판매량', '월': '월', '매장_카테고리': '카테고리'}
    )
    fig_category_sales.update_layout(
        xaxis_title='월',
        yaxis_title='총 판매량',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 카테고리별 월별 총 매출액 변화
    monthly_revenue = filtered_df.groupby(['연도', '월', '매장_카테고리'])['매출액'].sum().reset_index()
    fig_category_revenue = px.area(
        monthly_revenue,
        x='월', y='매출액', color='매장_카테고리', line_group='연도',
        markers=True,
        title='카테고리별 월별 총 매출액 변화',
        labels={'매출액': '총 매출액', '월': '월', '매장_카테고리': '카테고리'}
    )
    fig_category_revenue.update_layout(
        xaxis_title='월',
        yaxis_title='총 매출액',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 연도별 월별 평균 판매량 (근무당)
    monthly_stats_sales = filtered_df.groupby(['연도', '월']).agg(
        총_판매량=('판매량', 'sum'),
        근무_건수=('근무_여부', 'count')
    ).reset_index()
    monthly_stats_sales['평균_판매량_근무당'] = monthly_stats_sales['총_판매량'] / monthly_stats_sales['근무_건수']
    fig_avg_sales = px.line(
        monthly_stats_sales,
        x='월', y='평균_판매량_근무당', color='연도',
        markers=True,
        title='연도별 월별 평균 판매량 (근무당)',
        labels={'평균_판매량_근무당': '평균 판매량 (근무당)', '월': '월'}
    )
    fig_avg_sales.update_layout(
        xaxis_title='월',
        yaxis_title='평균 판매량 (근무당)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 연도별 월별 평균 매출액 (근무당)
    monthly_stats_revenue = filtered_df.groupby(['연도', '월']).agg(
        총_매출액=('매출액', 'sum'),
        근무_건수=('근무_여부', 'count')
    ).reset_index()
    monthly_stats_revenue['평균_매출액_근무당'] = monthly_stats_revenue['총_매출액'] / monthly_stats_revenue['근무_건수']
    fig_avg_revenue = px.line(
        monthly_stats_revenue,
        x='월', y='평균_매출액_근무당', color='연도',
        markers=True,
        title='연도별 월별 평균 매출액 (근무당)',
        labels={'평균_매출액_근무당': '평균 매출액 (근무당)', '월': '월'}
    )
    fig_avg_revenue.update_layout(
        xaxis_title='월',
        yaxis_title='평균 매출액 (근무당)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    return fig_sales, fig_revenue, fig_category_sales, fig_category_revenue, fig_avg_sales, fig_avg_revenue

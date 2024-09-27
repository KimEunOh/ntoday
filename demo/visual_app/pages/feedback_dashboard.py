import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_processing import load_data

# 페이지 등록
dash.register_page(__name__, path="/feedback_dashboard", name="Feedback Dashboard")

# 데이터 전처리
df = load_data()  # 전처리 함수 호출
df['기록_날짜'] = pd.to_datetime(df['기록_날짜'])

# 근무 시간 계산
df['근무_시작'] = pd.to_datetime(df['근무_시작'], format='%H:%M', errors='coerce')
df['근무_종료'] = pd.to_datetime(df['근무_종료'], format='%H:%M', errors='coerce')
df['근무_시간'] = (df['근무_종료'] - df['근무_시작']).dt.seconds / 3600
df['근무_시간'] = df['근무_시간'].fillna(0)
df['주'] = df['기록_날짜'].dt.to_period('W')

# 데이터 준비
weekly_stats = df.groupby(['주', '직원_ID']).agg(
    총_근무_시간=('근무_시간', 'sum'),
    평균_피드백_점수=('피드백_점수', 'mean')
).reset_index()

employment_feedback = df.groupby(['상태']).agg(
    평균_피드백_점수=('피드백_점수', 'mean')
).reset_index()

# 카테고리별 직원의 매출액과 근무 일수 계산
category_sales = df.groupby(['직원_ID', '매장_카테고리']).agg(
    총_매출액=('매출액', 'sum'),
    근무_일수=('기록_날짜', 'nunique')  # 직원이 해당 카테고리에서 근무한 일수 계산
).reset_index()

# 직원의 카테고리별 평균 매출액 계산
category_sales['평균_매출액_근무당'] = category_sales['총_매출액'] / category_sales['근무_일수']

# 연도 선택 체크박스 추가
unique_years = df['기록_날짜'].dt.year.unique()  # 데이터프레임에서 고유한 연도 추출

# '기록_날짜' 열을 그대로 유지하며 그룹화 후 연도를 추가하는 방식으로 수정
salary_stats = df.groupby(['직원_ID', df['기록_날짜'].dt.to_period('Y')]).agg(
    평균_급여=('직원_급여', 'mean')
).reset_index()

# '기록_날짜'를 datetime 형식으로 변환
salary_stats['기록_날짜'] = salary_stats['기록_날짜'].apply(lambda x: x.start_time)  # to_period로부터 datetime 변환

# 직원 ID 추출
employee_options = salary_stats['직원_ID'].unique()

# 색상 팔레트 정의
PRIMARY_COLOR = "#007BFF"
SECONDARY_COLOR = "#6C757D"
SUCCESS_COLOR = "#28A745"
DANGER_COLOR = "#DC3545"
WARNING_COLOR = "#FFC107"
INFO_COLOR = "#17A2B8"
LIGHT_COLOR = "#F8F9FA"
DARK_COLOR = "#343A40"

# 카드 스타일 정의
CARD_STYLE = {
    'box-shadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
    'border': 'none',
    'border-radius': '16px',
    'padding': '15px',
    'background-color': LIGHT_COLOR,
}

# 그래프를 위한 카드 컴포넌트 생성
def create_card(title, graph_id, additional_controls=None):
    components = [
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
                additional_controls if additional_controls else html.Div(),
                dcc.Graph(id=graph_id, config={'displayModeBar': False}, style={'height': '400px'}),
            ],
            className="card-body",
            style={'padding': '20px'}
        )
    ]
    return dbc.Card(
        components,
        className="h-100",
        style=CARD_STYLE
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
                options=[{'label': str(year), 'value': year} for year in sorted(unique_years)],
                value=list(sorted(unique_years)),  # 기본적으로 모든 연도가 선택됨
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
    style=CARD_STYLE,
    className="mb-4"
)



# 로딩 스피너 컴포넌트
loading_spinner = dbc.Spinner(
    children=[
        dbc.Row(
            [
                dbc.Col(create_card("주 단위 총 근무 시간에 따른 피드백 점수 변화", "weekly-feedback"), width=4, id="weekly-feedback-col"),
                dbc.Col(create_card("정규직, 계약직 여부에 따른 피드백 점수 변화", "employment-feedback"), width=4, id="employment-feedback-col"),
                dbc.Col(create_card("카테고리별 직원의 평균 매출액 (근무당)", "category-sales-personal"), width=4, id="category-sales-personal-col"),
            ],
            className="mb-4"
        ),
        dbc.Row(
            [
                dbc.Col(create_card("급여에 따른 피드백 점수", "salary-feedback"), width=4, id="salary-feedback-col"),
                dbc.Col(create_card("년도별 직원 급여", "salary-yearly"), width=4, id="salary-yearly-col"),
                dbc.Col(create_card("매장 거리와 피드백 점수 사이의 관계", "distance-feedback"), width=4, id="distance-feedback-col"),
            ],
            className="mb-4"
        ),
    ],
    color="primary",
    fullscreen=False,
    spinner_style={"width": "3rem", "height": "3rem"}
)

# 다크 모드 토글 버튼 추가 
dark_mode_toggle = dbc.Button(
    "Toggle Dark Mode",
    id="dark-mode-toggle",
    color="secondary",
    className="mb-4",
    style={'margin-left': '20px'}
)

# 페이지 레이아웃 정의
layout = dbc.Container(
    [

        html.Div(
            [
                dark_mode_toggle,  # 다크 모드 토글 버튼 추가 (선택 사항)
                year_checkbox,     # 중앙 연도 선택 체크박스
                loading_spinner,   # 그래프 섹션 (로딩 스피너 포함)
            ],
            style={
                "margin-left": "0px",  # 사이드바가 없는 경우 0으로 설정
                "padding": "20px"
            }
        )
    ],
    fluid=True,
    style={
        'background-color': '#E0F7FA',  # 전체 배경색 일관성 유지
        'padding-top': '70px'            # 네비게이션 바 높이만큼 패딩 추가
    }
)


# 다크 모드 토글 
@dash.callback(
    Output("page-content", "style"),
    [Input("dark-mode-toggle", "n_clicks")],
    [State("page-content", "style")]
)
def toggle_dark_mode(n_clicks, current_style):
    if n_clicks:
        if current_style and current_style.get('background-color') == '#E0F7FA':
            return {'background-color': '#343A40', 'color': '#FFFFFF', 'padding-top': '70px'}
        else:
            return {'background-color': '#E0F7FA', 'color': '#333', 'padding-top': '70px'}
    return current_style

# 콜백 함수: 그래프 업데이트 (연도 선택 체크박스 기반)
@dash.callback(
    [
        Output('weekly-feedback', 'figure'),
        Output('employment-feedback', 'figure'),
        Output('category-sales-personal', 'figure'),
        Output('salary-feedback', 'figure'),
        Output('salary-yearly', 'figure'),
        Output('distance-feedback', 'figure'),
    ],
    [
        Input('year-checkbox', 'value'),
        Input('category-sales-personal-col', 'children'),  # 필요 시 다른 필터 추가
    ]
)
def update_graphs(selected_years, _):
    if not selected_years:
        # 모든 그래프에 빈 Figure 반환
        return [go.Figure()] * 6

    # 필터링된 데이터 준비
    filtered_df = df[df['기록_날짜'].dt.year.isin(selected_years)]
    filtered_weekly_stats = weekly_stats[weekly_stats['주'].dt.year.isin(selected_years)]
    filtered_employment_feedback = employment_feedback  # 상태별 피드백은 연도와 무관하게 집계됨
    filtered_category_sales = category_sales[category_sales['직원_ID'].isin(employee_options)]
    filtered_salary_stats = salary_stats[salary_stats['기록_날짜'].dt.year.isin(selected_years)]
    filtered_distance_feedback = filtered_df

    # 1. 주 단위 총 근무 시간에 따른 피드백 점수 변화
    fig1 = px.scatter(
        filtered_weekly_stats,
        x='총_근무_시간', y='평균_피드백_점수', color='직원_ID',
        title='주 단위 총 근무 시간에 따른 피드백 점수 변화',
        labels={'총_근무_시간': '총 근무 시간 (시간)', '평균_피드백_점수': '평균 피드백 점수'},
        color_discrete_sequence=px.colors.sequential.Viridis,
        opacity=0.7,
        template='plotly_white'
    )
    fig1.update_layout(
        xaxis_title='총 근무 시간 (시간)',
        yaxis_title='평균 피드백 점수',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='closest',
        transition=dict(duration=500, easing='cubic-in-out'),
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 2. 정규직, 계약직 여부에 따른 피드백 점수 변화
    fig2 = px.bar(
        employment_feedback,
        x='상태', y='평균_피드백_점수',
        title='정규직, 계약직 여부에 따른 평균 피드백 점수',
        labels={'상태': '고용 형태', '평균_피드백_점수': '평균 피드백 점수'},
        color='상태',
        color_discrete_sequence=px.colors.diverging.Tealrose,
        template='plotly_white'
    )
    fig2.update_layout(
        xaxis_title='고용 형태',
        yaxis_title='평균 피드백 점수',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='closest',
        transition=dict(duration=500, easing='cubic-in-out'),
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 3. 카테고리별 직원의 평균 매출액 (근무당) 비교
    fig3 = px.bar(
        category_sales,
        x='직원_ID', y='평균_매출액_근무당', color='매장_카테고리',
        title='카테고리별 직원의 평균 매출액 (근무당) 비교',
        labels={'평균_매출액_근무당': '평균 매출액 (근무당)', '매장_카테고리': '카테고리'},
        barmode='group',
        color_discrete_sequence=px.colors.qualitative.Set2,
        template='plotly_white'
    )
    fig3.update_layout(
        xaxis_title='직원 ID',
        yaxis_title='평균 매출액 (근무당)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='closest',
        transition=dict(duration=500, easing='cubic-in-out'),
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 4. 급여에 따른 피드백 점수 시각화 - Box Plot
    filtered_df['급여_그룹'] = (filtered_df['직원_급여'] // 100) * 100  # 100만 원 단위로 그룹화
    fig4 = px.box(
        filtered_df,
        x='급여_그룹', y='피드백_점수',
        title='급여에 따른 피드백 점수 (100만 원 단위 그룹)',
        labels={'급여_그룹': '급여 (100만 원 단위)', '피드백_점수': '피드백 점수'},
        points='outliers',  # 이상치만 표시
        color_discrete_sequence=px.colors.sequential.Aggrnyl,
        template='plotly_white'
    )
    fig4.update_xaxes(tickformat=',', categoryorder='category ascending')
    fig4.update_layout(
        xaxis_title='급여 (100만 원 단위)',
        yaxis_title='피드백 점수',
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='closest',
        transition=dict(duration=500, easing='cubic-in-out'),
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 5. 년도별 직원 급여 - 선택된 연도 기준
    fig5 = px.bar(
        filtered_salary_stats,
        x='직원_ID', y='평균_급여', color=filtered_salary_stats['기록_날짜'].dt.year.astype(str),
        title='선택된 연도에 따른 직원별 급여 비교',
        labels={'직원_ID': '직원 ID', '평균_급여': '평균 급여', 'color': '연도'},
        barmode='group',
        color_discrete_sequence=px.colors.qualitative.Set2,
        template='plotly_white'
    )
    fig5.update_layout(
        xaxis_title='직원 ID',
        yaxis_title='평균 급여',
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='closest',
        transition=dict(duration=500, easing='cubic-in-out'),
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    # 6. 매장 거리와 피드백 점수 사이의 관계 - Box Plot
    filtered_df['거리_그룹'] = (filtered_df['직원_매장_거리'] // 1) * 1  # 1km 단위로 그룹화
    fig6 = px.box(
        filtered_df,
        x='거리_그룹', y='피드백_점수',
        title='매장 거리와 피드백 점수 사이의 관계 (1km 단위 그룹)',
        labels={'거리_그룹': '매장 거리 (km 단위)', '피드백_점수': '피드백 점수'},
        points='outliers',
        color_discrete_sequence=px.colors.sequential.Plasma,
        template='plotly_white'
    )
    fig6.update_layout(
        xaxis_title='매장 거리 (km 단위)',
        yaxis_title='피드백 점수',
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='closest',
        transition=dict(duration=500, easing='cubic-in-out'),
        font=dict(
            size=16,
            family='Arial',
            color='#333',
            weight='bold'
        )
    )

    return fig1, fig2, fig3, fig4, fig5, fig6

import os
import dash
import numpy as np
import logging
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
from dash.dash_table import DataTable
import pandas as pd
import plotly.express as px
from flask_caching import Cache

# 로깅 기본 구성
logging.basicConfig(level=logging.DEBUG)

# Dash 앱 초기화 및 Bootstrap 테마 적용
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY])
server = app.server  # 플랫폼에 배포 시 사용

# 캐시 디렉토리 생성
if not os.path.exists('cache-directory'):
    os.makedirs('cache-directory')

# Flask-Caching 설정
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',        # 파일 시스템을 캐시로 사용
    'CACHE_DIR': 'cache-directory',    # 캐시 파일을 저장할 디렉토리
    'CACHE_DEFAULT_TIMEOUT': 300       # 캐시 만료 시간 (초 단위, 기본 5분)
})

# CSV 파일 경로 설정
CSV_PATH = os.path.abspath('vacation/2024_vacation.csv')

# 그래프에 사용할 파스텔 색상 설정
pastel_colors = px.colors.qualitative.Pastel1

# 날짜를 정리하고 처리하는 헬퍼 함수
def clean_date(date):
    if pd.isna(date):
        return pd.NaT, None
    parts = date.split('(')
    date_cleaned = parts[0].strip()
    day_of_week = parts[1][:-1] if len(parts) > 1 else None
    try:
        date_converted = pd.to_datetime(date_cleaned, errors='coerce')
    except:
        date_converted = pd.NaT
    return date_converted, day_of_week

# 포인트를 일별로 분배하는 헬퍼 함수 수정
def distribute_points_by_day(row):
    total_points = float(row['신청 포인트'])
    start_date = row['시작 날짜']
    end_date = row['종료 날짜']
    vacation_type = row.get('휴가 종류', '기타')
    leave_reason = row.get('휴가 사유', 'N/A')
    remaining_after = float(row.get('잔여 포인트', 0.0))
    approval_status = row.get('승인 여부', '완료')
    document_number = row.get('문서 번호', 'N/A')
    department = row.get('기안 부서', 'N/A')
    applicant_name = row.get('기안자 이름', 'N/A')

    if pd.isna(start_date) or pd.isna(end_date):
        return pd.DataFrame()

    # '시작 날짜'부터 '종료 날짜'까지의 날짜 리스트 생성 (주말 제외)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    # 주말(토요일: 5, 일요일: 6)을 제외
    weekdays = date_range[date_range.weekday < 5]

    if len(weekdays) == 0:
        return pd.DataFrame()

    # 휴가 종류가 연차더라도, 포인트 값에 따라 반차 또는 반반차로 변경
    if vacation_type == '연차':
        if total_points == 0.25:
            vacation_type = '반반차'
        elif total_points == 0.5:
            vacation_type = '반차'
        else:
            vacation_type = '연차'

    distributed_point = {
        '문서 번호': document_number,
        '기안자 이름': applicant_name,
        '기안 부서': department,
        '시작 날짜': start_date,
        '종료 날짜': end_date,
        '포인트': total_points,        # 총 신청 포인트
        '휴가 종류': vacation_type,
        '휴가 사유': leave_reason,
        '잔여 포인트': remaining_after,
        '승인 여부': approval_status
    }

    return pd.DataFrame([distributed_point])

#휴가 기간을 분배하는 함수
def expand_leave_dates(row):
    total_points = float(row['포인트'])
    start_date = row['시작 날짜']
    end_date = row['종료 날짜']
    vacation_type = row['휴가 종류']
    applicant_name = row['기안자 이름']
    department = row['기안 부서']

    # '시작 날짜'부터 '종료 날짜'까지의 날짜 리스트 생성 (주말 제외)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    # 주말(토요일: 5, 일요일: 6)을 제외
    weekdays = date_range[date_range.weekday < 5]

    # 일별 포인트 계산 (총 포인트를 평일 수로 나눔)
    daily_point = total_points / len(weekdays) if len(weekdays) > 0 else 0

    expanded_rows = []
    for date in weekdays:
        expanded_row = {
            '기안자 이름': applicant_name,
            '기안 부서': department,
            '날짜': date,
            '포인트': daily_point,
            '휴가 종류': vacation_type
        }
        expanded_rows.append(expanded_row)

    return pd.DataFrame(expanded_rows)

def update_last_document_points(distributed_df):
    # 기안자 이름별로 그룹화하여 마지막 문서번호에 잔여 포인트 업데이트
    grouped = distributed_df.groupby(['기안자 이름', '문서 번호'])

    # 각 기안자의 마지막 문서 번호를 가져와 잔여 포인트를 계산 및 업데이트
    for (name, doc_num), group in grouped:
        # 각 기안자별로 문서 번호 기준으로 마지막 문서 찾기
        final_remaining = group['잔여 포인트'].iloc[-1]
        final_submit = group['포인트'].iloc[-1]

        # 마지막 문서에 해당하는 잔여 포인트 업데이트
        idx = (distributed_df['기안자 이름'] == name) & (distributed_df['문서 번호'] == doc_num)
        distributed_df.loc[idx, '잔여 포인트'] = final_remaining - final_submit

    return distributed_df

# 데이터 로드 및 처리 함수 (캐시 활성화)
@cache.memoize()
def load_and_process_data(file_mod_time):
    logging.debug("Loading and processing data...")
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, sep=',', encoding='utf-8-sig')

    # 컬럼 이름의 앞뒤 공백 제거
    df.columns = df.columns.str.strip()

    # 부서 명칭 변경
    df['기안 부서'] = df['기안 부서'].replace({
        '기술개발팀': '개발팀',
        'UI-UX팀': '퍼블리싱'
    })

    # 날짜 컬럼 분리 및 변환
    df[['기안일', '기안 요일']] = df['기안일'].apply(lambda x: clean_date(x)).apply(pd.Series)
    df[['시작 날짜', '시작 요일']] = df['시작 날짜'].apply(lambda x: clean_date(x)).apply(pd.Series)
    df[['종료 날짜', '종료 요일']] = df['종료 날짜'].apply(lambda x: clean_date(x)).apply(pd.Series)


    # 승인 여부가 '완료'인 연차만 필터링
    df = df[df['승인 여부'] == '완료']

    # 날짜 컬럼 변환
    df['시작 날짜'] = pd.to_datetime(df['시작 날짜'])
    df['종료 날짜'] = pd.to_datetime(df['종료 날짜'])

    # 포인트를 문서별로 처리
    distributed_df = pd.concat(
        df.apply(distribute_points_by_day, axis=1).tolist(),
        ignore_index=True
    )

    logging.debug(f"분배된 데이터프레임(distributed_df) 정보:\n{distributed_df.info()}")
    logging.debug(f"분배된 데이터프레임(distributed_df) 첫 5행:\n{distributed_df.head()}")


    # 마지막 문서별로 잔여 포인트 업데이트
    distributed_df = update_last_document_points(distributed_df)

    # 휴가 기간을 일별로 확장한 데이터프레임 생성
    expanded_df = pd.concat(
        distributed_df.apply(expand_leave_dates, axis=1).tolist(),
        ignore_index=True
    )

    logging.debug(f"확장된 데이터프레임(expanded_df) 정보:\n{expanded_df.info()}")
    logging.debug(f"확장된 데이터프레임(expanded_df) 첫 5행:\n{expanded_df.head()}")

    return df, distributed_df, expanded_df

# Dash 앱 레이아웃 설정
app.layout = dbc.Container([
    # 헤더
    dbc.Row(
        dbc.Col(
            dbc.Navbar(
                dbc.Container([
                    dbc.Row(
                        [
                            # 좌측: 로고 이미지
                            dbc.Col(
                                html.Img(
                                    src=app.get_asset_url("n2.png"),
                                    id="navbar-logo",
                                    style={
                                        "height": "60px",
                                        "width": "auto",
                                        "marginRight": "20px",  # 제목과의 간격 조절
                                    },
                                ),
                                width="auto",
                                align="center"
                            ),
                            # 중앙: 제목
                            dbc.Col(
                                html.H1(
                                    "연차 관리 대시보드",
                                    className='text-dark text-center',
                                    style={'margin': '0'}
                                ),
                                width=True,
                                align="center"
                            ),
                            # 우측: 빈 공간 (중앙 정렬을 위해)
                            dbc.Col(
                                # 빈 Column
                                width="auto"
                            )
                        ],
                        align="center",
                        className="w-100"
                    )
                ]),
                color="light",
                dark=False,
                className="p-0",  # 패딩 제거
            ),
            width=12
        )
    ),

    # 상단 영역: 필터 및 요약 정보
    dbc.Row([
        # 좌측: 필터 섹션
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("필터", className='text-center'),
                dbc.CardBody([
                    # 날짜 범위 선택 슬라이더
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("날짜 범위"),
                            dcc.RangeSlider(
                                id='date-slider',
                                min=0,               # 콜백에서 업데이트됨
                                max=0,
                                value=[0, 0],
                                marks={},            # 콜백에서 업데이트됨
                                step=24*60*60,      # 하루 단위 (초 단위)
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                        ], width=12)
                    ], className='mb-4'),

                    # 부서 선택 드롭다운
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("부서 선택"),
                            dcc.Dropdown(
                                id='department-filter',
                                options=[{'label': '전체', 'value': '전체'}],  # 초기 옵션
                                value='전체',
                                clearable=False
                            )
                        ], width=12)
                    ], className='mb-4'),

                    # 연차 유형 라디오 버튼
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("연차 유형"),
                            dbc.RadioItems(
                                id='leave-type',
                                options=[
                                    {'label': '연차 횟수', 'value': 'count'},
                                    {'label': '연차 시간', 'value': 'time'}
                                ],
                                value='count',
                                inline=True
                            )
                        ], width=12)
                    ], className='mb-4'),

                    # 정렬 기준 라디오 버튼
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("정렬 기준"),
                            dbc.RadioItems(
                                id='sort-criteria',
                                options=[
                                    {'label': '전체 기간', 'value': '전체'},
                                    {'label': '최근 1개월', 'value': '최근 1개월'},
                                    {'label': '최근 3개월', 'value': '최근 3개월'},
                                    {'label': '최근 6개월', 'value': '최근 6개월'},
                                    {'label': '최근 1년', 'value': '최근 1년'}
                                ],
                                value='전체',
                                inline=True
                            )
                        ], width=12)
                    ])
                ])
            ], style={'height': '100%'})
        ], md=6),

        # 우측: 요약 정보 및 월별 사용 그래프
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("요약 정보", className='text-center'),
                dbc.CardBody([
                    # 요약 정보 카드
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("총 연차 수", className='card-title'),
                                    html.P(id='total-leaves', className='card-text', style={'fontSize': '24px', 'fontWeight': 'bold'})
                                ])
                            ], color="info", inverse=True, className='h-100')
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("총 포인트 합계", className='card-title'),
                                    html.P(id='total-points', className='card-text', style={'fontSize': '24px', 'fontWeight': 'bold'})
                                ])
                            ], color="success", inverse=True, className='h-100')
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("연차 사용율 상위 부서(기간)", className='card-title'),
                                    html.P(id='highest-department', className='card-text', style={'fontSize': '18px', 'fontWeight': 'bold'})
                                ])
                            ], color="warning", inverse=True, className='h-100')
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("연차 사용율 하위 부서(기간)", className='card-title'),
                                    html.P(id='lowest-department', className='card-text', style={'fontSize': '18px', 'fontWeight': 'bold'})
                                ])
                            ], color="danger", inverse=True, className='h-100')
                        ], md=3)
                    ], className='g-4'),

                    # 월별 연차 사용 그래프
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(id='monthly-usage-bar', style={'height': '300px'})
                        ])
                    ], className='mt-4')
                ])
            ])
        ], md=6)
    ], className='mb-4'),

    # 새로운 그래프 추가: 연차 소진율, 요일별 연차 사용 비율, 부서별 잔여 연차 분포
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("연차 소진율", className='text-center'),
                dbc.CardBody([
                    dcc.Graph(id='vacation-usage-rate', style={'height': '400px'})
                ])
            ])
        ], md=4),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("요일별 연차 사용 비율", className='text-center'),
                dbc.CardBody([
                    dcc.Graph(id='weekday-vacation-ratio', style={'height': '400px'})
                ])
            ])
        ], md=3),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("부서별 잔여 연차 분포", className='text-center'),
                dbc.CardBody([
                    dcc.Graph(id='department-vacation-distribution', style={'height': '400px'})
                ])
            ])
        ], md=5),
    ], className='mb-4'),

    # 하단 영역: 테이블 및 차트
    dbc.Row([
        # 좌측: 연차 사용 테이블
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("연차 사용 테이블"),
                dbc.CardBody([
                    DataTable(
                        id='leave-table',
                        columns=[
                            {'name': '기안자 이름', 'id': '기안자 이름'},
                            {'name': '기안 부서', 'id': '기안 부서'},
                            {'name': '시작 날짜', 'id': '시작 날짜'},
                            {'name': '종료 날짜', 'id': '종료 날짜'},
                            {'name': '포인트', 'id': '포인트'},
                            {'name': '휴가 종류', 'id': '휴가 종류'},
                            {'name': '잔여 포인트', 'id': '잔여 포인트'},
                            {'name': '승인 여부', 'id': '승인 여부'}
                        ],
                        data=[],                      # 콜백에서 업데이트됨
                        page_size=10,
                        filter_action='native',       # 검색 기능 활성화
                        sort_action='native',         # 정렬 기능 활성화
                        sort_mode='multi',            # 다중 정렬 지원
                        style_table={'overflowY': 'auto', 'overflowX': 'auto', 'height': '400px'},
                        style_cell={'textAlign': 'center', 'padding': '5px'},
                        row_selectable='single',
                        selected_rows=[]
                    )
                ])
            ])
        ], md=6),

        # 우측: 월별 포인트 합계 바 차트
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("월별 포인트 합계", className='text-center'),
                dbc.CardBody([
                    dcc.Graph(id='points-by-vacation-type', style={'height': '400px'})
                ])
            ])
        ], md=6)
    ], className='mb-4'),

    # 상세 정보 영역: 선택된 기안자의 연차 상세 정보 테이블
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("기안자 연차 상세 정보"),
                dbc.CardBody([
                    DataTable(
                        id='detail-table',
                        columns=[
                            {'name': '문서 번호', 'id': '문서 번호'},
                            {'name': '기안자 이름', 'id': '기안자 이름'},
                            {'name': '기안 부서', 'id': '기안 부서'},
                            {'name': '시작 날짜', 'id': '시작 날짜'},
                            {'name': '포인트', 'id': '포인트'},
                            {'name': '휴가 종류', 'id': '휴가 종류'},
                            {'name': '휴가 사유', 'id': '휴가 사유'},
                            {'name': '현재 최종 잔여 포인트', 'id': '잔여 포인트'},
                            {'name': '승인 여부', 'id': '승인 여부'}
                        ],
                        data=[],
                        page_size=10,
                        style_table={'overflowY': 'auto', 'overflowX': 'auto', 'height': '400px'},
                        style_cell={'textAlign': 'center', 'padding': '5px'},
                    )
                ])
            ])
        ], md=12)
    ]),

    # Interval 컴포넌트: 1분(60초)마다 데이터 업데이트
    dcc.Interval(
        id='interval-component',
        interval=60*1000,      # 60,000 밀리초 = 60초 = 1분
        n_intervals=0         # 초기 값
    )
], fluid=True)

# 부서 필터 옵션 업데이트 콜백
@app.callback(
    Output('department-filter', 'options'),
    Input('interval-component', 'n_intervals')
)
def update_department_options(n_intervals):
    try:
        file_mod_time = int(os.path.getmtime(CSV_PATH))
        df, _, _ = load_and_process_data(file_mod_time)  
    except FileNotFoundError:
        return [{'label': '전체', 'value': '전체'}]
    except Exception as e:
        print(f"Error in update_department_options: {e}")
        return [{'label': '전체', 'value': '전체'}]

    department_column = '기안 부서' if '기안 부서' in df.columns else None
    if department_column:
        departments = sorted(df[department_column].dropna().unique())
    else:
        departments = []
    department_options = [{'label': '전체', 'value': '전체'}] + [{'label': dept, 'value': dept} for dept in departments]
    return department_options

# RangeSlider 설정을 업데이트하는 별도의 콜백 함수
@app.callback(
    [
        Output('date-slider', 'min'),
        Output('date-slider', 'max'),
        Output('date-slider', 'marks'),
        Output('date-slider', 'value')
    ],
    [
        Input('interval-component', 'n_intervals'),
        Input('sort-criteria', 'value')
    ]
)
def update_date_slider(n_intervals, sort_criteria):
    try:
        file_mod_time = int(os.path.getmtime(CSV_PATH))
        _, distributed_df, _ = load_and_process_data(file_mod_time)  
    except FileNotFoundError:
        return 0, 0, {}, [0, 0]
    except Exception as e:
        print(f"Error in update_date_slider: {e}")
        return 0, 0, {}, [0, 0]

    # 최소 및 최대 날짜 설정
    min_date = distributed_df['시작 날짜'].min()
    max_date = distributed_df['종료 날짜'].max()

    if pd.isna(min_date) or pd.isna(max_date):
        min_date = pd.Timestamp('2024-01-01')
        max_date = pd.Timestamp('2024-12-31')

    # 정렬 기준에 따라 날짜 범위 설정
    if sort_criteria == '최근 1개월':
        recent_start = max_date - pd.DateOffset(months=1)
    elif sort_criteria == '최근 3개월':
        recent_start = max_date - pd.DateOffset(months=3)
    elif sort_criteria == '최근 6개월':
        recent_start = max_date - pd.DateOffset(months=6)
    elif sort_criteria == '최근 1년':
        recent_start = max_date - pd.DateOffset(years=1)
    else:
        recent_start = min_date  # '전체' 선택 시 전체 기간

    # recent_start이 min_date보다 이전으로 설정되지 않도록 조정
    recent_start = max(recent_start, min_date)

    # RangeSlider에 사용할 Unix 타임스탬프 설정
    range_slider_min = int(min_date.timestamp())
    range_slider_max = int(max_date.timestamp())
    range_slider_marks = {int(date.timestamp()): date.strftime('%Y-%m') for date in pd.date_range(min_date, max_date, freq='MS')}
    range_slider_value = [int(recent_start.timestamp()), int(max_date.timestamp())]

    return range_slider_min, range_slider_max, range_slider_marks, range_slider_value

# 대시보드 컴포넌트를 업데이트하는 메인 콜백 함수
@app.callback(
    [
        Output('leave-table', 'data'),
        Output('monthly-usage-bar', 'figure'),
        Output('total-leaves', 'children'),
        Output('total-points', 'children'),
        Output('highest-department', 'children'),
        Output('lowest-department', 'children'),
        Output('points-by-vacation-type', 'figure'),
        Output('vacation-usage-rate', 'figure'),               # 연차 소진율 그래프
        Output('weekday-vacation-ratio', 'figure'),            # 요일별 연차 사용 비율 그래프
        Output('department-vacation-distribution', 'figure')   # 부서별 잔여 연차 분포 그래프
    ],
    [
        Input('interval-component', 'n_intervals'),
        Input('department-filter', 'value'),
        Input('leave-type', 'value'),
        Input('sort-criteria', 'value'),
        Input('date-slider', 'value')  # RangeSlider의 value를 Input으로 추가
    ]
)
def update_dashboard(n_intervals, department, leave_type, sort_criteria, date_slider_values):
    logging.debug("Updating dashboard...")
    try:
        # CSV 파일의 수정 시간 가져오기
        file_mod_time = int(os.path.getmtime(CSV_PATH))

        # 데이터 로드 및 처리
        df, distributed_df, expanded_df = load_and_process_data(file_mod_time)
    except FileNotFoundError:
        # CSV 파일이 없을 경우, 빈 데이터와 기본 값 반환
        return (
            [],                      # leave-table 데이터
            {},                      # monthly-usage-bar 그래프
            "0 회",                  # total-leaves
            "0 포인트",              # total-points
            "N/A",                   # highest-department
            "N/A",                   # lowest-department
            {},                      # points-by-vacation-type 그래프
            {},                      # vacation-usage-rate 그래프
            {},                      # weekday-vacation-ratio 그래프
            {}                      # department-vacation-distribution 그래프
        )
    except Exception:
        return (
            [], {}, "0 회", "0 포인트", "N/A", "N/A", {}, {}, {}, {}
        )

    # 부서 컬럼 확인
    department_column = '기안 부서' if '기안 부서' in df.columns else None

    # RangeSlider 값으로부터 시작 및 종료 날짜 설정
    if date_slider_values and len(date_slider_values) == 2:
        start_date = pd.to_datetime(date_slider_values[0], unit='s')
        end_date = pd.to_datetime(date_slider_values[1], unit='s')
    else:
        # 기본값 설정 (전체 기간)
        start_date = distributed_df['시작 날짜'].min()
        end_date = distributed_df['종료 날짜'].max()

    # 날짜 범위에 따라 원본 df 필터링
    df_filtered = df[
        (df['종료 날짜'] <= end_date) & (df['시작 날짜'] >= start_date)
    ]

    # 부서에 따라 df_filtered 필터링
    if department != '전체' and department_column:
        df_filtered = df_filtered[df_filtered[department_column] == department]

    # 총 연차 수와 총 포인트 합계 계산
    total_leaves = len(df_filtered)
    total_points = df_filtered['신청 포인트'].sum()

    # 분배된 df를 날짜 범위로 필터링
    filtered_df = distributed_df[
        (distributed_df['시작 날짜'] >= start_date) & (distributed_df['종료 날짜'] <= end_date)
    ]

    # 부서에 따른 필터링
    if department != '전체' and department_column:
        filtered_df = filtered_df[filtered_df['기안 부서'] == department]

    # 연차 유형에 따라 '연차 사용' 필드 조정
    if leave_type == 'count':
        filtered_df_display = filtered_df.copy()
        filtered_df_display['연차 사용'] = 1  # 횟수로 카운팅
    else:
        filtered_df_display = filtered_df.copy()
        filtered_df_display['연차 사용'] = filtered_df_display['포인트']  # 포인트 합계 사용

    # **요일별 집계를 위해 expanded_df를 날짜 범위와 부서로 필터링**
    expanded_filtered_df = expanded_df[
        (expanded_df['날짜'] >= start_date) & (expanded_df['날짜'] <= end_date)
    ]
    if department != '전체' and department_column:
        expanded_filtered_df = expanded_filtered_df[expanded_filtered_df['기안 부서'] == department]

    # **요일 정보 추가 (한국어 요일명)**
    day_mapping = {0: '월요일', 1: '화요일', 2: '수요일', 3: '목요일', 4: '금요일'}
    expanded_filtered_df['요일'] = expanded_filtered_df['날짜'].dt.dayofweek.map(day_mapping)

    # 추가 정렬 기준 적용
    if sort_criteria != '전체':
        if sort_criteria == '최근 1개월':
            recent_date = end_date - pd.DateOffset(months=1)
        elif sort_criteria == '최근 3개월':
            recent_date = end_date - pd.DateOffset(months=3)
        elif sort_criteria == '최근 6개월':
            recent_date = end_date - pd.DateOffset(months=6)
        elif sort_criteria == '최근 1년':
            recent_date = end_date - pd.DateOffset(years=1)
        filtered_df_display = filtered_df_display[filtered_df_display['시작 날짜'] >= recent_date]
        expanded_filtered_df = expanded_filtered_df[expanded_filtered_df['날짜'] >= recent_date]


    # 부서별 연차 사용 비율 계산
    filtered_df_usage = df[df['휴가 종류'].isin(['연차', '반차', '반반차'])]

    if department_column and '신청 포인트' in df_filtered.columns and len(df_filtered) > 0:
        # 1. 부서별 1년간 전체 연차 사용 일 수 계산
        total_dept_usage = filtered_df_usage.groupby(department_column)['신청 포인트'].sum()

        # 2. 선택된 기간 동안 부서별 총 연차 사용 일 수 계산
        selected_dept_sum = df_filtered[df_filtered['휴가 종류'].isin(['연차', '반차', '반반차'])].groupby(department_column)['신청 포인트'].sum()

        # 3. 부서별 전체 사용량 대비 선택된 기간 사용 비율 계산 (비율을 퍼센트로 변환)
        dept_usage_ratio = (selected_dept_sum / total_dept_usage).fillna(0) * 100  # 퍼센트로 변환

        # 4. 부서별 인원 수 계산 (부서별 인원 수 편차 보정)
        dept_employee_count = df.groupby(department_column)['기안자 이름'].nunique()

        # 5. 로그 변환을 통해 인원 수 편차 보정 (로그 스케일 적용)
        log_dept_employee_count = np.log1p(dept_employee_count)  # 로그(1 + 인원 수)

        # 6. 인원 수를 보정한 연차 사용 비율 계산
        dept_adjusted_usage_ratio = (dept_usage_ratio / log_dept_employee_count).fillna(0)

        # 7. 최고 및 최저 부서 추출 (보정된 비율 사용)
        if not dept_adjusted_usage_ratio.empty:
            highest_dept = dept_adjusted_usage_ratio.idxmax()
            lowest_dept = dept_adjusted_usage_ratio.idxmin()
        else:
            highest_dept = "N/A"
            lowest_dept = "N/A"
    else:
        highest_dept = "N/A"
        lowest_dept = "N/A"

    # 테이블 데이터 포맷 변경
    filtered_df_display = filtered_df_display.copy()
    filtered_df_display['시작 날짜'] = filtered_df_display['시작 날짜'].dt.strftime('%Y-%m-%d')
    filtered_df_display['종료 날짜'] = filtered_df_display['종료 날짜'].dt.strftime('%Y-%m-%d')
    filtered_df_display['포인트'] = filtered_df_display['포인트'].astype(float).apply(lambda x: x if x >= 0 else 0.0)

    # '잔여 포인트'를 원본 df의 '문서 번호'를 기준으로 매핑
    if '문서 번호' in filtered_df_display.columns:
        leave_points = df.set_index('문서 번호')['잔여 포인트']
        filtered_df_display['잔여 포인트'] = filtered_df_display['문서 번호'].map(leave_points)

    # 테이블에 필요한 컬럼만 선택
    table_data = filtered_df_display[['기안자 이름', '기안 부서', '시작 날짜', '종료 날짜', '포인트', '휴가 종류', '잔여 포인트', '승인 여부']].to_dict('records')

    # 월별 연차 사용량 그래프 생성
    monthly_usage = filtered_df_display.copy()
    monthly_usage['월'] = pd.to_datetime(monthly_usage['시작 날짜']).dt.to_period('M')
    monthly_usage_grouped = monthly_usage.groupby(['월', '휴가 종류'])['연차 사용'].sum().reset_index()
    monthly_usage_grouped['월'] = monthly_usage_grouped['월'].dt.to_timestamp()

    fig_monthly_usage = px.bar(
        monthly_usage_grouped,
        x='월',
        y='연차 사용',
        color='휴가 종류',
        title='월별 연차 사용량',
        labels={'월': '월', '연차 사용': '연차 사용량', '휴가 종류': '휴가 종류'},
        color_discrete_sequence=pastel_colors
    )
    fig_monthly_usage.update_layout(xaxis_title='월', yaxis_title='연차 사용량', height=350)

    # 월별 포인트 합계 바 차트 생성
    points_by_vacation = filtered_df.copy()
    points_by_vacation['월'] = points_by_vacation['시작 날짜'].dt.to_period('M')
    points_grouped = points_by_vacation.groupby(['월', '휴가 종류'])['포인트'].sum().reset_index()
    points_grouped['월'] = points_grouped['월'].dt.to_timestamp()

    fig_points_vacation = px.bar(
        points_grouped,
        x='월',
        y='포인트',
        color='휴가 종류',
        title='월별 포인트 합계',
        labels={'월': '월', '포인트': '포인트 합계', '휴가 종류': '휴가 종류'},
        color_discrete_sequence=pastel_colors
    )
    fig_points_vacation.update_layout(height=400)

    # 연차 소진율 그래프 생성
    team_usage_analysis = filtered_df_usage.groupby('기안 부서').agg(
        총사용량=('신청 포인트', 'sum'),         
        직원수=('기안자 이름', 'nunique')        
    ).reset_index()

    # 각 직원별 가장 최신 문서 번호로 잔여 포인트 데이터 추출
    final_remaining = distributed_df.sort_values(by=['기안자 이름', '문서 번호']).groupby('기안자 이름').tail(1)

    # 부서별 총잔여량 계산 (최종 잔여 포인트의 합계)
    total_remaining = final_remaining.groupby('기안 부서')['잔여 포인트'].sum().reset_index().rename(columns={'잔여 포인트': '총잔여량'})

    # 부서별 총잔여량을 team_usage_analysis에 병합
    team_usage_analysis = team_usage_analysis.merge(total_remaining, on='기안 부서', how='left')

    # 총잔여량이 NaN인 경우 0으로 채우기
    team_usage_analysis['총잔여량'] = team_usage_analysis['총잔여량'].fillna(0)

    # 부서별 평균 사용량 및 평균 잔여량 계산
    team_usage_analysis['평균사용량'] = team_usage_analysis['총사용량'] / team_usage_analysis['직원수']
    team_usage_analysis['평균잔여량'] = team_usage_analysis['총잔여량'] / team_usage_analysis['직원수']

    # 연차 소진율 (%) 계산 (평균 사용량 기반)
    team_usage_analysis['연차 소진율 (%)'] = (
        team_usage_analysis['평균사용량'] /
        (team_usage_analysis['평균사용량'] + team_usage_analysis['평균잔여량'])
    ) * 100

    # 소진율이 100%를 넘지 않도록 제한
    team_usage_analysis['연차 소진율 (%)'] = team_usage_analysis['연차 소진율 (%)'].clip(upper=100)

    # 연차 소진율 그래프 생성 (부서별 바 차트)
    fig_vacation_usage_rate = px.bar(
        team_usage_analysis,
        x='기안 부서',
        y='연차 소진율 (%)',
        title='부서별 연차 소진율 (%)',
        labels={'기안 부서': '부서', '연차 소진율 (%)': '연차 소진율 (%)'},
        color='연차 소진율 (%)',
        color_continuous_scale='Blues'
    )
    fig_vacation_usage_rate.update_layout(
        xaxis_title='부서',
        yaxis_title='연차 소진율 (%)',
        height=400,
        bargap=0.1  # 막대 간격 조정
    )

    # **요일별 연차 사용 비율 그래프 생성**
    weekday_usage = expanded_filtered_df.groupby('요일')['포인트'].sum().reset_index()

    # 요일별 연차 사용 비율 계산
    total_weekday_usage = weekday_usage['포인트'].sum()
    weekday_usage['연차 사용 비율 (%)'] = (weekday_usage['포인트'] / total_weekday_usage) * 100

    # 요일별 연차 사용 비율 그래프 생성 (파이 차트)
    fig_weekday_vacation_ratio = px.pie(
        weekday_usage,
        names='요일',
        values='연차 사용 비율 (%)',
        title='요일별 연차 사용 비율 (%)',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )


    # 부서별 잔여 연차 분포 그래프 생성
    latest_points = distributed_df.sort_values(by=['기안자 이름', '문서 번호']).groupby('기안자 이름').tail(1)

    # 부서별 잔여 연차 분포 그래프 생성 (Box Plot)
    fig_department_vacation_distribution = px.box(
        latest_points,
        x='기안 부서',
        y='잔여 포인트',
        title='부서별 최신 잔여 연차 분포 (문서 기준)',
        labels={'기안 부서': '부서', '잔여 포인트': '잔여 연차 일수'},
        color='기안 부서',
        boxmode='group'
    )

    # 박스 너비 조절
    fig_department_vacation_distribution.update_traces(width=0.5)

    # 레이아웃 업데이트
    fig_department_vacation_distribution.update_layout(
        xaxis_title='부서',
        yaxis_title='잔여 연차 일수',
        height=400
    )

    return (
        table_data,                     # leave-table 데이터
        fig_monthly_usage,             # monthly-usage-bar 그래프
        f"{total_leaves} 회",           # total-leaves
        f"{total_points} 포인트",        # total-points
        highest_dept,                  # highest-department
        lowest_dept,                   # lowest-department
        fig_points_vacation,           # points-by-vacation-type 그래프
        fig_vacation_usage_rate,       # 연차 소진율 그래프
        fig_weekday_vacation_ratio,    # 요일별 연차 사용 비율 그래프
        fig_department_vacation_distribution,  # 부서별 잔여 연차 분포 그래프
    )

# 선택된 행에 따른 상세 정보 표시 콜백 함수
@app.callback(
    Output('detail-table', 'data'),
    [Input('leave-table', 'selected_rows')],
    [State('leave-table', 'data')]
)
def display_detail(selected_rows, table_data):
    if not selected_rows:
        return []

    selected_row = table_data[selected_rows[0]]
    applicant_name = selected_row['기안자 이름']
    date = selected_row['시작 날짜']

    try:
        # CSV 파일의 수정 시간 가져오기
        file_mod_time = int(os.path.getmtime(CSV_PATH))

        # 데이터 로드 및 처리
        df, distributed_df, expanded_df = load_and_process_data(file_mod_time)  # 반환값 세 개 모두 받기

    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error in display_detail: {e}")
        return []

    # 선택된 기안자와 날짜에 해당하는 연차 데이터 필터링
    detail_df = distributed_df[
        (distributed_df['기안자 이름'] == applicant_name) &
        (distributed_df['시작 날짜'].dt.strftime('%Y-%m-%d') == date)
    ]

    # 선택된 기안자의 최종 잔여 포인트 계산
    applicant_df = distributed_df[distributed_df['기안자 이름'] == applicant_name]
    applicant_df = applicant_df.sort_values(by='문서 번호')
    if not applicant_df.empty:
        final_remaining_point = applicant_df['잔여 포인트'].iloc[-1]
    else:
        final_remaining_point = 0  # 또는 다른 기본값 설정

    # 날짜 순으로 정렬
    detail_df = detail_df.sort_values(by='시작 날짜')

    # detail_df의 '잔여 포인트'를 최종 잔여 포인트로 업데이트
    detail_df.loc[:, '잔여 포인트'] = final_remaining_point

    # 날짜 포맷 변경
    detail_df['시작 날짜'] = detail_df['시작 날짜'].dt.strftime('%Y-%m-%d')

    # 필요한 컬럼만 선택
    detail_df = detail_df[['문서 번호', '기안자 이름', '기안 부서', '시작 날짜', '포인트', '휴가 종류', '휴가 사유', '잔여 포인트', '승인 여부']]

    # '잔여 포인트' 소수점 정리
    detail_df['잔여 포인트'] = detail_df['잔여 포인트'].round(2)

    return detail_df.to_dict('records')

# Dash 앱 실행
if __name__ == '__main__':
    cache.clear()
    app.run_server(debug=True)
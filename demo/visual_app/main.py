
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from data_processing import load_data, watch_file
import threading

# Bootstrap 4.5.2 CDN URL
BOOTSTRAP_CDN = "https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css"

# Dash 앱 초기화, Multi-Page 설정
app = dash.Dash(
    __name__,
    external_stylesheets=[BOOTSTRAP_CDN],  # Bootstrap CSS 추가
    use_pages=True,
    suppress_callback_exceptions=True
)

server = app.server  


# 초기 데이터 로드
data = load_data()  # 최초 데이터 로드 및 전처리

# 네비게이션 바 컴포넌트 생성
def create_navbar():
    # 페이지 리스트 가져오기
    pages = dash.page_registry.values()
    
    # NavItems 생성
    nav_items = []
    for page in pages:
        icon_class = ""
        if page['name'] == "Sales Dashboard":
            icon_class = "fas fa-chart-line"
        elif page['name'] == "Schedule Dashboard":
            icon_class = "fas fa-calendar-alt"
        elif page['name'] == "Score Dashboard":
            icon_class = "fas fa-star"
        elif page['name'] == "Feedback Dashboard":
            icon_class = "fas fa-comments"
        else:
            icon_class = "fas fa-tachometer-alt"
        
        nav_item = dbc.NavItem(
            dbc.NavLink(
                [
                    html.I(className=icon_class, style={'margin-right': '8px'}),
                    page['name']
                ],
                href=page['path'],
                active="exact",
                className="nav-link" 
            )
        )
        nav_items.append(nav_item)
    
    # 네비게이션 바 생성
    navbar = dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    [
                        html.Span(" Dashboard Navigation", className="ml-2")
                    ],
                    href="/main",
                    className="navbar-brand"
                ),
                dbc.Nav(
                    nav_items,
                    className="ml-auto navbar-nav",
                    navbar=True
                ),
            ]
        ),
        color="primary",
        dark=True,
        className="navbar navbar-expand-lg navbar-dark bg-primary mb-4" 
    )
    
    return navbar

navbar = create_navbar()

# 메인 페이지 레이아웃 설정
app.layout = dbc.Container(
    [
        # FontAwesome CSS 링크 추가 (CDN 사용)
        html.Link(
            rel='stylesheet',
            href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css'
        ),
        dcc.Location(id='url', refresh=False),  # URL 관리용 컴포넌트
        navbar,
        html.H1(
            "SalesUP Dashboard Example",
            className="text-center my-4",
            style={
                'font-weight': 'bold',   
                'font-size': '2em',
                'color': '#111111'
            }
        ),
        dash.page_container  # 각 페이지의 컨텐츠가 표시되는 영역
    ],
    fluid=True,
    className="bg-light", 
    style={
        'background-color': '#E0F7FA',  
        'padding': '10px'
    }
)

# 파일 변경 감시 기능을 별도의 스레드에서 실행하는 함수
def start_watch_file():
    watch_file()  # 파일 변경 감시 시작

if __name__ == "__main__":
    # 파일 변경 감시를 별도의 스레드에서 실행
    watch_thread = threading.Thread(target=start_watch_file, daemon=True)
    watch_thread.start()

    # Dash 앱 실행
    app.run_server(debug=True)

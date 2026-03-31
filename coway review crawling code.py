import streamlit as st
import time
import os
import ssl
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 1. 보안 설정 (SSL 에러 방지) - 로컬/서버 공통
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'

# --- Streamlit UI 설정 ---
st.set_page_config(page_title="코웨이 리뷰 수집기", page_icon="📝")
st.title("📝 코웨이 제품 리뷰 수집기")
st.markdown("""
코웨이 공식몰의 제품 상세 페이지 URL을 입력하면, 리뷰를 자동으로 수집하여 엑셀 파일로 만들어 드립니다.
*배포 환경(무료 서버)의 성능 한계로 리뷰가 아주 많을 경우 시간이 오래 걸리거나 멈출 수 있습니다.*
""")

# URL 입력창
url = st.text_input("코웨이 제품 URL을 입력하세요:", placeholder="https://www.coway.com/product/...")

# 수집 시작 버튼
if st.button("리뷰 수집 시작 ✨"):
    if not url:
        st.error("URL을 입력해주세요.")
    elif "coway.com" not in url:
        st.error("올바른 코웨이 제품 URL이 아닙니다.")
    else:
        # 상태 메시지 표시를 위한 placeholder
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # --- Selenium 브라우저 설정 (핵심: Headless) ---
        status_text.text("🌐 브라우저 초기화 중...")
        options = Options()
        options.add_argument('--headless') # 화면 없음 (서버 필수)
        options.add_argument('--no-sandbox') # 보안 기능 비활성화 (리눅스 서버 필수)
        options.add_argument('--disable-dev-shm-usage') # 공유 메모리 부족 방지
        options.add_argument('--disable-gpu') # GPU 가속 비활성화
        # User-Agent 설정 (봇 탐지 회피 확률을 높임)
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        try:
            # webdriver-manager를 통해 드라이버 자동 설치 및 실행
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            status_text.text("📄 웹페이지 로딩 중... (약 5초 소요)")
            driver.get(url)
            driver.maximize_window()
            time.sleep(5) # 전체 페이지 로딩 대기
            progress_bar.progress(10)

            # --- 1. 리뷰 영역까지 자동으로 스크롤 내리기 ---
            status_text.text("🔍 리뷰 영역을 찾는 중...")
            for i in range(5): 
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)
            progress_bar.progress(20)

            # --- 2. '더보기' 버튼 반복 클릭 ---
            status_text.text("👆 '더보기' 버튼을 클릭하여 모든 리뷰를 불러오는 중입니다. 잠시만 기다려주세요...")
            click_count = 0
            while True:
                try:
                    # 'btn_list more' 버튼 찾기
                    more_button = driver.find_element(By.CSS_SELECTOR, "button.btn_list.more")
                    
                    if more_button.is_displayed():
                        # 버튼이 보이도록 스크롤 후 클릭
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", more_button)
                        click_count += 1
                        # st.write(f"{click_count}번째 더보기 클릭...") # 디버깅용
                        time.sleep(2) # 리뷰 로딩 대기
                    else:
                        break
                except:
                    # st.info("모든 리뷰를 불러왔습니다.")
                    break
            progress_bar.progress(60)

            # --- 3. 데이터 추출 (BeautifulSoup) ---
            status_text.text("📊 로딩된 리뷰 데이터를 수집 중...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 클래스명으로 데이터 매칭
            contents = soup.find_all('p', class_='txt_wrap')
            dates = soup.find_all('div', class_='info2')

            reviews = []
            # 데이터 개수가 맞지 않을 수 있으므로 최소 개수에 맞춰 반복
            for i in range(len(contents)):
                content_text = contents[i].get_text(strip=True)
                # 날짜 정보가 있는 경우만 가져오기
                date_info = dates[i].get_text(strip=True) if i < len(dates) else "N/A"
                
                if content_text:
                    reviews.append({
                        "날짜/정보": date_info,
                        "리뷰내용": content_text
                    })
            progress_bar.progress(80)

            # --- 4. 결과 처리 및 다운로드 버튼 생성 ---
            if reviews:
                df = pd.DataFrame(reviews)
                st.success(f"✅ 완료! 총 {len(reviews)}건의 리뷰를 수집했습니다.")
                
                # 웹 화면에 수집된 데이터 미리보기
                st.dataframe(df, use_container_width=True)

                # 엑셀 파일 생성을 위한 메모리 버퍼
                excel_data = BytesIO()
                # xlsxwriter 엔진 사용 (requirements.txt에 추가 필요)
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='CowayReviews')
                
                # 다운로드 버튼
                st.download_button(
                    label="📥 수집된 리뷰 엑셀 파일 다운로드",
                    data=excel_data.getvalue(),
                    file_name=f"coway_reviews_{time.strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("\n❌ 데이터를 찾지 못했습니다. URL이 정확한지, 리뷰가 존재하는지 확인해주세요.")
            
            progress_bar.progress(100)

        except Exception as e:
            st.error(f"⚠️ 오류 발생: {e}")
            st.info("무료 서버 환경에서는 일시적인 네트워크 문제로 에러가 발생할 수 있습니다. 잠시 후 다시 시도해보세요.")

        finally:
            # 브라우저 종료 (매우 중요: 메모리 누수 방지)
            if 'driver' in locals():
                driver.quit()
                status_text.text("브라우저 세션 종료.")

# --- 하단 정보 ---
st.markdown("---")
st.caption("Developed by AI Assistant | 데이터 수집 목적 이외의 무단 사용을 금합니다.")

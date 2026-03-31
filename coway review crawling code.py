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

# 1. 보안 설정 (SSL 에러 방지)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'

# --- Streamlit UI 설정 ---
st.set_page_config(page_title="코웨이 리뷰 수집기", page_icon="📝")
st.title("📝 코웨이 제품 리뷰 수집기")
st.markdown("URL을 입력하면 리뷰를 수집해 엑셀로 저장합니다. (Streamlit Cloud 최적화 버전)")

url = st.text_input("코웨이 제품 URL을 입력하세요:", placeholder="https://www.coway.com/product/...")

if st.button("리뷰 수집 시작 ✨"):
    if not url:
        st.error("URL을 입력해주세요.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # --- Selenium 브라우저 설정 (Streamlit Cloud 전용 경로) ---
        status_text.text("🌐 브라우저를 초기화 중입니다...")
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Streamlit Cloud 서버에 설치된 크롬 및 드라이버 경로 직접 지정
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")

        try:
            driver = webdriver.Chrome(service=service, options=options)
            
            status_text.text("📄 웹페이지 접속 중...")
            driver.get(url)
            time.sleep(5) 
            progress_bar.progress(20)

            # --- 1. 리뷰 영역으로 스크롤 ---
            status_text.text("🔍 리뷰 데이터를 찾는 중...")
            for _ in range(3): 
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)

            # --- 2. '더보기' 버튼 반복 클릭 ---
            status_text.text("👆 모든 리뷰를 불러오는 중 (더보기 클릭)...")
            while True:
                try:
                    more_button = driver.find_element(By.CSS_SELECTOR, "button.btn_list.more")
                    if more_button.is_displayed():
                        driver.execute_script("arguments[0].click();", more_button)
                        time.sleep(2) 
                    else:
                        break
                except:
                    break
            progress_bar.progress(60)

            # --- 3. 데이터 추출 ---
            status_text.text("📊 수집된 리뷰 읽기 중...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            contents = soup.find_all('p', class_='txt_wrap')
            dates = soup.find_all('div', class_='info2')

            reviews = []
            for i in range(len(contents)):
                content_text = contents[i].get_text(strip=True)
                date_info = dates[i].get_text(strip=True) if i < len(dates) else "N/A"
                if content_text:
                    reviews.append({"날짜/정보": date_info, "리뷰내용": content_text})
            
            progress_bar.progress(90)

            # --- 4. 결과 출력 및 다운로드 ---
            if reviews:
                df = pd.DataFrame(reviews)
                st.success(f"✅ 총 {len(reviews)}건의 리뷰 수집 완료!")
                st.dataframe(df, use_container_width=True)

                excel_data = BytesIO()
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=excel_data.getvalue(),
                    file_name="coway_reviews.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("데이터를 찾지 못했습니다. URL을 확인해주세요.")

        except Exception as e:
            st.error(f"⚠️ 오류 발생: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
            progress_bar.progress(100)
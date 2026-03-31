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

# SSL 보안 설정
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'

st.set_page_config(page_title="코웨이 리뷰 수집기", page_icon="📝")
st.title("📝 코웨이 제품 리뷰 수집기 (중복 제거 버전)")

url = st.text_input("코웨이 제품 URL을 입력하세요:", placeholder="https://www.coway.com/product/...")

if st.button("리뷰 수집 시작 ✨"):
    if not url:
        st.error("URL을 입력해주세요.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")

        try:
            status_text.text("🌐 브라우저 실행 중...")
            driver = webdriver.Chrome(service=service, options=options)
            
            status_text.text("📄 페이지 로딩 중...")
            driver.get(url)
            time.sleep(5)
            progress_bar.progress(20)

            # 1. 리뷰 영역으로 스크롤 (조금 더 확실하게 내림)
            status_text.text("🔍 리뷰 영역 스캔 중...")
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)

            # 2. '더보기' 버튼 반복 클릭
            status_text.text("👆 모든 리뷰 불러오는 중 (더보기 클릭)...")
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

            # 3. 데이터 추출 (중복 제거 로직 핵심)
            status_text.text("📊 데이터 정제 및 중복 제거 중...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 실제 리뷰가 담긴 컨테이너만 지정 (상단 필터 설명 제외)
            review_container = soup.find('div', class_='review_list')
            
            reviews = []
            seen_contents = set() # 중복 체크용 셋

            if review_container:
                # 컨테이너 안의 리뷰 본문과 날짜만 가져옴
                contents = review_container.find_all('p', class_='txt_wrap')
                dates = review_container.find_all('div', class_='info2')

                for i in range(len(contents)):
                    # 텍스트 추출 및 "신고" 등 불필요한 단어 제거
                    content_raw = contents[i].get_text(strip=True).replace("신고", "")
                    date_raw = dates[i].get_text(strip=True).replace("신고", "") if i < len(dates) else "N/A"
                    
                    # 중복 검사 (이미 추가된 내용이면 건너뜀)
                    if content_raw and content_raw not in seen_contents:
                        reviews.append({
                            "날짜/정보": date_raw,
                            "리뷰내용": content_raw
                        })
                        seen_contents.add(content_raw)
            
            progress_bar.progress(90)

            # 4. 결과 출력
            if reviews:
                df = pd.DataFrame(reviews)
                st.success(f"✅ 중복 제외 총 {len(reviews)}건 수집 완료!")
                st.dataframe(df, use_container_width=True)

                excel_data = BytesIO()
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 정제된 엑셀 파일 다운로드",
                    data=excel_data.getvalue(),
                    file_name=f"coway_reviews_{int(time.time())}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("수집된 리뷰가 없습니다. 페이지 구조를 확인해 주세요.")

        except Exception as e:
            st.error(f"⚠️ 오류 발생: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
            progress_bar.progress(100)
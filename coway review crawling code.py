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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# SSL 보안 설정
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'

st.set_page_config(page_title="코웨이 리뷰 수집기", page_icon="📝")
st.title("📝 코웨이 제품 리뷰 수집기 (안정화 버전)")

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
            status_text.text("🌐 브라우저를 실행 중입니다...")
            driver = webdriver.Chrome(service=service, options=options)
            
            status_text.text("📄 페이지에 접속 중...")
            driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)
            progress_bar.progress(20)

            # 1. 리뷰 섹션이 보일 때까지 스크롤 반복
            status_text.text("🔍 리뷰 영역을 찾는 중 (스크롤 내려가는 중)...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            for i in range(7): # 스크롤 횟수 증가
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1.5)
            
            progress_bar.progress(40)

            # 2. '더보기' 버튼 클릭 (요소가 나타날 때까지 대기 추가)
            status_text.text("👆 '더보기' 버튼을 확인하여 리뷰를 확장하는 중...")
            for _ in range(15): # 최대 15번 클릭 시도
                try:
                    # 더보기 버튼이 로드될 때까지 잠깐 대기
                    more_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_list.more"))
                    )
                    driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(2) # 로딩 대기
                except:
                    # 더 이상 버튼이 없으면 탈출
                    break
            
            progress_bar.progress(70)

            # 3. 데이터 추출
            status_text.text("📊 데이터를 파싱하고 있습니다...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 구역을 너무 좁게 잡으면 못 찾을 수 있으므로, 
            # 리뷰 본문 클래스(txt_wrap)를 기준으로 찾되 불필요한 값은 필터링합니다.
            all_contents = soup.find_all('p', class_='txt_wrap')
            all_dates = soup.find_all('div', class_='info2')

            reviews = []
            seen_contents = set()
            
            # 필터링할 제외 키워드 (제품 설명 등에 포함된 단어)
            exclude_keywords = ["에어매칭필터", "맞춤 필터", "청정 성능", "경험해보세요"]

            for i in range(len(all_contents)):
                content_raw = all_contents[i].get_text(strip=True).replace("신고", "")
                date_raw = all_dates[i].get_text(strip=True).replace("신고", "") if i < len(all_dates) else "N/A"
                
                # 유효성 검사: 본문이 있고, 제외 키워드가 없으며, 중복이 아닐 때만 저장
                if content_raw and not any(k in content_raw for k in exclude_keywords):
                    if content_raw not in seen_contents:
                        reviews.append({
                            "날짜/정보": date_raw,
                            "리뷰내용": content_raw
                        })
                        seen_contents.add(content_raw)
            
            progress_bar.progress(90)

            # 4. 결과 출력
            if reviews:
                df = pd.DataFrame(reviews)
                st.success(f"✅ 총 {len(reviews)}건의 고유 리뷰를 수집했습니다!")
                st.dataframe(df, use_container_width=True)

                excel_data = BytesIO()
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=excel_data.getvalue(),
                    file_name=f"coway_reviews_{int(time.time())}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("⚠️ 리뷰 데이터를 찾지 못했습니다. URL이 상세 페이지가 맞는지, 리뷰가 존재하는지 확인해 주세요.")
                # 디버깅용: 현재 페이지의 텍스트 일부 출력 (개발자 확인용)
                if st.checkbox("페이지 구조 확인(디버그)"):
                    st.write(soup.get_text()[:500])

        except Exception as e:
            st.error(f"⚠️ 실행 중 오류 발생: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
            progress_bar.progress(100)

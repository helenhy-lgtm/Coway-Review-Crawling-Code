import streamlit as st
import time
import os
import ssl
import re
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
st.title("📝 코웨이 제품 리뷰 수집기")

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
            
            status_text.text("📄 페이지 접속 중...")
            driver.get(url)
            time.sleep(5)
            progress_bar.progress(20)

            # 1. 리뷰 영역 탐색을 위한 스크롤
            status_text.text("🔍 리뷰 영역 스캔 중...")
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)

            # 2. '더보기' 버튼 반복 클릭
            status_text.text("👆 '더보기' 버튼을 눌러 모든 리뷰를 불러오는 중...")
            while True:
                try:
                    more_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_list.more"))
                    )
                    driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(1.5)
                except:
                    break
            progress_bar.progress(60)

            # 3. 데이터 추출 및 정제
            status_text.text("📊 불필요한 홍보 문구 제거 및 데이터 정제 중...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 개별 리뷰 아이템 단위를 먼저 찾습니다 (리뷰 1건당 하나의 li 또는 div)
            # 코웨이 리뷰 리스트 아이템의 클래스명을 타겟팅합니다.
            review_items = soup.select('div.review_list ul li') 
            if not review_items:
                # 위 선택자로 안 잡힐 경우를 대비한 대체 선택자
                review_items = soup.find_all('div', class_='txt_wrap')

            reviews = []
            seen_contents = set()
            
            # 날짜 형식 체크를 위한 정규식 (예: 2025.01.01)
            date_pattern = re.compile(r'\d{4}\.\d{2}\.\d{2}')

            for item in review_items:
                # 1. 리뷰 본문 추출
                content_tag = item.find('p', class_='txt_wrap') if hasattr(item, 'find') else item
                if not content_tag: continue
                
                content_text = content_tag.get_text(strip=True).replace("신고", "")
                
                # 2. 날짜/정보 추출 (해당 리뷰 아이템 내부에 있는 info2 클래스)
                # item이 tag 객체인 경우에만 find 수행
                parent = item if hasattr(item, 'find') else item.parent
                date_tag = parent.find('div', class_='info2') if parent else None
                date_info = date_tag.get_text(strip=True).replace("신고", "") if date_tag else "N/A"

                # [핵심 로직] 
                # 1. 본문에 '에어매칭필터' 같은 홍보 문구가 포함되어 있거나 
                # 2. 날짜 정보에 날짜 형식이 전혀 없다면 홍보 영역으로 간주하고 버림
                if "에어매칭필터" in content_text or "맞춤 필터" in content_text:
                    continue
                
                if content_text and content_text not in seen_contents:
                    # 날짜 정보가 유효한 경우만 저장하거나, 비정상적인 긴 텍스트는 필터링
                    if len(date_info) < 50: 
                        reviews.append({
                            "날짜/정보": date_info,
                            "리뷰내용": content_text
                        })
                        seen_contents.add(content_text)

            progress_bar.progress(90)

            # 4. 결과 출력
            if reviews:
                df = pd.DataFrame(reviews)
                st.success(f"✅ 정제 완료! 총 {len(reviews)}건의 리뷰를 수집했습니다.")
                st.dataframe(df, use_container_width=True)

                excel_data = BytesIO()
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 정제된 엑셀 파일 다운로드",
                    data=excel_data.getvalue(),
                    file_name=f"coway_reviews_cleaned_{int(time.time())}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("⚠️ 유효한 리뷰 데이터를 찾지 못했습니다.")

        except Exception as e:
            st.error(f"⚠️ 오류 발생: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
            progress_bar.progress(100)

import time
import os
import ssl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd

# 보안 설정 (SSL 에러 방지)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'

url = input("코웨이 제품 URL을 입력하세요: ")

service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
driver = webdriver.Chrome(service=service, options=options)

try:
    print("\n웹페이지 로딩 중...")
    driver.get(url)
    driver.maximize_window()
    time.sleep(5) # 전체 페이지 로딩 대기

    # 1. 리뷰 영역까지 자동으로 스크롤 내리기
    # txt_wrap이 보일 때까지 조금씩 내려갑니다.
    print("리뷰 영역을 찾는 중...")
    for i in range(5): 
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1)

    # 2. '더보기' 버튼 반복 클릭
    while True:
        try:
            # 알려주신 'btn_list more' 버튼 찾기
            more_button = driver.find_element(By.CSS_SELECTOR, "button.btn_list.more")
            
            if more_button.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", more_button)
                print("더보기 클릭 성공...")
                time.sleep(2) # 리뷰 로딩 대기
            else:
                break
        except:
            print("더 이상 '더보기' 버튼이 없거나 모든 리뷰를 불러왔습니다.")
            break

    # 3. 데이터 추출 (BeautifulSoup)
    print("데이터 수집 시작...")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # 알려주신 클래스명으로 데이터 매칭
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

    # 4. 결과 저장
    if reviews:
        df = pd.DataFrame(reviews)
        df.to_excel("coway_reviews_final.xlsx", index=False)
        print(f"\n✅ 완료! 총 {len(reviews)}건의 리뷰를 'coway_reviews_final.xlsx'로 저장했습니다.")
    else:
        print("\n❌ 데이터를 찾지 못했습니다. 클래스명이나 페이지 로딩 상태를 다시 확인해야 합니다.")

except Exception as e:
    print(f"오류 발생: {e}")

finally:
    driver.quit()
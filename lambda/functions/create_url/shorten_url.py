# 1. URL 단축 (create_short_url)
def lambda_handler(event, context):
    url = event['body']['url']           # 긴 URL 받기
    short_code = generate_short_code()   # 해시로 짧은 코드 생성
    table.put_item(...)                  # DynamoDB 저장
    return {'shortUrl': f'https://short.url/{short_code}'}



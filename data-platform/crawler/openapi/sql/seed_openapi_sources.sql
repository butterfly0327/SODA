INSERT INTO openapi_sources (source_code, source_name, base_url, collection_type)
VALUES
    -- 지도/교통
    ('NAVER_CLOUD_MAPS', '네이버 클라우드 플랫폼 Maps', 'https://naveropenapi.apigw.ntruss.com', 'CRAWL'),
    ('ODSAY',           'ODsay 대중교통',               'https://api.odsay.com',                 'CRAWL'),
    ('TMAP_SKT',        'T맵 (SKT)',                    'https://apis.openapi.sk.com',            'CRAWL'),
    -- 금융
    ('KIS_DEVELOPERS',  '한국투자증권 KIS Developers',  'https://openapi.koreainvestment.com:9443','CRAWL'),
    ('TOSSPAYMENTS',    '토스페이먼츠',                 'https://api.tosspayments.com',           'CRAWL'),
    -- 가상화폐
    ('UPBIT',           '업비트 (Upbit)',                'https://api.upbit.com',                  'CRAWL'),
    ('BITHUMB',         '빗썸 (Bithumb)',                'https://api.bithumb.com',                'CRAWL'),
    ('COINONE',         '코인원 (Coinone)',              'https://api.coinone.co.kr',              'CRAWL'),
    -- 개발자 플랫폼
    ('KAKAO_DEVELOPERS','카카오 Developers',            'https://dapi.kakao.com',                 'CRAWL'),
    -- 게임
    ('NEXON_OPENAPI',   '넥슨 Open API',                'https://openapi.nexon.com',              'CRAWL'),
    ('NEOPLE_DEVELOPERS','Neople Developers',           'https://api.neople.co.kr',               'CRAWL'),
    -- 영화/공연
    ('KOBIS',           '영화진흥위원회 (KOBIS)',         'http://www.kobis.or.kr/kobisopenapi',    'CRAWL'),
    ('KMDB',            '한국영화데이터베이스 (KMDb)',    'http://api.koreafilm.or.kr',             'CRAWL'),
    ('KOPIS',           '공연예술통합전산망 (KOPIS)',     'http://www.kopis.or.kr/openApi',         'CRAWL'),
    -- 공공데이터
    ('DATAGOKR',        '공공데이터포털 Open API',       'https://api.data.go.kr',                 'CSV')
ON CONFLICT (source_code)
DO UPDATE SET
    source_name     = EXCLUDED.source_name,
    base_url        = EXCLUDED.base_url,
    collection_type = EXCLUDED.collection_type;

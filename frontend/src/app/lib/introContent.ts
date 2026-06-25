import { Car, CloudRain, ShieldAlert, Store } from 'lucide-react';

export const HOME_INTRO_TITLE = '무슨 데이터를 찾고 계신가요?';

export const HOME_INTRO_EXAMPLES = [
  {
    label: '날씨 기반 수요 예측',
    prompt: '날씨 기반 프로젝트를 만들려고 해. openapi와 데이터셋 추천해줘',
    icon: CloudRain,
  },
  {
    label: '교통 혼잡 예측',
    prompt: '교통 혼잡 예측 프로젝트를 만들려고 해. openapi와 데이터셋 추천해줘',
    icon: Car,
  },
  {
    label: '소상공인 상권 분석',
    prompt: '소상공인 상권 분석 프로젝트를 만들려고 해. openapi와 데이터셋 추천해줘',
    icon: Store,
  },
  {
    label: '재난 안전 모니터링',
    prompt: '재난 안전 모니터링 프로젝트를 만들려고 해. openapi와 데이터셋 추천해줘',
    icon: ShieldAlert,
  },
];

export const HOME_INTRO_FOOTER_NOTE = 'SODA는 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요. 쿠키 기본 설정을 참고하세요.';

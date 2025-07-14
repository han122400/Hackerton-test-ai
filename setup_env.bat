@echo off
echo 🔄 가상환경 초기화 중...

:: 기존 가상환경 폴더 삭제 (있을 경우)
if exist mediapipe-env (
    echo 기존 가상환경 삭제 중...
    rmdir /s /q mediapipe-env
)

:: Python 3.10 기반 가상환경 생성
echo 가상환경 생성 중...
py -3.10 -m venv mediapipe-env

:: 가상환경 활성화
call mediapipe-env\Scripts\activate

:: pip 업그레이드 및 필수 패키지 설치
echo 필수 패키지 설치 중...
::pip install --upgrade pip
pip install fastapi uvicorn opencv-python mediapipe python-multipart

:: 결과 출력
echo 완료! 가상환경이 설정되고 패키지가 설치되었습니다.
echo.
echo ▶ 가상환경 활성화: call mediapipe-env\Scripts\activate
echo ▶ 서버 실행: uvicorn server:app --reload --host 0.0.0.0 --port 8000

pause

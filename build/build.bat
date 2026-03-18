@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

echo ============================================
echo  ChatSummarizer - Windows 빌드 스크립트
echo ============================================
echo.

:: 프로젝트 루트로 이동 (build.bat 이 있는 폴더의 부모)
cd /d "%~dp0.."

:: Python 버전 확인
python --version 2>nul
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.11+ 를 설치하세요.
    pause & exit /b 1
)

:: 가상환경 생성 (선택)
if not exist "venv" (
    echo [1/4] 가상환경 생성 중...
    python -m venv venv
)
call venv\Scripts\activate.bat

:: 의존성 설치
echo [2/4] 의존성 설치 중...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

:: UPX 설치 여부 확인 (없으면 경고만)
where upx >nul 2>&1
if errorlevel 1 (
    echo [경고] UPX가 PATH에 없습니다. UPX 없이 빌드합니다.
    echo        https://upx.github.io 에서 UPX 설치 시 파일 크기 20~30%% 추가 절감 가능.
)

:: 이전 빌드 정리
echo [3/4] 이전 빌드 정리 중...
if exist "dist\ChatSummarizer.exe" del /f "dist\ChatSummarizer.exe"
if exist "build\ChatSummarizer" rmdir /s /q "build\ChatSummarizer"

:: PyInstaller 빌드
echo [4/4] PyInstaller 빌드 중 (시간이 걸릴 수 있습니다)...
pyinstaller build\build.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo [실패] 빌드에 실패했습니다. 위 오류 메시지를 확인하세요.
    pause & exit /b 1
)

:: 결과 확인
echo.
echo ============================================
echo  빌드 완료!
echo ============================================
if exist "dist\ChatSummarizer.exe" (
    for %%A in ("dist\ChatSummarizer.exe") do (
        set SIZE=%%~zA
        set /a SIZE_MB=!SIZE! / 1048576
        echo  파일: dist\ChatSummarizer.exe
        echo  크기: !SIZE_MB! MB (!SIZE! bytes)
        if !SIZE_MB! GTR 50 (
            echo  [경고] 크기가 50MB를 초과합니다^^! build\build.spec 의 excludes 목록을 검토하세요.
        ) else (
            echo  [OK] 크기 제한 50MB 이하 통과^^!
        )
    )
) else (
    echo [오류] dist\ChatSummarizer.exe 를 찾을 수 없습니다.
)
echo ============================================
echo.
pause

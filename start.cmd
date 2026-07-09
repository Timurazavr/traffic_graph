@echo off
chcp 65001 > nul

echo [1/3] Компиляция C++ проекта...
g++ main.cpp DynamicGraph.cpp Socket.cpp -o main.exe -lws2_32
if %errorlevel% neq 0 (
    echo Ошибка компиляции! Выполнение прервано.
    pause
    exit /b %errorlevel%
)

echo [2/3] Фоновый запуск Python скрипта...
start "" "C:\Users\Timur\Programs\Python\Python313\python.exe" "C:\Users\Timur\Desktop\traffic_graph\main.py"

echo [3/3] Запуск скомпилированного файла...
main.exe

pause

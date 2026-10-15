@echo off
REM scan_param_editor.exe / scan_param_editor_gui.exe をビルドする。
REM 事前に Python と `pip install pyinstaller pyyaml ttkbootstrap` が必要(ビルドするPCのみ)。
REM 生成された exe (dist\*.exe) と config.yaml を、使うPCにコピーすれば単体で動く(Python不要)。

cd /d "%~dp0"
pyinstaller --onefile --name scan_param_editor --console --clean scan_param_editor.py
pyinstaller --onefile --name scan_param_editor_gui --windowed --clean --collect-all ttkbootstrap scan_param_editor_gui.py
echo.
echo 完了: dist\scan_param_editor.exe (CLI版) / dist\scan_param_editor_gui.exe (GUI版)
pause
